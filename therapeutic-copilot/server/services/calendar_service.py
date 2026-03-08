"""
SAATHI AI — Google Calendar Service
OAuth 2.0 flow + Calendar API for appointment event creation.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from config import settings
from loguru import logger
from typing import Optional, List


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _redirect_uri() -> str:
    """Return the configured Google OAuth redirect URI."""
    return settings.GOOGLE_REDIRECT_URI


def build_oauth_flow():
    """Build a Google OAuth2 flow object."""
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = _redirect_uri()
    return flow


class CalendarService:
    """Google Calendar integration for appointment scheduling."""

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate the Google OAuth authorization URL for a clinician.
        Pass clinician_id as state so the callback knows which DB row to update.
        """
        flow = build_oauth_flow()
        kwargs = {
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
        if state:
            kwargs["state"] = state
        auth_url, _ = flow.authorization_url(**kwargs)
        return auth_url

    def exchange_code_for_token(self, code: str) -> str:
        """Exchange an OAuth authorization code for credentials JSON string."""
        flow = build_oauth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        return json.dumps(token_data)

    def _build_service(self, token_json: str):
        """Build an authenticated Google Calendar API service from stored token JSON."""
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token_data = json.loads(token_json)
        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id", settings.GOOGLE_CLIENT_ID),
            client_secret=token_data.get("client_secret", settings.GOOGLE_CLIENT_SECRET),
            scopes=token_data.get("scopes", SCOPES),
        )
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    async def create_appointment_event(
        self,
        token_json: str,
        summary: str,
        start_iso: str,
        end_iso: str,
        attendee_email: Optional[str] = None,
        description: str = "",
    ) -> dict:
        """
        Create a Google Calendar event for an appointment, including a Google Meet link.
        Returns dict with google_event_id, html_link, and meet_link.
        """
        service = self._build_service(token_json)

        # Unique request ID for idempotent conference creation
        conference_request_id = str(uuid.uuid4())

        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_iso, "timeZone": "Asia/Kolkata"},
            "conferenceData": {
                "createRequest": {
                    "requestId": conference_request_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        if attendee_email:
            event_body["attendees"] = [{"email": attendee_email}]

        # conferenceDataVersion=1 required to generate Meet link
        event = (
            service.events()
            .insert(calendarId="primary", body=event_body, conferenceDataVersion=1)
            .execute()
        )
        logger.info(f"Google Calendar event created: {event.get('id')}")

        meet_link = event.get("hangoutLink") or ""
        # Fallback: look inside conferenceData.entryPoints
        if not meet_link:
            conf_data = event.get("conferenceData", {})
            for ep in conf_data.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meet_link = ep.get("uri", "")
                    break

        return {
            "google_event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
            "meet_link": meet_link,
        }

    async def list_events(
        self,
        token_json: str,
        max_results: int = 20,
        time_min: Optional[str] = None,
    ) -> List[dict]:
        """
        List upcoming Google Calendar events for the authenticated clinician.
        time_min: ISO 8601 lower bound; defaults to now (UTC).
        """
        service = self._build_service(token_json)

        if not time_min:
            time_min = datetime.now(tz=timezone.utc).isoformat()

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        logger.info(f"Listed {len(items)} calendar events")

        formatted = []
        for item in items:
            start = item.get("start", {})
            end = item.get("end", {})
            formatted.append(
                {
                    "event_id": item.get("id"),
                    "summary": item.get("summary", ""),
                    "description": item.get("description", ""),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "html_link": item.get("htmlLink"),
                    "meet_link": item.get("hangoutLink") or "",
                    "status": item.get("status"),
                }
            )
        return formatted

    async def delete_event(self, token_json: str, event_id: str) -> None:
        """Delete a Google Calendar event (e.g. on appointment cancellation)."""
        service = self._build_service(token_json)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(f"Google Calendar event deleted: {event_id}")
