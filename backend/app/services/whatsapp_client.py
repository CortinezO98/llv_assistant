"""
app/services/whatsapp_client.py

Cliente HTTP para enviar mensajes vía Meta WhatsApp Business API (Cloud API).
"""
import logging
from typing import Any

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://graph.facebook.com/v19.0"


class WhatsAppClient:
    def __init__(self):
        self._client = httpx.Client(
            timeout=30,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_token}",
                "Content-Type": "application/json",
            },
        )

    def _url(self) -> str:
        return f"{_BASE_URL}/{settings.whatsapp_phone_number_id}/messages"

    def send_text(self, to: str, text: str) -> dict[str, Any]:
        """Envía un mensaje de texto simple."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }
        return self._post(payload)

    def send_buttons(self, to: str, body: str, buttons: list[dict]) -> dict[str, Any]:
        """Envía mensaje con botones de respuesta rápida (máx 3)."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }
        return self._post(payload)

    def send_list(self, to: str, header: str, body: str, button_label: str, sections: list[dict]) -> dict[str, Any]:
        """Envía un mensaje de lista interactiva."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {"button": button_label, "sections": sections},
            },
        }
        return self._post(payload)

    def mark_as_read(self, message_id: str) -> None:
        """Marca un mensaje como leído."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        self._post(payload)

    def _post(self, payload: dict) -> dict[str, Any]:
        try:
            resp = self._client.post(self._url(), json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "WhatsApp API error: status=%s body=%s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.exception("Error en WhatsAppClient._post: %s", e)
            raise

    def close(self):
        self._client.close()
