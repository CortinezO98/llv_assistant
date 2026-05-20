"""
app/workers/followup_worker.py

Worker de seguimiento automático para sesiones sin respuesta.

Meta API obliga a usar Templates aprobados si pasaron 24h desde el último
mensaje del cliente. Para evitar ese costo y restricción, el seguimiento
se envía a las 4 HORAS de inactividad — dentro de la ventana de 24h donde
cualquier mensaje de texto libre es válido sin costo adicional.

Estrategia:
    - Sesión activa + sin respuesta del cliente en 4h → mensaje de seguimiento
    - Si tampoco responde en otras 4h → cierre automático con lead_temp=frio
    - Solo se envía 1 seguimiento por sesión usando flag follow_up_sent
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from app.db.models.messaging import MessageLog, OutboxMessage
from app.db.models.patient import Patient
from app.db.models.session import Session
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


# ── Configuración ─────────────────────────────────────────────────────────────
FOLLOWUP_AFTER_HOURS = 4
CLOSE_AFTER_HOURS = 8
MAX_FOLLOWUP_PER_SESSION = 1
MAX_SESSIONS_PER_RUN = 100


MSG_FOLLOWUP_ES = (
    "Hola 😊✨ Solo quería saber si aún deseas recibir información sobre tu tratamiento.\n\n"
    "Estamos aquí para ayudarte 💙\n"
    "👉 Puedes continuar respondiendo este mensaje."
)


MSG_CLOSE_ES = (
    "Entendemos que quizás no es el momento indicado 😊\n\n"
    "Cuando estés listo/a, con gusto te ayudamos aquí en *LLV Wellness Clinic* ✨\n"
    "¡Cuídate mucho! 💙"
)


def _safe_context(session: Session) -> dict[str, Any]:
    """
    Devuelve el context_json como dict de forma segura.
    Evita romper el worker si el JSON viene como string o con formato inválido.
    """
    ctx = session.context_json or {}

    if isinstance(ctx, str):
        try:
            ctx = json.loads(ctx)
        except Exception:
            ctx = {}

    if not isinstance(ctx, dict):
        ctx = {}

    return ctx


def _get_patient(db, session: Session) -> Patient | None:
    return (
        db.query(Patient)
        .filter(Patient.id == session.patient_id)
        .first()
    )


def _build_followup_message(patient: Patient | None) -> str:
    """
    Construye el mensaje de seguimiento.
    Conserva el tono original del archivo actual.
    """
    if patient and patient.full_name:
        nombre = patient.full_name.split()[0].strip()

        if nombre:
            return (
                f"Hola *{nombre}* 😊✨ Solo quería saber si aún deseas recibir "
                f"información sobre tu tratamiento.\n\n"
                f"Estamos aquí para ayudarte 💙\n"
                f"👉 Puedes continuar respondiendo este mensaje."
            )

    return MSG_FOLLOWUP_ES


def _enqueue_message(
    db,
    session: Session,
    text: str,
    sent_by_bot: int = 1,
) -> None:
    """
    Encola mensaje en Outbox y registra el mensaje en el historial.
    """
    db.add(
        OutboxMessage(
            whatsapp_number=session.whatsapp_number,
            payload_json=json.dumps(
                {
                    "to": session.whatsapp_number,
                    "text": text,
                },
                ensure_ascii=False,
            ),
            status="pending",
        )
    )

    db.add(
        MessageLog(
            session_id=session.id,
            whatsapp_number=session.whatsapp_number,
            direction="outbound",
            content=text,
            message_type="text",
            sent_by_bot=sent_by_bot,
            agent_id=None,
        )
    )

    db.flush()


def _should_skip_followup(ctx: dict[str, Any]) -> bool:
    """
    Evita enviar seguimiento en estados donde no conviene interrumpir:
    - handoff: ya pasó a agente
    - confirmacion: está en una etapa final
    - payment_intent_detected: está en proceso de pago o validación
    """
    flow_step = ctx.get("flow_step", "")

    if flow_step in ("handoff", "confirmacion"):
        return True

    if ctx.get("payment_intent_detected"):
        return True

    # Si sigue apenas en menú y no eligió opción, no insistimos.
    if flow_step == "menu" and not ctx.get("menu_opcion"):
        return True

    return False


def run_followup_worker() -> dict:
    """
    Busca sesiones activas sin actividad reciente y envía seguimiento.

    Retorna:
        dict con resumen operativo para logs.
    """
    db = SessionLocal()

    now = datetime.utcnow()
    followup_cutoff = now - timedelta(hours=FOLLOWUP_AFTER_HOURS)
    close_cutoff = now - timedelta(hours=CLOSE_AFTER_HOURS)

    sent_followup = 0
    closed = 0
    skipped = 0
    errors = 0

    try:
        active_sessions = (
            db.query(Session)
            .filter(
                Session.status == "active",
                Session.updated_at <= followup_cutoff,
            )
            .order_by(Session.updated_at.asc())
            .limit(MAX_SESSIONS_PER_RUN)
            .all()
        )

        for session in active_sessions:
            try:
                ctx = _safe_context(session)

                # ── Si ya se envió seguimiento, evaluar cierre ───────────────
                if ctx.get("follow_up_sent"):
                    if session.updated_at <= close_cutoff:
                        session.status = "completed"
                        ctx["lead_temperature"] = "frio"
                        ctx["closed_reason"] = "sin_respuesta_tras_seguimiento"
                        ctx["closed_at"] = now.isoformat()
                        session.context_json = ctx

                        _enqueue_message(db, session, MSG_CLOSE_ES)

                        closed += 1

                        logger.info(
                            "Sesión cerrada por inactividad | session=%s | number=%s",
                            session.id,
                            session.whatsapp_number,
                        )
                    else:
                        skipped += 1

                    continue

                # ── Evitar seguimiento en pasos sensibles ────────────────────
                if _should_skip_followup(ctx):
                    skipped += 1
                    continue

                # ── Enviar seguimiento ──────────────────────────────────────
                patient = _get_patient(db, session)
                message = _build_followup_message(patient)

                _enqueue_message(db, session, message)

                ctx["follow_up_sent"] = True
                ctx["follow_up_sent_at"] = now.isoformat()
                ctx["follow_up_count"] = int(ctx.get("follow_up_count", 0)) + 1
                session.context_json = ctx

                sent_followup += 1

                logger.info(
                    "Seguimiento enviado | session=%s | number=%s | step=%s",
                    session.id,
                    session.whatsapp_number,
                    ctx.get("flow_step", ""),
                )

            except Exception as exc:
                errors += 1
                logger.warning(
                    "Error procesando seguimiento | session=%s | error=%s",
                    getattr(session, "id", None),
                    exc,
                )

        db.commit()

        result = {
            "sent_followup": sent_followup,
            "closed": closed,
            "skipped": skipped,
            "errors": errors,
            "ran_at": now.isoformat(),
        }

        logger.info("Followup worker completado | %s", result)
        return result

    except Exception as exc:
        logger.exception("Error en followup_worker: %s", exc)
        db.rollback()

        return {
            "sent_followup": sent_followup,
            "closed": closed,
            "skipped": skipped,
            "errors": errors + 1,
            "error": str(exc),
            "ran_at": now.isoformat(),
        }

    finally:
        db.close()