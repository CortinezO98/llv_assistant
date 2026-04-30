"""
app/services/analytics_service.py

Servicio de analítica — registra eventos en llv_analytics_events.
Usado por AIOrchestrator en cada acción del bot.
"""
import logging
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.db.models.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: DBSession):
        self.db = db

    def track(
        self,
        event_type: str,
        session_id: int | None = None,
        patient_id: int | None = None,
        agent_id:   int | None = None,
        channel:    str = "whatsapp",
        **metadata: Any,
    ) -> None:
        """Registra un evento analítico. No lanza excepciones — nunca bloquea el flujo."""
        try:
            event = AnalyticsEvent(
                event_type    = event_type,
                session_id    = session_id,
                patient_id    = patient_id,
                agent_id      = agent_id,
                channel       = channel,
                metadata_json = metadata if metadata else None,
            )
            self.db.add(event)
            self.db.flush()
            logger.debug("Analytics: %s | session=%s | meta=%s", event_type, session_id, metadata)
        except Exception as exc:
            logger.warning("Analytics track error (non-fatal): %s", exc)

    # ── Helpers semánticos ────────────────────────────────────────────────────

    def conversation_started(self, session_id, patient_id, channel="whatsapp"):
        self.track("conversation_started", session_id=session_id, patient_id=patient_id, channel=channel)

    def message_received(self, session_id, patient_id, message_type="text"):
        self.track("message_received", session_id=session_id, patient_id=patient_id, message_type=message_type)

    def faq_resolved(self, session_id, patient_id, question: str, category: str):
        self.track("faq_resolved", session_id=session_id, patient_id=patient_id, question=question[:200], category=category)

    def ai_response(self, session_id, patient_id, function_called: str | None = None):
        self.track("ai_response", session_id=session_id, patient_id=patient_id, function_called=function_called or "text_response")

    def agent_handoff(self, session_id, patient_id, agent_id, reason: str):
        self.track("agent_handoff", session_id=session_id, patient_id=patient_id, agent_id=agent_id, reason=reason[:200])

    def appointment_created(self, session_id, patient_id, service: str, clinic: str):
        self.track("appointment_created", session_id=session_id, patient_id=patient_id, service=service[:200], clinic=clinic)

    def payment_sent(self, session_id, patient_id, method: str, product: str, amount: float | None = None):
        self.track("payment_sent", session_id=session_id, patient_id=patient_id, method=method, product=product[:200], amount=amount)

    def payment_proof_received(self, session_id, patient_id):
        self.track("payment_proof_received", session_id=session_id, patient_id=patient_id)

    def payment_completed(self, session_id, patient_id, agent_id, amount: float | None = None):
        self.track("payment_completed", session_id=session_id, patient_id=patient_id, agent_id=agent_id, amount=amount)

    def session_completed(self, session_id, patient_id):
        self.track("session_completed", session_id=session_id, patient_id=patient_id)

    def satisfaction_received(self, session_id, patient_id, score: int, agent_id=None):
        self.track("satisfaction_received", session_id=session_id, patient_id=patient_id, agent_id=agent_id, score=score)

    def plan_alert(self, level: int, count: int, limit: int):
        self.track(f"plan_alert_{level}", count=count, limit=limit)