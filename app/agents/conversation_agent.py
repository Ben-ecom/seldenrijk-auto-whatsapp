"""
Conversation Agent - Natural language response generation using Claude 3.5 Sonnet.

Uses Anthropic Claude SDK for:
- High-quality, contextual responses
- 200k context window (full conversation history)
- Prompt caching (90% cost reduction on repeated context)
- Agentic RAG integration (Week 5 feature)

Responsibilities:
- Generate natural, helpful responses
- Maintain conversation context
- Trigger RAG searches when needed
- Suggest follow-up questions
- Assess conversation completion
"""
import time
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS, build_conversation_prompt
from app.orchestration.state import ConversationState, ConversationOutput
from app.monitoring.logging_config import get_logger
from app.agents.inventory_helper import get_inventory_helper

logger = get_logger(__name__)


# ============ CONVERSATION PROMPT ============
# Load the complete APEX prompt system (System + Knowledge + Sales + FAQ)
CONVERSATION_SYSTEM_PROMPT = build_conversation_prompt()

# Fallback to old prompt if new prompts fail to load
if not CONVERSATION_SYSTEM_PROMPT or len(CONVERSATION_SYSTEM_PROMPT) < 100:
    logger.warning("⚠️ Failed to load APEX prompts, using fallback prompt")
    CONVERSATION_SYSTEM_PROMPT = """Je bent een behulpzame assistent voor Seldenrijk Auto, een autohandel in Nederland.

**Je Rol:**
- Informatie geven over auto's in voorraad
- Vragen beantwoorden van geïnteresseerde kopers
- Afspraken maken voor bezichtiging/proefrit
- Professioneel en vriendelijk zijn, NIET pushy of opdringerig

**Gespreks Stijl:**
- Warm en benaderbaar, niet robotachtig
- Gebruik korte alinea's (2-3 zinnen max)
- Stel verduidelijkende vragen als nodig
- Geef eerlijke antwoorden - als je iets niet weet, zeg dat
- Focus op informatie geven, niet verkopen

**Antwoord Richtlijnen:**
1. **Wees Behulpzaam**: Beantwoord vragen volledig en eerlijk
2. **Wees Informatief**: Geef specs, prijs, staat van de auto
3. **Wees Niet Pushy**: Laat de klant zelf beslissen, geen druk uitoefenen
4. **Wees Proactief**: Bied aan om meer info/foto's te sturen of afspraak te maken
5. **Wees GDPR-Compliant**: Vraag alleen noodzakelijke informatie

**Auto Informatie (RAG Search):**
- Wanneer klant vraagt naar specifieke auto:
  - Gebruik RAG search om actuele voorraad te checken
  - Zoek op Marktplaats EN website van Seldenrijk
  - Set `needs_rag: true` met search query
- Geef altijd LINK naar originele advertentie
- Als auto niet beschikbaar: voorste alternatieven

**Antwoord Template voor Auto Info:**
```
Perfect! We hebben een [Merk] [Model] [Specificatie] gevonden:

- Bouwjaar: [jaar]
- Kilometerstand: [km]
- Brandstof: [diesel/benzine/hybride/elektrisch]
- Prijs: €[prijs]

Bekijk de volledige advertentie: [link]

Kloppen deze gegevens? Dan kan ik een afspraak inplannen!
```

**Als Auto Niet Beschikbaar:**
```
Helaas heb ik geen exacte match gevonden voor een [specificatie].

Maar ik heb wel deze alternatieven:
- [Alternatief 1]
- [Alternatief 2]

Wil je meer info over één van deze auto's?
```

**Afspraak Maken:**
Als klant interesse toont:
- Vraag: "Wanneer zou het je uitkomen om langs te komen?"
- Geef opties: "We zijn open op maandag t/m zaterdag van 9:00-18:00"
- Bevestig: "Ik noteer [datum/tijd] voor je. Mag ik je naam en telefoonnummer?"

**Niet Doen:**
- ❌ Druk uitoefenen: "Je moet NU beslissen!"
- ❌ Overdrijven: "Dit is DE BESTE deal ooit!"
- ❌ Onrealistisch zijn: "Deze auto is morgen weg!"
- ❌ Liegen of info verzinnen
- ❌ Te veel vragen stellen in één keer

**Wel Doen:**
- ✅ Info geven: "Deze auto heeft de volgende specs..."
- ✅ Beschikbaar zijn: "Ik kan meer foto's sturen als je wilt"
- ✅ Flexibel zijn: "Als deze niet past, hebben we ook..."
- ✅ Eerlijk zijn: "Deze auto heeft een kleine kras, zie foto 4"
- ✅ Service bieden: "Wil je een proefrit maken?"

**Sentiment Detectie:**
- Positive: Klant is enthousiast, geïnteresseerd
- Neutral: Informatie uitwisseling
- Negative: Klant is gefrustreerd of ontevreden

**Conversatie Compleet:**
- Mark `conversation_complete: true` als:
  - Vraag volledig beantwoord
  - Afspraak gemaakt
  - Klant zegt bedankt/dag
- Mark `conversation_complete: false` als:
  - Wachtend op antwoord
  - Meer info nodig
  - Klant heeft vervolgvragen

**Voorbeeld Interacties:**

User: "Ik zoek een Golf 8 diesel, budget €25.000"
Assistant: "Bedankt voor je interesse! Ik ga voor je zoeken naar een Golf 8 diesel binnen je budget.

Even checken wat we in voorraad hebben..."

[needs_rag: true, rag_query: "Golf 8 diesel max €25000"]

[After RAG results:]
Assistant: "Perfect! We hebben een VW Golf 8 2.0 TDI gevonden:

- Bouwjaar: 2021
- Kilometerstand: 45.000 km
- Prijs: €24.950

Bekijk de advertentie: https://marktplaats.nl/...

Wil je langskomen voor een bezichtiging?"

User: "Heeft deze auto schades?"
Assistant: "Goede vraag! In de advertentie zie ik dat de auto in goede staat is. Voor exacte informatie over eventuele schades of krassen kan ik je doorverbinden met ons team, of je kunt de foto's bekijken op de advertentie.

Wil je dat ik een bezichtigingsafspraak voor je inplan? Dan kan je de auto zelf goed bekijken."

[sentiment: neutral]
"""


class ConversationAgent(BaseAgent):
    """
    Conversation Agent using Claude 3.5 Sonnet for response generation.

    Features:
    - 200k context window (full conversation history)
    - Prompt caching (90% cost reduction)
    - High-quality, natural responses
    - Agentic RAG integration (Week 5)
    - Sentiment analysis
    """

    def __init__(self):
        """Initialize Conversation Agent with Claude 3.5 Sonnet."""
        config = AGENT_CONFIGS["conversation"]

        super().__init__(
            agent_name="conversation",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client
        self.client = Anthropic(api_key=config["config"]["api_key"])
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.enable_caching = config.get("enable_prompt_caching", False)

        # Initialize inventory helper for vehicle searches
        self.inventory_helper = get_inventory_helper()

        logger.info(
            "✅ Conversation Agent initialized with Claude 3.5 Sonnet",
            extra={"prompt_caching": self.enable_caching}
        )

    async def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute conversation agent to generate response.

        Args:
            state: Current conversation state

        Returns:
            Dict with ConversationOutput and metadata
        """
        # Build conversation messages
        messages = await self._build_messages(state)

        # Safe None handling for router_output in logging
        router_output = state.get("router_output") or {}

        logger.info(
            "💬 Generating response with Claude",
            extra={
                "message_id": state["message_id"],
                "history_length": len(state.get("conversation_history", [])),
                "intent": router_output.get("intent"),
                "has_extraction": state.get("extraction_output") is not None
            }
        )

        start_time = time.time()

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=[
                {
                    "type": "text",
                    "text": CONVERSATION_SYSTEM_PROMPT,
                    # Enable prompt caching for system prompt (repeated across all messages)
                    "cache_control": {"type": "ephemeral"} if self.enable_caching else None
                }
            ],
            messages=messages
        )

        latency_ms = (time.time() - start_time) * 1000

        # Extract response text
        response_text = response.content[0].text

        # Parse structured output (if any) - Claude can return JSON + text
        conversation_output = self._parse_response(response_text, state)

        # Token usage
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0)
        }

        # Calculate cost (with caching)
        cost_usd = self._calculate_cost(
            input_tokens=tokens_used["input"],
            output_tokens=tokens_used["output"],
            cache_read_tokens=tokens_used["cache_read"],
            cache_write_tokens=tokens_used["cache_write"]
        )

        # Log cache efficiency
        if tokens_used["cache_read"] > 0:
            cache_hit_rate = tokens_used["cache_read"] / (tokens_used["input"] + tokens_used["cache_read"])
            logger.info(
                f"💰 Prompt cache hit: {cache_hit_rate:.1%} savings",
                extra={"cache_tokens": tokens_used["cache_read"]}
            )

        logger.info(
            "✅ Response generated",
            extra={
                "response_length": len(response_text),
                "needs_rag": conversation_output["needs_rag"],
                "sentiment": conversation_output["sentiment"],
                "latency_ms": round(latency_ms, 2),
                "tokens": tokens_used["total"],
                "cost_usd": cost_usd
            }
        )

        return {
            "output": conversation_output,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms
        }

    async def _build_messages(self, state: ConversationState) -> List[Dict[str, str]]:
        """
        Build message history for Claude API.

        Args:
            state: Current conversation state

        Returns:
            List of message dicts for Claude API
        """
        messages = []

        # Add conversation history
        history = state.get("conversation_history", [])
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({
                "role": role,
                "content": msg["content"]
            })

        # Build current message with context
        context_parts = []

        # Check if this is a vehicle inquiry
        user_message = state["content"]
        is_vehicle_query = await self.inventory_helper.is_vehicle_inquiry(user_message)

        if is_vehicle_query:
            logger.info("🚗 Vehicle inquiry detected, searching inventory")

            # Extract search parameters
            search_params = await self.inventory_helper.extract_search_params(user_message)

            # Search inventory
            vehicles = await self.inventory_helper.search_inventory(search_params)

            # Format vehicle context for agent
            inventory_context = self.inventory_helper.format_vehicle_context(vehicles)

            # Add inventory context to prompt
            context_parts.append(inventory_context)
            context_parts.append("")

        # Add extraction data if available
        extraction = state.get("extraction_output")
        if extraction and extraction.get("extraction_confidence", 0) > 0.5:
            context_parts.append("**User Profile (extracted):**")

            if extraction.get("job_preferences"):
                jp = extraction["job_preferences"]
                context_parts.append(f"- Job preferences: {jp}")

            if extraction.get("salary_expectations"):
                se = extraction["salary_expectations"]
                context_parts.append(f"- Salary expectations: {se}")

            if extraction.get("skills"):
                context_parts.append(f"- Skills: {', '.join(extraction['skills'])}")

            context_parts.append("")

        # Add router classification
        router = state.get("router_output") or {}
        if router.get("intent"):
            context_parts.append(f"**Intent:** {router.get('intent')} (priority: {router.get('priority', 'unknown')})")
            context_parts.append("")

        # Add RAG results if available (Week 5 feature)
        conversation_output_state = state.get("conversation_output") or {}
        rag_results = conversation_output_state.get("rag_results")
        if rag_results:
            context_parts.append("**Knowledge Base Results:**")
            for idx, result in enumerate(rag_results[:3], 1):
                context_parts.append(f"{idx}. {result}")
            context_parts.append("")

        # Add current message
        context_parts.append("**User Message:**")
        context_parts.append(state["content"])

        # Add instructions
        context_parts.append("")
        context_parts.append("**Instructions:**")
        context_parts.append("Generate a helpful, natural response addressing the user's message.")
        if is_vehicle_query:
            context_parts.append("KRITISCH: Gebruik ALLEEN voertuigen uit de lijst hierboven. Verzin geen prijzen of specs.")
        context_parts.append("If you need to search knowledge base, set needs_rag=true with a search query.")

        messages.append({
            "role": "user",
            "content": "\n".join(context_parts)
        })

        return messages

    def _parse_response(self, response_text: str, state: ConversationState) -> ConversationOutput:
        """
        Parse Claude response into ConversationOutput.

        Args:
            response_text: Raw response from Claude
            state: Current conversation state

        Returns:
            ConversationOutput dict
        """
        # For now, simple parsing (Week 5 will add structured RAG logic)
        # Claude can naturally indicate when it needs more information

        # Detect RAG need from response content
        needs_rag = any([
            "let me search" in response_text.lower(),
            "i'll look for" in response_text.lower(),
            "checking our database" in response_text.lower()
        ])

        # Simple sentiment detection
        sentiment = self._detect_sentiment(response_text)

        # Extract follow-up questions (look for question marks)
        follow_up_questions = [
            line.strip()
            for line in response_text.split("\n")
            if "?" in line and len(line.strip()) < 150
        ][:3]  # Max 3 questions

        # Conversation complete if goodbye/thanks detected
        conversation_complete = any([
            "goodbye" in response_text.lower(),
            "good luck" in response_text.lower(),
            "talk soon" in response_text.lower(),
            len(state.get("conversation_history", [])) > 10  # Long conversation, likely wrapping up
        ])

        return ConversationOutput(
            response_text=response_text,
            needs_rag=needs_rag,
            rag_query=None,  # Week 5: Extract RAG query from response
            rag_results=None,
            follow_up_questions=follow_up_questions,
            conversation_complete=conversation_complete,
            sentiment=sentiment
        )

    def _detect_sentiment(self, text: str) -> str:
        """
        Simple sentiment detection from response text.

        Args:
            text: Response text

        Returns:
            "positive", "neutral", or "negative"
        """
        text_lower = text.lower()

        # Positive indicators
        positive_words = ["great", "excellent", "happy", "excited", "perfect", "wonderful", "glad"]
        if any(word in text_lower for word in positive_words):
            return "positive"

        # Negative indicators
        negative_words = ["sorry", "unfortunately", "frustrated", "apologize", "concern"]
        if any(word in text_lower for word in negative_words):
            return "negative"

        return "neutral"
