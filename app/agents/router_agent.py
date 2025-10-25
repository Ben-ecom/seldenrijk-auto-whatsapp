"""
Router Agent - Intent classification and priority detection.

Uses Claude 3.5 Sonnet for fast, accurate classification of incoming messages.
Determines:
- User intent (job_search, salary_inquiry, complaint, etc.)
- Priority level (high, medium, low)
- Whether extraction is needed
- Whether to escalate to human

Output schema matches RouterOutput TypedDict from state.py.
"""
import json
from typing import Dict, Any
from anthropic import Anthropic

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import ConversationState, RouterOutput
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


# ============ ROUTER PROMPT ============

ROUTER_SYSTEM_PROMPT = """You are an intent classification expert for Seldenrijk Auto's WhatsApp customer service.

Your job is to analyze incoming messages and classify them into the correct intent category.

**Intent Categories:**
- car_inquiry: Questions about specific cars, models, availability, features
- showroom_info: Questions about opening hours, location, directions, contact info
- appointment: Request to schedule test drive, viewing, or meeting
- financing: Questions about financing, leasing, payment plans
- service_maintenance: Questions about car service, repairs, maintenance
- trade_in: Questions about trading in their current car
- complaint: Customer is unhappy, frustrated, or complaining about service
- general_inquiry: General questions about the dealership or cars
- unclear: Cannot determine intent from message

**Priority Levels:**
- high: Complaint, urgent service issue, hot lead ready to buy
- medium: Car inquiry, appointment request, financing questions
- low: General browsing, showroom info requests

**Extraction Needed:**
Set to true if message contains structured data like:
- Car preferences (brand, model, type, budget)
- Contact information (name, email, phone)
- Appointment preferences (date, time)
- Trade-in details (current car make/model/year)

**Escalate to Human:**
Set to true ONLY if:
- Intent is "complaint"
- User explicitly asks for a human agent
- Message is very sensitive or emotional
- Message is threatening or abusive

**DO NOT escalate** for:
- General questions (showroom hours, location, etc.) - AI can answer these
- Car inquiries - AI can provide information
- Appointment requests - AI can handle scheduling

**Output Format (JSON only):**
{
    "intent": "car_inquiry" | "showroom_info" | "appointment" | "financing" | "service_maintenance" | "trade_in" | "complaint" | "general_inquiry" | "unclear",
    "priority": "high" | "medium" | "low",
    "needs_extraction": true | false,
    "escalate_to_human": true | false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification"
}

**Examples:**

User: "Wat zijn de openingstijden van jullie showroom?"
Output:
{
    "intent": "showroom_info",
    "priority": "low",
    "needs_extraction": false,
    "escalate_to_human": false,
    "confidence": 0.95,
    "reasoning": "Customer asking about showroom hours - AI can answer this"
}

User: "Hebben jullie een BMW X5 beschikbaar?"
Output:
{
    "intent": "car_inquiry",
    "priority": "medium",
    "needs_extraction": true,
    "escalate_to_human": false,
    "confidence": 0.98,
    "reasoning": "Customer asking about specific car model availability"
}

User: "Ik wil graag een proefrit inplannen"
Output:
{
    "intent": "appointment",
    "priority": "medium",
    "needs_extraction": true,
    "escalate_to_human": false,
    "confidence": 0.97,
    "reasoning": "Customer requesting test drive appointment"
}

User: "Dit is onacceptabel! Ik wacht al 3 weken op een reactie!"
Output:
{
    "intent": "complaint",
    "priority": "high",
    "escalate_to_human": true,
    "confidence": 0.98,
    "reasoning": "Strong negative sentiment, frustration, requires human intervention"
}

User: "Hoi"
Output:
{
    "intent": "unclear",
    "priority": "low",
    "needs_extraction": false,
    "escalate_to_human": false,
    "confidence": 0.6,
    "reasoning": "Greeting with no clear intent, needs follow-up"
}

**Important:**
- ONLY output valid JSON
- Always include confidence score (0.0-1.0)
- Be concise in reasoning (1-2 sentences max)
- Consider conversation history if provided
"""


class RouterAgent(BaseAgent):
    """
    Router Agent for intent classification using Claude 3.5 Sonnet.

    Fast and accurate classification with prompt caching:
    - ~200 input tokens + ~100 output tokens per message
    - Prompt caching reduces costs by 90% after warmup
    - Latency: ~400ms average
    """

    def __init__(self):
        """Initialize Router Agent with Claude 3.5 Sonnet configuration."""
        config = AGENT_CONFIGS["router"]

        super().__init__(
            agent_name="router",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client
        self.client = Anthropic(**config["config"])
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.enable_prompt_caching = config.get("enable_prompt_caching", False)

        logger.info(f"✅ Router Agent initialized with Claude (caching: {self.enable_prompt_caching})")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute router agent to classify intent.

        Args:
            state: Current conversation state

        Returns:
            Dict with RouterOutput and metadata:
            {
                "output": RouterOutput dict,
                "tokens_used": {...},
                "cost_usd": 0.0001,
                "latency_ms": 250
            }
        """
        # Build user message with context
        user_message = self._build_user_message(state)

        logger.info(
            "🔀 Router classifying message",
            extra={
                "message_id": state["message_id"],
                "message_preview": state["content"][:100],
                "has_history": len(state.get("conversation_history", [])) > 0
            }
        )

        # Build system message with prompt caching
        system_messages = []
        if self.enable_prompt_caching:
            # Mark system prompt for caching (large, static prompt)
            system_messages.append({
                "type": "text",
                "text": ROUTER_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            })
        else:
            system_messages.append({
                "type": "text",
                "text": ROUTER_SYSTEM_PROMPT
            })

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            system=system_messages,
            messages=[
                {"role": "user", "content": user_message}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        # Parse response - Claude returns text in content blocks
        output_text = response.content[0].text

        # Extract JSON from response (Claude may wrap it in markdown)
        if "```json" in output_text:
            output_text = output_text.split("```json")[1].split("```")[0].strip()
        elif "```" in output_text:
            output_text = output_text.split("```")[1].split("```")[0].strip()

        router_output: RouterOutput = json.loads(output_text)

        # Token usage (Claude format)
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0)
        }

        # Calculate cost (including cache tokens)
        cost_usd = self._calculate_cost(
            input_tokens=tokens_used["input"],
            output_tokens=tokens_used["output"],
            cache_read_tokens=tokens_used["cache_read"],
            cache_write_tokens=tokens_used["cache_write"]
        )

        logger.info(
            "✅ Router classification complete",
            extra={
                "intent": router_output["intent"],
                "priority": router_output["priority"],
                "needs_extraction": router_output["needs_extraction"],
                "escalate": router_output["escalate_to_human"],
                "confidence": router_output["confidence"],
                "tokens": tokens_used["total"],
                "cost_usd": cost_usd
            }
        )

        return {
            "output": router_output,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }

    def _build_user_message(self, state: ConversationState) -> str:
        """
        Build user message with conversation context.

        Args:
            state: Current conversation state

        Returns:
            Formatted message for GPT-4o-mini
        """
        message_parts = []

        # Add conversation history if available
        history = state.get("conversation_history", [])
        if history:
            message_parts.append("**Conversation History:**")
            for msg in history[-5:]:  # Last 5 messages for context
                role = msg["role"].capitalize()
                content = msg["content"]
                message_parts.append(f"{role}: {content}")
            message_parts.append("")  # Blank line

        # Add current message
        message_parts.append("**Current Message:**")
        message_parts.append(state["content"])

        # Add sender info
        message_parts.append("")
        sender_name = state.get('sender_name', 'Customer')
        message_parts.append(f"**Sender:** {sender_name} ({state['sender_phone']})")

        # Add previous intents if available
        prev_intents = state.get("previous_intents", [])
        if prev_intents:
            message_parts.append(f"**Previous Intents:** {', '.join(prev_intents[-3:])}")

        return "\n".join(message_parts)
