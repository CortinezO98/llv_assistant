# LLV Assistant — Chatbot IA para LRV Aesthetic & Wellness Clinic

Bot conversacional IA-first construido con **FastAPI + Google Gemini Flash 1.5 + WhatsApp Business API**.

## Stack
- **Backend:** FastAPI (Python 3.11+) + SQLAlchemy + MySQL
- **IA:** Google Gemini Flash 1.5 (motor central NLP)
- **Canal:** Meta WhatsApp Business API (Cloud API)
- **Frontend:** React + TypeScript + Vite + TailwindCSS
- **Workers:** APScheduler + Outbox transaccional

## Inicio rápido (local con Docker)

```bash
# 1. Clonar
git clone https://github.com/TU_USER/llv-assistant.git
cd llv-assistant

# 2. Configurar variables de entorno
cp backend/.env.example backend/.env
# → Editar backend/.env con tus credenciales

# 3. Levantar todo
docker compose up --build

# 4. Crear tablas
docker compose exec backend python scripts/create_tables.py

# 5. Cargar FAQ inicial
docker compose exec backend python scripts/seed_faq.py
```

El backend estará en http://localhost:8000  
El frontend estará en http://localhost:5173  
Docs API (solo dev): http://localhost:8000/docs

## Estructura del proyecto

```
llv-assistant/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Endpoints REST
│   │   ├── bot/              # Motor de conversación
│   │   ├── core/             # Settings, seguridad
│   │   ├── db/models/        # Modelos SQLAlchemy
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Lógica de negocio
│   │   └── workers/          # Workers asíncronos
│   ├── scripts/              # Scripts de setup
│   └── tests/
├── frontend/                 # Dashboard React
├── docs/                     # Documentación técnica
└── docker-compose.yml
```

## Variables de entorno requeridas

Ver `backend/.env.example` para la lista completa.
