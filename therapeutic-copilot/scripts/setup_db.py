"""
SAATHI AI — Database Setup Script
Creates tables and seeds initial data for development.

Usage:
  python scripts/setup_db.py
  python scripts/setup_db.py --seed   (with sample data)
"""
import asyncio
import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from database import async_engine, Base
from models import *  # noqa
import uuid


async def create_tables():
    print("Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")


async def seed_demo_data():
    """Insert demo tenant, clinician, and patient for development."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    print("Seeding demo data...")

    async with AsyncSessionLocal() as db:
        # Create demo tenant
        await db.execute(text("""
            INSERT OR IGNORE INTO tenants (id, name, domain, widget_token, plan)
            VALUES (:id, :name, :domain, :token, :plan)
        """), {
            "id": "demo-tenant-001",
            "name": "MindWell Clinic",
            "domain": "mindwellclinic.com",
            "token": "demo_widget_token_abc123",
            "plan": "professional",
        })
        await db.commit()
    print("Demo data seeded. Widget token: demo_widget_token_abc123")


async def main(seed: bool):
    await create_tables()
    if seed:
        await seed_demo_data()
    print("Setup complete!")
    await async_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Seed demo data")
    args = parser.parse_args()
    asyncio.run(main(seed=args.seed))
