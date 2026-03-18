"""
SAATHI AI — Application Configuration
Centralised settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Saathi AI — Therapeutic Co-Pilot"
    APP_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = False
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./saathi_copilot.db"

    # ─── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ─── Auth / JWT ───────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ─── Encryption ───────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = ""

    # ─── AI Inference (Together AI for dev / llama.cpp for prod) ─────────────
    TOGETHER_API_KEY: str = ""
    TOGETHER_MODEL: str = "Qwen/Qwen2.5-7B-Instruct-Turbo"
    LLAMA_CPP_SERVER_URL: str = "http://localhost:8080"
    # Set to GGUF model path to use llama-cpp-python native bindings (prod preferred)
    LLAMA_CPP_PYTHON_MODEL_PATH: str = ""

    # ─── RAG / Pinecone ───────────────────────────────────────────────────────
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    PINECONE_INDEX: str = "therapeutic-kb"
    # Local ChromaDB path (used when PINECONE_API_KEY is not set)
    LOCAL_RAG_DB_PATH: str = "./chroma_db"

    # ─── Payments ────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""  # Set in Razorpay Dashboard → Webhooks

    # ─── Email (SendGrid) ─────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@saathi-ai.com"

    # ─── Google Calendar ─────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/calendar/callback"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
