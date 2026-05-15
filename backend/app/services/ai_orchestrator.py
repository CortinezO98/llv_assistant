"""
app/services/ai_orchestrator.py

🧠 CEREBRO DEL SISTEMA — AI Orchestrator con Flujo Conversacional Híbrido

Arquitectura:
- Paso 1 (Menú): Respuesta predefinida — 0 tokens Gemini
- Pasos 2-5 (Flujo): Máquina de estados estructurada — mínimo tokens
- Pasos 6+ (IA libre): Gemini toma el control con contexto completo
- Antes del handoff: Resumen de confirmación obligatorio
- Validación: 2 reintentos por dato, luego escala automática
"""
from __future__ import annotations

import copy
import json as _json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.appointment import Appointment
from app.db.models.messaging import FAQ, InboxMessage, OutboxMessage
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.services.agent_router import AgentRouter
from app.services.analytics_service import AnalyticsService
from app.services.gemini_service import GeminiService
from app.services.notification_service import NotificationService
from app.services.realtime_manager import realtime_manager

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# MENSAJES PREDEFINIDOS — 0 tokens de Gemini
# ══════════════════════════════════════════════════════════════════════════════

MSG_MENU_ES = """¡Hola! 😊 Bienvenido/a a *LLV Wellness Clinic* ✨
Soy LLV Assistant, tu asistente virtual.

Para atenderte mejor, elige el servicio que te interesa escribiendo el número 👇

1️⃣ Pérdida de peso (Semaglutide / Tirzepatide)
2️⃣ Quemadores de grasa solos
3️⃣ Péptidos (Glow Blend, GHK-Cu)
4️⃣ NAD+
5️⃣ Estética (Botox, rellenos, depilación láser)
6️⃣ Limpiezas faciales / Dermatología
7️⃣ Sueros de vitaminas

Escríbeme el número de tu opción 💙"""

MSG_MENU_EN = """Hi there! 😊 Welcome to *LLV Wellness Clinic* ✨
I'm LLV Assistant, your virtual assistant.

Please choose the service you're interested in by typing the number 👇

1️⃣ Weight loss (Semaglutide / Tirzepatide)
2️⃣ Fat burners only
3️⃣ Peptides (Glow Blend, GHK-Cu)
4️⃣ NAD+
5️⃣ Aesthetics (Botox, fillers, laser hair removal)
6️⃣ Facials / Dermatology
7️⃣ Vitamin IV therapy

Type the number of your choice 💙"""

MSG_PESO_FILTRO = """Perfecto 😊

Antes de recomendarte el tratamiento ideal, necesito hacerte una pregunta rápida 👇

¿Es tu primera vez usando estos medicamentos?

1️⃣ Sí, soy nuevo/a
2️⃣ No, ya he usado antes (recompra)"""

MSG_NUEVO_INICIO = """Perfecto 😊 Quiero ayudarte a encontrar la mejor opción para ti ✨

Primero, aquí tienes nuestra guía completa 📩
👉 https://guiainstructivallv.my.canva.site/

Necesito conocerte un poco 👇

¿Cuál es tu *peso actual* en libras? ⚖️"""

MSG_RECOMPRA_INICIO = """Perfecto 😊 Para darte continuidad y recomendarte correctamente tu siguiente pedido, necesito validar algunos datos 👇

¿Qué producto estás usando actualmente?

1️⃣ Semaglutide
2️⃣ Tirzepatide"""

MSG_INTENCION_ENTREGA = """Perfecto, gracias por la info 😊

Para ir adelantando tu proceso y ayudarte más rápido 👇

¿Cómo te gustaría recibir tu tratamiento?

1️⃣ Entrega a domicilio 🚚 (Puerto Rico)
2️⃣ Envío postal 📦 (PR / LATAM / USA)
3️⃣ Recoger en clínica 🏥
4️⃣ Aplicación en clínica con cita ✨

Escríbeme el número de tu opción"""

MSG_HANDOFF = """¡Listo! 😊 Ya tengo tu información ✨

En unos minutos uno de nuestros asesores te escribirá para:
✔ Confirmar dosis
✔ Programar entrega o cita
✔ Finalizar tu pedido

📲 En breve uno de nuestros asesores te contactará personalmente.

Mientras tanto, si deseas agilizar tu proceso puedes escribir:
👉 *"QUIERO EMPEZAR"*
y te daremos atención prioritaria 💙"""

# Respuestas para otros servicios (opciones 2-7 del menú)
MSG_OTROS_SERVICIOS = {
    "2": "¡Perfecto! 😊 Los quemadores de grasa son ideales como complemento o solos para acelerar resultados ✨\n\n¿Cuándo te gustaría recibirlos?\n\n1️⃣ Entrega a domicilio 🚚\n2️⃣ Envío postal 📦\n3️⃣ Recoger en clínica 🏥",
    "3": "¡Excelente elección! 😊 Los péptidos (Glow Blend, GHK-Cu) son tratamientos de regeneración celular y bienestar ✨\n\nUn asesor especializado te orientará con el protocolo ideal 💙\n\n¿Cómo prefieres continuar?\n1️⃣ Entrega a domicilio 🚚\n2️⃣ Envío postal 📦\n3️⃣ Recoger en clínica 🏥",
    "4": "¡Interesante! 😊 El NAD+ es uno de nuestros tratamientos más potentes para energía y longevidad ✨\n\nEl protocolo y precio se personaliza según tus objetivos. Un especialista te asesorará 💙\n\n¿Cómo te gustaría proceder?\n1️⃣ Entrega / recogido\n2️⃣ Cita en clínica para aplicación",
    "5": "¡Perfecto! 😊 Tenemos servicios de estética de alta calidad ✨\n\n💉 *Consulta médica / Valoración: $30.00 USD*\n\n¿Qué te interesa?\n1️⃣ Botox / Rellenos\n2️⃣ Depilación láser\n3️⃣ Consulta médica ($30 USD)\n4️⃣ Otro servicio estético",
    "6": "¡Genial! 😊 Nuestras limpiezas faciales y dermatología son increíbles ✨\n\n• Microdermoabrasión: $35\n• Dermaplaning: $40\n• Limpieza Profunda: $55\n• Hydra Facial: $65\n\n¿Te gustaría agendar una cita? 📅",
    "7": "¡Perfecto! 😊 Nuestros sueros de vitaminas IV te darán energía y bienestar ✨\n\nEl protocolo se personaliza según tus objetivos. Un especialista te asesorará 💙\n\n¿Cómo prefieres recibirlos?\n1️⃣ Cita en clínica (aplicación)\n2️⃣ Consultar protocolo con asesor",
}

# Preguntas secuenciales para cliente NUEVO (pérdida de peso)
PREGUNTAS_NUEVO = [
    ("peso_actual", "¿Cuál es tu *peso actual* en libras? ⚖️"),
    ("meta_bajar", "¿Cuánto te gustaría bajar aproximadamente? 🎯\n(Ej: 10 libras, 20 libras, más de 40 libras)"),
    ("condicion_medica", "¿Tienes alguna condición médica? 💙\n(Ej: tiroides, diabetes, hipertensión, embarazo, SOP, ninguna)"),
    ("tratamiento_previo", "¿Has usado antes algún tratamiento para bajar de peso?\n1️⃣ Sí\n2️⃣ No"),
    ("objetivo_principal", "¿Qué es lo que más te gustaría mejorar hoy? ✨\n\n1️⃣ Bajar peso\n2️⃣ Controlar ansiedad/apetito\n3️⃣ Tener más energía\n4️⃣ Mejorar hábitos"),
    ("cuando_empezar", "¡Gracias por compartir eso! 😊✨\n\n¿Cuándo te gustaría empezar?\n\n1️⃣ Hoy mismo 🔥\n2️⃣ Esta semana\n3️⃣ Este mes\n4️⃣ Solo estoy averiguando"),
]

# Preguntas secuenciales para cliente RECOMPRA
PREGUNTAS_RECOMPRA = [
    ("producto_actual", "¿Qué producto estás usando actualmente?\n\n1️⃣ Semaglutide\n2️⃣ Tirzepatide"),
    ("dosis_actual", "¿Qué dosis usaste en tu último pedido? 💉\n(Ej: 0.25mg, 0.5mg, 2.5mg)"),
    ("bajo_peso", "¿Has bajado de peso? 🎯\n1️⃣ Sí → ¿cuánto aproximadamente?\n2️⃣ No"),
    ("efectos_secundarios", "¿Has tenido efectos secundarios?\n1️⃣ No\n2️⃣ Sí → ¿cuáles?"),
    ("objetivo_ahora", "¿Cuál es tu objetivo ahora? 🎯\n\n1️⃣ Seguir bajando\n2️⃣ Mantener peso\n3️⃣ Mejorar energía\n4️⃣ Controlar ansiedad/apetito"),
    ("cuando_empezar", "¡Gracias! Ya casi terminamos ✨\n\n¿Cuándo te gustaría recibir tu siguiente pedido?\n1️⃣ Hoy mismo 🔥\n2️⃣ Esta semana\n3️⃣ Este mes"),
]

# Campos requeridos por tipo de entrega
CAMPOS_REQUERIDOS = {
    "entrega_local":   ["nombre_completo", "telefono", "pueblo", "producto"],
    "envio_postal":    ["nombre_completo", "telefono", "direccion", "ciudad", "pais", "producto"],
    "recoger_clinica": ["nombre_completo", "telefono", "sede", "dia_preferido", "hora_aproximada", "producto"],
    "cita_servicio":   ["nombre_completo", "telefono", "servicio", "sede", "dia_preferido", "hora_aproximada"],
}

LABELS_CAMPOS = {
    "nombre_completo": "nombre completo (nombre y apellido)",
    "telefono":        "número de teléfono",
    "pueblo":          "pueblo de entrega",
    "producto":        "producto y dosis",
    "email":           "correo electrónico",
    "direccion":       "dirección completa",
    "ciudad":          "ciudad / estado",
    "pais":            "país de destino",
    "sede":            "sede (Arecibo o Bayamón)",
    "dia_preferido":   "día preferido",
    "hora_aproximada": "hora aproximada",
    "servicio":        "servicio que desea",
}

SOLICITUD_DATOS = {
    "entrega_local": (
        "¡Perfecto! 😊 Para coordinar tu entrega necesito:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Pueblo de entrega:*\n"
        "• *Correo electrónico (opcional):*\n\n"
        "Puedes responderme todo junto o uno a la vez 💙"
    ),
    "envio_postal": (
        "¡Perfecto! 😊 Para coordinar tu envío necesito:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Dirección completa:*\n"
        "• *Ciudad / Estado:*\n"
        "• *País:*\n"
        "• *Correo electrónico (opcional):*\n\n"
        "Puedes responderme todo junto o uno a la vez 💙"
    ),
    "recoger_clinica": (
        "Tenemos dos sedes 😊\n\n"
        "📍 *Arecibo* — 939-715-3161\n"
        "📍 *Bayamón* — 787-269-6244\n\n"
        "¿En cuál prefieres recoger? Y también necesito:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Día que te gustaría pasar:*\n"
        "• *Hora aproximada:*\n"
        "• *Correo electrónico (opcional):*"
    ),
    "cita_servicio": (
        "¡Perfecto! 😊 Para agendar tu cita necesito:\n\n"
        "📍 *Sede* (Arecibo o Bayamón):\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Día que te gustaría:*\n"
        "• *Hora aproximada:*\n"
        "• *Correo electrónico (opcional):*\n\n"
        "✨ Uno de nuestros especialistas confirmará tu cita muy pronto."
    ),
}

# Lead temperature según respuesta de "cuando empezar"
LEAD_TEMP_MAP = {
    "1": "caliente", "hoy": "caliente", "hoy mismo": "caliente",
    "2": "caliente", "esta semana": "caliente",
    "3": "templado", "este mes": "templado",
    "4": "frio", "solo averiguando": "frio", "averiguando": "frio",
}

_UNSUPPORTED = {
    "audio":    "🎤 Recibí un audio. Por ahora proceso mensajes de texto. Escríbeme lo que necesitas o envía *agente* para hablar con un asesor.",
    "video":    "🎥 Recibí un video. Por favor escríbeme en texto lo que necesitas.",
    "location": "📍 Recibí una ubicación. Escríbeme en texto lo que necesitas.",
    "sticker":  "🙂 ¡Gracias! ¿En qué puedo ayudarte hoy?",
    "reaction": None,
}

_PAYMENT_INSTRUCTIONS = {
    "zelle":       "💳 *Pago por Zelle:*\nEnvía {amount} al correo: _pagos@llvclinic.com_\nEn el concepto escribe tu nombre completo.",
    "ath":         "📱 *Pago por ATH Móvil:*\nEnvía {amount} al número: _787-800-5222_\nEn el mensaje escribe tu nombre completo.",
    "paypal":      "💻 *Pago por PayPal:*\nEnvía {amount} a: _pagos@llvclinic.com_\nSelecciona 'Amigos y familia' para evitar comisiones.",
    "credit_card": "💳 *Pago con Tarjeta:*\nUn asesor te enviará el link de pago seguro en breve.",
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE VALIDACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _validate_phone(v: str) -> bool:
    return len(re.sub(r"\D", "", v)) >= 10

def _validate_name(v: str) -> bool:
    return len(v.strip().split()) >= 2

def _validate_email(v: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))

def _detect_language(text: str) -> str:
    english_words = ["hi", "hello", "hey", "i want", "i need", "help", "what", "how", "weight", "loss"]
    lower = text.lower()
    return "en" if any(w in lower for w in english_words) else "es"

def _detect_lead_temp(text: str) -> str:
    lower = text.lower().strip()
    for key, temp in LEAD_TEMP_MAP.items():
        if key in lower:
            return temp
    return "templado"


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrchestratorResult:
    reply: str | None
    action_taken: str
    success: bool


class AIOrchestrator:
    def __init__(self, db: DBSession):
        self.db = db
        self.gemini = GeminiService()
        self.analytics = AnalyticsService(db)
        self.agent_router = AgentRouter(db)
        self.notifications = NotificationService(db)

    # ── ENTRY POINT ───────────────────────────────────────────────────────────

    def process(self, inbox_msg: InboxMessage) -> dict[str, Any]:
        number   = inbox_msg.whatsapp_number
        msg_type = inbox_msg.message_type or "text"
        text     = inbox_msg.content or ""
        media_id = inbox_msg.media_id

        # Tipos no soportados
        if msg_type in _UNSUPPORTED:
            reply = _UNSUPPORTED[msg_type]
            if reply:
                self._send(number, reply)
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": f"unsupported:{msg_type}"}

        # Comprobante de pago
        if msg_type in ("image", "document") and media_id:
            return self._handle_payment_proof(number, media_id, inbox_msg)

        patient  = self._get_or_create_patient(number, inbox_msg.profile_name)
        session  = self._get_or_create_session(number, patient)
        ctx      = self._load_ctx(session)
        is_new   = not self._has_history(session)

        inbound_log = self._log_msg(session.id, number, "inbound", text, msg_type,
                                    inbox_msg.meta_message_id, False)

        realtime_manager.broadcast_sync({
            "type": "new_message",
            "message_id": inbound_log.id,
            "session_id": session.id,
            "patient_id": patient.id,
            "customer_name": patient.full_name or inbox_msg.profile_name or "Cliente",
            "whatsapp_number": number,
            "direction": "inbound",
            "content": text,
            "message_type": msg_type,
            "assigned_agent_id": session.assigned_agent_id,
            "created_at": inbound_log.created_at.isoformat() if inbound_log.created_at else datetime.utcnow().isoformat(),
        })

        self.analytics.message_received(session.id, patient.id, msg_type)

        # Sesión completada — survey o nueva sesión
        if session.status == "completed":
            session, ctx, is_new = self._handle_completed_session(
                session, patient, number, text, inbox_msg
            )
            if session is None:
                return {"ok": True, "skipped": True, "reason": "completed_survey"}

        # Sesión en agente — solo escuchar
        if session.status == "in_agent":
            inbox_msg.status = "done"
            self.db.flush()
            return {"ok": True, "skipped": True, "reason": "in_agent_mode"}

        if is_new:
            self.notifications.increment_conversation()
            self.analytics.conversation_started(session.id, patient.id)

        # ── MÁQUINA DE ESTADOS DEL FLUJO ─────────────────────────────────────
        reply, ctx = self._run_flow(text, ctx, patient, session)

        patient.last_interaction_at = datetime.utcnow()
        self._save_ctx(session, ctx)

        if reply:
            self._send(number, reply)
            self._log_msg(session.id, number, "outbound", reply, "text", None, True)

        inbox_msg.status = "done"
        self.db.commit()

        logger.info("Orchestrator OK | number=%s | step=%s | session=%s",
                    number, ctx.get("flow_step"), session.id)
        return {"ok": True, "action": ctx.get("flow_step", "unknown")}

    # ── MÁQUINA DE ESTADOS ────────────────────────────────────────────────────

    def _run_flow(
        self, text: str, ctx: dict, patient: Patient, session: Session
    ) -> tuple[str, dict]:
        """
        Estados del flujo:
        - menu           → Mostrando menú inicial
        - peso_filtro    → Preguntando nuevo vs recompra
        - nuevo_preguntas → Secuencia de preguntas cliente nuevo
        - recompra_preguntas → Secuencia de preguntas recompra
        - intencion_entrega → Preguntando cómo quiere recibir
        - captura_datos  → Recogiendo datos de contacto/entrega
        - confirmacion   → Esperando SÍ del cliente
        - gemini_libre   → IA libre para casos complejos
        """
        step = ctx.get("flow_step", "menu")
        msg  = text.strip()

        # ── Detección de escalada directa (cualquier paso) ───────────────────
        escalation_kw = [
            "agente", "asesor", "asesora", "persona", "humano", "humana",
            "hablar con", "conectar con", "agent", "human", "queja", "reclamo",
            "quiero empezar",
        ]
        non_esc = ["precio", "costo", "cuánto", "disponible", "horario", "cuanto"]
        msg_lower = msg.lower()
        if any(kw in msg_lower for kw in escalation_kw):
            if not any(kw in msg_lower for kw in non_esc):
                return self._do_escalate(ctx, patient, session, reason=f"Cliente solicitó: {msg[:80]}")

        # ── PASO: MENÚ ────────────────────────────────────────────────────────
        if step == "menu":
            lang = _detect_language(msg)
            ctx["language"] = lang

            # Si responde con número válido del menú
            if msg in ("1", "2", "3", "4", "5", "6", "7"):
                ctx["menu_opcion"] = msg
                if msg == "1":
                    ctx["flow_step"] = "peso_filtro"
                    return MSG_PESO_FILTRO, ctx
                else:
                    ctx["flow_step"] = "intencion_entrega"
                    ctx["tipo_servicio"] = msg
                    respuesta = MSG_OTROS_SERVICIOS.get(msg, "")
                    if msg in ("2", "3", "6", "7"):
                        # Estos van directo a captura de datos
                        ctx["flow_step"] = "intencion_entrega"
                    elif msg in ("4", "5"):
                        ctx["flow_step"] = "gemini_libre"
                    return respuesta, ctx

            # Si no elige número → mostrar menú
            ctx["flow_step"] = "menu"
            lang = ctx.get("language", "es")
            return MSG_MENU_ES if lang != "en" else MSG_MENU_EN, ctx

        # ── PASO: FILTRO NUEVO vs RECOMPRA ────────────────────────────────────
        if step == "peso_filtro":
            if msg in ("1", "sí", "si", "nuevo", "nueva", "primera vez"):
                ctx["tipo_cliente"] = "nuevo"
                ctx["flow_step"] = "nuevo_preguntas"
                ctx["pregunta_index"] = 0
                ctx["respuestas_nuevo"] = {}
                return MSG_NUEVO_INICIO, ctx
            elif msg in ("2", "no", "recompra", "ya he usado", "ya use"):
                ctx["tipo_cliente"] = "recompra"
                ctx["flow_step"] = "recompra_preguntas"
                ctx["pregunta_index"] = 0
                ctx["respuestas_recompra"] = {}
                return MSG_RECOMPRA_INICIO, ctx
            else:
                # Respuesta no reconocida → repregunta
                return MSG_PESO_FILTRO, ctx

        # ── PASO: PREGUNTAS CLIENTE NUEVO ─────────────────────────────────────
        if step == "nuevo_preguntas":
            idx     = ctx.get("pregunta_index", 0)
            resps   = ctx.get("respuestas_nuevo", {})

            # Guardar respuesta de la pregunta anterior (si no es la primera)
            if idx > 0:
                campo_anterior = PREGUNTAS_NUEVO[idx - 1][0]
                resps[campo_anterior] = msg

            ctx["respuestas_nuevo"] = resps

            # ¿Hay más preguntas?
            if idx < len(PREGUNTAS_NUEVO):
                campo, pregunta = PREGUNTAS_NUEVO[idx]
                ctx["pregunta_index"] = idx + 1

                # Si ya guardamos la respuesta del campo anterior,
                # avanzamos normalmente. La primera iteración siempre muestra la pregunta.
                if idx == 0:
                    # Primera pregunta ya fue enviada con MSG_NUEVO_INICIO
                    # Guardar primer mensaje como peso_actual
                    resps["peso_actual"] = msg
                    ctx["respuestas_nuevo"] = resps
                    ctx["pregunta_index"] = 1
                    _, siguiente_pregunta = PREGUNTAS_NUEVO[1]
                    return siguiente_pregunta, ctx

                if idx < len(PREGUNTAS_NUEVO):
                    _, siguiente_pregunta = PREGUNTAS_NUEVO[idx]
                    return siguiente_pregunta, ctx

            # Todas las preguntas respondidas → registrar lead temp
            cuando = resps.get("cuando_empezar", "3")
            ctx["lead_temperature"] = _detect_lead_temp(cuando)
            ctx["flow_step"] = "intencion_entrega"

            # Generar recomendación con Gemini (ya tenemos datos)
            faq_items   = self._load_faq()
            history     = self._build_history(session)
            patient_ctx = self._patient_context(patient)
            resumen_ctx = f"\n[DATOS CLIENTE NUEVO: {_json.dumps(resps, ensure_ascii=False)}]"

            gemini_result = self.gemini.process_message(
                user_message=f"El cliente ha completado el formulario. Datos: {_json.dumps(resps, ensure_ascii=False)}. Genera la recomendación de producto y dosis.",
                history=history,
                faq_items=faq_items,
                patient=patient_ctx,
            )
            recomendacion = gemini_result.get("text") or (
                "Gracias por tu información 😊✨\n\n"
                "Basado en tu perfil, un especialista te recomendará el tratamiento ideal.\n"
            )

            return recomendacion + "\n\n" + MSG_INTENCION_ENTREGA, ctx

        # ── PASO: PREGUNTAS RECOMPRA ──────────────────────────────────────────
        if step == "recompra_preguntas":
            idx   = ctx.get("pregunta_index", 0)
            resps = ctx.get("respuestas_recompra", {})

            if idx > 0:
                campo_anterior = PREGUNTAS_RECOMPRA[idx - 1][0]
                resps[campo_anterior] = msg

            ctx["respuestas_recompra"] = resps

            if idx == 0:
                # Primera respuesta ya fue la elección de producto
                resps["producto_actual"] = msg
                ctx["respuestas_recompra"] = resps
                ctx["pregunta_index"] = 1
                _, siguiente = PREGUNTAS_RECOMPRA[1]
                return siguiente, ctx

            if idx < len(PREGUNTAS_RECOMPRA):
                _, siguiente = PREGUNTAS_RECOMPRA[idx]
                ctx["pregunta_index"] = idx + 1
                return siguiente, ctx

            # Completado
            cuando = resps.get("cuando_empezar", "2")
            ctx["lead_temperature"] = _detect_lead_temp(cuando)
            ctx["flow_step"] = "intencion_entrega"

            # Ajuste de dosis con Gemini
            faq_items   = self._load_faq()
            history     = self._build_history(session)
            patient_ctx = self._patient_context(patient)

            gemini_result = self.gemini.process_message(
                user_message=f"Cliente recompra completó formulario. Datos: {_json.dumps(resps, ensure_ascii=False)}. Genera ajuste de dosis recomendado.",
                history=history,
                faq_items=faq_items,
                patient=patient_ctx,
            )
            ajuste = gemini_result.get("text") or "¡Perfecto! Ya casi terminamos ✨\n"

            return ajuste + "\n\n" + MSG_INTENCION_ENTREGA, ctx

        # ── PASO: INTENCIÓN DE ENTREGA ────────────────────────────────────────
        if step == "intencion_entrega":
            if msg in ("1", "entrega", "domicilio", "a domicilio"):
                ctx["tipo_entrega"] = "entrega_local"
            elif msg in ("2", "envio", "envío", "postal", "correo"):
                ctx["tipo_entrega"] = "envio_postal"
            elif msg in ("3", "recoger", "recojo", "clinica", "clínica"):
                ctx["tipo_entrega"] = "recoger_clinica"
            elif msg in ("4", "cita", "aplicacion", "aplicación"):
                ctx["tipo_entrega"] = "cita_servicio"
            else:
                return MSG_INTENCION_ENTREGA, ctx

            ctx["flow_step"]      = "captura_datos"
            ctx["datos"]          = {}
            ctx["retry_counts"]   = {}
            ctx["campo_actual"]   = None
            tipo = ctx["tipo_entrega"]
            return SOLICITUD_DATOS[tipo], ctx

        # ── PASO: CAPTURA DE DATOS ────────────────────────────────────────────
        if step == "captura_datos":
            return self._handle_captura_datos(msg, ctx, patient, session)

        # ── PASO: CONFIRMACIÓN ────────────────────────────────────────────────
        if step == "confirmacion":
            if msg.lower() in ("sí", "si", "yes", "ok", "okay", "correcto", "confirmo", "✅"):
                ctx["flow_step"] = "handoff"
                lead_temp = ctx.get("lead_temperature", "")
                datos     = ctx.get("datos", {})
                tipo      = ctx.get("tipo_entrega", "")
                summary   = self._build_agent_summary(datos, tipo, lead_temp)

                result = self._action_escalate_to_agent(
                    {"reason": "Datos confirmados — listo para procesar", "summary": summary,
                     "lead_temperature": lead_temp, "data_confirmed": True},
                    patient, session
                )
                return result.reply or MSG_HANDOFF, ctx
            else:
                # El cliente quiere corregir algo → Gemini libre con contexto
                ctx["flow_step"] = "gemini_libre"
                ctx["correccion"] = msg
                return self._handle_gemini_libre(msg, ctx, patient, session)

        # ── PASO: GEMINI LIBRE ────────────────────────────────────────────────
        if step == "gemini_libre":
            return self._handle_gemini_libre(msg, ctx, patient, session)

        # Default → mostrar menú
        ctx["flow_step"] = "menu"
        return MSG_MENU_ES, ctx

    # ── CAPTURA DE DATOS (validación con reintentos) ──────────────────────────

    def _handle_captura_datos(
        self, msg: str, ctx: dict, patient: Patient, session: Session
    ) -> tuple[str, dict]:
        tipo          = ctx.get("tipo_entrega", "entrega_local")
        datos         = ctx.get("datos", {})
        retry_counts  = ctx.get("retry_counts", {})
        campo_actual  = ctx.get("campo_actual")
        campos_req    = CAMPOS_REQUERIDOS.get(tipo, [])

        # Intentar extraer datos del mensaje con Gemini para texto libre
        datos_extraidos = self._extract_data_from_message(msg, tipo, datos)
        datos.update(datos_extraidos)

        # Si había un campo específico pendiente, guardarlo directamente
        if campo_actual and not datos.get(campo_actual):
            datos[campo_actual] = msg.strip()

        ctx["datos"] = datos

        # Validar todos los campos requeridos
        for campo in campos_req:
            valor = datos.get(campo, "").strip()
            if not valor:
                retries = retry_counts.get(campo, 0)
                if retries >= 2:
                    # Escalar con datos parciales
                    return self._do_escalate(
                        ctx, patient, session,
                        reason=f"Dato obligatorio no obtenido tras 2 intentos: {LABELS_CAMPOS.get(campo, campo)}",
                        missing=LABELS_CAMPOS.get(campo, campo)
                    )
                retry_counts[campo] = retries + 1
                ctx["retry_counts"] = retry_counts
                ctx["campo_actual"] = campo
                if retries == 0:
                    return f"Necesito tu *{LABELS_CAMPOS.get(campo, campo)}* para continuar 😊", ctx
                else:
                    return f"Por favor compárteme tu *{LABELS_CAMPOS.get(campo, campo)}* — es necesario para procesar tu solicitud 💙", ctx

            # Validar formato
            valido, error_msg = self._validate_field(campo, valor)
            if not valido:
                retries = retry_counts.get(campo, 0)
                if retries >= 2:
                    return self._do_escalate(
                        ctx, patient, session,
                        reason=f"Dato inválido tras 2 intentos: {LABELS_CAMPOS.get(campo, campo)}"
                    )
                retry_counts[campo] = retries + 1
                ctx["retry_counts"]  = retry_counts
                ctx["campo_actual"]  = campo
                datos[campo] = ""  # limpiar valor inválido
                ctx["datos"] = datos
                return error_msg, ctx

        # Email opcional — pedir si no se ha dado y no se ha reintentado
        email_val = datos.get("email", "").strip()
        email_retries = retry_counts.get("email", 0)
        if not email_val and email_retries < 1:
            retry_counts["email"] = 1
            ctx["retry_counts"]   = retry_counts
            ctx["campo_actual"]   = "email"
            return "¿Tienes un *correo electrónico*? (opcional — escribe 'no' si prefieres omitirlo) 📧", ctx

        if email_val and email_val.lower() in ("no", "n/a", "omitir", "sin correo"):
            datos["email"] = ""
            ctx["datos"] = datos

        # Todos los datos completos → mostrar resumen de confirmación
        ctx["campo_actual"] = None
        ctx["flow_step"]    = "confirmacion"
        summary_msg = self._build_confirmation_msg(datos, tipo)
        return summary_msg, ctx

    def _extract_data_from_message(self, msg: str, tipo: str, datos_existentes: dict) -> dict:
        """
        Extrae datos del mensaje usando heurísticas simples.
        Si el mensaje tiene múltiples líneas o pares clave-valor, los parsea.
        """
        extraidos = {}
        msg_lower = msg.lower()

        # Detectar nombre completo (2+ palabras que empiezan con mayúscula)
        if not datos_existentes.get("nombre_completo"):
            words = msg.strip().split()
            if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w[0].isalpha()):
                extraidos["nombre_completo"] = msg.strip()

        # Detectar teléfono
        if not datos_existentes.get("telefono"):
            phone_match = re.search(r"[\d\s\-\+\(\)]{10,}", msg)
            if phone_match:
                extraidos["telefono"] = phone_match.group().strip()

        # Detectar email
        if not datos_existentes.get("email"):
            email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", msg)
            if email_match:
                extraidos["email"] = email_match.group()

        # Detectar sede
        if not datos_existentes.get("sede"):
            if "arecibo" in msg_lower:
                extraidos["sede"] = "Arecibo"
            elif "bayam" in msg_lower:
                extraidos["sede"] = "Bayamón"

        return extraidos

    def _validate_field(self, campo: str, valor: str) -> tuple[bool, str]:
        if campo == "nombre_completo":
            if not _validate_name(valor):
                return False, "Por favor escribe tu *nombre y apellido completos* 😊\n(Ej: María García)"
        elif campo == "telefono":
            if not _validate_phone(valor):
                return False, "Por favor escribe un número de teléfono válido (mínimo 10 dígitos) 📞"
        elif campo == "email":
            if valor and not _validate_email(valor):
                return False, "Por favor escribe un correo electrónico válido (ej: nombre@gmail.com) 📧"
        elif campo == "direccion":
            if len(valor) < 10:
                return False, "Por favor escribe tu dirección completa (calle, número, ciudad) 📍"
        elif campo == "pueblo":
            if len(valor) < 3:
                return False, "Por favor escribe el nombre completo de tu pueblo 🗺️"
        return True, ""

    def _build_confirmation_msg(self, datos: dict, tipo: str) -> str:
        lines = [
            "¡Casi listo! 😊 Antes de pasarte con nuestro equipo, confirma que tus datos son correctos ✨\n",
            f"👤 *Nombre:* {datos.get('nombre_completo', '—')}",
            f"📞 *Teléfono:* {datos.get('telefono', '—')}",
        ]
        if datos.get("email"):
            lines.append(f"📧 *Email:* {datos['email']}")

        if tipo == "entrega_local":
            lines.append(f"🚚 *Entrega en:* {datos.get('pueblo', '—')}")
        elif tipo == "envio_postal":
            addr = ", ".join(filter(None, [datos.get("direccion"), datos.get("ciudad"), datos.get("pais")]))
            lines.append(f"📦 *Envío a:* {addr}")
        elif tipo == "recoger_clinica":
            lines.append(f"🏥 *Recoger en:* {datos.get('sede', '—')}")
            lines.append(f"📅 *Día:* {datos.get('dia_preferido', '—')} | ⏰ *Hora:* {datos.get('hora_aproximada', '—')}")
        elif tipo == "cita_servicio":
            lines.append(f"💉 *Servicio:* {datos.get('servicio', '—')}")
            lines.append(f"🏥 *Sede:* {datos.get('sede', '—')}")
            lines.append(f"📅 *Día:* {datos.get('dia_preferido', '—')} | ⏰ *Hora:* {datos.get('hora_aproximada', '—')}")

        if datos.get("producto") and tipo not in ("cita_servicio",):
            lines.append(f"💉 *Producto:* {datos['producto']}")

        lines.append(
            "\n¿Todo está correcto?\n"
            "✅ Escribe *SÍ* para confirmar\n"
            "✏️ O dime qué necesitas corregir"
        )
        return "\n".join(lines)

    def _build_agent_summary(self, datos: dict, tipo: str, lead_temp: str) -> str:
        emoji = {"caliente": "🔥", "templado": "🌤️", "frio": "❄️"}.get(lead_temp, "")
        lines = [
            f"{'='*40}",
            f"RESUMEN AGENTE {emoji} LEAD {lead_temp.upper() if lead_temp else 'N/A'}",
            f"{'='*40}",
        ]
        for campo, label in LABELS_CAMPOS.items():
            valor = datos.get(campo, "")
            if valor:
                lines.append(f"• {label.capitalize()}: {valor}")

        tipo_labels = {
            "entrega_local":   "🚚 Entrega local PR",
            "envio_postal":    "📦 Envío postal",
            "recoger_clinica": "🏥 Recoger en clínica",
            "cita_servicio":   "💉 Cita/servicio",
        }
        if tipo:
            lines.append(f"• Tipo: {tipo_labels.get(tipo, tipo)}")
        lines.append(f"{'='*40}")
        lines.append("✅ DATOS CONFIRMADOS POR EL CLIENTE")
        return "\n".join(lines)

    # ── GEMINI LIBRE ──────────────────────────────────────────────────────────

    def _handle_gemini_libre(
        self, msg: str, ctx: dict, patient: Patient, session: Session
    ) -> tuple[str, dict]:
        faq_items   = self._load_faq()
        history     = self._build_history(session)
        patient_ctx = self._patient_context(patient)

        extra = ""
        if ctx.get("datos"):
            extra = f"\n[DATOS RECOPILADOS: {_json.dumps(ctx.get('datos', {}), ensure_ascii=False)}]"
        if ctx.get("correccion"):
            extra += f"\n[CLIENTE QUIERE CORREGIR: {ctx['correccion']}. Actualiza el dato y muestra el resumen de confirmación.]"

        gemini_result = self.gemini.process_message(
            user_message=msg + extra,
            history=history,
            faq_items=faq_items,
            patient=patient_ctx,
        )

        self.analytics.ai_response(session.id, patient.id, gemini_result.get("function_call"))

        if gemini_result.get("function_call"):
            result = self._execute_action(
                gemini_result["function_call"],
                gemini_result["function_args"] or {},
                patient, session
            )
            return result.reply or "", ctx

        reply = gemini_result.get("text") or "¿En qué más puedo ayudarte? 😊"
        return reply, ctx

    # ── ESCALADA A AGENTE ─────────────────────────────────────────────────────

    def _do_escalate(
        self,
        ctx: dict,
        patient: Patient,
        session: Session,
        reason: str = "Solicitud del cliente",
        missing: str = "",
    ) -> tuple[str, dict]:
        datos     = ctx.get("datos", {})
        tipo      = ctx.get("tipo_entrega", "")
        lead_temp = ctx.get("lead_temperature", "")
        summary   = self._build_agent_summary(datos, tipo, lead_temp)
        if missing:
            summary += f"\n⚠️ DATO FALTANTE: {missing}"

        result = self._action_escalate_to_agent(
            {"reason": reason, "summary": summary, "lead_temperature": lead_temp, "data_confirmed": False},
            patient, session
        )
        ctx["flow_step"] = "handoff"
        return result.reply or MSG_HANDOFF, ctx

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _execute_action(self, fn_name: str, fn_args: dict, patient: Patient, session: Session) -> OrchestratorResult:
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
            return OrchestratorResult(reply="Estoy procesando tu solicitud. 🙏", action_taken="unknown", success=False)
        return handler(fn_args, patient, session)

    def _action_identify_patient(self, args, patient, session):
        if args.get("full_name"):
            patient.full_name = args["full_name"].strip()
        if args.get("location_type") in ("puerto_rico", "latam", "usa"):
            patient.location_type = args["location_type"]
        self.db.flush()
        name = patient.full_name or "estimado/a cliente"
        reply = (
            f"¡Hola de nuevo, *{name}*! 👋 Qué bueno verte por aquí. ¿Vienes por tu tratamiento habitual? 😊"
            if patient.is_recurrent else
            f"¡Perfecto, *{name}*! Ya tengo tus datos. ¿En qué puedo ayudarte hoy? 💚"
        )
        return OrchestratorResult(reply=reply, action_taken="identify_patient", success=True)

    def _action_evaluate_patient(self, args, patient, session):
        ctx = self._load_ctx(session)
        ctx.setdefault("evaluation", {}).update({
            "type": "new_patient",
            "recommended_product": args.get("recommended_product", "semaglutide"),
            "recommended_dose": args.get("recommended_dose", "0.25 MG"),
            "lead_temperature": args.get("lead_temperature", ""),
            **{k: args.get(k) for k in ["used_glp1_before", "current_weight_lbs", "weight_loss_goal_lbs", "medical_conditions", "main_goal"]},
        })
        self._save_ctx(session, ctx)
        product = args.get("recommended_product", "semaglutide").capitalize()
        dose    = args.get("recommended_dose", "0.25 MG")
        self.analytics.track("patient_evaluated", session_id=session.id, patient_id=patient.id, product=product, dose=dose, type="new")
        reply = (
            f"Perfecto, gracias por la info 😊\n\n"
            f"En tu caso, lo más recomendable es iniciar con *{product}* en dosis *{dose}* 💉✨\n"
            f"Controla el apetito y acelera la pérdida de peso de forma progresiva.\n\n"
            f"¿Te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍"
        )
        return OrchestratorResult(reply=reply, action_taken="evaluate_patient", success=True)

    def _action_evaluate_reorder(self, args, patient, session):
        ctx = self._load_ctx(session)
        adj = args.get("dose_adjustment", "mantener")
        product  = args.get("current_product", "").capitalize()
        new_dose = args.get("new_recommended_dose", "")
        ctx.setdefault("evaluation", {}).update({"type": "reorder", **args})
        self._save_ctx(session, ctx)
        adj_texts = {
            "subir":         f"Lo ideal es *subir la dosis* 📈 → *{product}* en *{new_dose}* 💉✨",
            "bajar":         f"Lo mejor es *ajustar la dosis* para que te sientas mejor 💉✨ → *{product}* en *{new_dose}*",
            "mantenimiento": "¡Qué bueno! 😍 Pasamos a *fase de mantenimiento* — aplicación cada 15 días ✨",
        }
        adj_text = adj_texts.get(adj, f"Súper 😊 vas muy bien. Mantén la misma dosis por ahora 👍✨")
        self.analytics.track("patient_evaluated", session_id=session.id, patient_id=patient.id, product=product, dose=new_dose, type="reorder")
        return OrchestratorResult(
            reply=adj_text + "\n\n¿Te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍",
            action_taken="evaluate_reorder", success=True
        )

    def _action_schedule_appointment(self, args, patient, session):
        service = args.get("service", "").strip()
        if not service:
            return OrchestratorResult(reply="Para agendar tu cita, ¿qué servicio te interesa?", action_taken="appt_missing_service", success=False)
        appt = Appointment(
            patient_id=patient.id, session_id=session.id,
            full_name=args.get("full_name", patient.full_name or ""),
            phone=args.get("phone", patient.whatsapp_number),
            service=service, clinic=args.get("clinic", "latam"),
            medical_conditions=args.get("medical_conditions"), status="pending_confirm",
        )
        if args.get("preferred_date"):
            try: appt.preferred_date = date.fromisoformat(args["preferred_date"])
            except Exception: pass
        self.db.add(appt); patient.is_recurrent = 1; self.db.flush()
        self.analytics.appointment_created(session.id, patient.id, service, appt.clinic)
        return OrchestratorResult(
            reply=f"✅ Cita registrada para *{service}*. Nuestro equipo confirmará tu horario en Vagaro pronto. ¿Alguna otra pregunta? 😊",
            action_taken="appointment_created", success=True
        )

    def _action_register_delivery(self, args, patient, session):
        from app.db.models.delivery import Delivery
        town    = args.get("delivery_town", "").strip()
        service = args.get("service_treatment", "").strip()
        if not town:
            return OrchestratorResult(reply="¿En qué pueblo de Puerto Rico te hacemos la entrega?", action_taken="delivery_missing_town", success=False)
        delivery = Delivery(
            patient_id=patient.id, session_id=session.id,
            patient_name=args.get("patient_name", patient.full_name or ""),
            phone=args.get("phone", patient.whatsapp_number),
            service_treatment=service, amount_to_pay=args.get("amount_to_pay"),
            delivery_town=town, status="pending",
        )
        self.db.add(delivery); patient.is_recurrent = 1; self.db.flush()
        self.analytics.track("delivery_created", session_id=session.id, patient_id=patient.id, service=service, town=town)
        return OrchestratorResult(
            reply=f"✅ Pedido registrado — entrega en *{town}*. Nuestro equipo coordinará contigo pronto 💙",
            action_taken="delivery_created", success=True
        )

    def _action_register_shipment(self, args, patient, session):
        from app.db.models.delivery import Shipment
        address = args.get("postal_address", "").strip()
        service = args.get("service_treatment", "").strip()
        if not address:
            return OrchestratorResult(
                reply="Para el envío necesito tu dirección completa:\n• Calle y número\n• Ciudad / Estado\n• País\n• Código postal",
                action_taken="shipment_missing_address", success=False
            )
        shipment = Shipment(
            patient_id=patient.id, session_id=session.id,
            patient_name=args.get("patient_name", patient.full_name or ""),
            phone=args.get("phone", patient.whatsapp_number), email=args.get("email"),
            postal_address=address, city=args.get("city"), state_province=args.get("state_province"),
            country=args.get("country", "Puerto Rico"), zip_code=args.get("zip_code"),
            service_treatment=service, amount_paid=args.get("amount_paid"), status="pending",
        )
        self.db.add(shipment); patient.is_recurrent = 1; self.db.flush()
        self.analytics.track("shipment_created", session_id=session.id, patient_id=patient.id, service=service, country=shipment.country)
        return OrchestratorResult(
            reply=f"✅ Envío registrado a *{address}*. Te enviaremos el número de rastreo pronto 💙",
            action_taken="shipment_created", success=True
        )

    def _action_send_payment_link(self, args, patient, session):
        method  = args.get("payment_method", "zelle").lower()
        product = args.get("product_service", "Tratamiento LLV")
        amount  = args.get("amount")
        amount_text = f"${amount:.2f} USD" if amount else "el monto indicado"
        payment = Payment(
            patient_id=patient.id, session_id=session.id, product_service=product,
            amount=amount, currency="USD",
            payment_method=method if method in ("link","ath","credit_card","zelle","paypal","apple_pay") else "other",
            status="link_sent",
        )
        self.db.add(payment); self.db.flush()
        self.analytics.payment_sent(session.id, patient.id, method, product, amount)
        instructions = _PAYMENT_INSTRUCTIONS.get(method, "Un asesor te enviará las instrucciones de pago.").format(amount=amount_text)
        return OrchestratorResult(
            reply=f"¡Perfecto! Aquí las instrucciones de pago de *{product}*:\n\n{instructions}\n\n📸 Envía el comprobante aquí para verificarlo 😊",
            action_taken="payment_sent", success=True
        )

    def _action_escalate_to_agent(self, args, patient, session):
        reason    = args.get("reason", "Solicitud del cliente")
        summary   = args.get("summary", "")
        lead_temp = args.get("lead_temperature", "")

        if not summary:
            history     = self._build_history(session)
            patient_ctx = self._patient_context(patient)
            summary     = self.gemini.generate_agent_summary(history, patient_ctx)

        location = patient.location_type or "latam"
        agent    = self.agent_router.assign_agent(session, location)

        if not agent:
            return OrchestratorResult(
                reply="Intenté conectarte con un asesor pero no hay disponibilidad ahora.\nHorario: Lun–Vie 8AM–5PM | Sáb 8AM–1PM 💙",
                action_taken="agent_unavailable", success=False
            )

        ctx = self._load_ctx(session)
        ctx.update({
            "agent_summary":      summary,
            "escalation_reason":  reason,
            "lead_temperature":   lead_temp,
            "escalated_at":       datetime.utcnow().isoformat(),
        })
        self._save_ctx(session, ctx)

        self.analytics.agent_handoff(session.id, patient.id, agent.id, reason)

        try:
            self.notifications.notify_agent_escalation(
                agent_email=agent.email, agent_name=agent.name,
                patient_name=patient.full_name or "Cliente",
                patient_number=patient.whatsapp_number,
                reason=reason, ai_summary=summary, session_id=session.id,
            )
        except Exception as e:
            logger.warning("No se pudo notificar al agente: %s", e)

        lead_emoji = {"caliente": "🔥", "templado": "🌤️", "frio": "❄️"}.get(lead_temp, "")
        return OrchestratorResult(
            reply=(
                f"Perfecto 😊✨ Ya tengo toda la información necesaria.\n\n"
                f"Voy a pasar tu caso a uno de nuestros especialistas para darte una recomendación personalizada 💙\n\n"
                f"📲 *{agent.name}* te contactará en breve."
            ),
            action_taken="agent_handoff", success=True
        )

    def _action_register_payment_proof(self, args, patient, session):
        media_id = args.get("media_id", "")
        product  = args.get("product_service", "Tratamiento LLV")
        payment  = (
            self.db.query(Payment)
            .filter(Payment.session_id == session.id, Payment.status == "link_sent")
            .order_by(Payment.created_at.desc()).first()
        )
        if payment:
            payment.proof_media_id = media_id; payment.status = "proof_received"
        else:
            payment = Payment(patient_id=patient.id, session_id=session.id, product_service=product, payment_method="other", proof_media_id=media_id, status="proof_received")
            self.db.add(payment)
        self.db.flush()
        self.analytics.payment_proof_received(session.id, patient.id)
        return OrchestratorResult(
            reply="✅ ¡Recibí tu comprobante! Lo verificaremos en breve y te confirmamos 💙 ¿Algo más en que pueda ayudarte?",
            action_taken="payment_proof_received", success=True
        )

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _handle_completed_session(self, session, patient, number, text, inbox_msg):
        ctx = self._load_ctx(session)
        if ctx.get("survey_answered"):
            new_session = Session(patient_id=patient.id, whatsapp_number=number, status="active", context_json={"flow_step": "menu", "history": []})
            self.db.add(new_session); self.db.flush()
            return new_session, self._load_ctx(new_session), True

        score = None
        stripped = text.strip()
        if stripped in ("1","2","3","4","5"):
            score = int(stripped)
        elif "⭐" in stripped:
            score = stripped.count("⭐")

        if score and 1 <= score <= 5:
            agent_id = session.assigned_agent_id
            self.analytics.track("satisfaction_received", session_id=session.id, patient_id=patient.id, agent_id=agent_id, score=score)
            ctx["survey_answered"] = True
            self._save_ctx(session, ctx)
            stars = "⭐" * score
            self._send(number, f"¡Gracias por tu calificación! {stars}\nTu opinión es muy importante 💙✨")
            inbox_msg.status = "done"; self.db.flush()
            return None, None, None

        new_session = Session(patient_id=patient.id, whatsapp_number=number, status="active", context_json={"flow_step": "menu", "history": []})
        self.db.add(new_session); self.db.flush()
        return new_session, self._load_ctx(new_session), True

    def _handle_payment_proof(self, number, media_id, inbox_msg):
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)
        inbound_log = self._log_msg(session.id, number, "inbound", f"[media:{media_id}]",
                                    inbox_msg.message_type, inbox_msg.meta_message_id, False)
        realtime_manager.broadcast_sync({
            "type": "new_message", "message_id": inbound_log.id,
            "session_id": session.id, "patient_id": patient.id,
            "customer_name": patient.full_name or "Cliente", "whatsapp_number": number,
            "direction": "inbound", "content": f"[media:{media_id}]",
            "message_type": inbox_msg.message_type,
            "assigned_agent_id": session.assigned_agent_id,
            "created_at": inbound_log.created_at.isoformat() if inbound_log.created_at else datetime.utcnow().isoformat(),
        })
        result = self._action_register_payment_proof({"media_id": media_id}, patient, session)
        if result.reply:
            self._send(number, result.reply)
            self._log_msg(session.id, number, "outbound", result.reply, "text", None, True)
        inbox_msg.status = "done"; self.db.commit()
        return {"ok": True, "action": "payment_proof_received"}

    def _load_ctx(self, session: Session) -> dict:
        ctx = session.context_json or {}
        if isinstance(ctx, str):
            try: ctx = _json.loads(ctx)
            except Exception: ctx = {}
        if "flow_step" not in ctx:
            ctx["flow_step"] = "menu"
        return ctx

    def _save_ctx(self, session: Session, ctx: dict):
        session.context_json = copy.deepcopy(ctx)
        flag_modified(session, "context_json")
        self.db.flush()

    def _get_or_create_patient(self, number, profile_name=None):
        patient = self.db.query(Patient).filter(Patient.whatsapp_number == number).first()
        if not patient:
            patient = Patient(whatsapp_number=number, full_name=profile_name)
            self.db.add(patient); self.db.flush()
        return patient

    def _get_or_create_session(self, number, patient):
        session = (
            self.db.query(Session)
            .filter(Session.whatsapp_number == number, Session.status.in_(["active", "in_agent"]))
            .order_by(Session.created_at.desc()).first()
        )
        if not session:
            from datetime import timedelta
            recent = (
                self.db.query(Session)
                .filter(Session.whatsapp_number == number, Session.status == "completed",
                        Session.updated_at >= datetime.utcnow() - timedelta(hours=24))
                .order_by(Session.updated_at.desc()).first()
            )
            if recent: return recent
            session = Session(patient_id=patient.id, whatsapp_number=number, status="active", context_json={"flow_step": "menu", "history": []})
            self.db.add(session); self.db.flush()
        return session

    def _has_history(self, session):
        from app.db.models.messaging import MessageLog as MsgLog
        return self.db.query(MsgLog).filter(MsgLog.session_id == session.id).first() is not None

    def _load_faq(self):
        return [{"question": f.question, "answer": f.answer, "category": f.category}
                for f in self.db.query(FAQ).filter(FAQ.is_active == 1).all()]

    def _build_history(self, session):
        from app.db.models.messaging import MessageLog as MsgLog
        logs = (self.db.query(MsgLog)
                .filter(MsgLog.session_id == session.id, MsgLog.message_type == "text")
                .order_by(MsgLog.created_at.desc()).limit(20).all())
        return [{"role": "user" if not l.sent_by_bot else "assistant", "content": l.content or ""}
                for l in reversed(logs)]

    def _patient_context(self, patient):
        if not patient: return None
        return {"whatsapp_number": patient.whatsapp_number, "full_name": patient.full_name,
                "location_type": patient.location_type, "is_recurrent": bool(patient.is_recurrent)}

    def _log_msg(self, session_id, number, direction, content, msg_type, meta_id, sent_by_bot):
        from app.db.models.messaging import MessageLog as MsgLog
        log = MsgLog(session_id=session_id, whatsapp_number=number,direction=direction,content=content, message_type=msg_type,meta_message_id=meta_id,sent_by_bot=1 if sent_by_bot else 0)
        self.db.add(log); self.db.flush()
        return log

    def _send(self, to, text):
        import json as _j
        self.db.add(OutboxMessage(whatsapp_number=to,payload_json=_j.dumps({"to": to, "text": text}), status="pending"))
        self.db.flush()