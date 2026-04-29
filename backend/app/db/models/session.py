from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Session(Base):
    __tablename__ = "llv_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("llv_patients.id"), nullable=False, index=True)
    whatsapp_number = Column(String(20), nullable=False, index=True)
    channel = Column(
        Enum("whatsapp", "instagram", "web", name="session_channel_enum"),
        default="whatsapp",
    )
    status = Column(
        Enum("active", "in_agent", "completed", "closed", name="session_status_enum"),
        default="active",
        index=True,
    )
    assigned_agent_id = Column(Integer, ForeignKey("llv_agents.id"), nullable=True)
    context_json = Column(JSON, nullable=True)        # historial comprimido para Gemini
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    patient = relationship("Patient", back_populates="sessions")
    assigned_agent = relationship("Agent", back_populates="active_sessions")
    messages = relationship("MessageLog", back_populates="session")
    appointments = relationship("Appointment", back_populates="session")
    payments = relationship("Payment", back_populates="session")
