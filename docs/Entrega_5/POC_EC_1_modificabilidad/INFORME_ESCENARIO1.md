# Informe: Escenario de Calidad #1 - Actualizar la tecnología persistencia no afecta la capa de dominio del aplicativo

## 1. Objetivo

Demostrar el cumplimiento del **Escenario de Calidad #1**: el microservicio **Generador de Cotización** modifica su tecnología de persistencia, reemplazando la base de datos PostgreSQL por una base de datos MySQL.

Todo esto creando nuevas clases en la capa de infraestructura sin necesidad de modificar la capa de dominio o lógica de negocio.

## 2. Arquitectura y servicios involucrados

| Servicio | Puerto | Rol en el escenario |
|----------|--------|---------------------|
| ms-generador-cotizacion | 8002 | Microservicio que expone las APIs a probar, modificando la tecnología de persistencia. |

## 3. Hipótesis

Si el servicio de generación de cotizaciones actualiza su tecnología, no es necesario modificar la capa de dominio ni la lógica de negocio. Los servicios CRUD de cotizaciones siguen funcionando sin novedad:

1. `POST /cotizaciones/solicitar` (crear cotización)
2. `GET /cotizaciones/{id}` (obtener cotización)
3. `GET /cotizaciones` (listar cotizaciones)
4. `PUT /cotizaciones/{id}` (actualizar cotización)

## 4. Procedimiento ejecutado

Se crearon las clases necesarias para realizar la conexión con la base de datos MySQL en la capa de infraestructura, se realiza la conexión usando el nuevo adaptador y finalmente se realizan pruebas en postman verificando el correcto funcionamiento del CRUD.

### 4.1 Creación de nuevo puerto de persistencia MySQL

Se agregaron las nuevas clases para soportar la conexión a la base de datos MySQL:

| Archivo | Función |
|--------|-------|
| `infrastructure/mysql_database.py` | Engine/sesion de MySQL |
| `infrastructure/mysql_outbox.py` | Implementación del outboxstore en MySQL |
| `infrastructure/mysql_repositories.py` | Implementación del puerto CotizacionRepository sobre MySQL |
| `infrastructure/mysql_unit_of_work.py` | Implementación del puerto UnitOfWork sobre MySQL |

Se modificaron las siguientes clases para agregar el nuevo adaptador:

| Archivo | Modificación |
|--------|-------|
| `infrastructure/config.py` | Nuevo String de conexión para MySQL |
| `interfaces/api.py` | Reemplazo de SqlAlchemyUnitOfWork() y SqlAlchemyOutboxStore() por sus contrapartes MySQLUnitOfWork() y MySQLOutboxStore()  |


### 4.2 Ejecución y pruebas del microservicio

Se realizó la ejecución del microservicio mediante la creación del contenedor en Docker y se realizaron las pruebas de forma exitosa (ver imagenes `prueba1.png`, `prueba2.png`, `prueba3.png`, `prueba4.png`, `prueba5.png`, `prueba6.png`)

## 9. Conclusión

El Escenario de Calidad #1 se cumple satisfactoriamente:

- **0% de modificación en las entidades de dominio ni efectos cascada** al reemplazar el puerto construido anteriormente con tecnología PostgreSQL por uno en MySQL.
- **Correcto funcionamiento del CRUD** sin necesidad de modificar la capa de dominio del aplicativo, lo que demuestra la correcta implementación de la arquitectura hexagonal y el patrón de inversión de dependencias.

## 10. Anexo: archivos de evidencia

| Archivo | Descripción |
|---------|-------------|
| `resultados/escenario1/prueba1.png` | Logs del levantamiento del microservicio. |
| `resultados/escenario1/prueba2.png` | Logs de la ejecución de los servicios del CRUD. |
| `resultados/escenario1/prueba3.png` | Ejecución del servicio de creación de cotización en Postman |
| `resultados/escenario1/prueba4.png` | Ejecución del servicio de obtener cotización en Postman. |
| `resultados/escenario1/prueba5.png` | Ejecución del servicio de listar cotizaciones en Postman. |
| `resultados/escenario1/prueba6.png` | Ejecución del servicio de actualizar cotización en Postman. |
| `postman/HogarAlpes_Escenario1.postman_collection.json` | Colección de Postman usada. |
