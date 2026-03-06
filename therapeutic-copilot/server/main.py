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
from database import async_engine, Base

# ─── Route imports ────────────────────────────────────────────────────────────
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.assessment_routes import router as assessment_router
from routes.crisis_routes import router as crisis_router
from routes.rag_routes import router as rag_router
from routes.widget_routes import router as widget_router
from routes.payment_routes import router as payment_router
from routes.websocket_routes import router as ws_router

# ─── API route imports ────────────────────────────────────────────────────────
from api.tenants import router as tenants_router
from api.users import router as users_router
from api.leads import router as leads_router
from api.appointments import router as appointments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Create tables if they don't exist (use Alembic for migrations in prod)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised.")
    yield
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


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Saathi AI is running", "version": settings.APP_VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG_MODE)
