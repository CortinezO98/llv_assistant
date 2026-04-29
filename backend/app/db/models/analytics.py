"""
app/db/models/analytics.py

Tabla de eventos analíticos — alimenta TODO el dashboard.
Cada acción del bot registra un evento aquí.
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func

from app.db.session import Base


class AnalyticsEvent(Base):
    __tablename__ = "llv_analytics_events"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type   = Column(String(60), nullable=False, index=True)
    # Tipos permitidos:
    # conversation_started   → nueva sesión iniciada
    # message_received       → mensaje entrante procesado
    # faq_resolved           → FAQ respondió sin escalar
    # ai_response            → Gemini generó respuesta
    # agent_handoff          → escalada a agente humano
    # appointment_created    → cita registrada
    # payment_sent           → link/instrucciones de pago enviadas
    # payment_proof_received → cliente envió comprobante
    # payment_completed      → pago verificado por agente
    # session_completed      → sesión marcada como completada
    # satisfaction_received  → cliente calificó la experiencia
    # plan_alert_80          → alerta 80% consumo enviada
    # plan_alert_100         → alerta 100% consumo enviada

    session_id   = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True, index=True)
    patient_id   = Column(Integer, ForeignKey("llv_patients.id"), nullable=True, index=True)
    agent_id     = Column(Integer, ForeignKey("llv_agents.id"),   nullable=True)

    # Datos adicionales del evento (flexible)
    metadata_json = Column(JSON, nullable=True)
    # Ejemplos:
    # faq_resolved   → {"question": "...", "category": "tratamiento", "confidence": 0.95}
    # agent_handoff  → {"reason": "...", "agent_name": "..."}
    # payment_sent   → {"method": "zelle", "product": "Kit Semaglutide", "amount": 150.0}
    # appointment_created → {"service": "Botox", "clinic": "arecibo"}

    channel      = Column(String(20), default="whatsapp")   # whatsapp | instagram | web
    created_at   = Column(DateTime, server_default=func.now(), index=True)
