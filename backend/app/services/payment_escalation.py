"""
app/services/payment_escalation.py

Detector de intención de pago para clientes de Puerto Rico.

Cuando el cliente expresa que va a pagar, ya pagó,
quiere enviar evidencia o menciona métodos de pago locales,
la conversación se escala automáticamente a un agente humano.

Casos cubiertos:
- "voy a pagar"
- "ya pagué"
- "te envié el comprobante"
- "pagué por ATH Móvil"
- "hice el zelle"
- "te mandé la captura"
- "a dónde envío el pago"
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.patient import Patient
from app.db.models.session import Session
from app.services.agent_router import AgentRouter
from app.services.analytics_service import AnalyticsService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


PAYMENT_KEYWORDS = [
    # Intención directa de pagar
    "voy a pagar",
    "quiero pagar",
    "deseo pagar",
    "puedo pagar",
    "cómo pago",
    "como pago",
    "dónde pago",
    "donde pago",
    "a dónde pago",
    "a donde pago",
    "me interesa pagar",
    "quiero hacer el pago",
    "voy hacer el pago",
    "voy a hacer el pago",
    "me puedes enviar los datos de pago",
    "me envías los datos de pago",
    "me envias los datos de pago",
    "cuáles son los datos de pago",
    "cuales son los datos de pago",

    # Pago realizado
    "ya pagué",
    "ya pague",
    "pagué",
    "pague",
    "ya hice el pago",
    "hice el pago",
    "acabo de pagar",
    "realicé el pago",
    "realice el pago",
    "envié el pago",
    "envie el pago",
    "mandé el pago",
    "mande el pago",
    "ya lo pagué",
    "ya lo pague",

    # Comprobantes / evidencia
    "comprobante",
    "recibo",
    "evidencia",
    "captura",
    "screenshot",
    "screen shot",
    "foto del pago",
    "imagen del pago",
    "te envié el comprobante",
    "te envie el comprobante",
    "te mandé el comprobante",
    "te mande el comprobante",
    "te envié la captura",
    "te envie la captura",
    "te mandé la captura",
    "te mande la captura",
    "adjunto comprobante",
    "adjunto recibo",
    "aquí está el recibo",
    "aqui esta el recibo",
    "aquí está la evidencia",
    "aqui esta la evidencia",

    # Métodos frecuentes Puerto Rico
    "ath móvil",
    "ath movil",
    "athmovil",
    "ath móvil business",
    "ath movil business",
    "ath business",
    "ath",
    "zelle",
    "paypal",
    "tarjeta",
    "tarjeta de crédito",
    "tarjeta de credito",
    "visa",
    "mastercard",
    "apple pay",
    "cash app",

    # Bancos y términos usados en PR
    "banco popular",
    "popular",
    "oriental bank",
    "oriental",
    "firstbank",
    "first bank",
    "bppr",
    "cooperativa",
    "transferencia",
    "transferí",
    "transferi",
    "depósito",
    "deposito",
    "deposité",
    "deposite",

    # Formas muy comunes al escribir por WhatsApp
    "hice el ath",
    "ya hice el ath",
    "hice zelle",
    "hice el zelle",
    "mandé zelle",
    "mande zelle",
    "envié por zelle",
    "envie por zelle",
    "envié por ath",
    "envie por ath",
    "te envié por ath",
    "te envie por ath",
    "te envié por zelle",
    "te envie por zelle",
    "te mandé por ath",
    "te mande por ath",
    "te mandé por zelle",
    "te mande por zelle",

    # Confirmación de datos de pago
    "número de zelle",
    "numero de zelle",
    "email de zelle",
    "correo de zelle",
    "número de ath",
    "numero de ath",
    "cuenta para pagar",
    "datos de pago",
]


PAYMENT_REGEX_PATTERNS = [
    r"\bya\s+pague\b",
    r"\bya\s+pague\b",
    r"\bvoy\s+a\s+pagar\b",
    r"\bquiero\s+pagar\b",
    r"\bhice\s+el\s+pago\b",
    r"\bcomprobante\b",
    r"\brecibo\b",
    r"\bevidencia\b",
    r"\bcaptura\b",
    r"\bath\s*movil\b",
    r"\bathmovil\b",
    r"\bath\b",
    r"\bzelle\b",
    r"\bpaypal\b",
    r"\btransferencia\b",
    r"\bdeposito\b",
    r"\bbanco\s+popular\b",
    r"\bfirst\s*bank\b",
    r"\boriental\b",
]


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    value = text.lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for original, replacement in replacements.items():
        value = value.replace(original, replacement)

    value = re.sub(r"\s+", " ", value)
    return value


def is_payment_intent(message: str | None) -> bool:
    """
    Retorna True si el mensaje parece estar relacionado con intención,
    confirmación o evidencia de pago.
    """
    text = normalize_text(message)

    if not text:
        return False

    normalized_keywords = [normalize_text(keyword) for keyword in PAYMENT_KEYWORDS]

    if any(keyword in text for keyword in normalized_keywords):
        return True

    for pattern in PAYMENT_REGEX_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def _safe_context(session: Session) -> dict[str, Any]:
    ctx = session.context_json or {}

    if isinstance(ctx, str):
        try:
            ctx = json.loads(ctx)
        except Exception:
            ctx = {}

    if not isinstance(ctx, dict):
        ctx = {}

    return ctx


def escalate_payment_intent(
    db: DBSession,
    session: Session,
    patient: Patient | None,
    message_text: str,
) -> bool:
    """
    Escala automáticamente una conversación cuando detecta intención de pago.

    Retorna:
    - True si escaló o ya estaba escalada.
    - False si no detectó intención de pago.
    """
    if not is_payment_intent(message_text):
        return False

    ctx = _safe_context(session)

    # Si ya está con agente, solo marcamos contexto para que el agente lo vea.
    if session.status == "in_agent" and session.assigned_agent_id:
        ctx["payment_intent_detected"] = True
        ctx["payment_intent_message"] = message_text[:500]
        ctx["payment_intent_at"] = datetime.utcnow().isoformat()
        ctx["escalation_reason"] = ctx.get(
            "escalation_reason",
            "Cliente manifestó intención de pago o envió comprobante.",
        )
        session.context_json = ctx
        db.flush()
        return True

    # En Puerto Rico se debe priorizar agentes de puerto_rico.
    location = "puerto_rico"

    if patient and patient.location_type:
        if patient.location_type == "puerto_rico":
            location = "puerto_rico"
        else:
            location = patient.location_type

    router = AgentRouter(db)
    assigned_agent: Agent | None = router.assign_agent(session, location=location)

    ctx["payment_intent_detected"] = True
    ctx["payment_intent_message"] = message_text[:500]
    ctx["payment_intent_at"] = datetime.utcnow().isoformat()
    ctx["escalation_reason"] = "Cliente manifestó intención de pago o envió comprobante."
    ctx["agent_summary"] = (
        "El cliente está hablando de pago. Revisar si requiere datos para pagar, "
        "validación de comprobante, confirmación de monto o liberación del pedido. "
        "Contexto Puerto Rico: validar ATH Móvil, Zelle, Banco Popular, Oriental, "
        "FirstBank, recibo, captura o evidencia enviada."
    )

    session.context_json = ctx
    session.status = "in_agent"

    analytics = AnalyticsService(db)

    if patient:
        analytics.agent_handoff(
            session_id=session.id,
            patient_id=patient.id,
            agent_id=assigned_agent.id if assigned_agent else None,
            reason="payment_intent_detected",
        )

    if assigned_agent and patient:
        try:
            NotificationService(db).notify_agent_escalation(
                agent_email=assigned_agent.email,
                agent_name=assigned_agent.name,
                patient_name=patient.full_name or "Cliente",
                patient_number=session.whatsapp_number,
                reason="Cliente manifestó intención de pago o envió comprobante.",
                ai_summary=ctx["agent_summary"],
                session_id=session.id,
            )
        except Exception as exc:
            logger.warning("No se pudo notificar escalamiento de pago: %s", exc)

    db.flush()
    return True