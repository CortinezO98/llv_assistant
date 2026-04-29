"""
app/api/routes/dashboard.py

Dashboard con los 8 KPIs — ahora alimentado por llv_analytics_events.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent
from app.db.models.agent import Agent
from app.db.models.analytics import AnalyticsEvent
from app.db.models.appointment import Appointment
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

    # ── Desde analytics_events (fuente de verdad) ─────────────────────────────
    def count_event(event_type: str):
        return db.query(func.count(AnalyticsEvent.id)).filter(
            AnalyticsEvent.event_type == event_type,
            AnalyticsEvent.created_at >= since
        ).scalar() or 0

    conv_started   = count_event("conversation_started")
    faq_resolved   = count_event("faq_resolved")
    agent_handoffs = count_event("agent_handoff")
    appt_created   = count_event("appointment_created")
    pay_sent       = count_event("payment_sent")
    pay_completed  = count_event("payment_completed")
    satisfaction   = count_event("satisfaction_received")

    # Usuarios únicos
    unique_users = db.query(func.count(func.distinct(AnalyticsEvent.patient_id))).filter(
        AnalyticsEvent.event_type == "conversation_started",
        AnalyticsEvent.created_at >= since,
    ).scalar() or 0

    # ── Desde modelos directos ────────────────────────────────────────────────
    total_sessions = db.query(func.count(Session.id)).filter(Session.created_at >= since).scalar() or 0
    completed      = db.query(func.count(Session.id)).filter(Session.created_at >= since, Session.status == "completed").scalar() or 0
    pct_completed  = round((completed / total_sessions * 100), 1) if total_sessions else 0

    status_dist = dict(
        db.query(Session.status, func.count(Session.id))
        .filter(Session.created_at >= since)
        .group_by(Session.status).all()
    )

    citas_confirmed = db.query(func.count(Appointment.id)).filter(
        Appointment.created_at >= since, Appointment.status.in_(["confirmed", "completed"])
    ).scalar() or 0

    ingresos = db.query(func.sum(Payment.amount)).filter(
        Payment.created_at >= since, Payment.status == "verified"
    ).scalar() or 0

    pct_escalated = round((agent_handoffs / total_sessions * 100), 1) if total_sessions else 0
    conversion    = round((citas_confirmed / total_sessions * 100), 1) if total_sessions else 0

    # ── Plan usage ─────────────────────────────────────────────────────────────
    plan_usage = NotificationService(db).get_current_usage()

    return {
        "period_days": days,
        "since": str(since),
        "conversations": {
            "total": total_sessions,
            "unique_users": unique_users,
            "completed": completed,
            "pct_completed": pct_completed,
            "status_distribution": status_dist,
        },
        "events": {
            "conversation_started": conv_started,
            "faq_resolved":         faq_resolved,
            "agent_handoffs":       agent_handoffs,
            "appointments_created": appt_created,
            "payments_sent":        pay_sent,
            "payments_completed":   pay_completed,
            "satisfaction_received": satisfaction,
        },
        "agents": {
            "escalated": agent_handoffs,
            "pct_escalated": pct_escalated,
        },
        "appointments": {
            "total_requested": appt_created,
            "confirmed": citas_confirmed,
            "conversion_pct": conversion,
        },
        "sales": {
            "verified_payments": pay_completed,
            "total_revenue_usd": float(ingresos),
        },
        "channels": {"whatsapp": total_sessions},
        "satisfaction": {"score": None, "responses": satisfaction, "note": "Encuesta pendiente"},
        "plan_usage": plan_usage,
    }


@router.get("/agents-ranking")
def get_agents_ranking(db: DBSession = Depends(get_db), _: Agent = Depends(get_current_agent)):
    agents = db.query(Agent).filter(Agent.is_active == 1).order_by(Agent.total_closed.desc()).all()
    return [
        {"id": a.id, "name": a.name, "role": a.role, "location": a.location,
         "current_load": a.current_load, "total_closed": a.total_closed}
        for a in agents
    ]


@router.get("/recent-activity")
def get_recent_activity(limit: int = 20, db: DBSession = Depends(get_db), _: Agent = Depends(get_current_agent)):
    recent = db.query(Session).order_by(Session.updated_at.desc()).limit(limit).all()
    result = []
    for s in recent:
        p = db.query(Patient).filter(Patient.id == s.patient_id).first()
        result.append({
            "session_id": s.id,
            "patient_name": p.full_name if p else "Desconocido",
            "whatsapp_number": s.whatsapp_number,
            "status": s.status,
            "channel": s.channel,
            "updated_at": str(s.updated_at),
        })
    return result


@router.get("/analytics/timeline")
def get_analytics_timeline(
    days: int = 30,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    """Eventos por día — para gráfica de línea en el dashboard."""
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(
            func.date(AnalyticsEvent.created_at).label("day"),
            AnalyticsEvent.event_type,
            func.count(AnalyticsEvent.id).label("count"),
        )
        .filter(AnalyticsEvent.created_at >= since)
        .group_by(func.date(AnalyticsEvent.created_at), AnalyticsEvent.event_type)
        .order_by(func.date(AnalyticsEvent.created_at))
        .all()
    )
    result: dict[str, dict] = {}
    for row in rows:
        day = str(row.day)
        if day not in result:
            result[day] = {"date": day}
        result[day][row.event_type] = row.count
    return list(result.values())
