# Informe: Saga Orquestada - Hogar de los Alpes

## 1. Objetivo

Demostrar la implementación de un **patrón Saga con orquestación centralizada** para coordinar una transacción distribuida entre múltiples microservicios. El informe evidencia:

- Una Saga exitosa que coordina 4 microservicios.
- Una Saga fallida que ejecuta compensaciones en orden inverso.
- Un Saga Log que permite monitorear el estado de cada transacción.

## 2. Microservicios participantes

| Servicio | Puerto | Rol en la Saga |
|----------|--------|----------------|
| ms-marketplace-asignacion | 8000 | Publica trabajos y selecciona proveedores. |
| ms-verificacion-acreditacion | 8001 | Verifica y acredita proveedores. |
| generador_cotizacion | 8002 | Genera cotizaciones para el trabajo. |
| ms-notificaciones | 8003 | Envía notificaciones al proveedor. |
| ms-orquestador | 8004 | Coordina la Saga, envía comandos y registra el Saga Log. |

## 3. Flujo de la Saga exitosa

El flujo coordina la asignación de un proveedor a un trabajo. Los pasos son:

1. **Marketplace**: seleccionar proveedor para un trabajo publicado.
2. **Verificación**: acreditar al proveedor seleccionado.
3. **Cotización**: generar cotización para el trabajo.
4. **Notificaciones**: enviar notificación al proveedor.
5. **Orquestador**: marca la Saga como `COMPLETADA`.

### Evidencia del flujo exitoso

| Paso | Descripción | Evidencia |
|------|-------------|-----------|
| Healthchecks | Todos los servicios responden 200 OK | `exitosa/paso1.png` |
| Acreditar proveedor | Proveedor queda acreditado en marketplace | `exitosa/paso2.png` |
| Crear trabajo | Se crea el trabajo en estado `SOLICITADO` | `exitosa/paso3.png` |
| Publicar trabajo | Trabajo pasa a estado `PUBLICADO` | `exitosa/paso4.png` |
| Seleccionar proveedor | Trabajo pasa a `PROVEEDOR_SELECCIONADO` | `exitosa/paso5.png` |
| Estado final de la Saga | Saga en estado `COMPLETADA` | `exitosa/paso6-1.png` |
| Saga Log | Logs muestran todos los eventos y comandos procesados | `exitosa/paso7.txt` |

El Saga Log del flujo exitoso (`exitosa/paso7.txt`) contiene los siguientes eventos en orden:

- `ProveedorSeleccionado` RECIBIDO (de marketplace)
- `ProveedorSeleccionadoParaValidacion` ENVIADO (a verificación)
- `ProveedorAcreditado` RECIBIDO (de verificación)
- `GenerarCotizacionCommand` ENVIADO (a cotización)
- `CotizacionSolicitada` RECIBIDO (de cotización)
- `NotificarProveedorAsignadoCommand` ENVIADO (a notificaciones)
- `NotificacionEnviada` RECIBIDO (de notificaciones)

## 4. Flujo de la Saga con fallo y compensación

El flujo de fallo se activa forzando el error de la pasarela de notificaciones. Cuando la notificación falla, el orquestador ejecuta compensaciones en orden inverso:

1. **Notificación falla**: emite `NotificacionFallida`.
2. **Compensación 1**: cancelar cotización (`CancelarCotizacionCommand`).
3. **Compensación 2**: revocar acreditación (`RevocarAcreditacionProveedorCommand`).
4. **Compensación 3**: revertir selección de proveedor en marketplace (HTTP).
5. **Orquestador**: marca la Saga como `COMPENSADA`.

### Evidencia del flujo con compensación

| Paso | Descripción | Evidencia |
|------|-------------|-----------|
| Crear trabajo | Se crea un nuevo trabajo para el flujo de fallo | `fallos/paso1.png` |
| Publicar trabajo | Trabajo publicado | `fallos/paso2.png` |
| Seleccionar proveedor | Trabajo en `PROVEEDOR_SELECCIONADO` | `fallos/paso3.png` |
| Listar Sagas | Saga en `COMPENSADA` con `compensated_steps` | `fallos/paso4.png` |
| Estado de la Saga | Saga `COMPENSADA` | `fallos/paso6.png` |
| Estado final del trabajo | Trabajo vuelve a `PUBLICADO` sin proveedor | `fallos/trabajo_despues_compesancion.png` |

La captura `fallos/paso4.png` muestra el campo `compensated_steps` con los tres pasos compensados:

```json
"compensated_steps": [
    "CotizacionCancelada",
    "AcreditacionRevocada",
    "SeleccionProveedorRevertida"
]
```

Esto demuestra que las compensaciones se ejecutaron en orden inverso:

```text
Cotización → Verificación → Marketplace
```

## 5. Cumplimiento de la rúbrica

| Requisito | Cómo se cumple | Evidencia |
|-----------|----------------|-----------|
| Saga con mínimo 3 servicios | Participan 4 servicios: marketplace, verificación, cotización, notificaciones. | `exitosa/paso7.txt` y `fallos/paso4.png` |
| Saga mediante orquestación | El `ms-orquestador` envía comandos y consume eventos de todos los servicios. | `exitosa/paso7.txt` (comandos ENVIADO por ms-orquestador) |
| Transacción exitosa | Saga llega a `COMPLETADA`. | `exitosa/paso6-1.png` |
| Transacción fallida | Notificación falla y Saga pasa a `COMPENSANDO`. | `fallos/paso6.png` |
| Compensación después del fallo | Se ejecutan 3 compensaciones y la Saga llega a `COMPENSADA`. | `fallos/paso4.png` y `fallos/trabajo_despues_compesancion.png` |
| Saga Log para monitoreo | Tabla `saga_logs` expuesta en `GET /sagas/{id}/logs`. | `exitosa/paso7.txt` y `fallos/paso4.png` |

## 6. Cómo reproducir la demostración

### Preparación

Asegurar que la pasarela de notificaciones esté en modo normal:

```bash
curl -X POST "http://localhost:8003/debug/dependencia-externa?fallar=false"
```

### Flujo exitoso

1. Acreditar proveedor:
   ```bash
   curl -X POST "http://localhost:8000/debug/acreditar-proveedor?proveedor_id=22222222-2222-2222-2222-222222222222"
   ```

2. Crear trabajo:
   ```bash
   curl -X POST http://localhost:8000/trabajos/solicitar \
     -H "Content-Type: application/json" \
     -d '{"cliente_id":"11111111-1111-1111-1111-111111111111","correlation_id":"corr-saga-exitosa","ubicacion":{"direccion":"Calle 100","ciudad":"Bogotá","pais":"CO"},"alcance":{"descripcion":"Instalación","categoria":"Electricidad"}}'
   ```

3. Publicar trabajo (usar el `trabajo_id` devuelto):
   ```bash
   curl -X POST http://localhost:8000/trabajos/{trabajo_id}/publicar \
     -H "Content-Type: application/json" \
     -d '{"correlation_id":"corr-saga-exitosa"}'
   ```

4. Seleccionar proveedor:
   ```bash
   curl -X POST http://localhost:8000/trabajos/{trabajo_id}/seleccionar-proveedor \
     -H "Content-Type: application/json" \
     -d '{"proveedor_id":"22222222-2222-2222-2222-222222222222","correlation_id":"corr-saga-exitosa"}'
   ```

5. Esperar 10-15 segundos y consultar el estado:
   ```bash
   curl http://localhost:8004/sagas
   curl http://localhost:8004/sagas/{saga_id}/estado
   curl http://localhost:8004/sagas/{saga_id}/logs
   ```

### Flujo con compensación

1. Activar fallo de notificaciones:
   ```bash
   curl -X POST "http://localhost:8003/debug/dependencia-externa?fallar=true"
   ```

2. Crear, publicar y seleccionar proveedor con un `correlation_id` diferente.

3. Esperar 15-20 segundos y consultar:
   ```bash
   curl http://localhost:8004/sagas/{saga_id}/estado
   curl http://localhost:8004/sagas/{saga_id}/logs
   curl http://localhost:8000/trabajos/{trabajo_id}
   ```

4. Restaurar notificaciones:
   ```bash
   curl -X POST "http://localhost:8003/debug/dependencia-externa?fallar=false"
   ```

## 7. Conclusión

La implementación cumple con todos los requisitos de la rúbrica:

- Se demostró una Saga orquestada con 4 microservicios.
- Se ejecutó una transacción exitosa completa hasta `COMPLETADA`.
- Se ejecutó una transacción fallida con compensación hasta `COMPENSADA`.
- Se verificó que el trabajo vuelve a estado `PUBLICADO` sin proveedor seleccionado.
- El Saga Log registra cada evento recibido y cada comando enviado, permitiendo monitorear el estado de la transacción.

## 8. Anexo: lista de capturas

### Flujo exitoso

- `resultados/exitosa/paso1.png` — Healthchecks
- `resultados/exitosa/paso2.png` — Acreditar proveedor
- `resultados/exitosa/paso3.png` — Crear trabajo
- `resultados/exitosa/paso4.png` — Publicar trabajo
- `resultados/exitosa/paso5.png` — Seleccionar proveedor
- `resultados/exitosa/paso6-1.png` — Saga `COMPLETADA`
- `resultados/exitosa/paso7.txt` — Saga Log completo

### Flujo con compensación

- `resultados/fallos/paso1.png` — Crear trabajo
- `resultados/fallos/paso2.png` — Publicar trabajo
- `resultados/fallos/paso3.png` — Seleccionar proveedor
- `resultados/fallos/paso4.png` — Listar Sagas con `COMPENSADA`
- `resultados/fallos/paso6.png` — Estado `COMPENSADA`
- `resultados/fallos/trabajo_despues_compesancion.png` — Trabajo revertido a `PUBLICADO`
