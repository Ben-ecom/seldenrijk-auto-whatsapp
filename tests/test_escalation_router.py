"""
Unit tests for EscalationRouter.

Tests:
- Channel determination based on urgency
- Notification message preparation
- SLA response time calculation
"""
import pytest
from unittest.mock import Mock, patch
from app.agents.escalation_router import EscalationRouter


class TestEscalationRouter:
    """Test EscalationRouter logic."""

    def test_channel_determination_critical(self):
        """Test critical urgency uses both channels."""
        router = EscalationRouter()
        channels = router._determine_channels("critical")

        assert "whatsapp" in channels
        assert "email" in channels

    def test_channel_determination_high(self):
        """Test high urgency uses both channels."""
        router = EscalationRouter()
        channels = router._determine_channels("high")

        assert "whatsapp" in channels
        assert "email" in channels

    def test_channel_determination_medium(self):
        """Test medium urgency uses WhatsApp only."""
        router = EscalationRouter()
        channels = router._determine_channels("medium")

        assert "whatsapp" in channels
        assert "email" not in channels

    def test_channel_determination_low(self):
        """Test low urgency uses email only."""
        router = EscalationRouter()
        channels = router._determine_channels("low")

        assert "email" in channels
        assert "whatsapp" not in channels

    def test_sla_response_times(self):
        """Test SLA response time mapping."""
        router = EscalationRouter()

        assert router._get_response_sla("critical") == "30 minuten"
        assert router._get_response_sla("high") == "2 uur"
        assert router._get_response_sla("medium") == "4 uur"
        assert router._get_response_sla("low") == "24 uur"

    def test_notification_preparation(self):
        """Test notification message preparation."""
        router = EscalationRouter()

        customer_info = {
            "name": "Jan Jansen",
            "phone": "+31612345678",
            "car_interest": "Golf 8 diesel",
            "budget": 25000,
            "escalation_reason": "complex_financing"
        }

        notification = router._prepare_notification(
            escalation_type="finance_advisor",
            urgency="high",
            customer_info=customer_info,
            conversation_context="Klant vraagt over BKR financiering",
            chatwoot_url="https://chatwoot.example.com/conversations/123"
        )

        # Check WhatsApp message
        assert "ESCALATIE" in notification["whatsapp_message"]
        assert "Jan Jansen" in notification["whatsapp_message"]
        assert "+31612345678" in notification["whatsapp_message"]
        assert "Golf 8 diesel" in notification["whatsapp_message"]

        # Check email
        assert "Jan Jansen" in notification["email_subject"]
        assert "HIGH" in notification["email_subject"]
        assert "complex_financing" in notification["email_body"]
        assert "25000" in notification["email_body"]

        # Check CC for high urgency
        assert len(notification["cc_emails"]) > 0
        assert "manager@seldenrijk.nl" in notification["cc_emails"]

        # Check internal note
        assert "finance_advisor" in notification["internal_note"]

    def test_notification_no_cc_for_low_urgency(self):
        """Test no CC emails for low urgency."""
        router = EscalationRouter()

        customer_info = {
            "name": "Test",
            "phone": "+31600000000",
            "car_interest": "General",
            "escalation_reason": "info"
        }

        notification = router._prepare_notification(
            escalation_type="sales_manager",
            urgency="low",
            customer_info=customer_info,
            conversation_context="Simple question",
            chatwoot_url="https://example.com"
        )

        assert len(notification["cc_emails"]) == 0

    @patch('app.agents.escalation_router.requests.post')
    def test_send_whatsapp_success(self, mock_post):
        """Test successful WhatsApp sending."""
        mock_post.return_value.status_code = 200

        router = EscalationRouter()
        result = router._send_whatsapp(
            recipient="+31612345678",
            message="Test message"
        )

        assert result is True
        mock_post.assert_called_once()

    @patch('app.agents.escalation_router.requests.post')
    def test_send_whatsapp_failure(self, mock_post):
        """Test failed WhatsApp sending."""
        mock_post.return_value.status_code = 500

        router = EscalationRouter()
        result = router._send_whatsapp(
            recipient="+31612345678",
            message="Test message"
        )

        assert result is False

    def test_log_escalation_generates_id(self):
        """Test escalation logging generates unique ID."""
        router = EscalationRouter()

        id1 = router._log_escalation(
            escalation_type="manager",
            urgency="high",
            customer_phone="+31612345678",
            conversation_id="conv_123"
        )

        id2 = router._log_escalation(
            escalation_type="manager",
            urgency="high",
            customer_phone="+31612345678",
            conversation_id="conv_123"
        )

        assert id1.startswith("ESC_")
        assert id2.startswith("ESC_")
        assert id1 != id2  # Should be unique


# Integration test scenarios
class TestEscalationScenarios:
    """Test complete escalation scenarios."""

    def test_scenario_complex_financing(self):
        """Test complex financing escalation scenario."""
        router = EscalationRouter()

        customer_info = {
            "name": "Test User",
            "phone": "+31600000000",
            "car_interest": "BMW 3-serie",
            "budget": 30000,
            "escalation_reason": "complex_financing"
        }

        # Verify correct routing
        channels = router._determine_channels("medium")
        assert "whatsapp" in channels

        notification = router._prepare_notification(
            escalation_type="finance_advisor",
            urgency="medium",
            customer_info=customer_info,
            conversation_context="BKR vraag",
            chatwoot_url="https://example.com"
        )

        assert "finance_advisor" in notification["internal_note"]

    def test_scenario_complaint_critical(self):
        """Test complaint escalation with critical urgency."""
        router = EscalationRouter()

        customer_info = {
            "name": "Angry Customer",
            "phone": "+31600000000",
            "car_interest": "Unknown",
            "escalation_reason": "complaint"
        }

        # Critical should use both channels
        channels = router._determine_channels("critical")
        assert "whatsapp" in channels
        assert "email" in channels

        # Manager should be CC'd
        notification = router._prepare_notification(
            escalation_type="manager",
            urgency="critical",
            customer_info=customer_info,
            conversation_context="Klacht over service",
            chatwoot_url="https://example.com"
        )

        assert "manager@seldenrijk.nl" in notification["cc_emails"]
        assert "30 minuten" in notification["whatsapp_message"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
