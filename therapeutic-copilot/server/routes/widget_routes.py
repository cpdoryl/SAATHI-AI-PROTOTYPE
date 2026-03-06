"""Widget API routes — serve config and JS bundle to embedded B2B widget."""
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/config")
async def get_widget_config(x_widget_token: str = Header(None)):
    """
    Return widget configuration for a tenant.
    Called by the embedded widget on initialisation.
    Validates widget_token → returns branding, AI persona config.
    """
    if not x_widget_token:
        raise HTTPException(status_code=401, detail="Widget token required")
    # TODO: Look up tenant by widget_token
    return {
        "tenant_id": "placeholder",
        "persona_name": "Saathi",
        "primary_color": "#4F46E5",
        "greeting": "Hi! I'm Saathi. How can I support you today?",
        "language": "en",
    }


@router.get("/bundle.js")
async def serve_widget_bundle():
    """Serve the compiled widget JavaScript bundle."""
    return FileResponse(
        path="../../widget/dist/widget.bundle.js",
        media_type="application/javascript",
    )
