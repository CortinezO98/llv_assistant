"""
app/workers/session_cleanup_worker.py

Worker de limpieza de sesiones:
  1. Expira sesiones activas sin actividad > 48h → status = completed
  2. Expira sesiones in_agent sin actividad > 72h → status = completed
  3. Rate limiting básico: bloquea números con > 50 mensajes en 1h
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func

from app.db.models.messaging import InboxMessage, MessageLog
from app.db.models.session import Session
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

ACTIVE_EXPIRE_HOURS   = 48
IN_AGENT_EXPIRE_HOURS = 72
RATE_LIMIT_MESSAGES   = 50   # mensajes por hora por número
RATE_LIMIT_WINDOW_H   = 1

# Números bloqueados en memoria (se limpia al reiniciar el worker)
_blocked_numbers: dict[str, datetime] = {}
BLOCK_DURATION_MIN = 60


def run_cleanup_worker() -> dict:
    """Limpia sesiones expiradas."""
    db = SessionLocal()
    now = datetime.utcnow()
    expired_active   = 0
    expired_in_agent = 0

    try:
        # ── 1. Expirar sesiones activas > 48h ────────────────────────────────
        cutoff_active = now - timedelta(hours=ACTIVE_EXPIRE_HOURS)
        stale_active = (
            db.query(Session)
            .filter(Session.status == "active", Session.updated_at <= cutoff_active)
            .all()
        )
        for s in stale_active:
            s.status = "completed"
            ctx = s.context_json or {}
            if isinstance(ctx, str):
                try: ctx = json.loads(ctx)
                except Exception: ctx = {}
            ctx["closed_reason"] = "inactividad_48h"
            s.context_json = ctx
            expired_active += 1

        # ── 2. Expirar sesiones in_agent > 72h ───────────────────────────────
        cutoff_agent = now - timedelta(hours=IN_AGENT_EXPIRE_HOURS)
        stale_agent = (
            db.query(Session)
            .filter(Session.status == "in_agent", Session.updated_at <= cutoff_agent)
            .all()
        )
        for s in stale_agent:
            s.status = "completed"
            ctx = s.context_json or {}
            if isinstance(ctx, str):
                try: ctx = json.loads(ctx)
                except Exception: ctx = {}
            ctx["closed_reason"] = "inactividad_agente_72h"
            s.context_json = ctx
            expired_in_agent += 1

        db.commit()

        result = {
            "expired_active":   expired_active,
            "expired_in_agent": expired_in_agent,
            "ran_at":           now.isoformat(),
        }
        logger.info("Cleanup worker | %s", result)
        return result

    except Exception as exc:
        logger.exception("Error en cleanup_worker: %s", exc)
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()


def is_rate_limited(number: str, db) -> bool:
    """
    Verifica si un número excede el límite de mensajes.
    Retorna True si debe ser bloqueado.
    """
    # ── Verificar si ya está bloqueado ────────────────────────────────────────
    if number in _blocked_numbers:
        unblock_at = _blocked_numbers[number]
        if datetime.utcnow() < unblock_at:
            logger.warning("Rate limit activo | number=%s | unblock_at=%s", number, unblock_at)
            return True
        else:
            del _blocked_numbers[number]

    # ── Contar mensajes en la última hora ─────────────────────────────────────
    window_start = datetime.utcnow() - timedelta(hours=RATE_LIMIT_WINDOW_H)
    try:
        count = (
            db.query(func.count(InboxMessage.id))
            .filter(
                InboxMessage.whatsapp_number == number,
                InboxMessage.created_at >= window_start,
            )
            .scalar() or 0
        )

        if count >= RATE_LIMIT_MESSAGES:
            _blocked_numbers[number] = datetime.utcnow() + timedelta(minutes=BLOCK_DURATION_MIN)
            logger.warning(
                "Rate limit alcanzado | number=%s | count=%s | bloqueado %s min",
                number, count, BLOCK_DURATION_MIN
            )
            return True

        return False

    except Exception as exc:
        logger.error("Error verificando rate limit: %s", exc)
        return False  # En caso de error, no bloquear