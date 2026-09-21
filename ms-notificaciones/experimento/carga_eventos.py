#!/usr/bin/env python3
"""Generador de eventos de prueba para el experimento de disponibilidad.

k6 (carga.js) solo ejercita el lado HTTP (/health, /ready). El volumen de
negocio real de este servicio llega por Pulsar, asi que este script publica
directamente al topico de comandos, con el mismo formato de sobre que espera
`pulsar_consumidor.procesar_mensaje` (messageType/payload/correlationId/
idempotencyKey), alternando entre los dos comandos que el servicio entiende.

Variables de entorno:
  PULSAR_SERVICE_URL  Default: pulsar://localhost:16650
                       (puerto que expone experimento/docker-compose.yml)
  TOPICO_COMANDOS      Default: persistent://hogar/alpes/notificaciones.comandos
  RATE                 Eventos por segundo (aproximado). Default: 2
  DURATION_SECONDS     Duracion total en segundos. Default: 60

Requiere el paquete `pulsar-client` (ya esta en requirements.txt del
servicio). Uso, desde el entorno virtual del proyecto:
  RATE=10 DURATION_SECONDS=300 python3 carga_eventos.py
"""
import json
import os
import time
import uuid

import pulsar

PULSAR_SERVICE_URL = os.getenv("PULSAR_SERVICE_URL", "pulsar://localhost:16650")
TOPICO_COMANDOS = os.getenv(
    "TOPICO_COMANDOS", "persistent://hogar/alpes/notificaciones.comandos"
)
RATE = float(os.getenv("RATE", "2"))
DURATION_SECONDS = float(os.getenv("DURATION_SECONDS", "60"))


def sobre_proveedor_asignado() -> dict:
    return {
        "messageType": "NotificarProveedorAsignadoCommand",
        "correlationId": str(uuid.uuid4()),
        "idempotencyKey": str(uuid.uuid4()),
        "payload": {
            "proveedor_id": str(uuid.uuid4()),
            "trabajo_id": str(uuid.uuid4()),
            "cliente_id": str(uuid.uuid4()),
            "detalles_trabajo": {
                "descripcion": "Reparacion de prueba (experimento de carga)",
                "categoria": "plomeria",
                "ubicacion": {
                    "direccion": "Calle de prueba 123",
                    "ciudad": "Bogota",
                },
            },
        },
    }


def sobre_cliente_notificado() -> dict:
    return {
        "messageType": "NotificarClienteProveedorAsignadoCommand",
        "correlationId": str(uuid.uuid4()),
        "idempotencyKey": str(uuid.uuid4()),
        "payload": {
            "cliente_id": str(uuid.uuid4()),
            "trabajo_id": str(uuid.uuid4()),
            "proveedor_id": str(uuid.uuid4()),
        },
    }


GENERADORES = [sobre_proveedor_asignado, sobre_cliente_notificado]


def main() -> None:
    client = pulsar.Client(PULSAR_SERVICE_URL)
    productor = client.create_producer(TOPICO_COMANDOS)

    intervalo = 1.0 / RATE if RATE > 0 else 0.0
    fin = time.monotonic() + DURATION_SECONDS
    enviados = 0

    print(
        f"Publicando en {TOPICO_COMANDOS} via {PULSAR_SERVICE_URL} "
        f"a ~{RATE} eventos/seg durante {DURATION_SECONDS}s..."
    )

    i = 0
    try:
        while time.monotonic() < fin:
            inicio = time.monotonic()
            sobre = GENERADORES[i % len(GENERADORES)]()
            productor.send(json.dumps(sobre).encode("utf-8"))
            enviados += 1
            i += 1

            if enviados % 50 == 0:
                print(f"  {enviados} eventos enviados...")

            transcurrido = time.monotonic() - inicio
            time.sleep(max(0.0, intervalo - transcurrido))
    finally:
        productor.flush()
        client.close()

    print(f"Listo: {enviados} eventos publicados.")


if __name__ == "__main__":
    main()
