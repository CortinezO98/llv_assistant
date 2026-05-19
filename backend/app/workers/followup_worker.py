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
    - Solo se envía 1 seguimiento por sesión (flag follow_up_sent)
"""
import json
import logging
from datetime import datetime, timedelta

from app.db.models.messaging import OutboxMessage
from app.db.models.patient import Patient
from app.db.models.session import Session
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
FOLLOWUP_AFTER_HOURS   = 4    # horas de inactividad antes del seguimiento
CLOSE_AFTER_HOURS      = 8    # horas sin respuesta para cerrar sesión
MAX_FOLLOWUP_PER_SESSION = 1  # un solo seguimiento por sesión

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


def run_followup_worker() -> dict:
    """
    Busca sesiones activas sin actividad reciente y envía seguimiento.
    Retorna un resumen de lo procesado.
    """
    db = SessionLocal()
    now = datetime.utcnow()
    followup_cutoff = now - timedelta(hours=FOLLOWUP_AFTER_HOURS)
    close_cutoff    = now - timedelta(hours=CLOSE_AFTER_HOURS)

    sent_followup = 0
    closed        = 0
    skipped       = 0

    try:
        # Sesiones activas (no in_agent, no completadas)
        active_sessions = (
            db.query(Session)
            .filter(
                Session.status == "active",
                Session.updated_at <= followup_cutoff,
            )
            .all()
        )

        for session in active_sessions:
            ctx = session.context_json or {}
            if isinstance(ctx, str):
                try: ctx = json.loads(ctx)
                except Exception: ctx = {}

            # No enviar seguimiento si ya se envió
            if ctx.get("follow_up_sent"):
                # Si ya se envió y aún no respondió → cerrar sesión
                if session.updated_at <= close_cutoff:
                    session.status = "completed"
                    ctx["lead_temperature"]  = "frio"
                    ctx["closed_reason"]     = "sin_respuesta_tras_seguimiento"
                    session.context_json     = ctx

                    patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
                    if patient:
                        _enqueue(db, session.whatsapp_number, MSG_CLOSE_ES)
                    closed += 1
                    logger.info("Sesión cerrada por inactividad | session=%s", session.id)
                else:
                    skipped += 1
                continue

            # No enviar si el flujo ya llegó al handoff (agente en camino)
            flow_step = ctx.get("flow_step", "")
            if flow_step in ("handoff", "confirmacion"):
                skipped += 1
                continue

            # No enviar si el menú ni siquiera se pasó
            if flow_step == "menu" and not ctx.get("menu_opcion"):
                skipped += 1
                continue

            # ── Enviar seguimiento ────────────────────────────────────────────
            patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
            nombre  = patient.full_name.split()[0] if patient and patient.full_name else None

            msg = MSG_FOLLOWUP_ES
            if nombre:
                msg = f"Hola *{nombre}* 😊✨ Solo quería saber si aún deseas recibir información sobre tu tratamiento.\n\nEstamos aquí para ayudarte 💙\n👉 Puedes continuar respondiendo este mensaje."

            _enqueue(db, session.whatsapp_number, msg)

            ctx["follow_up_sent"]    = True
            ctx["follow_up_sent_at"] = now.isoformat()
            session.context_json     = ctx

            sent_followup += 1
            logger.info(
                "Seguimiento enviado | session=%s | number=%s | step=%s",
                session.id, session.whatsapp_number, flow_step
            )

        db.commit()

        result = {
            "sent_followup": sent_followup,
            "closed":        closed,
            "skipped":       skipped,
            "ran_at":        now.isoformat(),
        }
        logger.info("Followup worker completado | %s", result)
        return result

    except Exception as exc:
        logger.exception("Error en followup_worker: %s", exc)
        db.rollback()
        return {"error": str(exc), "ran_at": now.isoformat()}
    finally:
        db.close()


def _enqueue(db, to: str, text: str):
    db.add(OutboxMessage(
        whatsapp_number=to,
        payload_json=json.dumps({"to": to, "text": text}),
        status="pending",
    ))
    db.flush()