"""
app/api/routes/dashboard.py

Dashboard con los 8 KPIs requeridos por el equipo de LRV:
1. Conversaciones iniciadas y usuarios únicos
2. % completadas y puntos de abandono
3. Personas que pasan a asesor
4. Conversión a citas y ventas
5. Ingresos del canal
6. Canales de entrada
7. Satisfacción / feedback
8. Consumo del plan
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent
from app.db.models.agent import Agent
from app.db.models.appointment import Appointment
from app.db.models.messaging import MessageLog, PlanUsage
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.db.session import get_db
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
def get_kpis(
    days: int = 30,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    since = date.today() - timedelta(days=days)

    # 1. Conversaciones y usuarios únicos
    total_sessions = db.query(func.count(Session.id)).filter(Session.created_at >= since).scalar() or 0
    unique_users = db.query(func.count(func.distinct(Session.patient_id))).filter(Session.created_at >= since).scalar() or 0

    # 2. Completadas y abandonadas
    completed = db.query(func.count(Session.id)).filter(Session.created_at >= since, Session.status == "completed").scalar() or 0
    pct_completed = round((completed / total_sessions * 100), 1) if total_sessions else 0

    status_dist = (
        db.query(Session.status, func.count(Session.id))
        .filter(Session.created_at >= since)
        .group_by(Session.status)
        .all()
    )
    abandonment = {s: c for s, c in status_dist}

    # 3. Escaladas a agente
    escalated = db.query(func.count(Session.id)).filter(
        Session.created_at >= since,
        Session.status.in_(["in_agent", "completed"]),
        Session.assigned_agent_id.isnot(None),
    ).scalar() or 0
    pct_escalated = round((escalated / total_sessions * 100), 1) if total_sessions else 0

    # 4. Citas y ventas
    citas_confirmed = db.query(func.count(Appointment.id)).filter(
        Appointment.created_at >= since,
        Appointment.status.in_(["confirmed", "completed"]),
    ).scalar() or 0
    citas_total = db.query(func.count(Appointment.id)).filter(Appointment.created_at >= since).scalar() or 0

    ventas = db.query(func.count(Payment.id)).filter(
        Payment.created_at >= since,
        Payment.status == "verified",
    ).scalar() or 0
    conversion_citas = round((citas_confirmed / total_sessions * 100), 1) if total_sessions else 0

    # 5. Ingresos
    ingresos = db.query(func.sum(Payment.amount)).filter(
        Payment.created_at >= since,
        Payment.status == "verified",
    ).scalar() or 0

    # 6. Canal de entrada (todos WhatsApp por ahora, expandir cuando se agreguen canales)
    canales = {"whatsapp": total_sessions}

    # 7. Satisfacción (placeholder — implementar encuesta post-conversación)
    satisfaction = {"score": None, "responses": 0, "note": "Encuesta pendiente de implementar"}

    # 8. Consumo del plan
    notif_svc = NotificationService(db)
    plan_usage = notif_svc.get_current_usage()

    return {
        "period_days": days,
        "since": str(since),
        "conversations": {
            "total": total_sessions,
            "unique_users": unique_users,
            "completed": completed,
            "pct_completed": pct_completed,
            "status_distribution": abandonment,
        },
        "agents": {
            "escalated": escalated,
            "pct_escalated": pct_escalated,
        },
        "appointments": {
            "total_requested": citas_total,
            "confirmed": citas_confirmed,
            "conversion_pct": conversion_citas,
        },
        "sales": {
            "verified_payments": ventas,
            "total_revenue_usd": float(ingresos),
        },
        "channels": canales,
        "satisfaction": satisfaction,
        "plan_usage": plan_usage,
    }


@router.get("/agents-ranking")
def get_agents_ranking(
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    agents = db.query(Agent).filter(Agent.is_active == 1).order_by(Agent.total_closed.desc()).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "location": a.location,
            "current_load": a.current_load,
            "total_closed": a.total_closed,
        }
        for a in agents
    ]


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = 20,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    recent_sessions = (
        db.query(Session)
        .order_by(Session.updated_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for s in recent_sessions:
        patient = db.query(Patient).filter(Patient.id == s.patient_id).first()
        result.append({
            "session_id": s.id,
            "patient_name": patient.full_name if patient else "Desconocido",
            "whatsapp_number": s.whatsapp_number,
            "status": s.status,
            "channel": s.channel,
            "updated_at": str(s.updated_at),
        })
    return result
