"""
app/api/routes/payments.py

Panel operativo de pagos para agentes.
Permite:
- Listar pagos por estado.
- Ver pagos con comprobante recibido.
- Marcar pagos como verificados.
- Rechazar pagos.
- Registrar analítica de pago completado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession, joinedload

from app.api.deps import get_current_agent
from app.db.models.agent import Agent
from app.db.models.payment import Payment
from app.db.models.patient import Patient
from app.db.models.session import Session
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/payments", tags=["payments"])


class VerifyPaymentBody(BaseModel):
    notes: str | None = None


class RejectPaymentBody(BaseModel):
    notes: str | None = None


def _payment_dict(payment: Payment) -> dict:
    patient = payment.patient

    return {
        "id": payment.id,
        "patient_id": payment.patient_id,
        "session_id": payment.session_id,
        "patient_name": patient.full_name if patient else None,
        "whatsapp_number": patient.whatsapp_number if patient else None,
        "product_service": payment.product_service,
        "amount": float(payment.amount) if payment.amount is not None else None,
        "currency": payment.currency,
        "payment_method": payment.payment_method,
        "payment_link_url": payment.payment_link_url,
        "proof_media_id": payment.proof_media_id,
        "status": payment.status,
        "verified_by_agent_id": payment.verified_by_agent_id,
        "verified_by_agent_name": (
            payment.verified_by_agent.name
            if payment.verified_by_agent
            else None
        ),
        "notes": payment.notes,
        "created_at": str(payment.created_at) if payment.created_at else None,
        "updated_at": str(payment.updated_at) if payment.updated_at else None,
    }


@router.get("/")
def list_payments(
    status: Optional[str] = Query(
        default=None,
        description="link_sent | proof_received | verified | rejected",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Buscar por nombre, WhatsApp, producto o método de pago",
    ),
    limit: int = Query(default=200, ge=1, le=500),
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    """
    Lista pagos para el panel operativo.

    Recomendado para agentes:
    - status=proof_received para revisar comprobantes pendientes.
    - status=verified para pagos aprobados.
    - status=rejected para pagos rechazados.
    """
    q = (
        db.query(Payment)
        .options(
            joinedload(Payment.patient),
            joinedload(Payment.verified_by_agent),
        )
        .order_by(Payment.created_at.desc())
    )

    if status:
        q = q.filter(Payment.status == status)

    if search:
        term = f"%{search.strip()}%"
        q = (
            q.join(Patient, Patient.id == Payment.patient_id)
            .filter(
                Patient.full_name.ilike(term)
                | Patient.whatsapp_number.ilike(term)
                | Payment.product_service.ilike(term)
                | Payment.payment_method.ilike(term)
            )
        )

    payments = q.limit(limit).all()
    return [_payment_dict(payment) for payment in payments]


@router.get("/{payment_id}")
def get_payment(
    payment_id: int,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    payment = (
        db.query(Payment)
        .options(
            joinedload(Payment.patient),
            joinedload(Payment.verified_by_agent),
        )
        .filter(Payment.id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    return _payment_dict(payment)


@router.patch("/{payment_id}/verify")
def verify_payment(
    payment_id: int,
    body: VerifyPaymentBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """
    Marca un pago como verificado.

    Este endpoint resuelve el cuello de botella operativo:
    el agente ya no necesita pedir que se actualice manualmente la BD.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if payment.status == "verified":
        return {
            "ok": True,
            "message": "El pago ya estaba verificado",
            "payment": _payment_dict(payment),
        }

    payment.status = "verified"
    payment.verified_by_agent_id = agent.id

    if body.notes:
        current_notes = payment.notes or ""
        payment.notes = (
            f"{current_notes}\n\n"
            f"[{datetime.utcnow().isoformat()}] Verificado por {agent.name}: {body.notes}"
        ).strip()
    else:
        current_notes = payment.notes or ""
        payment.notes = (
            f"{current_notes}\n\n"
            f"[{datetime.utcnow().isoformat()}] Verificado por {agent.name}"
        ).strip()

    analytics = AnalyticsService(db)
    analytics.payment_completed(
        session_id=payment.session_id,
        patient_id=payment.patient_id,
        agent_id=agent.id,
        amount=float(payment.amount) if payment.amount is not None else None,
    )

    db.commit()
    db.refresh(payment)

    return {
        "ok": True,
        "message": "Pago verificado correctamente",
        "payment": _payment_dict(payment),
    }


@router.patch("/{payment_id}/reject")
def reject_payment(
    payment_id: int,
    body: RejectPaymentBody,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """
    Rechaza un pago cuando el comprobante no es válido,
    falta información o el monto no coincide.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    payment.status = "rejected"

    reason = body.notes or "Pago rechazado por validación del agente."
    current_notes = payment.notes or ""
    payment.notes = (
        f"{current_notes}\n\n"
        f"[{datetime.utcnow().isoformat()}] Rechazado por {agent.name}: {reason}"
    ).strip()

    db.commit()
    db.refresh(payment)

    return {
        "ok": True,
        "message": "Pago rechazado correctamente",
        "payment": _payment_dict(payment),
    }