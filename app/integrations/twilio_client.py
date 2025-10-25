"""
Twilio WhatsApp Service Client

Centralized wrapper for Twilio WhatsApp Business API operations.
Handles message sending, delivery tracking, and error recovery.

Features:
- Automatic retry with exponential backoff
- Rate limiting (compliance with Twilio limits)
- Comprehensive error handling
- Delivery status webhooks
- Media message support (future)
"""
import os
import logging
from typing import Optional, Dict, Any, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import time
from functools import wraps

logger = logging.getLogger(__name__)


class TwilioWhatsAppClient:
    """
    Twilio WhatsApp Business API client.

    Provides high-level interface for sending WhatsApp messages via Twilio.
    Handles authentication, rate limiting, retries, and error recovery.

    Usage:
        client = TwilioWhatsAppClient()
        result = await client.send_message(
            to_number="+31612345678",
            message="Hello from Seldenrijk Auto!"
        )
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        """
        Initialize Twilio client.

        Args:
            account_sid: Twilio Account SID (defaults to env var)
            auth_token: Twilio Auth Token (defaults to env var)
            from_number: WhatsApp sender number (defaults to env var)
        """
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_WHATSAPP_NUMBER")

        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError(
                "Missing Twilio credentials. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_NUMBER environment variables."
            )

        # Initialize Twilio REST client
        self.client = Client(self.account_sid, self.auth_token)

        # Rate limiting (Twilio allows 80 messages/second per account)
        self._rate_limit_window = 1.0  # 1 second window
        self._rate_limit_max_messages = 80
        self._message_timestamps: List[float] = []

        logger.info(
            "Twilio WhatsApp client initialized",
            extra={"from_number": self.from_number}
        )

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if we can send, False if rate limited
        """
        now = time.time()

        # Remove timestamps older than rate limit window
        self._message_timestamps = [
            ts for ts in self._message_timestamps
            if now - ts < self._rate_limit_window
        ]

        # Check if we're at limit
        if len(self._message_timestamps) >= self._rate_limit_max_messages:
            logger.warning(
                "Rate limit reached",
                extra={
                    "messages_in_window": len(self._message_timestamps),
                    "max_allowed": self._rate_limit_max_messages
                }
            )
            return False

        return True

    def _record_message_sent(self):
        """Record that a message was sent (for rate limiting)."""
        self._message_timestamps.append(time.time())

    async def send_message(
        self,
        to_number: str,
        message: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message via Twilio.

        Args:
            to_number: Recipient phone number (E.164 format, e.g., "+31612345678")
            message: Message text (max 1600 characters)
            max_retries: Maximum retry attempts on failure
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Dict with status and message details:
            {
                "status": "sent" | "failed" | "rate_limited",
                "message_sid": "SM...",
                "to": "+31612345678",
                "error": Optional error message
            }

        Raises:
            ValueError: If to_number is invalid or message too long
        """
        # Validate inputs
        if not to_number:
            raise ValueError("to_number is required")

        if not message:
            raise ValueError("message is required")

        if len(message) > 1600:
            logger.warning(
                f"Message truncated from {len(message)} to 1600 characters",
                extra={"to": to_number}
            )
            message = message[:1600]

        # Normalize phone number (add whatsapp: prefix if missing)
        if not to_number.startswith("whatsapp:"):
            to_number_normalized = f"whatsapp:{to_number}"
        else:
            to_number_normalized = to_number

        # Check rate limit
        if not self._check_rate_limit():
            return {
                "status": "rate_limited",
                "to": to_number,
                "error": "Rate limit exceeded (80 messages/second)"
            }

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                # Send message via Twilio
                twilio_message = self.client.messages.create(
                    from_=self.from_number,
                    to=to_number_normalized,
                    body=message
                )

                # Record for rate limiting
                self._record_message_sent()

                logger.info(
                    "Message sent successfully",
                    extra={
                        "message_sid": twilio_message.sid,
                        "to": to_number,
                        "status": twilio_message.status,
                        "attempt": attempt + 1
                    }
                )

                return {
                    "status": "sent",
                    "message_sid": twilio_message.sid,
                    "to": to_number,
                    "twilio_status": twilio_message.status,
                    "price": twilio_message.price,
                    "price_unit": twilio_message.price_unit
                }

            except TwilioRestException as e:
                last_error = e

                # Log error details
                logger.error(
                    f"Twilio API error (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "error_code": e.code,
                        "error_message": e.msg,
                        "to": to_number,
                        "status": e.status
                    }
                )

                # Don't retry on permanent errors
                if e.code in [21211, 21612, 21614]:  # Invalid phone, unregistered, etc.
                    logger.error(
                        "Permanent error - not retrying",
                        extra={"error_code": e.code}
                    )
                    break

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error sending message (attempt {attempt + 1}/{max_retries})",
                    exc_info=True
                )

                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))

        # All retries failed
        return {
            "status": "failed",
            "to": to_number,
            "error": str(last_error),
            "attempts": max_retries
        }

    async def send_message_batch(
        self,
        messages: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Send multiple messages (respecting rate limits).

        Args:
            messages: List of dicts with "to" and "message" keys

        Returns:
            List of send results
        """
        results = []

        for msg in messages:
            result = await self.send_message(
                to_number=msg["to"],
                message=msg["message"]
            )
            results.append(result)

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        return results

    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get delivery status of a sent message.

        Args:
            message_sid: Twilio message SID

        Returns:
            Dict with message status details
        """
        try:
            message = self.client.messages(message_sid).fetch()

            return {
                "status": message.status,
                "sid": message.sid,
                "to": message.to,
                "from": message.from_,
                "date_sent": message.date_sent,
                "error_code": message.error_code,
                "error_message": message.error_message
            }

        except TwilioRestException as e:
            logger.error(f"Error fetching message status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global client instance (initialized on first use)
_twilio_client: Optional[TwilioWhatsAppClient] = None


def get_twilio_client() -> TwilioWhatsAppClient:
    """
    Get or create global Twilio client instance.

    Returns:
        TwilioWhatsAppClient singleton
    """
    global _twilio_client

    if _twilio_client is None:
        _twilio_client = TwilioWhatsAppClient()

    return _twilio_client
