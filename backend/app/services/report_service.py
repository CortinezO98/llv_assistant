"""
app/services/report_service.py

Servicio de reportería con inteligencia de negocio del flujo conversacional.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import cast, func, String, text, Numeric
from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.analytics import AnalyticsEvent
from app.db.models.appointment import Appointment
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.schemas.reports import ReportFilters

TRM        = 4200
COSTO_CONV = 35

NOMBRES_SERVICIOS = {
    "1": "Pérdida de peso (Semaglutide/Tirzepatide)",
    "2": "Quemadores de grasa",
    "3": "Péptidos (Glow Blend / GHK-Cu)",
    "4": "NAD+",
    "5": "Estética (Botox / Rellenos / Láser)",
    "6": "Limpiezas faciales / Dermatología",
    "7": "Sueros de vitaminas",
    "8": "Rejuvenecimiento vaginal",
    "9": "Morpheus",
}

STEP_LABELS = {
    "menu":               "1. Menú inicial",
    "peso_filtro":        "2. Filtro nuevo/recompra",
    "nuevo_preguntas":    "3A. Preguntas cliente nuevo",
    "recompra_preguntas": "3B. Preguntas recompra",
    "preguntas_generales":"3C. Preguntas generales",
    "intencion_entrega":  "4. Intención de entrega",
    "captura_datos":      "5. Captura de datos",
    "confirmacion":       "6. Confirmación",
    "handoff":            "7. Handoff completado",
    "gemini_libre":       "IA libre",
}

ENTREGA_LABELS = {
    "entrega": "🚚 Entrega a domicilio",
    "recoger": "🏥 Recoger en clínica",
    "cita":    "💉 Cita en clínica",
}


def normalize_dates(filters: ReportFilters) -> tuple[date, date]:
    until = filters.date_to or date.today()
    since = filters.date_from or (until - timedelta(days=filters.days))
    return since, until


def parse_products_csv(products: str | None) -> list[str]:
    if not products:
        return []
    return [p.strip() for p in products.split(',') if p.strip()]


def _sql(db: DBSession, q: str, params: dict):
    """Ejecuta SQL raw con manejo seguro de errores."""
    try:
        return db.execute(text(q), params).fetchall()
    except Exception:
        return []


def _flow_intelligence(db: DBSession, since: date, until: date, menu_opcion: str | None = None) -> dict:
    """Extrae métricas del flujo conversacional del context_json."""
    since_dt = datetime.combine(since, datetime.min.time())
    until_dt = datetime.combine(until, datetime.max.time())
    p = {"s": since_dt, "u": until_dt}

    # ── Ranking de servicios consultados ─────────────────────────────────────
    svc_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.menu_opcion')) op, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.menu_opcion') IS NOT NULL
        GROUP BY op ORDER BY cnt DESC
    """, p)

    svc_conv = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.menu_opcion')) op, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.menu_opcion') IS NOT NULL
        AND (status IN ('in_agent','completed')
             OR JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.flow_step'))='handoff')
        GROUP BY op
    """, p)

    totales = {r[0]: r[1] for r in svc_rows if r[0]}
    conv_map = {r[0]: r[1] for r in svc_conv if r[0]}
    servicios_ranking = []
    for op, tot in sorted(totales.items(), key=lambda x: -x[1]):
        if menu_opcion and op != menu_opcion:
            continue
        conv = conv_map.get(op, 0)
        servicios_ranking.append({
            "opcion": op,
            "servicio": NOMBRES_SERVICIOS.get(op, f"Opción {op}"),
            "total": tot,
            "convertidos": conv,
            "pct_conversion": round(conv / tot * 100, 1) if tot else 0,
        })

    # ── Abandono por paso ─────────────────────────────────────────────────────
    step_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.flow_step')) step, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.flow_step') IS NOT NULL
        GROUP BY step ORDER BY cnt DESC
    """, p)
    abandono = {STEP_LABELS.get(r[0], r[0]): (r[1] or 0) for r in step_rows if r[0]}

    # ── Temperatura de leads ──────────────────────────────────────────────────
    temp_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.lead_temperature')) temp, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.lead_temperature') IS NOT NULL
        GROUP BY temp
    """, p)
    lt = {"caliente": 0, "templado": 0, "frio": 0}
    for r in temp_rows:
        if r[0] in lt:
            lt[r[0]] = r[1] or 0
    total_leads = sum(lt.values())
    lead_temps = {
        k: {"count": v, "pct": round(v / total_leads * 100, 1) if total_leads else 0}
        for k, v in lt.items()
    }

    # ── Tipos de entrega ──────────────────────────────────────────────────────
    ent_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.tipo_entrega')) tipo, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.tipo_entrega') IS NOT NULL
        GROUP BY tipo ORDER BY cnt DESC
    """, p)
    tipos_entrega = {ENTREGA_LABELS.get(r[0], r[0]): (r[1] or 0) for r in ent_rows if r[0]}

    # ── Tipo de cliente (nuevo vs recompra) ───────────────────────────────────
    tipo_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.tipo_cliente')) tipo, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.tipo_cliente') IS NOT NULL
        GROUP BY tipo
    """, p)
    tipo_cliente = {r[0]: (r[1] or 0) for r in tipo_rows if r[0]}

    # ── Objetivos principales ─────────────────────────────────────────────────
    obj_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.respuestas.objetivo_principal')) obj, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.respuestas.objetivo_principal') IS NOT NULL
        GROUP BY obj ORDER BY cnt DESC LIMIT 10
    """, p)
    obj_map = {"1":"Bajar peso","2":"Controlar ansiedad/apetito","3":"Tener más energía","4":"Mejorar hábitos","5":"Otro"}
    objetivos = [{"objetivo": obj_map.get(r[0], r[0]), "count": r[1]} for r in obj_rows if r[0]]

    # ── Condiciones médicas ───────────────────────────────────────────────────
    cond_rows = _sql(db, """
        SELECT JSON_UNQUOTE(JSON_EXTRACT(context_json,'$.respuestas.condicion_medica')) cond, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        AND JSON_EXTRACT(context_json,'$.respuestas.condicion_medica') IS NOT NULL
        GROUP BY cond ORDER BY cnt DESC LIMIT 10
    """, p)
    condiciones = [
        {"condicion": r[0], "count": r[1]}
        for r in cond_rows
        if r[0] and r[0].lower() not in ("ninguna","no","2")
    ]

    # ── Horarios pico ─────────────────────────────────────────────────────────
    hora_rows = _sql(db, """
        SELECT HOUR(created_at) hora, COUNT(*) cnt
        FROM llv_sessions WHERE created_at>=:s AND created_at<=:u
        GROUP BY hora ORDER BY cnt DESC LIMIT 5
    """, p)
    horarios_pico = [{"hora": f"{r[0]:02d}:00", "conversaciones": r[1]} for r in hora_rows]

    return {
        "servicios_ranking":  servicios_ranking,
        "abandono_por_paso":  abandono,
        "lead_temperature":   lead_temps,
        "tipos_entrega":      tipos_entrega,
        "tipo_cliente":       tipo_cliente,
        "objetivos":          objetivos,
        "condiciones":        condiciones,
        "horarios_pico":      horarios_pico,
    }


def build_report_data(db: DBSession, filters: ReportFilters) -> dict:
    since, until = normalize_dates(filters)
    since_dt = datetime.combine(since, datetime.min.time())
    until_dt = datetime.combine(until, datetime.max.time())

    # ── Filtros de sesión ─────────────────────────────────────────────────────
    session_filters = [
        Session.created_at >= since_dt,
        Session.created_at <= until_dt,
    ]
    if filters.channel:
        session_filters.append(Session.channel == filters.channel)
    if filters.session_status:
        session_filters.append(Session.status == filters.session_status)
    if filters.agent_id:
        session_filters.append(Session.assigned_agent_id == filters.agent_id)

    total_sessions = db.query(func.count(Session.id)).filter(*session_filters).scalar() or 0
    unique_users   = db.query(func.count(func.distinct(Session.patient_id))).filter(*session_filters).scalar() or 0
    completed      = db.query(func.count(Session.id)).filter(*session_filters, Session.status == "completed").scalar() or 0
    status_dist    = dict(db.query(Session.status, func.count(Session.id)).filter(*session_filters).group_by(Session.status).all())
    escalated      = db.query(func.count(Session.id)).filter(*session_filters, Session.assigned_agent_id.isnot(None)).scalar() or 0

    agent_loads = (
        db.query(Agent.name, func.count(Session.id).label("count"))
        .join(Session, Session.assigned_agent_id == Agent.id)
        .filter(*session_filters)
        .group_by(Agent.id, Agent.name)
        .order_by(func.count(Session.id).desc())
        .all()
    )

    # ── Satisfacción por agente ───────────────────────────────────────────────
    sat_por_agente = {}
    try:
        sat_rows = (
            db.query(
                AnalyticsEvent.agent_id,
                func.avg(cast(func.json_unquote(func.json_extract(AnalyticsEvent.metadata_json, "$.score")), Numeric(3, 1))).label("avg"),
                func.count(AnalyticsEvent.id).label("total"),
            )
            .filter(
                AnalyticsEvent.event_type == "satisfaction_received",
                AnalyticsEvent.created_at >= since_dt,
                AnalyticsEvent.created_at <= until_dt,
                AnalyticsEvent.agent_id.isnot(None),
            )
            .group_by(AnalyticsEvent.agent_id)
            .all()
        )
        for row in sat_rows:
            ag = db.query(Agent).filter(Agent.id == row.agent_id).first()
            if ag:
                sat_por_agente[ag.name] = {"avg": round(float(row.avg or 0), 2), "total": row.total}
    except Exception:
        pass

    # ── Citas ─────────────────────────────────────────────────────────────────
    appointment_filters = [Appointment.created_at >= since_dt, Appointment.created_at <= until_dt]
    if filters.products:
        appointment_filters.append(Appointment.service.in_(filters.products))
    if filters.location:
        appointment_filters.append(Appointment.clinic == filters.location)

    citas_total     = db.query(func.count(Appointment.id)).filter(*appointment_filters).scalar() or 0
    citas_confirmed = db.query(func.count(Appointment.id)).filter(*appointment_filters, Appointment.status.in_(["confirmed","completed"])).scalar() or 0
    top_services    = (
        db.query(Appointment.service, func.count(Appointment.id).label("count"))
        .filter(*appointment_filters)
        .group_by(Appointment.service)
        .order_by(func.count(Appointment.id).desc())
        .limit(10).all()
    )

    # ── Pagos ─────────────────────────────────────────────────────────────────
    payment_filters = [Payment.created_at >= since_dt, Payment.created_at <= until_dt]
    if filters.products:
        payment_filters.append(Payment.product_service.in_(filters.products))
    if filters.payment_status:
        payment_filters.append(Payment.status == filters.payment_status)

    ventas          = db.query(func.count(Payment.id)).filter(*payment_filters, Payment.status == "verified").scalar() or 0
    ingresos        = db.query(func.sum(Payment.amount)).filter(*payment_filters, Payment.status == "verified").scalar() or 0
    payment_methods = dict(db.query(Payment.payment_method, func.count(Payment.id)).filter(*payment_filters).group_by(Payment.payment_method).all())
    top_unconverted = (
        db.query(Payment.product_service.label("product"), func.count(Payment.id).label("attempts"))
        .filter(*payment_filters, Payment.status != "verified")
        .group_by(Payment.product_service)
        .order_by(func.count(Payment.id).desc())
        .limit(5).all()
    )

    # ── Rentabilidad ──────────────────────────────────────────────────────────
    usd     = float(ingresos or 0)
    cop     = usd * TRM
    costo   = total_sessions * COSTO_CONV
    profit  = cop - costo

    # ── Pacientes ─────────────────────────────────────────────────────────────
    patient_filters = [Patient.created_at >= since_dt, Patient.created_at <= until_dt]
    new_patients = db.query(func.count(Patient.id)).filter(*patient_filters).scalar() or 0
    recurrent    = db.query(func.count(Patient.id)).filter(*patient_filters, Patient.is_recurrent == 1).scalar() or 0

    # ── Canales ───────────────────────────────────────────────────────────────
    channels = dict(db.query(Session.channel, func.count(Session.id)).filter(*session_filters).group_by(Session.channel).all())

    # ── Analytics insights ────────────────────────────────────────────────────
    analytics_filters = [AnalyticsEvent.created_at >= since_dt, AnalyticsEvent.created_at <= until_dt]
    if filters.channel:
        analytics_filters.append(AnalyticsEvent.channel == filters.channel)
    top_interests = (
        db.query(cast(AnalyticsEvent.metadata_json["service"], String).label("interest"), func.count(AnalyticsEvent.id).label("count"))
        .filter(*analytics_filters, AnalyticsEvent.event_type.in_(["appointment_created","payment_sent"]))
        .group_by("interest")
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(5).all()
    )

    # ── Flujo conversacional ──────────────────────────────────────────────────
    menu_opcion = None
    if filters.products and len(filters.products) == 1:
        # Intentar mapear producto a opción del menú
        reverse_map = {v: k for k, v in NOMBRES_SERVICIOS.items()}
        menu_opcion = reverse_map.get(filters.products[0])

    flow = _flow_intelligence(db, since, until, menu_opcion)

    pct_completed = round((completed / total_sessions * 100), 1) if total_sessions else 0
    pct_escalated = round((escalated / total_sessions * 100), 1) if total_sessions else 0
    conv_citas    = round((citas_confirmed / total_sessions * 100), 1) if total_sessions else 0

    return {
        "period": {"since": str(since), "until": str(until)},
        "conversations": {
            "total": total_sessions, "unique_users": unique_users,
            "completed": completed, "pct_completed": pct_completed,
            "status_distribution": status_dist,
        },
        "agents": {
            "escalated": escalated, "pct_escalated": pct_escalated,
            "by_agent": [{"name": a.name, "count": a.count} for a in agent_loads],
            "satisfaction": sat_por_agente,
        },
        "appointments": {
            "total_requested": citas_total, "confirmed": citas_confirmed,
            "conversion_pct": conv_citas,
            "top_services": [{"service": s.service, "count": s.count} for s in top_services],
        },
        "sales": {
            "verified_payments": ventas,
            "total_revenue_usd": usd,
            "total_revenue_cop": round(cop),
            "total_cost_cop":    round(costo),
            "net_profit_cop":    round(profit),
            "margin_pct":        round(profit / cop * 100, 1) if cop else 0,
            "payment_methods":   payment_methods,
        },
        "channels": channels,
        "satisfaction": {
            "by_agent": sat_por_agente,
            "note": "Basado en encuestas post-conversación",
        },
        "patients": {"new_this_period": new_patients, "total_recurrent": recurrent},
        "flow_intelligence": flow,
        "insights": {
            "top_interests": [{"interest": t.interest or "Sin etiqueta", "count": t.count} for t in top_interests],
            "top_unconverted_products": [{"product": t.product, "attempts": t.attempts} for t in top_unconverted],
        },
        "filters": filters.model_dump(),
    }