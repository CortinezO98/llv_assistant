"""
backend/main.py

Aplicación principal FastAPI para LLV Assistant.

Responsabilidades:
- Configurar logging estructurado.
- Inicializar WebSocket realtime.
- Registrar rutas REST y webhook.
- Ejecutar workers en segundo plano:
    1. conversation_worker: procesa mensajes entrantes de llv_inbox.
    2. outbox_worker: envía mensajes pendientes a WhatsApp.
    3. followup_worker: seguimiento de clientes inactivos.
    4. session_cleanup_worker: limpieza de sesiones expiradas.

Nota:
- El conversation_worker debe correr cada pocos segundos.
- El followup_worker y cleanup_worker pueden correr cada 30 minutos.
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


# ── Workers en background ─────────────────────────────────────────────────────

async def _run_workers_loop():
    """
    Loop principal de workers.

    Ejecuta frecuentemente:
    - conversation_worker: procesa mensajes pendientes de llv_inbox.
    - outbox_worker: envía respuestas pendientes de llv_outbox.

    Ejecuta cada 30 minutos:
    - followup_worker: seguimiento de clientes inactivos.
    - session_cleanup_worker: limpieza de sesiones vencidas.
    """

    from app.workers.conversation_worker import run_conversation_worker
    from app.workers.followup_worker import run_followup_worker
    from app.workers.outbox_worker import flush_outbox
    from app.workers.session_cleanup_worker import run_cleanup_worker

    conversation_interval = max(2, settings.conversation_worker_interval or 5)
    maintenance_interval = 30 * 60

    last_maintenance_run = 0.0

    # Espera corta para que FastAPI y la DB terminen de levantar.
    await asyncio.sleep(5)

    logger.info(
        "Workers activos | conversation_interval=%ss | maintenance_interval=%ss",
        conversation_interval,
        maintenance_interval,
    )

    while True:
        try:
            loop = asyncio.get_running_loop()

            # 1. Procesar mensajes entrantes del webhook.
            conversation_result = await loop.run_in_executor(
                None,
                run_conversation_worker,
            )

            if (
                conversation_result.get("processed")
                or conversation_result.get("failed")
                or conversation_result.get("skipped")
            ):
                logger.info("Conversation worker | %s", conversation_result)

            # 2. Enviar respuestas pendientes a WhatsApp.
            outbox_result = await loop.run_in_executor(
                None,
                flush_outbox,
            )

            if outbox_result.get("sent") or outbox_result.get("failed"):
                logger.info("Outbox worker | %s", outbox_result)

            # 3. Workers de mantenimiento cada 30 minutos.
            now = loop.time()

            if now - last_maintenance_run >= maintenance_interval:
                followup_result = await loop.run_in_executor(
                    None,
                    run_followup_worker,
                )
                logger.info("Followup worker | %s", followup_result)

                cleanup_result = await loop.run_in_executor(
                    None,
                    run_cleanup_worker,
                )
                logger.info("Cleanup worker | %s", cleanup_result)

                last_maintenance_run = now

        except Exception as exc:
            logger.exception("Error en loop de workers: %s", exc)

        await asyncio.sleep(conversation_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de FastAPI.

    Al iniciar:
    - Configura el loop para realtime WebSocket.
    - Inicia workers en background.

    Al apagar:
    - Cancela el task de workers correctamente.
    """

    logger.info("🚀 %s | env=%s", settings.app_name, settings.app_env)

    loop = asyncio.get_running_loop()

    realtime_manager.set_loop(loop)
    logger.info("⚡ Realtime WebSocket listo")

    worker_task = asyncio.create_task(_run_workers_loop())

    logger.info(
        "🔄 Workers iniciados | conversación cada %ss",
        settings.conversation_worker_interval,
    )

    try:
        yield

    finally:
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