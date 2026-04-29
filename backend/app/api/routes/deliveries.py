"""
app/api/routes/deliveries.py

Gestión de entregas locales (PR) y envíos postales (PR/LATAM/USA).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent, require_admin
from app.db.models.agent import Agent
from app.db.models.delivery import Delivery, Shipment
from app.db.session import get_db

router = APIRouter(prefix="/deliveries", tags=["deliveries"])
logger = logging.getLogger(__name__)


# ── ENTREGAS ──────────────────────────────────────────────────────────────────

@router.get("/")
def list_deliveries(
    status: str | None = None,
    db:    DBSession = Depends(get_db),
    _:     Agent     = Depends(get_current_agent),
):
    q = db.query(Delivery).order_by(Delivery.created_at.desc())
    if status:
        q = q.filter(Delivery.status == status)
    items = q.limit(200).all()
    return [_delivery_dict(d) for d in items]


@router.patch("/{delivery_id}")
def update_delivery(
    delivery_id: int,
    body: dict,
    db:   DBSession = Depends(get_db),
    _:    Agent     = Depends(get_current_agent),
):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")

    allowed = ["status", "assigned_carrier", "delivery_date", "notes", "amount_to_pay"]
    for field, val in body.items():
        if field in allowed:
            setattr(d, field, val)
    db.commit()
    return {"ok": True}


# ── ENVÍOS ────────────────────────────────────────────────────────────────────

@router.get("/shipments")
def list_shipments(
    status: str | None = None,
    db:    DBSession = Depends(get_db),
    _:     Agent     = Depends(get_current_agent),
):
    q = db.query(Shipment).order_by(Shipment.created_at.desc())
    if status:
        q = q.filter(Shipment.status == status)
    items = q.limit(200).all()
    return [_shipment_dict(s) for s in items]


@router.patch("/shipments/{shipment_id}")
def update_shipment(
    shipment_id: int,
    body: dict,
    db:  DBSession = Depends(get_db),
    _:   Agent     = Depends(get_current_agent),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Envío no encontrado")

    allowed = ["status", "tracking_number", "carrier", "shipment_date", "notes", "amount_paid"]
    for field, val in body.items():
        if field in allowed:
            setattr(s, field, val)
    db.commit()
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _delivery_dict(d: Delivery) -> dict:
    return {
        "id": d.id, "patient_name": d.patient_name, "phone": d.phone,
        "service_treatment": d.service_treatment,
        "amount_to_pay": float(d.amount_to_pay) if d.amount_to_pay else None,
        "delivery_town": d.delivery_town, "assigned_carrier": d.assigned_carrier,
        "delivery_date": str(d.delivery_date) if d.delivery_date else None,
        "status": d.status, "notes": d.notes,
        "created_at": str(d.created_at),
    }


def _shipment_dict(s: Shipment) -> dict:
    return {
        "id": s.id, "patient_name": s.patient_name, "phone": s.phone,
        "email": s.email, "postal_address": s.postal_address,
        "city": s.city, "state_province": s.state_province,
        "country": s.country, "zip_code": s.zip_code,
        "service_treatment": s.service_treatment,
        "amount_paid": float(s.amount_paid) if s.amount_paid else None,
        "shipment_date": str(s.shipment_date) if s.shipment_date else None,
        "tracking_number": s.tracking_number, "carrier": s.carrier,
        "status": s.status, "notes": s.notes,
        "created_at": str(s.created_at),
    }
