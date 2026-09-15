# Microservicio Generador de Cotización — Hogar de los Alpes

Prueba de concepto del contexto acotado **Generador de Cotización**, implementado con **arquitectura hexagonal** (puertos y adaptadores): dominio aislado, comandos/eventos, patrón Outbox, CRUD simple sobre cotizaciones, e integración event-driven con **Apache Pulsar**.

---

## 1. Stack Tecnológico

- **Python 3.11+**
- **FastAPI** — API REST
- **Uvicorn** — servidor ASGI
- **Pydantic v2** — validación y serialización
- **SQLAlchemy 2.x** — ORM y acceso a datos
- **PostgreSQL** — base de datos
- **Apache Pulsar** (`pulsar-client`) — mensajería

---

## 2. Instalación y Ejecución

Este microservicio se ejecuta como parte del stack completo definido en el `docker-compose.yml` de la raíz del repositorio, que también levanta Pulsar y PostgreSQL compartidos con `ms-marketplace-asignacion` y `ms-verificacion-acreditacion`.

```bash
# Desde la raíz del repositorio
docker compose up -d --build pulsar pulsar-init postgres cotizacion
```

- API base: `http://localhost:8002`
- Swagger: `http://localhost:8002/docs`
- Healthcheck: `curl http://localhost:8002/health`

### 2.1. Ejecución local sin Docker (para desarrollo)

```bash
cd generador_cotizacion
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export DATABASE_URL="postgresql://hogar:alpes@localhost:5432/cotizacion_db"
export PULSAR_SERVICE_URL="pulsar://localhost:6650"
uvicorn generador_cotizacion.main:app --reload --port 8002
```

Requiere que Postgres y Pulsar de la raíz ya estén corriendo (`docker compose up -d pulsar pulsar-init postgres`).

### 2.2. Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://hogar:alpes@localhost:5432/cotizacion_db` | Conexión a Postgres |
| `PULSAR_SERVICE_URL` | `pulsar://localhost:6650` | Broker Pulsar |
| `PULSAR_SUBSCRIPTION` | `cotizacion-sub` | Nombre de la suscripción del consumer |
| `PULSAR_CONSUMER_TOPICS` | `persistent://hogar/alpes/cotizaciones.comandos` | Tópico de comandos entrantes |
| `PULSAR_PRODUCER_TOPIC` | `persistent://hogar/alpes/cotizaciones.eventos` | Tópico donde se publican los eventos propios |
| `PULSAR_DLQ_TOPIC` | `persistent://hogar/alpes/dlq` | Dead Letter Queue |
| `PULSAR_MAX_REDELIVER_COUNT` | `5` | Reintentos antes de mover un mensaje a la DLQ |

Las tablas (`cotizaciones`, `outbox`, `idempotency_keys`) se crean automáticamente al iniciar la aplicación.

---

## 3. Modelo de dominio

### Cotización

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador de la cotización |
| `trabajo_id` | UUID | Referencia al `Trabajo` solicitado en `marketplace-asignacion` (integración por id, no FK física) |
| `proveedor_id` | UUID (opcional) | Proveedor que emite la cotización. `null` mientras está pendiente de asignar |
| `monto` | float (opcional) | Valor cotizado. `null` mientras está pendiente de cotizar |
| `moneda` | str | Moneda (default `COP`) |
| `descripcion` | str | Detalle de lo cotizado |
| `estado` | Enum | `SOLICITADA` \| `ENVIADA` \| `ACEPTADA` \| `RECHAZADA` |
| `fecha_solicitud` | datetime | Fecha de creación |
| `fecha_validez` | datetime (opcional) | Vigencia de la cotización |

`proveedor_id` y `monto` son opcionales porque una cotización puede originarse de dos formas (ver sección 4): con proveedor y monto conocidos desde el inicio (flujo HTTP), o generada automáticamente a partir de un trabajo publicado, pendiente de que un proveedor la complete (flujo Pulsar).

---

## 4. Comandos y eventos de dominio

| Origen | Comando de aplicación | Efecto |
|---|---|---|
| HTTP `POST /cotizaciones/solicitar` | `SolicitarCotizacion` | Crea la cotización con proveedor y monto conocidos |
| Mensaje Pulsar `GenerarCotizacionCommand` | `GenerarCotizacion` | Crea la cotización sin proveedor/monto (pendiente) |

Ambos flujos comparten el mismo aggregate (`Cotizacion.solicitar(...)`) y emiten el evento de dominio **`CotizacionSolicitada`**, persistido en la tabla `outbox` dentro de la misma transacción (patrón Outbox).

El resto de operaciones CRUD (consultar, listar, actualizar, eliminar) son inserciones/actualizaciones simples sin lógica de negocio adicional. `PUT /cotizaciones/{id}` es, en particular, el mecanismo para que un proveedor complete una cotización generada automáticamente (asignándole `proveedor_id` y `monto`).

---

## 5. Integración con Apache Pulsar

### 5.1. Consumo: `GenerarCotizacionCommand`

El microservicio se suscribe a `persistent://hogar/alpes/cotizaciones.comandos` (tópico publicado por `marketplace-asignacion` cuando un trabajo es publicado). Contrato del mensaje:

```json
{
  "messageId": "uuid",
  "messageType": "GenerarCotizacionCommand",
  "version": 1,
  "occurredAt": "2024-06-01T10:00:00Z",
  "correlationId": "corr-123",
  "causationId": null,
  "idempotencyKey": "idem-456",
  "producer": "marketplace-asignacion",
  "payload": {
    "trabajo_id": "t1-t1-t1",
    "cliente_id": "c1-c1-c1",
    "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
    "alcance": {"descripcion": "Pintura", "categoria": "Pintura", "notas": null}
  }
}
```

De este payload solo se usan `trabajo_id` y `alcance.descripcion` (la cotización no duplica datos del trabajo que pertenecen al bounded context de Marketplace y Asignación: `cliente_id` y `ubicacion` se descartan). Mensajes con `messageType` distinto de `GenerarCotizacionCommand` se ignoran con un log de advertencia.

Procesamiento (`interfaces/messaging/consumer.py`):
1. Se resuelve una clave de idempotencia (`idempotencyKey` del mensaje, o un hash calculado si no viene) y se verifica contra la tabla `idempotency_keys` — si ya se procesó, se hace *ack* sin duplicar efectos.
2. Se ejecuta `GenerarCotizacion` dentro de una transacción (Unit of Work + Outbox).
3. Si el procesamiento falla, el mensaje se responde con *negative acknowledge*; tras `PULSAR_MAX_REDELIVER_COUNT` reintentos se mueve automáticamente a la DLQ (`persistent://hogar/alpes/dlq`), configurada como Dead Letter Policy del consumer.

### 5.2. Producción: `CotizacionSolicitada`

Un hilo en background (`main.py::_start_outbox_relay`) revisa la tabla `outbox` cada 3 segundos y publica los eventos pendientes a `persistent://hogar/alpes/cotizaciones.eventos`, marcándolos como procesados. El consumer de comandos corre en otro hilo en background (`main.py::_start_consumer_with_retry`), con reintentos de conexión si Pulsar no está disponible al arrancar.

---

## 6. Endpoints HTTP

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Verifica estado del servicio y conexión a DB |
| POST | `/cotizaciones/solicitar` | Crea una cotización con proveedor y monto conocidos; emite `CotizacionSolicitada` |
| GET | `/cotizaciones/{id}` | Consulta una cotización |
| GET | `/cotizaciones?trabajo_id=...` | Lista cotizaciones, opcionalmente filtradas por trabajo |
| PUT | `/cotizaciones/{id}` | Actualiza proveedor, monto, descripción, estado o vigencia |
| DELETE | `/cotizaciones/{id}` | Elimina una cotización |

---

## 7. Ejemplo de uso

```bash
# Solicitar cotización con proveedor y monto conocidos (HTTP)
curl -s -X POST http://localhost:8002/cotizaciones/solicitar \
  -H "Content-Type: application/json" \
  -d '{
    "trabajo_id": "11111111-1111-1111-1111-111111111111",
    "proveedor_id": "22222222-2222-2222-2222-222222222222",
    "monto": 150000,
    "descripcion": "Cotización de pintura"
  }' | jq

# Publicar manualmente un GenerarCotizacionCommand de prueba (simula a marketplace-asignacion)
docker exec hogar_alpes_pulsar bin/pulsar-client produce \
  persistent://hogar/alpes/cotizaciones.comandos \
  -m '{"messageId":"m1","messageType":"GenerarCotizacionCommand","version":1,"occurredAt":"2024-06-01T10:00:00Z","correlationId":"corr-123","causationId":null,"idempotencyKey":"idem-456","producer":"marketplace-asignacion","payload":{"trabajo_id":"11111111-1111-1111-1111-111111111111","cliente_id":"c1","ubicacion":{"direccion":"Calle 1","ciudad":"Bogotá","pais":"CO"},"alcance":{"descripcion":"Pintura","categoria":"Pintura","notas":null}}}'

# Listar cotizaciones de un trabajo (deberían aparecer ambas)
curl -s "http://localhost:8002/cotizaciones?trabajo_id=11111111-1111-1111-1111-111111111111" | jq

# Completar la cotización generada por Pulsar con proveedor y monto
curl -s -X PUT http://localhost:8002/cotizaciones/{cotizacion_id} \
  -H "Content-Type: application/json" \
  -d '{"proveedor_id": "33333333-3333-3333-3333-333333333333", "monto": 175000}' | jq

# Eliminar
curl -s -X DELETE http://localhost:8002/cotizaciones/{cotizacion_id} -w "\nHTTP_CODE: %{http_code}\n"
```
