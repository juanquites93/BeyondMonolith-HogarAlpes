# Microservicio Notificaciones — Hogar de los Alpes

Microservicio del contexto acotado **Notificaciones**, diseñado e implementado con **Domain-Driven Design (DDD)** y **Event-Driven Architecture (EDA)** sobre Python, FastAPI y SQLAlchemy.

Se encarga de avisar a proveedores y clientes cuando ocurren eventos relevantes del marketplace (por ahora, la asignación de un proveedor a un trabajo).

---

## 1. Stack Tecnológico

- **Python 3.11+**
- **FastAPI** — API REST de alto rendimiento
- **Uvicorn** — servidor ASGI
- **Pydantic v2** — validación y serialización
- **SQLAlchemy 2.x** — ORM y acceso a datos
- **PostgreSQL** (producción) / **SQLite** (demo local)
- **Apache Pulsar** — cluster compartido por el equipo (este servicio solo actúa como cliente)
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
cd ms-notificaciones

# 2. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias en modo editable
pip install -e .
```

### 3.2. Ejecución Local (SQLite por defecto)

```bash
uvicorn ms-notificaciones.main:app --reload --port 8001
```

Accede a:
- API base: `http://127.0.0.1:8001`
- Documentación interactiva (Swagger): `http://127.0.0.1:8001/docs`
- Healthcheck: `curl http://127.0.0.1:8001/health`

### 3.3. Ejecución con PostgreSQL

```bash
export DATABASE_URL="postgresql://usuario:password@localhost:5432/notificaciones"
uvicorn ms-notificaciones.main:app --port 8001
```

### 3.4. Ejecución conectada al cluster de Pulsar

```bash
export PULSAR_SERVICE_URL="pulsar://localhost:6650"
uvicorn ms-notificaciones.main:app --port 8001
```

### 3.5. Verificar que funciona

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```

Respuesta esperada:
```json
{
  "status": "ok",
  "service": "ms-notificaciones"
}
```

---

## 4. Contrato de Mensajería

Este servicio consume comandos de un único tópico de Pulsar y no expone endpoints de escritura por HTTP: el único camino síncrono es la consulta (`GET`), toda intención de notificar entra por el broker.

**Tópico a consumir:** `persistent://hogar/alpes/notificaciones.comandos`

Los mensajes viajan como JSON con un sobre genérico (`messageId`, `messageType`, `version`, `occurredAt`, `correlationId`, `idempotencyKey`, `producer`, `payload`). `messageType` distingue entre los comandos que llegan por ese tópico:

| `messageType` | Quién se notifica | Payload |
|---|---|---|
| `NotificarProveedorAsignadoCommand` | El proveedor: le asignaron un trabajo | `proveedor_id`, `trabajo_id`, `cliente_id`, `detalles_trabajo.{descripcion, categoria, ubicacion.{direccion, ciudad}}` |
| `NotificarClienteProveedorAsignadoCommand` | El cliente: ya tiene proveedor asignado | `cliente_id`, `trabajo_id`, `proveedor_id` |

Ninguno de los dos trae el contacto real (email/teléfono) del destinatario, solo su id: mientras el equipo defina cómo resolverlo, se usa un contacto de ejemplo derivado del id (`{id}@hogaralpes.demo`), solo para poder demostrar el flujo completo.

`idempotencyKey` evita procesar dos veces el mismo comando si el broker lo reentrega (tabla `idempotency_keys`).

---

## 5. Arquitectura

```
domain/          Agregado Notificacion, eventos de dominio, value objects, puerto de repositorio
application/     Comandos, manejadores (orquestan dominio + repositorio + outbox)
infrastructure/  SQLAlchemy (ORM, repositorio, outbox, idempotencia), pasarela simulada,
                 consumidor y publicador de Pulsar
interfaces/      FastAPI (health, consulta de una notificación)
```

Misma arquitectura que `marketplace_asignacion`: agregado con eventos de dominio, patrón **Outbox** transaccional (el hecho y el evento de integración se escriben en la misma transacción) y **tabla de idempotencia** para tolerar reintentos del broker sin duplicar efectos.

---

## 6. Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Verifica estado del servicio y conexión a DB |
| GET | `/notificaciones/{id}` | Consulta el estado de una notificación |

---

## 7. Probar el Flujo sin un Cluster de Pulsar Desplegado

Con el servicio levantado (`PULSAR_SERVICE_URL` vacío), se puede alimentar el mismo procesamiento que usaría el consumidor real, directamente en Python:

```python
import json
from notificaciones.infrastructure.pulsar_consumidor import procesar_mensaje

mensaje = {
    "messageId": "uuid",
    "messageType": "NotificarProveedorAsignadoCommand",
    "version": 1,
    "occurredAt": "2024-06-01T11:00:00Z",
    "correlationId": "corr-456",
    "idempotencyKey": "idem-789",
    "producer": "marketplace-asignacion",
    "payload": {
        "proveedor_id": "p1-p1-p1",
        "trabajo_id": "t1-t1-t1",
        "cliente_id": "c1-c1-c1",
        "detalles_trabajo": {
            "descripcion": "Pintura",
            "categoria": "Pintura",
            "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá"},
        },
    },
}
procesar_mensaje(json.dumps(mensaje).encode())
```

**Resultado esperado:** la notificación queda en estado `ENVIADA` (o `FALLIDA` si la pasarela simulada rechaza el envío), el hecho queda registrado en la tabla `outbox`, y reenviar el mismo `messageId`/`idempotencyKey` no genera una segunda notificación.

Consultarla:

```bash
curl -s http://localhost:8001/notificaciones/{notificacion_id} | python3 -m json.tool
```
