from datetime import date, datetime, timedelta
from sqlalchemy import cast, func, String
from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.analytics import AnalyticsEvent
from app.db.models.appointment import Appointment
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.schemas.reports import ReportFilters


def normalize_dates(filters: ReportFilters) -> tuple[date, date]:
    until = filters.date_to or date.today()
    since = filters.date_from or (until - timedelta(days=filters.days))
    return since, until


def parse_products_csv(products: str | None) -> list[str]:
    if not products:
        return []
    return [p.strip() for p in products.split(',') if p.strip()]


def build_report_data(db: DBSession, filters: ReportFilters) -> dict:
    since, until = normalize_dates(filters)
    session_filters = [
        Session.created_at >= datetime.combine(since, datetime.min.time()),
        Session.created_at <= datetime.combine(until, datetime.max.time()),
    ]
    if filters.channel:
        session_filters.append(Session.channel == filters.channel)
    if filters.session_status:
        session_filters.append(Session.status == filters.session_status)
    if filters.agent_id:
        session_filters.append(Session.assigned_agent_id == filters.agent_id)

    total_sessions = db.query(func.count(Session.id)).filter(*session_filters).scalar() or 0
    unique_users = db.query(func.count(func.distinct(Session.patient_id))).filter(*session_filters).scalar() or 0
    completed = db.query(func.count(Session.id)).filter(*session_filters, Session.status == 'completed').scalar() or 0
    status_dist = dict(db.query(Session.status, func.count(Session.id)).filter(*session_filters).group_by(Session.status).all())
    escalated = db.query(func.count(Session.id)).filter(*session_filters, Session.assigned_agent_id.isnot(None)).scalar() or 0

    agent_loads = db.query(Agent.name, func.count(Session.id).label('count')).join(
        Session, Session.assigned_agent_id == Agent.id
    ).filter(*session_filters).group_by(Agent.id, Agent.name).order_by(func.count(Session.id).desc()).all()

    appointment_filters = [
        Appointment.created_at >= datetime.combine(since, datetime.min.time()),
        Appointment.created_at <= datetime.combine(until, datetime.max.time()),
    ]
    if filters.products:
        appointment_filters.append(Appointment.service.in_(filters.products))
    if filters.location:
        appointment_filters.append(Appointment.clinic == filters.location)

    citas_total = db.query(func.count(Appointment.id)).filter(*appointment_filters).scalar() or 0
    citas_confirmed = db.query(func.count(Appointment.id)).filter(*appointment_filters, Appointment.status.in_(['confirmed', 'completed'])).scalar() or 0
    top_services = db.query(Appointment.service, func.count(Appointment.id).label('count')).filter(*appointment_filters).group_by(Appointment.service).order_by(func.count(Appointment.id).desc()).limit(5).all()

    payment_filters = [
        Payment.created_at >= datetime.combine(since, datetime.min.time()),
        Payment.created_at <= datetime.combine(until, datetime.max.time()),
    ]
    if filters.products:
        payment_filters.append(Payment.product_service.in_(filters.products))
    if filters.payment_status:
        payment_filters.append(Payment.status == filters.payment_status)

    ventas = db.query(func.count(Payment.id)).filter(*payment_filters, Payment.status == 'verified').scalar() or 0
    ingresos = db.query(func.sum(Payment.amount)).filter(*payment_filters, Payment.status == 'verified').scalar() or 0
    payment_methods = dict(db.query(Payment.payment_method, func.count(Payment.id)).filter(*payment_filters).group_by(Payment.payment_method).all())
    top_unconverted = db.query(Payment.product_service.label('product'), func.count(Payment.id).label('attempts')).filter(
        *payment_filters, Payment.status != 'verified'
    ).group_by(Payment.product_service).order_by(func.count(Payment.id).desc()).limit(5).all()

    analytics_filters = [
        AnalyticsEvent.created_at >= datetime.combine(since, datetime.min.time()),
        AnalyticsEvent.created_at <= datetime.combine(until, datetime.max.time()),
    ]
    if filters.channel:
        analytics_filters.append(AnalyticsEvent.channel == filters.channel)
    top_interests = db.query(cast(AnalyticsEvent.metadata_json['service'], String).label('interest'), func.count(AnalyticsEvent.id).label('count')).filter(
        *analytics_filters, AnalyticsEvent.event_type.in_(['appointment_created', 'payment_sent'])
    ).group_by('interest').order_by(func.count(AnalyticsEvent.id).desc()).limit(5).all()

    patient_filters = [
        Patient.created_at >= datetime.combine(since, datetime.min.time()),
        Patient.created_at <= datetime.combine(until, datetime.max.time()),
    ]
    new_patients = db.query(func.count(Patient.id)).filter(*patient_filters).scalar() or 0
    recurrent = db.query(func.count(Patient.id)).filter(*patient_filters, Patient.is_recurrent == 1).scalar() or 0

    pct_completed = round((completed / total_sessions * 100), 1) if total_sessions else 0
    pct_escalated = round((escalated / total_sessions * 100), 1) if total_sessions else 0
    conversion_citas = round((citas_confirmed / total_sessions * 100), 1) if total_sessions else 0

    return {
        'period': {'since': str(since), 'until': str(until)},
        'conversations': {'total': total_sessions, 'unique_users': unique_users, 'completed': completed, 'pct_completed': pct_completed, 'status_distribution': status_dist},
        'agents': {'escalated': escalated, 'pct_escalated': pct_escalated, 'by_agent': [{'name': a.name, 'count': a.count} for a in agent_loads]},
        'appointments': {'total_requested': citas_total, 'confirmed': citas_confirmed, 'conversion_pct': conversion_citas, 'top_services': [{'service': s.service, 'count': s.count} for s in top_services]},
        'sales': {'verified_payments': ventas, 'total_revenue_usd': float(ingresos), 'payment_methods': payment_methods},
        'channels': dict(db.query(Session.channel, func.count(Session.id)).filter(*session_filters).group_by(Session.channel).all()),
        'satisfaction': {'score': None, 'responses': 0, 'note': 'Encuesta post-conversación pendiente de implementar'},
        'patients': {'new_this_period': new_patients, 'total_recurrent': recurrent},
        'insights': {
            'top_interests': [{'interest': t.interest or 'Sin etiqueta', 'count': t.count} for t in top_interests],
            'top_unconverted_products': [{'product': t.product, 'attempts': t.attempts} for t in top_unconverted],
        },
        'filters': filters.model_dump(),
    }
