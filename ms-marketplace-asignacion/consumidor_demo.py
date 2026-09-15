import os
import time
import logging

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMIDOR] %(message)s",
)
logger = logging.getLogger("consumidor")

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://hogar:alpes123@localhost:5432/marketplace"
)


def procesar_evento(row):
    msg_type = row["event_type"]
    payload = row["payload"]
    corr = row["correlation_id"] or "N/A"

    if msg_type == "TrabajoSolicitado":
        logger.info(
            f"📥 [{corr}] TrabajoSolicitado recibido | "
            f"trabajo_id={payload.get('trabajo_id')} | "
            f"cliente_id={payload.get('cliente_id')} | "
            f"Enviando notificación simulada al cliente..."
        )

    elif msg_type == "TrabajoPublicado":
        logger.info(
            f"📢 [{corr}] TrabajoPublicado recibido | "
            f"trabajo_id={payload.get('trabajo_id')} | "
            f"Notificando a proveedores cercanos..."
        )

    elif msg_type == "ProveedorSeleccionado":
        logger.info(
            f"✅ [{corr}] ProveedorSeleccionado recibido | "
            f"trabajo_id={payload.get('trabajo_id')} | "
            f"proveedor_id={payload.get('proveedor_id')} | "
            f"Confirmando orden de servicio..."
        )

    else:
        logger.info(f"❓ [{corr}] Evento desconocido: {msg_type}")


def run():
    logger.info("🚀 Consumidor de Outbox iniciado.")
    logger.info(f"   Conectando a PostgreSQL...")

    while True:
        try:
            conn = psycopg2.connect(DB_URL)
            logger.info("   ✅ Conexión establecida.")
            break
        except Exception as e:
            logger.warning(f"   ⏳ Esperando PostgreSQL... ({e})")
            time.sleep(2)

    while True:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, event_type, payload, correlation_id
                FROM outbox
                WHERE processed_at IS NULL
                ORDER BY occurred_at
                LIMIT 10
                """
            )
            rows = cur.fetchall()

            for row in rows:
                procesar_evento(row)
                cur.execute(
                    "UPDATE outbox SET processed_at = NOW() WHERE id = %s", (row["id"],)
                )
                conn.commit()
                logger.info(
                    f"   ↳ Evento {str(row['id'])[:8]}... marcado como procesado."
                )

        if not rows:
            logger.info("⏳ Sin eventos pendientes. Esperando...")

        time.sleep(2)


if __name__ == "__main__":
    run()
