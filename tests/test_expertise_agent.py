"""
Unit tests for ExpertiseAgent.

Tests:
- Query classification (Technical, Financial, Service)
- Escalation trigger detection
- Knowledge module queries
"""
import pytest
from app.agents.expertise_agent import (
    ExpertiseAgent,
    TechnicalKnowledgeModule,
    FinancialKnowledgeModule,
    ServiceKnowledgeModule
)


class TestTechnicalKnowledgeModule:
    """Test technical knowledge queries."""

    def test_motor_type_query(self):
        """Test TSI/TDI motor queries."""
        module = TechnicalKnowledgeModule()
        result = module.query("Wat is het verschil tussen TSI en TDI?")

        assert result["domain"] == "technical"
        assert result["confidence"] > 0.8
        assert len(result["snippets"]) > 0
        assert any("motor_types" in s["category"] for s in result["snippets"])

    def test_fuel_consumption_query(self):
        """Test fuel consumption queries."""
        module = TechnicalKnowledgeModule()
        result = module.query("Wat is het brandstofverbruik?")

        assert result["domain"] == "technical"
        assert result["confidence"] > 0.8
        assert any("fuel_consumption" in s["category"] for s in result["snippets"])

    def test_safety_features_query(self):
        """Test safety feature queries."""
        module = TechnicalKnowledgeModule()
        result = module.query("Heeft deze auto cruise control?")

        assert result["domain"] == "technical"
        assert any("safety_features" in s["category"] for s in result["snippets"])


class TestFinancialKnowledgeModule:
    """Test financial knowledge queries."""

    def test_financing_query(self):
        """Test financing queries."""
        module = FinancialKnowledgeModule()
        result = module.query("Kan ik deze auto financieren?")

        assert result["domain"] == "financial"
        assert result["confidence"] > 0.8
        assert any("financing_options" in s["category"] for s in result["snippets"])

    def test_trade_in_query(self):
        """Test trade-in queries."""
        module = FinancialKnowledgeModule()
        result = module.query("Accepteren jullie inruil?")

        assert result["domain"] == "financial"
        assert any("trade_in_process" in s["category"] for s in result["snippets"])

    def test_monthly_payment_query(self):
        """Test monthly payment queries."""
        module = FinancialKnowledgeModule()
        result = module.query("Wat zijn de maandlasten?")

        assert result["domain"] == "financial"
        assert any("monthly_payment_estimates" in s["category"] for s in result["snippets"])


class TestServiceKnowledgeModule:
    """Test service knowledge queries."""

    def test_test_drive_query(self):
        """Test test drive queries."""
        module = ServiceKnowledgeModule()
        result = module.query("Hoe werkt een proefrit?")

        assert result["domain"] == "service"
        assert result["confidence"] > 0.8
        assert any("test_drive" in s["category"] for s in result["snippets"])

    def test_warranty_query(self):
        """Test warranty queries."""
        module = ServiceKnowledgeModule()
        result = module.query("Wat is jullie garantie?")

        assert result["domain"] == "service"
        assert any("warranty" in s["category"] for s in result["snippets"])


class TestExpertiseAgent:
    """Test ExpertiseAgent classification and escalation logic."""

    def test_technical_classification(self):
        """Test technical query classification."""
        agent = ExpertiseAgent()
        classification = agent._classify_query("Wat is het brandstofverbruik van deze auto?")

        assert classification["primary_domain"] == "technical"
        assert classification["confidence"] > 0.5

    def test_financial_classification(self):
        """Test financial query classification."""
        agent = ExpertiseAgent()
        classification = agent._classify_query("Kan ik deze auto financieren met een lening?")

        assert classification["primary_domain"] == "financial"
        assert classification["confidence"] > 0.5

    def test_service_classification(self):
        """Test service query classification."""
        agent = ExpertiseAgent()
        classification = agent._classify_query("Kan ik vandaag langskomen voor een proefrit?")

        assert classification["primary_domain"] == "service"
        assert classification["confidence"] > 0.5

    def test_escalation_complex_financing(self):
        """Test escalation trigger for complex financing."""
        agent = ExpertiseAgent()
        classification = {"primary_domain": "financial", "complexity_level": "complex", "confidence": 0.9}

        escalation = agent._check_escalation_triggers(
            message="Ik heb BKR-registratie, kan ik toch financieren?",
            classification=classification,
            conversation_history=[]
        )

        assert escalation["escalate"] is True
        assert escalation["escalation_type"] == "finance_advisor"
        assert escalation["reason"] == "complex_financing"

    def test_escalation_complaint(self):
        """Test escalation trigger for complaints."""
        agent = ExpertiseAgent()
        classification = {"primary_domain": "service", "complexity_level": "simple", "confidence": 0.8}

        escalation = agent._check_escalation_triggers(
            message="Ik ben niet tevreden met de service",
            classification=classification,
            conversation_history=[]
        )

        assert escalation["escalate"] is True
        assert escalation["escalation_type"] == "manager"
        assert escalation["urgency"] == "critical"
        assert escalation["reason"] == "complaint"

    def test_escalation_technical_expert(self):
        """Test escalation for technical deep-dive."""
        agent = ExpertiseAgent()
        classification = {"primary_domain": "technical", "complexity_level": "complex", "confidence": 0.9}

        escalation = agent._check_escalation_triggers(
            message="Heeft deze auto verborgen schade?",
            classification=classification,
            conversation_history=[]
        )

        assert escalation["escalate"] is True
        assert escalation["escalation_type"] == "technical_expert"
        assert escalation["reason"] == "technical_deep_dive"

    def test_no_escalation_simple_query(self):
        """Test no escalation for simple queries."""
        agent = ExpertiseAgent()
        classification = {"primary_domain": "technical", "complexity_level": "simple", "confidence": 0.9}

        escalation = agent._check_escalation_triggers(
            message="Wat kost deze auto?",
            classification=classification,
            conversation_history=[]
        )

        assert escalation["escalate"] is False
        assert escalation["escalation_type"] is None

    def test_execute_no_escalation(self):
        """Test full execution without escalation."""
        agent = ExpertiseAgent()

        state = {
            "content": "Wat is het brandstofverbruik van een diesel?",
            "conversation_history": []
        }

        result = agent._execute(state)

        assert "output" in result
        assert result["output"]["escalation_decision"]["escalate"] is False
        assert result["output"]["knowledge"] is not None
        assert result["output"]["classification"]["primary_domain"] == "technical"

    def test_execute_with_escalation(self):
        """Test full execution with escalation."""
        agent = ExpertiseAgent()

        state = {
            "content": "Ik heb BKR-registratie, kan ik toch een auto financieren?",
            "conversation_history": []
        }

        result = agent._execute(state)

        assert "output" in result
        assert result["output"]["escalation_decision"]["escalate"] is True
        assert result["output"]["escalation_decision"]["escalation_type"] == "finance_advisor"
        assert result["output"]["knowledge"] is None  # No knowledge if escalating


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
