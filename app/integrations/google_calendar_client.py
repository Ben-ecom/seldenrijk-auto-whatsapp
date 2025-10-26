"""
Google Calendar API client.
Handles appointment scheduling, availability checks, and reminders.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import structlog

logger = structlog.get_logger(__name__)


class GoogleCalendarClient:
    """Google Calendar client for appointment management."""

    def __init__(self):
        """Initialize Google Calendar client from service account credentials."""
        credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not credentials_path:
            raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            self.service = build('calendar', 'v3', credentials=credentials)
            self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        except Exception as e:
            logger.error("google_calendar_init_failed", error=str(e))
            raise

    async def get_available_slots(
        self,
        days_ahead: int = 14,
        slot_duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots.

        Args:
            days_ahead: Number of days to check (default: 14)
            slot_duration_minutes: Slot duration (default: 60)

        Returns:
            List of available slots with start/end times

        Business Rules:
            - Working hours: 09:00-18:00
            - Working days: Monday-Saturday
            - Lunch break: 12:00-13:00
            - No Sundays
        """
        try:
            # Get existing events
            time_min = datetime.utcnow().isoformat() + 'Z'
            time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            existing_events = events_result.get('items', [])

            # Generate all possible slots
            available_slots = []
            current_date = datetime.now().date()

            for day_offset in range(days_ahead):
                check_date = current_date + timedelta(days=day_offset)

                # Skip Sundays
                if check_date.weekday() == 6:
                    continue

                # Generate slots for this day
                for hour in range(9, 18):  # 09:00-18:00
                    # Skip lunch break (12:00-13:00)
                    if hour == 12:
                        continue

                    slot_start = datetime.combine(check_date, datetime.min.time()).replace(hour=hour)
                    slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

                    # Check if slot conflicts with existing events
                    is_available = True
                    for event in existing_events:
                        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                        event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))

                        # Check for overlap
                        if not (slot_end <= event_start or slot_start >= event_end):
                            is_available = False
                            break

                    if is_available:
                        # Format label (e.g., "Morgen 10:00", "Dinsdag 14:00")
                        if day_offset == 0:
                            day_label = "Vandaag"
                        elif day_offset == 1:
                            day_label = "Morgen"
                        else:
                            days_nl = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
                            day_label = days_nl[check_date.weekday()]

                        available_slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "label": f"{day_label} {slot_start.strftime('%H:%M')}",
                            "date": check_date.isoformat()
                        })

            logger.info("calendar_slots_generated", count=len(available_slots))
            return available_slots

        except HttpError as e:
            logger.error("calendar_slots_fetch_failed", error=str(e))
            return []

    async def create_appointment(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        customer_phone: str,
        customer_email: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Create appointment in Google Calendar.

        Args:
            summary: Event title (e.g., "Proefrit: VW Golf - Jan de Vries")
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            customer_phone: Customer phone number
            customer_email: Customer email (optional)
            description: Event description

        Returns:
            Event ID if created successfully, None otherwise
        """
        try:
            event = {
                'summary': summary,
                'description': description or f"Contact: {customer_phone}",
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Europe/Amsterdam'
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Europe/Amsterdam'
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'sms', 'minutes': 60},  # 1 hour before
                        {'method': 'email', 'minutes': 1440}  # 1 day before
                    ]
                }
            }

            if customer_email:
                event['attendees'] = [{'email': customer_email}]

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            logger.info(
                "calendar_event_created",
                event_id=created_event['id'],
                summary=summary,
                start=start_time
            )

            return created_event['id']

        except HttpError as e:
            logger.error("calendar_event_create_failed", error=str(e))
            return None

    async def cancel_appointment(self, event_id: str) -> bool:
        """
        Cancel appointment.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            logger.info("calendar_event_cancelled", event_id=event_id)
            return True

        except HttpError as e:
            logger.error("calendar_event_cancel_failed", event_id=event_id, error=str(e))
            return False


# Singleton instance
_calendar_client: Optional[GoogleCalendarClient] = None


def get_calendar_client() -> GoogleCalendarClient:
    """Get or create Google Calendar client singleton."""
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = GoogleCalendarClient()
    return _calendar_client
