from sqlalchemy import Column, Integer, String, Date, Time, DateTime, Enum, Text, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Appointment(Base):
    __tablename__ = "llv_appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("llv_patients.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True)

    # Datos del agendamiento
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    service = Column(String(200), nullable=False)
    preferred_date = Column(Date, nullable=True)
    preferred_time = Column(Time, nullable=True)
    clinic = Column(
        Enum("arecibo", "bayamon", "latam", "virtual", name="clinic_enum"),
        nullable=False,
        default="latam",
    )
    medical_conditions = Column(Text, nullable=True)

    status = Column(
        Enum("pending_confirm", "confirmed", "cancelled", "completed", name="appt_status_enum"),
        default="pending_confirm",
        index=True,
    )
    vagaro_id = Column(String(100), nullable=True)    # fase 2
    confirmed_by_agent_id = Column(Integer, ForeignKey("llv_agents.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    patient = relationship("Patient", back_populates="appointments")
    session = relationship("Session", back_populates="appointments")
    confirmed_by_agent = relationship("Agent", back_populates="confirmed_appointments")
