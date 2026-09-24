"""Google Calendar tools: list upcoming events and create new ones.

Requires a one-time OAuth setup (see deploy/google_calendar_setup.py), run
locally on a machine with a browser. This module only refreshes the
resulting token — it never runs the interactive consent flow itself, so it
works headlessly on the Raspberry Pi.
"""

import os
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.tools import tool

TOKEN_PATH = "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "UTC")

NOT_CONNECTED_MSG = (
    "Google Calendar is not connected. Run deploy/google_calendar_setup.py "
    "locally (on a machine with a browser) to set it up, then redeploy."
)


def _get_calendar_service():
    """Build an authenticated Calendar API client, or None if not set up yet."""
    if not os.path.exists(TOKEN_PATH):
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@tool
def list_calendar_events(days_ahead: int = 7) -> str:
    """List upcoming events on the user's Google Calendar.

    `days_ahead` controls how far into the future to look (default: 7 days).
    """
    service = _get_calendar_service()
    if service is None:
        return NOT_CONNECTED_MSG

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except Exception as e:
        return f"Failed to fetch calendar events: {e}"

    events = events_result.get("items", [])
    if not events:
        return f"No upcoming events in the next {days_ahead} day(s)."

    lines = [f"Upcoming events (next {days_ahead} day(s)):"]
    for event in events:
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "?"))
        summary = event.get("summary", "(no title)")
        lines.append(f"- {start}: {summary}")
    return "\n".join(lines)


@tool
def create_calendar_event(summary: str, start_datetime: str, end_datetime: str, description: str = "") -> str:
    """Create a new event on the user's Google Calendar.

    `start_datetime` and `end_datetime` must be ISO 8601 datetimes without a
    timezone offset, e.g. "2026-09-25T14:00:00" — they're interpreted in the
    bot's configured CALENDAR_TIMEZONE (defaults to UTC if not set).
    """
    service = _get_calendar_service()
    if service is None:
        return NOT_CONNECTED_MSG

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": CALENDAR_TIMEZONE},
        "end": {"dateTime": end_datetime, "timeZone": CALENDAR_TIMEZONE},
    }

    try:
        created = service.events().insert(calendarId="primary", body=event_body).execute()
    except Exception as e:
        return f"Failed to create calendar event: {e}"

    return f"Event created: {created.get('summary')} at {start_datetime} ({created.get('htmlLink')})"
