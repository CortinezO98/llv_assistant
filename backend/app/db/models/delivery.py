"""
app/db/models/delivery.py

Modelos para entregas y envíos de productos LLV.
Entrega  → cliente recibe en Puerto Rico (carrero/enfermero)
Envío    → cliente recibe por correo postal (PR, LATAM, USA)
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey, Numeric, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Delivery(Base):
    """Entregas locales en Puerto Rico — carrero/enfermero asignado."""
    __tablename__ = "llv_deliveries"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    patient_id           = Column(Integer, ForeignKey("llv_patients.id"), nullable=True, index=True)
    session_id           = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True)

    # Datos del paciente
    patient_name         = Column(String(150), nullable=False)
    phone                = Column(String(20),  nullable=False)

    # Servicio/tratamiento
    service_treatment    = Column(String(300), nullable=False)
    amount_to_pay        = Column(Numeric(12, 2), nullable=True)
    currency             = Column(String(5), default="USD")

    # Logística de entrega
    delivery_town        = Column(String(100), nullable=False)   # Pueblo de entrega
    assigned_carrier     = Column(String(150), nullable=True)    # Carrero/Enfermero asignado
    delivery_date        = Column(Date, nullable=True)

    status = Column(
        Enum("pending", "assigned", "in_transit", "delivered", "cancelled", name="delivery_status_enum"),
        default="pending",
        index=True,
    )
    notes                = Column(Text, nullable=True)
    created_at           = Column(DateTime, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient", foreign_keys=[patient_id])


class Shipment(Base):
    """Envíos postales — PR, LATAM, USA."""
    __tablename__ = "llv_shipments"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    patient_id           = Column(Integer, ForeignKey("llv_patients.id"), nullable=True, index=True)
    session_id           = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True)

    # Datos del paciente
    patient_name         = Column(String(150), nullable=False)
    phone                = Column(String(20),  nullable=False)
    email                = Column(String(200), nullable=True)

    # Dirección postal
    postal_address       = Column(Text, nullable=False)
    city                 = Column(String(100), nullable=True)
    state_province       = Column(String(100), nullable=True)
    country              = Column(String(60),  default="Puerto Rico")
    zip_code             = Column(String(20),  nullable=True)

    # Servicio/tratamiento
    service_treatment    = Column(String(300), nullable=False)
    amount_paid          = Column(Numeric(12, 2), nullable=True)
    currency             = Column(String(5), default="USD")

    # Logística de envío
    shipment_date        = Column(Date, nullable=True)
    tracking_number      = Column(String(100), nullable=True)
    carrier              = Column(String(60), nullable=True)  # USPS, UPS, FedEx, etc.

    status = Column(
        Enum("pending", "processing", "shipped", "in_transit", "delivered", "returned", name="shipment_status_enum"),
        default="pending",
        index=True,
    )
    notes                = Column(Text, nullable=True)
    created_at           = Column(DateTime, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient", foreign_keys=[patient_id])
