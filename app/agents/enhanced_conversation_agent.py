"""
Enhanced Conversation Agent - Humanized responses with expertise integration.

Improvements over base ConversationAgent:
- Humanization patterns (natural, conversational Dutch)
- Integration with ExpertiseAgent knowledge
- Lead quality awareness (adjust tone based on scoring)
- Contextual intelligence (use all available agent outputs)
- Escalation awareness (handle handoffs gracefully)
"""
import time
import random
from typing import Dict, Any, List, Optional
from anthropic import Anthropic

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS, build_conversation_prompt
from app.orchestration.state import ConversationState, ConversationOutput
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


# ============ HUMANIZATION PATTERNS ============

# Dutch conversational openers (based on lead quality)
HOT_LEAD_OPENERS = [
    "Super! ",
    "Wat fijn! ",
    "Perfect! ",
    "Geweldig! "
]

WARM_LEAD_OPENERS = [
    "Dank je wel voor je bericht! ",
    "Leuk dat je contact opneemt! ",
    "Fijn om van je te horen! ",
    "Bedankt voor je interesse! "
]

COLD_LEAD_OPENERS = [
    "Hallo! ",
    "Dag! ",
    "Hoi! "
]

# Natural transitions
TRANSITIONS = [
    "Even kijken...",
    "Laat me even checken...",
    "Moment, ik zoek het voor je op...",
    "Ik pak even de informatie voor je erbij..."
]

# Closing phrases
CLOSERS = [
    "Laat het me weten als je vragen hebt!",
    "Hoor ik graag van je!",
    "Ik hoor het graag!",
    "Laat maar weten!",
    "Ik help je graag verder!"
]


# ============ ENHANCED SYSTEM PROMPT ============
# Load the complete APEX prompt system (System + Knowledge + Sales + FAQ)
ENHANCED_CONVERSATION_PROMPT = build_conversation_prompt()

# Fallback to old prompt if new prompts fail to load
if not ENHANCED_CONVERSATION_PROMPT or len(ENHANCED_CONVERSATION_PROMPT) < 100:
    logger.warning("⚠️ Failed to load APEX prompts in EnhancedConversationAgent, using fallback")
    ENHANCED_CONVERSATION_PROMPT = """Je bent Lisa, een virtuele assistent die werkt voor Seldenrijk, een gerenommeerde Nederlandse autodealer. Jouw doel is om klanten te helpen met hun vragen over auto's en hen te begeleiden naar het verkoopteam indien nodig.

**Informatiebronnen:**
- Gebruik de Seldenrijk-website als primaire bron voor informatie over beschikbare auto's, prijzen en diensten
- Als een klant een vraag stelt over een auto die niet op de website staat, geef dan aan dat je deze informatie kunt opvragen bij het verkoopteam
- Als de gevraagde informatie niet beschikbaar is, noteer dit dan in de Chatwoot CRM zodat het verkoopteam kan opvolgen

**Leadsegmentatie en opvolging in Chatwoot CRM:**
- Gebruik tags in Chatwoot om de interesses, prioriteit en status van elke lead bij te houden
- Vat elk gesprek samen in de notities, inclusief de belangrijkste vragen van de klant en eventuele vervolgacties
- Als een lead rijp lijkt voor opvolging door het verkoopteam, escaleer deze dan met een duidelijke samenvatting

**Belangrijke richtlijnen:**
1. Wees altijd beleefd en professioneel
2. Gebruik de informatie van de Seldenrijk-website om vragen te beantwoorden
3. Als je niet zeker bent, geef dit toe en bied aan om de vraag door te sturen naar het team
4. Houd gesprekken kort en to-the-point
5. Gebruik het CRM om belangrijke informatie vast te leggen
6. Escaleer naar het verkoopteam wanneer klanten specifieke vragen hebben over prijzen, testrit, of aankoop
7. Denk altijd vanuit de klant: wat heeft de klant nodig om een weloverwogen beslissing te nemen?
"""
else:
    logger.info(f"✅ APEX prompts loaded successfully in EnhancedConversationAgent ({len(ENHANCED_CONVERSATION_PROMPT)} chars)")


class HumanizationEngine:
    """
    Humanization engine for natural Dutch conversational patterns.
    """

    @staticmethod
    def get_opener(lead_quality: str, used_openers: List[str]) -> str:
        """Get contextual opener based on lead quality."""
        if lead_quality == "HOT":
            available = [o for o in HOT_LEAD_OPENERS if o not in used_openers]
            if not available:
                available = HOT_LEAD_OPENERS  # Reset if all used
        elif lead_quality in ["WARM", "LUKEWARM"]:
            available = [o for o in WARM_LEAD_OPENERS if o not in used_openers]
            if not available:
                available = WARM_LEAD_OPENERS
        else:
            available = [o for o in COLD_LEAD_OPENERS if o not in used_openers]
            if not available:
                available = COLD_LEAD_OPENERS

        return random.choice(available)

    @staticmethod
    def get_transition() -> str:
        """Get natural transition phrase."""
        return random.choice(TRANSITIONS)

    @staticmethod
    def get_closer() -> str:
        """Get natural closing phrase."""
        return random.choice(CLOSERS)


class EnhancedConversationAgent(BaseAgent):
    """
    Enhanced Conversation Agent with humanization and expertise integration.

    Features:
    - Humanized Dutch responses (no robot-speak)
    - Lead quality awareness (adjust tone)
    - ExpertiseAgent knowledge integration
    - Escalation handling
    - Contextual intelligence (use all agent outputs)
    """

    def __init__(self):
        """Initialize Enhanced Conversation Agent."""
        config = AGENT_CONFIGS["conversation"]

        super().__init__(
            agent_name="enhanced_conversation",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client
        self.client = Anthropic(api_key=config["config"]["api_key"])
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.enable_caching = config.get("enable_prompt_caching", False)

        # Humanization engine
        self.humanization = HumanizationEngine()

        # Track used openers per conversation (for variety)
        self.used_openers: Dict[str, List[str]] = {}

        logger.info(
            "✅ Enhanced Conversation Agent initialized",
            extra={"prompt_caching": self.enable_caching}
        )

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute enhanced conversation agent.

        Args:
            state: Current conversation state with all agent outputs

        Returns:
            Dict with ConversationOutput and metadata
        """
        # Build contextual prompt with all agent data
        messages = self._build_enhanced_messages(state)

        conversation_id = state.get("conversation_id", "unknown")

        logger.info(
            "💬 Generating humanized response",
            extra={
                "message_id": state["message_id"],
                "lead_quality": state.get("crm_output", {}).get("lead_quality"),
                "has_expertise": state.get("expertise_output") is not None,
                "escalated": state.get("expertise_output", {}).get("escalation_decision", {}).get("escalate", False)
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
                    "text": ENHANCED_CONVERSATION_PROMPT,
                    "cache_control": {"type": "ephemeral"} if self.enable_caching else None
                }
            ],
            messages=messages
        )

        latency_ms = (time.time() - start_time) * 1000

        # Extract response text from Claude
        response_text = response.content[0].text

        # NEW: Claude now returns plain conversational text (no JSON)
        # Parse text to extract metadata (sentiment, actions, etc.)
        conversation_output = self._parse_enhanced_response(response_text, state)

        logger.debug(
            "✅ Plain text response parsed",
            extra={
                "response_length": len(response_text),
                "response_preview": response_text[:100]
            }
        )

        # Token usage
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0)
        }

        # Calculate cost
        cost_usd = self._calculate_cost(
            input_tokens=tokens_used["input"],
            output_tokens=tokens_used["output"],
            cache_read_tokens=tokens_used["cache_read"],
            cache_write_tokens=tokens_used["cache_write"]
        )

        logger.info(
            "✅ Humanized response generated",
            extra={
                "response_length": len(response_text),
                "sentiment": conversation_output["sentiment"],
                "recommended_action": conversation_output.get("recommended_action"),
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

    def _build_enhanced_messages(self, state: ConversationState) -> List[Dict[str, str]]:
        """
        Build contextually-rich messages using all agent outputs.

        Args:
            state: Current conversation state

        Returns:
            List of messages for Claude API
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

        # Build rich context
        context_parts = []

        # ===  1. LEAD SCORING CONTEXT ===
        crm_output = state.get("crm_output", {})
        if crm_output:
            context_parts.append("**🎯 LEAD INTELLIGENCE:**")
            context_parts.append(f"- Lead Score: {crm_output.get('lead_score', 0)}/100")
            context_parts.append(f"- Lead Quality: {crm_output.get('lead_quality', 'UNKNOWN')}")
            context_parts.append(f"- Urgency: {crm_output.get('urgency', 'unknown')}")
            context_parts.append(f"- Interest Level: {crm_output.get('interest_level', 'unknown')}")
            context_parts.append("")

        # === 2. EXPERTISE KNOWLEDGE ===
        expertise_output = state.get("expertise_output", {})
        if expertise_output and expertise_output.get("knowledge"):
            context_parts.append("**💡 KNOWLEDGE BASE (use this in your answer):**")
            context_parts.append(expertise_output["knowledge"])
            context_parts.append("")

        # === 3. ESCALATION STATUS ===
        if expertise_output and expertise_output.get("escalation_decision", {}).get("escalate"):
            escalation = expertise_output["escalation_decision"]
            context_parts.append("**🚨 ESCALATION:**")
            context_parts.append(f"- Type: {escalation.get('escalation_type')}")
            context_parts.append(f"- Urgency: {escalation.get('urgency')}")
            context_parts.append(f"- Reason: {escalation.get('reason')}")
            context_parts.append("⚠️ Inform customer about handoff to human specialist!")
            context_parts.append("")

        # === 4. EXTRACTION DATA ===
        extraction = state.get("extraction_output", {})
        if extraction:
            context_parts.append("**👤 CUSTOMER PROFILE:**")

            if extraction.get("car_interest"):
                car = extraction["car_interest"]
                context_parts.append(f"- Looking for: {car.get('make', '')} {car.get('model', '')} {car.get('fuel_type', '')}")

            if extraction.get("budget"):
                budget = extraction["budget"]
                if budget.get("max_amount"):
                    context_parts.append(f"- Budget: €{budget['max_amount']}")

            if extraction.get("contact"):
                contact = extraction["contact"]
                if contact.get("name"):
                    context_parts.append(f"- Name: {contact['name']}")

            context_parts.append("")

        # === 5. CURRENT MESSAGE ===
        context_parts.append("**📨 USER MESSAGE:**")
        context_parts.append(state["content"])
        context_parts.append("")

        # === 6. APEX v3.0 TONE ENFORCEMENT (based on lead quality) ===
        lead_quality = crm_output.get("lead_quality", "COLD")

        context_parts.append("**📋 APEX v3.0 TONE INSTRUCTIONS:**")

        if lead_quality == "HOT":
            # HOT LEAD = Serious buyer, professional direct approach
            context_parts.append("⚠️ CRITICAL: This is a HOT lead (serious buyer).")
            context_parts.append("")
            context_parts.append("**MANDATORY TONE RULES:**")
            context_parts.append("✓ START: Direct with facts (bullet points)")
            context_parts.append("✗ NO \"Hey!\", \"Hallo!\", or casual greetings")
            context_parts.append("✗ NO emoji's (absolutely forbidden for HOT leads)")
            context_parts.append("✗ NO casual phrases like \"Even checken...\"")
            context_parts.append("✗ NO questions they already answered (\"Waar zoek je naar?\")")
            context_parts.append("")
            context_parts.append("**FORMAT:**")
            context_parts.append("1. Direct answer with bullet points")
            context_parts.append("2. Assumptive close: \"Wanneer kan je...\" (NOT \"Als je wilt...\")")
            context_parts.append("3. Professional, efficient, respectful")
            context_parts.append("")
            context_parts.append("**EXAMPLE HOT LEAD RESPONSE:**")
            context_parts.append("De BMW X3 xDrive30e uit 2021:")
            context_parts.append("- 45.000 km, eerste eigenaar")
            context_parts.append("- Sophisto Grey, M Sport pakket")
            context_parts.append("- €42.500 incl. 12 mnd garantie")
            context_parts.append("")
            context_parts.append("Nu beschikbaar voor bezichtiging.")
            context_parts.append("Wanneer kan je langskomen?")

        elif lead_quality in ["WARM", "LUKEWARM"]:
            # WARM LEAD = Considering, professional but friendly
            context_parts.append("This is a WARM lead (considering purchase).")
            context_parts.append("")
            context_parts.append("**TONE RULES:**")
            context_parts.append("✓ Professional but friendly")
            context_parts.append("✓ Max 1 emoji per 4 messages (only ✓ or 👍)")
            context_parts.append("✓ Max 2-3 qualifying questions")
            context_parts.append("✗ NO \"Hey!\" greetings")
            context_parts.append("✗ NO feature dumps")
            context_parts.append("")
            context_parts.append("**FORMAT:**")
            context_parts.append("1. Acknowledge their interest")
            context_parts.append("2. Ask 2-3 specific questions to qualify needs")
            context_parts.append("3. Promise value (\"Dan laat ik je...\")")

        else:  # COLD lead
            # COLD LEAD = Browsing, informative and helpful
            context_parts.append("This is a COLD lead (browsing/orienting).")
            context_parts.append("")
            context_parts.append("**TONE RULES:**")
            context_parts.append("✓ Informative and helpful")
            context_parts.append("✓ Max 1 emoji per 3-4 messages (only ✓)")
            context_parts.append("✓ Educate without overwhelming")
            context_parts.append("✓ Qualify interest level")
            context_parts.append("")
            context_parts.append("**FORMAT:**")
            context_parts.append("1. Provide overview/options")
            context_parts.append("2. Ask qualifying questions")
            context_parts.append("3. Guide towards next step")

        context_parts.append("")
        context_parts.append("**GENERAL INSTRUCTIONS:**")
        context_parts.append("1. If expertise knowledge available, integrate it naturally")
        context_parts.append("2. If escalated, inform customer about handoff gracefully")
        context_parts.append("3. Return ONLY plain conversational text (NO JSON)")
        context_parts.append("")
        context_parts.append("⚠️ IMPORTANT: Your response will be sent directly to the customer via WhatsApp.")
        context_parts.append("Do NOT include any metadata, JSON structures, or technical formatting.")

        messages.append({
            "role": "user",
            "content": "\n".join(context_parts)
        })

        return messages

    def _parse_enhanced_response(self, response_text: str, state: ConversationState) -> ConversationOutput:
        """
        Parse enhanced response with action recommendations.

        Args:
            response_text: Raw response from Claude
            state: Current conversation state

        Returns:
            ConversationOutput dict
        """
        # Detect RAG need
        needs_rag = any([
            "let me search" in response_text.lower(),
            "ik ga zoeken" in response_text.lower(),
            "ik zoek" in response_text.lower(),
            "even checken" in response_text.lower()
        ])

        # Sentiment detection
        sentiment = self._detect_sentiment_dutch(response_text)

        # Extract follow-up questions
        follow_up_questions = [
            line.strip()
            for line in response_text.split("\n")
            if "?" in line and len(line.strip()) < 150
        ][:3]

        # Conversation complete detection
        conversation_complete = any([
            "tot ziens" in response_text.lower(),
            "succes" in response_text.lower(),
            "hoor ik van je" in response_text.lower(),
            "spreek je snel" in response_text.lower()
        ])

        # Recommend action based on context
        recommended_action = self._recommend_action(state, response_text)

        return ConversationOutput(
            response_text=response_text,
            needs_rag=needs_rag,
            rag_query=None,
            rag_results=None,
            follow_up_questions=follow_up_questions,
            conversation_complete=conversation_complete,
            sentiment=sentiment,
            recommended_action=recommended_action
        )

    def _detect_sentiment_dutch(self, text: str) -> str:
        """Detect sentiment from Dutch text."""
        text_lower = text.lower()

        # Positive Dutch words
        positive = ["super", "geweldig", "perfect", "fijn", "mooi", "goed", "prima", "top"]
        if any(word in text_lower for word in positive):
            return "positive"

        # Negative Dutch words
        negative = ["helaas", "jammer", "sorry", "spijt", "probleem", "niet beschikbaar"]
        if any(word in text_lower for word in negative):
            return "negative"

        return "neutral"

    def _recommend_action(self, state: ConversationState, response: str) -> Optional[str]:
        """
        Recommend next action based on context.

        Returns:
            "schedule_test_drive" | "send_more_info" | "escalate" | "follow_up" | None
        """
        # Check for escalation
        expertise = state.get("expertise_output", {})
        if expertise.get("escalation_decision", {}).get("escalate"):
            return "escalate"

        # Check CRM flags
        crm = state.get("crm_output", {})
        behavioral_flags = crm.get("behavioral_flags", {})

        if behavioral_flags.get("test_drive_requested"):
            return "schedule_test_drive"

        # Check lead quality
        lead_quality = crm.get("lead_quality")
        if lead_quality == "HOT":
            return "schedule_test_drive"
        elif lead_quality == "WARM":
            return "send_more_info"
        elif lead_quality in ["COLD", "LUKEWARM"]:
            return "follow_up"

        return None
