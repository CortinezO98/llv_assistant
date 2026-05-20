"""
app/services/bot_service.py

Orquestador principal del bot LLV Assistant.
Arquitectura híbrida:
    - Menú + preguntas predefinidas → 0 tokens Gemini
    - Recomendación final + casos complejos → Gemini IA
    - Validación de datos + resumen de confirmación → obligatorio antes del handoff
    - Escalamiento automático por intención de pago o comprobante recibido
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.agent import Agent
from app.db.models.appointment import Appointment
from app.db.models.messaging import FAQ, InboxMessage, MessageLog, OutboxMessage
from app.db.models.patient import Patient
from app.db.models.payment import Payment
from app.db.models.session import Session
from app.services.agent_router import AgentRouter
from app.services.gemini_service import GeminiService
from app.services.notification_service import NotificationService
from app.services.payment_escalation import escalate_payment_intent

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# MENSAJES DEL MENÚ PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

MENU_MSG = """¡Hola! 😊 Bienvenido/a a *LLV Wellness Clinic* ✨
Soy LLV Assistant, tu asistente virtual. Para atenderte mejor, elige el servicio que te interesa escribiendo el número 👇

1️⃣ Pérdida de peso (Semaglutide / Tirzepatide)
2️⃣ Quemadores de grasa solos
3️⃣ Péptidos (Glow Blend, GHK-Cu)
4️⃣ NAD+
5️⃣ Estética (Botox, rellenos, depilación láser)
6️⃣ Limpiezas faciales / Dermatología
7️⃣ Sueros de vitaminas
8️⃣ Rejuvenecimiento vaginal
9️⃣ Morpheus (rostro, cuello y corporal)

Escríbeme el número de tu opción 💙"""

MENU_MSG_EN = """Hi there! 😊 Welcome to *LLV Wellness Clinic* ✨
I'm LLV Assistant, your virtual assistant. Please choose the service you're interested in by typing the number 👇

1️⃣ Weight loss (Semaglutide / Tirzepatide)
2️⃣ Fat burners only
3️⃣ Peptides (Glow Blend, GHK-Cu)
4️⃣ NAD+
5️⃣ Aesthetics (Botox, fillers, laser hair removal)
6️⃣ Facials / Dermatology
7️⃣ Vitamin IV therapy
8️⃣ Vaginal rejuvenation
9️⃣ Morpheus (face, neck and body)

Type the number of your choice 💙"""


# ══════════════════════════════════════════════════════════════════════════════
# FLUJOS DE PREGUNTAS POR OPCIÓN DEL MENÚ
# ══════════════════════════════════════════════════════════════════════════════

PREGUNTAS_NUEVO = [
    ("peso_actual", "¿Cuál es tu *peso actual* en libras? ⚖️"),
    (
        "meta_bajar",
        "¿Cuánto te gustaría bajar aproximadamente? 🎯\n"
        "_(Ej: 10 libras, 20 libras, más de 40 libras)_",
    ),
    (
        "condicion_medica",
        "¿Tienes alguna condición médica? 💙\n"
        "_(Ej: tiroides, diabetes, embarazo, hipertensión, SOP, ninguna)_",
    ),
    (
        "tratamiento_previo",
        "¿Has usado antes algún tratamiento para bajar de peso?\n"
        "1️⃣ Sí\n"
        "2️⃣ No",
    ),
    (
        "objetivo_principal",
        "¿Qué es lo que más te gustaría mejorar hoy? ✨\n\n"
        "1️⃣ Bajar peso\n"
        "2️⃣ Controlar ansiedad/apetito\n"
        "3️⃣ Tener más energía\n"
        "4️⃣ Mejorar hábitos\n"
        "5️⃣ Otro",
    ),
    (
        "cuando_empezar",
        "¡Gracias por compartir eso! 😊✨\n\n"
        "¿Cuándo te gustaría empezar?\n"
        "1️⃣ Hoy mismo 🔥\n"
        "2️⃣ Esta semana\n"
        "3️⃣ Este mes\n"
        "4️⃣ Solo estoy averiguando",
    ),
]

PREGUNTAS_RECOMPRA = [
    (
        "producto_actual",
        "¿Qué producto estás usando actualmente?\n"
        "1️⃣ Semaglutide\n"
        "2️⃣ Tirzepatide",
    ),
    (
        "dosis_actual",
        "¿Qué dosis usaste en tu último pedido? 💉\n"
        "_(Ej: 0.25mg, 0.5mg, 2.5mg)_",
    ),
    (
        "bajo_peso",
        "¿Has bajado de peso?\n"
        "1️⃣ Sí → ¿cuánto aproximadamente?\n"
        "2️⃣ No",
    ),
    (
        "efectos_secundarios",
        "¿Has tenido efectos secundarios?\n"
        "1️⃣ No\n"
        "2️⃣ Sí → ¿cuáles?",
    ),
    (
        "objetivo_ahora",
        "¿Cuál es tu objetivo ahora? 🎯\n"
        "1️⃣ Seguir bajando\n"
        "2️⃣ Mantener peso\n"
        "3️⃣ Mejorar energía\n"
        "4️⃣ Controlar ansiedad/apetito",
    ),
    (
        "cuando_empezar",
        "¡Gracias! Ya casi terminamos ✨\n"
        "¿Cuándo te gustaría recibir tu siguiente pedido?\n"
        "1️⃣ Hoy mismo 🔥\n"
        "2️⃣ Esta semana\n"
        "3️⃣ Este mes",
    ),
]

PREGUNTAS_QUEMADORES = [
    ("usado_antes", "¿Has usado quemadores de grasa anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    (
        "objetivo",
        "¿Cuál es tu objetivo principal? 🎯\n"
        "1️⃣ Bajar de peso\n"
        "2️⃣ Tener más energía\n"
        "3️⃣ Definir cuerpo\n"
        "4️⃣ Reducir ansiedad/apetito",
    ),
    ("hace_ejercicio", "¿Realizas ejercicio actualmente?\n1️⃣ Sí\n2️⃣ No"),
    (
        "condicion",
        "¿Tienes alguna condición médica o sensibilidad a estimulantes?\n"
        "_(Ej: presión alta, ansiedad, problemas cardíacos, o ninguna)_",
    ),
    (
        "formato",
        "¿Prefieres cápsulas o inyecciones? 💉\n"
        "1️⃣ Cápsulas\n"
        "2️⃣ Inyecciones\n"
        "3️⃣ Quiero recomendación",
    ),
]

PREGUNTAS_PEPTIDOS = [
    (
        "objetivo",
        "¿Qué resultado deseas obtener principalmente? 🎯\n"
        "1️⃣ Mejorar piel\n"
        "2️⃣ Crecimiento de cabello\n"
        "3️⃣ Antiaging\n"
        "4️⃣ Recuperación y bienestar",
    ),
    ("usado_antes", "¿Has utilizado péptidos anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    ("procedimiento", "¿Tienes algún procedimiento estético reciente o tratamiento activo?"),
    ("alergia", "¿Tienes alergias o alguna condición médica importante?"),
    (
        "producto",
        "¿Cuál de estos productos te interesa más?\n"
        "1️⃣ Glow Blend\n"
        "2️⃣ GHK-Cu\n"
        "3️⃣ Quiero recomendación",
    ),
]

PREGUNTAS_NAD = [
    (
        "objetivo",
        "¿Cuál es tu objetivo principal con NAD+? 🎯\n"
        "1️⃣ Más energía\n"
        "2️⃣ Mejorar enfoque mental\n"
        "3️⃣ Antiaging\n"
        "4️⃣ Recuperación física\n"
        "5️⃣ Bienestar general",
    ),
    ("usado_antes", "¿Has utilizado NAD+ anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    (
        "energia_actual",
        "¿Cómo describirías actualmente tus niveles de energía?\n"
        "1️⃣ Muy bajos\n"
        "2️⃣ Normales\n"
        "3️⃣ Altos",
    ),
    ("condicion", "¿Tienes alguna condición médica importante o tomas medicamentos actualmente?"),
    (
        "modalidad",
        "¿Prefieres aplicación en clínica o delivery? 🚚📍\n"
        "1️⃣ Aplicación en clínica\n"
        "2️⃣ Delivery",
    ),
]

PREGUNTAS_ESTETICA = [
    (
        "tratamiento",
        "¿Qué tratamiento te interesa?\n"
        "1️⃣ Botox\n"
        "2️⃣ Rellenos\n"
        "3️⃣ Depilación láser\n"
        "4️⃣ Evaluación general",
    ),
    ("primera_vez", "¿Es la primera vez que te realizas este procedimiento?\n1️⃣ Sí\n2️⃣ No"),
    ("resultado", "¿Qué resultado deseas lograr? 🎯"),
    ("condicion", "¿Tienes algún procedimiento estético reciente o condición médica importante?"),
    ("zona", "¿En qué zona deseas realizar el tratamiento? ✨"),
]

PREGUNTAS_FACIAL = [
    (
        "mejorar",
        "¿Qué te gustaría mejorar principalmente? 🎯\n"
        "1️⃣ Acné\n"
        "2️⃣ Manchas\n"
        "3️⃣ Poros abiertos\n"
        "4️⃣ Hidratación\n"
        "5️⃣ Limpieza profunda",
    ),
    (
        "tipo_piel",
        "¿Cómo describirías tu tipo de piel?\n"
        "1️⃣ Grasa\n"
        "2️⃣ Mixta\n"
        "3️⃣ Seca\n"
        "4️⃣ Sensible",
    ),
    ("experiencia", "¿Has realizado limpiezas faciales anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    ("condicion", "¿Tienes algún tratamiento dermatológico activo o alergias?"),
    ("ultima_limpieza", "¿Hace cuánto fue tu última limpieza facial?"),
]

PREGUNTAS_SUEROS = [
    (
        "objetivo",
        "¿Cuál es tu objetivo principal? 🎯\n"
        "1️⃣ Más energía\n"
        "2️⃣ Fortalecer defensas\n"
        "3️⃣ Mejorar hidratación\n"
        "4️⃣ Recuperación física\n"
        "5️⃣ Bienestar general",
    ),
    ("usado_antes", "¿Has utilizado sueros intravenosos anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    (
        "como_te_sientes",
        "¿Cómo te has sentido últimamente?\n"
        "1️⃣ Cansancio frecuente\n"
        "2️⃣ Estrés\n"
        "3️⃣ Baja energía\n"
        "4️⃣ Todo lo anterior",
    ),
    ("condicion", "¿Tienes alguna condición médica importante o alergias?"),
    (
        "modalidad",
        "¿Prefieres realizarlo en clínica o delivery? 🚚📍\n"
        "1️⃣ En clínica\n"
        "2️⃣ Delivery",
    ),
]

PREGUNTAS_REJUVENECIMIENTO = [
    (
        "objetivo",
        "¿Cuál es tu principal objetivo con el tratamiento? 🎯\n"
        "1️⃣ Mejorar firmeza\n"
        "2️⃣ Mejorar hidratación íntima\n"
        "3️⃣ Mejorar sensibilidad\n"
        "4️⃣ Rejuvenecimiento general\n"
        "5️⃣ Recuperación postparto",
    ),
    (
        "tratamiento_previo",
        "¿Has realizado anteriormente algún tratamiento íntimo estético?\n"
        "1️⃣ Sí\n"
        "2️⃣ No",
    ),
    (
        "sintomas",
        "¿Has presentado alguno de estos síntomas?\n"
        "1️⃣ Resequedad\n"
        "2️⃣ Incomodidad íntima\n"
        "3️⃣ Pérdida de firmeza\n"
        "4️⃣ Sensibilidad reducida\n"
        "5️⃣ Ninguno",
    ),
    ("condicion", "¿Tienes alguna condición médica importante o tratamiento ginecológico activo?"),
    (
        "evaluacion",
        "¿Te gustaría realizar tu evaluación en clínica? 📍\n"
        "1️⃣ Sí, me gustaría agendar\n"
        "2️⃣ Primero quiero más información",
    ),
]

PREGUNTAS_MORPHEUS = [
    (
        "zona",
        "¿En qué zona deseas realizar el tratamiento?\n"
        "1️⃣ Rostro\n"
        "2️⃣ Cuello\n"
        "3️⃣ Corporal\n"
        "4️⃣ Varias zonas",
    ),
    (
        "objetivo",
        "¿Cuál es tu principal objetivo? 🎯\n"
        "1️⃣ Reafirmar piel\n"
        "2️⃣ Mejorar flacidez\n"
        "3️⃣ Mejorar textura y poros\n"
        "4️⃣ Reducir marcas o cicatrices\n"
        "5️⃣ Rejuvenecimiento general",
    ),
    ("experiencia", "¿Te has realizado tratamientos estéticos anteriormente?\n1️⃣ Sí\n2️⃣ No"),
    ("condicion", "¿Tienes alguna condición médica, tratamiento dermatológico activo o sensibilidad en la piel?"),
    ("resultado", "¿Qué resultado te gustaría lograr con Morpheus? ✨"),
]

FLUJOS_MENU = {
    "2": {
        "intro": "¡Claro! 😊🔥\nNuestros quemadores de grasa ayudan a acelerar el metabolismo, aumentar energía y apoyar el proceso de pérdida de peso.\n\nPara recomendarte el más adecuado para ti, necesito hacerte unas preguntas 👇",
        "preguntas": PREGUNTAS_QUEMADORES,
        "tipo": "producto",
    },
    "3": {
        "intro": "¡Perfecto! 😊✨\nNuestros péptidos están enfocados en mejorar piel, cabello, recuperación y bienestar general.\n\nPara ayudarte a elegir el indicado, necesito conocerte un poco 👇",
        "preguntas": PREGUNTAS_PEPTIDOS,
        "tipo": "producto",
    },
    "4": {
        "intro": "¡Excelente elección! 😊✨\nEl NAD+ es uno de nuestros tratamientos más solicitados para energía, enfoque mental y bienestar general.\n\nAntes de recomendarte el protocolo ideal, necesito hacerte unas preguntas 👇",
        "preguntas": PREGUNTAS_NAD,
        "tipo": "producto",
    },
    "5": {
        "intro": "¡Claro que sí! 😊✨\nEn LLV Wellness Clinic contamos con diferentes tratamientos estéticos para ayudarte a verte y sentirte mejor.\n\nPara orientarte correctamente, cuéntame 👇",
        "preguntas": PREGUNTAS_ESTETICA,
        "tipo": "cita",
    },
    "6": {
        "intro": "¡Perfecto! 😊✨\nNuestras limpiezas faciales están diseñadas para ayudarte a mejorar la salud y apariencia de tu piel.\n\nAntes de recomendarte la mejor opción, necesito conocerte un poco 👇",
        "preguntas": PREGUNTAS_FACIAL,
        "tipo": "cita",
    },
    "7": {
        "intro": "¡Excelente! 😊✨\nNuestros sueros de vitaminas ayudan a mejorar energía, hidratación, sistema inmune y bienestar general.\n\nPara recomendarte el ideal para ti, necesito hacerte unas preguntas 👇",
        "preguntas": PREGUNTAS_SUEROS,
        "tipo": "producto",
    },
    "8": {
        "intro": "¡Claro que sí! 😊✨\nNuestro tratamiento de rejuvenecimiento vaginal está diseñado para ayudarte a mejorar bienestar íntimo, firmeza, hidratación y confianza de forma segura y profesional.\n\nPara orientarte correctamente, necesito hacerte unas preguntas 👇",
        "preguntas": PREGUNTAS_REJUVENECIMIENTO,
        "tipo": "cita",
    },
    "9": {
        "intro": "¡Excelente elección! 😊✨\nMorpheus es uno de nuestros tratamientos más avanzados para rejuvenecimiento, firmeza y mejora de la piel en rostro, cuello y cuerpo.\n\nEste procedimiento estimula colágeno, mejora textura, flacidez y apariencia de la piel 💫\n\nPara orientarte correctamente, necesito hacerte unas preguntas 👇",
        "preguntas": PREGUNTAS_MORPHEUS,
        "tipo": "cita",
    },
}

MSG_FINAL_HANDOFF = """✨ ¡Perfecto! Gracias por responder 😊

Uno de nuestros asesores especializados revisará tu información y continuará acompañándote en el proceso 💜

📍 Dependiendo del servicio solicitado, te ayudará con:
• Agendamiento de cita
• Coordinación de entrega
• Envío de link de pago
• Confirmación de tratamiento
• Resolución de dudas adicionales

⏰ En breve recibirás atención personalizada por parte de nuestro equipo LLV Wellness Clinic ✨"""

MSG_INTENCION_ENTREGA = """Perfecto, gracias por la info 😊

Para ir adelantando tu proceso y ayudarte más rápido 👇

¿Cómo te gustaría recibir tu tratamiento?

1️⃣ Entrega a domicilio 🚚
2️⃣ Recoger en clínica 🏥
3️⃣ Aplicación en clínica con cita ✨

Escríbeme el número de tu opción"""

SOLICITUD_DATOS = {
    "entrega": (
        "Perfecto 😊\nCompárteme por favor:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Correo electrónico:*\n"
        "• *Dirección y/o pueblo de envío:*\n\n"
        "Puedes responderme todo junto o uno a la vez 💙"
    ),
    "recoger": (
        "Perfecto 😊\nCompárteme por favor:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Correo electrónico:*\n"
        "• *Sede* (Arecibo o Bayamón):\n"
        "• *Día que te gustaría pasar:*\n"
        "• *Hora aproximada:*\n\n"
        "✨ Nuestro equipo revisará tu caso y te contactará lo antes posible."
    ),
    "cita": (
        "Perfecto 😊\nCompárteme por favor:\n\n"
        "• *Nombre completo:*\n"
        "• *Teléfono:*\n"
        "• *Correo electrónico:*\n"
        "• *Sede* (Arecibo o Bayamón):\n"
        "• *Día que te gustaría:*\n"
        "• *Hora aproximada:*\n\n"
        "✨ Uno de nuestros especialistas confirmará tu cita muy pronto."
    ),
}

CAMPOS_REQUERIDOS = {
    "entrega": ["nombre_completo", "telefono", "direccion"],
    "recoger": ["nombre_completo", "telefono", "sede", "dia", "hora"],
    "cita": ["nombre_completo", "telefono", "sede", "dia", "hora"],
}

LABELS_CAMPOS = {
    "nombre_completo": "nombre completo (nombre y apellido)",
    "telefono": "número de teléfono",
    "email": "correo electrónico",
    "direccion": "dirección y/o pueblo de envío",
    "sede": "sede (Arecibo o Bayamón)",
    "dia": "día preferido",
    "hora": "hora aproximada",
}

LEAD_TEMP_MAP = {
    "1": "caliente",
    "hoy": "caliente",
    "hoy mismo": "caliente",
    "2": "caliente",
    "esta semana": "caliente",
    "3": "templado",
    "este mes": "templado",
    "4": "frio",
    "solo": "frio",
    "averiguando": "frio",
}

_UNSUPPORTED_TYPES = {
    "audio": "🎤 Recibí un audio. Por ahora proceso mensajes de texto. Escríbeme lo que necesitas o envía *agente* para hablar con un asesor.",
    "video": "🎥 Recibí un video. Por favor escríbeme en texto lo que necesitas.",
    "location": "📍 Recibí una ubicación. Escríbeme en texto lo que necesitas.",
    "sticker": "🙂 ¡Gracias! ¿En qué puedo ayudarte hoy?",
    "reaction": None,
}

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


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE VALIDACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _validate_phone(v: str) -> bool:
    return len(re.sub(r"\D", "", v)) >= 10


def _validate_name(v: str) -> bool:
    return len(v.strip().split()) >= 2


def _detect_lead_temp(text: str) -> str:
    lower = text.lower()
    for key, temp in LEAD_TEMP_MAP.items():
        if key in lower:
            return temp
    return "templado"


def _detect_lang(text: str) -> str:
    english = [
        "hi",
        "hello",
        "hey",
        "i want",
        "i need",
        "help",
        "what",
        "how",
        "weight",
        "loss",
    ]
    return "en" if any(w in text.lower() for w in english) else "es"


def _extract_from_message(msg: str, existing: dict) -> dict:
    """Extrae datos del mensaje usando heurísticas simples."""
    found = {}

    if not existing.get("telefono"):
        m = re.search(r"[\d\s\-\+\(\)]{10,}", msg)
        if m:
            found["telefono"] = m.group().strip()

    if not existing.get("email"):
        m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", msg)
        if m:
            found["email"] = m.group()

    if not existing.get("sede"):
        lower = msg.lower()
        if "arecibo" in lower:
            found["sede"] = "Arecibo"
        elif "bayam" in lower:
            found["sede"] = "Bayamón"

    return found


# ══════════════════════════════════════════════════════════════════════════════
# BOT SERVICE
# ══════════════════════════════════════════════════════════════════════════════

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

        # Tipos no soportados.
        if msg_type in _UNSUPPORTED_TYPES:
            reply = _UNSUPPORTED_TYPES[msg_type]
            if reply:
                self._enqueue_outbox(number, reply)
            inbox_msg.status = "done"
            self.db.flush()
            return {
                "ok": True,
                "skipped": True,
                "reason": f"unsupported_type:{msg_type}",
            }

        # Imagen/documento: posible comprobante de pago.
        if msg_type in ("image", "document") and media_id:
            return self._handle_possible_payment_proof(number, media_id, inbox_msg)

        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)
        ctx = self._load_ctx(session)
        is_new = not self._has_history(session)

        self._log_message(
            session.id,
            number,
            "inbound",
            text,
            msg_type,
            inbox_msg.meta_message_id,
            False,
        )

        # Encuesta de satisfacción.
        if session.status == "completed":
            session, ctx, is_new = self._handle_completed_session(
                session,
                patient,
                number,
                text,
                inbox_msg,
            )

            if session is None:
                return {
                    "ok": True,
                    "skipped": True,
                    "reason": "survey_processed",
                }

        # Si ya está con agente, el bot no debe responder.
        # Si menciona pago, se marca contexto para que el agente lo vea.
        if session.status == "in_agent":
            escalate_payment_intent(
                self.db,
                session,
                patient,
                text,
            )

            inbox_msg.status = "done"
            patient.last_interaction_at = datetime.utcnow()
            self.db.commit()

            return {
                "ok": True,
                "skipped": True,
                "reason": "session_in_agent_mode",
            }

        if is_new:
            self._notifications.increment_conversation()

        # Escalamiento por intención de pago.
        # Puerto Rico: ATH Móvil, ATH, Zelle, recibo, captura, comprobante, transferencia.
        if escalate_payment_intent(self.db, session, patient, text):
            reply = (
                "Perfecto, te conecto con una de nuestras agentes para validar tu pago "
                "y continuar con el proceso de tu pedido. 💙"
            )

            patient.last_interaction_at = datetime.utcnow()

            self._enqueue_outbox(number, reply)

            self._log_message(
                session.id,
                number,
                "outbound",
                reply,
                "text",
                None,
                True,
            )

            inbox_msg.status = "done"
            self.db.commit()

            return {
                "ok": True,
                "escalated": True,
                "reason": "payment_intent_detected",
            }

        # Máquina de estados normal.
        reply, ctx = self._run_flow(text, ctx, patient, session)

        patient.last_interaction_at = datetime.utcnow()
        self._save_ctx(session, ctx)

        if reply:
            self._enqueue_outbox(number, reply)
            self._log_message(
                session.id,
                number,
                "outbound",
                reply,
                "text",
                None,
                True,
            )

        inbox_msg.status = "done"
        self.db.commit()

        return {"ok": True}

    # ── MÁQUINA DE ESTADOS ────────────────────────────────────────────────────

    def _run_flow(
        self,
        text: str,
        ctx: dict,
        patient: Patient,
        session: Session,
    ) -> tuple[str, dict]:
        step = ctx.get("flow_step", "menu")
        msg = text.strip()

        esc_kw = [
            "agente",
            "asesor",
            "asesora",
            "persona",
            "humano",
            "hablar con",
            "agent",
            "quiero empezar",
            "queja",
            "reclamo",
        ]
        non_esc = ["precio", "costo", "cuánto", "disponible", "horario"]

        if any(kw in msg.lower() for kw in esc_kw) and not any(kw in msg.lower() for kw in non_esc):
            return self._do_escalate(
                ctx,
                patient,
                session,
                reason=f"Cliente solicitó: {msg[:80]}",
            )

        if step == "menu":
            lang = _detect_lang(msg)
            ctx["language"] = lang

            if msg in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                ctx["menu_opcion"] = msg

                if msg == "1":
                    ctx["flow_step"] = "peso_filtro"
                    return (
                        "Perfecto 😊\n\n"
                        "¿Es tu primera vez usando estos medicamentos?\n\n"
                        "1️⃣ Sí, soy nuevo/a\n"
                        "2️⃣ No, ya he usado antes (recompra)"
                    ), ctx

                flujo = FLUJOS_MENU.get(msg)

                if flujo:
                    ctx["flow_step"] = "preguntas_generales"
                    ctx["pregunta_idx"] = 0
                    ctx["respuestas"] = {}
                    ctx["tipo_servicio"] = flujo["tipo"]
                    return flujo["intro"] + "\n\n" + flujo["preguntas"][0][1], ctx

                return MENU_MSG if lang != "en" else MENU_MSG_EN, ctx

            return MENU_MSG if lang != "en" else MENU_MSG_EN, ctx

        if step == "peso_filtro":
            if msg in ("1", "sí", "si", "nuevo", "nueva", "primera vez"):
                ctx["tipo_cliente"] = "nuevo"
                ctx["flow_step"] = "preguntas_nuevo"
                ctx["pregunta_idx"] = 0
                ctx["respuestas"] = {}
                return (
                    "Perfecto 😊 Quiero ayudarte a encontrar la mejor opción para ti ✨\n\n"
                    "Antes de recomendarte el tratamiento ideal, aquí tienes la guía completa 📩\n"
                    "👉 https://guiainstructivallv.my.canva.site/\n\n"
                    "Necesito conocerte un poco 👇\n\n"
                    + PREGUNTAS_NUEVO[0][1]
                ), ctx

            if msg in ("2", "no", "recompra", "ya he usado", "ya usé"):
                ctx["tipo_cliente"] = "recompra"
                ctx["flow_step"] = "preguntas_recompra"
                ctx["pregunta_idx"] = 0
                ctx["respuestas"] = {}
                return (
                    "Perfecto 😊 Para darte continuidad y recomendarte correctamente tu siguiente pedido, necesito validar algunos datos 👇\n\n"
                    + PREGUNTAS_RECOMPRA[0][1]
                ), ctx

            return (
                "Perfecto 😊\n\n"
                "¿Es tu primera vez usando estos medicamentos?\n\n"
                "1️⃣ Sí, soy nuevo/a\n"
                "2️⃣ No, ya he usado antes (recompra)"
            ), ctx

        if step == "preguntas_nuevo":
            return self._run_preguntas(msg, ctx, patient, session, PREGUNTAS_NUEVO, "nuevo")

        if step == "preguntas_recompra":
            return self._run_preguntas(msg, ctx, patient, session, PREGUNTAS_RECOMPRA, "recompra")

        if step == "preguntas_generales":
            opcion = ctx.get("menu_opcion", "2")
            flujo = FLUJOS_MENU.get(opcion, {})
            preguntas = flujo.get("preguntas", [])
            return self._run_preguntas(msg, ctx, patient, session, preguntas, "general")

        if step == "intencion_entrega":
            if msg in ("1", "entrega", "domicilio", "delivery"):
                ctx["tipo_entrega"] = "entrega"
            elif msg in ("2", "recoger", "clinica", "clínica"):
                ctx["tipo_entrega"] = "recoger"
            elif msg in ("3", "cita", "aplicacion", "aplicación"):
                ctx["tipo_entrega"] = "cita"
            else:
                return MSG_INTENCION_ENTREGA, ctx

            ctx["flow_step"] = "captura_datos"
            ctx["datos"] = {}
            ctx["retry_count"] = {}
            ctx["campo_actual"] = None

            return SOLICITUD_DATOS[ctx["tipo_entrega"]], ctx

        if step == "captura_datos":
            return self._handle_captura_datos(msg, ctx, patient, session)

        if step == "confirmacion":
            if msg.lower() in ("sí", "si", "yes", "ok", "correcto", "confirmo", "✅"):
                return self._do_escalate(
                    ctx,
                    patient,
                    session,
                    reason="Datos confirmados por el cliente",
                    confirmed=True,
                )

            datos = ctx.get("datos", {})
            ctx["flow_step"] = "captura_datos"
            ctx["correccion"] = msg

            lower = msg.lower()

            for campo, label in LABELS_CAMPOS.items():
                if campo in lower or label.split(" ")[0] in lower:
                    datos[campo] = ""
                    ctx["datos"] = datos
                    ctx["campo_actual"] = campo
                    return f"Claro, dime tu *{label}* correcto 😊", ctx

            return "Dime qué dato necesitas corregir y te ayudo ✨", ctx

        if step == "gemini_libre":
            return self._handle_gemini(msg, ctx, patient, session)

        ctx["flow_step"] = "menu"
        return MENU_MSG, ctx

    # ── PREGUNTAS SECUENCIALES ────────────────────────────────────────────────

    def _run_preguntas(
        self,
        msg: str,
        ctx: dict,
        patient: Patient,
        session: Session,
        preguntas: list,
        tipo: str,
    ) -> tuple[str, dict]:
        idx = ctx.get("pregunta_idx", 0)
        respuestas = ctx.get("respuestas", {})

        if idx > 0 and idx <= len(preguntas):
            campo = preguntas[idx - 1][0]
            respuestas[campo] = msg

        if idx == 0:
            campo = preguntas[0][0]
            respuestas[campo] = msg
            ctx["respuestas"] = respuestas
            ctx["pregunta_idx"] = 1

            if len(preguntas) > 1:
                return preguntas[1][1], ctx

        else:
            ctx["respuestas"] = respuestas

            if idx < len(preguntas):
                ctx["pregunta_idx"] = idx + 1
                return preguntas[idx][1], ctx

        ctx["respuestas"] = respuestas

        cuando = respuestas.get("cuando_empezar", respuestas.get("modalidad", "3"))
        ctx["lead_temperature"] = _detect_lead_temp(cuando)

        tipo_serv = ctx.get("tipo_servicio", "producto")

        if tipo == "general" and tipo_serv == "cita":
            ctx["flow_step"] = "captura_datos"
            ctx["tipo_entrega"] = "cita"
            ctx["datos"] = {}
            ctx["retry_count"] = {}
            ctx["campo_actual"] = None

            recomendacion = self._get_gemini_recomendacion(respuestas, ctx, patient, session)

            return recomendacion + "\n\n" + SOLICITUD_DATOS["cita"], ctx

        recomendacion = self._get_gemini_recomendacion(respuestas, ctx, patient, session)

        ctx["flow_step"] = "intencion_entrega"

        return recomendacion + "\n\n" + MSG_INTENCION_ENTREGA, ctx

    def _get_gemini_recomendacion(
        self,
        respuestas: dict,
        ctx: dict,
        patient: Patient,
        session: Session,
    ) -> str:
        try:
            faq_items = self._load_faq()
            history = self._build_history(session)
            patient_ctx = self._patient_context(patient)
            opcion = ctx.get("menu_opcion", "1")
            tipo_cliente = ctx.get("tipo_cliente", "nuevo")

            nombres_opciones = {
                "1": "pérdida de peso (Semaglutide/Tirzepatide)",
                "2": "quemadores de grasa",
                "3": "péptidos",
                "4": "NAD+",
                "5": "estética",
                "6": "limpiezas faciales",
                "7": "sueros de vitaminas",
                "8": "rejuvenecimiento vaginal",
                "9": "Morpheus",
            }

            nombre_servicio = nombres_opciones.get(opcion, "tratamiento")

            prompt = (
                f"El cliente eligió {nombre_servicio}. "
                f"Tipo: {'recompra' if tipo_cliente == 'recompra' else 'nuevo'}. "
                f"Respuestas del formulario: {json.dumps(respuestas, ensure_ascii=False)}. "
                f"Genera una recomendación personalizada breve (máximo 3 párrafos), "
                f"cálida y profesional en el estilo de LLV Wellness Clinic. "
                f"Menciona el producto o protocolo específico si aplica. "
                f"Termina con una frase de transición hacia el siguiente paso."
            )

            result = self._gemini.process_message(
                user_message=prompt,
                history=history,
                faq_items=faq_items,
                patient=patient_ctx,
            )

            return result.get("text") or (
                "¡Gracias por tu información! 😊✨\n\n"
                "Con base en tus respuestas, tenemos opciones ideales para ti."
            )

        except Exception as exc:
            logger.warning("Error generando recomendación Gemini: %s", exc)

            return (
                "¡Gracias por tu información! 😊✨\n\n"
                "Con base en tus respuestas, uno de nuestros especialistas te orientará con la mejor opción."
            )

    # ── CAPTURA Y VALIDACIÓN DE DATOS ─────────────────────────────────────────

    def _handle_captura_datos(
        self,
        msg: str,
        ctx: dict,
        patient: Patient,
        session: Session,
    ) -> tuple[str, dict]:
        tipo_entrega = ctx.get("tipo_entrega", "entrega")
        datos = ctx.get("datos", {})
        retry_count = ctx.get("retry_count", {})
        campo_actual = ctx.get("campo_actual")
        campos_req = CAMPOS_REQUERIDOS.get(tipo_entrega, [])

        extraidos = _extract_from_message(msg, datos)
        datos.update(extraidos)

        if campo_actual and not datos.get(campo_actual):
            datos[campo_actual] = msg.strip()

        if not datos.get("nombre_completo"):
            words = msg.strip().split()

            if 2 <= len(words) <= 5:
                datos["nombre_completo"] = msg.strip()

        ctx["datos"] = datos

        for campo in campos_req:
            valor = datos.get(campo, "").strip()

            if not valor:
                retries = retry_count.get(campo, 0)

                if retries >= 2:
                    return self._do_escalate(
                        ctx,
                        patient,
                        session,
                        reason=f"Dato obligatorio no obtenido: {LABELS_CAMPOS.get(campo, campo)}",
                    )

                retry_count[campo] = retries + 1
                ctx["retry_count"] = retry_count
                ctx["campo_actual"] = campo
                ctx["datos"] = datos

                if retries == 0:
                    return f"Necesito tu *{LABELS_CAMPOS.get(campo, campo)}* para continuar 😊", ctx

                return (
                    f"Por favor compárteme tu *{LABELS_CAMPOS.get(campo, campo)}* "
                    f"— es necesario para procesar tu solicitud 💙"
                ), ctx

            if campo == "nombre_completo" and not _validate_name(valor):
                retries = retry_count.get(campo, 0)

                if retries >= 2:
                    return self._do_escalate(
                        ctx,
                        patient,
                        session,
                        reason="Nombre inválido tras 2 intentos",
                    )

                retry_count[campo] = retries + 1
                ctx["retry_count"] = retry_count
                datos[campo] = ""
                ctx["datos"] = datos

                return (
                    "Por favor escribe tu *nombre y apellido completos* 😊\n"
                    "_(Ej: María García)_"
                ), ctx

            if campo == "telefono" and not _validate_phone(valor):
                retries = retry_count.get(campo, 0)

                if retries >= 2:
                    return self._do_escalate(
                        ctx,
                        patient,
                        session,
                        reason="Teléfono inválido tras 2 intentos",
                    )

                retry_count[campo] = retries + 1
                ctx["retry_count"] = retry_count
                datos[campo] = ""
                ctx["datos"] = datos

                return "Por favor escribe un *número de teléfono válido* (mínimo 10 dígitos) 📞", ctx

        if not datos.get("email") and retry_count.get("email", 0) < 1:
            retry_count["email"] = 1
            ctx["retry_count"] = retry_count
            ctx["campo_actual"] = "email"
            ctx["datos"] = datos

            return "¿Tienes un *correo electrónico*? (opcional — escribe 'no' si prefieres omitirlo) 📧", ctx

        if datos.get("email", "").lower() in ("no", "n/a", "omitir", "sin correo"):
            datos["email"] = ""

        ctx["campo_actual"] = None
        ctx["flow_step"] = "confirmacion"
        ctx["datos"] = datos

        return self._build_confirmation_msg(datos, tipo_entrega), ctx

    def _build_confirmation_msg(self, datos: dict, tipo: str) -> str:
        lines = [
            "¡Casi listo! 😊 Antes de pasarte con nuestro equipo, confirma que tus datos son correctos ✨\n",
            f"👤 *Nombre:* {datos.get('nombre_completo', '—')}",
            f"📞 *Teléfono:* {datos.get('telefono', '—')}",
        ]

        if datos.get("email"):
            lines.append(f"📧 *Email:* {datos['email']}")

        if tipo == "entrega":
            lines.append(f"🚚 *Entrega en:* {datos.get('direccion', '—')}")

        elif tipo == "recoger":
            lines.append(f"🏥 *Sede:* {datos.get('sede', '—')}")
            lines.append(f"📅 *Día:* {datos.get('dia', '—')} | ⏰ *Hora:* {datos.get('hora', '—')}")

        elif tipo == "cita":
            lines.append(f"💉 *Sede:* {datos.get('sede', '—')}")
            lines.append(f"📅 *Día:* {datos.get('dia', '—')} | ⏰ *Hora:* {datos.get('hora', '—')}")

        lines.append(
            "\n¿Todo está correcto?\n"
            "✅ Escribe *SÍ* para confirmar\n"
            "✏️ O dime qué necesitas corregir"
        )

        return "\n".join(lines)

    # ── ESCALADA ──────────────────────────────────────────────────────────────

    def _do_escalate(
        self,
        ctx: dict,
        patient: Patient,
        session: Session,
        reason: str = "Solicitud del cliente",
        confirmed: bool = False,
    ) -> tuple[str, dict]:
        datos = ctx.get("datos", {})
        respuestas = ctx.get("respuestas", {})
        lead_temp = ctx.get("lead_temperature", "")
        opcion = ctx.get("menu_opcion", "")

        nombres_opciones = {
            "1": "Pérdida de peso",
            "2": "Quemadores de grasa",
            "3": "Péptidos",
            "4": "NAD+",
            "5": "Estética",
            "6": "Limpiezas faciales",
            "7": "Sueros IV",
            "8": "Rejuvenecimiento vaginal",
            "9": "Morpheus",
        }

        servicio = nombres_opciones.get(opcion, "Servicio LLV")
        lead_emoji = {
            "caliente": "🔥",
            "templado": "🌤️",
            "frio": "❄️",
        }.get(lead_temp, "")

        summary_lines = [
            f"{'=' * 40}",
            f"RESUMEN {lead_emoji} LEAD {lead_temp.upper() if lead_temp else 'N/A'}",
            f"Servicio: {servicio}",
            f"{'=' * 40}",
        ]

        if datos.get("nombre_completo"):
            summary_lines.append(f"👤 Nombre: {datos['nombre_completo']}")

        if datos.get("telefono"):
            summary_lines.append(f"📞 Teléfono: {datos['telefono']}")

        if datos.get("email"):
            summary_lines.append(f"📧 Email: {datos['email']}")

        if ctx.get("tipo_entrega"):
            tipo_labels = {
                "entrega": "🚚 Entrega local",
                "recoger": "🏥 Recoger clínica",
                "cita": "💉 Cita clínica",
            }
            summary_lines.append(f"Tipo: {tipo_labels.get(ctx['tipo_entrega'], '')}")

        if datos.get("direccion"):
            summary_lines.append(f"📍 Dirección: {datos['direccion']}")

        if datos.get("sede"):
            summary_lines.append(f"🏥 Sede: {datos['sede']}")

        if datos.get("dia"):
            summary_lines.append(f"📅 Día: {datos['dia']} | ⏰ Hora: {datos.get('hora', '—')}")

        if respuestas:
            summary_lines.append("\n📋 Perfil del cliente:")

            for key, value in respuestas.items():
                if value:
                    summary_lines.append(f"  • {key}: {value}")

        if confirmed:
            summary_lines.append("\n✅ DATOS CONFIRMADOS POR EL CLIENTE")

        summary_lines.append(f"Motivo escalada: {reason}")

        summary = "\n".join(summary_lines)

        location = patient.location_type or "latam"
        agent = self._agent_router.assign_agent(session, location)

        ctx_session = self._load_ctx(session)

        ctx_session.update(
            {
                "agent_summary": summary,
                "escalation_reason": reason,
                "lead_temperature": lead_temp,
                "escalated_at": datetime.utcnow().isoformat(),
            }
        )

        self._save_ctx(session, ctx_session)

        ctx["flow_step"] = "handoff"

        if not agent:
            return (
                "Intenté conectarte con un asesor pero en este momento no hay disponibilidad. "
                "Por favor escríbenos en horario de atención:\n"
                "• Lun–Vie: 8:00 AM – 5:00 PM\n"
                "• Sáb: 8:00 AM – 1:00 PM\n"
                "¡Te responderemos tan pronto sea posible! 💙"
            ), ctx

        logger.info(
            "Escalada | agent=%s | session=%s | lead=%s",
            agent.name,
            session.id,
            lead_temp,
        )

        return MSG_FINAL_HANDOFF, ctx

    def _handle_gemini(
        self,
        msg: str,
        ctx: dict,
        patient: Patient,
        session: Session,
    ) -> tuple[str, dict]:
        faq_items = self._load_faq()
        history = self._build_history(session)
        patient_ctx = self._patient_context(patient)

        result = self._gemini.process_message(
            user_message=msg,
            history=history,
            faq_items=faq_items,
            patient=patient_ctx,
        )

        if result.get("function_call"):
            reply = self._handle_function_call(
                result["function_call"],
                result.get("function_args") or {},
                patient,
                session,
            )
        else:
            reply = result.get("text") or "¿En qué más puedo ayudarte? 😊"

        return reply, ctx

    # ── FUNCTION CALL HANDLER ─────────────────────────────────────────────────

    def _handle_function_call(
        self,
        fn_name: str,
        args: dict,
        patient: Patient,
        session: Session,
    ) -> str:
        logger.info("Function call: %s | args=%s", fn_name, args)

        handlers = {
            "identify_patient": self._fn_identify_patient,
            "schedule_appointment": self._fn_schedule_appointment,
            "send_payment_link": self._fn_send_payment_link,
            "escalate_to_agent": lambda a, p, s: self._do_escalate({}, p, s, a.get("reason", ""))[0],
            "register_payment_proof": self._fn_register_payment_proof,
        }

        handler = handlers.get(fn_name)

        if handler:
            return handler(args, patient, session)

        return "Estoy procesando tu solicitud. Un momento por favor."

    def _fn_identify_patient(
        self,
        args: dict,
        patient: Patient,
        session: Session,
    ) -> str:
        if args.get("full_name"):
            patient.full_name = args["full_name"]

        if args.get("location_type") in ("puerto_rico", "latam", "usa"):
            patient.location_type = args["location_type"]

        self.db.flush()

        name = patient.full_name or "estimado/a cliente"

        if patient.is_recurrent:
            return f"¡Hola de nuevo, *{name}*! 👋 ¿Vienes por tu tratamiento habitual? 😊"

        return f"¡Perfecto, *{name}*! Ya tengo tus datos. ¿En qué puedo ayudarte hoy? 💚"

    def _fn_schedule_appointment(
        self,
        args: dict,
        patient: Patient,
        session: Session,
    ) -> str:
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

        return f"✅ Cita registrada para *{appt.service}*. Nuestro equipo la confirmará pronto. 😊"

    def _fn_send_payment_link(
        self,
        args: dict,
        patient: Patient,
        session: Session,
    ) -> str:
        method = args.get("payment_method", "zelle")
        product = args.get("product_service", "Tratamiento LLV")
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

        instructions = {
            "zelle": (
                f"💳 *Pago por Zelle:*\n"
                f"Envía {amount_text} a: _pagos@llvclinic.com_\n"
                f"Escribe tu nombre en el concepto."
            ),
            "ath": (
                f"📱 *Pago por ATH Móvil:*\n"
                f"Envía {amount_text} al: _787-800-5222_\n"
                f"Escribe tu nombre en el mensaje."
            ),
            "paypal": (
                f"💻 *Pago por PayPal:*\n"
                f"Envía {amount_text} a: _pagos@llvclinic.com_\n"
                f"Selecciona 'Amigos y familia'."
            ),
            "credit_card": "💳 *Pago con Tarjeta:*\nUn asesor te enviará el link de pago seguro.",
        }.get(method, "Un asesor te enviará las instrucciones de pago.")

        return (
            f"Aquí las instrucciones de pago de *{product}*:\n\n"
            f"{instructions}\n\n"
            f"📸 Envía el comprobante aquí para verificarlo 😊"
        )

    def _fn_register_payment_proof(
        self,
        args: dict,
        patient: Patient,
        session: Session,
    ) -> str:
        media_id = args.get("media_id", "")
        product = args.get("product_service", "Tratamiento LLV")

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

        return "✅ ¡Recibí tu comprobante! Lo verificaremos en breve y te confirmamos 💙"

    # ── SESIÓN COMPLETADA / ENCUESTA ──────────────────────────────────────────

    def _handle_completed_session(
        self,
        session,
        patient,
        number,
        text,
        inbox_msg,
    ):
        ctx = self._load_ctx(session)

        if ctx.get("survey_answered"):
            new_session = Session(
                patient_id=patient.id,
                whatsapp_number=number,
                status="active",
                context_json={"flow_step": "menu"},
            )

            self.db.add(new_session)
            self.db.flush()

            return new_session, self._load_ctx(new_session), True

        stripped = text.strip()
        score = None

        if stripped in ("1", "2", "3", "4", "5"):
            score = int(stripped)

        elif "⭐" in stripped:
            score = stripped.count("⭐")

        if score and 1 <= score <= 5:
            from app.services.analytics_service import AnalyticsService

            AnalyticsService(self.db).track(
                "satisfaction_received",
                session_id=session.id,
                patient_id=patient.id,
                agent_id=session.assigned_agent_id,
                score=score,
            )

            ctx["survey_answered"] = True
            self._save_ctx(session, ctx)

            self._enqueue_outbox(
                number,
                f"¡Gracias por tu calificación! {'⭐' * score}\n"
                f"Tu opinión es muy importante para nosotros 💙✨",
            )

            inbox_msg.status = "done"
            self.db.flush()

            return None, None, None

        new_session = Session(
            patient_id=patient.id,
            whatsapp_number=number,
            status="active",
            context_json={"flow_step": "menu"},
        )

        self.db.add(new_session)
        self.db.flush()

        return new_session, self._load_ctx(new_session), True

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _load_ctx(self, session: Session) -> dict:
        ctx = session.context_json or {}

        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}

        if "flow_step" not in ctx:
            ctx["flow_step"] = "menu"

        return ctx

    def _save_ctx(self, session: Session, ctx: dict):
        import copy

        session.context_json = copy.deepcopy(ctx)
        flag_modified(session, "context_json")
        self.db.flush()

    def _has_history(self, session: Session) -> bool:
        return (
            self.db.query(MessageLog)
            .filter(MessageLog.session_id == session.id)
            .first()
            is not None
        )

    def _handle_possible_payment_proof(self, number, media_id, inbox_msg):
        patient = self._get_or_create_patient(number, inbox_msg.profile_name)
        session = self._get_or_create_session(number, patient)

        self._log_message(
            session.id,
            number,
            "inbound",
            f"[media:{media_id}]",
            inbox_msg.message_type,
            inbox_msg.meta_message_id,
            False,
        )

        reply = self._fn_register_payment_proof(
            {
                "media_id": media_id,
            },
            patient,
            session,
        )

        # Escalar automáticamente porque imagen/documento puede ser comprobante.
        escalate_payment_intent(
            self.db,
            session,
            patient,
            "comprobante de pago recibido",
        )

        self._enqueue_outbox(number, reply)

        self._log_message(
            session.id,
            number,
            "outbound",
            reply,
            "text",
            None,
            True,
        )

        inbox_msg.status = "done"
        patient.last_interaction_at = datetime.utcnow()

        self.db.commit()

        return {
            "ok": True,
            "payment_proof_received": True,
            "escalated": True,
        }

    def _get_or_create_patient(self, number, profile_name=None):
        patient = (
            self.db.query(Patient)
            .filter(Patient.whatsapp_number == number)
            .first()
        )

        if not patient:
            patient = Patient(
                whatsapp_number=number,
                full_name=profile_name,
            )

            self.db.add(patient)
            self.db.flush()

        return patient

    def _get_or_create_session(self, number, patient):
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
                context_json={"flow_step": "menu"},
            )

            self.db.add(session)
            self.db.flush()

        return session

    def _load_faq(self):
        return [
            {
                "question": f.question,
                "answer": f.answer,
                "category": f.category,
            }
            for f in self.db.query(FAQ).filter(FAQ.is_active == 1).all()
        ]

    def _build_history(self, session):
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

        return [
            {
                "role": "user" if not log.sent_by_bot else "assistant",
                "content": log.content or "",
            }
            for log in reversed(logs)
        ]

    def _patient_context(self, patient):
        if not patient:
            return None

        return {
            "whatsapp_number": patient.whatsapp_number,
            "full_name": patient.full_name,
            "location_type": patient.location_type,
            "is_recurrent": bool(patient.is_recurrent),
        }

    def _log_message(
        self,
        session_id,
        number,
        direction,
        content,
        msg_type,
        meta_id,
        sent_by_bot,
    ):
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

    def _enqueue_outbox(self, to, text):
        payload = json.dumps(
            {
                "to": to,
                "text": text,
            },
            ensure_ascii=False,
        )

        self.db.add(
            OutboxMessage(
                whatsapp_number=to,
                payload_json=payload,
                status="pending",
            )
        )

        self.db.flush()