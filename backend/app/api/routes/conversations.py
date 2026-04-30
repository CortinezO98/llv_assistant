"""
app/api/routes/conversations.py

Panel de conversaciones en vivo.
- Admins/supervisores ven TODAS las conversaciones
- Agentes ven SOLO las asignadas a ellos
- Agentes pueden responder, cerrar y transferir conversaciones
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_admin
from app.db.models.agent import Agent
from app.db.models.messaging import MessageLog, OutboxMessage
from app.db.models.patient import Patient
from app.db.models.session import Session
from app.db.session import get_db
from app.services.agent_router import AgentRouter
from app.services.analytics_service import AnalyticsService
from app.workers.outbox_worker import flush_outbox

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────
class SendMessageBody(BaseModel):
    message: str


class TransferBody(BaseModel):
    agent_id: int


# ── Listar conversaciones (filtradas por rol) ─────────────────────────────────
@router.get("/")
def list_conversations(
    status: str | None = None,
    limit:  int = 50,
    db:     DBSession = Depends(get_db),
    agent:  Agent     = Depends(get_current_agent),
):
    """
    Admin/Supervisor → todas las conversaciones.
    Agente           → solo las asignadas a él.
    """
    q = db.query(Session).order_by(Session.updated_at.desc())

    # Filtro por rol
    if agent.role == "agent":
        q = q.filter(Session.assigned_agent_id == agent.id)

    # Filtro por estado
    if status:
        q = q.filter(Session.status == status)
    else:
        # Por defecto mostrar activas y en_agente
        q = q.filter(Session.status.in_(["active", "in_agent"]))

    sessions = q.limit(limit).all()

    result = []
    for s in sessions:
        patient = db.query(Patient).filter(Patient.id == s.patient_id).first()
        assigned = db.query(Agent).filter(Agent.id == s.assigned_agent_id).first() if s.assigned_agent_id else None

        # Último mensaje
        last_msg = (
            db.query(MessageLog)
            .filter(MessageLog.session_id == s.id)
            .order_by(MessageLog.created_at.desc())
            .first()
        )

        # Resumen IA si existe
        ctx = s.context_json or {}
        if isinstance(ctx, str):
            try: ctx = json.loads(ctx)
            except: ctx = {}

        result.append({
            "session_id":     s.id,
            "status":         s.status,
            "channel":        s.channel,
            "patient": {
                "id":             patient.id if patient else None,
                "name":           patient.full_name if patient else "Desconocido",
                "whatsapp_number": s.whatsapp_number,
                "location_type":  patient.location_type if patient else "latam",
                "is_recurrent":   bool(patient.is_recurrent) if patient else False,
            },
            "assigned_agent": {
                "id":   assigned.id if assigned else None,
                "name": assigned.name if assigned else None,
            } if assigned else None,
            "last_message":   last_msg.content if last_msg else None,
            "last_message_at": str(last_msg.created_at) if last_msg else None,
            "ai_summary":     ctx.get("agent_summary"),
            "escalation_reason": ctx.get("escalation_reason"),
            "created_at":     str(s.created_at),
            "updated_at":     str(s.updated_at),
        })

    return result


# ── Obtener historial de una conversación ─────────────────────────────────────
@router.get("/{session_id}/messages")
def get_messages(
    session_id: int,
    db:    DBSession = Depends(get_db),
    agent: Agent     = Depends(get_current_agent),
):
    session = _get_session_or_403(session_id, agent, db)

    messages = (
        db.query(MessageLog)
        .filter(MessageLog.session_id == session_id)
        .order_by(MessageLog.created_at.asc())
        .all()
    )

    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
    ctx = session.context_json or {}
    if isinstance(ctx, str):
        try: ctx = json.loads(ctx)
        except: ctx = {}

    return {
        "session_id": session_id,
        "status": session.status,
        "patient": {
            "id":              patient.id if patient else None,
            "name":            patient.full_name if patient else "Desconocido",
            "whatsapp_number": session.whatsapp_number,
            "location_type":   patient.location_type if patient else "latam",
            "is_recurrent":    bool(patient.is_recurrent) if patient else False,
        },
        "ai_summary":        ctx.get("agent_summary"),
        "escalation_reason": ctx.get("escalation_reason"),
        "escalated_at":      ctx.get("escalated_at"),
        "messages": [
            {
                "id":           m.id,
                "direction":    m.direction,
                "content":      m.content,
                "message_type": m.message_type,
                "sent_by_bot":  bool(m.sent_by_bot),
                "agent_id":     m.agent_id,
                "created_at":   str(m.created_at),
            }
            for m in messages
        ],
    }


# ── Agente envía mensaje al cliente ──────────────────────────────────────────
@router.post("/{session_id}/send")
def send_message(
    session_id: int,
    body: SendMessageBody,
    db:   DBSession = Depends(get_db),
    agent: Agent    = Depends(get_current_agent),
):
    """El agente escribe desde el dashboard → se envía por WhatsApp al cliente."""
    session = _get_session_or_403(session_id, agent, db)

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    number = session.whatsapp_number

    # Encolar en outbox → WhatsApp
    db.add(OutboxMessage(
        whatsapp_number = number,
        payload_json    = json.dumps({"to": number, "text": body.message.strip()}),
        status          = "pending",
    ))

    # Registrar en log como mensaje del agente (no del bot)
    db.add(MessageLog(
        session_id      = session_id,
        whatsapp_number = number,
        direction       = "outbound",
        content         = body.message.strip(),
        message_type    = "text",
        sent_by_bot     = 0,
        agent_id        = agent.id,
    ))

    db.commit()

    # Enviar inmediatamente
    flush_outbox()

    logger.info("Agente %s envió mensaje | session=%s", agent.name, session_id)
    return {"ok": True, "sent_by": agent.name}


# ── Agente toma una conversación ──────────────────────────────────────────────
@router.post("/{session_id}/take")
def take_conversation(
    session_id: int,
    db:   DBSession = Depends(get_db),
    agent: Agent    = Depends(get_current_agent),
):
    """El agente toma manualmente una conversación activa."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    old_agent_id = session.assigned_agent_id

    # Liberar al agente anterior si existía
    if old_agent_id and old_agent_id != agent.id:
        old_agent = db.query(Agent).filter(Agent.id == old_agent_id).first()
        if old_agent:
            old_agent.current_load = max(0, (old_agent.current_load or 1) - 1)

    session.assigned_agent_id = agent.id
    session.status = "in_agent"
    agent.current_load = (agent.current_load or 0) + 1

    db.commit()
    return {"ok": True, "assigned_to": agent.name}


# ── Cerrar conversación ───────────────────────────────────────────────────────
@router.post("/{session_id}/close")
def close_conversation(
    session_id: int,
    db:   DBSession = Depends(get_db),
    agent: Agent    = Depends(get_current_agent),
):
    """Cierra la conversación y libera al agente."""
    session = _get_session_or_403(session_id, agent, db)

    session.status = "completed"

    # Liberar carga del agente
    if session.assigned_agent_id:
        assigned = db.query(Agent).filter(Agent.id == session.assigned_agent_id).first()
        if assigned:
            assigned.current_load = max(0, (assigned.current_load or 1) - 1)
            assigned.total_closed = (assigned.total_closed or 0) + 1

    # Analytics
    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
    analytics = AnalyticsService(db)
    analytics.session_completed(session_id, patient.id if patient else None)

    db.commit()

    # ── Enviar encuesta de satisfacción al cliente ──────────────────────────
    if patient and patient.whatsapp_number:
        try:
            survey_msg = (
                "¡Gracias por contactarnos! 💙\n\n"
                "Nos encantaría saber cómo fue tu experiencia con LLV Wellness Clinic.\n\n"
                "Por favor califica nuestro servicio del *1 al 5*:\n"
                "⭐ 1 - Muy malo\n"
                "⭐⭐ 2 - Malo\n"
                "⭐⭐⭐ 3 - Regular\n"
                "⭐⭐⭐⭐ 4 - Bueno\n"
                "⭐⭐⭐⭐⭐ 5 - Excelente\n\n"
                "_Tu opinión nos ayuda a mejorar_ 🙏"
            )
            outbox = OutboxMessage(
                whatsapp_number=patient.whatsapp_number,
                payload_json={"type": "text", "text": {"body": survey_msg}},
                status="pending",
            )
            db.add(outbox)
            db.commit()
            flush_outbox()
        except Exception as e:
            logger.warning("Error enviando encuesta: %s", e)

    logger.info("Conversación cerrada | session=%s | agent=%s", session_id, agent.name)
    return {"ok": True, "closed_by": agent.name}


# ── Transferir a otro agente ──────────────────────────────────────────────────
@router.post("/{session_id}/transfer")
def transfer_conversation(
    session_id: int,
    body: TransferBody,
    db:   DBSession = Depends(get_db),
    agent: Agent    = Depends(get_current_agent),
):
    """Transfiere la conversación a otro agente."""
    session = _get_session_or_403(session_id, agent, db)

    target = db.query(Agent).filter(Agent.id == body.agent_id, Agent.is_active == 1).first()
    if not target:
        raise HTTPException(status_code=404, detail="Agente destino no encontrado")

    # Liberar agente actual
    if session.assigned_agent_id:
        current = db.query(Agent).filter(Agent.id == session.assigned_agent_id).first()
        if current:
            current.current_load = max(0, (current.current_load or 1) - 1)

    # Asignar al nuevo agente
    session.assigned_agent_id = target.id
    session.status = "in_agent"
    target.current_load = (target.current_load or 0) + 1

    db.commit()
    logger.info("Conversación transferida | session=%s | from=%s | to=%s", session_id, agent.name, target.name)
    return {"ok": True, "transferred_to": target.name}


# ── Estadísticas rápidas para el agente ───────────────────────────────────────
@router.get("/stats/me")
def my_stats(
    db:   DBSession = Depends(get_db),
    agent: Agent    = Depends(get_current_agent),
):
    """Estadísticas personales del agente autenticado."""
    active = db.query(Session).filter(
        Session.assigned_agent_id == agent.id,
        Session.status == "in_agent"
    ).count()

    return {
        "agent_id":      agent.id,
        "name":          agent.name,
        "role":          agent.role,
        "current_load":  agent.current_load or 0,
        "total_closed":  agent.total_closed or 0,
        "active_now":    active,
    }


# ── Helper: verificar acceso a la sesión ─────────────────────────────────────
def _get_session_or_403(session_id: int, agent: Agent, db: DBSession) -> Session:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    # Agente solo puede acceder a sus conversaciones asignadas
    if agent.role == "agent" and session.assigned_agent_id != agent.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta conversación")
    return session