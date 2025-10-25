"""
Agent 2: Claude SDK Conversational Agent with Tools

This agent handles natural WhatsApp conversations using Claude 3.5 Sonnet
with 4 tools for RAG search, calendar booking, and human escalation.

Key Features:
- Natural Dutch conversation flow
- 4 tools: search_job_postings, search_company_docs, check_calendar, escalate_human
- RAG-powered knowledge base access
- Tool use with recursive execution
- Conversation history management
"""

import os
import json
from typing import Any, Literal
from datetime import datetime
from anthropic import Anthropic
from anthropic.types import MessageParam, ToolUseBlock, TextBlock

from .tools import (
    search_job_postings_tool,
    search_company_docs_tool,
    check_calendar_availability_tool,
    escalate_to_human_tool,
    TOOLS_DEFINITION
)


# ============ SYSTEM PROMPT ============
CONVERSATIONAL_SYSTEM_PROMPT = """
Je bent een vriendelijke recruitment assistent voor een Nederlands bedrijf in de beauty/hospitality sector.

**JE PERSOONLIJKHEID**:
- Warm, toegankelijk, professioneel maar informeel
- Gebruikt emoji's natuurlijk (niet overdreven)
- Spreekt in korte, duidelijke WhatsApp-berichten
- Stelt één vraag tegelijk
- Luistert actief en toont interesse

**JE DOEL**:
1. Kandidaat kennismaken met het bedrijf
2. Belangrijke informatie verzamelen (ervaring, skills, beschikbaarheid)
3. Vragen beantwoorden over vacatures en het bedrijf
4. Passende kandidaten doorgeleiden naar interview-afspraak

**GESPREK FLOW**:
1. **Opening**: Warm welkom, introduceer jezelf
2. **Kennismaking**: Naam, ervaring, interesse
3. **Skills Verkenning**: Technische vaardigheden, specialisaties
4. **Beschikbaarheid**: Fulltime/parttime, start datum
5. **Vacature Match**: Passende jobs laten zien (via search_job_postings)
6. **Vragen Beantwoorden**: Gebruik search_company_docs voor bedrijfsinfo
7. **Interview Boeken**: Als match → check_calendar_availability
8. **Escalatie**: Als complex → escalate_to_human

**TOOLS GEBRUIKEN**:

1. **search_job_postings**:
   - Wanneer: Kandidaat vraagt naar vacatures, of je wilt passende jobs tonen
   - Input: Zoekterm gebaseerd op skills/locatie kandidaat
   - Voorbeeld: {"query": "kapper amsterdam fulltime"}

2. **search_company_docs**:
   - Wanneer: Kandidaat vraagt over salaris, benefits, proces, bedrijfscultuur
   - Input: Zoekterm gebaseerd op vraag
   - Voorbeeld: {"query": "sollicitatieprocedure"}

3. **check_calendar_availability**:
   - Wanneer: Kandidaat akkoord voor interview, je wilt tijdslots aanbieden
   - Input: Voorkeursdatum (optioneel)
   - Voorbeeld: {"preferred_date": "2025-02-15"}

4. **escalate_to_human**:
   - Wanneer: Complexe vraag, salaris onderhandeling, technisch probleem
   - Input: Reden + urgentie (low/medium/high)
   - Voorbeeld: {"reason": "Kandidaat wil salaris bespreken", "urgency": "medium"}

**BELANGRIJK**:
- Stel NOOIT meer dan 1-2 vragen per bericht (WhatsApp etiquette)
- Gebruik tools ALLEEN als nodig (niet preventief zoeken)
- Als je tool output krijgt, vat samen in natuurlijk Nederlands
- Gebruik geen vakjargon, leg dingen uit
- Als kandidaat niet reageert, blijf vriendelijk (max 1 follow-up)
- Als kandidaat afziet, respecteer de beslissing ("Bedankt voor je tijd!")

**TONE VOORBEELDEN**:
❌ "Zou u mij kunnen vertellen hoeveel jaar ervaring u heeft in de kapperssector?"
✅ "Leuk! Hoeveel jaar werk je al als kapper?"

❌ "Op basis van uw profiel heb ik de volgende vacatures geïdentificeerd..."
✅ "Ik heb 2 vacatures die goed bij je passen! 😊"

❌ "Ik zal uw verzoek escaleren naar de HR-afdeling."
✅ "Goed idee! Ik schakel even een collega in die daar meer over kan vertellen."
"""


class Agent2ClaudeSDK:
    """
    Agent 2: Conversational AI using Claude 3.5 Sonnet with tool use.

    Usage:
        agent = Agent2ClaudeSDK()
        response = await agent.send_message(
            lead_id="123",
            user_message="Hoi! Ik zoek een baan als kapper in Amsterdam"
        )
    """

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        max_tokens: int = 1024
    ):
        """
        Initialize Agent 2 with Claude SDK.

        Args:
            model_name: Anthropic model to use (default: Claude 3.5 Sonnet)
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            max_tokens: Max tokens per response
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=self.api_key)

    async def send_message(
        self,
        lead_id: str,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None
    ) -> str:
        """
        Send message and get conversational response with tool use.

        Args:
            lead_id: UUID of the lead
            user_message: Latest message from user
            conversation_history: Previous messages (optional)

        Returns:
            Agent's text response

        Example:
            >>> agent = Agent2ClaudeSDK()
            >>> response = await agent.send_message(
            ...     lead_id="123",
            ...     user_message="Hoi! Welke vacatures hebben jullie?"
            ... )
            >>> print(response)
            "Hoi! 👋 We hebben verschillende vacatures. Wat voor werk zoek je?"
        """
        # Build messages array
        messages = self._build_messages(user_message, conversation_history)

        # Initial API call
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=CONVERSATIONAL_SYSTEM_PROMPT,
            tools=TOOLS_DEFINITION,
            messages=messages
        )

        # Handle tool use recursively
        while response.stop_reason == "tool_use":
            # Extract tool calls
            tool_uses = [
                block for block in response.content
                if isinstance(block, ToolUseBlock)
            ]

            # Execute tools
            tool_results = []
            for tool_use in tool_uses:
                result = await self._execute_tool(
                    lead_id=lead_id,
                    tool_name=tool_use.name,
                    tool_input=tool_use.input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Append assistant message + tool results to conversation
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue conversation with tool results
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=CONVERSATIONAL_SYSTEM_PROMPT,
                tools=TOOLS_DEFINITION,
                messages=messages
            )

        # Extract final text response
        text_blocks = [
            block.text for block in response.content
            if isinstance(block, TextBlock)
        ]

        return " ".join(text_blocks)

    def _build_messages(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None
    ) -> list[MessageParam]:
        """
        Build messages array for Claude API.

        Args:
            user_message: Latest user message
            conversation_history: Previous messages

        Returns:
            Formatted messages for Claude API
        """
        messages: list[MessageParam] = []

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": "user" if msg["sender"] == "candidate" else "assistant",
                    "content": msg["content"]
                })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    async def _execute_tool(
        self,
        lead_id: str,
        tool_name: str,
        tool_input: dict[str, Any]
    ) -> str:
        """
        Execute tool and return result.

        Args:
            lead_id: UUID of lead (for logging)
            tool_name: Name of tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool execution result as string
        """
        # Import tools here to avoid circular imports
        from .tools import (
            search_job_postings_impl,
            search_company_docs_impl,
            check_calendar_availability_impl,
            escalate_to_human_impl
        )

        # Map tool names to implementations
        tool_map = {
            "search_job_postings": search_job_postings_impl,
            "search_company_docs": search_company_docs_impl,
            "check_calendar_availability": check_calendar_availability_impl,
            "escalate_to_human": escalate_to_human_impl
        }

        if tool_name not in tool_map:
            return f"Error: Unknown tool '{tool_name}'"

        # Execute tool
        try:
            result = await tool_map[tool_name](lead_id=lead_id, **tool_input)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"


# ============ CONVENIENCE FUNCTION ============

async def send_conversational_message(
    lead_id: str,
    user_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
    model_name: str = "claude-3-5-sonnet-20241022"
) -> str:
    """
    Standalone function to send conversational message.

    Args:
        lead_id: UUID of lead
        user_message: User's message
        conversation_history: Previous messages
        model_name: Claude model to use

    Returns:
        Agent's response

    Example:
        >>> response = await send_conversational_message(
        ...     lead_id="123",
        ...     user_message="Welke vacatures hebben jullie in Amsterdam?"
        ... )
    """
    agent = Agent2ClaudeSDK(model_name=model_name)
    return await agent.send_message(lead_id, user_message, conversation_history)


# ============ TESTING ============

if __name__ == "__main__":
    """
    Test Agent 2 with sample conversation.

    Run: python -m agent.agent_2_claude
    """
    import asyncio

    async def test_conversation():
        print("Testing Agent 2 (Claude SDK) conversation...\n")

        agent = Agent2ClaudeSDK()

        # Simulate conversation
        test_messages = [
            "Hoi! Ik ben Sarah en zoek een baan als kapper in Amsterdam",
            "Ja, ik heb 5 jaar ervaring. Vooral gespecialiseerd in kleuren.",
            "Fulltime, 40 uur per week graag!",
            "Wat is jullie sollicitatieprocedure?",
            "Klinkt goed! Wanneer kan ik langskomen voor een gesprek?"
        ]

        conversation_history = []

        for user_msg in test_messages:
            print(f"\n{'='*50}")
            print(f"Kandidaat: {user_msg}")
            print(f"{'='*50}")

            response = await agent.send_message(
                lead_id="test-123",
                user_message=user_msg,
                conversation_history=conversation_history
            )

            print(f"\nAgent: {response}")

            # Update history
            conversation_history.append({"sender": "candidate", "content": user_msg})
            conversation_history.append({"sender": "agent", "content": response})

    asyncio.run(test_conversation())
