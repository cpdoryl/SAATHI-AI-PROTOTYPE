"""Environment variable manager — validates required keys on startup."""
from config import settings
from loguru import logger


def validate_config() -> bool:
    """
    Check that all required environment variables are set.
    Called on application startup. Returns False if critical keys are missing.
    """
    warnings = []
    errors = []

    if not settings.TOGETHER_API_KEY and not settings.LLAMA_CPP_SERVER_URL:
        errors.append("Neither TOGETHER_API_KEY nor LLAMA_CPP_SERVER_URL is set — AI inference disabled")

    if not settings.PINECONE_API_KEY:
        warnings.append("PINECONE_API_KEY not set — RAG knowledge base disabled")

    if not settings.RAZORPAY_KEY_ID:
        warnings.append("RAZORPAY_KEY_ID not set — payments disabled")

    if settings.JWT_SECRET_KEY == "change-me-in-production":
        warnings.append("JWT_SECRET_KEY is using default value — change before deploying")

    for w in warnings:
        logger.warning(f"CONFIG WARNING: {w}")

    for e in errors:
        logger.error(f"CONFIG ERROR: {e}")

    return len(errors) == 0
