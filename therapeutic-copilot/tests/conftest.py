"""Pytest configuration for Saathi AI test suite."""
import pytest
import asyncio
import sys
import os

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

# Use SQLite for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_saathi.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DEBUG_MODE", "true")
# Pinecone — real credentials not needed; RAG tests mock the Pinecone index directly
os.environ.setdefault("PINECONE_API_KEY", "test-key-not-real")
os.environ.setdefault("PINECONE_INDEX", "test-index")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
