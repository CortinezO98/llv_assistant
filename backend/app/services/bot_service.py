"""
app/services/bot_service.py

Orquestador principal del bot LLV Assistant.
Coordina: GeminiService (IA central) + DB + WhatsApp + Agentes + Pagos + Notificaciones.
"""
import json
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.db.models.agent import Agent
from app.db.models.appointment import Appointment
from app.db.models.messaging import FAQ, InboxMessage, MessageLog, OutboxMessage
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.services.agent_router import AgentRouter
from app.services.gemini_service import GeminiService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Métodos de pago por ubicación
_PAYMENT_INFO = {
    "puerto_rico": {
        "methods": ["ATH Móvil", "Tarjeta de crédito", "Apple Pay", "Zelle", "PayPal"],
        "primary": "ATH Móvil",
    },
    "latam": {
        "methods": ["Zelle", "PayPal"],
        "primary": "Zelle",
    },
    "usa": {
        "methods": ["Zelle", "PayPal", "Credit Card"],
        "primary": "Zelle",
    },
}

_UNSUPPORTED_TYPES = {
    "audio": "🎤 Recibí un audio. Por ahora proceso mensajes de texto. Escríbeme lo que necesitas o envía *agente* para hablar con un asesor.",
    "video": "🎥 Recibí un video. Por favor escríbeme en texto lo que necesitas.",
    "location": "📍 Recibí una ubicación. Escríbeme en texto lo que necesitas.",
    "sticker": "🙂 ¡Gracias! ¿En qué puedo ayudarte hoy?",
    "reaction": None,  # ignorar silenciosamente
}


class BotService:
    def __init__(self, db: DBSession):
        self.db = db
        self._gemini = GeminiService()
        self._agent_router = AgentRouter(db)
        self._notifications = NotificationService(db)

    # ── ENTRY POINT ───────────────────────────────────────────────────────────

    def process_message(self, inbox_msg: InboxMessage) -> dict[str, Any]:
        number = inbox_msg.whatsapp_number
        msg_type = inbox_msg.message_type or "text"
        text = inbox_msg.content or ""
        media_id = inbox_msg.media_id

        # Manejo de tipos no soportados
        if msg_type in _UNSUPPORTED_TYPES:
            reply = _UNSUPPORTED_TYPES[msg_type]
            if reply:
                self._enqueue_outbox(number, reply)
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": f"unsupported_type:{msg_type}"}

        # Si es imagen/documento podría ser un comprobante de pago
        if msg_type in ("image", "document") and media_id:
            return self._handle_possible_payment_proof(number, media_id, inbox_msg)

        # Obtener o crear paciente y sesión
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)

        # Log del mensaje entrante
        self._log_message(session.id, number, "inbound", text, msg_type, inbox_msg.meta_message_id, False)

        # Si la sesión está en modo agente → no procesar con IA
        if session.status == "in_agent":
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": "session_in_agent_mode"}

        # Cargar FAQ activo
        faq_items = self._load_faq()

        # Construir historial reciente de la sesión
        history = self._build_history(session)

        # Construir contexto del paciente para Gemini
        patient_ctx = self._patient_context(patient)

        # ── LLAMADA A GEMINI ──────────────────────────────────────────────────
        result = self._gemini.process_message(
            user_message=text,
            history=history,
            faq_items=faq_items,
            patient=patient_ctx,
            media_id=media_id,
        )

        # Actualizar timestamp de interacción
        patient.last_interaction_at = datetime.utcnow()

        # Procesar resultado
        if result["function_call"]:
            reply = self._handle_function_call(
                result["function_call"],
                result["function_args"] or {},
                patient,
                session,
                inbox_msg,
            )
        else:
            reply = result["text"] or "Entendido. ¿En qué más puedo ayudarte?"

        # Enviar respuesta y registrar
        if reply:
            self._enqueue_outbox(number, reply)
            self._log_message(session.id, number, "outbound", reply, "text", None, True)

        # Es una conversación nueva (primer mensaje) → contar en el plan
        if not history:
            self._notifications.increment_conversation()

        inbox_msg.status = "done"
        self.db.commit()
        return {"ok": True}

    # ── FUNCTION CALL HANDLER ─────────────────────────────────────────────────

    def _handle_function_call(
        self,
        fn_name: str,
        args: dict,
        patient: Patient,
        session: Session,
        inbox_msg: InboxMessage,
    ) -> str:
        logger.info("Function call: %s | args=%s", fn_name, args)

        if fn_name == "identify_patient":
            return self._fn_identify_patient(args, patient, session)

        if fn_name == "schedule_appointment":
            return self._fn_schedule_appointment(args, patient, session)

        if fn_name == "send_payment_link":
            return self._fn_send_payment_link(args, patient, session)

        if fn_name == "escalate_to_agent":
            return self._fn_escalate_to_agent(args, patient, session)

        if fn_name == "register_payment_proof":
            return self._fn_register_payment_proof(args, patient, session)

        logger.warning("Función desconocida: %s", fn_name)
        return "Estoy procesando tu solicitud. Un momento por favor."

    def _fn_identify_patient(self, args: dict, patient: Patient, session: Session) -> str:
        if args.get("full_name"):
            patient.full_name = args["full_name"]
        if args.get("birth_date"):
            try:
                patient.birth_date = date.fromisoformat(args["birth_date"])
            except Exception:
                pass
        if args.get("location_type") in ("puerto_rico", "latam", "usa"):
            patient.location_type = args["location_type"]
        self.db.flush()

        name = patient.full_name or "estimado/a cliente"
        if patient.is_recurrent:
            return (
                f"¡Hola de nuevo, *{name}*! 👋 Qué bueno verte por aquí. "
                f"¿Vienes por tu tratamiento habitual o quieres explorar algo nuevo? "
                f"Estoy aquí para ayudarte. 😊"
            )
        return (
            f"¡Perfecto, *{name}*! Ya tengo tus datos registrados. "
            f"¿En qué puedo ayudarte hoy? Puedes preguntarme sobre nuestros tratamientos, "
            f"precios, disponibilidad o agendar una valoración. 💚"
        )

    def _fn_schedule_appointment(self, args: dict, patient: Patient, session: Session) -> str:
        appt = Appointment(
            patient_id=patient.id,
            session_id=session.id,
            full_name=args.get("full_name", patient.full_name or ""),
            phone=args.get("phone", patient.whatsapp_number),
            service=args.get("service", ""),
            clinic=args.get("clinic", "latam"),
            medical_conditions=args.get("medical_conditions"),
            status="pending_confirm",
        )
        if args.get("preferred_date"):
            try:
                appt.preferred_date = date.fromisoformat(args["preferred_date"])
            except Exception:
                pass

        self.db.add(appt)
        patient.is_recurrent = 1
        self.db.flush()

        logger.info("Cita registrada | patient=%s | service=%s", patient.id, appt.service)
        return (
            f"✅ ¡Listo! Registré tu solicitud de cita para *{appt.service}*.\n\n"
            f"📋 *Resumen:*\n"
            f"• Nombre: {appt.full_name}\n"
            f"• Servicio: {appt.service}\n"
            f"• Clínica: {appt.clinic.replace('_', ' ').title()}\n"
            f"{'• Fecha preferida: ' + str(appt.preferred_date) + chr(10) if appt.preferred_date else ''}"
            f"\n🕐 Un miembro de nuestro equipo confirmará tu cita en Vagaro y se pondrá en contacto contigo pronto.\n"
            f"¿Tienes alguna otra pregunta? 😊"
        )

    def _fn_send_payment_link(self, args: dict, patient: Patient, session: Session) -> str:
        method = args.get("payment_method", "zelle")
        product = args.get("product_service", "Tratamiento LRV")
        amount = args.get("amount")

        payment = Payment(
            patient_id=patient.id,
            session_id=session.id,
            product_service=product,
            amount=amount,
            currency="USD",
            payment_method=method,
            status="link_sent",
        )
        self.db.add(payment)
        self.db.flush()

        amount_text = f"${amount:.2f} USD" if amount else "el monto indicado"

        # Instrucciones según método
        payment_instructions = {
            "zelle": "💳 *Pago por Zelle:*\nEnvía {amount} al correo: _pagos@llvclinic.com_\nEn el concepto escribe tu nombre completo.",
            "ath":   "📱 *Pago por ATH Móvil:*\nEnvía {amount} al número: _787-800-5222_\nEn el mensaje escribe tu nombre completo.",
            "paypal": "💻 *Pago por PayPal:*\nEnvía {amount} a: _pagos@llvclinic.com_\nSelecciona 'Amigos y familia' para evitar comisiones.",
            "credit_card": "💳 *Pago con Tarjeta:*\nUn asesor te enviará el link de pago seguro en breve.",
        }.get(method, "Un asesor te enviará las instrucciones de pago.")

        return (
            f"¡Perfecto! Aquí están las instrucciones para tu pago de *{product}*:\n\n"
            f"{payment_instructions.format(amount=amount_text)}\n\n"
            f"📸 Una vez realices el pago, por favor *envía el comprobante* (foto o captura) "
            f"aquí mismo y lo verificaremos. ¿Alguna duda? 😊"
        )

    def _fn_escalate_to_agent(self, args: dict, patient: Patient, session: Session) -> str:
        reason = args.get("reason", "Solicitud del cliente")

        # Generar resumen con IA
        history = self._build_history(session)
        patient_ctx = self._patient_context(patient)
        summary = self._gemini.generate_agent_summary(history, patient_ctx)

        # Asignar agente
        location = patient.location_type or "latam"
        agent = self._agent_router.assign_agent(session, location)

        if not agent:
            return (
                "Intenté conectarte con un asesor pero en este momento no hay disponibilidad. "
                "Por favor escríbenos en horario de atención:\n"
                "• Lun–Vie: 8:00 AM – 5:00 PM\n"
                "• Sáb: 8:00 AM – 1:00 PM\n"
                "¡Te responderemos tan pronto sea posible! 💚"
            )

        # Guardar resumen en el contexto de la sesión para que el agente lo vea
        session.context_json = session.context_json or {}
        if isinstance(session.context_json, str):
            try:
                session.context_json = json.loads(session.context_json)
            except Exception:
                session.context_json = {}
        session.context_json["agent_summary"] = summary
        session.context_json["escalation_reason"] = reason
        self.db.flush()

        logger.info("Escalada a agente | agent=%s | session=%s | reason=%s", agent.name, session.id, reason)
        return (
            f"Perfecto, te voy a conectar con uno de nuestros asesores. 👋\n\n"
            f"*{agent.name}* tomará tu consulta en un momento. "
            f"¡Ya tiene el contexto completo de tu conversación para atenderte mejor! 💚"
        )

    def _fn_register_payment_proof(self, args: dict, patient: Patient, session: Session) -> str:
        media_id = args.get("media_id", "")
        product = args.get("product_service", "Tratamiento LRV")

        # Buscar pago pendiente de esta sesión
        payment = (
            self.db.query(Payment)
            .filter(
                Payment.session_id == session.id,
                Payment.status == "link_sent",
            )
            .order_by(Payment.created_at.desc())
            .first()
        )
        if payment:
            payment.proof_media_id = media_id
            payment.status = "proof_received"
        else:
            # Crear nuevo registro de pago con comprobante
            payment = Payment(
                patient_id=patient.id,
                session_id=session.id,
                product_service=product,
                payment_method="other",
                proof_media_id=media_id,
                status="proof_received",
            )
            self.db.add(payment)
        self.db.flush()

        return (
            "✅ ¡Recibí tu comprobante de pago! Nuestro equipo lo verificará y "
            "te confirmará en breve.\n\n"
            "Normalmente verificamos en menos de 2 horas en horario laboral. "
            "¿Hay algo más en lo que pueda ayudarte? 😊"
        )

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _handle_possible_payment_proof(
        self, number: str, media_id: str, inbox_msg: InboxMessage
    ) -> dict:
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)
        self._log_message(session.id, number, "inbound", f"[media:{media_id}]", inbox_msg.message_type, inbox_msg.meta_message_id, False)

        reply = self._fn_register_payment_proof({"media_id": media_id}, patient, session)
        self._enqueue_outbox(number, reply)
        self._log_message(session.id, number, "outbound", reply, "text", None, True)

        inbox_msg.status = "done"
        self.db.commit()
        return {"ok": True}

    def _get_or_create_patient(self, number: str, profile_name: str | None = None) -> Patient:
        patient = self.db.query(Patient).filter(Patient.whatsapp_number == number).first()
        if not patient:
            patient = Patient(whatsapp_number=number, full_name=profile_name)
            self.db.add(patient)
            self.db.flush()
            logger.info("Nuevo paciente creado | number=%s", number)
        return patient

    def _get_or_create_session(self, number: str, patient: Patient) -> Session:
        # Buscar sesión activa o en_agente
        session = (
            self.db.query(Session)
            .filter(
                Session.whatsapp_number == number,
                Session.status.in_(["active", "in_agent"]),
            )
            .order_by(Session.created_at.desc())
            .first()
        )
        if not session:
            session = Session(
                patient_id=patient.id,
                whatsapp_number=number,
                status="active",
                context_json={"history": []},
            )
            self.db.add(session)
            self.db.flush()
            logger.info("Nueva sesión creada | number=%s | session=%s", number, session.id)
        return session

    def _load_faq(self) -> list[dict]:
        items = self.db.query(FAQ).filter(FAQ.is_active == 1).all()
        return [{"question": f.question, "answer": f.answer, "category": f.category} for f in items]

    def _build_history(self, session: Session) -> list[dict]:
        logs = (
            self.db.query(MessageLog)
            .filter(
                MessageLog.session_id == session.id,
                MessageLog.message_type == "text",
            )
            .order_by(MessageLog.created_at.desc())
            .limit(20)
            .all()
        )
        history = []
        for log in reversed(logs):
            role = "user" if not log.sent_by_bot else "assistant"
            history.append({"role": role, "content": log.content or ""})
        return history

    def _patient_context(self, patient: Patient) -> dict | None:
        if not patient:
            return None
        return {
            "whatsapp_number": patient.whatsapp_number,
            "full_name": patient.full_name,
            "location_type": patient.location_type,
            "is_recurrent": bool(patient.is_recurrent),
        }

    def _log_message(
        self, session_id, number, direction, content, msg_type, meta_id, sent_by_bot
    ) -> None:
        log = MessageLog(
            session_id=session_id,
            whatsapp_number=number,
            direction=direction,
            content=content,
            message_type=msg_type,
            meta_message_id=meta_id,
            sent_by_bot=1 if sent_by_bot else 0,
        )
        self.db.add(log)
        self.db.flush()

    def _enqueue_outbox(self, to: str, text: str) -> None:
        import json as _json
        payload = _json.dumps({"to": to, "text": text})
        msg = OutboxMessage(whatsapp_number=to, payload_json=payload, status="pending")
        self.db.add(msg)
        self.db.flush()
