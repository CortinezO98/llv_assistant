"""
app/services/ai_orchestrator.py

🧠 CEREBRO DEL SISTEMA — AI Orchestrator

Flujo:
    Mensaje usuario
        ↓
    AI Orchestrator  ←── contexto: paciente + FAQ + historial
        ↓
    Gemini (interpretación NLP + function calling)
        ↓
    Backend (validación de negocio)
        ↓
    Acción (cita / pago / FAQ / agente / identificación)
        ↓
    Analytics (registro del evento)
        ↓
    Respuesta natural → WhatsApp

Diferencia vs bot_service anterior:
    - bot_service era un orquestador implícito con lógica dispersa
    - AIOrchestrator es el cerebro EXPLÍCITO que decide qué hacer
    - Separa claramente: interpretar (Gemini) vs ejecutar (Backend) vs registrar (Analytics)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
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
from app.services.analytics_service import AnalyticsService
from app.services.gemini_service import GeminiService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# ── Tipos de mensajes no soportados ──────────────────────────────────────────
_UNSUPPORTED = {
    "audio":    "🎤 Recibí un audio. Por ahora proceso mensajes de texto. Escríbeme lo que necesitas o envía *agente* para hablar con un asesor.",
    "video":    "🎥 Recibí un video. Por favor escríbeme en texto lo que necesitas.",
    "location": "📍 Recibí una ubicación. Escríbeme en texto lo que necesitas.",
    "sticker":  "🙂 ¡Gracias! ¿En qué puedo ayudarte hoy?",
    "reaction": None,
}

# ── Instrucciones de pago por ubicación ──────────────────────────────────────
_PAYMENT_INSTRUCTIONS = {
    "zelle":       "💳 *Pago por Zelle:*\nEnvía {amount} al correo: _pagos@llvclinic.com_\nEn el concepto escribe tu nombre completo.",
    "ath":         "📱 *Pago por ATH Móvil:*\nEnvía {amount} al número: _787-800-5222_\nEn el mensaje escribe tu nombre completo.",
    "paypal":      "💻 *Pago por PayPal:*\nEnvía {amount} a: _pagos@llvclinic.com_\nSelecciona 'Amigos y familia' para evitar comisiones.",
    "credit_card": "💳 *Pago con Tarjeta:*\nUn asesor te enviará el link de pago seguro en breve.",
}


@dataclass
class OrchestratorResult:
    reply: str | None
    action_taken: str
    success: bool


class AIOrchestrator:
    """
    Orquestador central. Coordina:
    - GeminiService  → interpreta el lenguaje natural
    - Backend        → valida reglas de negocio y persiste
    - AnalyticsService → registra cada evento
    - AgentRouter    → distribuye carga entre agentes
    - NotificationService → alertas de consumo
    """

    def __init__(self, db: DBSession):
        self.db          = db
        self.gemini      = GeminiService()
        self.analytics   = AnalyticsService(db)
        self.agent_router = AgentRouter(db)
        self.notifications = NotificationService(db)

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY POINT PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════

    def process(self, inbox_msg: InboxMessage) -> dict[str, Any]:
        """
        Punto de entrada principal. Recibe un mensaje del inbox y coordina
        todo el flujo: interpretación IA → acción backend → analytics → respuesta.
        """
        number   = inbox_msg.whatsapp_number
        msg_type = inbox_msg.message_type or "text"
        text     = inbox_msg.content or ""
        media_id = inbox_msg.media_id

        # ── 1. Mensajes no soportados (audio, video, etc.) ────────────────────
        if msg_type in _UNSUPPORTED:
            reply = _UNSUPPORTED[msg_type]
            if reply:
                self._send(number, reply)
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": f"unsupported:{msg_type}"}

        # ── 2. Imagen/documento → posible comprobante de pago ─────────────────
        if msg_type in ("image", "document") and media_id:
            return self._handle_payment_proof(number, media_id, inbox_msg)

        # ── 3. Obtener/crear paciente y sesión ────────────────────────────────
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)

        # ── 4. Registrar mensaje entrante ─────────────────────────────────────
        self._log_msg(session.id, number, "inbound", text, msg_type, inbox_msg.meta_message_id, False)
        self.analytics.message_received(session.id, patient.id, msg_type)

        # ── 5. Sesión en modo agente → solo registrar, no procesar con IA ─────
        if session.status == "in_agent":
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": "in_agent_mode"}

        # ── 6. Primera vez que escribe en esta sesión → contar conversación ───
        is_new_conversation = not self._has_history(session)
        if is_new_conversation:
            self.notifications.increment_conversation()
            self.analytics.conversation_started(session.id, patient.id)

        # ── 7. Cargar contexto para Gemini ────────────────────────────────────
        faq_items   = self._load_faq()
        history     = self._build_history(session)
        patient_ctx = self._patient_context(patient)

        # ── 8. GEMINI INTERPRETA el mensaje ───────────────────────────────────
        gemini_result = self.gemini.process_message(
            user_message=text,
            history=history,
            faq_items=faq_items,
            patient=patient_ctx,
            media_id=media_id,
        )
        patient.last_interaction_at = datetime.utcnow()

        # ── 9. BACKEND EJECUTA la acción ──────────────────────────────────────
        if gemini_result["function_call"]:
            result = self._execute_action(
                fn_name  = gemini_result["function_call"],
                fn_args  = gemini_result["function_args"] or {},
                patient  = patient,
                session  = session,
            )
            self.analytics.ai_response(session.id, patient.id, gemini_result["function_call"])
        else:
            # Respuesta de texto puro → Gemini manejó con FAQ o respuesta libre
            reply = gemini_result["text"] or "Entendido. ¿En qué más puedo ayudarte?"
            result = OrchestratorResult(reply=reply, action_taken="text_response", success=True)
            self.analytics.ai_response(session.id, patient.id, None)

        # ── 10. ENVIAR respuesta al cliente ───────────────────────────────────
        if result.reply:
            self._send(number, result.reply)
            self._log_msg(session.id, number, "outbound", result.reply, "text", None, True)

        inbox_msg.status = "done"
        self.db.commit()

        logger.info(
            "Orchestrator OK | number=%s | action=%s | session=%s",
            number, result.action_taken, session.id
        )
        return {"ok": True, "action": result.action_taken}

    # ═══════════════════════════════════════════════════════════════════════════
    # EJECUTORES DE ACCIONES (Backend valida y persiste)
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_action(
        self,
        fn_name: str,
        fn_args: dict,
        patient: Patient,
        session: Session,
    ) -> OrchestratorResult:
        """
        Ejecuta la acción que Gemini decidió invocar.
        El backend valida las reglas de negocio antes de persistir.
        """
        logger.info("Action: %s | args=%s | patient=%s", fn_name, fn_args, patient.id)

        actions = {
            "identify_patient":       self._action_identify_patient,
            "evaluate_patient":       self._action_evaluate_patient,
            "evaluate_reorder":       self._action_evaluate_reorder,
            "schedule_appointment":   self._action_schedule_appointment,
            "register_delivery":      self._action_register_delivery,
            "register_shipment":      self._action_register_shipment,
            "send_payment_link":      self._action_send_payment_link,
            "escalate_to_agent":      self._action_escalate_to_agent,
            "register_payment_proof": self._action_register_payment_proof,
        }

        handler = actions.get(fn_name)
        if not handler:
            logger.warning("Acción desconocida: %s", fn_name)
            return OrchestratorResult(
                reply="Estoy procesando tu solicitud. Un momento por favor. 🙏",
                action_taken="unknown_action",
                success=False
            )

        return handler(fn_args, patient, session)

    # ── Acción: identificar paciente ─────────────────────────────────────────
    def _action_identify_patient(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        # Backend valida y persiste
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
            reply = (
                f"¡Hola de nuevo, *{name}*! 👋 Qué bueno verte por aquí. "
                f"¿Vienes por tu tratamiento habitual o quieres explorar algo nuevo? "
                f"Estoy aquí para ayudarte. 😊"
            )
        else:
            reply = (
                f"¡Perfecto, *{name}*! Ya tengo tus datos registrados. "
                f"¿En qué puedo ayudarte hoy? Puedes preguntarme sobre nuestros tratamientos, "
                f"precios, disponibilidad o agendar una valoración. 💚"
            )
        return OrchestratorResult(reply=reply, action_taken="identify_patient", success=True)

    # ── Acción: entrega local PR ─────────────────────────────────────────────
    def _action_register_delivery(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        from app.db.models.delivery import Delivery

        delivery_town = args.get("delivery_town", "").strip()
        service       = args.get("service_treatment", "").strip()

        if not delivery_town:
            return OrchestratorResult(
                reply="Para coordinar tu entrega necesito saber en qué *pueblo de Puerto Rico* te la entregamos. ¿Cuál es?",
                action_taken="delivery_missing_town", success=False
            )
        if not service:
            return OrchestratorResult(
                reply="¿Cuál es el tratamiento o kit que deseas pedir? (ej: Semaglutide 0.5 MG, Kit 1 mes)",
                action_taken="delivery_missing_service", success=False
            )

        delivery = Delivery(
            patient_id        = patient.id,
            session_id        = session.id,
            patient_name      = args.get("patient_name", patient.full_name or ""),
            phone             = args.get("phone", patient.whatsapp_number),
            service_treatment = service,
            amount_to_pay     = args.get("amount_to_pay"),
            delivery_town     = delivery_town,
            status            = "pending",
        )
        self.db.add(delivery)
        patient.is_recurrent = 1
        self.db.flush()

        self.analytics.track("delivery_created", session_id=session.id, patient_id=patient.id, service=service, town=delivery_town)

        reply = (
            f"✅ ¡Registré tu pedido de entrega!\n\n"
            f"📋 *Resumen:*\n"
            f"• Nombre: {delivery.patient_name}\n"
            f"• Tratamiento: {service}\n"
            f"• Pueblo de entrega: {delivery_town}\n"
            f"{'• Monto a pagar: $' + str(delivery.amount_to_pay) + ' USD' + chr(10) if delivery.amount_to_pay else ''}\n"
            f"Nuestro equipo coordinará la entrega contigo pronto. 💙\n\n"
            f"¿Deseas proceder con el pago ahora o tienes alguna pregunta adicional?"
        )
        return OrchestratorResult(reply=reply, action_taken="delivery_created", success=True)

    # ── Acción: envío postal ─────────────────────────────────────────────────
    def _action_register_shipment(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        from app.db.models.delivery import Shipment

        postal_address = args.get("postal_address", "").strip()
        service        = args.get("service_treatment", "").strip()

        if not postal_address:
            return OrchestratorResult(
                reply=(
                    "Para coordinar tu envío necesito tu *dirección postal completa*. "
                    "Por favor comparte:\n"
                    "• Dirección (calle, número, apt)\n"
                    "• Ciudad / Municipio\n"
                    "• Estado / Provincia\n"
                    "• País\n"
                    "• Código postal"
                ),
                action_taken="shipment_missing_address", success=False
            )
        if not service:
            return OrchestratorResult(
                reply="¿Cuál es el tratamiento o kit que deseas pedir? (ej: Tirzepatide 5 MG, Kit 2 semanas)",
                action_taken="shipment_missing_service", success=False
            )

        shipment = Shipment(
            patient_id        = patient.id,
            session_id        = session.id,
            patient_name      = args.get("patient_name", patient.full_name or ""),
            phone             = args.get("phone", patient.whatsapp_number),
            email             = args.get("email"),
            postal_address    = postal_address,
            city              = args.get("city"),
            state_province    = args.get("state_province"),
            country           = args.get("country", "Puerto Rico"),
            zip_code          = args.get("zip_code"),
            service_treatment = service,
            amount_paid       = args.get("amount_paid"),
            status            = "pending",
        )
        self.db.add(shipment)
        patient.is_recurrent = 1
        self.db.flush()

        self.analytics.track("shipment_created", session_id=session.id, patient_id=patient.id, service=service, country=shipment.country)

        reply = (
            f"✅ ¡Registré tu pedido de envío!\n\n"
            f"📋 *Resumen:*\n"
            f"• Nombre: {shipment.patient_name}\n"
            f"• Tratamiento: {service}\n"
            f"• Dirección: {postal_address}\n"
            f"{'• Ciudad: ' + str(shipment.city) + chr(10) if shipment.city else ''}"
            f"• País: {shipment.country}\n\n"
            f"Te enviaremos el número de rastreo una vez despachado. 💙\n\n"
            f"¿Deseas proceder con el pago ahora?"
        )
        return OrchestratorResult(reply=reply, action_taken="shipment_created", success=True)

    # ── Acción: evaluar cliente nuevo ────────────────────────────────────────
    def _action_evaluate_patient(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        import json as _json
        ctx = session.context_json or {}
        if isinstance(ctx, str):
            try: ctx = _json.loads(ctx)
            except: ctx = {}
        ctx["evaluation"] = {
            "type": "new_patient",
            "used_glp1_before": args.get("used_glp1_before"),
            "current_weight_lbs": args.get("current_weight_lbs"),
            "weight_loss_goal_lbs": args.get("weight_loss_goal_lbs"),
            "medical_conditions": args.get("medical_conditions", "ninguna"),
            "recommended_product": args.get("recommended_product", "semaglutide"),
            "recommended_dose": args.get("recommended_dose", "0.25 MG"),
        }
        session.context_json = ctx
        self.db.flush()

        product = args.get("recommended_product", "semaglutide").capitalize()
        dose    = args.get("recommended_dose", "0.25 MG")

        reply = (
            "Perfecto, gracias por la info 😊\n\n"
            f"En tu caso, lo más recomendable es iniciar con *{product}* en dosis *{dose}*, "
            "para que tu cuerpo se adapte de forma segura.\n"
            "✨ Controla el apetito y acelera la pérdida de peso de forma progresiva.\n\n"
            "Efectos posibles: náuseas, dolor de cabeza o acidez (temporales y manejables).\n"
            "Te envío la guía completa del tratamiento 📩\n\n"
            "¿Te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍"
        )
        self.analytics.track("patient_evaluated", session_id=session.id, patient_id=patient.id, product=product, dose=dose, type="new")
        return OrchestratorResult(reply=reply, action_taken="evaluate_patient", success=True)

    # ── Acción: evaluar recompra ──────────────────────────────────────────────
    def _action_evaluate_reorder(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        import json as _json
        ctx = session.context_json or {}
        if isinstance(ctx, str):
            try: ctx = _json.loads(ctx)
            except: ctx = {}
        ctx["evaluation"] = {
            "type": "reorder",
            "current_product": args.get("current_product"),
            "current_dose": args.get("current_dose"),
            "dose_adjustment": args.get("dose_adjustment"),
            "new_recommended_dose": args.get("new_recommended_dose"),
            "side_effects": args.get("side_effects", "ninguno"),
        }
        session.context_json = ctx
        self.db.flush()

        product   = args.get("current_product", "").capitalize()
        new_dose  = args.get("new_recommended_dose", "")
        adj       = args.get("dose_adjustment", "mantener")

        if adj == "subir":
            adj_text = (f"Como no has tenido efectos secundarios y quieres seguir bajando, "
                        f"lo ideal es *subir la dosis* 📈\n"
                        f"Te recomiendo continuar con *{product}* en dosis *{new_dose}* 💉✨")
        elif adj == "bajar":
            adj_text = (f"Gracias por contarme 😊. Lo mejor es *ajustar la dosis* "
                        f"para que te sientas mejor 💉✨\n"
                        f"Te recomiendo continuar con *{product}* en dosis *{new_dose}*")
        elif adj == "mantenimiento":
            adj_text = ("¡Qué bueno leer eso! 😍 Si ya llegaste a tu peso ideal, "
                        "pasamos a *fase de mantenimiento* ✨\n"
                        "Espaciamos la aplicación (cada 15 días o según evolución) 💉")
        else:
            adj_text = "Súper 😊 vas muy bien. Lo ideal es *mantener la misma dosis* por ahora 👍✨"

        reply = adj_text + "\n\n¿Te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍"
        self.analytics.track("patient_evaluated", session_id=session.id, patient_id=patient.id,
                             product=product, dose=new_dose, type="reorder", adjustment=adj)
        return OrchestratorResult(reply=reply, action_taken="evaluate_reorder", success=True)

    # ── Acción: agendar cita ─────────────────────────────────────────────────
    def _action_schedule_appointment(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        # Backend valida campos mínimos
        service = args.get("service", "").strip()
        if not service:
            return OrchestratorResult(
                reply="Para agendar tu cita necesito saber qué servicio o tratamiento te interesa. ¿Cuál sería?",
                action_taken="appointment_missing_service",
                success=False
            )

        # Persistir solicitud de cita
        appt = Appointment(
            patient_id          = patient.id,
            session_id          = session.id,
            full_name           = args.get("full_name", patient.full_name or ""),
            phone               = args.get("phone", patient.whatsapp_number),
            service             = service,
            clinic              = args.get("clinic", "latam"),
            medical_conditions  = args.get("medical_conditions"),
            status              = "pending_confirm",
        )
        if args.get("preferred_date"):
            try:
                appt.preferred_date = date.fromisoformat(args["preferred_date"])
            except Exception:
                pass

        self.db.add(appt)
        patient.is_recurrent = 1
        self.db.flush()

        # Analytics
        self.analytics.appointment_created(session.id, patient.id, service, appt.clinic)

        reply = (
            f"✅ ¡Listo! Registré tu solicitud de cita para *{service}*.\n\n"
            f"📋 *Resumen:*\n"
            f"• Nombre: {appt.full_name}\n"
            f"• Servicio: {service}\n"
            f"• Clínica: {appt.clinic.replace('_', ' ').title()}\n"
            f"{'• Fecha preferida: ' + str(appt.preferred_date) + chr(10) if appt.preferred_date else ''}"
            f"\n🕐 Nuestro equipo confirmará tu cita pronto. ¿Tienes alguna pregunta adicional? 😊"
        )
        return OrchestratorResult(reply=reply, action_taken="appointment_created", success=True)

    # ── Acción: enviar link/instrucciones de pago ────────────────────────────
    def _action_send_payment_link(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        method  = args.get("payment_method", "zelle").lower()
        product = args.get("product_service", "Tratamiento LRV")
        amount  = args.get("amount")

        # Backend valida: método de pago válido para la ubicación del paciente
        amount_text = f"${amount:.2f} USD" if amount else "el monto indicado"

        payment = Payment(
            patient_id      = patient.id,
            session_id      = session.id,
            product_service = product,
            amount          = amount,
            currency        = "USD",
            payment_method  = method if method in ("link","ath","credit_card","zelle","paypal","apple_pay") else "other",
            status          = "link_sent",
        )
        self.db.add(payment)
        self.db.flush()

        # Analytics
        self.analytics.payment_sent(session.id, patient.id, method, product, amount)

        instructions = _PAYMENT_INSTRUCTIONS.get(
            method,
            "Un asesor te enviará las instrucciones de pago en breve."
        ).format(amount=amount_text)

        reply = (
            f"¡Perfecto! Aquí están las instrucciones para tu pago de *{product}*:\n\n"
            f"{instructions}\n\n"
            f"📸 Una vez realices el pago, por favor *envía el comprobante* (foto o captura) "
            f"aquí mismo para verificarlo. ¿Alguna duda? 😊"
        )
        return OrchestratorResult(reply=reply, action_taken="payment_sent", success=True)

    # ── Acción: escalar a agente ─────────────────────────────────────────────
    def _action_escalate_to_agent(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        reason = args.get("reason", "Solicitud del cliente")

        # Generar resumen IA de la conversación
        history     = self._build_history(session)
        patient_ctx = self._patient_context(patient)
        summary     = self.gemini.generate_agent_summary(history, patient_ctx)

        # Backend selecciona agente con menor carga (round-robin)
        location = patient.location_type or "latam"
        agent    = self.agent_router.assign_agent(session, location)

        if not agent:
            return OrchestratorResult(
                reply=(
                    "Intenté conectarte con un asesor pero en este momento no hay disponibilidad. "
                    "Por favor escríbenos en horario de atención:\n"
                    "• Lun–Vie: 8:00 AM – 5:00 PM\n"
                    "• Sáb: 8:00 AM – 1:00 PM\n"
                    "¡Te responderemos tan pronto sea posible! 💚"
                ),
                action_taken="agent_unavailable",
                success=False
            )

        # Guardar resumen en la sesión para que el agente lo vea en el dashboard
        import json as _json
        ctx = session.context_json or {}
        if isinstance(ctx, str):
            try: ctx = _json.loads(ctx)
            except Exception: ctx = {}
        ctx["agent_summary"]       = summary
        ctx["escalation_reason"]   = reason
        ctx["escalated_at"]        = datetime.utcnow().isoformat()
        session.context_json = ctx
        self.db.flush()

        # Analytics
        self.analytics.agent_handoff(session.id, patient.id, agent.id, reason)

        reply = (
            f"Perfecto, te conecto con uno de nuestros asesores. 👋\n\n"
            f"*{agent.name}* tomará tu consulta en un momento. "
            f"Ya tiene el contexto de tu conversación para atenderte mejor. 💚"
        )
        return OrchestratorResult(reply=reply, action_taken="agent_handoff", success=True)

    # ── Acción: registrar comprobante de pago ────────────────────────────────
    def _action_register_payment_proof(self, args: dict, patient: Patient, session: Session) -> OrchestratorResult:
        media_id = args.get("media_id", "")
        product  = args.get("product_service", "Tratamiento LRV")

        # Buscar pago link_sent en esta sesión
        payment = (
            self.db.query(Payment)
            .filter(Payment.session_id == session.id, Payment.status == "link_sent")
            .order_by(Payment.created_at.desc())
            .first()
        )
        if payment:
            payment.proof_media_id = media_id
            payment.status         = "proof_received"
        else:
            payment = Payment(
                patient_id      = patient.id,
                session_id      = session.id,
                product_service = product,
                payment_method  = "other",
                proof_media_id  = media_id,
                status          = "proof_received",
            )
            self.db.add(payment)
        self.db.flush()

        self.analytics.payment_proof_received(session.id, patient.id)

        reply = (
            "✅ ¡Recibí tu comprobante! Nuestro equipo lo verificará y te confirmará en breve.\n\n"
            "Normalmente verificamos en menos de 2 horas en horario laboral. "
            "¿Hay algo más en lo que pueda ayudarte? 😊"
        )
        return OrchestratorResult(reply=reply, action_taken="payment_proof_received", success=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS INTERNOS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_payment_proof(self, number: str, media_id: str, inbox_msg: InboxMessage) -> dict:
        """Maneja imagen/documento entrante como posible comprobante de pago."""
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)
        self._log_msg(session.id, number, "inbound", f"[media:{media_id}]", inbox_msg.message_type, inbox_msg.meta_message_id, False)

        result = self._action_register_payment_proof({"media_id": media_id}, patient, session)
        if result.reply:
            self._send(number, result.reply)
            self._log_msg(session.id, number, "outbound", result.reply, "text", None, True)

        inbox_msg.status = "done"
        self.db.commit()
        return {"ok": True, "action": "payment_proof_received"}

    def _get_or_create_patient(self, number: str, profile_name: str | None = None) -> Patient:
        patient = self.db.query(Patient).filter(Patient.whatsapp_number == number).first()
        if not patient:
            patient = Patient(whatsapp_number=number, full_name=profile_name)
            self.db.add(patient)
            self.db.flush()
            logger.info("Nuevo paciente | number=%s", number)
        return patient

    def _get_or_create_session(self, number: str, patient: Patient) -> Session:
        session = (
            self.db.query(Session)
            .filter(Session.whatsapp_number == number, Session.status.in_(["active", "in_agent"]))
            .order_by(Session.created_at.desc())
            .first()
        )
        if not session:
            session = Session(
                patient_id    = patient.id,
                whatsapp_number = number,
                status        = "active",
                context_json  = {"history": []},
            )
            self.db.add(session)
            self.db.flush()
            logger.info("Nueva sesión | number=%s | session=%s", number, session.id)
        return session

    def _has_history(self, session: Session) -> bool:
        from app.db.models.messaging import MessageLog as MsgLog
        return self.db.query(MsgLog).filter(
            MsgLog.session_id == session.id
        ).first() is not None

    def _load_faq(self) -> list[dict]:
        items = self.db.query(FAQ).filter(FAQ.is_active == 1).all()
        return [{"question": f.question, "answer": f.answer, "category": f.category} for f in items]

    def _build_history(self, session: Session) -> list[dict]:
        from app.db.models.messaging import MessageLog as MsgLog
        logs = (
            self.db.query(MsgLog)
            .filter(MsgLog.session_id == session.id, MsgLog.message_type == "text")
            .order_by(MsgLog.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {"role": "user" if not log.sent_by_bot else "assistant", "content": log.content or ""}
            for log in reversed(logs)
        ]

    def _patient_context(self, patient: Patient) -> dict | None:
        if not patient:
            return None
        return {
            "whatsapp_number": patient.whatsapp_number,
            "full_name":       patient.full_name,
            "location_type":   patient.location_type,
            "is_recurrent":    bool(patient.is_recurrent),
        }

    def _log_msg(self, session_id, number, direction, content, msg_type, meta_id, sent_by_bot) -> None:
        from app.db.models.messaging import MessageLog as MsgLog
        self.db.add(MsgLog(
            session_id      = session_id,
            whatsapp_number = number,
            direction       = direction,
            content         = content,
            message_type    = msg_type,
            meta_message_id = meta_id,
            sent_by_bot     = 1 if sent_by_bot else 0,
        ))
        self.db.flush()

    def _send(self, to: str, text: str) -> None:
        import json as _json
        self.db.add(OutboxMessage(
            whatsapp_number = to,
            payload_json    = _json.dumps({"to": to, "text": text}),
            status          = "pending",
        ))
        self.db.flush()