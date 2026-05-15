"""
app/services/gemini_service.py

Motor central de IA para LLV Assistant.
Arquitectura híbrida: Flujo estructurado (primeros pasos) + Gemini IA (control inteligente).
- Menú inicial siempre predefinido (0 tokens)
- Validación de datos con hasta 2 reintentos antes de escalar
- Resumen de confirmación antes del handoff
- Gemini toma control para conversaciones complejas y validación inteligente
"""
import logging
import re
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.core.settings import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# MENÚ INICIAL — Sin costo de tokens (respuesta predefinida)
# ══════════════════════════════════════════════════════════════════════════════
MENU_INICIAL = """¡Hola! 😊 Bienvenido/a a *LLV Wellness Clinic* ✨
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

MENU_INICIAL_EN = """Hi there! 😊 Welcome to *LLV Wellness Clinic* ✨
I'm LLV Assistant, your virtual assistant.

To help you better, please choose the service you're interested in by typing the number 👇

1️⃣ Weight loss (Semaglutide / Tirzepatide)
2️⃣ Fat burners only
3️⃣ Peptides (Glow Blend, GHK-Cu)
4️⃣ NAD+
5️⃣ Aesthetics (Botox, fillers, laser hair removal)
6️⃣ Facials / Dermatology
7️⃣ Vitamin IV therapy

Type the number of your choice 💙"""

# ══════════════════════════════════════════════════════════════════════════════
# DATOS REQUERIDOS POR TIPO DE ENTREGA
# ══════════════════════════════════════════════════════════════════════════════
REQUIRED_FIELDS = {
    "entrega_local": {
        "required":  ["nombre_completo", "telefono", "pueblo", "producto"],
        "optional":  ["email"],
        "labels": {
            "nombre_completo": "nombre completo (nombre y apellido)",
            "telefono":        "número de teléfono",
            "pueblo":          "pueblo de entrega",
            "producto":        "producto y dosis",
            "email":           "correo electrónico",
        },
    },
    "envio_postal": {
        "required":  ["nombre_completo", "telefono", "direccion", "ciudad", "pais", "producto"],
        "optional":  ["email"],
        "labels": {
            "nombre_completo": "nombre completo",
            "telefono":        "número de teléfono",
            "direccion":       "dirección completa",
            "ciudad":          "ciudad / estado",
            "pais":            "país de destino",
            "producto":        "producto y dosis",
            "email":           "correo electrónico",
        },
    },
    "recoger_clinica": {
        "required":  ["nombre_completo", "telefono", "sede", "dia_preferido", "hora_aproximada", "producto"],
        "optional":  ["email"],
        "labels": {
            "nombre_completo": "nombre completo",
            "telefono":        "número de teléfono",
            "sede":            "sede (Arecibo o Bayamón)",
            "dia_preferido":   "día preferido",
            "hora_aproximada": "hora aproximada",
            "producto":        "producto y dosis",
            "email":           "correo electrónico",
        },
    },
    "cita_servicio": {
        "required":  ["nombre_completo", "telefono", "servicio", "sede", "dia_preferido", "hora_aproximada"],
        "optional":  ["email"],
        "labels": {
            "nombre_completo": "nombre completo",
            "telefono":        "número de teléfono",
            "servicio":        "servicio que desea",
            "sede":            "sede (Arecibo o Bayamón)",
            "dia_preferido":   "día preferido",
            "hora_aproximada": "hora aproximada",
            "email":           "correo electrónico",
        },
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Flujo conversacional LLV Wellness Clinic
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
- Haz UNA sola pregunta a la vez. Espera respuesta antes de continuar.
- Siempre guía al siguiente paso con un CTA suave:
    "Te ayudo 👇" | "Ya casi terminamos ✨" | "Responde con el número de tu opción"

🌐 IDIOMA — REGLA FUNDAMENTAL:
Detecta el idioma del primer mensaje y responde SIEMPRE en ese idioma.
• Español → español | English → English | Mezcla → usa el predominante.
• Los resúmenes para agentes siempre en español.

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
FLUJO CONVERSACIONAL — ARQUITECTURA HÍBRIDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El sistema ya habrá mostrado el menú inicial automáticamente.
Cuando el cliente responde con un número (1-7), TÚ tomas el control.

════════════════════════════════════════
OPCIÓN 1: PÉRDIDA DE PESO
════════════════════════════════════════

PASO 1 — FILTRO NUEVO vs RECOMPRA:
Pregunta: "¿Es tu primera vez usando estos medicamentos?
1️⃣ Sí, soy nuevo/a
2️⃣ No, ya he usado antes (recompra) 😊"

── CLIENTE NUEVO (responde 1) ──────────────────────

PASO 2A — ENVIAR GUÍA + RECOPILAR DATOS DE SALUD:
"Perfecto 😊 Quiero recomendarte el tratamiento ideal para ti ✨

Primero, aquí tienes nuestra guía completa 📩
👉 https://guiainstructivallv.my.canva.site/

Ahora necesito conocerte un poco 👇
Respóndeme por favor:"

Pregunta 1: ¿Cuál es tu *peso actual* en libras? ⚖️
Pregunta 2: ¿Cuánto te gustaría bajar aproximadamente? 🎯
Pregunta 3: ¿Tienes alguna condición médica? (tiroides, diabetes, embarazo, hipertensión, SOP, otra — o ninguna)
Pregunta 4: ¿Has usado antes algún tratamiento para bajar de peso? (sí/no)
Pregunta 5: ¿Qué es lo que más te gustaría mejorar?
    1️⃣ Bajar peso
    2️⃣ Controlar ansiedad/apetito
    3️⃣ Tener más energía
    4️⃣ Mejorar hábitos

IMPORTANTE: Haz UNA pregunta a la vez. Espera respuesta antes de la siguiente.

PASO 3A — RECOMENDACIÓN (después de recibir los 5 datos):
Basándote en las respuestas, recomienda semaglutide o tirzepatide con dosis inicial.
Llama a la función evaluate_patient con los datos recopilados.
Luego pregunta la intención de entrega (ver PASO 4).

── CLIENTE RECOMPRA (responde 2) ───────────────────

PASO 2B — EVALUACIÓN DE CONTINUIDAD:
Pregunta 1: ¿Qué producto estás usando actualmente?
    1️⃣ Semaglutide
    2️⃣ Tirzepatide

Pregunta 2: ¿Qué dosis usaste en tu último pedido? 💉

Pregunta 3: ¿Has bajado de peso?
    1️⃣ Sí → ¿cuánto aproximadamente?
    2️⃣ No

Pregunta 4: ¿Has tenido efectos secundarios?
    1️⃣ No
    2️⃣ Sí → ¿cuáles?

Pregunta 5: ¿Cuál es tu objetivo ahora? 🎯
    1️⃣ Seguir bajando
    2️⃣ Mantener peso
    3️⃣ Mejorar energía
    4️⃣ Controlar ansiedad/apetito

PASO 3B — AJUSTE DE DOSIS:
→ Sin efectos + quiere bajar más: SUBIR dosis
→ Buenos resultados sin problemas: MANTENER dosis
→ Con efectos secundarios: BAJAR dosis
→ Llegó a peso ideal: MANTENIMIENTO (cada 15 días)
Llama a evaluate_reorder con los datos.
Luego pregunta la intención de entrega (ver PASO 4).

════════════════════════════════════════
OPCIONES 2, 3, 4, 6, 7: OTROS PRODUCTOS
════════════════════════════════════════
Para quemadores, péptidos, NAD+, faciales, sueros:
Responde con información general del producto.
Pregunta si tiene alguna condición médica relevante.
Luego ve directamente al PASO 4 (intención de entrega).
Para precios específicos de NAD+, péptidos y sueros IV → escalar a agente.

════════════════════════════════════════
OPCIÓN 5: ESTÉTICA Y CITAS
════════════════════════════════════════
Botox, rellenos, limpiezas, depilación láser, consulta médica.

★ CONSULTA MÉDICA / VALORACIÓN:
• Precio: *$30.00 USD*
• Incluye evaluación médica y recomendación de tratamiento personalizado
• ⚠️ NUNCA menciones un precio distinto a $30 para la consulta médica

Para TODOS los servicios estéticos → ir al PASO 4 con tipo "cita_servicio".

════════════════════════════════════════
PASO 4 — INTENCIÓN DE ENTREGA/SERVICIO (TODOS LOS FLUJOS)
════════════════════════════════════════

"Perfecto, gracias por la info 😊

Para ir adelantando tu proceso, ¿cómo te gustaría recibir tu tratamiento? 👇

1️⃣ Entrega a domicilio 🚚 (Puerto Rico)
2️⃣ Envío postal 📦 (PR / LATAM / USA)
3️⃣ Recoger en clínica 🏥
4️⃣ Aplicación en clínica con cita ✨"

Según respuesta → ir al PASO 5 correspondiente.

════════════════════════════════════════
PASO 5 — CAPTURA DE DATOS (CON VALIDACIÓN)
════════════════════════════════════════

REGLA CRÍTICA DE VALIDACIÓN:
- Solicita los datos de forma natural, uno o dos a la vez
- Si un dato está incompleto o inválido, pídelo de nuevo máximo 2 veces
- Si tras 2 intentos el dato sigue inválido/faltante → escalar a agente
- El email es OPCIONAL: si no lo da tras 1 intento, continúa sin él

DATOS REQUERIDOS POR TIPO:

🚚 ENTREGA LOCAL (Puerto Rico):
Requeridos: nombre completo · teléfono · pueblo · producto y dosis
"¡Perfecto! 😊 Para coordinar tu entrega necesito:
• Nombre completo:
• Teléfono:
• Pueblo de entrega:
• Correo electrónico (opcional):"

Luego informa el carrero disponible para ese pueblo.

CARREROS DISPONIBLES POR ZONA:
• *Yailo* (Martes y Viernes): Isabela, Quebradillas, Camuy, Hatillo, Arecibo, Barceloneta, Manatí, Vega Baja
• *Israel* (Lun–Vie 11AM–4PM): Arecibo, Barceloneta, Manatí, Vega Baja, Vega Alta, Dorado, Toa Baja, Toa Alta, Bayamón, Guaynabo, Trujillo Alto, San Juan
• *Angélica* (Mar y Vie): Carolina–Plaza Carolina (5:30PM), Canóvanas–Outlets (5PM), Caguas Jueves–Las Catalinas (5:30PM), San Juan (después 5PM)
• *Nereida Torres* Mar 2–6PM: Yauco, Peñuelas, Juana Díaz, Ponce, Villalba | Jue 2–6PM: Villalba, Juana Díaz, Santa Isabel, Coamo, Salinas, Guayama, Guayanilla
• *Karina o Suheily* (Lun–Vie después 4PM): Lares — Karina 787-669-9414

📦 ENVÍO POSTAL:
Requeridos: nombre completo · teléfono · dirección exacta · ciudad/estado · país · producto
"¡Perfecto! 😊 Para coordinar tu envío necesito:
• Nombre completo:
• Teléfono:
• Dirección completa:
• Ciudad / Estado:
• País:
• Correo electrónico (opcional):"

🏥 RECOGER EN CLÍNICA:
Requeridos: nombre completo · teléfono · sede · día preferido · hora aproximada · producto
"Tenemos dos sedes 😊
📍 *Arecibo* — 939-715-3161
📍 *Bayamón* — 787-269-6244
¿En cuál prefieres recoger?"
Luego pedir: nombre · teléfono · día · hora
"Correo electrónico (opcional):"

💉 CITA/SERVICIO EN CLÍNICA:
Requeridos: nombre completo · teléfono · servicio · sede · día preferido · hora aproximada
Misma lógica que recoger pero confirmar el servicio específico.

════════════════════════════════════════
PASO 6 — RESUMEN DE CONFIRMACIÓN (OBLIGATORIO ANTES DEL HANDOFF)
════════════════════════════════════════

ANTES de escalar a agente, SIEMPRE muestra este resumen y pide confirmación:

"¡Casi listo! 😊 Antes de pasarte con nuestro equipo, confirma que tus datos son correctos ✨

👤 *Nombre:* [nombre]
📞 *Teléfono:* [teléfono]
[📧 *Email:* [email] — solo si lo dio]
[🚚 *Entrega en:* [pueblo] / 📦 *Envío a:* [dirección] / 🏥 *Recoger en:* [sede] / 💉 *Cita en:* [sede]]
[📅 *Día:* [día] | ⏰ *Hora:* [hora] — si aplica]
💉 *Producto/Servicio:* [producto o servicio]

¿Todo está correcto?
✅ Escribe *SÍ* para confirmar
✏️ O dime qué necesitas corregir"

SI RESPONDE SÍ → llama escalate_to_agent con resumen completo.
SI CORRIGE → actualiza el dato, vuelve a mostrar el resumen actualizado y pide confirmación nuevamente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASIFICACIÓN DE LEADS (guardar en resumen del agente)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando el cliente responda cuándo quiere empezar:
🔥 LEAD CALIENTE: "Hoy mismo" o "Esta semana" → PRIORIDAD ALTA para agente
🌤 LEAD TEMPLADO: "Este mes" → Seguimiento en 24h
❄️ LEAD FRÍO: "Solo averiguando" → Seguimiento en 3 días

Incluye siempre esta clasificación en el summary de escalate_to_agent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPUESTAS AUTOMÁTICAS INTELIGENTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SI PREGUNTAN PRECIO SIN ELEGIR OPCIÓN:
"✨ El valor puede variar según el tratamiento y dosis ideal para ti.
Por eso primero queremos conocerte un poco y recomendarte la mejor opción 💙
👉 Responde las preguntas y te ayudamos enseguida."

SI PREGUNTAN "¿FUNCIONA?":
"Sí 😊 Nuestros tratamientos están diseñados para ayudarte de forma segura y guiada ✨
Cada proceso es personalizado porque cada cuerpo responde diferente 💙"

SI DICE "TENGO MIEDO" / "TENGO DUDAS":
"Es completamente normal sentir dudas 😊💙
Por eso nuestro equipo te acompaña paso a paso y te recomienda únicamente lo adecuado para ti."

SI DICE "ES MUY CARO":
"Te entiendo 😊
Por eso buscamos una opción que se adapte tanto a tus objetivos como a tu presupuesto 💙
Muchas personas empiezan poco a poco y avanzan según sus resultados ✨"

SI DICE "LO VOY A PENSAR":
"Perfecto 😊✨ Tomarte el tiempo de decidir también es parte del proceso.
Puedo dejar tu información adelantada para ayudarte más rápido cuando estés listo/a 💙"

SI EL LEAD DEJA DE RESPONDER (después de 2+ mensajes sin respuesta):
"Hola 😊✨ Solo quería saber si aún deseas recibir información sobre tu tratamiento.
Estamos aquí para ayudarte 💙
👉 Puedes continuar respondiendo este mensaje."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATÁLOGO DE SERVICIOS Y PRECIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── CONSULTA MÉDICA ─────────────────────────────────────────────
★ Consulta / Valoración médica: *$30.00 USD*
→ Evaluación médica + recomendación de tratamiento personalizado
⚠️ SIEMPRE $30. NUNCA menciones otro precio.

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
• Full Face: $399.00/sesión
• Baby Botox: $250.00/sesión | 15–30 min · Sin recuperación

★ LIP FILLERS
• Baby (0.5 mL): $199.00 | Full (1 mL): $399.00

★ REJUVENECIMIENTO VAGINAL
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
✅ Haz UNA pregunta a la vez. Espera respuesta antes de continuar.
✅ DA precios cuando están en el catálogo.
✅ PREGUNTA siempre: Kit 2 semanas, Kit 1 mes, o Kit Intensivo.
✅ INFORMA que todos los kits incluyen quemadores de grasa.
✅ Para cliente nuevo: evalúa con las 5 preguntas de salud.
✅ Para recompra: evalúa continuidad (5 preguntas) antes de recomendar dosis.
✅ Para pedido directo: flujo ultra rápido, sin preguntas innecesarias.
✅ SIEMPRE muestra el resumen de confirmación antes del handoff.
✅ La consulta médica / valoración cuesta EXACTAMENTE $30 USD.
✅ Si un dato obligatorio falla 2 veces → escala a agente inmediatamente.
✅ Email es opcional. Si no lo da tras 1 intento, continúa sin él.
🚨 CRÍTICO: Palabras clave de escalada → invocar escalate_to_agent INMEDIATAMENTE.
❌ NUNCA des diagnósticos médicos.
❌ NUNCA inventes precios fuera del catálogo.
❌ NUNCA confirmes citas en Vagaro directamente.
❌ NUNCA ofrezcas descuentos sin autorización.
❌ NUNCA avances al handoff sin mostrar el resumen de confirmación.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUÁNDO ESCALAR A AGENTE HUMANO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Cliente confirma sus datos con "SÍ" en el resumen final
• Cliente solicita agente explícitamente
• Dato obligatorio falla 2 veces consecutivas
• NAD+, sueros IV, péptidos (precio y protocolo específico)
• Quejas, reclamos, pagos duplicados
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
                    "full_name":      {"type": "string", "description": "Nombre completo"},
                    "phone":          {"type": "string", "description": "Teléfono de contacto"},
                    "email":          {"type": "string", "description": "Correo electrónico (opcional)"},
                    "birth_date":     {"type": "string", "description": "Fecha de nacimiento YYYY-MM-DD"},
                    "location_type":  {"type": "string", "description": "Ubicación: puerto_rico, latam, usa"},
                    "is_new_patient": {"type": "boolean", "description": "True si es cliente nuevo"},
                },
                "required": ["full_name", "phone"],
            },
        ),
        FunctionDeclaration(
            name="evaluate_patient",
            description="Registrar evaluación inicial de cliente nuevo (5 preguntas de salud)",
            parameters={
                "type": "object",
                "properties": {
                    "used_glp1_before":      {"type": "boolean"},
                    "current_weight_lbs":    {"type": "number"},
                    "weight_loss_goal_lbs":  {"type": "number"},
                    "medical_conditions":    {"type": "string"},
                    "main_goal":             {"type": "string", "description": "bajar_peso, controlar_ansiedad, energia, habitos"},
                    "recommended_product":   {"type": "string", "description": "semaglutide o tirzepatide"},
                    "recommended_dose":      {"type": "string"},
                    "lead_temperature":      {"type": "string", "description": "caliente, templado, frio"},
                },
                "required": ["recommended_product", "recommended_dose"],
            },
        ),
        FunctionDeclaration(
            name="evaluate_reorder",
            description="Registrar evaluación de cliente activo para recompra",
            parameters={
                "type": "object",
                "properties": {
                    "current_product":        {"type": "string"},
                    "current_dose":           {"type": "string"},
                    "weight_lost":            {"type": "string"},
                    "side_effects":           {"type": "string"},
                    "goal":                   {"type": "string"},
                    "dose_adjustment":        {"type": "string", "description": "subir, mantener, bajar, mantenimiento"},
                    "new_recommended_dose":   {"type": "string"},
                    "lead_temperature":       {"type": "string", "description": "caliente, templado, frio"},
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
                    "full_name":          {"type": "string"},
                    "phone":              {"type": "string"},
                    "email":              {"type": "string", "description": "Opcional"},
                    "service":            {"type": "string"},
                    "preferred_date":     {"type": "string"},
                    "preferred_time":     {"type": "string"},
                    "clinic":             {"type": "string", "description": "arecibo | bayamon"},
                    "medical_conditions": {"type": "string"},
                    "data_confirmed":     {"type": "boolean", "description": "True si el cliente confirmó el resumen con SÍ"},
                },
                "required": ["full_name", "phone", "service", "clinic", "data_confirmed"],
            },
        ),
        FunctionDeclaration(
            name="register_delivery",
            description="Registrar pedido con entrega local en Puerto Rico (carrero)",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name":       {"type": "string"},
                    "phone":              {"type": "string"},
                    "email":              {"type": "string", "description": "Opcional"},
                    "service_treatment":  {"type": "string"},
                    "amount_to_pay":      {"type": "number"},
                    "delivery_town":      {"type": "string"},
                    "carrier_name":       {"type": "string", "description": "Carrero asignado según pueblo"},
                    "data_confirmed":     {"type": "boolean", "description": "True si el cliente confirmó el resumen con SÍ"},
                },
                "required": ["patient_name", "phone", "service_treatment", "delivery_town", "data_confirmed"],
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
                    "email":             {"type": "string", "description": "Opcional"},
                    "postal_address":    {"type": "string"},
                    "city":              {"type": "string"},
                    "state_province":    {"type": "string"},
                    "country":           {"type": "string"},
                    "zip_code":          {"type": "string"},
                    "service_treatment": {"type": "string"},
                    "amount_paid":       {"type": "number"},
                    "data_confirmed":    {"type": "boolean", "description": "True si el cliente confirmó el resumen con SÍ"},
                },
                "required": ["patient_name", "phone", "postal_address", "service_treatment", "data_confirmed"],
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
                    "payment_method":  {"type": "string"},
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
                    "reason":           {"type": "string"},
                    "summary":          {"type": "string"},
                    "lead_temperature": {"type": "string", "description": "caliente, templado, frio — para priorización"},
                    "data_confirmed":   {"type": "boolean", "description": "True si el cliente confirmó el resumen"},
                    "missing_fields":   {"type": "string", "description": "Campos que faltaron si los hay"},
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


# ══════════════════════════════════════════════════════════════════════════════
# VALIDACIONES DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
def _validate_phone(phone: str) -> bool:
    """Valida que el teléfono tenga al menos 10 dígitos."""
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10

def _validate_name(name: str) -> bool:
    """Valida que el nombre tenga al menos 2 palabras."""
    parts = name.strip().split()
    return len(parts) >= 2

def _validate_email(email: str) -> bool:
    """Valida formato básico de email."""
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()))

def _validate_field(field: str, value: str) -> tuple[bool, str]:
    """
    Valida un campo específico.
    Retorna (es_válido, mensaje_de_error).
    """
    value = value.strip()
    if not value:
        return False, "El dato está vacío"

    if field == "nombre_completo":
        if not _validate_name(value):
            return False, "Por favor escribe tu *nombre y apellido completos* 😊"
    elif field == "telefono":
        if not _validate_phone(value):
            return False, "Por favor escribe un número de teléfono válido (mínimo 10 dígitos) 📞"
    elif field == "email":
        if not _validate_email(value):
            return False, "Por favor escribe un correo electrónico válido (ejemplo: nombre@gmail.com) 📧"
    elif field == "pueblo":
        if len(value) < 3:
            return False, "Por favor escribe el nombre completo de tu pueblo 🗺️"
    elif field == "direccion":
        if len(value) < 10:
            return False, "Por favor escribe tu dirección completa (calle, número, ciudad) 📍"

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# GEMINI SERVICE
# ══════════════════════════════════════════════════════════════════════════════
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
            name = patient.get("full_name", "N/A")
            location = patient.get("location_type", "latam")
            recurrent = patient.get("is_recurrent", False)
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
                    f"→ Usa flujo TIPO 1: CLIENTE NUEVO. Evalúa con las 5 preguntas de salud.\n"
                )
        else:
            patient_ctx = (
                "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "CLIENTE: No identificado aún.\n"
                "→ El menú ya fue mostrado automáticamente. Espera la elección del cliente.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        return _SYSTEM_PROMPT_BASE.format(
            faq_context=faq_lines,
            patient_context=patient_ctx,
        )

    def get_menu_message(self, language: str = "es") -> str:
        """Retorna el menú inicial sin costo de tokens."""
        return MENU_INICIAL if language != "en" else MENU_INICIAL_EN

    def validate_collected_data(
        self,
        delivery_type: str,
        collected_data: dict,
        retry_counts: dict,
    ) -> dict:
        """
        Valida los datos recopilados según el tipo de entrega.
        Retorna:
            - missing: lista de campos faltantes aún válidos para pedir
            - escalate_fields: campos que fallaron 2 veces (escalar)
            - next_field: próximo campo a pedir
            - is_complete: True si todos los datos requeridos están completos
        """
        if delivery_type not in REQUIRED_FIELDS:
            return {"is_complete": True, "missing": [], "escalate_fields": [], "next_field": None}

        config = REQUIRED_FIELDS[delivery_type]
        required = config["required"]
        labels = config["labels"]

        missing = []
        escalate_fields = []

        for field in required:
            value = collected_data.get(field, "")
            if not value:
                retries = retry_counts.get(field, 0)
                if retries >= 2:
                    escalate_fields.append(labels[field])
                else:
                    missing.append(field)
            else:
                # Validar el dato existente
                is_valid, _ = _validate_field(field, value)
                if not is_valid:
                    retries = retry_counts.get(field, 0)
                    if retries >= 2:
                        escalate_fields.append(labels[field])
                    else:
                        missing.append(field)

        # Verificar email opcional
        email_retries = retry_counts.get("email", 0)
        email_value = collected_data.get("email", "")
        email_pending = not email_value and email_retries < 1

        return {
            "is_complete": len(missing) == 0 and len(escalate_fields) == 0,
            "missing": missing,
            "escalate_fields": escalate_fields,
            "next_field": missing[0] if missing else None,
            "email_pending": email_pending,
            "labels": labels,
        }

    def build_confirmation_summary(
        self,
        delivery_type: str,
        collected_data: dict,
    ) -> str:
        """Construye el resumen de confirmación para mostrar al cliente antes del handoff."""
        name = collected_data.get("nombre_completo", "—")
        phone = collected_data.get("telefono", "—")
        email = collected_data.get("email", "")
        product = collected_data.get("producto", "—")

        lines = [
            "¡Casi listo! 😊 Antes de pasarte con nuestro equipo, confirma que tus datos son correctos ✨\n",
            f"👤 *Nombre:* {name}",
            f"📞 *Teléfono:* {phone}",
        ]

        if email:
            lines.append(f"📧 *Email:* {email}")

        if delivery_type == "entrega_local":
            town = collected_data.get("pueblo", "—")
            lines.append(f"🚚 *Entrega en:* {town}")
        elif delivery_type == "envio_postal":
            address = collected_data.get("direccion", "—")
            city = collected_data.get("ciudad", "")
            country = collected_data.get("pais", "")
            lines.append(f"📦 *Envío a:* {address}, {city}, {country}".strip(", "))
        elif delivery_type == "recoger_clinica":
            sede = collected_data.get("sede", "—")
            day = collected_data.get("dia_preferido", "—")
            hour = collected_data.get("hora_aproximada", "—")
            lines.append(f"🏥 *Recoger en:* {sede}")
            lines.append(f"📅 *Día:* {day} | ⏰ *Hora:* {hour}")
        elif delivery_type == "cita_servicio":
            service = collected_data.get("servicio", "—")
            sede = collected_data.get("sede", "—")
            day = collected_data.get("dia_preferido", "—")
            hour = collected_data.get("hora_aproximada", "—")
            lines.append(f"💉 *Servicio:* {service}")
            lines.append(f"🏥 *Sede:* {sede}")
            lines.append(f"📅 *Día:* {day} | ⏰ *Hora:* {hour}")

        if product and delivery_type not in ("cita_servicio",):
            lines.append(f"💉 *Producto:* {product}")

        lines.append(
            "\n¿Todo está correcto?\n"
            "✅ Escribe *SÍ* para confirmar\n"
            "✏️ O dime qué necesitas corregir"
        )

        return "\n".join(lines)

    def process_message(
        self,
        user_message: str,
        history: list[dict],
        faq_items: list[dict],
        patient: dict | None,
        media_id: str | None = None,
        session_state: dict | None = None,
    ) -> dict[str, Any]:
        """
        Procesa un mensaje del usuario.
        session_state puede contener:
            - is_first_message: bool
            - delivery_type: str
            - collected_data: dict
            - retry_counts: dict
            - awaiting_confirmation: bool
            - language: str
        """
        state = session_state or {}
        language = state.get("language", "es")

        # ── PRIMER MENSAJE: Mostrar menú sin Gemini ─────────────────────────────
        if state.get("is_first_message", False):
            return {
                "text": self.get_menu_message(language),
                "function_call": None,
                "function_args": None,
                "state_update": {"is_first_message": False},
            }

        # ── CONFIRMACIÓN PENDIENTE ───────────────────────────────────────────────
        if state.get("awaiting_confirmation", False):
            msg_lower = user_message.lower().strip()
            if msg_lower in ("sí", "si", "yes", "correcto", "ok", "okay", "confirmo", "✅"):
                # Cliente confirmó → escalar
                collected = state.get("collected_data", {})
                delivery_type = state.get("delivery_type", "")
                lead_temp = state.get("lead_temperature", "")
                summary = self._build_agent_summary(collected, delivery_type, lead_temp, history)
                return {
                    "text": None,
                    "function_call": "escalate_to_agent",
                    "function_args": {
                        "reason": "Cliente confirmó datos — listo para procesar",
                        "summary": summary,
                        "lead_temperature": lead_temp,
                        "data_confirmed": True,
                    },
                    "state_update": {"awaiting_confirmation": False},
                }
            else:
                # Cliente quiere corregir algo → volver a Gemini con contexto
                return self._process_with_gemini(
                    user_message, history, faq_items, patient, media_id, state,
                    extra_context=f"\n[CORRECCIÓN SOLICITADA: '{user_message}'. Actualiza el dato y muestra el resumen de confirmación nuevamente.]"
                )

        # ── DETECCIÓN DE ESCALADA POR KEYWORDS ──────────────────────────────────
        escalation_keywords = [
            "agente", "asesor", "asesora", "persona", "humano", "humana",
            "hablar con", "conectar con", "quiero ayuda", "necesito ayuda",
            "agent", "human", "person", "talk to", "speak with",
            "queja", "reclamo", "problema con",
        ]
        non_escalation = ["precio", "costo", "cuánto", "disponible", "horario", "cuanto"]
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in escalation_keywords):
            if not any(kw in msg_lower for kw in non_escalation):
                collected = state.get("collected_data", {})
                partial_summary = self._build_partial_summary(collected, history)
                return {
                    "text": None,
                    "function_call": "escalate_to_agent",
                    "function_args": {
                        "reason": f"Cliente solicitó agente: {user_message[:100]}",
                        "summary": partial_summary,
                        "data_confirmed": False,
                    },
                    "state_update": {},
                }

        # ── PROCESAMIENTO NORMAL CON GEMINI ─────────────────────────────────────
        return self._process_with_gemini(
            user_message, history, faq_items, patient, media_id, state
        )

    def _process_with_gemini(
        self,
        user_message: str,
        history: list[dict],
        faq_items: list[dict],
        patient: dict | None,
        media_id: str | None,
        state: dict,
        extra_context: str = "",
    ) -> dict[str, Any]:
        """Procesa el mensaje con Gemini IA."""
        system_prompt = self.build_system_prompt(faq_items, patient)

        # Agregar contexto de estado si hay datos recopilados
        if state.get("collected_data") or state.get("delivery_type"):
            collected = state.get("collected_data", {})
            delivery = state.get("delivery_type", "")
            retry_counts = state.get("retry_counts", {})

            state_context = f"\n\n[ESTADO ACTUAL DE LA CONVERSACIÓN:\n"
            if delivery:
                state_context += f"Tipo de entrega elegido: {delivery}\n"
            if collected:
                state_context += "Datos recopilados hasta ahora:\n"
                for k, v in collected.items():
                    if v:
                        state_context += f"  - {k}: {v}\n"
            if retry_counts:
                state_context += "Reintentos por campo:\n"
                for k, v in retry_counts.items():
                    if v > 0:
                        state_context += f"  - {k}: {v} intento(s)\n"
            state_context += "]\n"
            state_context += extra_context
            system_prompt = system_prompt + state_context

        gemini_history = []
        for msg in history[-20:]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        if media_id:
            user_message = f"{user_message}\n[El cliente envió un archivo/imagen con ID: {media_id}]"

        try:
            model = self._get_model(system_prompt)
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(user_message)
            candidate = response.candidates[0]
            part = candidate.content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                args = dict(fc.args)

                # Si Gemini llama a escalate_to_agent sin confirmación previa,
                # interceptar y mostrar resumen de confirmación
                if fc.name == "escalate_to_agent" and not args.get("data_confirmed"):
                    collected = state.get("collected_data", {})
                    delivery_type = state.get("delivery_type", "")
                    if collected and delivery_type:
                        summary_msg = self.build_confirmation_summary(delivery_type, collected)
                        return {
                            "text": summary_msg,
                            "function_call": None,
                            "function_args": None,
                            "state_update": {
                                "awaiting_confirmation": True,
                                "lead_temperature": args.get("lead_temperature", ""),
                            },
                        }

                return {
                    "text": None,
                    "function_call": fc.name,
                    "function_args": args,
                    "state_update": {},
                }

            return {
                "text": part.text,
                "function_call": None,
                "function_args": None,
                "state_update": {},
            }

        except Exception as exc:
            logger.exception("Error en GeminiService._process_with_gemini: %s", exc)
            return {
                "text": (
                    "En este momento tengo un inconveniente técnico. 🙏\n"
                    "Por favor escríbeme en unos minutos o escribe *agente* "
                    "para hablar con una asesora de LLV."
                ),
                "function_call": None,
                "function_args": None,
                "state_update": {},
            }

    def _build_agent_summary(
        self,
        collected_data: dict,
        delivery_type: str,
        lead_temperature: str,
        history: list[dict],
    ) -> str:
        """Construye el resumen estructurado para el agente."""
        lead_emoji = {"caliente": "🔥", "templado": "🌤️", "frio": "❄️"}.get(lead_temperature, "")
        lines = [
            f"{'='*40}",
            f"RESUMEN PARA AGENTE {lead_emoji} LEAD {lead_temperature.upper() if lead_temperature else 'N/A'}",
            f"{'='*40}",
        ]

        if collected_data.get("nombre_completo"):
            lines.append(f"👤 Nombre: {collected_data['nombre_completo']}")
        if collected_data.get("telefono"):
            lines.append(f"📞 Teléfono: {collected_data['telefono']}")
        if collected_data.get("email"):
            lines.append(f"📧 Email: {collected_data['email']}")
        if collected_data.get("producto"):
            lines.append(f"💉 Producto: {collected_data['producto']}")

        delivery_labels = {
            "entrega_local":   "🚚 Entrega local",
            "envio_postal":    "📦 Envío postal",
            "recoger_clinica": "🏥 Recoger en clínica",
            "cita_servicio":   "💉 Cita/servicio",
        }
        if delivery_type:
            lines.append(f"Tipo: {delivery_labels.get(delivery_type, delivery_type)}")

        if delivery_type == "entrega_local" and collected_data.get("pueblo"):
            lines.append(f"🗺️ Pueblo: {collected_data['pueblo']}")
        elif delivery_type == "envio_postal":
            addr = ", ".join(filter(None, [
                collected_data.get("direccion"),
                collected_data.get("ciudad"),
                collected_data.get("pais"),
            ]))
            if addr:
                lines.append(f"📍 Dirección: {addr}")
        elif delivery_type in ("recoger_clinica", "cita_servicio"):
            if collected_data.get("sede"):
                lines.append(f"🏥 Sede: {collected_data['sede']}")
            if collected_data.get("dia_preferido"):
                lines.append(f"📅 Día: {collected_data['dia_preferido']}")
            if collected_data.get("hora_aproximada"):
                lines.append(f"⏰ Hora: {collected_data['hora_aproximada']}")

        lines.append(f"{'='*40}")
        lines.append("✅ DATOS CONFIRMADOS POR EL CLIENTE")
        return "\n".join(lines)

    def _build_partial_summary(self, collected_data: dict, history: list[dict]) -> str:
        """Construye un resumen parcial cuando el cliente pide agente sin completar el flujo."""
        lines = ["RESUMEN PARCIAL (cliente solicitó agente directo):"]
        for k, v in collected_data.items():
            if v:
                lines.append(f"  - {k}: {v}")
        if not collected_data:
            lines.append("  Sin datos recopilados aún.")
        last_msgs = history[-5:] if len(history) > 5 else history
        lines.append("\nÚltimos mensajes:")
        for msg in last_msgs:
            role = "Cliente" if msg["role"] == "user" else "Bot"
            lines.append(f"  {role}: {msg['content'][:100]}")
        return "\n".join(lines)

    def generate_agent_summary(self, history: list[dict], patient: dict | None) -> str:
        """Genera resumen con Gemini para el agente (usado en handoff complejo)."""
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
2. 🌡️ Temperatura del lead (caliente 🔥 / templado 🌤️ / frío ❄️) con justificación
3. Datos identificados (nombre, teléfono, email si tiene, pueblo/ubicación)
4. Producto e interés (tratamiento, dosis, tipo de kit)
5. Tipo de entrega solicitada
6. Evaluación de salud (si aplica): condiciones médicas, dosis recomendada
7. ¿Confirmó sus datos? (sí/no)
8. Próxima acción recomendada para la asesora

Sé concisa y directa. Máximo 250 palabras.
""".strip()

        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.exception("Error generando resumen para agente: %s", exc)
            return "No se pudo generar el resumen automático."