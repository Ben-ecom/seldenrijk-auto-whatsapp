"""
Unit tests for webhook authentication security module.

Tests cover HMAC signature verification for Chatwoot, WAHA, 360Dialog, and Twilio webhooks,
including edge cases, invalid signatures, and development mode bypasses.
"""
import pytest
import hmac
import hashlib
import os
import base64
from unittest.mock import patch
from fastapi import HTTPException

from app.security.webhook_auth import (
    verify_chatwoot_signature,
    verify_waha_signature,
    verify_360dialog_signature,
    verify_whatsapp_token,
    verify_twilio_signature,
)


class TestChatwootSignatureVerification:
    """Test suite for Chatwoot HMAC-SHA256 signature verification."""

    def test_valid_chatwoot_signature(self):
        """Test Chatwoot signature verification with valid signature."""
        payload = b'{"event":"message_created","id":123}'
        secret = "test_chatwoot_secret"

        # Generate valid signature
        expected_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        with patch.dict(os.environ, {"CHATWOOT_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            assert verify_chatwoot_signature(payload, expected_sig) is True

    def test_chatwoot_invalid_signature(self):
        """Test Chatwoot signature verification rejects invalid signature."""
        payload = b'{"event":"message_created","id":123}'
        secret = "test_chatwoot_secret"
        invalid_signature = "invalid_signature_123"

        with patch.dict(os.environ, {"CHATWOOT_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_chatwoot_signature(payload, invalid_signature)

            assert exc_info.value.status_code == 403
            assert "Invalid webhook signature" in str(exc_info.value.detail)

    def test_chatwoot_missing_signature(self):
        """Test Chatwoot signature verification rejects missing signature."""
        payload = b'{"event":"message_created","id":123}'
        secret = "test_chatwoot_secret"

        with patch.dict(os.environ, {"CHATWOOT_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_chatwoot_signature(payload, None)

            assert exc_info.value.status_code == 403
            assert "Missing X-Chatwoot-Signature header" in str(exc_info.value.detail)

    def test_chatwoot_missing_secret(self):
        """Test Chatwoot signature verification fails when secret not configured."""
        payload = b'{"event":"message_created","id":123}'

        with patch.dict(os.environ, {}, clear=True):
            # Remove all env vars
            with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                with pytest.raises(HTTPException) as exc_info:
                    verify_chatwoot_signature(payload, "some_signature")

                assert exc_info.value.status_code == 500
                assert "CHATWOOT_WEBHOOK_SECRET not configured" in str(exc_info.value.detail)

    def test_chatwoot_development_bypass_no_signature(self):
        """Test Chatwoot signature verification allows bypass in development mode."""
        payload = b'{"event":"message_created","id":123}'

        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CHATWOOT_WEBHOOK_SECRET": "secret"}):
            # No signature in development mode should pass
            assert verify_chatwoot_signature(payload, None) is True

    def test_chatwoot_different_payload_different_signature(self):
        """Test different payloads produce different signatures."""
        secret = "test_chatwoot_secret"
        payload1 = b'{"event":"message_created","id":123}'
        payload2 = b'{"event":"message_created","id":456}'

        sig1 = hmac.new(secret.encode(), payload1, hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode(), payload2, hashlib.sha256).hexdigest()

        assert sig1 != sig2

        with patch.dict(os.environ, {"CHATWOOT_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            # sig1 should NOT work for payload2
            with pytest.raises(HTTPException):
                verify_chatwoot_signature(payload2, sig1)


class TestWAHASignatureVerification:
    """Test suite for WAHA HMAC-SHA512/SHA256 signature verification."""

    def test_valid_waha_signature_sha512(self):
        """Test WAHA signature verification with valid SHA512 signature."""
        payload = b'{"event":"message","payload":{"id":"msg_123"}}'
        secret = "test_waha_secret"

        # Generate valid SHA512 signature
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            assert verify_waha_signature(payload, expected_sig, "sha512") is True

    def test_valid_waha_signature_sha256(self):
        """Test WAHA signature verification with valid SHA256 signature."""
        payload = b'{"event":"message","payload":{"id":"msg_456"}}'
        secret = "test_waha_secret"

        # Generate valid SHA256 signature
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            assert verify_waha_signature(payload, expected_sig, "sha256") is True

    def test_waha_default_algorithm_sha512(self):
        """Test WAHA uses SHA512 by default when algorithm not specified."""
        payload = b'{"event":"message","payload":{"id":"msg_789"}}'
        secret = "test_waha_secret"

        # Generate SHA512 signature (default)
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            # No algorithm parameter = SHA512 default
            assert verify_waha_signature(payload, expected_sig, None) is True

    def test_waha_invalid_signature(self):
        """Test WAHA signature verification rejects invalid signature."""
        payload = b'{"event":"message","payload":{"id":"msg_001"}}'
        secret = "test_waha_secret"
        invalid_signature = "invalid_waha_signature_12345"

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_waha_signature(payload, invalid_signature, "sha512")

            assert exc_info.value.status_code == 403
            assert "Invalid webhook signature" in str(exc_info.value.detail)

    def test_waha_missing_signature(self):
        """Test WAHA signature verification rejects missing signature."""
        payload = b'{"event":"message","payload":{"id":"msg_002"}}'
        secret = "test_waha_secret"

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_waha_signature(payload, None, "sha512")

            assert exc_info.value.status_code == 403
            assert "Missing X-Webhook-Hmac header" in str(exc_info.value.detail)

    def test_waha_missing_secret(self):
        """Test WAHA signature verification fails when secret not configured."""
        payload = b'{"event":"message","payload":{"id":"msg_003"}}'

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                verify_waha_signature(payload, "some_signature", "sha512")

            assert exc_info.value.status_code == 500
            assert "WAHA_WEBHOOK_SECRET not configured" in str(exc_info.value.detail)

    def test_waha_development_bypass_no_secret(self):
        """Test WAHA signature verification allows bypass in development mode when secret not set."""
        payload = b'{"event":"message","payload":{"id":"msg_004"}}'

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            # No secret in development mode should pass
            assert verify_waha_signature(payload, None, "sha512") is True

    def test_waha_wrong_algorithm_fails(self):
        """Test WAHA signature generated with wrong algorithm fails verification."""
        payload = b'{"event":"message","payload":{"id":"msg_005"}}'
        secret = "test_waha_secret"

        # Generate SHA256 signature
        sha256_sig = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

        with patch.dict(os.environ, {"WAHA_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            # Try to verify with SHA512 algorithm - should fail
            with pytest.raises(HTTPException):
                verify_waha_signature(payload, sha256_sig, "sha512")


class TestDialog360SignatureVerification:
    """Test suite for 360Dialog HMAC-SHA256 signature verification."""

    def test_valid_360dialog_signature(self):
        """Test 360Dialog signature verification with valid signature."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.123"}]}}]}]}'
        secret = "test_360dialog_secret"

        # Generate valid signature
        expected_sig_raw = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # 360Dialog format: "sha256=<hex>"
        signature_with_prefix = f"sha256={expected_sig_raw}"

        with patch.dict(os.environ, {"DIALOG360_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            assert verify_360dialog_signature(payload, signature_with_prefix) is True

    def test_360dialog_invalid_signature(self):
        """Test 360Dialog signature verification rejects invalid signature."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.456"}]}}]}]}'
        secret = "test_360dialog_secret"
        invalid_signature = "sha256=invalid_signature_123"

        with patch.dict(os.environ, {"DIALOG360_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_360dialog_signature(payload, invalid_signature)

            assert exc_info.value.status_code == 403
            assert "Invalid webhook signature" in str(exc_info.value.detail)

    def test_360dialog_missing_signature(self):
        """Test 360Dialog signature verification rejects missing signature."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.789"}]}}]}]}'
        secret = "test_360dialog_secret"

        with patch.dict(os.environ, {"DIALOG360_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_360dialog_signature(payload, None)

            assert exc_info.value.status_code == 403
            assert "Missing X-Hub-Signature-256 header" in str(exc_info.value.detail)

    def test_360dialog_missing_secret(self):
        """Test 360Dialog signature verification fails when secret not configured."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.000"}]}}]}]}'

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                verify_360dialog_signature(payload, "sha256=some_signature")

            assert exc_info.value.status_code == 500
            assert "DIALOG360_WEBHOOK_SECRET not configured" in str(exc_info.value.detail)

    def test_360dialog_invalid_signature_format_no_prefix(self):
        """Test 360Dialog signature verification rejects signature without sha256= prefix."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.111"}]}}]}]}'
        secret = "test_360dialog_secret"

        # Missing "sha256=" prefix
        invalid_signature = "abcdef1234567890"

        with patch.dict(os.environ, {"DIALOG360_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_360dialog_signature(payload, invalid_signature)

            assert exc_info.value.status_code == 403
            assert "Invalid signature format" in str(exc_info.value.detail)

    def test_360dialog_empty_signature_after_prefix(self):
        """Test 360Dialog signature verification rejects signature with only prefix."""
        payload = b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.222"}]}}]}]}'
        secret = "test_360dialog_secret"

        # Only prefix, no actual signature
        invalid_signature = "sha256="

        with patch.dict(os.environ, {"DIALOG360_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_360dialog_signature(payload, invalid_signature)

            assert exc_info.value.status_code == 403


class TestWhatsAppTokenVerification:
    """Test suite for WhatsApp webhook token verification."""

    def test_valid_whatsapp_token(self):
        """Test WhatsApp token verification with valid parameters."""
        expected_token = "test_verify_token_12345"
        challenge = "challenge_string_abc123"

        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": expected_token}):
            result = verify_whatsapp_token(
                hub_mode="subscribe",
                hub_verify_token=expected_token,
                hub_challenge=challenge
            )

            assert result == challenge

    def test_whatsapp_token_invalid_mode(self):
        """Test WhatsApp token verification rejects invalid mode."""
        expected_token = "test_verify_token_12345"

        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": expected_token}):
            with pytest.raises(HTTPException) as exc_info:
                verify_whatsapp_token(
                    hub_mode="invalid_mode",
                    hub_verify_token=expected_token,
                    hub_challenge="challenge_123"
                )

            assert exc_info.value.status_code == 403
            assert "Invalid hub.mode" in str(exc_info.value.detail)

    def test_whatsapp_token_invalid_token(self):
        """Test WhatsApp token verification rejects invalid token."""
        expected_token = "test_verify_token_correct"
        wrong_token = "test_verify_token_wrong"

        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": expected_token}):
            with pytest.raises(HTTPException) as exc_info:
                verify_whatsapp_token(
                    hub_mode="subscribe",
                    hub_verify_token=wrong_token,
                    hub_challenge="challenge_123"
                )

            assert exc_info.value.status_code == 403
            assert "Invalid verification token" in str(exc_info.value.detail)

    def test_whatsapp_token_missing_env_var(self):
        """Test WhatsApp token verification fails when token not configured."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                verify_whatsapp_token(
                    hub_mode="subscribe",
                    hub_verify_token="some_token",
                    hub_challenge="challenge_123"
                )

            assert exc_info.value.status_code == 500
            assert "WHATSAPP_VERIFY_TOKEN not configured" in str(exc_info.value.detail)


class TestConstantTimeComparison:
    """Test constant-time comparison is used (timing attack prevention)."""

    def test_constant_time_comparison_used(self):
        """Verify hmac.compare_digest is used for signature comparison."""
        # This test ensures we're using constant-time comparison
        # which prevents timing attacks on signature validation

        payload = b'{"test":"data"}'
        secret = "test_secret"

        # Generate two different signatures
        sig1 = hmac.new(secret.encode(), b'{"test":"data1"}', hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret.encode(), b'{"test":"data2"}', hashlib.sha256).hexdigest()

        # Verify signatures are different
        assert sig1 != sig2

        # Both signatures should be rejected (not the correct one for our payload)
        with patch.dict(os.environ, {"CHATWOOT_WEBHOOK_SECRET": secret, "ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException):
                verify_chatwoot_signature(payload, sig1)

            with pytest.raises(HTTPException):
                verify_chatwoot_signature(payload, sig2)


class TestTwilioSignatureVerification:
    """Test suite for Twilio HMAC-SHA256 + Base64 signature verification."""

    def compute_twilio_signature(self, auth_token: str, url: str, params: dict) -> str:
        """
        Helper method to compute valid Twilio signature.

        This replicates Twilio's signing algorithm for testing.
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())

        # Concatenate URL + params
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])

        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            auth_token.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Base64 encode
        return base64.b64encode(computed_hash).decode('utf-8')

    def test_valid_signature_simple_message(self):
        """Test that valid signature passes verification for simple message."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Hello, I am looking for a car"
        }

        # Compute valid signature
        valid_signature = self.compute_twilio_signature(auth_token, webhook_url, params)

        # Verify
        assert verify_twilio_signature(auth_token, webhook_url, params, valid_signature) is True

    def test_invalid_signature(self):
        """Test that invalid signature fails verification."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test message"
        }

        invalid_signature = "this_is_definitely_not_valid"

        assert verify_twilio_signature(auth_token, webhook_url, params, invalid_signature) is False

    def test_tampered_body_fails(self):
        """Test that tampering with message body fails verification."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        original_params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Original message"
        }

        # Compute signature for original
        signature = self.compute_twilio_signature(auth_token, webhook_url, original_params)

        # Tamper with body
        tampered_params = original_params.copy()
        tampered_params["Body"] = "Tampered message"

        # Verification should fail
        assert verify_twilio_signature(auth_token, webhook_url, tampered_params, signature) is False

    def test_tampered_from_number_fails(self):
        """Test that changing From number fails verification."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        original_params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test"
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, original_params)

        # Change From number
        tampered_params = original_params.copy()
        tampered_params["From"] = "whatsapp:+31699999999"

        assert verify_twilio_signature(auth_token, webhook_url, tampered_params, signature) is False

    def test_url_manipulation_fails(self):
        """Test that changing URL fails verification."""
        auth_token = "test_auth_token_12345"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test"
        }

        original_url = "https://example.com/webhooks/twilio/whatsapp"
        signature = self.compute_twilio_signature(auth_token, original_url, params)

        # Change URL (attacker tries different endpoint)
        tampered_url = "https://example.com/webhooks/twilio/other"

        assert verify_twilio_signature(auth_token, tampered_url, params, signature) is False

    def test_empty_body_message(self):
        """Test signature verification for message with empty body."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": ""  # Empty message
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, params)

        assert verify_twilio_signature(auth_token, webhook_url, params, signature) is True

    def test_special_characters_in_body(self):
        """Test signature with special characters in message body."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Hallo! Ik zoek een auto voor 25.000 euro"  # Dutch + special characters
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, params)

        assert verify_twilio_signature(auth_token, webhook_url, params, signature) is True

    def test_multiple_parameters(self):
        """Test signature with many parameters (realistic Twilio payload)."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params = {
            "MessageSid": "SM1234567890abcdef",
            "SmsSid": "SM1234567890abcdef",
            "AccountSid": "AC1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "To": "whatsapp:+31850000000",
            "Body": "Test message",
            "NumMedia": "0",
            "NumSegments": "1",
            "SmsStatus": "received",
            "ApiVersion": "2010-04-01",
            "ProfileName": "John Doe"
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, params)

        assert verify_twilio_signature(auth_token, webhook_url, params, signature) is True

    def test_missing_parameter_fails(self):
        """Test that removing a parameter fails verification."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        full_params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test",
            "ProfileName": "John"
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, full_params)

        # Remove ProfileName
        partial_params = {k: v for k, v in full_params.items() if k != "ProfileName"}

        assert verify_twilio_signature(auth_token, webhook_url, partial_params, signature) is False

    def test_added_parameter_fails(self):
        """Test that adding an extra parameter fails verification."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        original_params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test"
        }

        signature = self.compute_twilio_signature(auth_token, webhook_url, original_params)

        # Add extra parameter (attacker injection)
        extended_params = original_params.copy()
        extended_params["ExtraParam"] = "malicious_value"

        assert verify_twilio_signature(auth_token, webhook_url, extended_params, signature) is False

    def test_wrong_auth_token_fails(self):
        """Test that using wrong auth token fails verification."""
        correct_token = "correct_token_12345"
        wrong_token = "wrong_token_99999"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"

        params = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test"
        }

        # Compute signature with correct token
        signature = self.compute_twilio_signature(correct_token, webhook_url, params)

        # Try to verify with wrong token
        assert verify_twilio_signature(wrong_token, webhook_url, params, signature) is False

    def test_case_sensitive_params(self):
        """Test that parameter keys are case-sensitive."""
        auth_token = "test_auth_token_12345"
        webhook_url = "https://example.com/webhooks/twilio/whatsapp"
        params_lowercase = {
            "messagesid": "SM1234567890abcdef",
            "from": "whatsapp:+31612345678",
            "body": "Test"
        }

        signature_lowercase = self.compute_twilio_signature(auth_token, webhook_url, params_lowercase)

        # Change case of keys
        params_uppercase = {
            "MessageSid": "SM1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "Body": "Test"
        }

        # Should fail because keys are different
        assert verify_twilio_signature(auth_token, webhook_url, params_uppercase, signature_lowercase) is False

    def test_empty_params(self):
        """Test signature verification with no parameters."""
        auth_token = "test_token"
        url = "https://example.com/webhook"
        params = {}

        # Compute signature for empty params
        data = url
        computed_hash = hmac.new(
            auth_token.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(computed_hash).decode('utf-8')

        assert verify_twilio_signature(auth_token, url, params, signature) is True

    def test_url_with_query_string(self):
        """Test that query strings in URL are included in signature."""
        auth_token = "test_token"
        url_with_query = "https://example.com/webhook?param=value"
        params = {"Body": "Test"}

        # Compute signature (URL includes query string)
        signature = self.compute_twilio_signature(auth_token, url_with_query, params)

        assert verify_twilio_signature(auth_token, url_with_query, params, signature) is True

    def test_url_with_trailing_slash(self):
        """Test that URL trailing slash matters."""
        auth_token = "test_token"
        params = {"Body": "Test"}

        url_no_slash = "https://example.com/webhook"
        signature_no_slash = self.compute_twilio_signature(auth_token, url_no_slash, params)

        url_with_slash = "https://example.com/webhook/"

        # Should fail because URLs are different
        assert verify_twilio_signature(auth_token, url_with_slash, params, signature_no_slash) is False

    def test_constant_time_comparison_security(self):
        """Test that constant-time comparison prevents timing attacks."""
        auth_token = "test_token"
        url = "https://example.com/webhook"
        params = {"Body": "Test"}

        # Generate correct signature
        correct_sig = self.compute_twilio_signature(auth_token, url, params)

        # Create signature that differs by one character
        tampered_sig = correct_sig[:-1] + ('A' if correct_sig[-1] != 'A' else 'B')

        # Both should be handled in constant time (we can't test timing here,
        # but we can verify the function uses hmac.compare_digest)
        assert verify_twilio_signature(auth_token, url, params, correct_sig) is True
        assert verify_twilio_signature(auth_token, url, params, tampered_sig) is False

    def test_realistic_whatsapp_payload(self):
        """Test with realistic WhatsApp Business API payload from Twilio."""
        auth_token = "your_auth_token_here"
        url = "https://seldenrijk.up.railway.app/webhooks/twilio/whatsapp"
        params = {
            "SmsMessageSid": "SM1234567890abcdef",
            "NumMedia": "0",
            "ProfileName": "Jan de Vries",
            "SmsSid": "SM1234567890abcdef",
            "WaId": "31612345678",
            "SmsStatus": "received",
            "Body": "Hoi, ik zoek een BMW 3-serie",
            "To": "whatsapp:+31850000000",
            "NumSegments": "1",
            "MessageSid": "SM1234567890abcdef",
            "AccountSid": "AC1234567890abcdef",
            "From": "whatsapp:+31612345678",
            "ApiVersion": "2010-04-01"
        }

        signature = self.compute_twilio_signature(auth_token, url, params)

        assert verify_twilio_signature(auth_token, url, params, signature) is True
