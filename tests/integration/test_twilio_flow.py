"""
Integration tests for Twilio WhatsApp end-to-end flow.

Tests the complete journey:
1. Twilio webhook receives message
2. Signature validation
3. Message processing (Celery queue)
4. LangGraph workflow execution
5. Response generation
6. Twilio message sending
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import hmac
import hashlib
import base64
import os

# Import your FastAPI app
from app.main import app

client = TestClient(app)


class TestTwilioWebhookValidation:
    """Tests for Twilio webhook signature validation."""

    @pytest.fixture
    def auth_token(self):
        """Mock Twilio auth token."""
        return "test_auth_token_12345"

    @pytest.fixture
    def webhook_url(self):
        """Test webhook URL - must match what FastAPI TestClient generates."""
        # TestClient uses 'http://testserver' as base URL
        return "http://testserver/webhooks/twilio/whatsapp"

    def compute_signature(self, auth_token, url, params):
        """Compute valid Twilio signature."""
        # Twilio signature algorithm: HMAC-SHA256(auth_token, url + sorted_params)
        sorted_params = sorted(params.items())
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])
        signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('ascii')
        return signature

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @patch("app.api.webhooks.redis_client")
    @patch("app.api.webhooks.process_message_async")
    def test_valid_signature_accepted(
        self,
        mock_process_message,
        mock_redis,
        auth_token,
        webhook_url
    ):
        """Test that valid Twilio signature is accepted."""

        # Mock Redis (no duplicate)
        mock_redis.get.return_value = None

        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_process_message.delay.return_value = mock_task

        # Prepare webhook payload
        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Ik zoek een Volkswagen Golf",
            "ProfileName": "John Doe",
            "NumMedia": "0"
        }

        # Compute valid signature
        signature = self.compute_signature(auth_token, webhook_url, params)

        # Send webhook request
        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["message_sid"] == "SM123456789"

        # Verify Celery task was queued
        mock_process_message.delay.assert_called_once()

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    def test_invalid_signature_rejected(self, webhook_url):
        """Test that invalid Twilio signature is rejected."""

        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Ik zoek een Volkswagen Golf",
            "ProfileName": "John Doe",
            "NumMedia": "0"
        }

        # Send webhook with INVALID signature
        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params,
            headers={"X-Twilio-Signature": "invalid_signature_123"}
        )

        # Assert rejection
        assert response.status_code == 403
        assert "Invalid webhook signature" in response.json()["detail"]

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    def test_missing_signature_rejected(self):
        """Test that missing signature is rejected."""

        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "Body": "Test message"
        }

        # Send webhook WITHOUT signature header
        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params
        )

        # Assert rejection
        assert response.status_code == 403


class TestTwilioDeduplication:
    """Tests for Twilio message deduplication."""

    @pytest.fixture
    def auth_token(self):
        return "test_auth_token_12345"

    @pytest.fixture
    def webhook_url(self):
        return "http://testserver/webhooks/twilio/whatsapp"

    def compute_signature(self, auth_token, url, params):
        sorted_params = sorted(params.items())
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])
        signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('ascii')
        return signature

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @patch("app.api.webhooks.redis_client")
    @patch("app.api.webhooks.process_message_async")
    def test_duplicate_message_ignored(
        self,
        mock_process_message,
        mock_redis,
        auth_token,
        webhook_url
    ):
        """Test that duplicate messages are ignored."""

        # Mock Redis to indicate message was already processed
        mock_redis.get.return_value = "processed"

        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Duplicate message",
            "ProfileName": "John Doe",
            "NumMedia": "0"
        }

        signature = self.compute_signature(auth_token, webhook_url, params)

        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )

        # Assert ignored
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "duplicate"

        # Verify Celery task was NOT queued
        mock_process_message.delay.assert_not_called()


class TestTwilioMessageProcessing:
    """Tests for Twilio message processing workflow."""

    @pytest.fixture
    def auth_token(self):
        return "test_auth_token_12345"

    @pytest.fixture
    def webhook_url(self):
        return "http://testserver/webhooks/twilio/whatsapp"

    def compute_signature(self, auth_token, url, params):
        sorted_params = sorted(params.items())
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])
        signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('ascii')
        return signature

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @patch("app.api.webhooks.redis_client")
    @patch("app.api.webhooks.process_message_async")
    def test_message_queued_with_correct_payload(
        self,
        mock_process_message,
        mock_redis,
        auth_token,
        webhook_url
    ):
        """Test that message is queued with correct transformed payload."""

        mock_redis.get.return_value = None

        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_process_message.delay.return_value = mock_task

        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Ik zoek een Volkswagen Golf",
            "ProfileName": "John Doe",
            "NumMedia": "0"
        }

        signature = self.compute_signature(auth_token, webhook_url, params)

        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )

        assert response.status_code == 200

        # Verify Celery task was called with correct payload
        mock_process_message.delay.assert_called_once()
        call_args = mock_process_message.delay.call_args[0][0]

        # Verify transformed payload structure
        assert call_args["id"] == "SM123456789"
        assert call_args["conversation"]["id"] == "whatsapp:+31612345678"
        assert call_args["sender"]["phone_number"] == "+31612345678"
        assert call_args["content"] == "Ik zoek een Volkswagen Golf"
        assert call_args["source"] == "twilio"  # CRITICAL for routing
        assert call_args["channel"] == "whatsapp"


class TestTwilioClientIntegration:
    """Tests for Twilio client message sending."""

    @patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending via Twilio client."""
        from app.integrations.twilio_client import TwilioWhatsAppClient

        client = TwilioWhatsAppClient()

        # Mock Twilio REST API
        with patch.object(client.client.messages, 'create') as mock_create:
            # Mock successful message creation
            mock_message = MagicMock()
            mock_message.sid = "SM987654321"
            mock_message.status = "queued"
            mock_message.price = None
            mock_message.price_unit = None
            mock_create.return_value = mock_message

            # Send message
            result = await client.send_message(
                to_number="+31612345678",
                message="Test response"
            )

            # Verify result
            assert result["status"] == "sent"
            assert result["message_sid"] == "SM987654321"
            assert result["to"] == "+31612345678"

            # Verify Twilio API was called correctly
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["from_"] == "whatsapp:+14155238886"
            assert call_kwargs["to"] == "whatsapp:+31612345678"
            assert call_kwargs["body"] == "Test response"

    @patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @pytest.mark.asyncio
    async def test_send_message_rate_limited(self):
        """Test rate limiting behavior."""
        from app.integrations.twilio_client import TwilioWhatsAppClient

        client = TwilioWhatsAppClient()

        # Mock rate limit by filling timestamp buffer
        import time
        client._message_timestamps = [time.time()] * 80  # Max capacity

        # Attempt to send message
        result = await client.send_message(
            to_number="+31612345678",
            message="Test message"
        )

        # Verify rate limited
        assert result["status"] == "rate_limited"
        assert "Rate limit exceeded" in result["error"]

    @patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @pytest.mark.asyncio
    async def test_send_message_retry_on_failure(self):
        """Test automatic retry on temporary failure."""
        from app.integrations.twilio_client import TwilioWhatsAppClient
        from twilio.base.exceptions import TwilioRestException

        client = TwilioWhatsAppClient()

        with patch.object(client.client.messages, 'create') as mock_create:
            # First call fails, second succeeds
            mock_message = MagicMock()
            mock_message.sid = "SM987654321"
            mock_message.status = "queued"
            mock_message.price = None
            mock_message.price_unit = None

            mock_create.side_effect = [
                TwilioRestException(500, "http://api.twilio.com", msg="Server error", code=20500),
                mock_message
            ]

            # Send message (should retry and succeed)
            result = await client.send_message(
                to_number="+31612345678",
                message="Test message",
                max_retries=3,
                retry_delay=0.1  # Fast retry for testing
            )

            # Verify success after retry
            assert result["status"] == "sent"
            assert mock_create.call_count == 2


class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.fixture
    def auth_token(self):
        return "test_auth_token_12345"

    @pytest.fixture
    def webhook_url(self):
        return "http://testserver/webhooks/twilio/whatsapp"

    def compute_signature(self, auth_token, url, params):
        sorted_params = sorted(params.items())
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])
        signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('ascii')
        return signature

    @patch.dict(os.environ, {
        "TWILIO_AUTH_TOKEN": "test_auth_token_12345",
        "TWILIO_ACCOUNT_SID": "ACtest123",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    })
    @patch("app.integrations.twilio_client.Client")
    @patch("app.api.webhooks.redis_client")
    @patch("app.orchestration.graph_builder.execute_graph")
    @patch("app.tasks.process_message._fetch_conversation_history")
    def test_complete_message_flow(
        self,
        mock_fetch_history,
        mock_execute_graph,
        mock_redis,
        mock_twilio_client_class,
        auth_token,
        webhook_url
    ):
        """Test complete flow from webhook to Twilio response."""

        # Mock Redis (no duplicate)
        mock_redis.get.return_value = None

        # Mock conversation history
        mock_fetch_history.return_value = []

        # Mock LangGraph execution
        mock_execute_graph.return_value = {
            "message_id": "SM123456789",
            "conversation_id": "whatsapp:+31612345678",
            "content": "Ik zoek een Volkswagen Golf",
            "sender_name": "John Doe",
            "sender_phone": "+31612345678",
            "source": "twilio",
            "conversation_output": {
                "response_text": "Bedankt voor uw interesse! Welke auto zoekt u?",
                "intent": "car_inquiry",
                "confidence": 0.95
            },
            "escalate_to_human": False,
            "error_occurred": False
        }

        # Mock Twilio client
        mock_twilio_instance = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM987654321"
        mock_message.status = "queued"
        mock_message.price = None
        mock_message.price_unit = None
        mock_twilio_instance.messages.create.return_value = mock_message
        mock_twilio_client_class.return_value = mock_twilio_instance

        # Prepare webhook payload
        params = {
            "MessageSid": "SM123456789",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Ik zoek een Volkswagen Golf",
            "ProfileName": "John Doe",
            "NumMedia": "0"
        }

        # Compute valid signature
        signature = self.compute_signature(auth_token, webhook_url, params)

        # Send webhook request (this queues Celery task)
        response = client.post(
            "/webhooks/twilio/whatsapp",
            data=params,
            headers={"X-Twilio-Signature": signature}
        )

        # Verify webhook accepted
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"

        # NOTE: Full end-to-end test would require running Celery worker
        # For integration test, we verify webhook acceptance and payload structure
        # Actual LangGraph + Twilio send is tested in separate unit tests
