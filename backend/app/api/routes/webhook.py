"""
app/api/routes/webhook.py

Webhook seguro de WhatsApp Cloud API.

Responsabilidades:
- Verificación GET del webhook con Meta.
- Recepción POST de mensajes.
- Validación opcional de firma X-Hub-Signature-256.
- Límite de tamaño del payload.
- Rate limiting por número.
- Deduplicación por meta_message_id.
- Inserción en llv_inbox.
- Broadcast realtime para dashboard.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.core.settings import settings
from app.db.models.messaging import InboxMessage
from app.db.session import get_db
from app.services.realtime_manager import realtime_manager
from app.workers.session_cleanup_worker import is_rate_limited

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)

# 256 KB es más seguro que 10 KB porque Meta puede enviar payloads con metadata de media.
MAX_PAYLOAD_BYTES = 256_000


@router.get("")
@router.get("/")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    Verificación exigida por Meta para registrar el webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.webhook_verify_token:
        logger.info("Webhook verificado correctamente por Meta.")

        if hub_challenge and hub_challenge.isdigit():
            return int(hub_challenge)

        return hub_challenge

    logger.warning("Intento de verificación fallido en webhook.")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("")
@router.post("/")
async def receive_webhook(
    request: Request,
    db: DBSession = Depends(get_db),
):
    """
    Recibe eventos de WhatsApp Cloud API.

    Este endpoint solo encola mensajes en llv_inbox.
    El procesamiento conversacional debe hacerlo el worker/servicio del bot.
    """

    # 1. Validar tamaño del payload
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            if int(content_length) > MAX_PAYLOAD_BYTES:
                logger.warning("Payload demasiado grande | size=%s", content_length)
                raise HTTPException(status_code=413, detail="Payload demasiado grande")
        except ValueError:
            logger.warning("Content-Length inválido | value=%s", content_length)

    raw_body = await request.body()

    if len(raw_body) > MAX_PAYLOAD_BYTES:
        logger.warning("Payload excede tamaño permitido | size=%s", len(raw_body))
        raise HTTPException(status_code=413, detail="Payload demasiado grande")

    # 2. Validar firma Meta si está configurado WHATSAPP_APP_SECRET
    app_secret = getattr(settings, "whatsapp_app_secret", "")

    if app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not _verify_signature(raw_body, app_secret, signature):
            logger.warning("Firma inválida en webhook | signature=%s", signature[:30])
            raise HTTPException(status_code=403, detail="Firma inválida")

    # 3. Parsear JSON
    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except Exception:
        logger.warning("Webhook recibió JSON inválido.")
        raise HTTPException(status_code=400, detail="JSON inválido")

    try:
        messages = _extract_messages(payload)

        created = 0
        duplicated = 0
        rate_limited = 0

        for msg_data in messages:
            whatsapp_number = msg_data.get("whatsapp_number")
            meta_message_id = msg_data.get("meta_message_id")

            if not whatsapp_number or not meta_message_id:
                continue

            # 4. Rate limiting por número
            if is_rate_limited(whatsapp_number, db):
                rate_limited += 1
                logger.warning(
                    "Mensaje ignorado por rate limit | number=%s | meta_id=%s",
                    whatsapp_number,
                    meta_message_id,
                )
                continue

            # 5. Deduplicación
            existing = (
                db.query(InboxMessage)
                .filter(InboxMessage.meta_message_id == meta_message_id)
                .first()
            )

            if existing:
                duplicated += 1
                logger.debug("Mensaje duplicado ignorado | meta_id=%s", meta_message_id)
                continue

            inbox = InboxMessage(
                whatsapp_number=whatsapp_number,
                profile_name=msg_data.get("profile_name"),
                meta_message_id=meta_message_id,
                message_type=msg_data.get("message_type", "text"),
                content=msg_data.get("content"),
                media_id=msg_data.get("media_id"),
                status="pending",
            )

            db.add(inbox)
            created += 1

            # 6. Notificar en tiempo real al dashboard
            realtime_manager.broadcast_sync(
                {
                    "type": "inbox_message_received",
                    "whatsapp_number": whatsapp_number,
                    "profile_name": msg_data.get("profile_name"),
                    "message_type": msg_data.get("message_type", "text"),
                    "content": msg_data.get("content"),
                    "media_id": msg_data.get("media_id"),
                    "meta_message_id": meta_message_id,
                }
            )

        db.commit()

        logger.info(
            "Webhook procesado | received=%s | created=%s | duplicated=%s | rate_limited=%s",
            len(messages),
            created,
            duplicated,
            rate_limited,
        )

        return {
            "ok": True,
            "received": len(messages),
            "created": created,
            "duplicated": duplicated,
            "rate_limited": rate_limited,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Error procesando webhook: %s", exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error procesando webhook")


def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    """
    Verifica la firma HMAC-SHA256 enviada por Meta.

    Header esperado:
    X-Hub-Signature-256: sha256=<hash>
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extrae mensajes útiles desde el payload de WhatsApp Cloud API.
    Soporta:
    - text
    - button
    - interactive button_reply
    - interactive list_reply
    - image/document/audio/video/sticker
    """
    results: list[dict[str, Any]] = []

    try:
        entries = payload.get("entry", [])

        for entry in entries:
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                messages = value.get("messages", [])

                contact_map = {
                    contact.get("wa_id"): contact.get("profile", {}).get("name")
                    for contact in contacts
                    if contact.get("wa_id")
                }

                fallback_profile_name = None

                if contacts:
                    fallback_profile_name = (
                        contacts[0]
                        .get("profile", {})
                        .get("name")
                    )

                for message in messages:
                    whatsapp_number = message.get("from")
                    meta_message_id = message.get("id")
                    message_type = message.get("type", "text")

                    content = None
                    media_id = None

                    if message_type == "text":
                        content = (
                            message
                            .get("text", {})
                            .get("body", "")
                        )

                    elif message_type == "button":
                        content = (
                            message
                            .get("button", {})
                            .get("text", "")
                        )

                    elif message_type == "interactive":
                        interactive = message.get("interactive", {})
                        interactive_type = interactive.get("type")

                        if interactive_type == "button_reply":
                            content = (
                                interactive
                                .get("button_reply", {})
                                .get("title", "")
                            )

                        elif interactive_type == "list_reply":
                            content = (
                                interactive
                                .get("list_reply", {})
                                .get("title", "")
                            )

                        else:
                            content = "[interactive]"

                    elif message_type in ("image", "document", "audio", "video", "sticker"):
                        media = message.get(message_type, {})
                        media_id = media.get("id")
                        content = media.get("caption") or f"[{message_type}]"

                    else:
                        content = f"[{message_type}]"

                    results.append(
                        {
                            "whatsapp_number": whatsapp_number,
                            "profile_name": contact_map.get(whatsapp_number) or fallback_profile_name,
                            "meta_message_id": meta_message_id,
                            "message_type": message_type,
                            "content": content,
                            "media_id": media_id,
                        }
                    )

    except Exception as exc:
        logger.exception("Error extrayendo mensajes del webhook: %s", exc)

    return results