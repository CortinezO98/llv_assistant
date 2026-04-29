from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agents import router as agents_router
from app.api.routes.appointments import appointments_router, patients_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.faq import router as faq_router
from app.api.routes.health import router as health_router
from app.api.routes.plan import router as plan_router
from app.api.routes.webhook import router as webhook_router
from app.core.settings import settings

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando %s | env=%s", settings.app_name, settings.app_env)
    yield
    logger.info("⏹️  Cerrando %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Chatbot IA para LRV Aesthetic & Wellness Clinic",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(patients_router)
app.include_router(appointments_router)
app.include_router(faq_router)
app.include_router(plan_router)
app.include_router(dashboard_router)
