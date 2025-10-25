"""
Test webhook security implementation.
Tests signature verification and rate limiting.
"""
import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def generate_chatwoot_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for Chatwoot webhook."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def generate_360dialog_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for 360Dialog webhook."""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

class TestWebhookSecurity:
    """Test webhook security features."""

    def test_chatwoot_webhook_without_signature(self, monkeypatch):
        """Test Chatwoot webhook rejects requests without signature."""
        monkeypatch.setenv("CHATWOOT_WEBHOOK_SECRET", "test-secret")

        response = client.post(
            "/webhooks/chatwoot",
            json={"event": "message_created"}
        )

        assert response.status_code == 403
        assert "Missing X-Chatwoot-Signature header" in response.text

    def test_chatwoot_webhook_with_invalid_signature(self, monkeypatch):
        """Test Chatwoot webhook rejects invalid signatures."""
        monkeypatch.setenv("CHATWOOT_WEBHOOK_SECRET", "test-secret")

        response = client.post(
            "/webhooks/chatwoot",
            json={"event": "message_created"},
            headers={"X-Chatwoot-Signature": "invalid-signature"}
        )

        assert response.status_code == 403
        assert "Invalid webhook signature" in response.text

    def test_chatwoot_webhook_with_valid_signature(self, monkeypatch):
        """Test Chatwoot webhook accepts valid signatures."""
        secret = "test-secret"
        payload = '{"event":"message_created","message_type":"incoming","content":"test"}'

        monkeypatch.setenv("CHATWOOT_WEBHOOK_SECRET", secret)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        signature = generate_chatwoot_signature(payload, secret)

        response = client.post(
            "/webhooks/chatwoot",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": signature
            }
        )

        # Should accept (even if processing fails due to missing setup)
        assert response.status_code in [200, 500]  # 500 is ok if celery not running

    def test_360dialog_webhook_without_signature(self, monkeypatch):
        """Test 360Dialog webhook rejects requests without signature."""
        monkeypatch.setenv("DIALOG360_WEBHOOK_SECRET", "test-secret")

        response = client.post(
            "/webhooks/360dialog",
            json={"entry": []}
        )

        assert response.status_code == 403
        assert "Missing X-Hub-Signature-256 header" in response.text

    def test_360dialog_webhook_with_valid_signature(self, monkeypatch):
        """Test 360Dialog webhook accepts valid signatures."""
        secret = "test-secret"
        payload = '{"entry":[]}'

        monkeypatch.setenv("DIALOG360_WEBHOOK_SECRET", secret)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        signature = generate_360dialog_signature(payload, secret)

        response = client.post(
            "/webhooks/360dialog",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature
            }
        )

        # Should accept (even if processing fails)
        assert response.status_code in [200, 500]

    def test_whatsapp_verification_success(self, monkeypatch):
        """Test WhatsApp webhook verification endpoint."""
        monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")

        response = client.get(
            "/webhooks/whatsapp/verify",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge-string-12345"
            }
        )

        assert response.status_code == 200
        assert response.text == '"challenge-string-12345"'

    def test_whatsapp_verification_invalid_token(self, monkeypatch):
        """Test WhatsApp verification rejects invalid tokens."""
        monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")

        response = client.get(
            "/webhooks/whatsapp/verify",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-string-12345"
            }
        )

        assert response.status_code == 403

    @pytest.mark.skip(reason="Rate limiting requires Redis")
    def test_rate_limiting(self, monkeypatch):
        """Test rate limiting blocks excessive requests."""
        secret = "test-secret"
        monkeypatch.setenv("CHATWOOT_WEBHOOK_SECRET", secret)

        # Send 101 requests (limit is 100/min)
        for i in range(101):
            payload = f'{{"event":"message_created","id":{i}}}'
            signature = generate_chatwoot_signature(payload, secret)

            response = client.post(
                "/webhooks/chatwoot",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Chatwoot-Signature": signature
                }
            )

            if i < 100:
                assert response.status_code in [200, 500]
            else:
                # 101st request should be rate limited
                assert response.status_code == 429
                assert "Rate limit exceeded" in response.text

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self):
        """Test basic health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "WhatsApp Recruitment Platform" in response.json()["name"]

    def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
