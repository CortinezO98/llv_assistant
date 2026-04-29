from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, Text, ForeignKey,
    SmallInteger, BigInteger, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class MessageLog(Base):
    __tablename__ = "llv_message_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("llv_sessions.id"), nullable=True, index=True)
    whatsapp_number = Column(String(20), nullable=False, index=True)
    direction = Column(
        Enum("inbound", "outbound", name="msg_direction_enum"),
        nullable=False,
    )
    content = Column(Text, nullable=True)
    message_type = Column(String(30), default="text")
    meta_message_id = Column(String(100), unique=True, nullable=True)   # deduplicación
    sent_by_bot = Column(SmallInteger, default=1)
    agent_id = Column(Integer, ForeignKey("llv_agents.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relaciones
    session = relationship("Session", back_populates="messages")


class FAQ(Base):
    __tablename__ = "llv_faq"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(80), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(SmallInteger, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlanUsage(Base):
    __tablename__ = "llv_plan_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_month = Column(Date, nullable=False, unique=True, index=True)
    conversation_count = Column(Integer, default=0)
    plan_limit = Column(Integer, default=1500)
    alert_80_sent = Column(SmallInteger, default=0)
    alert_100_sent = Column(SmallInteger, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OutboxMessage(Base):
    """Patrón Outbox transaccional — garantiza entrega de mensajes a WhatsApp."""
    __tablename__ = "llv_outbox"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    whatsapp_number = Column(String(20), nullable=False)
    payload_json = Column(Text, nullable=False)       # JSON del mensaje a enviar
    status = Column(
        Enum("pending", "sent", "failed", name="outbox_status_enum"),
        default="pending",
        index=True,
    )
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)


class InboxMessage(Base):
    """Cola de mensajes entrantes pendientes de procesar."""
    __tablename__ = "llv_inbox"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    whatsapp_number = Column(String(20), nullable=False, index=True)
    profile_name = Column(String(150), nullable=True)
    meta_message_id = Column(String(100), unique=True, nullable=False)
    message_type = Column(String(30), default="text")
    content = Column(Text, nullable=True)
    media_id = Column(String(200), nullable=True)     # para imágenes/documentos
    status = Column(
        Enum("pending", "processing", "done", "error", name="inbox_status_enum"),
        default="pending",
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now(), index=True)
