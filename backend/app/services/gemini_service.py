"""
app/services/gemini_service.py

Motor central de IA para LLV Assistant.
A diferencia del proyecto Servicio Colectivo JC donde Gemini era fallback,
aquí Gemini procesa TODOS los mensajes como motor principal.

Implementa:
- System prompt dinámico con FAQ + contexto del negocio LRV
- Function calling para acciones del bot (agendar, pagar, escalar, etc.)
- Historial de conversación por sesión
"""
import json
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.core.settings import settings

logger = logging.getLogger(__name__)

# ── SYSTEM PROMPT BASE ────────────────────────────────────────────────────────
_SYSTEM_PROMPT_BASE = """
Eres LLV Assistant, el asistente virtual oficial de LRV Aesthetic & Wellness Clinic.

IDENTIDAD:
- Nombre: LLV Assistant
- Tono: Profesional, cercano, cálido, orientado a ventas y servicio al cliente.
- Idioma: Español. Usa WhatsApp markdown: *negrita* para destacar, nunca uses HTML.
- Máximo 3 párrafos por respuesta. Sé conciso pero completo.

NEGOCIO:
LRV Aesthetic & Wellness Clinic ofrece tratamientos estéticos y de bienestar:
- Pérdida de peso: Semaglutide, Tirzepatide (kits semanales subcutáneos)
- Quemadores de grasa: Lipominomix, Co Mic LC, Glutathione (intramuscular)
- Sueroterapia, Botox, Rellenos, Faciales, Corporales, Depilación Láser Diodo
- Péptidos: Sermorelin, Tesamorelin, GHK-Cu, Glow Blend
- Evaluaciones médicas y seguimiento
- Entregas área Metro, Norte, Sur (Puerto Rico)
- Envíos a PR y Estados Unidos

UBICACIONES:
- Clínica Arecibo (Puerto Rico)
- Clínica Bayamón (Puerto Rico)
- Servicio LATAM y USA vía envío

HORARIOS:
- Lunes a Viernes: 8:00 AM – 5:00 PM
- Sábados: 8:00 AM – 1:00 PM
- Domingos: Cerrado

MÉTODOS DE PAGO:
- ATH Móvil, Tarjeta de crédito, Apple Pay (Puerto Rico)
- Zelle, PayPal (internacional)
- Links de pago digitales

FLUJO DE IDENTIFICACIÓN:
1. En el PRIMER mensaje de un número nuevo, preséntate y pide: nombre completo y número de teléfono.
2. Si el cliente es de Puerto Rico, solicita también fecha de nacimiento (por regulaciones locales, no se usa cédula).
3. Si el cliente ya existe en el sistema (se te indicará), salúdalo por nombre y personaliza la conversación.

REGLAS IMPORTANTES:
- NUNCA des diagnósticos médicos ni recomendaciones clínicas específicas.
- NUNCA inventes precios. Solo menciona precios cuando se te proporcionen.
- NUNCA confirmes citas directamente en el sistema (un agente lo hace en Vagaro).
- NO manejes quejas complejas — escala al agente.
- NO ofrezcas descuentos sin autorización.
- Si te preguntan algo fuera de tu alcance, sé honesto y ofrece escalar.

CUÁNDO ESCALAR A AGENTE HUMANO:
- El cliente lo solicita explícitamente
- Quejas, reclamos o situaciones delicadas
- Preguntas médicas complejas o casos especiales
- Precios especiales o negociaciones
- Confirmación de cita (tú recopilas los datos, el agente confirma)

ACCIONES DISPONIBLES (Function Calling):
Tienes acceso a las siguientes herramientas que puedes invocar cuando sea necesario:
- schedule_appointment: Cuando el cliente quiere agendar una cita o valoración
- send_payment_link: Cuando el cliente está listo para pagar
- escalate_to_agent: Cuando necesitas transferir a un agente humano
- register_payment_proof: Cuando el cliente envía un comprobante de pago
- identify_patient: Para buscar/registrar al paciente en la base de datos

{faq_context}

{patient_context}
""".strip()


# ── FUNCTION DECLARATIONS ─────────────────────────────────────────────────────
_TOOLS = Tool(
    function_declarations=[
        FunctionDeclaration(
            name="schedule_appointment",
            description="Registrar una solicitud de cita o valoración del paciente",
            parameters={
                "type": "object",
                "properties": {
                    "full_name":           {"type": "string", "description": "Nombre completo del paciente"},
                    "phone":               {"type": "string", "description": "Número de teléfono de contacto"},
                    "service":             {"type": "string", "description": "Servicio o tratamiento solicitado"},
                    "preferred_date":      {"type": "string", "description": "Fecha preferida (YYYY-MM-DD)"},
                    "preferred_time":      {"type": "string", "description": "Hora preferida (HH:MM)"},
                    "clinic":              {"type": "string", "description": "Clínica: arecibo, bayamon, latam o virtual"},
                    "medical_conditions":  {"type": "string", "description": "Condiciones médicas relevantes"},
                },
                "required": ["full_name", "phone", "service"],
            },
        ),
        FunctionDeclaration(
            name="send_payment_link",
            description="Enviar link de pago o instrucciones de pago al cliente",
            parameters={
                "type": "object",
                "properties": {
                    "product_service":    {"type": "string", "description": "Producto o servicio a pagar"},
                    "amount":             {"type": "number", "description": "Monto en USD"},
                    "payment_method":     {"type": "string", "description": "Método: zelle, ath, paypal, link, credit_card"},
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
                    "reason": {"type": "string", "description": "Razón de la escalada"},
                    "summary": {"type": "string", "description": "Resumen breve de la conversación para el agente"},
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
                    "media_id":       {"type": "string", "description": "ID del archivo/imagen en WhatsApp"},
                    "product_service": {"type": "string", "description": "Producto o servicio del pago"},
                },
                "required": ["media_id"],
            },
        ),
        FunctionDeclaration(
            name="identify_patient",
            description="Registrar o actualizar los datos de identificación del paciente",
            parameters={
                "type": "object",
                "properties": {
                    "full_name":    {"type": "string", "description": "Nombre completo"},
                    "phone":        {"type": "string", "description": "Teléfono de contacto"},
                    "birth_date":   {"type": "string", "description": "Fecha de nacimiento (YYYY-MM-DD) — requerido para PR"},
                    "location_type": {"type": "string", "description": "Ubicación: puerto_rico, latam, usa"},
                },
                "required": ["full_name", "phone"],
            },
        ),
    ]
)


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        # Model se crea dinámicamente por conversación para poder inyectar
        # el system_prompt con FAQ y contexto del paciente actualizado.

    def _get_model(self, system_prompt: str) -> genai.GenerativeModel:
        return genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=system_prompt,
            tools=[_TOOLS],
        )

    def build_system_prompt(self, faq_items: list[dict], patient: dict | None) -> str:
        """Construye el system prompt con FAQ y contexto del paciente."""
        # FAQ context
        if faq_items:
            faq_lines = "\nBASE DE CONOCIMIENTO (responde directamente estas preguntas sin escalar):\n"
            for item in faq_items:
                faq_lines += f"\nP: {item['question']}\nR: {item['answer']}\n"
        else:
            faq_lines = ""

        # Patient context
        if patient:
            if patient.get("is_recurrent"):
                patient_ctx = (
                    f"\nCLIENTE IDENTIFICADO (recurrente):\n"
                    f"- Nombre: {patient.get('full_name', 'N/A')}\n"
                    f"- Historial: cliente frecuente — personaliza el saludo y ofrece sus productos habituales.\n"
                )
            else:
                patient_ctx = (
                    f"\nCLIENTE IDENTIFICADO (nuevo):\n"
                    f"- Nombre: {patient.get('full_name', 'N/A')}\n"
                    f"- Ya tienes sus datos básicos registrados.\n"
                )
        else:
            patient_ctx = "\nCLIENTE: No identificado aún. Solicita nombre y teléfono en este primer mensaje."

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
        """
        Procesa un mensaje del usuario con Gemini.

        Returns:
            {
                "text": str | None,           # respuesta de texto para enviar al cliente
                "function_call": str | None,  # nombre de la función a ejecutar
                "function_args": dict | None, # argumentos de la función
            }
        """
        system_prompt = self.build_system_prompt(faq_items, patient)

        # Construir historial en formato Gemini
        gemini_history = []
        for msg in history[-20:]:  # máximo 20 turnos de contexto
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Si hay media (comprobante de pago) agregar nota al mensaje
        if media_id:
            user_message = f"{user_message}\n[El cliente envió un archivo/imagen con ID: {media_id}]"

        try:
            model = self._get_model(system_prompt)
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(user_message)
            candidate = response.candidates[0]
            part = candidate.content.parts[0]

            # ¿La IA invocó una función?
            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                return {
                    "text": None,
                    "function_call": fc.name,
                    "function_args": dict(fc.args),
                }

            # Respuesta de texto normal
            return {
                "text": part.text,
                "function_call": None,
                "function_args": None,
            }

        except Exception as exc:
            logger.exception("Error en GeminiService.process_message: %s", exc)
            return {
                "text": (
                    "En este momento tengo un inconveniente técnico. "
                    "Por favor escríbeme en unos minutos o escribe *agente* "
                    "para hablar con un asesor. 🙏"
                ),
                "function_call": None,
                "function_args": None,
            }

    def generate_agent_summary(self, history: list[dict], patient: dict | None) -> str:
        """Genera un resumen de la conversación para el agente humano."""
        patient_info = ""
        if patient:
            patient_info = f"Cliente: {patient.get('full_name', 'No identificado')} | Tel: {patient.get('whatsapp_number', 'N/A')}"

        history_text = "\n".join(
            f"{'Cliente' if m['role'] == 'user' else 'Bot'}: {m['content']}"
            for m in history[-15:]
        )

        prompt = f"""
Eres un asistente que genera resúmenes de conversaciones de WhatsApp para agentes de ventas.

{patient_info}

CONVERSACIÓN:
{history_text}

Genera un resumen estructurado en español con:
1. Datos del cliente identificados
2. Servicio o producto de interés
3. Preguntas o inquietudes principales
4. Estado actual de la conversación
5. Siguiente acción recomendada para el agente

Sé conciso y directo. Máximo 200 palabras.
""".strip()

        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.exception("Error generando resumen para agente: %s", exc)
            return f"Resumen no disponible. {patient_info}\n\nÚltimo mensaje del cliente: {history[-1]['content'] if history else 'N/A'}"
