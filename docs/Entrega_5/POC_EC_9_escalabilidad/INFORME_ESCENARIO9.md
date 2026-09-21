# Informe: Escenario de Calidad #4 - Disponibilidad ante falla externa

## 1. Objetivo

Demostrar el cumplimiento del **Escenario de Calidad #4**: el microservicio **Marketplace y Asignación** sigue disponible y aceptando solicitudes aun cuando el servicio externo de **Verificación y Acreditación** falle o esté inaccesible.

El desacoplamiento mediante **comunicación asíncrona con Apache Pulsar** permite que los mensajes se encolen mientras la dependencia externa se recupera, garantizando la disponibilidad del flujo de publicación y selección de proveedores.

## 2. Arquitectura y servicios involucrados

| Servicio | Puerto | Rol en el escenario |
|----------|--------|---------------------|
| ms-marketplace-asignacion | 8000 | Expone la API de trabajos y usa un adapter local (`AcreditacionPort`) para validar proveedores sin depender de verificación. |
| ms-verificacion-acreditacion | 8001 | Servicio externo simulado. Consume comandos de Pulsar para verificar y acreditar proveedores. |
| Apache Pulsar | 6650 / 8080 | Broker de mensajería que desacopla marketplace de verificación. |

## 3. Hipótesis

Si el servicio de Verificación y Acreditación cae, Marketplace debe seguir respondiendo con éxito a:

1. `POST /trabajos/solicitar` (crear trabajo)
2. `POST /trabajos/{id}/publicar` (publicar trabajo)
3. `POST /trabajos/{id}/seleccionar-proveedor` (seleccionar proveedor)

Cuando Verificación vuelva a estar disponible, debe consumir los mensajes pendientes en el tópico `verificacion.comandos` y completar la verificación/acreditación del proveedor.

## 4. Procedimiento ejecutado

Se ejecutó la colección de Postman `postman/HogarAlpes_Escenario4.postman_collection.json` paso a paso. A continuación se detalla el flujo realizado con los comandos `curl` equivalentes y los resultados obtenidos.

### 4.1 Preparación: healthchecks

Se verificó que todos los servicios estuvieran healthy antes de iniciar.

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8001/health
```

**Resultado:**

```json
{ "status": "ok", "service": "marketplace-asignacion" }
{ "status": "ok", "service": "verificacion-acreditacion" }
```

### 4.2 Flujo base con verificación activa

Se creó un trabajo, se publicó, se acreditó un proveedor y se seleccionó para confirmar el comportamiento normal del sistema.

| Paso | Request | HTTP | Estado |
|------|---------|------|--------|
| Crear trabajo | `POST /trabajos/solicitar` | 201 | `SOLICITADO` |
| Publicar trabajo | `POST /trabajos/{id}/publicar` | 200 | `PUBLICADO` |
| Acreditar proveedor | `POST /debug/acreditar-proveedor` | 200 | acreditado localmente |
| Seleccionar proveedor | `POST /trabajos/{id}/seleccionar-proveedor` | 200 | `PROVEEDOR_SELECCIONADO` |

IDs generados (flujo base):

```text
trabajo_id: ce23b382-2903-4153-bec1-924dd0d30476
proveedor_id: a49f51d5-1c96-40fb-87d5-b71a023332eb
```

### 4.3 Simulación de falla externa

Se detuvo el contenedor de verificación para simular la caída del servicio externo:

```bash
docker compose stop verificacion
```

Se confirmó que el servicio dejó de estar disponible:

```text
NAME                     SERVICE       STATE
hogar_alpes_verificacion verificacion  stopped
```

### 4.4 Flujo durante la falla

Con verificación caída, se ejecutó un nuevo flujo completo en Marketplace:

| Paso | Request | HTTP | Estado / Observación |
|------|---------|------|----------------------|
| Crear trabajo durante falla | `POST /trabajos/solicitar` | **201** | `SOLICITADO` — Marketplace sigue respondiendo. |
| Publicar trabajo durante falla | `POST /trabajos/{id}/publicar` | **200** | `PUBLICADO` — sin errores. |
| Acreditar proveedor durante falla | `POST /debug/acreditar-proveedor` | **200** | Validación local en Marketplace. |
| Seleccionar proveedor durante falla | `POST /trabajos/{id}/seleccionar-proveedor` | **200** | `PROVEEDOR_SELECCIONADO` — adapter local funciona. |

IDs generados (flujo de falla):

```text
trabajo_id_falla: 96a2f8ca-7137-49c3-bb56-ea2d1eaf4311
proveedor_id_falla: f61d5ab6-cb75-47ba-9b33-795612f82f5b
```

### 4.5 Evidencia de mensaje pendiente en Pulsar

Mientras verificación estaba caída, se consultó el tópico `verificacion.comandos`:

```bash
docker exec hogar_alpes_pulsar bin/pulsar-admin topics stats persistent://hogar/alpes/verificacion.comandos
```

Valores relevantes extraídos:

```text
msgInCounter: 13
subscriptions.verificacion-sub.msgBacklog: 1
subscriptions.verificacion-sub.consumers: []
```

Esto demuestra que:

- El mensaje fue publicado en Pulsar.
- Hay un mensaje en backlog pendiente de consumo.
- No hay consumidores activos porque verificación está caído.

### 4.6 Recuperación del servicio externo

Se levantó el servicio de verificación:

```bash
docker compose start verificacion
```

Después de ~15 segundos, verificación volvió a estar healthy:

```json
{ "status": "ok", "service": "verificacion-acreditacion" }
```

Se verificó que el backlog se consumió:

```text
subscriptions.verificacion-sub.msgBacklog: 0
subscriptions.verificacion-sub.consumers: 1
```

Y el estado final del proveedor quedó:

```json
{
  "proveedor_id": "f61d5ab6-cb75-47ba-9b33-795612f82f5b",
  "estado_verificacion": "APROBADA",
  "estado_acreditacion": "ACREDITADO"
}
```

### 4.7 Idempotencia

Se reenviaron las peticiones iniciales con la misma `idempotency_key` para verificar que no se duplican efectos:

| Paso | Request | HTTP | Observación |
|------|---------|------|-------------|
| Reenviar crear trabajo | `POST /trabajos/solicitar` | 200 | Mismo `trabajo_id`, estado `SOLICITADO`. |
| Reenviar seleccionar proveedor | `POST /trabajos/{id}/seleccionar-proveedor` | 200 | Mismo proveedor seleccionado, sin duplicados. |

## 5. Evidencia de logs

Se guardaron los logs de los servicios en:

| Archivo | Contenido |
|---------|-----------|
| `resultados/escenario4/marketplace_logs.txt` | Logs de Marketplace durante todo el experimento. |
| `resultados/escenario4/verificacion_logs.txt` | Logs de Verificación: apagado, reinicio y consumo del mensaje pendiente. |
| `resultados/escenario4/pulsar_logs.txt` | Logs del broker Pulsar. |

### 5.1 Marketplace publica eventos a Pulsar

```text
2026-09-21 04:26:21,113 INFO marketplace_asignacion.infrastructure.pulsar_producer Evento publicado a Pulsar
2026-09-21 04:26:21,135 INFO marketplace_asignacion.main Outbox publicado
```

### 5.2 Verificación se recupera y consume el mensaje

```text
2026-09-21 04:27:06,497 INFO verificacion_acreditacion.main Iniciando consumer Pulsar en background thread
2026-09-21 04:27:06,523 INFO verificacion_acreditacion.infrastructure.pulsar_consumer Pulsar consumer started
2026-09-21 04:27:06,525 INFO verificacion_acreditacion.interfaces.messaging.consumer Procesando mensaje entrante
2026-09-21 04:27:06,534 INFO verificacion_acreditacion.application.handlers Verificación procesada
2026-09-21 04:27:06,540 INFO verificacion_acreditacion.infrastructure.pulsar_consumer Mensaje procesado
```

### 5.3 Verificación acredita al proveedor

```text
2026-09-21 04:27:57,509 INFO verificacion_acreditacion.application.handlers Proveedor acreditado
INFO:     172.20.0.1:53240 - "POST /acreditaciones HTTP/1.1" 201 Created
```

## 6. Cumplimiento del escenario de calidad

| Requisito | Cómo se cumple | Evidencia |
|-----------|----------------|-----------|
| Marketplace disponible durante falla externa | Todos los requests a Marketplace respondieron 200/201 aunque verificación estuviera caída. | Logs de requests y respuestas en `resultados/escenario4/`. |
| Desacoplamiento por Pulsar | Los mensajes se encolaron en `verificacion.comandos` con backlog 1 y 0 consumidores. | Stats de Pulsar mostrando `msgBacklog: 1` y `consumers: []`. |
| Recuperación automática | Al levantar verificación, el consumer se reconectó y procesó el mensaje pendiente. | Logs de verificación y `msgBacklog: 0`. |
| Estado final consistente | El proveedor quedó `APROBADA` / `ACREDITADO`. | Estado final consultado vía API. |
| Idempotencia | Reenviar requests con la misma clave no duplicó trabajos ni selecciones. | Respuestas 200 con mismos IDs. |

## 7. Cómo reproducir

### 7.1 Levantar el entorno

```bash
docker compose up --build -d
```

### 7.2 Ejecutar el flujo base

```bash
# 1. Crear trabajo
curl -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"55555555-5555-5555-5555-555555555555","ubicacion":{"direccion":"Calle 10","ciudad":"Bogotá","pais":"CO"},"alcance":{"descripcion":"Pintura interior","categoria":"Pintura"}}'

# 2. Publicar trabajo
curl -X POST http://localhost:8000/trabajos/{trabajo_id}/publicar -H "Content-Type: application/json" -d '{}'

# 3. Acreditar proveedor
curl -X POST "http://localhost:8000/debug/acreditar-proveedor?proveedor_id={proveedor_id}"

# 4. Seleccionar proveedor
curl -X POST http://localhost:8000/trabajos/{trabajo_id}/seleccionar-proveedor \
  -H "Content-Type: application/json" \
  -d '{"proveedor_id":"{proveedor_id}"}'
```

### 7.3 Simular la falla y ejecutar el flujo durante la caída

```bash
# Detener verificación
docker compose stop verificacion

# Repetir los pasos 1-4 con IDs diferentes. Marketplace debe seguir respondiendo 200/201.

# Verificar mensaje pendiente en Pulsar
docker exec hogar_alpes_pulsar bin/pulsar-admin topics stats persistent://hogar/alpes/verificacion.comandos
```

### 7.4 Recuperación

```bash
# Levantar verificación
docker compose start verificacion

# Esperar ~15 segundos y consultar estado del proveedor
curl http://localhost:8001/proveedores/{proveedor_id}/estado
```

## 8. Observaciones

1. **Fake External Validation**: el adaptador externo simulado en `ms-verificacion-acreditacion` aprueba automáticamente la verificación al procesar el mensaje. Por eso el estado final del proveedor fue `APROBADA` en lugar de `PENDIENTE`. Esto no afecta el objetivo del escenario (disponibilidad), pero sí explica la diferencia con el valor esperado en la colección Postman.

2. **Endpoint de DLQ**: el endpoint `/admin/dlq` de Marketplace retornó `count: 0`, confirmando que los mensajes no se perdieron ni fueron a la cola de mensajes muertos.

3. **Idempotencia**: el uso de `idempotency_key` garantiza que reintentos no generen duplicados, lo cual es crítico cuando la dependencia externa se recupera y los mensajes pueden re-procesarse.

## 9. Conclusión

El Escenario de Calidad #4 se cumple satisfactoriamente:

- **Marketplace permanece disponible** aun cuando el servicio de Verificación y Acreditación está caído.
- **Pulsar actúa como buffer** de mensajes, permitiendo que la dependencia externa se recupere sin pérdida de información.
- **La recuperación es automática**: al reiniciar verificación, el consumer procesa el mensaje pendiente y completa la acreditación.
- **La idempotencia evita duplicados** en caso de reintentos o re-procesamiento.

## 10. Anexo: archivos de evidencia

| Archivo | Descripción |
|---------|-------------|
| `resultados/escenario4/ids_base.txt` | IDs del flujo base. |
| `resultados/escenario4/ids_falla.txt` | IDs del flujo durante la falla. |
| `resultados/escenario4/marketplace_logs.txt` | Logs completos de Marketplace. |
| `resultados/escenario4/verificacion_logs.txt` | Logs completos de Verificación. |
| `resultados/escenario4/pulsar_logs.txt` | Logs del broker Pulsar. |
| `postman/HogarAlpes_Escenario4.postman_collection.json` | Colección de Postman usada. |
| `postman/README_Escenario4_Postman.md` | Guía de ejecución del escenario. |
