"""
Extraction Agent - Structured car preference extraction using direct Anthropic API.

Extracts automotive preferences from customer WhatsApp messages:
- Car make/model (Volkswagen Golf, BMW 3-serie, etc.)
- Fuel type (diesel, benzine, hybride, elektrisch)
- Price range (min/max budget in euros)
- Mileage preferences (max kilometers)
- Year preferences (min build year)
- Transmission type (automaat, handgeschakeld)
- Body type (SUV, sedan, hatchback, etc.)
"""
from typing import Optional, Dict, Any
import json
from anthropic import Anthropic

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import (
    ConversationState,
    ExtractionOutput,
    CarPreferences
)
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


# ============ EXTRACTION PROMPT ============

EXTRACTION_SYSTEM_PROMPT = """Je bent een data-extractie expert voor een autodealer (Seldenrijk Auto).

Extraheer gestructureerde auto-voorkeuren uit klantberichten in het Nederlands.

**Auto Merk & Model:**
- Extraheer specifieke merken (bijv. "Volkswagen", "BMW", "Audi")
- Extraheer specifieke modellen (bijv. "Golf 8", "3-serie", "Q5")
- Normaliseer merknamen (bijv. "VW" → "Volkswagen")

**Brandstoftype:**
- Extracteer brandstoftype: "diesel", "benzine", "hybride", "elektrisch", "lpg"
- Standaard: null (niet gespecificeerd)

**Prijsrange:**
- Extraheer numerieke waarden (verwijder "€", "k", komma's)
- Converteer "k" naar duizenden (bijv. "25k" → 25000)
- min_price: minimale budget
- max_price: maximale budget

**Kilometerstand:**
- Extraheer maximale kilometerstand
- Normaliseer (bijv. "150k km" → 150000)

**Bouwjaar:**
- Extraheer minimaal bouwjaar
- Accepteer jaar of relatief (bijv. "na 2018" → 2018)

**Transmissie:**
- Detecteer: "automaat", "handgeschakeld"
- Standaard: null

**Carrosserie:**
- Detecteer: "SUV", "sedan", "hatchback", "stationwagon", "coupé", "cabrio", "MPV"
- Standaard: null

**Kleur:**
- Extraheer kleurvoorkeur indien genoemd
- Standaard: null

**Belangrijk:**
- Retourneer JSON met alleen GEVONDEN velden
- Wees conservatief - alleen extraheren wat expliciet genoemd is
- Gebruik null voor niet-gevonden velden
- GEEN hallucinatie van data

**Output format:**
```json
{
    "make": "Volkswagen of null",
    "model": "Golf 8 of null",
    "fuel_type": "diesel/benzine/hybride/elektrisch/lpg of null",
    "min_price": nummer of null,
    "max_price": nummer of null,
    "max_mileage": nummer (km) of null,
    "min_year": nummer (jaar) of null,
    "transmission": "automaat/handgeschakeld of null",
    "body_type": "SUV/sedan/etc of null",
    "preferred_color": "zwart/wit/etc of null"
}
```"""


class ExtractionAgent(BaseAgent):
    """
    Extraction Agent using direct Anthropic API for car preference extraction.

    Completely rewritten for automotive domain (removed recruitment code).
    No Pydantic AI dependency (removed due to async context issues).
    """

    def __init__(self):
        """Initialize Extraction Agent with Anthropic API."""
        config = AGENT_CONFIGS["extraction"]

        super().__init__(
            agent_name="extraction",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client directly
        self.client = Anthropic(api_key=config["config"]["api_key"])
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 500)

        logger.info("✅ Extraction Agent initialized (Automotive Domain, No Pydantic AI)")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute extraction agent to extract car preferences.

        Args:
            state: Current conversation state

        Returns:
            Dict with ExtractionOutput and metadata
        """
        # Build extraction prompt
        user_message = self._build_extraction_prompt(state)

        logger.info(
            "🚗 Extracting car preferences",
            extra={
                "message_id": state["message_id"],
                "intent": state.get("router_output", {}).get("intent"),
                "message_preview": state["content"][:100]
            }
        )

        try:
            # Call Anthropic API directly (no Pydantic AI)
            response = self.client.messages.create(
                model=self.model,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Extract JSON from Claude response
            response_text = response.content[0].text

            # Parse JSON (Claude may wrap in markdown)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            extracted_car_prefs = json.loads(response_text)

            # Build CarPreferences TypedDict
            car_preferences: CarPreferences = {
                "make": extracted_car_prefs.get("make"),
                "model": extracted_car_prefs.get("model"),
                "fuel_type": extracted_car_prefs.get("fuel_type"),
                "min_price": extracted_car_prefs.get("min_price"),
                "max_price": extracted_car_prefs.get("max_price"),
                "max_mileage": extracted_car_prefs.get("max_mileage"),
                "min_year": extracted_car_prefs.get("min_year"),
                "transmission": extracted_car_prefs.get("transmission"),
                "body_type": extracted_car_prefs.get("body_type"),
                "preferred_color": extracted_car_prefs.get("preferred_color")
            }

            # Calculate extraction confidence
            confidence = self._calculate_confidence(car_preferences)

            # Build output (AUTOMOTIVE DOMAIN - NO JOB/SALARY FIELDS!)
            extraction_output: ExtractionOutput = {
                "car_preferences": car_preferences,
                "extraction_confidence": confidence
            }

            # Token usage from API response
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
                "total": response.usage.input_tokens + response.usage.output_tokens
            }

            # Calculate cost
            cost_usd = self._calculate_cost(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )

            logger.info(
                "✅ Car preference extraction complete",
                extra={
                    "confidence": confidence,
                    "extracted_fields": len([v for v in car_preferences.values() if v]),
                    "cost_usd": cost_usd,
                    "make": car_preferences.get("make"),
                    "model": car_preferences.get("model"),
                    "fuel_type": car_preferences.get("fuel_type")
                }
            )

            return {
                "output": extraction_output,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd
            }

        except json.JSONDecodeError as e:
            logger.error(
                f"❌ JSON parsing failed: {e}",
                extra={"response_text": response_text[:200]}
            )
            return self._empty_extraction()

        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}", exc_info=True)
            return self._empty_extraction()

    def _build_extraction_prompt(self, state: ConversationState) -> str:
        """
        Build extraction prompt with conversation context.

        Args:
            state: Current conversation state

        Returns:
            Formatted extraction prompt
        """
        message_parts = []

        # Add conversation history for context
        history = state.get("conversation_history", [])
        if history:
            message_parts.append("**Gesprekshistorie:**")
            for msg in history[-3:]:  # Last 3 messages
                role = "Klant" if msg["role"] == "user" else "Assistent"
                content = msg["content"]
                message_parts.append(f"{role}: {content}")
            message_parts.append("")

        # Add current message
        message_parts.append("**Huidig bericht om te extraheren:**")
        message_parts.append(state["content"])

        # Add intent hint
        router_output = state.get("router_output", {})
        if router_output:
            intent = router_output.get("intent")
            message_parts.append("")
            message_parts.append(f"**Intent:** {intent}")
            message_parts.append("(Focus extractie op auto-voorkeuren relevant voor deze intent)")

        return "\n".join(message_parts)

    def _empty_extraction(self) -> Dict[str, Any]:
        """
        Return empty extraction output for fallback scenarios.

        Returns:
            Dict with empty ExtractionOutput and zero costs
        """
        extraction_output: ExtractionOutput = {
            "car_preferences": None,
            "extraction_confidence": 0.0
        }

        return {
            "output": extraction_output,
            "tokens_used": {
                "input": 0,
                "output": 0,
                "total": 0
            },
            "cost_usd": 0.0
        }

    def _calculate_confidence(self, car_prefs: CarPreferences) -> float:
        """
        Calculate extraction confidence based on filled fields.

        Args:
            car_prefs: Extracted car preferences

        Returns:
            Confidence score 0.0-1.0
        """
        # Count total possible fields and filled fields
        total_fields = 10  # make, model, fuel_type, min_price, max_price, max_mileage, min_year, transmission, body_type, preferred_color
        filled_fields = sum([
            car_prefs.get("make") is not None,
            car_prefs.get("model") is not None,
            car_prefs.get("fuel_type") is not None,
            car_prefs.get("min_price") is not None,
            car_prefs.get("max_price") is not None,
            car_prefs.get("max_mileage") is not None,
            car_prefs.get("min_year") is not None,
            car_prefs.get("transmission") is not None,
            car_prefs.get("body_type") is not None,
            car_prefs.get("preferred_color") is not None
        ])

        # Calculate confidence (at least 0.2 if any fields filled)
        if filled_fields == 0:
            return 0.1  # Low confidence if nothing extracted

        confidence = filled_fields / total_fields
        return max(0.2, min(1.0, confidence))  # Clamp between 0.2 and 1.0
