from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Text, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Patient(Base):
    __tablename__ = "llv_patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    whatsapp_number = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=True)
    birth_date = Column(Date, nullable=True)          # identificador adicional PR
    email = Column(String(200), nullable=True)
    location_type = Column(
        Enum("puerto_rico", "latam", "usa", name="location_type_enum"),
        nullable=False,
        default="latam",
    )
    is_recurrent = Column(SmallInteger, default=0)    # 1 tras primera compra/cita
    last_interaction_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    sessions = relationship("Session", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    payments = relationship("Payment", back_populates="patient")
