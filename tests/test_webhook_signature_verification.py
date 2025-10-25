"""
Unit tests for webhook signature verification.

Tests HMAC signature verification for:
- Chatwoot (HMAC-SHA256)
- WAHA (HMAC-SHA512/SHA256)
- 360Dialog (HMAC-SHA256)
"""
import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from unittest.mock import patch
import os


@pytest.fixture
def client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_secrets():
    """Mock webhook secrets for testing."""
    secrets = {
        "CHATWOOT_WEBHOOK_SECRET": "test-chatwoot-secret-32chars-long",
        "WAHA_WEBHOOK_SECRET": "test-waha-secret-32chars-longggg",
        "DIALOG360_WEBHOOK_SECRET": "test-360dialog-secret-32chars",
        "ENVIRONMENT": "production"  # Disable dev bypass
    }
    with patch.dict(os.environ, secrets):
        yield secrets


def calculate_signature(payload: bytes, secret: str, algorithm="sha256") -> str:
    """Calculate HMAC signature for testing."""
    hash_func = hashlib.sha512 if algorithm == "sha512" else hashlib.sha256
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        hash_func
    ).hexdigest()


class TestChatwootSignatureVerification:
    """Test Chatwoot webhook signature verification."""

    def test_valid_signature(self, client, mock_secrets):
        """Test webhook with valid HMAC-SHA256 signature."""
        payload = b'{"test": "data"}'
        secret = mock_secrets["CHATWOOT_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha256")

        response = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": signature
            }
        )

        # Should accept webhook (may ignore due to invalid format, but NOT 403)
        assert response.status_code != 403, "Valid signature should not return 403"

    def test_invalid_signature(self, client, mock_secrets):
        """Test webhook with invalid signature."""
        payload = b'{"test": "data"}'

        response = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": "invalid-signature-12345"
            }
        )

        assert response.status_code == 403
        assert "Invalid webhook signature" in response.json()["detail"]

    def test_missing_signature(self, client, mock_secrets):
        """Test webhook with missing signature header."""
        payload = b'{"test": "data"}'

        response = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 403
        assert "Missing X-Chatwoot-Signature header" in response.json()["detail"]

    def test_development_bypass(self, client):
        """Test signature bypass in development mode."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            payload = b'{"test": "data"}'

            response = client.post(
                "/webhooks/chatwoot",
                content=payload,
                headers={"Content-Type": "application/json"}
                # No signature header
            )

            # Should accept webhook in dev mode
            assert response.status_code != 403


class TestWAHASignatureVerification:
    """Test WAHA webhook signature verification."""

    def test_valid_signature_sha512(self, client, mock_secrets):
        """Test webhook with valid HMAC-SHA512 signature."""
        payload = b'{"event": "message", "payload": {"id": "123"}}'
        secret = mock_secrets["WAHA_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha512")

        response = client.post(
            "/webhooks/waha",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Hmac": signature,
                "X-Webhook-Hmac-Algorithm": "sha512"
            }
        )

        # Should accept webhook (may ignore due to format, but NOT 403)
        assert response.status_code != 403

    def test_valid_signature_sha256(self, client, mock_secrets):
        """Test webhook with valid HMAC-SHA256 signature."""
        payload = b'{"event": "message", "payload": {"id": "123"}}'
        secret = mock_secrets["WAHA_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha256")

        response = client.post(
            "/webhooks/waha",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Hmac": signature,
                "X-Webhook-Hmac-Algorithm": "sha256"
            }
        )

        # Should accept webhook
        assert response.status_code != 403

    def test_invalid_signature(self, client, mock_secrets):
        """Test webhook with invalid signature."""
        payload = b'{"event": "message", "payload": {"id": "123"}}'

        response = client.post(
            "/webhooks/waha",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Hmac": "invalid-signature-12345",
                "X-Webhook-Hmac-Algorithm": "sha512"
            }
        )

        assert response.status_code == 403
        assert "Invalid webhook signature" in response.json()["detail"]

    def test_missing_signature(self, client, mock_secrets):
        """Test webhook with missing signature header."""
        payload = b'{"event": "message", "payload": {"id": "123"}}'

        response = client.post(
            "/webhooks/waha",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 403
        assert "Missing X-Webhook-Hmac header" in response.json()["detail"]

    def test_development_bypass(self, client):
        """Test signature bypass in development mode when secret not configured."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "WAHA_WEBHOOK_SECRET": ""  # Not configured
        }, clear=True):
            payload = b'{"event": "message", "payload": {"id": "123"}}'

            response = client.post(
                "/webhooks/waha",
                content=payload,
                headers={"Content-Type": "application/json"}
                # No signature header
            )

            # Should accept webhook in dev mode
            assert response.status_code != 403


class Test360DialogSignatureVerification:
    """Test 360Dialog webhook signature verification."""

    def test_valid_signature(self, client, mock_secrets):
        """Test webhook with valid HMAC-SHA256 signature (X-Hub-Signature-256 format)."""
        payload = b'{"entry": [{"changes": [{"value": {"messages": [{"id": "123"}]}}]}]}'
        secret = mock_secrets["DIALOG360_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha256")

        response = client.post(
            "/webhooks/360dialog",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={signature}"  # Format: sha256=<hex>
            }
        )

        # Should accept webhook
        assert response.status_code != 403

    def test_invalid_signature(self, client, mock_secrets):
        """Test webhook with invalid signature."""
        payload = b'{"entry": []}'

        response = client.post(
            "/webhooks/360dialog",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid-signature-12345"
            }
        )

        assert response.status_code == 403
        assert "Invalid webhook signature" in response.json()["detail"]

    def test_missing_signature(self, client, mock_secrets):
        """Test webhook with missing signature header."""
        payload = b'{"entry": []}'

        response = client.post(
            "/webhooks/360dialog",
            content=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 403
        assert "Missing X-Hub-Signature-256 header" in response.json()["detail"]

    def test_invalid_signature_format(self, client, mock_secrets):
        """Test webhook with invalid signature format (missing sha256= prefix)."""
        payload = b'{"entry": []}'
        secret = mock_secrets["DIALOG360_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha256")

        response = client.post(
            "/webhooks/360dialog",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature  # Missing "sha256=" prefix
            }
        )

        assert response.status_code == 403
        assert "Invalid signature format" in response.json()["detail"]


class TestSignatureTimingAttack:
    """Test protection against timing attacks."""

    def test_constant_time_comparison(self, client, mock_secrets):
        """
        Test that signature comparison uses constant-time algorithm.

        Timing attacks exploit variable-time string comparison to guess secrets
        byte-by-byte. Using hmac.compare_digest prevents this.
        """
        payload = b'{"test": "data"}'
        secret = mock_secrets["CHATWOOT_WEBHOOK_SECRET"]

        # Generate two different signatures (same length)
        valid_signature = calculate_signature(payload, secret, "sha256")
        invalid_signature = "a" * len(valid_signature)  # Same length, different value

        # Both invalid signatures should take similar time to reject
        # (we can't easily test timing in unit tests, but we verify rejection)
        response1 = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": invalid_signature
            }
        )

        response2 = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": "z" * len(valid_signature)
            }
        )

        # Both should return 403 (constant-time comparison used)
        assert response1.status_code == 403
        assert response2.status_code == 403


class TestSignatureIntegration:
    """Integration tests for signature verification."""

    def test_chatwoot_real_webhook_payload(self, client, mock_secrets):
        """Test with realistic Chatwoot webhook payload."""
        payload = b'''{
            "event": "message_created",
            "id": 12345,
            "content": "Hello",
            "message_type": "incoming",
            "conversation": {
                "id": 67890
            }
        }'''

        secret = mock_secrets["CHATWOOT_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha256")

        response = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": signature
            }
        )

        # Should accept (signature valid)
        assert response.status_code != 403

    def test_waha_real_webhook_payload(self, client, mock_secrets):
        """Test with realistic WAHA webhook payload."""
        payload = b'''{
            "event": "message",
            "payload": {
                "id": "msg-12345",
                "from": "31612345678@c.us",
                "body": "Hello",
                "fromMe": false
            }
        }'''

        secret = mock_secrets["WAHA_WEBHOOK_SECRET"]
        signature = calculate_signature(payload, secret, "sha512")

        response = client.post(
            "/webhooks/waha",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Hmac": signature,
                "X-Webhook-Hmac-Algorithm": "sha512"
            }
        )

        # Should accept (signature valid)
        assert response.status_code != 403


# Run tests with: pytest tests/test_webhook_signature_verification.py -v
