from sqlalchemy import Column, Integer, String, DateTime, Enum, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Agent(Base):
    __tablename__ = "llv_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum("agent", "supervisor", "admin", "superadmin", name="agent_role_enum"),
        default="agent",
    )
    location = Column(
        Enum("puerto_rico", "latam", name="agent_location_enum"),
        nullable=False,
        default="latam",
    )
    is_active = Column(SmallInteger, default=1)
    current_load = Column(Integer, default=0)
    total_closed = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    active_sessions = relationship(
        "Session",
        back_populates="assigned_agent",
        foreign_keys="Session.assigned_agent_id",
    )
    verified_payments = relationship(
        "Payment",
        back_populates="verified_by_agent",
        foreign_keys="Payment.verified_by_agent_id",
    )
    confirmed_appointments = relationship(
        "Appointment",
        back_populates="confirmed_by_agent",
        foreign_keys="Appointment.confirmed_by_agent_id",
    )