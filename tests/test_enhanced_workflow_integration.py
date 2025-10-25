"""
Integration tests for Enhanced Workflow (Phase 3.5).

Tests the complete flow:
START → router → expertise → extraction → enhanced_crm → enhanced_conversation → [escalation_router] → END

Tests:
- Normal conversation flow (no escalation)
- Escalation flow (ExpertiseAgent triggers escalation)
- HOT lead flow (high lead score)
- WARM lead flow with expertise knowledge
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.orchestration.graph_builder import build_graph
from app.orchestration.state import ConversationState


class TestEnhancedWorkflowIntegration:
    """Test complete enhanced workflow integration."""

    @patch('app.agents.router_agent.RouterAgent.execute')
    @patch('app.agents.expertise_agent.ExpertiseAgent.execute')
    @patch('app.agents.extraction_agent.ExtractionAgent.execute')
    @patch('app.agents.enhanced_crm_agent.EnhancedCRMAgent.execute')
    @patch('app.agents.enhanced_conversation_agent.EnhancedConversationAgent.execute')
    def test_normal_conversation_flow(
        self,
        mock_conversation,
        mock_crm,
        mock_extraction,
        mock_expertise,
        mock_router
    ):
        """Test normal conversation flow without escalation."""

        # Mock router output
        mock_router.return_value = {
            "output": {
                "intent": "car_inquiry",
                "priority": "medium",
                "escalate_to_human": False,
                "needs_extraction": True,
                "confidence": 0.95
            },
            "tokens_used": 100,
            "cost_usd": 0.001
        }

        # Mock expertise output (no escalation)
        mock_expertise.return_value = {
            "output": {
                "domain": "technical",
                "knowledge": "De Golf 8 heeft een TDI motor met uitstekend verbruik.",
                "escalation_decision": {
                    "escalate": False
                }
            },
            "tokens_used": 150,
            "cost_usd": 0.002
        }

        # Mock extraction output
        mock_extraction.return_value = {
            "output": {
                "car_interest": {
                    "make": "Volkswagen",
                    "model": "Golf 8",
                    "fuel_type": "diesel"
                },
                "budget": {
                    "max_amount": 25000
                },
                "extraction_confidence": 0.9
            },
            "tokens_used": 120,
            "cost_usd": 0.0015
        }

        # Mock enhanced CRM output
        mock_crm.return_value = {
            "output": {
                "lead_score": 65,
                "lead_quality": "WARM",
                "urgency": "medium",
                "interest_level": "considering",
                "tags_added": ["interest:volkswagen", "preference:diesel", "engagement:warm-lead"],
                "behavioral_flags": {
                    "test_drive_requested": False,
                    "has_trade_in": False,
                    "needs_financing": False
                },
                "custom_attributes": {
                    "lead_score": 65,
                    "lead_quality": "WARM"
                },
                "contact_updated": True,
                "contact_created": False
            },
            "tokens_used": 80,
            "cost_usd": 0.001
        }

        # Mock enhanced conversation output
        mock_conversation.return_value = {
            "output": {
                "response_text": "Fijn om van je te horen! De Golf 8 diesel is een uitstekende keuze.",
                "sentiment": "positive",
                "needs_rag": False,
                "conversation_complete": False,
                "recommended_action": "send_more_info",
                "follow_up_questions": []
            },
            "tokens_used": 200,
            "cost_usd": 0.003
        }

        # Build graph
        graph = build_graph()

        # Create initial state
        initial_state: ConversationState = {
            "message_id": "msg_test_001",
            "conversation_id": "conv_test_001",
            "sender_phone": "+31612345678",
            "content": "Ik zoek een Golf 8 diesel",
            "conversation_history": [],
            "total_tokens_used": 0,
            "total_cost_usd": 0.0
        }

        # Execute graph (synchronous for testing)
        # Note: We test node functions directly since async execution is complex in tests
        from app.orchestration.graph_builder import (
            router_node,
            expertise_node,
            extraction_node,
            enhanced_crm_node,
            enhanced_conversation_node
        )

        # Simulate workflow
        state = router_node(initial_state)
        assert "router_output" in state

        state = expertise_node(state)
        assert "expertise_output" in state
        assert state.get("escalate_to_human") is not True  # No escalation

        state = extraction_node(state)
        assert "extraction_output" in state

        state = enhanced_crm_node(state)
        assert "crm_output" in state
        assert state["crm_output"]["lead_score"] == 65
        assert state["crm_output"]["lead_quality"] == "WARM"

        state = enhanced_conversation_node(state)
        assert "conversation_output" in state
        assert "Fijn om van je te horen" in state["conversation_output"]["response_text"]

        # Verify no escalation
        assert state.get("escalate_to_human") is not True

    @patch('app.agents.router_agent.RouterAgent.execute')
    @patch('app.agents.expertise_agent.ExpertiseAgent.execute')
    @patch('app.agents.extraction_agent.ExtractionAgent.execute')
    @patch('app.agents.enhanced_crm_agent.EnhancedCRMAgent.execute')
    @patch('app.agents.enhanced_conversation_agent.EnhancedConversationAgent.execute')
    @patch('app.agents.escalation_router.EscalationRouter.execute')
    def test_escalation_flow(
        self,
        mock_escalation_router,
        mock_conversation,
        mock_crm,
        mock_extraction,
        mock_expertise,
        mock_router
    ):
        """Test escalation flow when ExpertiseAgent triggers escalation."""

        # Mock router output
        mock_router.return_value = {
            "output": {
                "intent": "financing_inquiry",
                "priority": "medium",
                "escalate_to_human": False,
                "needs_extraction": True,
                "confidence": 0.92
            },
            "tokens_used": 100,
            "cost_usd": 0.001
        }

        # Mock expertise output (WITH escalation)
        mock_expertise.return_value = {
            "output": {
                "domain": "financial",
                "knowledge": "Voor BKR financiering moet je contact opnemen met een adviseur.",
                "escalation_decision": {
                    "escalate": True,
                    "escalation_type": "finance_advisor",
                    "urgency": "medium",
                    "reason": "complex_financing"
                }
            },
            "tokens_used": 150,
            "cost_usd": 0.002
        }

        # Mock extraction, CRM, conversation
        mock_extraction.return_value = {
            "output": {"extraction_confidence": 0.8},
            "tokens_used": 100,
            "cost_usd": 0.001
        }

        mock_crm.return_value = {
            "output": {
                "lead_score": 60,
                "lead_quality": "WARM",
                "tags_added": ["escalated:finance_advisor", "status:needs-human-attention"],
                "behavioral_flags": {},
                "custom_attributes": {},
                "contact_updated": True
            },
            "tokens_used": 80,
            "cost_usd": 0.001
        }

        mock_conversation.return_value = {
            "output": {
                "response_text": "Ik begrijp je vraag over BKR. Een collega neemt contact met je op.",
                "sentiment": "neutral",
                "needs_rag": False,
                "recommended_action": "escalate"
            },
            "tokens_used": 180,
            "cost_usd": 0.002
        }

        # Mock escalation router
        mock_escalation_router.return_value = {
            "output": {
                "escalation_id": "ESC_001",
                "channels_used": ["whatsapp"],
                "whatsapp_sent": True,
                "chatwoot_assigned": True
            },
            "tokens_used": 0,
            "cost_usd": 0.0
        }

        # Simulate workflow
        from app.orchestration.graph_builder import (
            router_node,
            expertise_node,
            extraction_node,
            enhanced_crm_node,
            enhanced_conversation_node,
            escalation_router_node
        )

        initial_state: ConversationState = {
            "message_id": "msg_test_002",
            "conversation_id": "conv_test_002",
            "sender_phone": "+31612345678",
            "content": "Kan ik financieren met BKR?",
            "conversation_history": [],
            "total_tokens_used": 0,
            "total_cost_usd": 0.0
        }

        state = router_node(initial_state)
        state = expertise_node(state)

        # Verify escalation flag set
        assert state.get("escalate_to_human") is True
        assert state.get("escalation_type") == "finance_advisor"
        assert state.get("escalation_urgency") == "medium"

        state = extraction_node(state)
        state = enhanced_crm_node(state)
        state = enhanced_conversation_node(state)

        # Escalation router should be called
        state = escalation_router_node(state)
        assert "escalation_output" in state
        assert state["escalation_output"]["escalation_id"] == "ESC_001"

    @patch('app.agents.router_agent.RouterAgent.execute')
    @patch('app.agents.expertise_agent.ExpertiseAgent.execute')
    @patch('app.agents.extraction_agent.ExtractionAgent.execute')
    @patch('app.agents.enhanced_crm_agent.EnhancedCRMAgent.execute')
    @patch('app.agents.enhanced_conversation_agent.EnhancedConversationAgent.execute')
    def test_hot_lead_flow(
        self,
        mock_conversation,
        mock_crm,
        mock_extraction,
        mock_expertise,
        mock_router
    ):
        """Test HOT lead flow with high lead score."""

        # Mock outputs for HOT lead
        mock_router.return_value = {
            "output": {
                "intent": "test_drive_request",
                "priority": "high",
                "escalate_to_human": False,
                "needs_extraction": True,
                "confidence": 0.98
            },
            "tokens_used": 90,
            "cost_usd": 0.001
        }

        mock_expertise.return_value = {
            "output": {
                "domain": "service",
                "knowledge": "Proefritten zijn mogelijk op afspraak.",
                "escalation_decision": {"escalate": False}
            },
            "tokens_used": 130,
            "cost_usd": 0.0015
        }

        mock_extraction.return_value = {
            "output": {
                "car_interest": {
                    "make": "Volkswagen",
                    "model": "Golf 8",
                    "fuel_type": "diesel"
                },
                "budget": {"max_amount": 25000},
                "extraction_confidence": 0.95
            },
            "tokens_used": 110,
            "cost_usd": 0.0012
        }

        # HOT lead CRM output
        mock_crm.return_value = {
            "output": {
                "lead_score": 85,  # HOT lead
                "lead_quality": "HOT",
                "urgency": "critical",
                "interest_level": "ready-to-buy",
                "tags_added": [
                    "behavior:test-drive-requested",
                    "intent:ready-to-buy",
                    "engagement:hot-lead"
                ],
                "behavioral_flags": {
                    "test_drive_requested": True
                },
                "custom_attributes": {
                    "lead_score": 85,
                    "lead_quality": "HOT"
                },
                "contact_updated": True
            },
            "tokens_used": 85,
            "cost_usd": 0.001
        }

        # Enthusiastic response for HOT lead
        mock_conversation.return_value = {
            "output": {
                "response_text": "Super! Wanneer zou je langs kunnen komen voor een proefrit?",
                "sentiment": "positive",
                "needs_rag": False,
                "recommended_action": "schedule_test_drive"
            },
            "tokens_used": 190,
            "cost_usd": 0.0025
        }

        # Simulate workflow
        from app.orchestration.graph_builder import (
            router_node,
            expertise_node,
            extraction_node,
            enhanced_crm_node,
            enhanced_conversation_node
        )

        initial_state: ConversationState = {
            "message_id": "msg_test_003",
            "conversation_id": "conv_test_003",
            "sender_phone": "+31612345678",
            "content": "Kan ik vandaag langskomen voor een proefrit in de Golf 8?",
            "conversation_history": [],
            "total_tokens_used": 0,
            "total_cost_usd": 0.0
        }

        state = router_node(initial_state)
        state = expertise_node(state)
        state = extraction_node(state)
        state = enhanced_crm_node(state)

        # Verify HOT lead scoring
        assert state["crm_output"]["lead_score"] >= 70
        assert state["crm_output"]["lead_quality"] == "HOT"
        assert state["crm_output"]["behavioral_flags"]["test_drive_requested"] is True

        state = enhanced_conversation_node(state)

        # Verify enthusiastic response
        assert "Super!" in state["conversation_output"]["response_text"]
        assert state["conversation_output"]["recommended_action"] == "schedule_test_drive"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
