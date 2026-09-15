# Microservicio Generador de cotizaciones
## 1. Microservicio implementado
Nombre: Generador de cotizaciones
Responsable: Juan Hernández
## 2. Rol del microservicio en la solución
El microservicio de Generador de cotizaciones recibe solicitudes de cotización a partir de un un tópico de comandos, para despues generar un evento al generarse la solicitud. Adicionalmente también se expone un CRUD de cotizaciones.
Su responsabilidad principal en esta iteración es:
1. Recibir solicitudes de cotización.
2. Gestionar el ciclo de una cotización.
3. Emitir un evento con la confirmación de la creación de solicitud de la cotización.

## 3. Alcance técnico implementado

### Casos de uso principales:
- Solicitar una cotización
- Notificar con un evento la solicitud de cotización

### Integración asíncrona:
- Publicación de comandos/eventos por Apache Pulsar
- Trazabilidad de mensajes mediante correlationId

### Persistencia:
Modelo CRUD para la solicitud de cotizaciones

### Observabilidad:
- Endpoint de healthcheck
- Logs estructurados para seguimiento del flujo
