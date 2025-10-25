"""
Agent 1: Pydantic AI Structured Extraction Agent

This agent extracts structured qualification data from conversation history
using Pydantic AI with GPT-4o-mini for cost-effective, type-safe extraction.

Key Features:
- Type-safe extraction with Pydantic models
- Automatic validation of scores and thresholds
- Cost-effective (GPT-4o-mini: €0.003/conversation)
- Deterministic qualification logic
"""

import os
from typing import Any
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from .models import LeadQualification, ConversationMessage


# ============ SYSTEM PROMPT ============
EXTRACTION_SYSTEM_PROMPT = """
Je bent een ervaren recruiter die kandidaten kwalificeert voor vacatures in de beauty/hospitality sector.

Je taak: Analyseer het gesprek en extraheer gestructureerde kandidaatinformatie.

**SCORINGSYSTEEM** (totaal 100 punten):

1. **Technische Skills (0-40 punten)**:
   - 30-40 punten: Expert niveau (5+ jaar, meerdere specialisaties)
   - 20-29 punten: Ervaren (3-5 jaar, basis specialisaties)
   - 10-19 punten: Junior (1-3 jaar, basis skills)
   - 0-9 punten: Geen relevante ervaring

   Voorbeelden beauty sector:
   - Knippen, kleuren, highlights, balayage
   - Extensions, permanenten, behandelingen
   - Productkennis (merken, chemie)

2. **Soft Skills (0-40 punten)**:
   - 30-40 punten: Uitstekend klantcontact, proactief, enthousiast
   - 20-29 punten: Goede communicatie, positieve instelling
   - 10-19 punten: Basis klantcontact, moet nog groeien
   - 0-9 punten: Geen klantervaring of negatieve signalen

   Let op:
   - Klantgerichtheid, geduld, luistervaardigheid
   - Teamwork, flexibiliteit
   - Telefoonvaardigheden, kassaervaring

3. **Ervaring (0-20 punten)**:
   - 16-20 punten: 5+ jaar relevante ervaring
   - 11-15 punten: 3-5 jaar ervaring
   - 6-10 punten: 1-3 jaar ervaring
   - 0-5 punten: < 1 jaar ervaring

**KWALIFICATIE DREMPELS**:
- **Qualified** (≥70 punten): Direct doorgaan naar interview
- **Pending Review** (30-69 punten): Menselijke beoordeling nodig
- **Disqualified** (<30 punten): Niet geschikt

**DISQUALIFICATIE REDENEN**:
- Geen relevante ervaring (< 1 jaar)
- Negatieve klantvaardigheden
- Onbeschikbaar voor gevraagde uren
- Onrealistische salarisverwachtingen
- Geen interesse meer (afgehaakt in gesprek)

**MISSING INFO**:
Als cruciale informatie ontbreekt, noteer in `missing_info`:
- "ervaring" - Aantal jaren ervaring niet duidelijk
- "technische_skills" - Geen concrete skills genoemd
- "beschikbaarheid" - Uren/dagen niet genoemd
- "motivatie" - Waarom deze job/bedrijf onduidelijk

**EXTRACTION CONFIDENCE**:
Geef je vertrouwen in de extractie (0.0-1.0):
- 0.9-1.0: Alle info compleet en duidelijk
- 0.7-0.8: Meeste info aanwezig, enkele aannames
- 0.5-0.6: Veel ontbrekende info, veel aannames
- <0.5: Onvoldoende info om te scoren

**BELANGRIJK**:
- Wees objectief, geen vooroordelen
- Gebruik alleen informatie uit het gesprek
- Als twijfel → pending_review
- Leg uit waarom scores zijn toegekend in `reasoning`
"""


class Agent1PydanticAI:
    """
    Agent 1: Structured Extraction using Pydantic AI + GPT-4o-mini

    Usage:
        agent = Agent1PydanticAI()
        result = await agent.extract_qualification(conversation_history)
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: str | None = None
    ):
        """
        Initialize Agent 1 with Pydantic AI.

        Args:
            model_name: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Initialize Pydantic AI Agent with result_type
        self.agent = Agent(
            model=OpenAIModel(model_name, api_key=self.api_key),
            result_type=LeadQualification,
            system_prompt=EXTRACTION_SYSTEM_PROMPT
        )

    async def extract_qualification(
        self,
        conversation_history: list[ConversationMessage],
        job_context: str | None = None
    ) -> LeadQualification:
        """
        Extract structured qualification data from conversation.

        Args:
            conversation_history: List of messages between candidate and agent
            job_context: Optional job posting context for better scoring

        Returns:
            LeadQualification: Type-safe Pydantic model with scores and status

        Example:
            >>> messages = [
            ...     ConversationMessage(sender="agent", content="Hoi! Hoe heet je?"),
            ...     ConversationMessage(sender="candidate", content="Ik ben Sarah"),
            ...     ConversationMessage(sender="agent", content="Hoeveel jaar ervaring heb je?"),
            ...     ConversationMessage(sender="candidate", content="5 jaar als kapper, gespecialiseerd in kleuren")
            ... ]
            >>> result = await agent.extract_qualification(messages)
            >>> print(result.overall_score)  # 75
            >>> print(result.qualification_status)  # "qualified"
        """
        # Format conversation as transcript
        transcript = self._format_transcript(conversation_history)

        # Add job context if provided
        if job_context:
            transcript = f"**VACATURE CONTEXT**:\n{job_context}\n\n**GESPREK**:\n{transcript}"

        # Run Pydantic AI agent
        result = await self.agent.run(transcript)

        # Result.data is automatically validated LeadQualification model
        return result.data

    def _format_transcript(self, messages: list[ConversationMessage]) -> str:
        """
        Format conversation messages into readable transcript.

        Args:
            messages: List of conversation messages

        Returns:
            Formatted transcript string
        """
        lines = []
        for msg in messages:
            sender_label = "Agent" if msg.sender == "agent" else "Kandidaat"
            timestamp_str = msg.timestamp.strftime("%H:%M")
            lines.append(f"[{timestamp_str}] {sender_label}: {msg.content}")

        return "\n".join(lines)

    async def extract_with_context(
        self,
        conversation_history: list[dict[str, Any]],
        job_context: str | None = None
    ) -> LeadQualification:
        """
        Extract qualification from raw conversation data (dict format).

        This is a convenience method for API endpoints that receive
        conversation data as plain dictionaries.

        Args:
            conversation_history: List of message dicts with keys: sender, content, timestamp
            job_context: Optional job posting context

        Returns:
            LeadQualification model
        """
        # Convert dicts to Pydantic models
        messages = [
            ConversationMessage(**msg)
            for msg in conversation_history
        ]

        return await self.extract_qualification(messages, job_context)


# ============ STANDALONE EXTRACTION FUNCTION ============

async def extract_lead_qualification(
    conversation_history: list[dict[str, Any]],
    job_context: str | None = None,
    model_name: str = "gpt-4o-mini"
) -> LeadQualification:
    """
    Standalone function to extract qualification data.

    This function is useful for FastAPI endpoints or background jobs.

    Args:
        conversation_history: Raw conversation data
        job_context: Optional job posting context
        model_name: OpenAI model to use

    Returns:
        LeadQualification: Extracted and validated data

    Example:
        >>> result = await extract_lead_qualification([
        ...     {"sender": "agent", "content": "Hoi!"},
        ...     {"sender": "candidate", "content": "Hoi, ik ben Sarah"}
        ... ])
        >>> result.qualification_status
        'pending_review'
    """
    agent = Agent1PydanticAI(model_name=model_name)
    return await agent.extract_with_context(conversation_history, job_context)


# ============ TESTING HELPERS ============

def get_sample_conversation() -> list[ConversationMessage]:
    """
    Get sample conversation for testing.
    """
    from datetime import datetime, timedelta

    base_time = datetime.now()

    return [
        ConversationMessage(
            sender="agent",
            content="Hoi! 👋 Bedankt voor je interesse. Hoe heet je?",
            timestamp=base_time
        ),
        ConversationMessage(
            sender="candidate",
            content="Hallo! Ik ben Sarah van der Berg.",
            timestamp=base_time + timedelta(minutes=1)
        ),
        ConversationMessage(
            sender="agent",
            content="Leuk je te spreken Sarah! Hoeveel jaar ervaring heb je in de haarbranche?",
            timestamp=base_time + timedelta(minutes=2)
        ),
        ConversationMessage(
            sender="candidate",
            content="Ik werk nu 5 jaar als kapper. Ik ben vooral gespecialiseerd in kleuren en balayage.",
            timestamp=base_time + timedelta(minutes=3)
        ),
        ConversationMessage(
            sender="agent",
            content="Dat klinkt goed! Welke technieken beheers je nog meer?",
            timestamp=base_time + timedelta(minutes=4)
        ),
        ConversationMessage(
            sender="candidate",
            content="Ik doe ook knippen, highlights, en ik heb een cursus extensions gedaan. En ik werk graag met klanten, vind het leuk om ze te adviseren over nieuwe looks.",
            timestamp=base_time + timedelta(minutes=5)
        ),
        ConversationMessage(
            sender="agent",
            content="Perfect! Wat is je beschikbaarheid?",
            timestamp=base_time + timedelta(minutes=6)
        ),
        ConversationMessage(
            sender="candidate",
            content="Ik kan fulltime, 40 uur per week. Weekenden zijn geen probleem.",
            timestamp=base_time + timedelta(minutes=7)
        )
    ]


if __name__ == "__main__":
    """
    Test Agent 1 with sample conversation.

    Run: python -m agent.agent_1_pydantic
    """
    import asyncio

    async def test_extraction():
        print("Testing Agent 1 (Pydantic AI) extraction...\n")

        # Initialize agent
        agent = Agent1PydanticAI()

        # Get sample conversation
        conversation = get_sample_conversation()

        # Extract qualification
        print("Analyzing conversation...")
        result = await agent.extract_qualification(conversation)

        # Print results
        print("\n" + "="*50)
        print("EXTRACTION RESULTS")
        print("="*50)
        print(f"Name: {result.full_name}")
        print(f"Experience: {result.years_experience} years")
        print(f"Skills: {', '.join(result.skills)}")
        print(f"\nScores:")
        print(f"  Technical: {result.technical_score}/40")
        print(f"  Soft Skills: {result.soft_skills_score}/40")
        print(f"  Experience: {result.experience_score}/20")
        print(f"  Overall: {result.overall_score}/100")
        print(f"\nStatus: {result.qualification_status.upper()}")
        print(f"Confidence: {result.extraction_confidence:.2f}")
        if result.missing_info:
            print(f"Missing Info: {', '.join(result.missing_info)}")
        if result.reasoning:
            print(f"\nReasoning:\n{result.reasoning}")

    asyncio.run(test_extraction())
