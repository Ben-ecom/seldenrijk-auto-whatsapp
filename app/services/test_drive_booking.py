"""
Test Drive Booking Service.
Handles test drive scheduling with Google Calendar and HubSpot CRM integration.
"""
import os
from typing import List, Dict, Any, Optional
import structlog

from app.integrations.google_calendar_client import get_calendar_client
from app.integrations.hubspot_client import get_hubspot_client

logger = structlog.get_logger(__name__)


class TestDriveBookingService:
    """Service for managing test drive bookings."""

    def __init__(self):
        """Initialize test drive booking service."""
        self.calendar_enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
        self.hubspot_enabled = os.getenv("HUBSPOT_ENABLED", "false").lower() == "true"

    async def get_available_slots(
        self,
        days_ahead: int = 7,
        max_slots: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get available test drive slots.

        Args:
            days_ahead: Number of days to look ahead (default: 7)
            max_slots: Maximum number of slots to return (default: 5)

        Returns:
            List of available slots with labels for user display
        """
        if not self.calendar_enabled:
            logger.warning("Calendar integration disabled - returning mock slots")
            return self._get_mock_slots()

        try:
            calendar_client = get_calendar_client()
            slots = await calendar_client.get_available_slots(
                days_ahead=days_ahead,
                slot_duration_minutes=60
            )

            # Return first N slots
            return slots[:max_slots]

        except Exception as e:
            logger.error("Failed to fetch calendar slots", error=str(e), exc_info=True)
            return self._get_mock_slots()

    def _get_mock_slots(self) -> List[Dict[str, Any]]:
        """Return mock slots when Calendar API is unavailable."""
        from datetime import datetime, timedelta

        mock_slots = []
        current_date = datetime.now().date()

        for day_offset in [1, 2, 3]:  # Tomorrow, day after, etc.
            check_date = current_date + timedelta(days=day_offset)
            for hour in [10, 14, 16]:  # 10:00, 14:00, 16:00
                slot_start = datetime.combine(check_date, datetime.min.time()).replace(hour=hour)
                slot_end = slot_start + timedelta(hours=1)

                if day_offset == 1:
                    day_label = "Morgen"
                else:
                    days_nl = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
                    day_label = days_nl[check_date.weekday()]

                mock_slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "label": f"{day_label} {slot_start.strftime('%H:%M')}",
                    "date": check_date.isoformat()
                })

        return mock_slots[:5]

    async def format_slots_message(
        self,
        car_model: str,
        slots: List[Dict[str, Any]]
    ) -> str:
        """
        Format available slots into user-friendly message.

        Args:
            car_model: Car model name
            slots: List of available slots

        Returns:
            Formatted message with slot options
        """
        if not slots:
            return (
                "Sorry, er zijn momenteel geen beschikbare tijdslots voor een proefrit. "
                "Bel ons voor een afspraak: +31 XX XXX XXXX"
            )

        slot_lines = [
            f"{i+1}️⃣ {slot['label']}"
            for i, slot in enumerate(slots)
        ]

        message = f"""🚗 **Proefrit plannen: {car_model}**

Wanneer past het jou?

{chr(10).join(slot_lines)}

Reageer met het nummer van je keuze (bijvoorbeeld "1" voor {slots[0]['label']}).
"""
        return message.strip()

    async def confirm_booking(
        self,
        slot_index: int,
        slots: List[Dict[str, Any]],
        customer_phone: str,
        customer_name: str,
        car_model: str,
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm test drive booking.

        Args:
            slot_index: Selected slot index (0-based)
            slots: Available slots list
            customer_phone: Customer phone number
            customer_name: Customer name
            car_model: Car model
            customer_email: Customer email (optional)

        Returns:
            Dict with booking result:
            {
                "success": bool,
                "event_id": str (if success),
                "deal_id": str (if HubSpot enabled),
                "message": str (confirmation message for user)
            }
        """
        if slot_index >= len(slots):
            return {
                "success": False,
                "message": "Ongeldige keuze. Kies een nummer uit de lijst."
            }

        selected_slot = slots[slot_index]

        # Create calendar event (if enabled)
        event_id = None
        if self.calendar_enabled:
            try:
                calendar_client = get_calendar_client()
                event_id = await calendar_client.create_appointment(
                    summary=f"Proefrit: {car_model} - {customer_name}",
                    start_time=selected_slot["start"],
                    end_time=selected_slot["end"],
                    customer_phone=customer_phone,
                    customer_email=customer_email,
                    description=f"Klant: {customer_name}\nTelefoon: {customer_phone}\nModel: {car_model}"
                )

                if not event_id:
                    logger.error("Failed to create calendar event")
                    return {
                        "success": False,
                        "message": "Sorry, er ging iets mis bij het bevestigen van je afspraak. Probeer opnieuw."
                    }

            except Exception as e:
                logger.error("Calendar booking failed", error=str(e), exc_info=True)
                return {
                    "success": False,
                    "message": "Sorry, er ging iets mis. Bel ons voor een afspraak: +31 XX XXX XXXX"
                }

        # Create HubSpot deal (if enabled)
        deal_id = None
        if self.hubspot_enabled:
            try:
                hubspot_client = get_hubspot_client()

                # Find or create contact
                contact = await hubspot_client.find_contact_by_phone(customer_phone)
                if not contact:
                    # Create contact
                    name_parts = customer_name.split(" ", 1)
                    first_name = name_parts[0] if name_parts else None
                    last_name = name_parts[1] if len(name_parts) > 1 else None

                    contact_id = await hubspot_client.create_contact(
                        phone=customer_phone,
                        first_name=first_name,
                        last_name=last_name,
                        lead_score=50,  # Default score for test drive request
                        lead_status="WARM"
                    )
                else:
                    contact_id = contact["id"]

                # Create deal
                if contact_id:
                    deal_id = await hubspot_client.create_deal(
                        contact_id=contact_id,
                        deal_name=f"Proefrit {car_model}",
                        deal_stage="appointmentscheduled",
                        amount=0.0,
                        close_date=selected_slot["date"]
                    )

                    logger.info(
                        "HubSpot deal created for test drive",
                        deal_id=deal_id,
                        contact_id=contact_id,
                        car_model=car_model
                    )

            except Exception as e:
                logger.error("HubSpot deal creation failed (non-critical)", error=str(e))
                # Continue - don't block booking if HubSpot fails

        # Generate confirmation message
        confirmation_message = f"""✅ **Proefrit bevestigd!**

📅 {selected_slot["label"]}
🚗 {car_model}
📍 Seldenrijk Auto, Hoofdstraat 123

Je ontvangt een bevestiging per WhatsApp 1 uur voor je afspraak.

Tot dan! 👋"""

        logger.info(
            "Test drive booking confirmed",
            customer_phone=customer_phone,
            car_model=car_model,
            slot=selected_slot["label"],
            event_id=event_id,
            deal_id=deal_id
        )

        return {
            "success": True,
            "event_id": event_id,
            "deal_id": deal_id,
            "message": confirmation_message.strip()
        }


# Singleton instance
_booking_service: Optional[TestDriveBookingService] = None


def get_booking_service() -> TestDriveBookingService:
    """Get or create test drive booking service singleton."""
    global _booking_service
    if _booking_service is None:
        _booking_service = TestDriveBookingService()
    return _booking_service
