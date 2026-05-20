"""
backend/main.py — versión actualizada

Cambios:
    1. Logging estructurado según entorno
    2. Workers de seguimiento, limpieza y outbox integrados como tareas periódicas
    3. Registro del worker de seguimiento en el lifespan
    4. Registro de la ruta de pagos /payments
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agents import router as agents_router
from app.api.routes.appointments import appointments_router, patients_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.deliveries import router as deliveries_router
from app.api.routes.faq import router as faq_router
from app.api.routes.health import router as health_router
from app.api.routes.payments import router as payments_router
from app.api.routes.plan import router as plan_router
from app.api.routes.realtime import router as realtime_router
from app.api.routes.reports import router as reports_router
from app.api.routes.webhook import router as webhook_router

from app.core.settings import settings
from app.services.realtime_manager import realtime_manager
from app.utils.structured_logger import setup_logging


# ── Logging estructurado ──────────────────────────────────────────────────────
setup_logging(settings.app_env)
logger = logging.getLogger(__name__)


# ── Workers periódicos ────────────────────────────────────────────────────────

async def _run_workers_loop():
    """
    Loop que ejecuta los workers de mantenimiento cada 30 minutos.

    Ejecuta:
    - Seguimiento de clientes inactivos.
    - Limpieza de sesiones expiradas.
    - Flush del outbox por si quedaron mensajes pendientes.
    """
    from app.workers.followup_worker import run_followup_worker
    from app.workers.session_cleanup_worker import run_cleanup_worker
    from app.workers.outbox_worker import flush_outbox

    interval_seconds = 30 * 60

    # Esperar 1 minuto al arranque para que la app y DB estén listas.
    await asyncio.sleep(60)

    while True:
        try:
            logger.info("Workers periódicos ejecutándose...")

            loop = asyncio.get_running_loop()

            # Seguimiento de clientes inactivos.
            followup_result = await loop.run_in_executor(
                None,
                run_followup_worker,
            )
            logger.info("Followup worker | %s", followup_result)

            # Limpieza de sesiones expiradas.
            cleanup_result = await loop.run_in_executor(
                None,
                run_cleanup_worker,
            )
            logger.info("Cleanup worker | %s", cleanup_result)

            # Flush outbox residual.
            outbox_result = await loop.run_in_executor(
                None,
                flush_outbox,
            )
            logger.info("Outbox worker | %s", outbox_result)

        except Exception as exc:
            logger.exception("Error en workers periódicos: %s", exc)

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de FastAPI.

    - Configura loop para WebSocket realtime.
    - Inicia workers periódicos.
    - Cancela workers al apagar la app.
    """
    logger.info("🚀 %s | env=%s", settings.app_name, settings.app_env)

    loop = asyncio.get_running_loop()
    realtime_manager.set_loop(loop)
    logger.info("⚡ Realtime WebSocket listo")

    worker_task = asyncio.create_task(_run_workers_loop())
    logger.info("🔄 Workers periódicos iniciados cada 30 minutos")

    yield

    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    logger.info("🛑 Workers detenidos correctamente")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url=None,
)


# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rutas ─────────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(webhook_router)

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(patients_router)
app.include_router(appointments_router)
app.include_router(payments_router)
app.include_router(faq_router)
app.include_router(plan_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(conversations_router)
app.include_router(deliveries_router)
app.include_router(realtime_router)