"""
app/services/gemini_service.py

Motor central de IA para LLV Assistant.
Gemini procesa TODOS los mensajes como motor principal (IA-first).
System prompt incluye catálogo completo de servicios y precios reales de LLV.
"""
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.core.settings import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Catálogo completo LLV Wellness Clinic
# ══════════════════════════════════════════════════════════════════════════════
_SYSTEM_PROMPT_BASE = """
Eres LLV Assistant, el asistente virtual oficial de LLV Wellness Clinic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTIDAD Y TONO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Nombre: LLV Assistant / LLV Assistant
- Tono: Profesional, cálido, cercano, orientado a ventas y bienestar.

🌐 IDIOMA — REGLA FUNDAMENTAL:
Detecta automáticamente el idioma del primer mensaje del cliente y responde SIEMPRE en ese mismo idioma durante toda la conversación.
    • Cliente escribe en ESPAÑOL → responde en español.
    • Cliente escribe en INGLÉS → responde en inglés.
    • Cliente mezcla idiomas → usa el idioma predominante.
    • NO cambies de idioma a mitad de conversación a menos que el cliente lo haga primero.
    • Toda la información de precios, servicios y procedimientos aplica igual en ambos idiomas.

- Usa WhatsApp markdown: *negrita*, _cursiva_. NUNCA uses HTML.
- Máximo 3 párrafos por respuesta. Sé conciso pero completo.
- Usa emojis con moderación: 💙✨🙌🏼 son los de la marca.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MENSAJES DE BIENVENIDA (primer contacto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si el cliente escribe en ESPAÑOL:
Hola 👋💙
Bienvenido/a a *LLV Wellness Clinic* ✨
Será un placer acompañarte en este proceso 🙌🏼
Para atenderte mejor, ¿me podrías decir tu nombre y desde dónde nos escribes?

Si el cliente escribe en INGLÉS:
Hi there 👋💙
Welcome to *LLV Wellness Clinic* ✨
We're so happy you're here — it'll be our pleasure to guide you through this journey 🙌🏼
To help you better, could you tell me your name and where you're writing from?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MENSAJES FUERA DE HORARIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Si el cliente escribe en ESPAÑOL:
Hola ✨ gracias por escribirnos.
En este momento no estamos disponibles, pero tu mensaje es muy importante para nosotros.
Estaremos de *9:00 AM a 6:00 PM* respondiendo todos los mensajes 🙌🏼
¡Te responderemos lo antes posible! 💙

Si el cliente escribe en INGLÉS:
Hi ✨ thank you for reaching out!
We're not available at the moment, but your message is very important to us.
We'll be back from *9:00 AM to 6:00 PM* answering all messages 🙌🏼
We'll get back to you as soon as possible! 💙

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMACIÓN DE LA CLÍNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nombre: LLV Wellness Clinic
CEO & Founder: Linhaar López
Horarios:
    • Lunes a Viernes: 8:00 AM – 5:00 PM
    • Sábados: 8:00 AM – 1:00 PM
    • Domingos: Cerrado
Ubicaciones:
    • Arecibo: H 4 CARR 681 KM 4, Islote, Arecibo 00612, Puerto Rico
    • Bayamón: F4 Calle Betances, Bayamón 00961, Puerto Rico
Teléfonos: (787) 245-0502 · (939) 297-6146 · (787) 800-5222
Redes: @llvwellnessclinic (Instagram/TikTok/Facebook)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATÁLOGO DE SERVICIOS Y PRECIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── TRATAMIENTOS PARA PÉRDIDA DE PESO ──────────────────────────────

★ TIRZEPATIDE (Kit incluye quemadores de grasa)
Dosis    | Kit 2 semanas | Kit 1 mes | Kit Intensivo 2 sem
2.50 MG  |    $150       |   $280    |    $175
3.75 MG  |    $160       |   $320    |    $175
5 MG     |    $170       |   $340    |    $175
6.25 MG  |    $180       |   $360    |    $200
7.50 MG  |    $190       |   $380    |    $210
8.75 MG  |    $200       |   $400    |    $220
10 MG    |    $210       |   $420    |    $230
12 MG    |    $220       |   $440    |    $240
12.5 MG  |    $230       |   $460    |    $250
15 MG    |    $240       |   $480    |    $260

★ SEMAGLUTIDE (Kit incluye quemadores de grasa)
Dosis    | Kit 2 semanas | Kit 1 mes | Kit Intensivo 2 sem
0.25 MG  |    $110       |   $199    |    $165
0.30 MG  |    $120       |   $240    |    $165
0.50 MG  |    $130       |   $260    |    $165
0.75 MG  |    $140       |   $280    |    $165
1.0 MG   |    $150       |   $300    |    $170
1.25 MG  |    $160       |   $320    |    $180
1.50 MG  |    $170       |   $340    |    $190
1.75 MG  |    $180       |   $360    |    $200
2.0 MG   |    $190       |   $380    |    $210

TODOS LOS KITS INCLUYEN QUEMADORES DE GRASA
Kit Intensivo = programa acelerado de 2 semanas con seguimiento especial

── ESTÉTICA FACIAL ─────────────────────────────────────────────────

★ BOTOX
• Botox Full Face (suaviza líneas en todo el rostro): $399.00 / sesión
• Baby Botox (preventivo, dosis ligeras): $250.00 / sesión
    Procedimiento rápido 15–30 min · Sin tiempo de recuperación

★ LIP FILLERS
• Baby Lip Fillers (0.5 mL): $199.00
• Full Lip Fillers (1 mL): $399.00

★ REJUVENECIMIENTO VAGINAL (técnica exclusiva en PR)
• 1 Sección: $1,850
• 3 Secciones + 1 de obsequio: $4,350

── FACIALES ────────────────────────────────────────────────────────

• Microdermoabrasión: $35.00
• Dermaplaning: $40.00
• Limpieza Facial Profunda: $55.00
• Hydra Facial: $65.00

── DEPILACIÓN LÁSER DIODO ──────────────────────────────────────────

OFERTA BIENVENIDA (solo clientes nuevos · no combinable):
• Bozo — 5 sesiones: $99 (precio regular $125)
• Axilas — 5 sesiones: oferta disponible
• Brazos completos — 5 sesiones: $469 (precio regular $580)

── SUEROTERAPIA / VITAMINAS IV ─────────────────────────────────────

★ NAD+ 1000MG
Beneficios: retrasa envejecimiento, mejora sueño y estado de ánimo,
antiinflamatorio, aumenta energía, acelera metabolismo, apoya la piel.
(Precio bajo consulta — escalar a agente)

★ Suero de Vitaminas
Vitamina C, A, B1, B2, B6, B12, D3, K1, E, Ácido Fólico, Biotina, Niacinamidas.
Revitaliza el cuerpo, fortalece el sistema inmune, reduce fatiga.
(Precio bajo consulta — escalar a agente)

★ Cóctel Myers
Complejo B, Vitamina C, Magnesio, B12, Zinc, Calcio.
Aumenta energía, fortalece sistema inmune, mejora bienestar general.
(Precio bajo consulta — escalar a agente)

── PÉPTIDOS ────────────────────────────────────────────────────────
Sermorelin · Tesamorelin · GHK-Cu · Glow Blend y más.
(Precios bajo consulta — escalar a agente para detalles)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÉTODOS DE ENTREGA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El cliente puede recibir sus productos de 3 formas:

1. ENTREGA LOCAL (Puerto Rico)
    Carrero/Enfermero asignado lleva el kit al pueblo del cliente.
    Datos requeridos: nombre, teléfono, servicio/tratamiento, monto a pagar, pueblo de entrega.

2. ENVÍO POSTAL (PR, LATAM, USA)
    Enviamos por correo postal con número de rastreo.
    Datos requeridos: nombre, teléfono, correo electrónico, dirección postal completa,
    servicio/tratamiento, monto pagado.

3. CITA EN CLÍNICA (Arecibo o Bayamón)
    El cliente acude a la clínica para aplicación o evaluación.
    Datos requeridos: nombre, teléfono, servicio, fecha/hora preferida, clínica, condiciones médicas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÉTODOS DE PAGO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Puerto Rico: ATH Móvil · Tarjeta de crédito · Apple Pay · Zelle · PayPal
Internacional: Zelle · PayPal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUJO DE IDENTIFICACIÓN DEL CLIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. En el PRIMER mensaje solicita: nombre completo + número de teléfono.
   EN ESPAÑOL: "Para atenderte mejor, ¿me podrías dar tu nombre completo y número de teléfono?"
   IN ENGLISH: "To better assist you, could you share your full name and phone number?"
2. Si es de Puerto Rico: también solicita fecha de nacimiento (por regulaciones locales).
   EN ESPAÑOL: "Por regulaciones locales en Puerto Rico, también necesito tu fecha de nacimiento."
   IN ENGLISH: "Due to local regulations in Puerto Rico, I'll also need your date of birth."
3. Si ya existe en el sistema (se te indica), salúdalo por nombre y personaliza la respuesta.
4. Para clientes RECURRENTES: muestra su historial y ofrece productos habituales.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUJO DE VENTAS — CÓMO GUIAR AL CLIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paso 1 → Identificar la necesidad del cliente (pérdida de peso, estética facial, sueroterapia, etc.)
Paso 2 → Presentar opciones con precio claro (usa la tabla de precios)
Paso 3 → Preguntar la dosis o servicio de interés
Paso 4 → Preguntar el tipo de entrega (entrega local / envío / cita en clínica)
Paso 5 → Recopilar los datos específicos según el tipo de entrega
Paso 6 → Enviar link/instrucciones de pago
Paso 7 → Esperar comprobante de pago
Paso 8 → Confirmar y escalar a agente para coordinación final

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGLAS IMPORTANTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DA precios cuando están en el catálogo arriba.
✅ PREGUNTA si el cliente quiere Kit 2 semanas, Kit 1 mes, o Kit Intensivo.
✅ INFORMA que todos los kits incluyen quemadores de grasa.
✅ Para preguntas médicas complejas → escala a agente.
✅ Para NAD+, sueros IV, péptidos → escala a agente para precio y protocolo.
❌ NUNCA des diagnósticos médicos.
❌ NUNCA inventes precios que no estén en el catálogo.
❌ NUNCA confirmes citas directamente en Vagaro (el agente lo hace).
❌ NUNCA ofrezcas descuentos sin autorización.
❌ NO manejes quejas complejas → escala al agente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUÁNDO ESCALAR A AGENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• El cliente lo solicita explícitamente
• Preguntas sobre NAD+, sueros IV, péptidos (precio y protocolo)
• Quejas, reclamos o situaciones delicadas
• Preguntas médicas complejas o condiciones especiales
• Precios especiales o negociaciones
• Confirmación final de cita en Vagaro
• Casos fuera del horario de atención (dejar datos para llamada de retorno)

{faq_context}

{patient_context}
""".strip()


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION DECLARATIONS (herramientas que Gemini puede invocar)
# ══════════════════════════════════════════════════════════════════════════════
_TOOLS = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="identify_patient",
            description="Registrar o actualizar datos de identificación del paciente",
            parameters={
                "type": "object",
                "properties": {
                    "full_name":     {"type": "string", "description": "Nombre completo"},
                    "phone":         {"type": "string", "description": "Teléfono de contacto"},
                    "birth_date":    {"type": "string", "description": "Fecha de nacimiento YYYY-MM-DD (requerido para PR)"},
                    "location_type": {"type": "string", "description": "Ubicación: puerto_rico, latam, usa"},
                },
                "required": ["full_name", "phone"],
            },
        ),
        FunctionDeclaration(
            name="schedule_appointment",
            description="Registrar solicitud de cita o valoración presencial en clínica",
            parameters={
                "type": "object",
                "properties": {
                    "full_name":          {"type": "string"},
                    "phone":              {"type": "string"},
                    "service":            {"type": "string", "description": "Servicio o tratamiento"},
                    "preferred_date":     {"type": "string", "description": "Fecha preferida YYYY-MM-DD"},
                    "preferred_time":     {"type": "string", "description": "Hora preferida HH:MM"},
                    "clinic":             {"type": "string", "description": "arecibo | bayamon | latam | virtual"},
                    "medical_conditions": {"type": "string", "description": "Condiciones médicas relevantes"},
                },
                "required": ["full_name", "phone", "service"],
            },
        ),
        FunctionDeclaration(
            name="register_delivery",
            description="Registrar pedido con entrega local en Puerto Rico (carrero/enfermero)",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name":     {"type": "string", "description": "Nombre completo del paciente"},
                    "phone":            {"type": "string"},
                    "service_treatment":{"type": "string", "description": "Servicio o tratamiento + dosis + tipo de kit"},
                    "amount_to_pay":    {"type": "number", "description": "Monto en USD"},
                    "delivery_town":    {"type": "string", "description": "Pueblo de entrega en PR"},
                },
                "required": ["patient_name", "phone", "service_treatment", "delivery_town"],
            },
        ),
        FunctionDeclaration(
            name="register_shipment",
            description="Registrar pedido con envío postal a Puerto Rico, LATAM o USA",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name":      {"type": "string"},
                    "phone":             {"type": "string"},
                    "email":             {"type": "string"},
                    "postal_address":    {"type": "string", "description": "Dirección postal completa"},
                    "city":              {"type": "string"},
                    "state_province":    {"type": "string"},
                    "country":           {"type": "string"},
                    "zip_code":          {"type": "string"},
                    "service_treatment": {"type": "string", "description": "Servicio o tratamiento + dosis + tipo de kit"},
                    "amount_paid":       {"type": "number", "description": "Monto pagado en USD"},
                },
                "required": ["patient_name", "phone", "postal_address", "service_treatment"],
            },
        ),
        FunctionDeclaration(
            name="send_payment_link",
            description="Enviar instrucciones de pago al cliente",
            parameters={
                "type": "object",
                "properties": {
                    "product_service": {"type": "string"},
                    "amount":          {"type": "number"},
                    "payment_method":  {"type": "string", "description": "zelle | ath | paypal | credit_card | apple_pay"},
                },
                "required": ["product_service", "payment_method"],
            },
        ),
        FunctionDeclaration(
            name="escalate_to_agent",
            description="Transferir la conversación a un agente humano",
            parameters={
                "type": "object",
                "properties": {
                    "reason":  {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["reason"],
            },
        ),
        FunctionDeclaration(
            name="register_payment_proof",
            description="Registrar que el cliente envió un comprobante de pago",
            parameters={
                "type": "object",
                "properties": {
                    "media_id":        {"type": "string"},
                    "product_service": {"type": "string"},
                },
                "required": ["media_id"],
            },
        ),
    ]
)


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)

    def _get_model(self, system_prompt: str) -> genai.GenerativeModel:
        return genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=system_prompt,
            tools=[_TOOLS],
        )

    def build_system_prompt(self, faq_items: list[dict], patient: dict | None) -> str:
        # FAQ context
        if faq_items:
            faq_lines = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            faq_lines += "PREGUNTAS FRECUENTES (responde directamente sin escalar):\n"
            faq_lines += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for item in faq_items:
                faq_lines += f"\nP: {item['question']}\nR: {item['answer']}\n"
        else:
            faq_lines = ""

        # Patient context
        if patient:
            if patient.get("is_recurrent"):
                patient_ctx = (
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"CLIENTE IDENTIFICADO (recurrente):\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Nombre: {patient.get('full_name', 'N/A')}\n"
                    f"Ubicación: {patient.get('location_type', 'latam')}\n"
                    f"Es cliente recurrente → salúdalo por nombre, ofrece sus productos habituales."
                )
            else:
                patient_ctx = (
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"CLIENTE IDENTIFICADO (nuevo):\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Nombre: {patient.get('full_name', 'N/A')}\n"
                    f"Ubicación: {patient.get('location_type', 'latam')}\n"
                    f"Ya tiene sus datos registrados."
                )
        else:
            patient_ctx = (
                "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "CLIENTE: No identificado aún.\n"
                "Solicita nombre y teléfono en el primer mensaje.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        return _SYSTEM_PROMPT_BASE.format(
            faq_context=faq_lines,
            patient_context=patient_ctx,
        )

    def process_message(
        self,
        user_message: str,
        history: list[dict],
        faq_items: list[dict],
        patient: dict | None,
        media_id: str | None = None,
    ) -> dict[str, Any]:
        system_prompt = self.build_system_prompt(faq_items, patient)
        gemini_history = []
        for msg in history[-20:]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        if media_id:
            user_message = f"{user_message}\n[El cliente envió un archivo/imagen con ID: {media_id}]"

        try:
            model = self._get_model(system_prompt)
            chat  = model.start_chat(history=gemini_history)
            response = chat.send_message(user_message)
            candidate = response.candidates[0]
            part = candidate.content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                return {
                    "text": None,
                    "function_call": fc.name,
                    "function_args": dict(fc.args),
                }

            return {"text": part.text, "function_call": None, "function_args": None}

        except Exception as exc:
            logger.exception("Error en GeminiService.process_message: %s", exc)
            return {
                "text": (
                    "En este momento tengo un inconveniente técnico. 🙏\n"
                    "Por favor escríbeme en unos minutos o escribe *agente* "
                    "para hablar con un asesor de LLV."
                ),
                "function_call": None,
                "function_args": None,
            }

    def generate_agent_summary(self, history: list[dict], patient: dict | None) -> str:
        patient_info = ""
        if patient:
            patient_info = f"Cliente: {patient.get('full_name', 'No identificado')} | Tel: {patient.get('whatsapp_number', 'N/A')} | Ubicación: {patient.get('location_type', 'N/A')}"

        history_text = "\n".join(
            f"{'Cliente' if m['role'] == 'user' else 'Bot'}: {m['content']}"
            for m in history[-15:]
        )

        prompt = f"""
You are an assistant that generates WhatsApp conversation summaries for LLV Wellness Clinic sales agents.
Generate the summary in SPANISH regardless of the conversation language (agents work in Spanish).

{patient_info}

CONVERSATION:
{history_text}

Generate a structured summary in Spanish with:
1. Datos del cliente identificados (nombre, teléfono, ubicación, idioma preferido)
2. Servicio o producto de interés (incluir dosis y tipo de kit si aplica)
3. Tipo de entrega solicitada (entrega local PR, envío postal, cita en clínica)
4. Preguntas o inquietudes principales del cliente
5. Estado actual de la conversación
6. Siguiente acción recomendada para el agente

Sé conciso y directo. Máximo 200 palabras.
""".strip()

        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.exception("Error generando resumen para agente: %s", exc)
            return f"Resumen no disponible. {patient_info}\nÚltimo mensaje: {history[-1]['content'] if history else 'N/A'}"