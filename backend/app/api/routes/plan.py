"""
app/api/routes/plan.py

Control del plan mensual — solo accesible por superadmin para:
- Renovar plan mensual cuando el cliente paga
- Agregar conversaciones adicionales
- Activar / desactivar el servicio
- Ver consumo real del mes
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_superadmin
from app.db.models.agent import Agent
from app.db.models.messaging import PlanUsage
from app.db.session import get_db
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/plan", tags=["plan"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RenewPlanBody(BaseModel):
    plan_limit: int = 1500
    payment_reference: str | None = None
    notes: str | None = None


class AddConversationsBody(BaseModel):
    extra_conversations: int
    payment_reference: str | None = None
    notes: str | None = None


class ToggleServiceBody(BaseModel):
    service_active: bool
    notes: str | None = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_current_usage_row(db: DBSession) -> PlanUsage:
    today = date.today()
    period = date(today.year, today.month, 1)

    usage = (
        db.query(PlanUsage)
        .filter(PlanUsage.period_month == period)
        .first()
    )

    if not usage:
        usage = PlanUsage(
            period_month=period,
            conversation_count=0,
            plan_limit=1500,
            extra_conversations=0,
            service_active=1,
        )
        db.add(usage)
        db.flush()

    return usage


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/usage")
def get_plan_usage(
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    """Uso del plan actual — visible para todos los roles."""
    svc = NotificationService(db)
    return svc.get_current_usage()


@router.post("/renew")
def renew_monthly_plan(
    body: RenewPlanBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(require_superadmin),
):
    """
    Renueva el plan mensual cuando el cliente realiza el pago.
    - Resetea conversaciones extra a 0
    - Activa el servicio
    - Registra referencia de pago y fecha de vencimiento
    - Solo superadmin puede ejecutar esta acción
    """
    usage = _get_current_usage_row(db)

    now = datetime.utcnow()
    usage.plan_limit = body.plan_limit
    usage.extra_conversations = 0
    usage.service_active = 1
    usage.paid_at = now
    usage.expires_at = now + timedelta(days=30)
    usage.last_payment_reference = body.payment_reference
    usage.notes = body.notes
    usage.updated_by_agent_id = agent.id
    usage.alert_80_sent = 0
    usage.alert_100_sent = 0

    db.commit()

    return {
        "ok": True,
        "message": "Plan mensual renovado correctamente",
        "plan_limit": usage.plan_limit,
        "extra_conversations": usage.extra_conversations,
        "service_active": bool(usage.service_active),
        "paid_at": str(usage.paid_at),
        "expires_at": str(usage.expires_at),
    }


@router.post("/add-conversations")
def add_extra_conversations(
    body: AddConversationsBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(require_superadmin),
):
    """
    Agrega conversaciones adicionales al plan actual.
    Útil cuando el cliente compra un paquete extra sin renovar el mes completo.
    Solo superadmin puede ejecutar esta acción.
    """
    if body.extra_conversations <= 0:
        raise HTTPException(
            status_code=400,
            detail="extra_conversations debe ser mayor que 0",
        )

    usage = _get_current_usage_row(db)

    usage.extra_conversations = (usage.extra_conversations or 0) + body.extra_conversations
    usage.last_payment_reference = body.payment_reference
    usage.notes = body.notes
    usage.updated_by_agent_id = agent.id

    # Si agrega conversaciones, reactiva el servicio automáticamente
    usage.service_active = 1

    db.commit()

    return {
        "ok": True,
        "message": f"Se agregaron {body.extra_conversations} conversaciones adicionales",
        "extra_conversations": usage.extra_conversations,
        "total_limit": (usage.plan_limit or 0) + (usage.extra_conversations or 0),
        "service_active": bool(usage.service_active),
    }


@router.post("/toggle-service")
def toggle_service(
    body: ToggleServiceBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(require_superadmin),
):
    """
    Activa o desactiva el servicio del bot.
    Cuando está inactivo, el bot no responde mensajes.
    El dashboard sigue accesible para administración.
    Solo superadmin puede ejecutar esta acción.
    """
    usage = _get_current_usage_row(db)

    usage.service_active = 1 if body.service_active else 0
    usage.notes = body.notes
    usage.updated_by_agent_id = agent.id

    db.commit()

    return {
        "ok": True,
        "message": f"Servicio {'activado' if body.service_active else 'desactivado'} correctamente",
        "service_active": bool(usage.service_active),
    }