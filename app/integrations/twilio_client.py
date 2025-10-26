"""
Twilio WhatsApp Service Client

Centralized wrapper for Twilio WhatsApp Business API operations.
Handles message sending, delivery tracking, and error recovery.

Features:
- Automatic retry with exponential backoff
- Rate limiting (compliance with Twilio limits)
- Redis-based message deduplication
- Comprehensive error handling
- Phone number format normalization
- Structured logging
- Delivery status webhooks
- Media message support
"""
import os
import hashlib
import structlog
from typing import Optional, Dict, Any, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import time
from functools import wraps

from app.utils.phone_formatter import format_phone_for_twilio, normalize_phone_to_e164
from app.database.redis_client import get_redis_client

logger = structlog.get_logger(__name__)


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

        # Initialize Redis for deduplication
        self.redis_client = get_redis_client()

        # Rate limiting (Twilio allows 80 messages/second per account)
        self._rate_limit_window = 1.0  # 1 second window
        self._rate_limit_max_messages = 80
        self._message_timestamps: List[float] = []

        logger.info(
            "Twilio WhatsApp client initialized",
            from_number=self.from_number
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
                messages_in_window=len(self._message_timestamps),
                max_allowed=self._rate_limit_max_messages
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
        media_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message via Twilio with deduplication.

        Args:
            to_number: Recipient phone number (any format - will be normalized)
            message: Message text (max 1600 characters)
            media_url: Optional media URL for images/videos
            max_retries: Maximum retry attempts on failure
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Dict with status and message details:
            {
                "status": "sent" | "failed" | "rate_limited" | "duplicate",
                "message_sid": "SM...",
                "to": "+31612345678",
                "error": Optional error message
            }

        Raises:
            ValueError: If to_number is invalid or message too long
        """
        # Validate inputs
        if not message:
            raise ValueError("message is required")

        if len(message) > 1600:
            logger.warning(
                "Message truncated from length",
                original_length=len(message),
                to=to_number
            )
            message = message[:1600]

        # Normalize phone number using formatter
        try:
            to_number_formatted = format_phone_for_twilio(to_number)
            to_number_e164 = normalize_phone_to_e164(to_number)
        except ValueError as e:
            logger.error("Invalid phone number", phone=to_number, error=str(e))
            return {
                "status": "failed",
                "to": to_number,
                "error": f"Invalid phone number: {str(e)}"
            }

        # Deduplication check (1 hour TTL)
        message_hash = hashlib.sha256(f"{to_number_e164}:{message}".encode()).hexdigest()[:16]
        cache_key = f"twilio:send:dedupe:{to_number_e164}:{message_hash}"

        if self.redis_client.get(cache_key):
            logger.info(
                "Duplicate message blocked",
                to=to_number_e164,
                message_hash=message_hash
            )
            return {
                "status": "duplicate",
                "to": to_number_e164,
                "error": "Duplicate message within 1 hour window"
            }

        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded", to=to_number_e164)
            return {
                "status": "rate_limited",
                "to": to_number_e164,
                "error": "Rate limit exceeded (80 messages/second)"
            }

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                # Prepare message parameters
                message_params = {
                    "from_": self.from_number,
                    "to": to_number_formatted,
                    "body": message
                }

                # Add media URL if provided
                if media_url:
                    message_params["media_url"] = [media_url]

                # Send message via Twilio
                twilio_message = self.client.messages.create(**message_params)

                # Record for rate limiting
                self._record_message_sent()

                # Cache deduplication key (1 hour TTL)
                self.redis_client.setex(cache_key, 3600, "1")

                logger.info(
                    "Message sent successfully",
                    message_sid=twilio_message.sid,
                    to=to_number_e164,
                    status=twilio_message.status,
                    attempt=attempt + 1,
                    has_media=bool(media_url)
                )

                return {
                    "status": "sent",
                    "message_sid": twilio_message.sid,
                    "to": to_number_e164,
                    "twilio_status": twilio_message.status,
                    "price": twilio_message.price,
                    "price_unit": twilio_message.price_unit
                }

            except TwilioRestException as e:
                last_error = e

                # Log error details
                logger.error(
                    "Twilio API error",
                    attempt=f"{attempt + 1}/{max_retries}",
                    error_code=e.code,
                    error_message=e.msg,
                    to=to_number_e164,
                    status=e.status
                )

                # Don't retry on permanent errors
                # 21211: Invalid To number
                # 21612: The 'To' number is not currently reachable via SMS or WhatsApp
                # 21614: 'To' number is not a valid mobile number
                # 63016: Message body is required
                # 20003: Authentication Error
                if e.code in [21211, 21612, 21614, 63016, 20003]:
                    logger.error(
                        "Permanent error - not retrying",
                        error_code=e.code
                    )
                    break

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info("Retrying after backoff", wait_seconds=wait_time)
                    time.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(
                    "Unexpected error sending message",
                    attempt=f"{attempt + 1}/{max_retries}",
                    error=str(e),
                    exc_info=True
                )

                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))

        # All retries failed
        return {
            "status": "failed",
            "to": to_number_e164,
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
            logger.error(
                "Error fetching message status",
                message_sid=message_sid,
                error=str(e)
            )
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
