"""
Unit tests for Enhanced Conversation Agent.

Tests:
- Humanization patterns (Dutch conversational openers)
- Lead quality tone adjustment
- ExpertiseAgent knowledge integration
- Escalation handling
- Action recommendations
"""
import pytest
from app.agents.enhanced_conversation_agent import (
    EnhancedConversationAgent,
    HumanizationEngine
)


class TestHumanizationEngine:
    """Test humanization patterns."""

    def test_hot_lead_opener(self):
        """Test HOT lead gets enthusiastic opener."""
        engine = HumanizationEngine()

        opener = engine.get_opener("HOT", [])

        # Should be from HOT_LEAD_OPENERS
        assert opener in ["Super! ", "Wat fijn! ", "Perfect! ", "Geweldig! "]

    def test_warm_lead_opener(self):
        """Test WARM lead gets friendly opener."""
        engine = HumanizationEngine()

        opener = engine.get_opener("WARM", [])

        # Should be from WARM_LEAD_OPENERS
        warm_openers = [
            "Dank je wel voor je bericht! ",
            "Leuk dat je contact opneemt! ",
            "Fijn om van je te horen! ",
            "Bedankt voor je interesse! "
        ]
        assert opener in warm_openers

    def test_cold_lead_opener(self):
        """Test COLD lead gets simple opener."""
        engine = HumanizationEngine()

        opener = engine.get_opener("COLD", [])

        # Should be from COLD_LEAD_OPENERS
        assert opener in ["Hallo! ", "Dag! ", "Hoi! "]

    def test_opener_variety(self):
        """Test that openers vary (no repeats if possible)."""
        engine = HumanizationEngine()

        # Get 3 openers
        used = []
        opener1 = engine.get_opener("HOT", used)
        used.append(opener1)

        opener2 = engine.get_opener("HOT", used)
        used.append(opener2)

        opener3 = engine.get_opener("HOT", used)

        # Should get different openers (variety)
        assert opener1 != opener2 or opener2 != opener3

    def test_transition_phrases(self):
        """Test natural transition phrases."""
        engine = HumanizationEngine()

        transition = engine.get_transition()

        transitions = [
            "Even kijken...",
            "Laat me even checken...",
            "Moment, ik zoek het voor je op...",
            "Ik pak even de informatie voor je erbij..."
        ]
        assert transition in transitions

    def test_closing_phrases(self):
        """Test natural closing phrases."""
        engine = HumanizationEngine()

        closer = engine.get_closer()

        closers = [
            "Laat het me weten als je vragen hebt!",
            "Hoor ik graag van je!",
            "Ik hoor het graag!",
            "Laat maar weten!",
            "Ik help je graag verder!"
        ]
        assert closer in closers


class TestEnhancedConversationAgent:
    """Test Enhanced Conversation Agent."""

    def test_sentiment_detection_dutch(self):
        """Test Dutch sentiment detection."""
        agent = EnhancedConversationAgent()

        # Positive
        positive_text = "Super! Dat klinkt geweldig!"
        assert agent._detect_sentiment_dutch(positive_text) == "positive"

        # Negative
        negative_text = "Helaas is deze auto niet beschikbaar, jammer."
        assert agent._detect_sentiment_dutch(negative_text) == "negative"

        # Neutral
        neutral_text = "De auto heeft een 2.0 TDI motor."
        assert agent._detect_sentiment_dutch(neutral_text) == "neutral"

    def test_action_recommendation_escalation(self):
        """Test action recommendation when escalated."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Test message",
            "expertise_output": {
                "escalation_decision": {
                    "escalate": True,
                    "escalation_type": "finance_advisor"
                }
            }
        }

        action = agent._recommend_action(state, "response text")

        assert action == "escalate"

    def test_action_recommendation_test_drive(self):
        """Test action recommendation for test drive request."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Kan ik een proefrit maken?",
            "crm_output": {
                "lead_quality": "WARM",
                "behavioral_flags": {
                    "test_drive_requested": True
                }
            }
        }

        action = agent._recommend_action(state, "response text")

        assert action == "schedule_test_drive"

    def test_action_recommendation_hot_lead(self):
        """Test action recommendation for HOT lead."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Test message",
            "crm_output": {
                "lead_quality": "HOT",
                "behavioral_flags": {
                    "test_drive_requested": False
                }
            }
        }

        action = agent._recommend_action(state, "response text")

        assert action == "schedule_test_drive"

    def test_action_recommendation_warm_lead(self):
        """Test action recommendation for WARM lead."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Test message",
            "crm_output": {
                "lead_quality": "WARM",
                "behavioral_flags": {
                    "test_drive_requested": False
                }
            }
        }

        action = agent._recommend_action(state, "response text")

        assert action == "send_more_info"

    def test_action_recommendation_cold_lead(self):
        """Test action recommendation for COLD lead."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Test message",
            "crm_output": {
                "lead_quality": "COLD",
                "behavioral_flags": {}
            }
        }

        action = agent._recommend_action(state, "response text")

        assert action == "follow_up"

    def test_build_enhanced_messages_with_crm(self):
        """Test message building with CRM output."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Ik zoek een Golf 8",
            "message_id": "msg_123",
            "conversation_history": [],
            "crm_output": {
                "lead_score": 75,
                "lead_quality": "HOT",
                "urgency": "high",
                "interest_level": "ready-to-buy"
            }
        }

        messages = agent._build_enhanced_messages(state)

        # Verify CRM context included
        assert len(messages) == 1
        content = messages[0]["content"]

        assert "LEAD INTELLIGENCE" in content
        assert "75/100" in content
        assert "HOT" in content

    def test_build_enhanced_messages_with_expertise(self):
        """Test message building with ExpertiseAgent knowledge."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Wat is het verbruik?",
            "message_id": "msg_123",
            "conversation_history": [],
            "expertise_output": {
                "knowledge": "De TDI motor heeft een gemiddeld verbruik van 5.2L/100km."
            }
        }

        messages = agent._build_enhanced_messages(state)

        content = messages[0]["content"]

        assert "KNOWLEDGE BASE" in content
        assert "5.2L/100km" in content

    def test_build_enhanced_messages_with_escalation(self):
        """Test message building with escalation."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "BKR financing vraag",
            "message_id": "msg_123",
            "conversation_history": [],
            "expertise_output": {
                "escalation_decision": {
                    "escalate": True,
                    "escalation_type": "finance_advisor",
                    "urgency": "medium",
                    "reason": "complex_financing"
                }
            }
        }

        messages = agent._build_enhanced_messages(state)

        content = messages[0]["content"]

        assert "ESCALATION" in content
        assert "finance_advisor" in content
        assert "handoff" in content.lower()

    def test_build_enhanced_messages_with_extraction(self):
        """Test message building with extraction data."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Test message",
            "message_id": "msg_123",
            "conversation_history": [],
            "extraction_output": {
                "car_interest": {
                    "make": "Volkswagen",
                    "model": "Golf 8",
                    "fuel_type": "diesel"
                },
                "budget": {
                    "max_amount": 25000
                }
            }
        }

        messages = agent._build_enhanced_messages(state)

        content = messages[0]["content"]

        assert "CUSTOMER PROFILE" in content
        assert "Volkswagen Golf 8 diesel" in content
        assert "€25000" in content

    def test_parse_enhanced_response_rag_detection(self):
        """Test RAG need detection from Dutch response."""
        agent = EnhancedConversationAgent()

        # Response indicating RAG need
        response = "Even kijken... Ik ga zoeken naar die auto voor je."

        state = {"content": "Test", "message_id": "msg_123"}

        output = agent._parse_enhanced_response(response, state)

        assert output["needs_rag"] is True

    def test_parse_enhanced_response_conversation_complete(self):
        """Test conversation completion detection."""
        agent = EnhancedConversationAgent()

        # Response indicating completion
        response = "Top! Hoor ik van je. Tot ziens!"

        state = {"content": "Test", "message_id": "msg_123"}

        output = agent._parse_enhanced_response(response, state)

        assert output["conversation_complete"] is True

    def test_parse_enhanced_response_follow_up_questions(self):
        """Test follow-up question extraction."""
        agent = EnhancedConversationAgent()

        # Multiple lines with questions
        response = "Interessant!\n\nWat is je budget?\n\nEn welke brandstof geef je de voorkeur?"

        state = {"content": "Test", "message_id": "msg_123"}

        output = agent._parse_enhanced_response(response, state)

        # Should extract questions from separate lines
        assert len(output["follow_up_questions"]) >= 2
        assert any("budget" in q.lower() for q in output["follow_up_questions"])


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    def test_hot_lead_with_test_drive_logic(self):
        """Test HOT lead requesting test drive (logic only, no API call)."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Kan ik vandaag langskomen voor een proefrit?",
            "message_id": "msg_123",
            "sender_phone": "+31612345678",
            "conversation_id": "conv_123",
            "conversation_history": [],
            "crm_output": {
                "lead_score": 85,
                "lead_quality": "HOT",
                "urgency": "critical",
                "interest_level": "ready-to-buy",
                "behavioral_flags": {
                    "test_drive_requested": True
                }
            }
        }

        # Test recommendation logic only
        action = agent._recommend_action(state, "response text")
        assert action == "schedule_test_drive"

        # Test that HOT lead gets enthusiastic opener
        lead_quality = state["crm_output"]["lead_quality"]
        opener = agent.humanization.get_opener(lead_quality, [])
        assert opener in ["Super! ", "Wat fijn! ", "Perfect! ", "Geweldig! "]

    def test_warm_lead_with_expertise_logic(self):
        """Test WARM lead with technical question + expertise knowledge (logic only, no API call)."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Wat is het brandstofverbruik?",
            "message_id": "msg_123",
            "sender_phone": "+31612345678",
            "conversation_id": "conv_123",
            "conversation_history": [],
            "crm_output": {
                "lead_score": 60,
                "lead_quality": "WARM",
                "urgency": "medium",
                "interest_level": "considering",
                "behavioral_flags": {
                    "test_drive_requested": False
                }
            },
            "expertise_output": {
                "knowledge": "De Golf 8 TDI heeft een gemiddeld verbruik van 5.2 liter per 100 km (circa 1 op 19)."
            }
        }

        # Test recommendation logic only
        action = agent._recommend_action(state, "response text")
        assert action == "send_more_info"

        # Test message building includes expertise
        messages = agent._build_enhanced_messages(state)
        content = messages[0]["content"]
        assert "KNOWLEDGE BASE" in content or "KENNIS" in content

    def test_escalated_financing_question_logic(self):
        """Test escalated financing question (logic only, no API call)."""
        agent = EnhancedConversationAgent()

        state = {
            "content": "Kan ik financieren met BKR?",
            "message_id": "msg_123",
            "sender_phone": "+31612345678",
            "conversation_id": "conv_123",
            "conversation_history": [],
            "crm_output": {
                "lead_score": 55,
                "lead_quality": "WARM",
                "urgency": "medium",
                "behavioral_flags": {}
            },
            "expertise_output": {
                "escalation_decision": {
                    "escalate": True,
                    "escalation_type": "finance_advisor",
                    "urgency": "medium",
                    "reason": "complex_financing"
                }
            }
        }

        # Test recommendation logic only
        action = agent._recommend_action(state, "response text")
        assert action == "escalate"

        # Test message building includes escalation context
        messages = agent._build_enhanced_messages(state)
        content = messages[0]["content"]
        assert "ESCALATION" in content or "ESCALATIE" in content


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
