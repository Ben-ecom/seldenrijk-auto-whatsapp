"""
Unit tests for enhanced Twilio WhatsApp client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.integrations.twilio_client import TwilioWhatsAppClient


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = Mock()
    redis_mock.get = Mock(return_value=None)
    redis_mock.setex = Mock(return_value=True)
    return redis_mock


@pytest.fixture
def mock_twilio_message():
    """Mock Twilio message response."""
    message = Mock()
    message.sid = "SM123456789"
    message.status = "queued"
    message.price = "-0.005"
    message.price_unit = "USD"
    return message


@pytest.fixture
def twilio_client(mock_redis):
    """Create Twilio client with mocked dependencies."""
    with patch("app.integrations.twilio_client.get_redis_client", return_value=mock_redis):
        with patch.dict("os.environ", {
            "TWILIO_ACCOUNT_SID": "AC123",
            "TWILIO_AUTH_TOKEN": "token123",
            "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
        }):
            client = TwilioWhatsAppClient()
            return client


@pytest.mark.asyncio
async def test_send_message_success(twilio_client, mock_twilio_message, mock_redis):
    """Test successful message sending."""
    with patch.object(twilio_client.client.messages, "create", return_value=mock_twilio_message):
        result = await twilio_client.send_message(
            to_number="+31612345678",
            message="Test message"
        )

        assert result["status"] == "sent"
        assert result["message_sid"] == "SM123456789"
        assert result["to"] == "+31612345678"

        # Verify deduplication key was cached
        mock_redis.setex.assert_called_once()
        cache_key = mock_redis.setex.call_args[0][0]
        assert cache_key.startswith("twilio:send:dedupe:+31612345678:")


@pytest.mark.asyncio
async def test_send_message_with_waha_format(twilio_client, mock_twilio_message):
    """Test sending message with WAHA phone format."""
    with patch.object(twilio_client.client.messages, "create", return_value=mock_twilio_message):
        result = await twilio_client.send_message(
            to_number="31612345678@c.us",
            message="Test message"
        )

        assert result["status"] == "sent"
        assert result["to"] == "+31612345678"


@pytest.mark.asyncio
async def test_send_message_duplicate_blocked(twilio_client, mock_redis):
    """Test duplicate message is blocked."""
    # Simulate existing cache entry
    mock_redis.get = Mock(return_value="1")

    result = await twilio_client.send_message(
        to_number="+31612345678",
        message="Duplicate message"
    )

    assert result["status"] == "duplicate"
    assert "1 hour" in result["error"]


@pytest.mark.asyncio
async def test_send_message_invalid_phone(twilio_client):
    """Test invalid phone number."""
    result = await twilio_client.send_message(
        to_number="invalid",
        message="Test message"
    )

    assert result["status"] == "failed"
    assert "Invalid phone number" in result["error"]


@pytest.mark.asyncio
async def test_send_message_with_media(twilio_client, mock_twilio_message):
    """Test sending message with media URL."""
    with patch.object(twilio_client.client.messages, "create", return_value=mock_twilio_message) as mock_create:
        result = await twilio_client.send_message(
            to_number="+31612345678",
            message="Image message",
            media_url="https://example.com/image.jpg"
        )

        assert result["status"] == "sent"

        # Verify media_url was passed to Twilio
        call_kwargs = mock_create.call_args[1]
        assert "media_url" in call_kwargs
        assert call_kwargs["media_url"] == ["https://example.com/image.jpg"]


@pytest.mark.asyncio
async def test_send_message_truncates_long_message(twilio_client, mock_twilio_message):
    """Test long message is truncated to 1600 characters."""
    long_message = "x" * 2000

    with patch.object(twilio_client.client.messages, "create", return_value=mock_twilio_message) as mock_create:
        result = await twilio_client.send_message(
            to_number="+31612345678",
            message=long_message
        )

        assert result["status"] == "sent"

        # Verify message was truncated
        call_kwargs = mock_create.call_args[1]
        assert len(call_kwargs["body"]) == 1600


@pytest.mark.asyncio
async def test_send_message_rate_limit(twilio_client):
    """Test rate limiting blocks message."""
    # Fill rate limit window
    twilio_client._message_timestamps = [1000.0] * 80

    with patch("time.time", return_value=1000.5):
        result = await twilio_client.send_message(
            to_number="+31612345678",
            message="Test message"
        )

        assert result["status"] == "rate_limited"
        assert "80 messages/second" in result["error"]


@pytest.mark.asyncio
async def test_send_message_twilio_error_permanent(twilio_client):
    """Test permanent Twilio error (no retry)."""
    from twilio.base.exceptions import TwilioRestException

    error = TwilioRestException(
        status=400,
        uri="/Messages",
        msg="Invalid phone number",
        code=21211
    )

    with patch.object(twilio_client.client.messages, "create", side_effect=error):
        result = await twilio_client.send_message(
            to_number="+31612345678",
            message="Test message",
            max_retries=3
        )

        assert result["status"] == "failed"
        # Should only attempt once (no retries for permanent errors)
        assert twilio_client.client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_send_message_twilio_error_retry(twilio_client, mock_twilio_message):
    """Test transient Twilio error with retry."""
    from twilio.base.exceptions import TwilioRestException

    error = TwilioRestException(
        status=500,
        uri="/Messages",
        msg="Internal server error",
        code=20500
    )

    # Fail twice, then succeed
    with patch.object(
        twilio_client.client.messages,
        "create",
        side_effect=[error, error, mock_twilio_message]
    ):
        with patch("time.sleep"):  # Skip actual sleep
            result = await twilio_client.send_message(
                to_number="+31612345678",
                message="Test message",
                max_retries=3,
                retry_delay=0.1
            )

            assert result["status"] == "sent"
            # Should have retried 3 times total
            assert twilio_client.client.messages.create.call_count == 3


@pytest.mark.asyncio
async def test_phone_number_normalization(twilio_client, mock_twilio_message):
    """Test various phone number formats are normalized correctly."""
    test_cases = [
        "+31612345678",           # E.164
        "31612345678",            # No +
        "31612345678@c.us",       # WAHA
        "+31 6 12 34 56 78",      # With spaces
        "+31-6-12-34-56-78",      # With hyphens
    ]

    for phone in test_cases:
        with patch.object(twilio_client.client.messages, "create", return_value=mock_twilio_message) as mock_create:
            # Reset Redis mock
            twilio_client.redis_client.get = Mock(return_value=None)

            result = await twilio_client.send_message(
                to_number=phone,
                message="Test message"
            )

            assert result["status"] == "sent"

            # Verify normalized phone was used
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["to"] == "whatsapp:+31612345678"


def test_rate_limit_window_cleanup(twilio_client):
    """Test old timestamps are removed from rate limit window."""
    import time

    # Add old timestamps
    twilio_client._message_timestamps = [
        time.time() - 10,  # 10 seconds ago (outside window)
        time.time() - 0.5,  # 0.5 seconds ago (inside window)
        time.time() - 0.2,  # 0.2 seconds ago (inside window)
    ]

    # Check rate limit (should clean up old timestamp)
    result = twilio_client._check_rate_limit()

    assert result is True
    assert len(twilio_client._message_timestamps) == 2  # Old timestamp removed
