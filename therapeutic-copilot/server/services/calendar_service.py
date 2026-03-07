"""
SAATHI AI — Google Calendar Service
OAuth 2.0 flow + Calendar API for appointment event creation.
"""
import json
from config import settings
from loguru import logger
from typing import Optional


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_URI = "http://localhost:8000/api/v1/calendar/oauth/callback"


def build_oauth_flow():
    """Build a Google OAuth2 flow object."""
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


class CalendarService:
    """Google Calendar integration for appointment scheduling."""

    def get_authorization_url(self) -> str:
        """Generate the Google OAuth authorization URL for a clinician."""
        flow = build_oauth_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
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
        Create a Google Calendar event for an appointment.
        Returns the created event dict (includes htmlLink and id).
        """
        service = self._build_service(token_json)

        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_iso, "timeZone": "Asia/Kolkata"},
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

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        logger.info(f"Google Calendar event created: {event.get('id')}")
        return {
            "google_event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
        }

    async def delete_event(self, token_json: str, event_id: str) -> None:
        """Delete a Google Calendar event (e.g. on appointment cancellation)."""
        service = self._build_service(token_json)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(f"Google Calendar event deleted: {event_id}")
