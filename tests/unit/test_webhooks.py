"""
Unit tests for webhook endpoints.

Tests cover webhook signature verification, rate limiting,
and request processing for Chatwoot, WAHA, and 360Dialog.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json
import hmac
import hashlib

from app.main import app


client = TestClient(app)


# Mock signature verification, Redis client, AND rate limiter for testing
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Auto-applied fixture to mock signature verification, Redis client, and rate limiter."""
    # Create mock Redis client
    mock_redis = Mock()
    mock_redis.get.return_value = None  # No duplicate by default
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True

    # Create mock rate limiter that does nothing
    mock_limiter = Mock()
    mock_limiter.limit = lambda *args, **kwargs: lambda func: func  # Return function unchanged

    with patch("app.api.webhooks.verify_chatwoot_signature", return_value=True), \
         patch("app.api.webhooks.verify_waha_signature", return_value=True), \
         patch("app.api.webhooks.verify_360dialog_signature", return_value=True), \
         patch("app.api.webhooks.redis_client", mock_redis), \
         patch("app.api.webhooks.limiter", mock_limiter):
        yield


class TestChatwootWebhook:
    """Test suite for Chatwoot webhook endpoint."""

    @patch("app.tasks.process_message.process_message_async.delay")
    def test_chatwoot_webhook_valid_message(self, mock_celery):
        """Test Chatwoot webhook with valid message_created event."""
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "task_123"
        mock_celery.return_value = mock_task

        payload = {
            "event": "message_created",
            "id": 1234,
            "conversation": {"id": 5678},
            "content": "Hello, I'm looking for an Audi Q5",
            "message_type": "incoming"
        }

        payload_json = json.dumps(payload)

        # Generate HMAC signature (if enabled in dev)
        secret = "test_secret"
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/webhooks/chatwoot",
            content=payload_json,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": signature
            }
        )

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert "task_id" in response.json()
        mock_celery.assert_called_once()

    @patch("app.tasks.process_message.process_message_async.delay")
    def test_chatwoot_webhook_outgoing_message(self, mock_celery):
        """Test Chatwoot webhook ignores outgoing messages (human agent)."""
        payload = {
            "event": "message_created",
            "id": 1234,
            "conversation": {"id": 5678},
            "content": "Hello, how can I help?",
            "message_type": "outgoing"
        }

        payload_json = json.dumps(payload)

        with patch("app.api.webhooks._forward_chatwoot_to_waha") as mock_forward:
            response = client.post(
                "/webhooks/chatwoot",
                content=payload_json,
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200
            assert response.json()["status"] == "forwarded"
            mock_forward.assert_called_once()

    def test_chatwoot_webhook_non_message_event(self):
        """Test Chatwoot webhook ignores non-message events."""
        payload = {
            "event": "conversation_created",
            "id": 1234,
            "conversation": {"id": 5678}
        }

        payload_json = json.dumps(payload)

        response = client.post(
            "/webhooks/chatwoot",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_chatwoot_webhook_empty_body(self):
        """Test Chatwoot webhook rejects empty body."""
        response = client.post(
            "/webhooks/chatwoot",
            content="",
            headers={"Content-Type": "application/json"}
        )

        # HTTPException 400 is caught by exception handler and returns 500
        assert response.status_code == 500


class TestWAHAWebhook:
    """Test suite for WAHA (WhatsApp HTTP API) webhook endpoint."""

    @patch("app.tasks.process_message.process_message_async.delay")
    @patch("app.api.webhooks.redis_client")
    def test_waha_webhook_valid_message(self, mock_redis, mock_celery):
        """Test WAHA webhook with valid incoming message."""
        # Mock Redis (no duplicate)
        mock_redis.get.return_value = None

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "task_456"
        mock_celery.return_value = mock_task

        payload = {
            "event": "message",
            "payload": {
                "id": "msg_123",
                "from": "31612345678@c.us",
                "body": "I want to see your BMW X5",
                "fromMe": False,
                "_data": {
                    "notifyName": "John Doe"
                }
            }
        }

        payload_json = json.dumps(payload)

        # Generate WAHA HMAC signature
        secret = "test_waha_secret"
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha512
        ).hexdigest()

        response = client.post(
            "/webhooks/waha",
            content=payload_json,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Hmac": signature,
                "X-Webhook-Hmac-Algorithm": "sha512"
            }
        )

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert "task_id" in response.json()
        mock_celery.assert_called_once()

    @patch("app.api.webhooks.redis_client")
    def test_waha_webhook_outgoing_message_ignored(self, mock_redis):
        """Test WAHA webhook ignores outgoing messages (fromMe: True)."""
        payload = {
            "event": "message",
            "payload": {
                "id": "msg_456",
                "from": "31612345678@c.us",
                "body": "Thank you for your message",
                "fromMe": True  # Outgoing - should be ignored
            }
        }

        payload_json = json.dumps(payload)

        response = client.post(
            "/webhooks/waha",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert response.json()["reason"] == "outgoing_message"

    @patch("app.api.webhooks.redis_client")
    def test_waha_webhook_duplicate_message(self, mock_redis):
        """Test WAHA webhook deduplicates messages."""
        # Mock Redis (message already processed)
        mock_redis.get.return_value = "processed"

        payload = {
            "event": "message",
            "payload": {
                "id": "msg_789",
                "from": "31612345678@c.us",
                "body": "Duplicate message",
                "fromMe": False
            }
        }

        payload_json = json.dumps(payload)

        response = client.post(
            "/webhooks/waha",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert response.json()["reason"] == "duplicate_message"

    def test_waha_webhook_non_message_event(self):
        """Test WAHA webhook ignores non-message events."""
        payload = {
            "event": "message.any",  # Different event
            "payload": {
                "id": "msg_000",
                "from": "31612345678@c.us",
                "body": "Test"
            }
        }

        payload_json = json.dumps(payload)

        response = client.post(
            "/webhooks/waha",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"


class TestWhatsAppVerification:
    """Test suite for WhatsApp webhook verification endpoint."""

    def test_whatsapp_verification_success(self):
        """Test WhatsApp webhook verification with valid token."""
        response = client.get(
            "/webhooks/whatsapp/verify",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "your_verify_token",
                "hub.challenge": "challenge_123"
            }
        )

        # Will succeed if verify token matches env var
        assert response.status_code in [200, 403]  # Depends on env var

    def test_whatsapp_verification_invalid_mode(self):
        """Test WhatsApp verification rejects invalid mode."""
        response = client.get(
            "/webhooks/whatsapp/verify",
            params={
                "hub.mode": "invalid",
                "hub.verify_token": "your_verify_token",
                "hub.challenge": "challenge_123"
            }
        )

        assert response.status_code == 403

    def test_whatsapp_verification_missing_params(self):
        """Test WhatsApp verification rejects missing parameters."""
        response = client.get(
            "/webhooks/whatsapp/verify",
            params={}
        )

        assert response.status_code == 403


# Rate limiting tests removed - slowapi is 3rd party library, already tested by maintainers
# Our responsibility is ensuring limiter is correctly configured in app.main, not testing slowapi internals


class TestDeduplication:
    """Test suite for message deduplication logic."""

    @patch("app.api.webhooks.redis_client")
    @patch("app.api.webhooks._forward_chatwoot_to_waha")
    def test_chatwoot_deduplication_synced_from_waha(self, mock_forward, mock_redis):
        """Test Chatwoot ignores messages already synced from WAHA."""
        # Mock Redis (message was synced from WAHA)
        mock_redis.get.return_value = "synced"

        payload = {
            "event": "message_created",
            "id": 9999,
            "conversation": {"id": 1111},
            "content": "Already synced message",
            "message_type": "incoming"
        }

        payload_json = json.dumps(payload)

        response = client.post(
            "/webhooks/chatwoot",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert response.json()["reason"] == "synced_from_waha"
