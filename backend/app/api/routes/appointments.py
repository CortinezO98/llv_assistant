"""Rutas de citas y pacientes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_agent
from app.db.models.agent import Agent
from app.db.models.appointment import Appointment
from app.db.models.patient import Patient
from app.db.session import get_db

appointments_router = APIRouter(prefix="/appointments", tags=["appointments"])
patients_router = APIRouter(prefix="/patients", tags=["patients"])


@appointments_router.get("/")
def list_appointments(
    status: str | None = None,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    q = db.query(Appointment).order_by(Appointment.created_at.desc())
    if status:
        q = q.filter(Appointment.status == status)
    items = q.limit(100).all()
    return [
        {
            "id": a.id, "full_name": a.full_name, "phone": a.phone,
            "service": a.service, "preferred_date": str(a.preferred_date) if a.preferred_date else None,
            "clinic": a.clinic, "status": a.status, "created_at": str(a.created_at),
        }
        for a in items
    ]


@appointments_router.patch("/{appt_id}/confirm")
def confirm_appointment(
    appt_id: int,
    db: DBSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    from fastapi import HTTPException
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    appt.status = "confirmed"
    appt.confirmed_by_agent_id = agent.id
    db.commit()
    return {"ok": True}


@patients_router.get("/")
def list_patients(
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).limit(200).all()
    return [
        {
            "id": p.id, "whatsapp_number": p.whatsapp_number, "full_name": p.full_name,
            "location_type": p.location_type, "is_recurrent": bool(p.is_recurrent),
            "last_interaction_at": str(p.last_interaction_at) if p.last_interaction_at else None,
        }
        for p in patients
    ]


@patients_router.get("/{patient_id}")
def get_patient(
    patient_id: int,
    db: DBSession = Depends(get_db),
    _: Agent = Depends(get_current_agent),
):
    from fastapi import HTTPException
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.created_at.desc()).all()
    return {
        "id": p.id, "whatsapp_number": p.whatsapp_number, "full_name": p.full_name,
        "birth_date": str(p.birth_date) if p.birth_date else None,
        "email": p.email, "location_type": p.location_type,
        "is_recurrent": bool(p.is_recurrent), "notes": p.notes,
        "appointments": [{"id": a.id, "service": a.service, "status": a.status, "created_at": str(a.created_at)} for a in appointments],
    }
