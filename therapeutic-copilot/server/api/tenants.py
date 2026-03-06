"""Tenant management API — B2B clinic onboarding."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter()


@router.get("/")
async def list_tenants(db: AsyncSession = Depends(get_db)):
    """List all registered tenants (admin only)."""
    # TODO: Add admin auth guard
    return {"tenants": []}


@router.post("/")
async def create_tenant(payload: dict, db: AsyncSession = Depends(get_db)):
    """Register a new clinic/tenant."""
    # TODO: Implement tenant creation with widget_token generation
    return {"message": "Tenant created", "tenant_id": "placeholder"}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """Get tenant details by ID."""
    return {"tenant_id": tenant_id}
