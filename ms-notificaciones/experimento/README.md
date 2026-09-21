# Entorno del experimento de disponibilidad

Este `docker-compose.yml` levanta una copia **aislada** de todo lo que necesita
`ms-notificaciones` para el experimento descrito en
[`../docs/experimento-disponibilidad.md`](../docs/experimento-disponibilidad.md):
su propio Pulsar, su propio Postgres, 3 réplicas del servicio y un balanceador
de carga (Nginx) delante de ellas. No comparte nada con el `docker-compose.yml`
de la raíz del monorepo (puertos, nombres de contenedor y datos son propios).

## Arrancar el experimento

```bash
cd ms-notificaciones/experimento
docker compose up -d --build
```

Esto levanta, en orden: `pulsar` → `pulsar-init` (crea el tenant/namespace
`hogar/alpes`) → `postgres` → las 3 réplicas (`notificaciones_1/2/3`) → `nginx`.

Verifica que las 3 réplicas están sanas antes de empezar cualquier prueba:

```bash
curl -s http://localhost:18000/ready   # a traves del balanceador
for p in notificaciones_1 notificaciones_2 notificaciones_3; do
  docker compose exec $p curl -s localhost:8000/ready; echo
done
```

**Punto de entrada del experimento:** `http://localhost:18000` (Nginx). No le
pegues directo a una réplica salvo para depurar — el balanceador es lo que
estamos validando.

## Simular N=2 réplicas (variante del diseño, sección 7)

Por defecto corren las 3. Para la variante de 2 réplicas, apaga una **antes**
de arrancar la prueba de carga:

```bash
docker compose stop notificaciones_3
```

Para volver a 3:

```bash
docker compose start notificaciones_3
```

## Inyectar la falla durante la prueba (punto H del diseño)

Exactamente el mismo comando, pero a mitad de la ventana de carga en 4x
(fase 4 del diseño del experimento):

```bash
docker compose stop notificaciones_1   # o el que este activo en ese momento
```

Y para la fase de recuperación (fase 5):

```bash
docker compose start notificaciones_1
```

Confirma en los logs y en `/metrics` que Nginx dejó de enviarle tráfico
mientras estuvo apagada, y que la volvió a incluir sola al reiniciarla (sin
que tú se lo digas a Nginx — eso es lo que valida la hipótesis).

## Ver qué réplica atendió cada solicitud

Cada respuesta trae el header `X-Instance-Id`:

```bash
curl -sD - http://localhost:18000/ -o /dev/null | grep -i x-instance-id
```

## Ver las métricas

Nginx reparte `/metrics` igual que cualquier otra ruta, así que pegarle al
balanceador solo te muestra los contadores **de una réplica al azar**, no la
suma de las tres:

```bash
curl -s http://localhost:18000/metrics
```

Para ver las métricas de cada réplica por separado (lo que necesitas para
comparar entre ellas durante el experimento):

```bash
for p in notificaciones_1 notificaciones_2 notificaciones_3; do
  echo "--- $p ---"
  docker compose exec $p curl -s localhost:8000/metrics | grep -E "^notificaciones_eventos|^http_requests_total"
done
```

## Apagar todo y borrar los datos del experimento

```bash
docker compose down -v
```

(`-v` borra los volúmenes de Postgres/Pulsar del experimento — no toca nada
de la raíz del monorepo).
