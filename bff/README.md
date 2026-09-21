# BFF (Backend for Frontend) — Hogar de los Alpes

Punto de entrada único en **GraphQL** para los clientes (web/móvil), que agrega las capacidades de negocio de los 4 microservicios del sistema. El BFF no tiene base de datos propia ni lógica de negocio: solo traduce operaciones GraphQL a llamadas HTTP (REST) contra los microservicios reales y transforma sus respuestas a tipos GraphQL.

Construido con **FastAPI** + **Strawberry GraphQL**.

## Arquitectura

Cada resolver GraphQL (`Query`/`Mutation`) delega en un cliente HTTP que llama al endpoint REST equivalente del microservicio correspondiente y mapea el JSON de respuesta a un tipo Strawberry.

## Estructura de archivos


| Archivo | Responsabilidad |
|---|---|
| `infrastructure/config.py` | Clase `Settings` que lee `MARKETPLACE_URL`, `VERIFICACION_URL`, `COTIZACION_URL`, `NOTIFICACIONES_URL` desde variables de entorno. |
| `infrastructure/clientes.py` | Una clase por microservicio (`ClienteMarketplace`, `ClienteVerificacion`, `ClienteCotizacion`, `ClienteNotificaciones`) con métodos `async` que llaman al REST real vía `httpx.AsyncClient`. |
| `interfaces/graphql/esquemas.py` | Tipos de salida (`@strawberry.type`) e inputs de entrada (`@strawberry.input`) del esquema GraphQL. |
| `interfaces/graphql/consultas.py` | `class Query` con un campo por microservicio para leer un recurso por id. |
| `interfaces/graphql/mutaciones.py` | `class Mutation` con las operaciones de escritura disponibles. |
| `interfaces/graphql/router.py` | Construye `strawberry.Schema(query=Query, mutation=Mutation)` y el `GraphQLRouter` de FastAPI, montado en `/graphql`. |
| `interfaces/health.py` | `GET /health` |
| `main.py` | Crea la app FastAPI e incluye los routers de health y GraphQL. |

## Esquema GraphQL

### Queries (`consultas.py`)

| Campo GraphQL | Microservicio destino | Endpoint REST |
|---|---|---|
| `trabajo(trabajoId)` | marketplace | `GET /trabajos/{id}` |
| `estadoProveedor(proveedorId)` | verificación | `GET /proveedores/{id}/estado` |
| `cotizacion(cotizacionId)` | cotización | `GET /cotizaciones/{id}` |
| `notificacion(notificacionId)` | notificaciones | `GET /notificaciones/{id}` |

### Mutations (`mutaciones.py`)

| Campo GraphQL | Microservicio destino | Endpoint REST |
|---|---|---|
| `solicitarTrabajo(input)` | marketplace | `POST /trabajos/solicitar` |
| `iniciarVerificacion(proveedorId)` | verificación | `POST /verificaciones` |
| `solicitarCotizacion(input)` | cotización | `POST /cotizaciones/solicitar` |

Este es un esquema base: cada microservicio expone más operaciones por REST (publicar trabajo, seleccionar proveedor, aprobar/rechazar verificación, listar/actualizar/eliminar cotización, etc.) que pueden agregarse como nuevos campos siguiendo el mismo patrón: agregar el método al cliente en `clientes.py`, el tipo/input en `esquemas.py`, y el resolver en `consultas.py` o `mutaciones.py`.

## Cómo ejecutarlo

### Con Docker Compose

Desde la raíz del repositorio:

```bash
docker compose up -d
```

El BFF queda disponible en `http://localhost:8010/graphql` (incluye GraphiQL/Playground al abrirlo en el navegador) y su healthcheck en `http://localhost:8010/health`. Dentro de la red de Docker, el servicio se conecta a los demás microservicios por su nombre de servicio (`marketplace`, `verificacion`, `cotizacion`, `notificaciones`), variables ya configuradas en `docker-compose.yml`.

### Standalone

```bash
cd bff
pip install -r requirements.txt
cp .env.ejemplo .env   # ajustar URLs si los microservicios no corren en localhost
uvicorn bff.main:app --host 0.0.0.0 --port 8010 --reload
```

Requiere que los 4 microservicios estén corriendo y accesibles en las URLs configuradas (por defecto `http://localhost:8000-8003`).

## Ejemplo de uso

Query:

```graphql
query {
  trabajo(trabajoId: "5c1e2e2a-1111-4b3a-9c9a-abcdef123456") {
    trabajoId
    estado
    proveedorSeleccionadoId
  }
}
```

Mutation:

```graphql
mutation {
  solicitarTrabajo(input: {
    clienteId: "5c1e2e2a-1111-4b3a-9c9a-abcdef123456"
    ubicacion: { direccion: "Calle 10 #5-20", ciudad: "Bogotá", pais: "CO" }
    alcance: { descripcion: "Reparación de tubería", categoria: "plomeria" }
  }) {
    trabajoId
    estado
  }
}
```

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `MARKETPLACE_URL` | `http://localhost:8000` | Base URL de `ms-marketplace-asignacion` |
| `VERIFICACION_URL` | `http://localhost:8001` | Base URL de `ms-verificacion-acreditacion` |
| `COTIZACION_URL` | `http://localhost:8002` | Base URL de `generador_cotizacion` |
| `NOTIFICACIONES_URL` | `http://localhost:8003` | Base URL de `ms-notificaciones` |
