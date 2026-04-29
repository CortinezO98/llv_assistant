"""
app/api/routes/webhook.py

Webhook de WhatsApp Business API (Meta Cloud API).
- GET  /webhook  → verificación del webhook por Meta
- POST /webhook  → recepción de mensajes entrantes
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.core.settings import settings
from app.db.models.messaging import InboxMessage
from app.db.session import get_db
from app.workers.outbox_worker import flush_outbox

router = APIRouter(tags=["webhook"])
logger = logging.getLogger(__name__)


# ── GET — verificación del webhook ───────────────────────────────────────────
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.webhook_verify_token:
        logger.info("Webhook verificado correctamente por Meta.")
        return int(hub_challenge)
    logger.warning("Intento de verificación de webhook fallido.")
    raise HTTPException(status_code=403, detail="Verification failed")


# ── POST — mensajes entrantes ─────────────────────────────────────────────────
@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extraer mensajes del payload de Meta
    messages = _extract_messages(body)

    for msg_data in messages:
        number = msg_data.get("number")
        meta_id = msg_data.get("meta_message_id")

        if not number or not meta_id:
            continue

        # Deduplicar
        existing = db.query(InboxMessage).filter(InboxMessage.meta_message_id == meta_id).first()
        if existing:
            logger.debug("Mensaje duplicado ignorado | meta_id=%s", meta_id)
            continue

        inbox = InboxMessage(
            whatsapp_number=number,
            profile_name=msg_data.get("profile_name"),
            meta_message_id=meta_id,
            message_type=msg_data.get("type", "text"),
            content=msg_data.get("text"),
            media_id=msg_data.get("media_id"),
            status="pending",
        )
        db.add(inbox)

    db.commit()

    # Procesar en background
    background_tasks.add_task(_process_inbox, db)
    background_tasks.add_task(flush_outbox)

    return {"status": "ok"}


def _extract_messages(body: dict) -> list[dict]:
    """Extrae mensajes del payload de Meta WhatsApp Cloud API."""
    results = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                messages = value.get("messages", [])

                contact_map = {c["wa_id"]: c.get("profile", {}).get("name") for c in contacts}

                for msg in messages:
                    number = msg.get("from")
                    msg_type = msg.get("type", "text")
                    meta_id = msg.get("id")
                    profile_name = contact_map.get(number)

                    data = {
                        "number": number,
                        "meta_message_id": meta_id,
                        "profile_name": profile_name,
                        "type": msg_type,
                        "text": None,
                        "media_id": None,
                    }

                    if msg_type == "text":
                        data["text"] = msg.get("text", {}).get("body", "")
                    elif msg_type in ("image", "document", "audio", "video", "sticker"):
                        data["media_id"] = msg.get(msg_type, {}).get("id")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            data["text"] = interactive["button_reply"].get("title", "")
                        elif interactive.get("type") == "list_reply":
                            data["text"] = interactive["list_reply"].get("title", "")
                    elif msg_type == "reaction":
                        data["type"] = "reaction"

                    results.append(data)
    except Exception as exc:
        logger.exception("Error extrayendo mensajes del webhook: %s", exc)
    return results


def _process_inbox(db: DBSession) -> None:
    """Procesa mensajes pendientes del inbox usando BotService."""
    from app.services.bot_service import BotService

    try:
        pending = (
            db.query(InboxMessage)
            .filter(InboxMessage.status == "pending")
            .order_by(InboxMessage.created_at.asc())
            .limit(settings.conversation_worker_batch)
            .all()
        )
        for msg in pending:
            msg.status = "processing"
            db.flush()
            try:
                svc = BotService(db)
                svc.process_message(msg)
            except Exception as exc:
                logger.exception("Error procesando mensaje id=%s: %s", msg.id, exc)
                msg.status = "error"
                db.flush()
    except Exception as exc:
        logger.exception("Error en _process_inbox: %s", exc)
    finally:
        db.close()
