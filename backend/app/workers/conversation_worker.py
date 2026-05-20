"""
app/workers/conversation_worker.py

Worker conversacional para procesar mensajes entrantes desde llv_inbox.

IMPORTANTE:
Este worker NO contiene el flujo conversacional.
El flujo real está centralizado en app/services/bot_service.py.

Responsabilidades:
- Leer mensajes pendientes de llv_inbox.
- Marcar mensajes como processing.
- Delegar el procesamiento al BotService.
- BotService se encarga de:
    - Crear/buscar paciente.
    - Crear/buscar sesión.
    - Ejecutar el flujo conversacional real.
    - Detectar intención de pago.
    - Manejar comprobantes.
    - Encolar respuestas en llv_outbox.
    - Marcar inbox como done.
- Manejar errores y evitar que mensajes queden bloqueados.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.settings import settings
from app.db.models.messaging import InboxMessage
from app.db.session import SessionLocal
from app.services.bot_service import BotService

logger = logging.getLogger(__name__)


def run_conversation_worker() -> dict[str, Any]:
    """
    Procesa mensajes pendientes de llv_inbox.

    Retorna un resumen operativo:

    {
        "processed": int,
        "failed": int,
        "skipped": int
    }
    """

    db = SessionLocal()

    processed = 0
    failed = 0
    skipped = 0

    try:
        batch_size = max(1, settings.conversation_worker_batch or 10)

        pending_messages = (
            db.query(InboxMessage)
            .filter(InboxMessage.status == "pending")
            .order_by(InboxMessage.created_at.asc())
            .limit(batch_size)
            .all()
        )

        if not pending_messages:
            return {
                "processed": 0,
                "failed": 0,
                "skipped": 0,
            }

        logger.info(
            "Conversation worker | mensajes pendientes=%s",
            len(pending_messages),
        )

        bot_service = BotService(db)

        for inbox in pending_messages:
            try:
                logger.info(
                    "Procesando inbox | id=%s | number=%s | type=%s | content=%s",
                    inbox.id,
                    inbox.whatsapp_number,
                    inbox.message_type,
                    (inbox.content or "")[:120],
                )

                # Marcar como processing para evitar doble procesamiento
                # si el worker se ejecuta nuevamente mientras trabaja.
                inbox.status = "processing"
                db.flush()

                result = bot_service.process_message(inbox)

                if result.get("skipped"):
                    skipped += 1
                else:
                    processed += 1

                logger.info(
                    "Inbox procesado | id=%s | result=%s",
                    inbox.id,
                    result,
                )

            except Exception as exc:
                logger.exception(
                    "Error procesando inbox | id=%s | number=%s | error=%s",
                    getattr(inbox, "id", None),
                    getattr(inbox, "whatsapp_number", None),
                    exc,
                )

                failed += 1

                try:
                    inbox.status = "error"
                    db.commit()
                except Exception as commit_exc:
                    logger.exception(
                        "No se pudo marcar inbox como error | id=%s | error=%s",
                        getattr(inbox, "id", None),
                        commit_exc,
                    )
                    db.rollback()

        result = {
            "processed": processed,
            "failed": failed,
            "skipped": skipped,
        }

        logger.info("Conversation worker | %s", result)
        return result

    except Exception as exc:
        logger.exception("Error general en conversation_worker: %s", exc)
        db.rollback()

        return {
            "processed": processed,
            "failed": failed + 1,
            "skipped": skipped,
            "error": str(exc),
        }

    finally:
        db.close()