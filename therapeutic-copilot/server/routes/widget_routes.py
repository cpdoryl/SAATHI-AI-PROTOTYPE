"""Widget API routes — serve config and JS bundle to embedded B2B widget."""
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Tenant

router = APIRouter()


@router.get("/config")
async def get_widget_config(
    x_widget_token: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return widget configuration for a tenant.
    Called by the embedded widget on initialisation.
    Validates widget_token → returns branding, AI persona config.
    """
    if not x_widget_token:
        raise HTTPException(status_code=401, detail="Widget token required")

    result = await db.execute(
        select(Tenant).where(
            Tenant.widget_token == x_widget_token,
            Tenant.is_active.is_(True),
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive widget token",
        )

    return {
        "tenant_id": tenant.id,
        "persona_name": "Saathi",
        "primary_color": "#4F46E5",
        "greeting": "Hi! I'm Saathi. How can I support you today?",
        "language": "en",
        "pinecone_namespace": tenant.pinecone_namespace,
    }


@router.get("/bundle.js")
async def serve_widget_bundle():
    """Serve the compiled widget JavaScript bundle."""
    return FileResponse(
        path="../../widget/dist/widget.bundle.js",
        media_type="application/javascript",
    )
