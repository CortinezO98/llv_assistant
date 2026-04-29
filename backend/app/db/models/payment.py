from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Payment(Base):
    __tablename__ = "llv_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("llv_patients.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True)

    product_service = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(5), default="USD")
    payment_method = Column(
        Enum("link", "ath", "credit_card", "zelle", "paypal", "apple_pay", "other",
             name="payment_method_enum"),
        nullable=False,
        default="zelle",
    )
    payment_link_url = Column(String(500), nullable=True)
    proof_media_id = Column(String(200), nullable=True)   # media_id de WhatsApp del comprobante

    status = Column(
        Enum("link_sent", "proof_received", "verified", "rejected", name="payment_status_enum"),
        default="link_sent",
        index=True,
    )
    verified_by_agent_id = Column(Integer, ForeignKey("llv_agents.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    patient = relationship("Patient", back_populates="payments")
    session = relationship("Session", back_populates="payments")
    verified_by_agent = relationship("Agent", back_populates="verified_payments")
