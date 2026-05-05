"""
app/api/routes/conversations.py

Panel de conversaciones en vivo.
- Admins/supervisores ven TODAS las conversaciones
- Agentes ven SOLO las asignadas a ellos
- Agentes pueden responder, cerrar y transferir conversaciones
- Agentes pueden crear citas y entregas desde conversaciones escaladas
"""
import json
import logging
from datetime import date, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_admin
from app.db.models.agent import Agent
from app.db.models.appointment import Appointment
from app.db.models.delivery import Delivery
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


class CreateAppointmentBody(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    service: str
    preferred_date: str | None = None
    preferred_time: str | None = None
    clinic: str = "latam"
    medical_conditions: str | None = None
    notes: str | None = None
    notify_customer: bool = True


class CreateDeliveryBody(BaseModel):
    patient_name: str | None = None
    phone: str | None = None
    service_treatment: str
    amount_to_pay: float | None = None
    delivery_town: str
    assigned_carrier: str | None = None
    delivery_date: str | None = None
    notes: str | None = None
    notify_customer: bool = True


# ── Listar conversaciones (filtradas por rol) ─────────────────────────────────
@router.get("/")
def list_conversations(
    status: str | None = None,
    limit: int = 50,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
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

        assigned = (
            db.query(Agent)
            .filter(Agent.id == s.assigned_agent_id)
            .first()
            if s.assigned_agent_id
            else None
        )

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
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}

        result.append({
            "session_id": s.id,
            "status": s.status,
            "channel": s.channel,
            "patient": {
                "id": patient.id if patient else None,
                "name": patient.full_name if patient and patient.full_name else "Cliente",
                "whatsapp_number": s.whatsapp_number,
                "location_type": patient.location_type if patient else "latam",
                "is_recurrent": bool(patient.is_recurrent) if patient else False,
            },
            "assigned_agent": {
                "id": assigned.id if assigned else None,
                "name": assigned.name if assigned else None,
            } if assigned else None,

            "last_message": last_msg.content if last_msg else None,
            "last_message_at": str(last_msg.created_at) if last_msg else None,
            "last_message_id": last_msg.id if last_msg else None,
            "last_message_direction": last_msg.direction if last_msg else None,
            "last_message_sent_by_bot": bool(last_msg.sent_by_bot) if last_msg else None,

            "ai_summary": ctx.get("agent_summary"),
            "escalation_reason": ctx.get("escalation_reason"),
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        })

    return result


# ── Mensajes de una conversación ──────────────────────────────────────────────
@router.get("/{session_id}/messages")
def get_messages(
    session_id: int,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
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
        try:
            ctx = json.loads(ctx)
        except Exception:
            ctx = {}

    return {
        "session_id": session_id,
        "status": session.status,
        "patient": {
            "id": patient.id if patient else None,
            "name": patient.full_name if patient and patient.full_name else "Cliente",
            "whatsapp_number": session.whatsapp_number,
            "location_type": patient.location_type if patient else "latam",
            "is_recurrent": bool(patient.is_recurrent) if patient else False,
        },
        "ai_summary": ctx.get("agent_summary"),
        "escalation_reason": ctx.get("escalation_reason"),
        "escalated_at": ctx.get("escalated_at"),
        "messages": [
            {
                "id": m.id,
                "direction": m.direction,
                "content": m.content,
                "message_type": m.message_type,
                "sent_by_bot": bool(m.sent_by_bot),
                "agent_id": m.agent_id,
                "created_at": str(m.created_at),
            }
            for m in messages
        ],
    }


# ── Enviar mensaje como agente ────────────────────────────────────────────────
@router.post("/{session_id}/send")
def send_message(
    session_id: int,
    body: SendMessageBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    session = _get_session_or_403(session_id, agent, db)

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    # Registrar en log
    log = MessageLog(
        session_id=session.id,
        whatsapp_number=session.whatsapp_number,
        direction="outbound",
        content=body.message,
        message_type="text",
        sent_by_bot=0,
        agent_id=agent.id,
    )
    db.add(log)

    # Encolar para envío
    db.add(
        OutboxMessage(
            whatsapp_number=session.whatsapp_number,
            payload_json=json.dumps({"to": session.whatsapp_number, "text": body.message}),
            status="pending",
        )
    )

    db.commit()
    flush_outbox()

    return {"ok": True}


# ── Tomar conversación ────────────────────────────────────────────────────────
@router.post("/{session_id}/take")
def take_conversation(
    session_id: int,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    session.assigned_agent_id = agent.id
    session.status = "in_agent"
    agent.current_load = (agent.current_load or 0) + 1

    db.commit()

    return {"ok": True}


# ── Cerrar conversación ───────────────────────────────────────────────────────
@router.post("/{session_id}/close")
def close_conversation(
    session_id: int,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    session = _get_session_or_403(session_id, agent, db)

    router_svc = AgentRouter(db)
    router_svc.release_agent(session)

    session.status = "completed"

    analytics = AnalyticsService(db)
    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
    if patient:
        analytics.session_completed(session.id, patient.id)

    db.commit()

    return {"ok": True}


# ── Transferir conversación ───────────────────────────────────────────────────
@router.post("/{session_id}/transfer")
def transfer_conversation(
    session_id: int,
    body: TransferBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(require_admin),
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    target_agent = db.query(Agent).filter(Agent.id == body.agent_id, Agent.is_active == 1).first()
    if not target_agent:
        raise HTTPException(status_code=404, detail="Agente destino no encontrado")

    # Liberar agente anterior
    if session.assigned_agent_id:
        prev_agent = db.query(Agent).filter(Agent.id == session.assigned_agent_id).first()
        if prev_agent:
            prev_agent.current_load = max(0, (prev_agent.current_load or 1) - 1)

    session.assigned_agent_id = target_agent.id
    target_agent.current_load = (target_agent.current_load or 0) + 1

    db.commit()

    return {"ok": True}


# ── Estadísticas del agente ───────────────────────────────────────────────────
@router.get("/my-stats")
def my_stats(
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Estadísticas personales del agente autenticado."""
    active = (
        db.query(Session)
        .filter(
            Session.assigned_agent_id == agent.id,
            Session.status == "in_agent",
        )
        .count()
    )

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "current_load": agent.current_load or 0,
        "total_closed": agent.total_closed or 0,
        "active_now": active,
    }


# ── Crear cita desde conversación ────────────────────────────────────────────
@router.post("/{session_id}/appointment")
def create_appointment_from_conversation(
    session_id: int,
    body: CreateAppointmentBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """
    Permite que un agente cree una cita manualmente desde una conversación
    ya escalada o asignada a agente.
    Envía confirmación por WhatsApp al cliente si notify_customer=True.
    """
    session = _get_session_or_403(session_id, agent, db)
    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    full_name = (body.full_name or patient.full_name or "Cliente").strip()
    phone = (body.phone or patient.whatsapp_number or session.whatsapp_number).strip()

    appt = Appointment(
        patient_id=patient.id,
        session_id=session.id,
        full_name=full_name,
        phone=phone,
        service=body.service.strip(),
        clinic=body.clinic,
        medical_conditions=body.medical_conditions,
        status="pending_confirm",
        confirmed_by_agent_id=agent.id,
        notes=body.notes,
    )

    if body.preferred_date:
        try:
            appt.preferred_date = date.fromisoformat(body.preferred_date)
        except Exception:
            raise HTTPException(status_code=400, detail="preferred_date debe ser YYYY-MM-DD")

    if body.preferred_time:
        try:
            appt.preferred_time = time.fromisoformat(body.preferred_time)
        except Exception:
            raise HTTPException(status_code=400, detail="preferred_time debe ser HH:MM")

    db.add(appt)

    # Actualizar nombre real del paciente si el agente lo captura
    if body.full_name and body.full_name.strip():
        patient.full_name = body.full_name.strip()

    patient.is_recurrent = 1

    analytics = AnalyticsService(db)
    analytics.appointment_created(
        session.id,
        patient.id,
        body.service.strip(),
        body.clinic,
    )

    confirmation_msg = (
        f"✅ Tu solicitud de cita fue registrada.\n\n"
        f"📋 *Resumen:*\n"
        f"• Nombre: {full_name}\n"
        f"• Servicio: {body.service.strip()}\n"
        f"• Clínica: {body.clinic.replace('_', ' ').title()}\n"
        + (f"• Fecha preferida: {appt.preferred_date}\n" if appt.preferred_date else "")
        + (f"• Hora preferida: {appt.preferred_time}\n" if appt.preferred_time else "")
        + f"\nNuestro equipo confirmará la disponibilidad contigo. 💙"
    )

    if body.notify_customer:
        db.add(
            OutboxMessage(
                whatsapp_number=session.whatsapp_number,
                payload_json=json.dumps({
                    "to": session.whatsapp_number,
                    "text": confirmation_msg,
                }),
                status="pending",
            )
        )

        db.add(
            MessageLog(
                session_id=session.id,
                whatsapp_number=session.whatsapp_number,
                direction="outbound",
                content=confirmation_msg,
                message_type="text",
                sent_by_bot=0,
                agent_id=agent.id,
            )
        )

    db.commit()

    if body.notify_customer:
        flush_outbox()

    return {
        "ok": True,
        "appointment_id": appt.id,
        "message": "Cita creada correctamente",
    }


# ── Crear entrega desde conversación ─────────────────────────────────────────
@router.post("/{session_id}/delivery")
def create_delivery_from_conversation(
    session_id: int,
    body: CreateDeliveryBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """
    Permite que un agente cree una entrega manualmente desde una conversación
    ya escalada o asignada a agente.
    Envía confirmación por WhatsApp al cliente si notify_customer=True.
    """
    session = _get_session_or_403(session_id, agent, db)
    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    patient_name = (body.patient_name or patient.full_name or "Cliente").strip()
    phone = (body.phone or patient.whatsapp_number or session.whatsapp_number).strip()

    delivery = Delivery(
        patient_id=patient.id,
        session_id=session.id,
        patient_name=patient_name,
        phone=phone,
        service_treatment=body.service_treatment.strip(),
        amount_to_pay=body.amount_to_pay,
        delivery_town=body.delivery_town.strip(),
        assigned_carrier=body.assigned_carrier,
        notes=body.notes,
        status="pending",
    )

    if body.delivery_date:
        try:
            delivery.delivery_date = date.fromisoformat(body.delivery_date)
        except Exception:
            raise HTTPException(status_code=400, detail="delivery_date debe ser YYYY-MM-DD")

    db.add(delivery)

    # Actualizar nombre real del paciente si el agente lo captura
    if body.patient_name and body.patient_name.strip():
        patient.full_name = body.patient_name.strip()

    patient.is_recurrent = 1

    analytics = AnalyticsService(db)
    analytics.track(
        "delivery_created",
        session_id=session.id,
        patient_id=patient.id,
        agent_id=agent.id,
        service=body.service_treatment.strip(),
        town=body.delivery_town.strip(),
    )

    confirmation_msg = (
        f"✅ Tu entrega fue registrada correctamente.\n\n"
        f"📦 *Resumen:*\n"
        f"• Nombre: {patient_name}\n"
        f"• Producto/Tratamiento: {body.service_treatment.strip()}\n"
        f"• Pueblo de entrega: {body.delivery_town.strip()}\n"
        + (f"• Monto a pagar: ${body.amount_to_pay} USD\n" if body.amount_to_pay else "")
        + (f"• Fecha estimada: {delivery.delivery_date}\n" if delivery.delivery_date else "")
        + (f"• Carrero asignado: {body.assigned_carrier}\n" if body.assigned_carrier else "")
        + f"\nNuestro equipo coordinará los detalles contigo. 💙"
    )

    if body.notify_customer:
        db.add(
            OutboxMessage(
                whatsapp_number=session.whatsapp_number,
                payload_json=json.dumps({
                    "to": session.whatsapp_number,
                    "text": confirmation_msg,
                }),
                status="pending",
            )
        )

        db.add(
            MessageLog(
                session_id=session.id,
                whatsapp_number=session.whatsapp_number,
                direction="outbound",
                content=confirmation_msg,
                message_type="text",
                sent_by_bot=0,
                agent_id=agent.id,
            )
        )

    db.commit()

    if body.notify_customer:
        flush_outbox()

    return {
        "ok": True,
        "delivery_id": delivery.id,
        "message": "Entrega creada correctamente",
    }


# ── Helper: verificar acceso a la sesión ─────────────────────────────────────
def _get_session_or_403(session_id: int, agent: Agent, db: DBSession) -> Session:
    session = db.query(Session).filter(Session.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Agente solo puede acceder a sus conversaciones asignadas
    if agent.role == "agent" and session.assigned_agent_id != agent.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta conversación",
        )

    return session