# Microservicio Marketplace y Asignación — Hogar de los Alpes

Microservicio del contexto acotado **Marketplace y Asignación**, diseñado e implementado con **Domain-Driven Design (DDD)** y **Event-Driven Architecture (EDA)** sobre Python, FastAPI y SQLAlchemy.

---

## 1. Stack Tecnológico

- **Python 3.11+**
- **FastAPI** — API REST de alto rendimiento
- **Uvicorn** — servidor ASGI
- **Pydantic v2** — validación y serialización
- **SQLAlchemy 2.x** — ORM y acceso a datos
- **PostgreSQL** (producción) / **SQLite** (demo local)
- **pytest** — pruebas automatizadas

---

## 2. Requisitos Previos

- Python 3.11 o superior
- `pip` y `venv` disponibles

---

## 3. Instalación y Ejecución del Microservicio

### 3.1. Instalación

```bash
# 1. Ubicarse en la raíz del proyecto
cd marketplace_asignacion

# 2. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias en modo editable
pip install -e .
```

### 3.2. Ejecución Local (SQLite por defecto)

```bash
uvicorn marketplace_asignacion.main:app --reload --port 8000
```

Accede a:
- API base: `http://127.0.0.1:8000`
- Documentación interactiva (Swagger): `http://127.0.0.1:8000/docs`
- Healthcheck: `curl http://127.0.0.1:8000/health`

### 3.3. Ejecución con PostgreSQL

```bash
export DATABASE_URL="postgresql://usuario:password@localhost:5432/marketplace"
uvicorn marketplace_asignacion.main:app --port 8000
```

### 3.4. Verificar que funciona

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Respuesta esperada:
```json
{
  "status": "ok",
  "service": "marketplace-asignacion"
}
```

---

## 4. Tests

### 4.1. Ejecutar todos los tests

```bash
# Suite completa
pytest tests/ -v

# Solo dominio
pytest tests/test_domain.py -v

# Solo contrato de eventos
pytest tests/test_event_contracts.py -v

# Solo integración
pytest tests/test_integration.py -v
```

### 4.2. Qué hace cada test

#### `tests/test_domain.py` — Tests de invariantes del aggregate
Prueban las reglas de negocio puras del dominio, sin depender de base de datos ni API.

| Test | Qué verifica | Escenario relacionado |
|------|--------------|----------------------|
| `test_solicitar_trabajo_genera_evento_y_cambia_estado` | Un trabajo en `BORRADOR` puede pasar a `SOLICITADO` y emite `TrabajoSolicitado` | Flujo normal de creación |
| `test_publicar_sin_solicitar_falla` | No se permite publicar un trabajo que no esté `SOLICITADO` | Protección de invariante de estado |
| `test_publicar_tras_solicitar_cambia_estado` | Tras `SOLICITADO`, publicar cambia a `PUBLICADO` y emite `TrabajoPublicado` | Transición válida de publicación |
| `test_seleccionar_proveedor_sin_publicar_falla` | No se permite seleccionar proveedor si no está `PUBLICADO` | Protección de invariante de estado |
| `test_seleccionar_proveedor_no_acreditado_falla` | Lanza `ProveedorNoAcreditadoError` si el proveedor no está acreditado | Regla de negocio de acreditación |
| `test_seleccionar_proveedor_acreditado_exitoso` | Si está acreditado, pasa a `PROVEEDOR_SELECCIONADO` y emite `ProveedorSeleccionado` | Flujo normal de asignación |

#### `tests/test_event_contracts.py` — Tests de contrato de eventos
Verifican que los eventos de dominio tengan la estructura, campos y versionado esperados.

| Test | Qué verifica | Escenario relacionado |
|------|--------------|----------------------|
| `test_evento_trabajo_solicitado_payload` | `TrabajoSolicitado` tiene `trabajo_id`, `cliente_id`, `ubicacion`, `alcance`, `correlation_id` y metadata base (`event_id`, `version`, `occurred_at`) | Contrato de integración del evento |
| `test_evento_trabajo_publicado_payload` | `TrabajoPublicado` tiene `trabajo_id`, `cliente_id`, `publicado_en` y metadata base | Contrato de integración del evento |
| `test_evento_proveedor_seleccionado_payload` | `ProveedorSeleccionado` tiene `trabajo_id`, `proveedor_id`, `seleccionado_en` y metadata base | Contrato de integración del evento |

#### `tests/test_integration.py` — Tests de integración (API + DB + Outbox + Idempotencia)
Prueban el microservicio completo levantado vía `TestClient`, incluyendo persistencia, emisión de eventos y comportamiento de idempotencia.

| Test | Qué verifica | Escenario relacionado |
|------|--------------|----------------------|
| `test_solicitar_trabajo_persiste_y_genera_outbox` | El endpoint `POST /trabajos/solicitar` persiste el trabajo en SQLite y genera una fila en la tabla `outbox` con `event_type = TrabajoSolicitado` | DISP-01, CE-01 |
| `test_publicar_trabajo_transiciona_estado` | El endpoint `POST /trabajos/{id}/publicar` cambia el estado a `PUBLICADO` y genera `TrabajoPublicado` en outbox | DISP-01, CE-01 |
| `test_seleccionar_proveedor_valida_acreditacion` | Sin acreditar devuelve HTTP 409; acreditando devuelve 200 y estado `PROVEEDOR_SELECCIONADO` | DISP-02 (aislamiento de fallos) |
| `test_idempotencia_solicitar_trabajo` | Enviar el mismo `idempotency_key` dos veces devuelve HTTP 201 la primera y HTTP 200 (cacheado) la segunda, con el mismo `trabajo_id` | DISP-01 (idempotencia) |

---

## 5. Cómo Probar los Escenarios de Calidad con el Microservicio Levantado

A continuación se presentan comandos `curl` para validar manualmente cada escenario de calidad documentado en `PLANTILLA_ENTREGA_3.pdf`. Antes de ejecutarlos, asegúrate de tener el servicio corriendo:

```bash
uvicorn marketplace_asignacion.main:app --port 8000
```

### 5.1. Disponibilidad (DISP)

#### DISP-01 — Outbox como buffer ante caída del broker
En el MVP el "broker" es un publisher simulado que lee de la tabla `outbox`. Para demostrar que el sistema sigue funcionando sin broker real:

```bash
# 1. Crear un trabajo (esto persiste en DB y en outbox)
curl -s -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": "11111111-1111-1111-1111-111111111111",
    "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
    "alcance": {"descripcion": "Pintura", "categoria": "Pintura"}
  }' | jq
```

**Resultado esperado:** HTTP 201 y `estado: SOLICITADO`. El evento quedó en la tabla `outbox` aunque no haya broker externo. La operación del usuario **no se detuvo**.

#### DISP-02 — Aislamiento de fallos (proveedor no acreditado)
```bash
# 2. Publicar el trabajo creado (reemplaza {trabajo_id} por el UUID retornado)
curl -s -X POST http://localhost:8000/trabajos/{trabajo_id}/publicar \
  -H "Content-Type: application/json" \
  -d '{}' | jq

# 3. Intentar seleccionar un proveedor NO acreditado → debe fallar con 409
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST \
  http://localhost:8000/trabajos/{trabajo_id}/seleccionar-proveedor \
  -H "Content-Type: application/json" \
  -d '{"proveedor_id": "22222222-2222-2222-2222-222222222222"}'
```

**Resultado esperado:** HTTP 409 con mensaje `El proveedor ... no está acreditado`. El error es **local y aislado**; no afecta otros trabajos ni el estado global.

#### DISP-03 — Idempotencia (retry seguro)
```bash
# 4. Enviar SolicitarTrabajo con idempotency_key
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "idempotency_key": "demo-idem-001",
    "cliente_id": "33333333-3333-3333-3333-333333333333",
    "ubicacion": {"direccion": "Av Reforma", "ciudad": "CDMX", "pais": "MX"},
    "alcance": {"descripcion": "Electricidad", "categoria": "Electricidad"}
  }'

# 5. Reenviar exactamente el mismo payload con la misma idempotency_key
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "idempotency_key": "demo-idem-001",
    "cliente_id": "33333333-3333-3333-3333-333333333333",
    "ubicacion": {"direccion": "Av Reforma", "ciudad": "CDMX", "pais": "MX"},
    "alcance": {"descripcion": "Electricidad", "categoria": "Electricidad"}
  }'
```

**Resultado esperado:** Primera vez HTTP 201. Segunda vez HTTP 200 con **el mismo `trabajo_id`**. No se creó duplicado.

---

### 5.2. Modificabilidad (MOD)

#### MOD-01 — Extensión por país sin tocar el core
Esta táctica se demuestra en el código, no con un solo `curl`. Sin embargo, puedes verificar que el dominio está desacoplado:

```bash
# Consultar un trabajo existente → la respuesta solo expone datos del dominio,
# no detalles de implementación de la base de datos
curl -s http://localhost:8000/trabajos/{trabajo_id} | jq
```

Observa que el JSON no expone columnas de SQLAlchemy ni IDs internos del ORM. El contrato (`TrabajoResponse`) es independiente del modelo de persistencia.

#### MOD-02 — Versionado de eventos en el outbox
```bash
# Consultar directamente la base de datos SQLite para ver la estructura versionada
sqlite3 marketplace_asignacion.db "SELECT event_type, version, payload FROM outbox LIMIT 5;"
```

**Resultado esperado:** Cada fila tiene `event_type`, `version = 1`, `payload` JSON con `correlation_id` y `occurred_at`. Esto permite que futuros consumidores ignoren campos nuevos (forward compatibility).

---

### 5.3. Escalabilidad (ESC)

#### ESC-01 — Latencia del front door bajo carga
Puedes simular carga con `ab` o `wrk`, o simplemente observar que el endpoint `solicitar` responde sin esperar al broker:

```bash
# Medir tiempo de respuesta de una solicitud
time curl -s -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": "44444444-4444-4444-4444-444444444444",
    "ubicacion": {"direccion": "Rua Augusta", "ciudad": "São Paulo", "pais": "BR"},
    "alcance": {"descripcion": "Hidráulica", "categoria": "Hidráulica"}
  }' > /dev/null
```

**Resultado esperado:** La respuesta HTTP 201 llega en **menos de 200 ms** porque solo escribe en DB local. La publicación al "broker" ocurre de forma asíncrona después del response.

#### ESC-02 — Fan-out desacoplado
Verifica que el publisher procesa eventos pendientes sin bloquear la API:

```bash
# 1. Crear varios trabajos
for i in {1..5}; do
  curl -s -X POST http://localhost:8000/trabajos/solicitar \
    -H "Content-Type: application/json" \
    -d "{\"cliente_id\": \"$(python3 -c 'import uuid; print(uuid.uuid4())')\", \"ubicacion\": {\"direccion\": \"Calle $i\", \"ciudad\": \"Bogotá\", \"pais\": \"CO\"}, \"alcance\": {\"descripcion\": \"Test $i\", \"categoria\": \"Test\"}}" > /dev/null
done

# 2. Consultar la tabla outbox: debe tener múltiples eventos pendientes (processed_at IS NULL)
sqlite3 marketplace_asignacion.db "SELECT COUNT(*) as pendientes FROM outbox WHERE processed_at IS NULL;"
```

**Resultado esperado:** Las solicitudes retornan inmediatamente; los eventos quedan en `outbox` para ser publicados por el relay. El proceso API no se bloquea.

---

### 5.4. Consistencia Eventual (CE)

#### CE-01 — Traza end-to-end con correlation_id
```bash
# Enviar un trabajo con correlation_id explícito
curl -s -X POST http://localhost:8000/trabajos/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "correlation_id": "trace-abc-123",
    "cliente_id": "55555555-5555-5555-5555-555555555555",
    "ubicacion": {"direccion": "Calle Final", "ciudad": "Buenos Aires", "pais": "AR"},
    "alcance": {"descripcion": "Gasfitería", "categoria": "Gasfitería"}
  }' | jq

# Verificar que el correlation_id se propagó al outbox
sqlite3 marketplace_asignacion.db "SELECT event_type, correlation_id FROM outbox WHERE correlation_id = 'trace-abc-123';"
```

**Resultado esperado:** El `correlation_id` aparece tanto en la respuesta HTTP como en la tabla `outbox`, permitiendo trazar el evento hasta consumidores externos.

---

## 6. Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Verifica estado del servicio y conexión a DB |
| POST | `/trabajos/solicitar` | Crea un trabajo en estado `SOLICITADO` |
| POST | `/trabajos/{id}/publicar` | Transiciona a `PUBLICADO` |
| POST | `/trabajos/{id}/seleccionar-proveedor` | Valida acreditación y transiciona a `PROVEEDOR_SELECCIONADO` |
| GET | `/trabajos/{id}` | Consulta estado y datos del trabajo |

---

## 7. Escenarios de Calidad que Cumple este Microservicio

El diseño arquitectónico favorece activamente los siguientes escenarios de calidad priorizados para **Hogar de los Alpes**. El atributo más crítico para este bounded context es la **Disponibilidad**, seguido de **Modificabilidad** y **Escalabilidad**.

> Ver detalle completo de fuente, estímulo, artefacto, entorno, respuesta y medida en el documento **`PLANTILLA_ENTREGA_3.pdf`**.

### 7.1. Disponibilidad (H/M) — Atributo Principal

**Escenario clave:** Una falla en la integración con un partner o en la publicación de eventos no debe detener la operación global del marketplace ni del flujo de siniestros.

**Tácticas aplicadas en el código:**
- **Patrón Outbox:** la escritura del estado del aggregate y la emisión de eventos ocurren en una única transacción de base de datos. Si el broker cae, los eventos quedan persistidos en la tabla `outbox` y se reintentan al recuperarse.
- **Idempotencia:** los comandos aceptan `idempotency_key`. Si un cliente reintenta por timeout parcial, el sistema devuelve el resultado cacheado (HTTP 200) sin crear duplicados.
- **Aislamiento de fallos:** un error en `SeleccionarProveedor` (ej. proveedor no acreditado) se traduce en HTTP 409 local. No propaga cascada a otros microservicios porque no hay transacciones distribuidas síncronas.
- **Healthcheck activo:** `/health` verifica conectividad a la base de datos, permitiendo que el orquestador retire réplicas enfermas automáticamente.

### 7.2. Modificabilidad (H/H)

**Escenario clave:** El negocio debe incorporar reglas de asignación distintas para México, Brasil y Argentina, además de nuevos partners B2B2C, sin detener el servicio global.

**Tácticas aplicadas en el código:**
- **Capas DDD estrictas:** el dominio (`domain/`) no depende de FastAPI ni de SQLAlchemy. Cambiar el framework web o la base de datos no afecta las reglas de negocio.
- **Anti-Corruption Layer:** `AcreditacionPort` desacopla la verificación de proveedores del servicio concreto. Se puede cambiar la implementación (HTTP, gRPC, caché Redis) sin tocar `AsignacionService`.
- **Eventos de integración versionados:** cada evento lleva `version`, `event_type` y `occurred_at`. Esto permite evolucionar el contrato sin romper consumidores existentes.
- **Bajo acoplamiento:** los comandos y eventos desacoplan al productor del consumidor. Agregar un nuevo consumidor no requiere modificar este microservicio.

### 7.3. Escalabilidad (H/H)

**Escenario clave:** Soportar 25M requests/día con picos de 4x y proyección a 36k trabajos/día sin degradar la latencia del front door de solicitudes.

**Tácticas aplicadas en el código:**
- **Patrón Outbox:** desacopla la escritura de la publicación de eventos. El publicador puede escalar independientemente (proceso background, CronJob o sidecar).
- **Aggregate pequeño:** `Trabajo` no mantiene bloqueos globales ni listas masivas en memoria. Facilita sharding por `cliente_id`, `pais` o rango de fechas.
- **FastAPI + Uvicorn:** servidor ASGI que aprovecha I/O no bloqueante para healthchecks, validaciones Pydantic y lecturas concurrentes.
- **Broker externo (diseñado):** al reemplazar el publisher simulado por Kafka o RabbitMQ, el fan-out de eventos no consume recursos del proceso API.

### 7.4. Consistencia Eventual (Escenario transversal)

**Escenario clave:** Los consumidores de eventos (pagos, notificaciones, analytics) deben reflejar el cambio de estado del trabajo sin requerir consistencia inmediata síncrona.

**Tácticas aplicadas en el código:**
- **Consistencia eventual por diseño:** el aggregate emite eventos de dominio que se almacenan en outbox y se publican de forma asíncrona. Los consumidores eventualmente reciben `TrabajoPublicado` o `ProveedorSeleccionado`.
- **Correlation ID:** cada comando y evento lleva `correlation_id`, lo que permite trazar el flujo end-to-end a través de múltiples microservicios.

---

## 8. Documentación Adicional

- **`IMPLEMENTACION.md`**: contiene el diseño DDD detallado, modelo de eventos, decisiones arquitectónicas, tradeoffs, riesgos, estructura de carpetas y próximos pasos.
- **`PLANTILLA_ENTREGA_3.pdf`**: plantilla de escenarios de calidad arquitectónica con fuente, estímulo, artefacto, entorno, respuesta y medida para Disponibilidad, Modificabilidad y Escalabilidad.
- **`/docs` (Swagger UI)**: disponible automáticamente al levantar el servicio en `http://localhost:8000/docs`.

---

## 9. Licencia y Autoría

Proyecto académico desarrollado como parte de la materia de Arquitectura de Software — Universidad de los Andes.  
Uso educativo y demostrativo.
