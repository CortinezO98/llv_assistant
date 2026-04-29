"""
scripts/seed_data.py

Carga inicial de datos:
1. Crea el usuario administrador
2. Crea los 6 agentes iniciales de LRV
3. Carga las 22 preguntas frecuentes de la guía instructiva

Ejecutar: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import hash_password
from app.db.models.agent import Agent
from app.db.models.messaging import FAQ
from app.db.session import SessionLocal

db = SessionLocal()

# ── AGENTES ───────────────────────────────────────────────────────────────────
AGENTS = [
    # Admin
    {"name": "Linhaar López", "email": "linhaar@llvclinic.com", "password": "CambiarEsto2024!", "role": "admin", "location": "puerto_rico"},
    # Supervisores y agentes PR
    {"name": "Agente PR-1", "email": "agente1.pr@llvclinic.com", "password": "CambiarEsto2024!", "role": "agent", "location": "puerto_rico"},
    {"name": "Agente PR-2", "email": "agente2.pr@llvclinic.com", "password": "CambiarEsto2024!", "role": "agent", "location": "puerto_rico"},
    {"name": "Agente PR-3", "email": "agente3.pr@llvclinic.com", "password": "CambiarEsto2024!", "role": "agent", "location": "puerto_rico"},
    # Agentes LATAM
    {"name": "Agente LATAM-1", "email": "agente1.latam@llvclinic.com", "password": "CambiarEsto2024!", "role": "agent", "location": "latam"},
    {"name": "Agente LATAM-2", "email": "agente2.latam@llvclinic.com", "password": "CambiarEsto2024!", "role": "agent", "location": "latam"},
]

print("Creando agentes...")
for a_data in AGENTS:
    existing = db.query(Agent).filter(Agent.email == a_data["email"]).first()
    if not existing:
        agent = Agent(
            name=a_data["name"],
            email=a_data["email"],
            password_hash=hash_password(a_data["password"]),
            role=a_data["role"],
            location=a_data["location"],
        )
        db.add(agent)
        print(f"  ✅ Creado: {a_data['name']} ({a_data['role']})")
    else:
        print(f"  ⏭️  Ya existe: {a_data['name']}")

# ── FAQ ────────────────────────────────────────────────────────────────────────
FAQS = [
    # TRATAMIENTO
    ("tratamiento", "¿Qué son el Semaglutide y el Tirzepatide?",
     "Son medicamentos agonistas GLP-1 (y en el caso del Tirzepatide, también actúa sobre el receptor GIP) que ayudan a regular el apetito y mejorar la forma en que tu cuerpo gestiona la alimentación. Actúan a nivel hormonal logrando disminuir el hambre, aumentar la sensación de saciedad, reducir los antojos y darte mayor control sobre lo que comes, permitiendo una pérdida de peso progresiva, natural y sostenible."),
    ("tratamiento", "¿Cuál es la diferencia entre Semaglutide y Tirzepatide?",
     "El SEMAGLUTIDE actúa sobre el receptor GLP-1 y es ideal para pacientes con mayor peso (más de 200 lbs) o que buscan un efecto más fuerte en el control del apetito. El TIRZEPATIDE tiene doble acción (GLP-1 y GIP) y es ideal para pacientes con menor peso (menos de 200 lbs) o que prefieren una mejor tolerancia. En ambos casos se aplica una vez por semana de forma subcutánea."),
    ("tratamiento", "¿Cuántas veces a la semana se aplica el tratamiento?",
     "Una vez por semana, el mismo día cada semana, de forma subcutánea. Es importante mantener el mismo día para asegurar la continuidad y mejores resultados."),
    ("tratamiento", "¿Qué personas NO pueden usar este tratamiento?",
     "Este tratamiento NO está recomendado para mujeres embarazadas ni en período de lactancia. Personas con otras condiciones médicas deben informarlo previamente con su doctor."),
    ("tratamiento", "¿Puedo usar el tratamiento si tengo tiroides o diabetes?",
     "Sí, en muchos casos personas con tiroides o diabetes pueden utilizarlo. Sin embargo, es importante informarlo previamente con tu doctor. Los resultados pueden variar según el metabolismo."),
    ("tratamiento", "¿Puedo suspender el tratamiento?",
     "Sí puedes suspenderlo, pero lo recomendable es hacer una disminución progresiva de la dosis para evitar descompensaciones. No se recomienda suspenderlo de forma brusca."),
    ("tratamiento", "¿El tratamiento genera dependencia?",
     "No genera dependencia. Sin embargo, el cuerpo sí se adapta a su uso, por lo que no se recomienda suspenderlo bruscamente. Lo ideal es reducir la frecuencia gradualmente."),
    ("tratamiento", "¿Qué pasa cuando llego a mi peso ideal?",
     "Se recomienda pasar a una fase de mantenimiento disminuyendo progresivamente la frecuencia: de semanal a cada 15 días, luego mensual, hasta que el cuerpo se mantenga sin el tratamiento. Esto evita el efecto rebote."),
    # APLICACION
    ("aplicacion", "¿Cómo se aplica el Semaglutide o Tirzepatide?",
     "Se aplica en el abdomen, 2 dedos al lado del ombligo. Pasos: 1. Limpia la zona con alcohol. 2. Pellizca ligeramente la piel. 3. Inserta la aguja en 90°. 4. Aplica lentamente. 5. Retira y desecha. Alterna el lado cada semana. Usa la aguja PEQUEÑA subcutánea."),
    ("aplicacion", "¿Cómo se aplica el quemador de grasa?",
     "Se aplica en el glúteo (recomendado), brazo o muslo, de forma intramuscular. Pasos: 1. Limpia la zona. 2. Inserta la aguja completamente a 90°. 3. Aplica lentamente. 4. Retira y desecha. Usa la aguja GRANDE intramuscular."),
    ("aplicacion", "¿Puedo usar la misma aguja para el medicamento y el quemador?",
     "No. El medicamento principal usa aguja PEQUEÑA (subcutánea) y el quemador usa aguja GRANDE (intramuscular). Usar la aguja incorrecta puede causar dolor o mala aplicación."),
    ("aplicacion", "¿Puedo aplicar el quemador de grasa en el abdomen?",
     "No. El quemador es intramuscular y debe aplicarse en glúteo, brazo o muslo. Aplicarlo en el abdomen es incorrecto y puede generar molestias."),
    ("aplicacion", "¿Las jeringas tienen un orden específico?",
     "Sí. Las jeringas suelen estar numeradas (1, 2, 3, 4) indicando el orden correcto porque el tratamiento maneja dosis progresivas para que el cuerpo se adapte gradualmente."),
    ("aplicacion", "¿Qué hago si olvidé aplicar una dosis?",
     "Aplícala tan pronto lo recuerdes si no ha pasado demasiado tiempo. Lo ideal es mantener un día fijo de aplicación semanal para asegurar la continuidad."),
    # PRODUCTOS
    ("productos", "¿Qué incluye el kit de tratamiento?",
     "El kit incluye: instrucciones de uso, medicamento principal refrigerado (Semaglutide o Tirzepatide), quemador de grasa, toallitas con alcohol y agujas para aplicación correcta. El contenido puede variar según el pedido."),
    ("productos", "¿Cuáles son los quemadores de grasa disponibles?",
     "LIPOMINOMIX: moviliza y metaboliza la grasa como fuente de energía. CO MIC LC: apoya el hígado en el procesamiento de grasas. GLUTATHIONE: antioxidante que desintoxica el organismo y mejora el metabolismo."),
    # CUIDADOS
    ("cuidados", "¿Debo mantener el medicamento refrigerado?",
     "Sí, entre 2°C y 8°C. No debe congelarse. Se recomienda guardarlo en la puerta de la nevera para evitar que se congele."),
    ("cuidados", "¿Qué pasa si el medicamento llega a temperatura ambiente?",
     "No pasa nada. Puede mantenerse fuera de refrigeración unos días sin perder efectividad, siempre que no esté expuesto a calor extremo o luz solar directa. Una vez lo recibas, guárdalo en la nevera."),
    # RESULTADOS
    ("resultados", "¿Cuáles son los efectos secundarios?",
     "Pueden presentarse náuseas, vómitos, dolor de cabeza o malestar estomacal durante las primeras semanas mientras el cuerpo se adapta. Son temporales y puedes tomar medicamentos para aliviarlos sin afectar la efectividad del tratamiento."),
    ("resultados", "¿Cuándo empezaré a ver resultados?",
     "Desde las primeras semanas, aunque varía según cada persona. El metabolismo, la alimentación y la constancia influyen directamente en la velocidad del proceso."),
    ("resultados", "¿Es necesario hacer dieta o ejercicio?",
     "No es obligatorio, pero sí altamente recomendable. Una alimentación balanceada y actividad física permiten obtener resultados más rápidos y efectivos."),
    ("resultados", "¿Los resultados se mantienen al dejar el tratamiento?",
     "Para mantener los resultados a largo plazo es importante acompañar el tratamiento con hábitos saludables de alimentación y actividad física."),
]

print("\nCargando FAQ...")
for i, (cat, q, a) in enumerate(FAQS, 1):
    existing = db.query(FAQ).filter(FAQ.question == q).first()
    if not existing:
        faq = FAQ(category=cat, question=q, answer=a, is_active=1)
        db.add(faq)
        print(f"  ✅ FAQ #{i}: [{cat}] {q[:60]}...")
    else:
        print(f"  ⏭️  Ya existe: {q[:60]}...")

db.commit()
db.close()

print(f"\n✅ Seed completado. {len(FAQS)} FAQs + {len(AGENTS)} agentes cargados.")
print("\n⚠️  IMPORTANTE: Cambia las contraseñas de los agentes en el dashboard antes de ir a producción.")
