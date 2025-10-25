"""
Unit tests for Enhanced CRM Agent.

Tests:
- Lead scoring algorithm (0-100 points)
- Lead quality classification (HOT/WARM/LUKEWARM/COLD)
- Intelligent tagging system (20+ tags)
- Behavioral flag detection
- Custom attributes preparation
"""
import pytest
from app.agents.enhanced_crm_agent import (
    EnhancedCRMAgent,
    LeadScoringEngine,
    IntelligentTagging
)


class TestLeadScoringEngine:
    """Test lead scoring algorithm."""

    def test_hot_lead_score(self):
        """Test HOT lead scoring (70-100 points)."""
        engine = LeadScoringEngine()

        # Perfect lead: Specific car, budget, test drive, urgent
        message = "Ik zoek een Golf 8 diesel, budget €25.000, kan ik vandaag langskomen voor een proefrit?"

        result = engine.calculate_score(
            message=message,
            extraction=None,
            expertise_output=None,
            conversation_history=[]
        )

        assert result["lead_score"] >= 70
        assert result["lead_quality"] == "HOT"
        assert result["interest_level"] == "ready-to-buy"
        assert result["urgency"] in ["critical", "high"]

    def test_warm_lead_score(self):
        """Test WARM lead scoring (50-69 points)."""
        engine = LeadScoringEngine()

        # Good lead: Specific car, budget mentioned, wants test drive
        message = "Ik ben geïnteresseerd in een Audi A4 diesel 2023, budget rond de €30.000, kan ik een proefrit maken?"

        result = engine.calculate_score(
            message=message,
            extraction=None,
            expertise_output=None,
            conversation_history=[]
        )

        assert 50 <= result["lead_score"] < 70
        assert result["lead_quality"] == "WARM"
        assert result["interest_level"] == "considering"

    def test_cold_lead_score(self):
        """Test COLD lead scoring (0-29 points)."""
        engine = LeadScoringEngine()

        # Vague inquiry: No specifics
        message = "Wat voor auto's hebben jullie?"

        result = engine.calculate_score(
            message=message,
            extraction=None,
            expertise_output=None,
            conversation_history=[]
        )

        assert result["lead_score"] < 30
        assert result["lead_quality"] == "COLD"
        assert result["interest_level"] == "browsing"

    def test_score_breakdown(self):
        """Test score breakdown components."""
        engine = LeadScoringEngine()

        message = "Golf 8 diesel, €25.000, proefrit morgen"

        result = engine.calculate_score(
            message=message,
            extraction=None,
            expertise_output=None,
            conversation_history=[]
        )

        breakdown = result["score_breakdown"]

        # Verify all components present
        assert "car_inquiry" in breakdown
        assert "budget_mentioned" in breakdown
        assert "urgency_signals" in breakdown
        assert "test_drive_request" in breakdown
        assert "trade_in_interest" in breakdown
        assert "financing_interest" in breakdown

        # Verify car inquiry score
        assert breakdown["car_inquiry"] > 0

        # Verify budget score
        assert breakdown["budget_mentioned"] > 0

        # Verify test drive score
        assert breakdown["test_drive_request"] == 15

    def test_car_inquiry_scoring(self):
        """Test car inquiry specificity scoring."""
        engine = LeadScoringEngine()

        # Specific make/model
        result1 = engine._score_car_inquiry("Ik zoek een Golf 8", None)
        assert result1 >= 15

        # With year and fuel type
        result2 = engine._score_car_inquiry("Golf 8 2021 diesel", None)
        assert result2 >= 25

        # With features
        result3 = engine._score_car_inquiry("Golf 8 diesel automaat met cruise control", None)
        assert result3 == 30

    def test_urgency_scoring(self):
        """Test urgency signal detection."""
        engine = LeadScoringEngine()

        # Critical urgency
        score1, level1 = engine._score_urgency("Kan ik vandaag langskomen?", [])
        assert score1 == 15
        assert level1 == "critical"

        # High urgency
        score2, level2 = engine._score_urgency("Kan ik deze week langskomen?", [])
        assert score2 == 10
        assert level2 == "high"

        # Medium urgency
        score3, level3 = engine._score_urgency("Ik heb interesse", [])
        assert score3 == 5
        assert level3 == "medium"

    def test_test_drive_scoring(self):
        """Test test drive request detection."""
        engine = LeadScoringEngine()

        assert engine._score_test_drive("Kan ik een proefrit maken?") == 15
        assert engine._score_test_drive("Mag ik testrijden?") == 15
        assert engine._score_test_drive("Gewoon informatie") == 0

    def test_trade_in_scoring(self):
        """Test trade-in interest detection."""
        engine = LeadScoringEngine()

        assert engine._score_trade_in("Kan ik mijn oude auto inruilen?") == 10
        assert engine._score_trade_in("Accepteren jullie inruil?") == 10
        assert engine._score_trade_in("Gewoon informatie") == 0

    def test_financing_scoring(self):
        """Test financing interest detection."""
        engine = LeadScoringEngine()

        assert engine._score_financing("Kan ik financieren?") == 10
        assert engine._score_financing("Wat zijn de maandlasten?") == 10
        assert engine._score_financing("Gewoon informatie") == 0


class TestIntelligentTagging:
    """Test intelligent tagging system."""

    def test_journey_tags(self):
        """Test customer journey tags."""
        # First contact
        tags1 = IntelligentTagging.generate_tags(
            message="Hallo, ik zoek een auto",
            lead_score_data={"lead_quality": "COLD", "urgency": "low"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "journey:first-contact" in tags1

        # Initial inquiry (1-3 messages)
        tags2 = IntelligentTagging.generate_tags(
            message="Wat kost deze auto?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[{"role": "user"}, {"role": "assistant"}, {"role": "user"}]
        )
        assert "journey:initial-inquiry" in tags2

        # Information gathering (4-6 messages)
        tags3 = IntelligentTagging.generate_tags(
            message="Wat is het verbruik?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[{"role": "user"}] * 5
        )
        assert "journey:information-gathering" in tags3

    def test_car_interest_tags(self):
        """Test car make/model interest tags."""
        # Volkswagen interest
        tags1 = IntelligentTagging.generate_tags(
            message="Ik zoek een Golf 8",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "interest:volkswagen" in tags1

        # Audi interest
        tags2 = IntelligentTagging.generate_tags(
            message="Hebben jullie een Audi A4?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "interest:audi" in tags2

    def test_fuel_preference_tags(self):
        """Test fuel type preference tags."""
        # Diesel preference
        tags1 = IntelligentTagging.generate_tags(
            message="Ik zoek een diesel auto",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "preference:diesel" in tags1

        # Benzine preference
        tags2 = IntelligentTagging.generate_tags(
            message="Ik wil een benzine auto",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "preference:benzine" in tags2

        # Green energy preference
        tags3 = IntelligentTagging.generate_tags(
            message="Hebben jullie hybride auto's?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "preference:green-energy" in tags3

    def test_purchase_intent_tags(self):
        """Test purchase intent tags based on lead quality."""
        # HOT lead
        tags1 = IntelligentTagging.generate_tags(
            message="Ik wil deze auto kopen",
            lead_score_data={"lead_quality": "HOT", "urgency": "critical"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "intent:ready-to-buy" in tags1

        # WARM lead
        tags2 = IntelligentTagging.generate_tags(
            message="Ik overweeg deze auto",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "intent:seriously-considering" in tags2

        # COLD lead
        tags3 = IntelligentTagging.generate_tags(
            message="Gewoon kijken",
            lead_score_data={"lead_quality": "COLD", "urgency": "low"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "intent:browsing" in tags3

    def test_behavioral_tags(self):
        """Test behavioral tags."""
        # Test drive requested
        tags1 = IntelligentTagging.generate_tags(
            message="Kan ik een proefrit maken?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:test-drive-requested" in tags1

        # Trade-in interest
        tags2 = IntelligentTagging.generate_tags(
            message="Kan ik mijn oude auto inruilen?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:has-trade-in" in tags2

        # Financing interest
        tags3 = IntelligentTagging.generate_tags(
            message="Kan ik financieren?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:needs-financing" in tags3

        # Price-sensitive
        tags4 = IntelligentTagging.generate_tags(
            message="Wat is de prijs? Heb je iets goedkopers?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:price-sensitive" in tags4

        # Technical buyer
        tags5 = IntelligentTagging.generate_tags(
            message="Wat is het motorvermogen en brandstofverbruik?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:technical-buyer" in tags5

        # Family buyer
        tags6 = IntelligentTagging.generate_tags(
            message="Hoeveel ruimte is er voor kinderen?",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "behavior:family-buyer" in tags6

    def test_engagement_tags(self):
        """Test engagement level tags."""
        # Hot lead
        tags1 = IntelligentTagging.generate_tags(
            message="Test message",
            lead_score_data={"lead_quality": "HOT", "urgency": "critical"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "engagement:hot-lead" in tags1

        # Warm lead
        tags2 = IntelligentTagging.generate_tags(
            message="Test message",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "engagement:warm-lead" in tags2

        # Cold lead
        tags3 = IntelligentTagging.generate_tags(
            message="Test message",
            lead_score_data={"lead_quality": "COLD", "urgency": "low"},
            expertise_output=None,
            conversation_history=[]
        )
        assert "engagement:cold-lead" in tags3

    def test_escalation_tags(self):
        """Test escalation tags from ExpertiseAgent."""
        expertise_output = {
            "escalation_decision": {
                "escalate": True,
                "escalation_type": "finance_advisor"
            }
        }

        tags = IntelligentTagging.generate_tags(
            message="Test message",
            lead_score_data={"lead_quality": "WARM", "urgency": "medium"},
            expertise_output=expertise_output,
            conversation_history=[]
        )

        assert "escalated:finance_advisor" in tags
        assert "status:needs-human-attention" in tags

    def test_source_tag_always_present(self):
        """Test that source tag is always added."""
        tags = IntelligentTagging.generate_tags(
            message="Any message",
            lead_score_data={"lead_quality": "COLD", "urgency": "low"},
            expertise_output=None,
            conversation_history=[]
        )

        assert "source:whatsapp-ai-agent" in tags


class TestEnhancedCRMAgent:
    """Test Enhanced CRM Agent integration."""

    def test_behavioral_flags_extraction(self):
        """Test behavioral flag extraction."""
        agent = EnhancedCRMAgent()

        # Test drive requested
        flags1 = agent._extract_behavioral_flags("Kan ik een proefrit maken?")
        assert flags1["test_drive_requested"] is True
        assert flags1["has_trade_in"] is False
        assert flags1["needs_financing"] is False

        # Multiple behaviors
        flags2 = agent._extract_behavioral_flags("Kan ik financieren en mijn oude auto inruilen?")
        assert flags2["has_trade_in"] is True
        assert flags2["needs_financing"] is True

    def test_custom_attributes_preparation(self):
        """Test custom attributes preparation."""
        agent = EnhancedCRMAgent()

        state = {
            "content": "Golf 8 diesel, €25.000",
            "sender_phone": "+31612345678",
            "conversation_id": "conv_123",
            "conversation_history": [{"role": "user"}] * 3,
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

        lead_score_data = {
            "lead_score": 75,
            "lead_quality": "WARM",
            "interest_level": "considering",
            "urgency": "medium"
        }

        behavioral_flags = {
            "test_drive_requested": True,
            "has_trade_in": False,
            "needs_financing": False,
            "escalated": False
        }

        attributes = agent._prepare_custom_attributes(
            state=state,
            lead_score_data=lead_score_data,
            behavioral_flags=behavioral_flags
        )

        # Verify core attributes
        assert attributes["lead_score"] == 75
        assert attributes["lead_quality"] == "WARM"
        assert attributes["interest_level"] == "considering"
        assert attributes["urgency"] == "medium"

        # Verify extraction data
        assert attributes["interested_in_make"] == "Volkswagen"
        assert attributes["interested_in_model"] == "Golf 8"
        assert attributes["interested_in_fuel_type"] == "diesel"
        assert attributes["budget_max"] == 25000

        # Verify behavioral flags
        assert attributes["test_drive_requested"] is True
        assert attributes["has_trade_in"] is False

        # Verify conversation stage
        assert attributes["conversation_stage"] == "initial-inquiry"

    def test_execute_full_flow(self):
        """Test complete CRM agent execution."""
        agent = EnhancedCRMAgent()

        state = {
            "content": "Golf 8 diesel, €25.000, kan ik morgen langskomen voor een proefrit?",
            "sender_phone": "+31612345678",
            "conversation_id": "conv_123",
            "message_id": "msg_123",
            "conversation_history": []
        }

        result = agent._execute(state)

        # Verify output structure
        assert "output" in result
        assert "tokens_used" in result
        assert "cost_usd" in result

        output = result["output"]

        # Verify lead score calculated
        assert "lead_score" in output
        assert "lead_quality" in output
        assert output["lead_score"] >= 60  # Should be at least WARM

        # Verify tags generated
        assert "tags_added" in output
        assert len(output["tags_added"]) >= 5

        # Verify custom attributes
        assert "custom_attributes" in output
        assert "lead_score" in output["custom_attributes"]

        # Verify behavioral flags
        assert "behavioral_flags" in output
        assert output["behavioral_flags"]["test_drive_requested"] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
