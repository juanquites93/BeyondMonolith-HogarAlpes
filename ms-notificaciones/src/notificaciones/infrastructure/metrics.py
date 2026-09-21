"""Metricas propias del lado de eventos (consumo desde Pulsar).

Las metricas de HTTP (requests OK/fallidos, latencia) las expone
automaticamente prometheus-fastapi-instrumentator sobre /metrics (ver
main.py). Aqui solo se agrega lo que esa libreria no cubre: cuantos
eventos se consumieron y con que resultado.
"""
from prometheus_client import Counter

eventos_consumidos_total = Counter(
    "notificaciones_eventos_consumidos_total",
    "Eventos de Pulsar procesados por este servicio, por resultado.",
    ["resultado"],
)

# Se inicializan en 0 para que ambas series existan desde el arranque
# (evita que un dashboard/alerta las vea como "sin datos" antes del primer evento).
eventos_consumidos_total.labels(resultado="ok")
eventos_consumidos_total.labels(resultado="fallido")