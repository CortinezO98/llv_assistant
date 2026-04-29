"""
app/workers/outbox_worker.py

Worker que procesa la cola Outbox y envía mensajes a WhatsApp.
Patrón transaccional: garantiza entrega con reintentos automáticos.
"""
import json
import logging

from app.core.settings import settings
from app.db.models.messaging import OutboxMessage
from app.db.session import SessionLocal
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def flush_outbox() -> dict:
    """Procesa todos los mensajes pendientes del outbox."""
    db = SessionLocal()
    client = WhatsAppClient()
    sent = 0
    failed = 0

    try:
        pending = (
            db.query(OutboxMessage)
            .filter(
                OutboxMessage.status == "pending",
                OutboxMessage.attempts < MAX_ATTEMPTS,
            )
            .order_by(OutboxMessage.created_at.asc())
            .limit(50)
            .all()
        )

        for msg in pending:
            msg.attempts = (msg.attempts or 0) + 1
            try:
                payload = json.loads(msg.payload_json)
                client.send_text(to=payload["to"], text=payload["text"])
                msg.status = "sent"
                from datetime import datetime
                msg.processed_at = datetime.utcnow()
                sent += 1
            except Exception as exc:
                logger.warning("Outbox fallo | id=%s | attempt=%s | error=%s", msg.id, msg.attempts, exc)
                msg.last_error = str(exc)
                if msg.attempts >= MAX_ATTEMPTS:
                    msg.status = "failed"
                    failed += 1
            db.flush()

        db.commit()
        logger.info("Outbox flush | sent=%s | failed=%s | total=%s", sent, failed, len(pending))
        return {"sent": sent, "failed": failed}

    except Exception as exc:
        logger.exception("Error en flush_outbox: %s", exc)
        db.rollback()
        return {"sent": 0, "failed": 0, "error": str(exc)}
    finally:
        db.close()
        client.close()
