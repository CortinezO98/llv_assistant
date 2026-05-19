"""
app/api/routes/dashboard.py
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, text, cast, Numeric
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

COSTO_REAL_POR_CONV_COP = 35
TRM = 4200


def _count_event(db, event_type, since, agent_id=None):
    q = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_type == event_type,
        AnalyticsEvent.created_at >= since,
    )
    if agent_id:
        q = q.filter(AnalyticsEvent.agent_id == agent_id)
    return q.scalar() or 0


def _avg_satisfaction(db, since, agent_id=None):
    """Calcula satisfacción promedio usando cast correcto para SQLAlchemy."""
    try:
        q = db.query(
            func.avg(
                cast(
                    func.json_unquote(
                        func.json_extract(AnalyticsEvent.metadata_json, "$.score")
                    ),
                    Numeric(3, 1)
                )
            )
        ).filter(
            AnalyticsEvent.event_type == "satisfaction_received",
            AnalyticsEvent.created_at >= since,
        )
        if agent_id:
            q = q.filter(AnalyticsEvent.agent_id == agent_id)
        result = q.scalar()
        return round(float(result), 2) if result else None
    except Exception:
        return None


def _get_lead_temp_distribution(db, since):
    try:
        rows = db.execute(text("""
            SELECT
                JSON_UNQUOTE(JSON_EXTRACT(context_json, '$.lead_temperature')) AS temp,
                COUNT(*) as cnt
            FROM llv_sessions
            WHERE created_at >= :since
              AND JSON_EXTRACT(context_json, '$.lead_temperature') IS NOT NULL
            GROUP BY temp
        """), {"since": since}).fetchall()
        dist = {"caliente": 0, "templado": 0, "frio": 0}
        for row in rows:
            temp = row[0] or ""
            if temp in dist:
                dist[temp] = row[1] or 0
        return dist
    except Exception:
        return {"caliente": 0, "templado": 0, "frio": 0}


def _get_flow_abandonment(db, since):
    try:
        rows = db.execute(text("""
            SELECT
                JSON_UNQUOTE(JSON_EXTRACT(context_json, '$.flow_step')) AS step,
                COUNT(*) as cnt
            FROM llv_sessions
            WHERE created_at >= :since
              AND JSON_EXTRACT(context_json, '$.flow_step') IS NOT NULL
              AND status IN ('active', 'completed')
            GROUP BY step
            ORDER BY cnt DESC
        """), {"since": since}).fetchall()

        STEP_LABELS = {
            "menu":               "1. Menú inicial",
            "peso_filtro":        "2. Filtro nuevo/recompra",
            "nuevo_preguntas":    "3A. Preguntas cliente nuevo",
            "recompra_preguntas": "3B. Preguntas recompra",
            "intencion_entrega":  "4. Intención de entrega",
            "captura_datos":      "5. Captura de datos",
            "confirmacion":       "6. Confirmación",
            "handoff":            "7. Handoff completado",
            "gemini_libre":       "IA libre",
        }
        result = {}
        for row in rows:
            step = row[0] or "desconocido"
            result[STEP_LABELS.get(step, step)] = row[1] or 0
        return result
    except Exception:
        return {}


def _get_flow_completion_rate(db, since):
    try:
        total = db.query(func.count(Session.id)).filter(
            Session.created_at >= since
        ).scalar() or 0

        llegaron_preguntas = db.execute(text("""
            SELECT COUNT(*) FROM llv_sessions
            WHERE created_at >= :since
              AND JSON_UNQUOTE(JSON_EXTRACT(context_json, '$.flow_step'))
                  IN ('nuevo_preguntas','recompra_preguntas','intencion_entrega',
                      'captura_datos','confirmacion','handoff','gemini_libre')
        """), {"since": since}).scalar() or 0

        llegaron_handoff = db.execute(text("""
            SELECT COUNT(*) FROM llv_sessions
            WHERE created_at >= :since
              AND (
                JSON_UNQUOTE(JSON_EXTRACT(context_json, '$.flow_step')) = 'handoff'
                OR status IN ('in_agent','completed')
              )
        """), {"since": since}).scalar() or 0

        return {
            "total_iniciaron":    total,
            "llegaron_preguntas": llegaron_preguntas,
            "llegaron_handoff":   llegaron_handoff,
            "pct_preguntas":      round((llegaron_preguntas / total * 100), 1) if total else 0,
            "pct_handoff":        round((llegaron_handoff   / total * 100), 1) if total else 0,
        }
    except Exception:
        return {"total_iniciaron": 0, "llegaron_preguntas": 0, "llegaron_handoff": 0,
                "pct_preguntas": 0, "pct_handoff": 0}


@router.get("/kpis")
def get_kpis(
    days: int = 30,
    db: DBSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    since    = date.today() - timedelta(days=days)
    role     = current_agent.role
    is_super = role == "superadmin"
    is_agent = role == "agent"
    agent_id = current_agent.id if is_agent else None

    conv_started   = _count_event(db, "conversation_started", since, agent_id)
    faq_resolved   = _count_event(db, "faq_resolved",         since, agent_id)
    agent_handoffs = _count_event(db, "agent_handoff",        since, agent_id)
    appt_created   = _count_event(db, "appointment_created",  since, agent_id)
    pay_sent       = _count_event(db, "payment_sent",         since, agent_id)
    pay_completed  = _count_event(db, "payment_completed",    since, agent_id)
    satisfaction   = _count_event(db, "satisfaction_received",since, agent_id)
    avg_sat        = _avg_satisfaction(db, since, agent_id)

    unique_users = db.query(func.count(func.distinct(AnalyticsEvent.patient_id))).filter(
        AnalyticsEvent.event_type == "conversation_started",
        AnalyticsEvent.created_at >= since,
    ).scalar() or 0

    sess_q = db.query(Session).filter(Session.created_at >= since)
    if is_agent:
        sess_q = sess_q.filter(Session.assigned_agent_id == agent_id)

    total_sessions = sess_q.count()
    completed      = sess_q.filter(Session.status == "completed").count()
    pct_completed  = round((completed / total_sessions * 100), 1) if total_sessions else 0

    status_dist = dict(
        db.query(Session.status, func.count(Session.id))
        .filter(Session.created_at >= since)
        .group_by(Session.status).all()
    )

    citas_confirmed = db.query(func.count(Appointment.id)).filter(
        Appointment.created_at >= since,
        Appointment.status.in_(["confirmed", "completed"]),
    ).scalar() or 0

    ingresos = db.query(func.sum(Payment.amount)).filter(
        Payment.created_at >= since,
        Payment.status == "verified",
    ).scalar() or 0

    pct_escalated = round((agent_handoffs / total_sessions * 100), 1) if total_sessions else 0
    conversion    = round((citas_confirmed / total_sessions * 100), 1) if total_sessions else 0

    plan_usage = NotificationService(db).get_current_usage()

    flow_metrics = None
    if not is_agent:
        lead_temp_dist   = _get_lead_temp_distribution(db, since)
        flow_abandonment = _get_flow_abandonment(db, since)
        flow_completion  = _get_flow_completion_rate(db, since)
        flow_metrics = {
            "lead_temperature": {
                "caliente": lead_temp_dist.get("caliente", 0),
                "templado":  lead_temp_dist.get("templado", 0),
                "frio":      lead_temp_dist.get("frio", 0),
                "total":     sum(lead_temp_dist.values()),
            },
            "abandonment_by_step": flow_abandonment,
            "completion":          flow_completion,
        }

    ganancias = None
    if is_super:
        ingreso_cop   = float(ingresos) * TRM
        costo_cop     = total_sessions * COSTO_REAL_POR_CONV_COP
        ganancia_neta = ingreso_cop - costo_cop
        ganancias = {
            "ingreso_cop":    round(ingreso_cop),
            "costo_cop":      round(costo_cop),
            "ganancia_neta":  round(ganancia_neta),
            "margen_pct":     round((ganancia_neta / ingreso_cop * 100), 1) if ingreso_cop else 0,
            "costo_por_conv": COSTO_REAL_POR_CONV_COP,
        }

    return {
        "period_days": days,
        "since":       str(since),
        "role":        role,
        "conversations": {
            "total": total_sessions, "unique_users": unique_users,
            "completed": completed, "pct_completed": pct_completed,
            "status_distribution": status_dist,
        },
        "events": {
            "conversation_started":  conv_started,
            "faq_resolved":          faq_resolved,
            "agent_handoffs":        agent_handoffs,
            "appointments_created":  appt_created,
            "payments_sent":         pay_sent,
            "payments_completed":    pay_completed,
            "satisfaction_received": satisfaction,
        },
        "agents":       {"escalated": agent_handoffs, "pct_escalated": pct_escalated},
        "appointments": {"total_requested": appt_created, "confirmed": citas_confirmed, "conversion_pct": conversion},
        "sales":        {"verified_payments": pay_completed, "total_revenue_usd": float(ingresos)},
        "satisfaction": {"avg_score": avg_sat, "responses": satisfaction},
        "plan_usage":   plan_usage,
        "flow_metrics": flow_metrics,
        "ganancias":    ganancias,
    }


@router.get("/agents-ranking")
def get_agents_ranking(
    db: DBSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    if current_agent.role == "agent":
        a = db.query(Agent).filter(Agent.id == current_agent.id).first()
        return [{"id": a.id, "name": a.name, "role": a.role, "location": a.location,
                 "current_load": a.current_load, "total_closed": a.total_closed}]
    agents = db.query(Agent).filter(Agent.is_active == 1).order_by(Agent.total_closed.desc()).all()
    return [{"id": a.id, "name": a.name, "role": a.role, "location": a.location,
             "current_load": a.current_load, "total_closed": a.total_closed} for a in agents]


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = 20,
    db: DBSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    q = db.query(Session).order_by(Session.updated_at.desc())
    if current_agent.role == "agent":
        q = q.filter(Session.assigned_agent_id == current_agent.id)
    recent = q.limit(limit).all()
    result = []
    for s in recent:
        p = db.query(Patient).filter(Patient.id == s.patient_id).first()
        result.append({
            "session_id": s.id, "patient_name": p.full_name if p else "Desconocido",
            "whatsapp_number": s.whatsapp_number, "status": s.status,
            "channel": s.channel, "updated_at": str(s.updated_at),
        })
    return result


@router.get("/analytics/timeline")
def get_analytics_timeline(
    days: int = 30,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
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
    result: dict = {}
    for row in rows:
        day = str(row.day)
        if day not in result:
            result[day] = {"date": day}
        result[day][row.event_type] = row.count
    return list(result.values())


@router.get("/agents-satisfaction")
def agents_satisfaction(
    days: int = 30,
    db: DBSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    since = datetime.utcnow() - timedelta(days=days)
    try:
        q = (
            db.query(
                AnalyticsEvent.agent_id,
                func.avg(
                    cast(
                        func.json_unquote(
                            func.json_extract(AnalyticsEvent.metadata_json, "$.score")
                        ),
                        Numeric(3, 1)
                    )
                ).label("avg_score"),
                func.count(AnalyticsEvent.id).label("total_surveys"),
            )
            .filter(
                AnalyticsEvent.event_type == "satisfaction_received",
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.agent_id.isnot(None),
            )
            .group_by(AnalyticsEvent.agent_id)
        )
        if current_agent.role == "agent":
            q = q.filter(AnalyticsEvent.agent_id == current_agent.id)

        rows = q.all()
        result = []
        for row in rows:
            agent_obj = db.query(Agent).filter(Agent.id == row.agent_id).first()
            result.append({
                "agent_id":      row.agent_id,
                "agent_name":    agent_obj.name if agent_obj else "Desconocido",
                "avg_score":     round(float(row.avg_score or 0), 2),
                "total_surveys": row.total_surveys,
            })
        result.sort(key=lambda x: x["avg_score"], reverse=True)
        return result
    except Exception:
        return []


@router.get("/flow-metrics")
def get_flow_metrics(
    days: int = 30,
    db: DBSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    if current_agent.role == "agent":
        return {"error": "Sin permisos"}
    since = date.today() - timedelta(days=days)
    return {
        "lead_temperature":    _get_lead_temp_distribution(db, since),
        "abandonment_by_step": _get_flow_abandonment(db, since),
        "completion":          _get_flow_completion_rate(db, since),
    }