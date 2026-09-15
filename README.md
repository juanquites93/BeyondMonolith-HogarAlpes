# Hogar de los Alpes

## 1. Descripción general

**Hogar de los Alpes** es una plataforma de servicios domésticos que conecta clientes con proveedores de mantenimiento y reparación del hogar. El proyecto sigue una arquitectura de microservicios desacoplados, comunicación asincrónica por eventos y principios de Domain-Driven Design (DDD).

### Microservicios incluidos en esta entrega



1. **`ms-marketplace-asignacion`**: Gestiona el ciclo de vida de los trabajos (solicitud, publicación y selección de proveedores) y emite eventos de integración hacia otros sistemas.
2. **`ms-verificacion-acreditacion`**: Valida si un proveedor cumple las condiciones para ser acreditado y habilitado para la asignación de trabajos.
3. **Generador de Cotizaciones**: Recibe `GenerarCotizacionCommand` por Pulsar cuando un trabajo es publicado.
4. **Notificaciones y Comunicaciones**: Recibe comandos de notificación por Pulsar cuando se selecciona un proveedor.



---

## 2. Arquitectura resumida

| Principio | Implementación |
|-----------|----------------|
| **DDD (Domain-Driven Design)** | Entidades, objetos valor, eventos de dominio, lenguaje ubicuo (`Trabajo`, `Proveedor`, `Acreditación`, `Cumplimiento`). |
| **Arquitectura Hexagonal** | Dominio puro en el centro. Puertos (interfaces abstractas) y adaptadores (SQLAlchemy, Pulsar, FastAPI). |
| **CQS (Command Query Separation)** | Comandos mutan estado. Queries leen estado. Separación explícita en capa de aplicación. |
| **Event-Driven** | Comunicación entre MS mediante eventos de integración publicados/consumidos por Apache Pulsar. |
| **Outbox Pattern** | Los eventos se persisten en la misma transacción de base de datos antes de publicarse al broker. |
| **DLQ (Dead Letter Queue)** | Mensajes fallidos se mueven a tópico DLQ de Pulsar (consumer) o tabla DLQ local (producer). |
| **Idempotencia** | Tabla `idempotency_keys` evita procesar comandos duplicados. |
| **Trazabilidad** | Todos los mensajes llevan `correlationId`, `messageId`, `version` y `producer`. |

### Patrón de comunicación

```
┌──────────────┐    HTTP     ┌──────────────────┐
│   Cliente    │ ───────────> │ ms-marketplace   │
│   (REST)     │              │ -asignacion      │
└──────────────┘              └────────┬─────────┘
                                       │
                              ┌────────▼────────┐
                              │  Outbox (DB)    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ Apache Pulsar   │
                              └────────┬────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
┌─────────▼─────────┐      ┌───────────▼──────────┐   ┌───────────▼──────────┐
│   verificacion.   │      │   cotizaciones.      │   │   notificaciones.    │
│   comandos        │      │   comandos           │   │   comandos           │
│   (Consumer)      │      │   (Futuro)           │   │   (Futuro)           │
└───────────────────┘      └──────────────────────┘   └──────────────────────┘

Queries síncronas:  HTTP GET  /proveedores/{id}/estado, /trabajos/{id}
Comandos async:     Pulsar producer/consumer
```

---

## 3. Estructura de carpetas

```
BeyondMonolith-HogarAlpes/
├── docker-compose.yml                 # Orquestación de Pulsar, PostgreSQL, MS
├── README.md                          # Este archivo
│
├── ms-marketplace-asignacion/         # Microservicio 1
│   ├── Dockerfile
│   ├── IMPLEMENTACION_CAMBIOS_PULSAR.md
│   ├── IMPLEMENTACION_EVENTOS_COTIZACIONES_NOTIFICACIONES.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── src/marketplace_asignacion/
│       ├── main.py
│       ├── domain/
│       │   ├── model.py
│       │   ├── events.py
│       │   ├── value_objects.py
│       │   ├── repository.py
│       │   └── services.py
│       ├── application/
│       │   ├── commands.py
│       │   ├── handlers.py
│       │   ├── integration_events.py
│       │   ├── unit_of_work.py
│       │   └── outbox_port.py
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── orm.py
│       │   ├── repositories.py
│       │   ├── unit_of_work_impl.py
│       │   ├── outbox.py
│       │   ├── pulsar_client.py
│       │   ├── pulsar_producer.py
│       │   └── idempotency.py
│       └── interfaces/
│           ├── api.py
│           ├── health.py
│           └── schemas.py
│   └── tests/
│       ├── test_domain.py
│       ├── test_integration.py
│       ├── test_publisher.py
│       ├── test_health.py
│       └── ...
│
├── ms-verificacion-acreditacion/      # Microservicio 2
│   ├── Dockerfile
│   ├── IMPLEMENTACION.md
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── src/verificacion_acreditacion/
│       ├── main.py
│       ├── domain/
│       │   ├── model.py
│       │   ├── events.py
│       │   ├── value_objects.py
│       │   ├── repository.py
│       │   ├── services.py
│       │   └── exceptions.py
│       ├── application/
│       │   ├── commands.py
│       │   ├── handlers.py
│       │   ├── unit_of_work.py
│       │   └── outbox_port.py
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── orm.py
│       │   ├── repositories.py
│       │   ├── unit_of_work_impl.py
│       │   ├── outbox.py
│       │   ├── pulsar_client.py
│       │   ├── pulsar_consumer.py
│       │   └── idempotency.py
│       └── interfaces/
│           ├── api/
│           │   ├── router.py
│           │   └── schemas.py
│           ├── messaging/
│           │   └── consumer.py
│           └── health.py
│   └── tests/
│       ├── test_domain.py
│       ├── test_integration.py
│       ├── test_consumer.py
│       ├── test_idempotencia.py
│       └── ...
│
├── docs/
│   ├── ARQUITECTURA_DETALLE.md
│   ├── FLUJO_INTEGRACION_PULSAR.md
│   └── FLUJO_INTEGRACION_PULSAR.mmd
│
└── postman/
    ├── HogarAlpes_Escenario4.postman_collection.json
    ├── HogarAlpes_LocalEC2.postman_environment.json
    └── README_Escenario4_Postman.md
```

---

## 4. Requisitos previos

### Software necesario

| Herramienta | Versión mínima | Propósito |
|-------------|----------------|-----------|
| Docker Engine | 24.x | Contenedores de servicios |
| Docker Compose (plugin) | 2.20+ | Orquestación multi-servicio |
| Postman | Última estable | Pruebas manuales de API |

### Puertos necesarios

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| `8000` | ms-marketplace-asignacion (FastAPI) | Local / EC2 |
| `8001` | ms-verificacion-acreditacion (FastAPI) | Local / EC2 |
| `5432` | PostgreSQL | Interno Docker (expuesto opcionalmente) |
| `6650` | Apache Pulsar (binary protocol) | Interno / Local |
| `8080` | Apache Pulsar (Admin REST API) | Interno / Local |

### Variables de entorno mínimas

Las variables se configuran directamente en `docker-compose.yml`. No es necesario crear un `.env` para levantar el entorno local.

```bash
# Solo si deseas override local
cp docker-compose.yml docker-compose.override.yml
# Editar docker-compose.override.yml con tus valores
```

---

## 5. Ejecución con Docker Compose

### 5.1 Levantar todo el ecosistema

```bash
docker compose up -d --build
```

Este comando:
- Construye las imágenes de ambos microservicios.
- Levanta PostgreSQL, Apache Pulsar, Marketplace y Verificación.
- Ejecuta un init script para crear tenant/namespace en Pulsar.

### 5.2 Verificar estado de los contenedores

```bash
docker compose ps
```

**Esperado:** Los 4 servicios deben estar `Up (healthy)`:

```
NAME                       STATUS                   PORTS
hogar_alpes_marketplace    Up (healthy)             0.0.0.0:8000->8000/tcp
hogar_alpes_verificacion   Up (healthy)             0.0.0.0:8001->8001/tcp
hogar_alpes_postgres       Up (healthy)             0.0.0.0:5432->5432/tcp
hogar_alpes_pulsar         Up (healthy)             0.0.0.0:6650->6650, 8080->8080/tcp
```

### 5.3 Ver logs en tiempo real

```bash
# Todos los servicios
docker compose logs -f

# Solo un servicio
docker compose logs -f marketplace
docker compose logs -f verificacion
docker compose logs -f pulsar
docker compose logs -f postgres
```

### 5.4 Reiniciar un servicio específico

```bash
docker compose restart marketplace
docker compose restart verificacion
```

### 5.5 Detener todo

```bash
docker compose down
```

### 5.6 Detener todo y eliminar datos persistentes

```bash
# ⚠️ Esto borra la base de datos PostgreSQL y los datos de Pulsar
docker compose down -v
```

### 5.7 Reconstruir desde cero

```bash
docker compose down -v
docker compose up -d --build
```

### 5.8 Ejecutar pruebas unitarias dentro de los contenedores

```bash
# Marketplace
docker exec hogar_alpes_marketplace pytest tests/ -v

# Verificación
docker exec hogar_alpes_verificacion pytest tests/ -v
```

---

## 6. Endpoints de verificación

### 6.1 Healthchecks

| Microservicio | URL local | URL en EC2 (ejemplo) |
|---------------|-----------|----------------------|
| Marketplace | `http://localhost:8000/health` | `http://<EC2_IP>:8000/health` |
| Verificación | `http://localhost:8001/health` | `http://<EC2_IP>:8001/health` |

**Respuesta esperada:**
```json
{"status":"ok","service":"marketplace-asignacion"}
{"status":"ok","service":"verificacion-acreditacion"}
```
---

**Autor:** Equipo de desarrollo Hogar de los Alpes  
**Versión del README:** 1.0  
**Fecha:** 2026
