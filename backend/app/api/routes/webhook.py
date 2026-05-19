"""
app/api/routes/webhook.py  — con rate limiting y signature validation

Cambios vs versión anterior:
    1. Rate limiting: bloquea números con flood (>50 msgs/hora)
    2. Meta signature validation: verifica X-Hub-Signature-256
    3. Request timeout guard: ignora payloads > 10KB
    4. Logging estructurado
"""
import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.core.settings import settings
from app.db.models.messaging import InboxMessage
from app.db.session import SessionLocal, get_db
from app.workers.outbox_worker import flush_outbox
from app.workers.session_cleanup_worker import is_rate_limited

router = APIRouter(tags=["webhook"])
logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 10_240  # 10 KB


# ── Verificación Meta ─────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode:         str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge:    str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.webhook_verify_token:
        logger.info("Webhook verificado por Meta.")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


# ── Recepción de mensajes ─────────────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    # ── 1. Tamaño máximo ──────────────────────────────────────────────────────
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
        logger.warning("Payload demasiado grande | size=%s", content_length)
        raise HTTPException(status_code=413, detail="Payload too large")

    raw_body = await request.body()

    # ── 2. Validación de firma Meta (si está configurado el app_secret) ───────
    app_secret = getattr(settings, "whatsapp_app_secret", "")
    if app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(raw_body, app_secret, signature):
            logger.warning("Firma inválida en webhook | sig=%s", signature[:20])
            raise HTTPException(status_code=403, detail="Invalid signature")

    # ── 3. Parsear JSON ───────────────────────────────────────────────────────
    try:
        import json as _json
        body: dict[str, Any] = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    messages = _extract_messages(body)
    inserted = 0

    for msg_data in messages:
        number  = msg_data.get("number")
        meta_id = msg_data.get("meta_message_id")

        if not number or not meta_id:
            continue

        # ── 4. Rate limiting por número ───────────────────────────────────────
        if is_rate_limited(number, db):
            logger.warning("Rate limit activo | number=%s", number)
            continue

        # ── 5. Deduplicación ──────────────────────────────────────────────────
        existing = (
            db.query(InboxMessage)
            .filter(InboxMessage.meta_message_id == meta_id)
            .first()
        )
        if existing:
            logger.debug("Duplicado ignorado | meta_id=%s", meta_id)
            continue

        db.add(InboxMessage(
            whatsapp_number=msg_data.get("number"),
            profile_name=msg_data.get("profile_name"),
            meta_message_id=meta_id,
            message_type=msg_data.get("type", "text"),
            content=msg_data.get("text"),
            media_id=msg_data.get("media_id"),
            status="pending",
        ))
        inserted += 1

    db.commit()

    if inserted > 0:
        background_tasks.add_task(_process_inbox)

    return {"status": "ok", "received": len(messages), "inserted": inserted}


def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    """Verifica HMAC-SHA256 de Meta."""
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _extract_messages(body: dict) -> list[dict]:
    results: list[dict] = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value    = change.get("value", {})
                contacts = value.get("contacts", [])
                messages = value.get("messages", [])

                contact_map = {
                    c.get("wa_id"): c.get("profile", {}).get("name")
                    for c in contacts if c.get("wa_id")
                }

                for msg in messages:
                    number   = msg.get("from")
                    msg_type = msg.get("type", "text")
                    meta_id  = msg.get("id")

                    data = {
                        "number": number, "meta_message_id": meta_id,
                        "profile_name": contact_map.get(number),
                        "type": msg_type, "text": None, "media_id": None,
                    }

                    if msg_type == "text":
                        data["text"] = msg.get("text", {}).get("body", "")
                    elif msg_type in ("image","document","audio","video","sticker"):
                        data["media_id"] = msg.get(msg_type, {}).get("id")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            data["text"] = interactive.get("button_reply", {}).get("title", "")
                        elif interactive.get("type") == "list_reply":
                            data["text"] = interactive.get("list_reply", {}).get("title", "")

                    results.append(data)
    except Exception as exc:
        logger.exception("Error extrayendo mensajes del webhook: %s", exc)
    return results


def _process_inbox() -> None:
    from app.services.ai_orchestrator import AIOrchestrator
    db = SessionLocal()
    try:
        pending = (
            db.query(InboxMessage)
            .filter(InboxMessage.status == "pending")
            .order_by(InboxMessage.created_at.asc())
            .limit(settings.conversation_worker_batch)
            .all()
        )
        logger.info("Inbox pendientes: %s", len(pending))
        for msg in pending:
            msg.status = "processing"
            db.flush()
            try:
                AIOrchestrator(db).process(msg)
            except Exception as exc:
                logger.exception("Error procesando inbox id=%s: %s", msg.id, exc)
                msg.status = "error"
                db.flush()
        db.commit()
    except Exception as exc:
        logger.exception("Error en _process_inbox: %s", exc)
        db.rollback()
    finally:
        db.close()
    flush_outbox()