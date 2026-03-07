"""
Google Calendar OAuth routes.
Flow: clinician clicks "Connect Calendar" → /authorize → Google → /callback → token stored in DB.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Clinician
from services.calendar_service import CalendarService
from loguru import logger

router = APIRouter()


@router.get("/authorize")
async def authorize_google_calendar(clinician_id: str = Query(...)):
    """
    Start the Google OAuth flow for a clinician.
    Redirects the browser to Google's consent page.
    The clinician_id is embedded in the state parameter so the callback
    knows which DB row to update.
    """
    if not __import__("config").settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    service = CalendarService()
    auth_url = service.get_authorization_url()
    # Append clinician_id as state so callback can retrieve it
    sep = "&" if "?" in auth_url else "?"
    return RedirectResponse(url=f"{auth_url}{sep}state={clinician_id}")


@router.get("/oauth/callback")
async def google_oauth_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth callback — exchanges code for token and persists it on the Clinician row.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    clinician_id = state
    result = await db.execute(select(Clinician).where(Clinician.id == clinician_id))
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")

    service = CalendarService()
    try:
        token_json = service.exchange_code_for_token(code)
    except Exception as e:
        logger.error(f"Google token exchange failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to exchange OAuth code")

    clinician.google_calendar_token = token_json
    await db.commit()
    logger.info(f"Google Calendar token stored for clinician {clinician_id}")

    return {"message": "Google Calendar connected successfully", "clinician_id": clinician_id}


@router.get("/status")
async def calendar_status(clinician_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Check whether a clinician has connected their Google Calendar."""
    result = await db.execute(select(Clinician).where(Clinician.id == clinician_id))
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")
    return {
        "clinician_id": clinician_id,
        "calendar_connected": bool(clinician.google_calendar_token),
    }
