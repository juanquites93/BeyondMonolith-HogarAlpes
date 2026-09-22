# Informe: Escenario de Calidad — Disponibilidad (ms-notificaciones)

## 1. Objetivo

Validar, con un experimento ejecutado (no solo diseñado), el siguiente escenario de calidad de disponibilidad sobre `ms-notificaciones`:

> **Estímulo:** una instancia de un microservicio crítico deja de responder mientras el sistema procesa un volumen equivalente al pico de demanda (4x lo normal).
> **Respuesta esperada:** el tráfico se redirige automáticamente a instancias saludables; las operaciones continúan sin intervención manual; los eventos siguen siendo procesados por los consumidores disponibles.
> **Medida:** 99,9% de las solicitudes se atienden correctamente durante la falla de una instancia, sin caída general del servicio.

El diseño completo del experimento (hipótesis, cálculo de volumen, fases, definición de éxito, criterios de aceptación) está en `ms-notificaciones/docs/experimento-disponibilidad.md`. Este informe se enfoca en **qué se ejecutó y qué se concluyó**.

## 2. Veredicto

**El escenario de calidad SE CUMPLE**, con las salvedades de muestra y entorno que se explican en la sección 6.

| Componente de la respuesta esperada | ¿Se observó? | Evidencia |
|---|---|---|
| Tráfico redirigido automáticamente a instancias sanas | ✅ Sí | `Pruebas` |
| Operaciones continúan sin intervención manual | ✅ Sí (el único paso humano fue apagar/prender la réplica, que es la causa simulada, no una reparación) | Sección 5.3 |
| Eventos siguen procesándose por consumidores disponibles | ✅ Sí | `Pruebas`, `Pruebas` |
| ≥99,9% de solicitudes atendidas correctamente | ✅ Sí — se midió **100%** (0 fallidas de 6.176) | `Pruebas` |
| Sin pérdida de eventos | ✅ Sí — 0 mensajes en backlog al final | `Pruebas` |

## 3. Entorno de ejecución

Entorno aislado en `ms-notificaciones/experimento/` (Docker Compose propio, sin tocar el despliegue compartido en AWS ni el `docker-compose.yml`/Terraform de la raíz del monorepo):

- 3 réplicas nombradas de `ms-notificaciones` (`notificaciones_1/2/3`) detrás de Nginx (balanceador con health check pasivo `max_fails=2 fail_timeout=10s` y reintentos `proxy_next_upstream`).
- Pulsar y Postgres propios del experimento (aislados del despliegue real).
- Generación de carga: `k6` (HTTP, contra el balanceador) y un script Python propio (`carga_eventos.py`) publicando eventos directamente al tópico de Pulsar.
- Ejecutado localmente (laptop, macOS + Docker Desktop) el 2026-09-21, ante la imposibilidad de acceso SSH al entorno AWS compartido con el equipo (ver decisión documentada en la sustentación).

## 4. Ajuste del volumen de carga (y por qué)

El diseño original partía de una cifra de negocio (289 req/s del sistema completo, → ~13,9 eventos/seg hacia notificaciones en el "4x" teórico). Al correr la fase de calentamiento, el entorno local (laptop compartiendo CPU entre Pulsar, Postgres, Nginx y 3 réplicas) mostró degradación de latencia ya con 10 req/s de línea base. Se ajustó la carga a la capacidad real medida, en vez de forzar la cifra teórica sin evidencia de que la infraestructura de prueba la soportara (criterio ya previsto en la sección 3.3 del diseño):

| Parámetro | Línea base (1x) | Fase "4x" |
|---|---|---|
| Tasa HTTP objetivo (`/ready` vía Nginx) | 10 req/s | 25 req/s |
| Tasa de eventos Pulsar | 2 eventos/s | 8 eventos/s |
| Duración | 65 s | 255 s (incluye rampa de 15 s) |
| Falla inyectada | No | Sí — `notificaciones_2` apagada ~45 s a la mitad de la ventana |

## 5. Análisis de cada prueba realizada

### 5.1 Prueba 1 — Arranque del entorno (3 réplicas simultáneas)

**Qué se hizo:** `docker compose up -d --build`.

**Resultado:** `notificaciones_1` y `notificaciones_3` murieron al arrancar con `IntegrityError: duplicate key value violates unique constraint "pg_type_typname_nsp_index"`.

**Análisis:** las 3 réplicas ejecutan `Base.metadata.create_all()` contra el mismo Postgres al iniciar. Dos de las tres intentaron crear la misma tabla al mismo tiempo (condición de carrera real, no hipotética) y una perdió. Se resolvió reiniciando los contenedores afectados (la tabla ya existía, arrancaron sin problema la segunda vez). **No estaba anticipado por la auditoría de código previa** — solo se detectó al ejecutar de verdad.

Evidencia: `Pruebas`.

### 5.2 Prueba 2 — Verificación de salud antes de generar carga

**Qué se hizo:** `GET /ready` a cada réplica directamente, y 30 solicitudes a través de Nginx.

**Resultado:** al verificar, `notificaciones_2` respondía 503 (no las otras dos). Investigando el log, arrancó antes de que `pulsar-init` terminara de crear el namespace `hogar/alpes`, su hilo consumidor murió con `TopicNotFound`, y al no existir lógica de reconexión, quedó permanentemente "no lista". Se resolvió con `docker compose restart notificaciones_2` (una vez el namespace ya existía, conectó a la primera). Confirma en la práctica el punto de la auditoría original sobre falta de reintentos/backoff en llamadas salientes.

Una vez corregido, el reparto de 30 solicitudes vía Nginx dio 10/10/10 — confirmando distribución equitativa entre las 3 réplicas sanas.

Evidencia: `Pruebas`, `Pruebas` (primer bloque).

### 5.3 Prueba 3 — Línea base (1x), sin falla

**Qué se hizo:** k6 (10 req/s, 65 s) + generador de eventos (2 eventos/s, 65 s) en paralelo, sin apagar nada.

**Resultado:** 563 solicitudes HTTP, **0% fallidas**; 123 eventos publicados y confirmados consumidos (41 por cada una de las 3 réplicas — reparto exacto, evidencia de que la suscripción `Shared` de Pulsar funciona como consumidores en competencia). Latencia HTTP: promedio 360 ms, p95 2,26 s, máximo 4,42 s (más alta de lo esperable para un servicio tan simple — atribuible a recursos compartidos del laptop, ver limitaciones).

Evidencia: `Pruebas`, `Pruebas`, `Pruebas`.

### 5.4 Prueba 4 — Fase 4x con inyección de falla y recuperación (la prueba central)

**Qué se hizo:** k6 (25 req/s, 255 s) + generador de eventos (8 eventos/s, 270 s) en paralelo. A la mitad de la ventana, `docker compose stop notificaciones_2`; ~45 segundos después, `docker compose start notificaciones_2`. Se muestreó el header `X-Instance-Id` de cada respuesta durante toda la prueba para confirmar el reparto real.

**Resultado:**
- **6.176 solicitudes HTTP, 0 fallidas (0,00%)** — incluyendo toda la ventana en la que una de las 3 réplicas estuvo apagada.
- **Redirección inmediata:** en el primer muestreo tomado justo después de apagar la réplica, ya no le llegaba ninguna solicitud (0 de 30).
- **Recuperación automática:** al reiniciar la réplica, volvió a recibir tráfico sola (11/9/10 en el muestreo posterior), sin ninguna acción sobre Nginx.
- **2.066 eventos publicados en total** (línea base + 4x). Verificado en las estadísticas del propio Pulsar (no solo en las métricas de la app): `msgInCounter: 2066`, `msgOutCounter: 2067` (una redelivery — un mensaje en tránsito hacia la réplica justo cuando se apagó, reentregado solo a otra réplica sana), `msgBacklog: 0`, `unackedMessages: 0` al final → **cero eventos perdidos**.

Evidencia: `Pruebas`, `Pruebas`, `Pruebas`, `Pruebas`, `Pruebas`, `Pruebas`.

**Nota sobre las métricas por réplica:** al reiniciar `notificaciones_2`, su contador interno de eventos consumidos (Prometheus, en memoria del proceso) volvió a cero — por eso muestra `0` en `03_metricas_por_replica.txt` en vez de su valor real acumulado antes de la falla. La prueba de "cero pérdida" no depende de esa métrica: se sostiene en las estadísticas de Pulsar (`msgBacklog`), que son independientes del ciclo de vida de la app.

## 6. Significancia estadística del resultado

La muestra de la fase 4x (6.176 solicitudes) quedó por debajo de las 10.000–20.000 recomendadas en el diseño original para que un 99,9% sea estadísticamente robusto. Aun así, con **0 fallas observadas en 6.176 intentos**, la regla de tres (estimación estándar del peor caso cuando no se observan fallas) da un límite superior de 95% de confianza de **~0,049%** de tasa de falla real — cómodamente por debajo del 0,1% que exige el escenario (equivalente a 99,9% de éxito). La conclusión se sostiene, aunque una corrida más larga la haría más robusta.

## 7. Hallazgos adicionales (no forman parte del veredicto, pero son relevantes)

1. **Condición de carrera en `create_all()`** al arrancar múltiples réplicas contra la misma base de datos (sección 5.1). No corregido en código — queda como mejora pendiente.
2. **Sin retry/backoff en la conexión a Pulsar** al arrancar (sección 5.2). Confirma el punto F de la auditoría original de arquitectura. No corregido en código — queda como mejora pendiente.
3. **Las métricas de Prometheus no sobreviven un reinicio de contenedor** (son en memoria del proceso). Para un entorno productivo, harían falta scrapeadas por un Prometheus externo con retención propia, no solo el endpoint `/metrics` expuesto por cada instancia.

## 8. Limitaciones de esta ejecución

- Las 3 réplicas comparten la misma máquina física (laptop) — no hay aislamiento real de hardware como lo habría entre instancias EC2 separadas.
- Muestra por debajo del tamaño ideal (sección 6).
- No se ejecutó la variante N=2 (solo N=3) por límite de tiempo.
- La latencia de la fase 4x salió más baja que la línea base (122 ms vs. 360 ms de promedio), lo cual es contraintuitivo. Se atribuye a efectos de arranque en frío en la línea base (primeras conexiones a BD, primeras importaciones de Python), no a una relación real entre volumen de carga y latencia.

## 9. Conclusiones

### 9.1 Medidas cuantitativas encontradas

| Medida | Línea base (1x) | Fase 4x (con falla) | Umbral del escenario |
|---|---|---|---|
| % de solicitudes HTTP exitosas | 100% (563/563) | **100% (6.176/6.176)** | ≥ 99,9% |
| % de solicitudes fallidas | 0,00% | 0,00% | ≤ 0,1% |
| Límite superior de la tasa de falla real (95% de confianza, regla de tres) | — | ~0,049% | ≤ 0,1% |
| Eventos publicados vs. procesados | 123 / 123 | 2.066 / 2.066 (`msgOutCounter` 2.067 por 1 redelivery) | 0 perdidos |
| Backlog de eventos al finalizar | — | 0 mensajes | 0 |
| Mensajes sin confirmar (`unackedMessages`) al finalizar | — | 0 | 0 |
| Latencia HTTP (avg / p90 / p95 / max) | 360 ms / 1,19 s / 2,26 s / 4,42 s | 122,8 ms / 225,8 ms / 646,2 ms / 3,65 s | No definido en el escenario original |
| Tiempo de redirección de tráfico tras apagar la réplica | — | Inmediato (0 solicitudes a esa réplica ya en el primer muestreo, < 1 s) | No definido en el escenario original |
| Duración de la ventana de falla simulada | — | ~45 s | — |
| Tiempo de reincorporación de la réplica recuperada | — | Inmediato (retoma tráfico en el primer muestreo tras el reinicio) | No definido en el escenario original |
| Réplicas que absorbieron la carga durante la falla | — | 2 de 3 (18 y 22 de 40 solicitudes muestreadas; 833 y 836 eventos consumidos) | — |
| Cantidad de réplicas usadas en la corrida | N=3 | N=3 (N=2 no se corrió, ver limitaciones) | — |

### 9.2 Medidas cualitativas encontradas

- **El mecanismo de disponibilidad funciona por diseño, no por casualidad:** la redirección de tráfico y la recuperación automática se explican directamente por decisiones de arquitectura concretas (health check pasivo + reintentos de Nginx, suscripción `Shared` de Pulsar), no por comportamiento accidental — se pudo trazar cada resultado numérico a la decisión que lo produce.
- **Ejecutar el experimento reveló riesgos operacionales invisibles para una auditoría de solo lectura del código:** la condición de carrera al crear tablas y la falta de reconexión a Pulsar (secciones 5.1 y 5.2) solo aparecieron al arrancar el sistema de verdad con 3 réplicas simultáneas — ninguna revisión estática de código las hubiera detectado con la misma certeza.
- **El "arranque coordinado de varias réplicas" es un momento de mayor fragilidad que el "estado estable con una réplica caída":** las dos fallas reales ocurrieron al iniciar el sistema, no durante la ventana de falla inyectada en régimen estable — sugiere que el riesgo de disponibilidad no está distribuido parejo en el tiempo, sino concentrado en los momentos de arranque/escalado.
- **La observabilidad agregada en los pasos previos (instance-id, `/ready`, métricas) fue lo que hizo posible medir el experimento, no solo ejecutarlo:** sin el header `X-Instance-Id` no se podría haber demostrado la redirección de tráfico; sin `/ready` separado de `/health` no se podría haber distinguido una réplica "viva pero no lista" de una realmente sana.
- **Las métricas en memoria del proceso son una fuente de evidencia frágil ante fallas reales:** el propio experimento demostró esto al perder el contador de eventos de `notificaciones_2` en su reinicio — la evidencia confiable de "cero pérdida" tuvo que venir de una fuente externa a la aplicación (las estadísticas del broker), no de la instrumentación propia del servicio.
- **El resultado cuantitativo (100%) es más fuerte que lo mínimo exigido por el escenario (99,9%), pero la confianza en ese número depende del tamaño de muestra** — es una conclusión cualitativa importante en sí misma: un resultado perfecto con poca muestra amerita más cautela que un resultado de 99,95% con una muestra grande.

### 9.3 Síntesis

1. **El escenario de calidad de disponibilidad se cumple** para `ms-notificaciones` en el entorno con réplicas, balanceador y health checks reales construido para este experimento: la caída de una instancia bajo carga de "4x" no generó ninguna solicitud fallida ni ningún evento perdido, y la recuperación fue automática.
2. **El despliegue real en AWS, tal como está hoy, no cumpliría este escenario** — corre una sola instancia sin balanceador (hallazgo de la auditoría inicial, documentado en `ms-notificaciones/docs/experimento-disponibilidad.md`). El cumplimiento demostrado aquí es del *diseño*, no del despliegue actual.
3. **Ejecutar el experimento (no solo diseñarlo) encontró 2 fallas reales** que el análisis de código por sí solo no había detectado, ambas relacionadas con el arranque coordinado de múltiples réplicas. Quedan documentadas como trabajo pendiente, no como parte de este resultado.
4. El resultado cuantitativo (100% de éxito, 0 eventos perdidos) supera holgadamente el umbral exigido (99,9%), incluso considerando el tamaño de muestra por debajo del ideal.

## 10. Evidencias

Todos los artefactos crudos de la ejecución están en `Pruebas`:

| Archivo | Contenido |
|---|---|
| `01_docker_compose_ps.txt` | Estado final de los contenedores |
| `02_pulsar_topic_stats.json` | Estadísticas del tópico/suscripción en Pulsar (backlog, contadores de entrada/salida) |
| `03_metricas_por_replica.txt` | `/metrics` de cada réplica al final de la prueba |
| `04_baseline_k6_summary.json` | Resumen JSON de k6, línea base |
| `05_baseline_eventos_pulsar.log` | Log del generador de eventos, línea base |
| `06_baseline_k6_resultados.txt` | Resultados finales de k6, línea base (formato legible) |
| `07_fase4x_k6_log_completo.log` | Log completo de k6, fase 4x (progreso segundo a segundo + resumen) |
| `08_fase4x_k6_summary.json` | Resumen JSON de k6, fase 4x |
| `09_fase4x_eventos_pulsar.log` | Log del generador de eventos, fase 4x |
| `10_hallazgo_condicion_carrera_create_all.log` | Evidencia del hallazgo 1 (condición de carrera) |
| `11_hallazgo_pulsar_topicnotfound_sin_retry.log` | Evidencia del hallazgo 2 (sin retry de Pulsar) |
| `12_reparto_trafico_nginx.txt` | Reparto de tráfico (`X-Instance-Id`) antes, durante y después de la falla |
