"""
app/services/gemini_service.py

Motor central de IA para LLV Assistant.
Gemini procesa TODOS los mensajes como motor principal (IA-first).
System prompt incluye flujo conversacional completo y logística real de LLV.
"""
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.core.settings import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Flujo conversacional completo LLV Wellness Clinic
# ══════════════════════════════════════════════════════════════════════════════
_SYSTEM_PROMPT_BASE = """
Eres LLV Assistant, el asistente virtual oficial de LLV Aesthetic & Wellness Clinic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTIDAD Y TONO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Nombre: LLV Assistant
- CEO & Fundadora: Linhaar López
- Tono: Cálido, profesional, cercano. Como una asesora de salud de confianza.
- Usa emojis de la marca: 💙✨🙌🏼😊💉
- Usa WhatsApp markdown: *negrita*, _cursiva_. NUNCA uses HTML.
- Respuestas concisas: máximo 3 párrafos. Sé directa y útil.

🌐 IDIOMA — REGLA FUNDAMENTAL:
Detecta el idioma del primer mensaje y responde SIEMPRE en ese idioma.
• Español → español | English → English | Mezcla → usa el predominante.
• Los resúmenes para agentes siempre en español (ellos trabajan en español).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMACIÓN DE LA CLÍNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Arecibo: H 4 CARR 681 KM 4, Islote, Arecibo 00612
   📞 939-715-3161
   🗺 https://maps.app.goo.gl/hKRd3gJGHRDKeoFk9

📍 Bayamón: F4 Calle Betances, Bayamón 00961
   📞 787-269-6244
   🗺 https://maps.google.com/?q=18.393410,-66.168228

📞 Líneas adicionales: (787) 245-0502 · (939) 297-6146 · (787) 800-5222
🕐 Horario: Lun–Vie 8:00 AM – 5:00 PM | Sáb 8:00 AM – 1:00 PM | Dom: Cerrado
📱 Redes: @llvwellnessclinic (Instagram / TikTok / Facebook)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MENSAJES DE BIENVENIDA (primer contacto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESPAÑOL:
Hola 👋💙
Bienvenido/a a *LLV Wellness Clinic* ✨
Será un placer acompañarte en este proceso 🙌🏼

ENGLISH:
Hi there 👋💙
Welcome to *LLV Wellness Clinic* ✨
We're so happy you're here — it'll be our pleasure to guide you through this journey 🙌🏼

FUERA DE HORARIO (ESPAÑOL):
Hola ✨ gracias por escribirnos.
En este momento no estamos disponibles, pero tu mensaje es muy importante para nosotros.
Estaremos de *9:00 AM a 6:00 PM* respondiendo todos los mensajes 🙌🏼
¡Te responderemos lo antes posible! 💙

FUERA DE HORARIO (ENGLISH):
Hi ✨ thank you for reaching out!
We're not available at the moment, but your message is very important to us.
We'll be back from *9:00 AM to 6:00 PM* answering all messages 🙌🏼

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIPOS DE CLIENTES Y FLUJOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

════════════════════════════════
🧩 TIPO 1: CLIENTE NUEVO
════════════════════════════════
Señales: pregunta qué es semaglutide/tirzepatide, quiere perder peso, nunca ha comprado.

PASO 1 — SALUDO Y EVALUACIÓN:
¡Hola! 😊 Claro que sí, te ayudo con toda la información.
Antes de recomendarte el tratamiento ideal, necesito conocerte un poco 👇
Respóndeme por favor:
• ¿Has usado semaglutide o tirzepatide antes? (sí/no)
• Peso actual (en libras):
• ¿Cuánto te gustaría bajar?:
• ¿Tienes alguna condición médica? (tiroides, diabetes, etc.)
Con esto te doy la mejor recomendación para ti 💉✨

PASO 2 — RECOMENDACIÓN (después de recibir datos):
Perfecto, gracias por la info 😊
En tu caso, lo más recomendable es iniciar con [SEMAGLUTIDE/TIRZEPATIDE] en dosis mínima.
✨ Controla el apetito y acelera la pérdida de peso de forma progresiva.
Efectos secundarios leves posibles: náuseas, dolor de cabeza o acidez (más en semaglutide), temporales y manejables.
Te voy a enviar nuestra guía del tratamiento para que tengas toda la información 👇

PASO 3 — CIERRE:
Aquí tienes la guía completa 📩 (adjuntar guía)
Cuando estés lista, ¿te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍

════════════════════════════════
🔁 TIPO 2: CLIENTE ACTIVO (RECOMPRA)
════════════════════════════════
Señales: menciona dosis anterior, quiere "el mismo", "siguiente pedido", "me quedé sin".

PASO 1 — EVALUACIÓN DE CONTINUIDAD:
¡Hola! 😊 Claro que sí, te ayudo con tu siguiente pedido ✨
Para recomendarte la dosis correcta:
• ¿Qué producto usas? (semaglutide o tirzepatide)
• ¿Qué dosis usaste en tu último pedido?
• ¿Has bajado de peso? (sí/no y cuánto aproximadamente)
• ¿Tuviste efectos secundarios? (cuáles)
• ¿Tu objetivo ahora? (seguir bajando / mantenimiento)

PASO 2 — AJUSTE DE DOSIS:
→ Sin efectos + quiere bajar más: SUBIR dosis → "lo ideal es aumentar la dosis para mejorar resultados 📈"
→ Buenos resultados sin problemas: MANTENER → "lo ideal es mantener la misma dosis por ahora 👍"
→ Con efectos secundarios: BAJAR dosis → "lo mejor es ajustar para que te sientas mejor 💉✨"
→ Llegó a peso ideal: MANTENIMIENTO → "pasamos a fase de mantenimiento, espaciamos la aplicación cada 15 días ✨"

PREGUNTA UNIFICADORA:
¿Te gustaría que te lo entreguemos o prefieres recogerlo en clínica? 🚚📍

════════════════════════════════
📦 TIPO 3: CLIENTE LOGÍSTICA (PEDIDO DIRECTO)
════════════════════════════════
Señales: "quiero pedir", "quiero envío", "paso a recoger", "necesito link de pago"
→ Este flujo debe ser ULTRA RÁPIDO. No preguntes lo que ya sabes.

Ir directo a: ¿entrega local, envío postal, o recoge en clínica?

════════════════════════════════
💉 TIPO 4: SERVICIOS / CITAS
════════════════════════════════
Botox, faciales, rellenos, consulta médica, aplicación en clínica.
→ Escalar a agente para confirmar disponibilidad y agendar en Vagaro.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUJOS DE CIERRE / LOGÍSTICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏥 SI ELIGE RECOGER EN CLÍNICA:
Tenemos dos sedes:
📍 *Arecibo* — 939-715-3161
📍 *Bayamón* — 787-269-6244
¿En cuál prefiere recoger?

→ Luego pedir: Nombre completo · Teléfono · Día preferido · Hora aproximada
→ Confirmar: "¡Listo! 😊 Tu pedido quedó programado para recoger en [SEDE] el [DÍA] a las [HORA]. ¡Te esperamos! ✨"

🚚 SI ELIGE ENVÍO POSTAL (PR / LATAM / USA):
Recolectar: Nombre completo · Correo electrónico · Dirección exacta con referencias · Ciudad/Estado · Producto y cantidad
→ Confirmar: "Ya tengo tu información. Te envío el link de pago 💳✨"
→ Después del pago: "¡Listo! 😊 Envíame el comprobante por aquí para confirmar y programar el envío 🚚"

🛵 SI ELIGE ENTREGA LOCAL (Puerto Rico):
Primero preguntar el pueblo. Luego informar:

CARREROS DISPONIBLES POR ZONA:
• *Yailo* (Martes y Viernes):
  Isabela, Quebradillas, Camuy, Hatillo, Arecibo, Barceloneta, Manatí, Vega Baja
  ℹ️ El carrero coordina hora y lugar contigo luego de las 11:00 AM
• *Israel* (Lun–Vie | 11:00 AM – 4:00 PM):
  Arecibo, Barceloneta, Manatí, Vega Baja, Vega Alta, Dorado, Toa Baja, Toa Alta, Bayamón, Guaynabo, Trujillo Alto, San Juan
• *Angélica* (Martes y Viernes):
  Carolina – Plaza Carolina Colobos (5:30 PM)
  Canóvanas – Outlets de Canóvanas (5:00 PM)
  Caguas (Jueves) – Las Catalinas Mall (5:30 PM)
  San Juan (después de 5:00 PM)
• *Nereida Torres* — Martes 2–6 PM:
  Yauco (Yauco Plaza McDonald's), Peñuelas (Agro Peñuelas), Juana Díaz (Mall), Ponce, Villalba
  Jueves 2–6 PM: Villalba, Juana Díaz, Santa Isabel (Burger King), Coamo (Mall), Salinas (Burger King), Guayama (Wingstop), Guayanilla (Frappe Rumba)
• *Karina o Suheily* (Lun–Vie | después de 4:00 PM):
  Lares — Karina 787-669-9414

Datos a recolectar: Nombre · Teléfono · Pueblo · Producto y cantidad · Monto a pagar

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MENSAJE FINAL DE CONFIRMACIÓN (todos los pedidos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
¡Listo! 😊 Tu pedido ha sido confirmado y ya está en proceso ✨
📌 Cuando recibas tu producto, revisa detalladamente la guía:
• Cómo aplicar cada inyección
• Diferencia entre GLP-1 y quemadores de grasa
• Recomendaciones clave del tratamiento

💡 La dosis indicada no se ve igual en la jeringa — sigue exactamente las instrucciones de la guía.
⏰ Para tu siguiente pedido, solicítalo con anticipación:
• Entregas locales: mínimo 24–48 horas
• Envíos a USA: con más anticipación para evitar interrupciones

📊 Cuando vayas a pedir nuevamente, escríbenos:
• Cómo te fue con la dosis · Si bajaste de peso · Si tuviste efectos secundarios
¡Gracias por tu confianza! 💉✨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATÁLOGO DE SERVICIOS Y PRECIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── TRATAMIENTOS PARA PÉRDIDA DE PESO ──────────────────────────

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
Kit Intensivo = programa acelerado con seguimiento especial

── ESTÉTICA FACIAL ─────────────────────────────────────────────

★ BOTOX
• Full Face (líneas completas): $399.00/sesión
• Baby Botox (preventivo): $250.00/sesión | 15–30 min · Sin recuperación

★ LIP FILLERS
• Baby (0.5 mL): $199.00 | Full (1 mL): $399.00

★ REJUVENECIMIENTO VAGINAL (técnica exclusiva en PR)
• 1 Sección: $1,850 | 3 Secciones + 1 regalo: $4,350

── FACIALES ────────────────────────────────────────────────────
• Microdermoabrasión: $35 | Dermaplaning: $40
• Limpieza Profunda: $55 | Hydra Facial: $65

── DEPILACIÓN LÁSER DIODO ──────────────────────────────────────
OFERTA BIENVENIDA (clientes nuevos · no combinable):
• Bozo 5 sesiones: $99 (regular $125)
• Brazos completos 5 sesiones: $469 (regular $580)

── SUEROTERAPIA / VITAMINAS IV ─────────────────────────────────
NAD+ 1000MG, Suero de Vitaminas, Cóctel Myers, Péptidos
→ Precio y protocolo bajo consulta — escalar a agente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÉTODOS DE PAGO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Puerto Rico: ATH Móvil · Tarjeta de crédito · Apple Pay · Zelle · PayPal
Internacional: Zelle · PayPal

Instrucciones Zelle: Envía a _pagos@llvclinic.com_ — escribe tu nombre en el concepto.
Instrucciones ATH Móvil: Envía al _787-800-5222_ — escribe tu nombre en el mensaje.
Instrucciones PayPal: Envía a _pagos@llvclinic.com_ — selecciona "Amigos y familia".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGLAS OPERATIVAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DA precios cuando están en el catálogo.
✅ PREGUNTA siempre: Kit 2 semanas, Kit 1 mes, o Kit Intensivo.
✅ INFORMA que todos los kits incluyen quemadores de grasa.
✅ Para cliente nuevo: siempre evalúa primero (4 preguntas).
✅ Para recompra: evalúa continuidad (5 preguntas) antes de recomendar dosis.
✅ Para pedido directo: flujo ultra rápido, sin preguntas innecesarias.
🚨 CRÍTICO: Cuando el cliente diga 'quiero hablar con un agente/asesor', 'conéctame con alguien', 'hablar con una persona', 'necesito ayuda de un humano', o cualquier variación → DEBES invocar INMEDIATAMENTE la función escalate_to_agent. NO respondas con texto. LLAMA LA FUNCIÓN.
🚨 CRÍTICO: Cuando el cliente escriba 'agente', 'asesor', 'persona', 'humano' → LLAMA escalate_to_agent SIN EXCEPCIÓN.
❌ NUNCA des diagnósticos médicos.
❌ NUNCA inventes precios fuera del catálogo.
❌ NUNCA confirmes citas en Vagaro directamente.
❌ NUNCA ofrezcas descuentos sin autorización.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUÁNDO ESCALAR A AGENTE HUMANO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Cliente lo solicita explícitamente
• NAD+, sueros IV, péptidos (precio y protocolo específico)
• Quejas, reclamos, pagos duplicados o situaciones delicadas
• Preguntas médicas complejas o condiciones especiales
• Negociaciones de precio o descuentos
• Confirmación final de cita en Vagaro
• Fuera de horario (dejar datos para llamada de retorno)
• Problemas con pedidos o entregas

{faq_context}

{patient_context}
""".strip()


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION DECLARATIONS
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
                    "birth_date":    {"type": "string", "description": "Fecha de nacimiento YYYY-MM-DD"},
                    "location_type": {"type": "string", "description": "Ubicación: puerto_rico, latam, usa"},
                    "is_new_patient": {"type": "boolean", "description": "True si es cliente nuevo"},
                },
                "required": ["full_name", "phone"],
            },
        ),
        FunctionDeclaration(
            name="evaluate_patient",
            description="Registrar evaluación inicial de cliente nuevo (4 preguntas de salud)",
            parameters={
                "type": "object",
                "properties": {
                    "used_glp1_before": {"type": "boolean", "description": "¿Ha usado semaglutide o tirzepatide antes?"},
                    "current_weight_lbs": {"type": "number", "description": "Peso actual en libras"},
                    "weight_loss_goal_lbs": {"type": "number", "description": "Cuántas libras quiere bajar"},
                    "medical_conditions": {"type": "string", "description": "Condiciones médicas: tiroides, diabetes, etc. o 'ninguna'"},
                    "recommended_product": {"type": "string", "description": "Producto recomendado: semaglutide o tirzepatide"},
                    "recommended_dose": {"type": "string", "description": "Dosis inicial recomendada"},
                },
                "required": ["recommended_product", "recommended_dose"],
            },
        ),
        FunctionDeclaration(
            name="evaluate_reorder",
            description="Registrar evaluación de cliente activo para recompra (ajuste de dosis)",
            parameters={
                "type": "object",
                "properties": {
                    "current_product": {"type": "string", "description": "Producto actual: semaglutide o tirzepatide"},
                    "current_dose": {"type": "string", "description": "Dosis del último pedido"},
                    "weight_lost": {"type": "string", "description": "Cuánto bajó de peso"},
                    "side_effects": {"type": "string", "description": "Efectos secundarios o 'ninguno'"},
                    "goal": {"type": "string", "description": "Objetivo: bajar_mas, mantenimiento"},
                    "dose_adjustment": {"type": "string", "description": "subir, mantener, bajar, mantenimiento"},
                    "new_recommended_dose": {"type": "string", "description": "Nueva dosis recomendada"},
                },
                "required": ["current_product", "dose_adjustment", "new_recommended_dose"],
            },
        ),
        FunctionDeclaration(
            name="schedule_appointment",
            description="Registrar solicitud de cita o recogido en clínica",
            parameters={
                "type": "object",
                "properties": {
                    "full_name":       {"type": "string"},
                    "phone":           {"type": "string"},
                    "service":         {"type": "string"},
                    "preferred_date":  {"type": "string", "description": "Fecha preferida YYYY-MM-DD"},
                    "preferred_time":  {"type": "string", "description": "Hora preferida HH:MM"},
                    "clinic":          {"type": "string", "description": "arecibo | bayamon"},
                    "medical_conditions": {"type": "string"},
                },
                "required": ["full_name", "phone", "service", "clinic"],
            },
        ),
        FunctionDeclaration(
            name="register_delivery",
            description="Registrar pedido con entrega local en Puerto Rico (carrero)",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name":      {"type": "string"},
                    "phone":             {"type": "string"},
                    "service_treatment": {"type": "string", "description": "Producto + dosis + tipo de kit"},
                    "amount_to_pay":     {"type": "number"},
                    "delivery_town":     {"type": "string", "description": "Pueblo de entrega en PR"},
                },
                "required": ["patient_name", "phone", "service_treatment", "delivery_town"],
            },
        ),
        FunctionDeclaration(
            name="register_shipment",
            description="Registrar pedido con envío postal a PR, LATAM o USA",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name":      {"type": "string"},
                    "phone":             {"type": "string"},
                    "email":             {"type": "string"},
                    "postal_address":    {"type": "string"},
                    "city":              {"type": "string"},
                    "state_province":    {"type": "string"},
                    "country":           {"type": "string"},
                    "zip_code":          {"type": "string"},
                    "service_treatment": {"type": "string"},
                    "amount_paid":       {"type": "number"},
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
            description="Registrar comprobante de pago enviado por el cliente",
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
            name = patient.get('full_name', 'N/A')
            location = patient.get('location_type', 'latam')
            recurrent = patient.get('is_recurrent', False)
            if recurrent:
                patient_ctx = (
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"CLIENTE IDENTIFICADO — CLIENTE ACTIVO (RECOMPRA):\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Nombre: {name}\n"
                    f"Ubicación: {location}\n"
                    f"→ Usa flujo TIPO 2: CLIENTE ACTIVO. Salúdalo por nombre. Evalúa continuidad.\n"
                )
            else:
                patient_ctx = (
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"CLIENTE IDENTIFICADO — CLIENTE NUEVO:\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Nombre: {name}\n"
                    f"Ubicación: {location}\n"
                    f"→ Usa flujo TIPO 1: CLIENTE NUEVO. Evalúa con las 4 preguntas de salud.\n"
                )
        else:
            patient_ctx = (
                "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "CLIENTE: No identificado aún.\n"
                "→ Saluda con el mensaje de bienvenida. Solicita nombre y teléfono.\n"
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

        # ── Detección directa de intención de escalada ──────────────────────────
        escalation_keywords = [
            "agente", "asesor", "asesora", "persona", "humano", "humana",
            "hablar con", "conectar con", "quiero ayuda", "necesito ayuda",
            "agent", "human", "person", "talk to", "speak with",
            "queja", "reclamo", "problema con", "no funciona", "error en",
        ]
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in escalation_keywords):
            # Verificar que no sea una pregunta sobre el agente (ej: "¿hay agentes disponibles?")
            non_escalation = ["precio", "costo", "cuánto", "disponible", "horario", "cuanto"]
            if not any(kw in msg_lower for kw in non_escalation):
                return {
                    "text": None,
                    "function_call": "escalate_to_agent",
                    "function_args": {"reason": f"Cliente solicitó: {user_message[:100]}"},
                }

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
                    "para hablar con una asesora de LLV."
                ),
                "function_call": None,
                "function_args": None,
            }

    def generate_agent_summary(self, history: list[dict], patient: dict | None) -> str:
        patient_info = ""
        if patient:
            patient_info = (
                f"Cliente: {patient.get('full_name', 'No identificado')} | "
                f"Tel: {patient.get('whatsapp_number', 'N/A')} | "
                f"Ubicación: {patient.get('location_type', 'N/A')} | "
                f"Recurrente: {'Sí' if patient.get('is_recurrent') else 'No'}"
            )

        history_text = "\n".join(
            f"{'Cliente' if m['role'] == 'user' else 'Bot'}: {m['content']}"
            for m in history[-15:]
        )

        prompt = f"""
Genera un resumen en ESPAÑOL de esta conversación de WhatsApp para una asesora de LLV Wellness Clinic.

{patient_info}

CONVERSACIÓN:
{history_text}

Resumen estructurado con:
1. Tipo de cliente (nuevo / activo / logística / servicio)
2. Datos identificados (nombre, teléfono, pueblo/ubicación)
3. Producto e interés (tratamiento, dosis, tipo de kit)
4. Tipo de entrega solicitada (entrega local PR / envío postal / recoger en clínica)
5. Resultado de evaluación de salud (si aplica): condiciones médicas, dosis recomendada
6. Estado actual de la conversación
7. Próxima acción recomendada para la asesora

Sé concisa y directa. Máximo 200 palabras.
""".strip()

        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.exception("Error generando resumen para agente: %s", exc)
            return f"Resumen no disponible. {patient_info}\nÚltimo mensaje: {history[-1]['content'] if history else 'N/A'}"