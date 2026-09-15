# Implementación – Verificación y Acreditación

## 1. Objetivo
Construir desde cero el microservicio **Verificación y Acreditación** siguiendo arquitectura hexagonal, DDD y event-driven con Apache Pulsar.

## 2. Decisiones clave
- **Idioma ubicuo:** Proveedor, Verificación, Acreditación, EstadoVerificación, EstadoAcreditación, Evidencia, Cumplimiento.
- **Base de datos:** SQLite por defecto para demos locales. PostgreSQL soportado cambiando `DATABASE_URL`.
- **Broker:** Apache Pulsar con `pulsar-client` oficial de Python.
- **Outbox:** Implementación funcional con SQLAlchemy en la misma transacción del comando.

## 3. Estructura de carpetas
```
ms-verificacion-acreditacion/
├── src/verificacion_acreditacion/
│   ├── domain/          # Modelo puro, eventos, repositorios abstractos
│   ├── application/     # Comandos, handlers, UoW y Outbox (puertos)
│   ├── infrastructure/  # DB, ORM, repos concretos, Pulsar client/producer/consumer
│   ├── interfaces/      # API REST (FastAPI) + Messaging consumer
│   └── seedwork/        # (reservado para utilidades transversales)
├── tests/               # Dominio, integración, consumer, idempotencia
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## 4. Casos de uso implementados
1. `IniciarVerificacionProveedor` – POST `/verificaciones`
2. `AprobarVerificacionProveedor` – POST `/verificaciones/{id}/aprobar`
3. `RechazarVerificacionProveedor` – POST `/verificaciones/{id}/rechazar`
4. `AcreditarProveedor` – POST `/acreditaciones`
5. `ConsultarEstadoProveedor` – GET `/proveedores/{id}/estado`

## 5. Reglas de negocio
- No se puede acreditar un proveedor sin verificación aprobada.
- No se puede aprobar/rechazar dos veces la misma verificación activa.
- Comandos con la misma `idempotency_key` no duplican efectos.

## 6. Eventos emitidos
- `VerificacionProveedorIniciada`
- `VerificacionProveedorAprobada`
- `VerificacionProveedorRechazada`
- `ProveedorAcreditado`
- `ProveedorNoAcreditado`

## 7. Pulsar
- **Consumer:** suscrito a `persistent://hogar/alpes/verificacion.comandos`.
- **Producer:** publica en `persistent://hogar/alpes/verificacion.eventos` leyendo de la tabla Outbox.
- **Retry:** `negative_acknowledge()` en fallo de procesamiento.
- **DLQ:** documentada; se activa mediante política de suscripción en Pulsar.

## 8. Pruebas
- `test_domain.py`: invariantes de negocio.
- `test_integration.py`: comando → DB → outbox.
- `test_consumer.py`: simulación de mensaje Pulsar → handler.
- `test_idempotencia.py`: mensaje duplicado no genera doble efecto.

## 9. Cómo ejecutar localmente
```bash
cd ms-verificacion-acreditacion
pip install -r requirements.txt
uvicorn src.verificacion_acreditacion.main:app --reload --port 8001
```

## 10. Pendiente / Mejoras futuras
- Implementar Schema Registry (Avro/Protobuf) para validación de contratos.
- Configurar DLQ explícita en código del consumer.
- Reemplazar SQLite por PostgreSQL en producción.
- Agregar métricas Prometheus.
