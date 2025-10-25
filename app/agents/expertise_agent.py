"""
Expertise Agent - Knowledge Base with Escalation Logic.

This agent:
1. Classifies queries into knowledge domains (Technical, Financial, Service)
2. Provides expert knowledge snippets
3. Detects when human escalation is needed
4. Returns escalation decisions with urgency levels

Knowledge Modules:
- Technical: Motor types, specs, features
- Financial: Financing, trade-in, pricing
- Service: Test drives, warranty, delivery
"""
import json
import random
from typing import Dict, List, Optional, Any
from anthropic import Anthropic

from app.agents.base import BaseAgent
from app.orchestration.state import ConversationState
from app.monitoring.logging_config import get_logger
from app.config.agents_config import ANTHROPIC_CONFIG

logger = get_logger(__name__)


class TechnicalKnowledgeModule:
    """Technical automotive knowledge base."""

    def __init__(self):
        self.knowledge_base = {
            "motor_types": {
                "TSI": "Turbocharged Stratified Injection - benzinemotor met turbo en directe inspuiting",
                "TDI": "Turbocharged Direct Injection - dieselmotor met turbo en directe inspuiting",
                "TFSI": "Turbo Fuel Stratified Injection - Audi's versie van TSI",
                "TDI BiTurbo": "Diesel met twee turbo's voor meer vermogen",
                "PHEV": "Plug-in Hybrid Electric Vehicle - hybride met oplaadbare batterij",
                "EV": "Electric Vehicle - volledig elektrisch"
            },
            "fuel_consumption": {
                "diesel": "Gemiddeld 5-7 liter per 100km, afhankelijk van model en rijstijl",
                "benzine": "Gemiddeld 6-9 liter per 100km, afhankelijk van model en rijstijl",
                "hybride": "Gemiddeld 4-6 liter per 100km, afhankelijk van elektrisch rijden",
                "elektrisch": "Gemiddeld 15-20 kWh per 100km, afhankelijk van model"
            },
            "safety_features": {
                "adaptive_cruise_control": "Automatisch afstand houden tot voorganger",
                "lane_assist": "Waarschuwing en correctie bij ongewild van baan gaan",
                "blind_spot": "Waarschuwing voor voertuigen in dode hoek",
                "emergency_brake": "Automatisch remmen bij dreigend ongeval"
            }
        }

    def query(self, question: str) -> Dict[str, Any]:
        """Query technical knowledge base."""
        question_lower = question.lower()
        relevant_snippets = []

        if "tsi" in question_lower or "tdi" in question_lower or "motor" in question_lower:
            relevant_snippets.append({"category": "motor_types", "data": self.knowledge_base["motor_types"]})

        if "verbruik" in question_lower or "brandstof" in question_lower:
            relevant_snippets.append({"category": "fuel_consumption", "data": self.knowledge_base["fuel_consumption"]})

        if "cruise control" in question_lower or "safety" in question_lower or "veilig" in question_lower:
            relevant_snippets.append({"category": "safety_features", "data": self.knowledge_base["safety_features"]})

        return {
            "snippets": relevant_snippets,
            "domain": "technical",
            "confidence": 0.85 if relevant_snippets else 0.0
        }


class FinancialKnowledgeModule:
    """Financial knowledge (financing, trade-in, pricing)."""

    def __init__(self):
        self.knowledge_base = {
            "financing_options": [
                "Autolening met vaste rente (4.5% - 7.5%)",
                "Lease (private lease of financial lease)",
                "Betalen in termijnen (tot 60 maanden)",
                "Ballonfinanciering (lage maandlasten, restbedrag aan einde)"
            ],
            "trade_in_process": {
                "step1": "Gratis waardetaxatie van je huidige auto",
                "step2": "Inruilwaarde wordt afgetrokken van aankoopprijs",
                "step3": "Eventuele restschuld kan meegenomen worden in financiering",
                "time": "Taxatie duurt ongeveer 15-30 minuten"
            },
            "monthly_payment_estimates": {
                "15000_euro": "€250 - €300 per maand (60 maanden)",
                "25000_euro": "€400 - €500 per maand (60 maanden)",
                "35000_euro": "€550 - €700 per maand (60 maanden)"
            },
            "taxes": {
                "mrb": "Motorrijtuigenbelasting - afhankelijk van gewicht en brandstof",
                "bpm": "Belasting Personenauto's en Motorrijwielen - al betaald bij aankoop"
            }
        }

    def query(self, question: str) -> Dict[str, Any]:
        """Query financial knowledge base."""
        question_lower = question.lower()
        relevant_snippets = []

        if "financier" in question_lower or "lening" in question_lower:
            relevant_snippets.append({"category": "financing_options", "data": self.knowledge_base["financing_options"]})

        if "inruil" in question_lower or "trade" in question_lower:
            relevant_snippets.append({"category": "trade_in_process", "data": self.knowledge_base["trade_in_process"]})

        if "maandlasten" in question_lower or "per maand" in question_lower:
            relevant_snippets.append({"category": "monthly_payment_estimates", "data": self.knowledge_base["monthly_payment_estimates"]})

        if "belasting" in question_lower or "mrb" in question_lower or "bpm" in question_lower:
            relevant_snippets.append({"category": "taxes", "data": self.knowledge_base["taxes"]})

        return {
            "snippets": relevant_snippets,
            "domain": "financial",
            "confidence": 0.90 if relevant_snippets else 0.0
        }


class ServiceKnowledgeModule:
    """Service & process knowledge."""

    def __init__(self):
        self.knowledge_base = {
            "test_drive": {
                "duration": "30-45 minuten",
                "requirements": "Geldig rijbewijs meenemen",
                "booking": "Vandaag nog mogelijk, reserveer van tevoren",
                "location": "Seldenrijk Harderwijk, Parallelweg 30"
            },
            "warranty": {
                "dealer_warranty": "1 jaar dealer garantie standaard",
                "extended": "Uitgebreide garantie tot 3 jaar mogelijk",
                "coverage": "Alle mechanische en elektrische onderdelen"
            },
            "delivery": {
                "preparation_time": "3-5 werkdagen na aankoop",
                "includes": "APK, onderhoudsbeurt, schoonmaak, tankje vol",
                "home_delivery": "Mogelijk tegen meerprijs (€100-€200)"
            }
        }

    def query(self, question: str) -> Dict[str, Any]:
        """Query service knowledge base."""
        question_lower = question.lower()
        relevant_snippets = []

        if "proefrit" in question_lower or "test" in question_lower:
            relevant_snippets.append({"category": "test_drive", "data": self.knowledge_base["test_drive"]})

        if "garantie" in question_lower or "warranty" in question_lower:
            relevant_snippets.append({"category": "warranty", "data": self.knowledge_base["warranty"]})

        if "levering" in question_lower or "bezorgen" in question_lower or "delivery" in question_lower:
            relevant_snippets.append({"category": "delivery", "data": self.knowledge_base["delivery"]})

        return {
            "snippets": relevant_snippets,
            "domain": "service",
            "confidence": 0.88 if relevant_snippets else 0.0
        }


class ExpertiseAgent(BaseAgent):
    """
    Expertise Agent - Provides knowledge and detects escalation needs.

    Features:
    - 3 knowledge modules (Technical, Financial, Service)
    - Query classification
    - Escalation trigger detection
    - Urgency assessment
    """

    def __init__(self):
        super().__init__(
            agent_name="expertise",
            model="claude-3-5-haiku-20241022",  # Fast model for classification
            max_retries=3,
            timeout_seconds=15
        )

        self.client = Anthropic(api_key=ANTHROPIC_CONFIG["api_key"])

        # Initialize knowledge modules
        self.knowledge_base = {
            "technical": TechnicalKnowledgeModule(),
            "financial": FinancialKnowledgeModule(),
            "service": ServiceKnowledgeModule()
        }

        logger.info("✅ ExpertiseAgent initialized with 3 knowledge modules")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute expertise analysis and escalation check.

        Returns:
            {
                "output": {
                    "classification": {...},
                    "escalation_decision": {...},
                    "knowledge": {...},
                    "confidence": 0.0-1.0
                },
                "tokens_used": {...},
                "cost_usd": 0.0
            }
        """
        message = state["content"]

        logger.info(f"🧠 ExpertiseAgent analyzing message: {message[:100]}...")

        # Step 1: Classify query
        classification = self._classify_query(message)

        # Step 2: Check escalation triggers
        escalation_decision = self._check_escalation_triggers(
            message=message,
            classification=classification,
            conversation_history=state.get("conversation_history", [])
        )

        # Step 3: Get knowledge if no escalation
        knowledge = None
        if not escalation_decision["escalate"]:
            knowledge = self._get_knowledge(
                domain=classification["primary_domain"],
                query=message
            )

        logger.info(
            f"📊 Classification: {classification['primary_domain']}, "
            f"Escalate: {escalation_decision['escalate']}, "
            f"Confidence: {classification['confidence']}"
        )

        return {
            "output": {
                "domain": classification["primary_domain"],  # Add top-level domain field
                "classification": classification,
                "escalation_decision": escalation_decision,
                "knowledge": knowledge,
                "confidence": classification["confidence"]
            },
            "tokens_used": {
                "input": 0,  # No API call for knowledge base
                "output": 0,
                "total": 0
            },
            "cost_usd": 0.0
        }

    def _classify_query(self, message: str) -> Dict[str, Any]:
        """
        Classify query into knowledge domains using keyword matching.

        Returns:
            {
                "primary_domain": "technical" | "financial" | "service",
                "complexity_level": "simple" | "moderate" | "complex",
                "confidence": 0.0-1.0
            }
        """
        message_lower = message.lower()

        # Domain keyword matching
        technical_keywords = ["motor", "tsi", "tdi", "verbruik", "brandstof", "specificatie",
                              "cruise control", "veilig", "feature", "elektrisch", "hybride"]

        financial_keywords = ["financier", "lening", "prijs", "kost", "maandlasten", "inruil",
                              "trade", "belasting", "mrb", "bpm", "betalen", "aflossen"]

        service_keywords = ["proefrit", "test", "garantie", "levering", "bezorgen", "afspraak",
                           "langskomen", "bezichtigen", "delivery", "warranty"]

        # Count matches
        technical_score = sum(1 for kw in technical_keywords if kw in message_lower)
        financial_score = sum(1 for kw in financial_keywords if kw in message_lower)
        service_score = sum(1 for kw in service_keywords if kw in message_lower)

        # Determine primary domain
        scores = {
            "technical": technical_score,
            "financial": financial_score,
            "service": service_score
        }

        primary_domain = max(scores, key=scores.get)
        max_score = scores[primary_domain]

        # Complexity assessment (simple heuristic)
        complexity = "simple"
        if len(message.split()) > 20:
            complexity = "moderate"
        if any(word in message_lower for word in ["bkr", "restschuld", "remap", "verborgen schade"]):
            complexity = "complex"

        # Confidence based on score
        confidence = min(0.95, 0.5 + (max_score * 0.15))

        return {
            "primary_domain": primary_domain if max_score > 0 else "service",  # Default to service
            "complexity_level": complexity,
            "confidence": confidence
        }

    def _check_escalation_triggers(
        self,
        message: str,
        classification: Dict,
        conversation_history: List
    ) -> Dict[str, Any]:
        """
        Check if message triggers human escalation.

        Returns:
            {
                "escalate": True/False,
                "escalation_type": "finance_advisor" | "technical_expert" | "manager" | None,
                "urgency": "low" | "medium" | "high" | "critical",
                "reason": "complex_financing" | "complaint" | etc.
            }
        """
        message_lower = message.lower()

        # Trigger 1: Complex Financing
        financing_keywords = ["bkr", "aflossingsvrij", "lease", "custom plan", "rente",
                             "annuïteit", "restschuld", "negatieve bkr"]

        if any(kw in message_lower for kw in financing_keywords):
            if classification["complexity_level"] == "complex":
                return {
                    "escalate": True,
                    "escalation_type": "finance_advisor",
                    "urgency": "medium",
                    "reason": "complex_financing"
                }

        # Trigger 2: Technical Expert Needed
        expert_keywords = ["remap", "chip tune", "verborgen schade", "complete onderhoudshistorie",
                          "exacte specificaties", "technische details van motor"]

        if any(kw in message_lower for kw in expert_keywords):
            return {
                "escalate": True,
                "escalation_type": "technical_expert",
                "urgency": "low",
                "reason": "technical_deep_dive"
            }

        # Trigger 3: Legal/Policy Questions
        legal_keywords = ["retour", "annuleren", "terugbetaling", "garantieclaim",
                         "juridisch", "aansprakelijk", "wet"]

        if any(kw in message_lower for kw in legal_keywords):
            return {
                "escalate": True,
                "escalation_type": "manager",
                "urgency": "high",
                "reason": "legal_question"
            }

        # Trigger 4: Complaint Detection
        complaint_indicators = ["teleurgesteld", "niet tevreden", "slechte service",
                               "klacht", "probleem met", "advertentie klopt niet"]

        if any(ind in message_lower for ind in complaint_indicators):
            return {
                "escalate": True,
                "escalation_type": "manager",
                "urgency": "critical",
                "reason": "complaint"
            }

        # Trigger 5: Custom Requests
        custom_keywords = ["kunnen jullie zoeken", "importeren", "custom deal",
                          "speciale wens", "op maat"]

        if any(kw in message_lower for kw in custom_keywords):
            return {
                "escalate": True,
                "escalation_type": "sales_manager",
                "urgency": "medium",
                "reason": "custom_request"
            }

        # Trigger 6: Repeated Confusion (if many messages)
        if len(conversation_history) > 5:
            # Check if customer asking same question repeatedly
            # Simple heuristic: if last 3 messages are very similar
            if len(conversation_history) >= 3:
                recent_user_messages = [
                    msg["content"] for msg in conversation_history[-5:]
                    if msg.get("role") == "user"
                ]
                if len(recent_user_messages) >= 3:
                    # Check similarity (simple: same keywords appear)
                    first_words = set(recent_user_messages[0].lower().split())
                    similarities = [
                        len(first_words & set(msg.lower().split())) / len(first_words)
                        for msg in recent_user_messages[1:]
                    ]
                    if sum(s > 0.5 for s in similarities) >= 2:  # 2+ similar messages
                        return {
                            "escalate": True,
                            "escalation_type": "manager",
                            "urgency": "medium",
                            "reason": "repeated_confusion"
                        }

        # No escalation needed
        return {
            "escalate": False,
            "escalation_type": None,
            "urgency": "low",
            "reason": None
        }

    def _get_knowledge(self, domain: str, query: str) -> Dict[str, Any]:
        """Retrieve relevant knowledge from domain module."""
        if domain == "technical":
            return self.knowledge_base["technical"].query(query)
        elif domain == "financial":
            return self.knowledge_base["financial"].query(query)
        elif domain == "service":
            return self.knowledge_base["service"].query(query)
        else:
            return {"snippets": [], "confidence": 0.0}
