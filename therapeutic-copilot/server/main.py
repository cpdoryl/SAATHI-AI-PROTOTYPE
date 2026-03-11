"""
SAATHI AI — FastAPI Application Entry Point
Therapeutic Co-Pilot Backend | RYL NEUROACADEMY PRIVATE LIMITED
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from config import settings
from database import async_engine, Base, AsyncSessionLocal

# ─── Route imports ────────────────────────────────────────────────────────────
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.assessment_routes import router as assessment_router
from routes.crisis_routes import router as crisis_router
from routes.rag_routes import router as rag_router
from routes.widget_routes import router as widget_router
from routes.payment_routes import router as payment_router
from routes.websocket_routes import router as ws_router
from routes.calendar_routes import router as calendar_router

# ─── API route imports ────────────────────────────────────────────────────────
from api.tenants import router as tenants_router
from api.users import router as users_router
from api.leads import router as leads_router
from api.appointments import router as appointments_router
from api.patients import router as patients_router
from api.analytics import router as analytics_router


async def _dropout_scan_job():
    """APScheduler job: daily dropout re-engagement scan."""
    from services.dropout_service import DropoutService
    async with AsyncSessionLocal() as db:
        try:
            service = DropoutService()
            flagged = await service.scan_inactive_patients(db)
            logger.info(f"[cron] Dropout scan: {len(flagged)} patients flagged for re-engagement")
        except Exception as exc:
            logger.error(f"[cron] Dropout scan failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Create tables if they don't exist (use Alembic for migrations in prod)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised.")

    # ─── ML Crisis Model: warm up on startup (loads weights into memory) ─────────
    try:
        import asyncio as _asyncio
        from services.ml_crisis_service import get_ml_crisis_service
        # Load model in thread pool (CPU-bound, avoids blocking the event loop)
        svc = await _asyncio.get_event_loop().run_in_executor(
            None, get_ml_crisis_service
        )
        if svc.is_ready:
            logger.info("ML crisis model loaded and ready (DistilBERT 6-class).")
        else:
            logger.warning(
                "ML crisis model NOT loaded — keyword-only fallback is active. "
                "Run: python scripts/setup_crisis_model.py to install weights."
            )
    except Exception as _exc:
        logger.warning(f"ML crisis model warm-up failed: {_exc}. Keyword fallback active.")

    # ─── Emotion Classifier: warm up on startup ──────────────────────────────
    try:
        import asyncio as _asyncio2
        from services.emotion_classifier_service import get_emotion_service
        emo_svc = await _asyncio2.get_event_loop().run_in_executor(
            None, get_emotion_service
        )
        if emo_svc.is_ready:
            logger.info("Emotion classifier loaded and ready (DistilBERT 8-class).")
        else:
            logger.warning(
                "Emotion classifier NOT loaded — emotion detection disabled. "
                "Run: python scripts/setup_emotion_model.py to install weights."
            )
    except Exception as _exc:
        logger.warning(f"Emotion classifier warm-up failed: {_exc}.")

    # ─── Intent Classifier: warm up on startup ───────────────────────────────
    try:
        import asyncio as _asyncio3
        from services.intent_classifier_service import get_intent_service
        intent_svc = await _asyncio3.get_event_loop().run_in_executor(
            None, get_intent_service
        )
        if intent_svc.is_ready:
            logger.info("Intent classifier loaded and ready (DistilBERT 7-class).")
        else:
            logger.warning(
                "Intent classifier NOT loaded — intent routing disabled. "
                "Run: python scripts/setup_intent_model.py to install weights."
            )
    except Exception as _exc:
        logger.warning(f"Intent classifier warm-up failed: {_exc}.")

    # ─── Topic Classifier: warm up on startup ────────────────────────────────
    try:
        import asyncio as _asyncio4
        from services.topic_classifier_service import get_topic_service
        topic_svc = await _asyncio4.get_event_loop().run_in_executor(
            None, get_topic_service
        )
        if topic_svc.is_ready:
            logger.info("Topic classifier loaded and ready (DistilBERT 5-label multi-label).")
        else:
            logger.warning(
                "Topic classifier NOT loaded — topic context disabled. "
                "Run: python scripts/setup_topic_model.py to install weights."
            )
    except Exception as _exc:
        logger.warning(f"Topic classifier warm-up failed: {_exc}.")

    # ─── APScheduler: daily dropout re-engagement cron ────────────────────────
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            _dropout_scan_job,
            trigger=CronTrigger(hour=9, minute=0),  # 09:00 UTC daily
            id="dropout_scan",
            name="Daily dropout re-engagement scan",
            replace_existing=True,
        )
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("APScheduler started: dropout scan at 09:00 UTC daily")
    except ImportError:
        logger.warning("APScheduler not installed — dropout cron job disabled")

    yield

    # ─── Shutdown ────────────────────────────────────────────────────────────
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown(wait=False)
    logger.info("Shutting down Saathi AI backend.")
    await async_engine.dispose()


# ─── App factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="B2B SaaS Therapeutic Co-Pilot — AI-powered mental healthcare platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Rate limiting (Redis sliding window) ─────────────────────────────────────
from middleware.rate_limit_middleware import rate_limit_middleware  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware           # noqa: E402
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router,        prefix="/api/v1/auth",        tags=["Auth"])
app.include_router(chat_router,        prefix="/api/v1/chat",        tags=["Chat"])
app.include_router(assessment_router,  prefix="/api/v1/assessments", tags=["Assessments"])
app.include_router(crisis_router,      prefix="/api/v1/crisis",      tags=["Crisis"])
app.include_router(rag_router,         prefix="/api/v1/rag",         tags=["RAG"])
app.include_router(widget_router,      prefix="/api/v1/widget",      tags=["Widget"])
app.include_router(payment_router,     prefix="/api/v1/payments",    tags=["Payments"])
app.include_router(ws_router,          prefix="/ws",                 tags=["WebSocket"])
app.include_router(tenants_router,     prefix="/api/v1/tenants",     tags=["Tenants"])
app.include_router(users_router,       prefix="/api/v1/users",       tags=["Users"])
app.include_router(leads_router,       prefix="/api/v1/leads",       tags=["Leads"])
app.include_router(appointments_router, prefix="/api/v1/appointments", tags=["Appointments"])
app.include_router(patients_router,    prefix="/api/v1/patients",    tags=["Patients"])
app.include_router(calendar_router,    prefix="/api/v1/calendar",    tags=["Calendar"])
app.include_router(analytics_router,   prefix="/api/v1/analytics",   tags=["Analytics"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Saathi AI is running", "version": settings.APP_VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG_MODE)
