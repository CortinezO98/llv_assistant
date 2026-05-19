"""
app/utils/structured_logger.py

Logging estructurado con contexto de sesión, paciente y tipo de error.
Reemplaza los logs de texto plano por JSON filtrable en producción.

Uso:
    from app.utils.structured_logger import get_logger, log_event

    logger = get_logger(__name__)
    logger.info("Mensaje procesado", extra={"session_id": 123, "patient_id": 456})

    # O con helper directo:
    log_event("message_processed", session_id=123, patient_id=456, step="menu")
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formatea logs como JSON con campos indexables."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "ts":       datetime.utcnow().isoformat() + "Z",
            "level":    record.levelname,
            "logger":   record.name,
            "msg":      record.getMessage(),
        }

        # Campos de contexto del negocio
        business_fields = [
            "session_id", "patient_id", "agent_id",
            "number", "whatsapp_number",
            "flow_step", "menu_opcion", "lead_temp",
            "event_type", "error_type",
            "function_call", "duration_ms",
        ]
        for field in business_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Stack trace si hay excepción
        if record.exc_info:
            log_data["exception"] = {
                "type":    record.exc_info[0].__name__ if record.exc_info[0] else None,
                "msg":     str(record.exc_info[1]) if record.exc_info[1] else None,
                "trace":   traceback.format_exc(),
            }

        return json.dumps(log_data, ensure_ascii=False, default=str)


class PlainFormatter(logging.Formatter):
    """Formato legible para desarrollo local."""

    COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color  = self.COLORS.get(record.levelname, "")
        reset  = self.RESET
        base   = f"{color}[{record.levelname}]{reset} {record.name} | {record.getMessage()}"

        extras = []
        for field in ["session_id", "patient_id", "flow_step", "number"]:
            if hasattr(record, field):
                extras.append(f"{field}={getattr(record, field)}")

        if extras:
            base += f"  ({', '.join(extras)})"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def setup_logging(env: str = "development") -> None:
    """
    Configura el sistema de logging según el entorno.
    Llamar una sola vez al inicio de la app (en main.py).
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if env == "development" else logging.INFO)

    # Limpiar handlers existentes
    root.handlers.clear()

    handler = logging.StreamHandler()

    if env == "production":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(PlainFormatter())

    root.addHandler(handler)

    # Silenciar loggers ruidosos
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger configurado para el módulo dado."""
    return logging.getLogger(name)


def log_event(
    event_type: str,
    level: str = "info",
    **kwargs: Any,
) -> None:
    """
    Helper para loguear un evento de negocio con contexto.

    Uso:
        log_event("message_received", session_id=123, number="+1787...", step="menu")
        log_event("escalation", level="warning", session_id=123, reason="cliente solicitó agente")
        log_event("error", level="error", session_id=123, error_type="gemini_timeout")
    """
    logger = logging.getLogger("llv.events")
    extra  = {"event_type": event_type, **kwargs}

    msg = f"{event_type}"
    if "session_id" in kwargs:
        msg += f" | session={kwargs['session_id']}"
    if "number" in kwargs:
        msg += f" | number={kwargs['number']}"

    getattr(logger, level)(msg, extra=extra)