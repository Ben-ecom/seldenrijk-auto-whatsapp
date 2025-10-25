"""
Unit Tests voor Agent 1 (Pydantic AI Extractie Agent)

Test coverage:
- Extractie accuracy
- Scoring systeem (100 punten)
- Kwalificatie thresholds
- Missing info detectie
- Confidence scoring
"""

import pytest
from datetime import datetime
from agent import Agent1PydanticAI, ConversationMessage


# ============ TEST DATA ============

QUALIFIED_CONVERSATION = [
    ConversationMessage(
        sender="agent",
        content="Hoi! Welkom bij Hair & Beauty Recruitment. Wat is je naam?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Hoi! Ik ben Sarah",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Leuk je te ontmoeten Sarah! Hoeveel jaar ervaring heb je als kapper?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Ik heb 8 jaar ervaring, waarvan 5 jaar in een salon in Amsterdam",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Mooi! Welke technieken beheers je?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Ik kan knippen, kleuren, highlights, balayage en ombre. Ook föhnen en updos voor bruiden",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Geweldig! Hoeveel uur per week wil je werken?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Ik zoek een fulltime baan, 40 uur per week",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Perfect! Wat zijn je sterke punten?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Ik ben erg klantgericht, creatief en werk graag in een team. Klanten vinden me vriendelijk en professioneel",
        timestamp=datetime.now()
    ),
]

DISQUALIFIED_CONVERSATION = [
    ConversationMessage(
        sender="agent",
        content="Hoi! Wat is je naam?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Jan",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Hoeveel ervaring heb je als kapper?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Ik heb geen ervaring, maar ik wil graag leren",
        timestamp=datetime.now()
    ),
]

PENDING_CONVERSATION = [
    ConversationMessage(
        sender="agent",
        content="Hoi! Wat is je naam?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="Lisa",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="agent",
        content="Hoeveel ervaring heb je?",
        timestamp=datetime.now()
    ),
    ConversationMessage(
        sender="candidate",
        content="2 jaar in een klein salon",
        timestamp=datetime.now()
    ),
]


# ============ TESTS ============

@pytest.mark.asyncio
async def test_agent1_qualified_extraction():
    """Test dat gekwalificeerde kandidaat correct wordt geëxtraheerd."""
    agent = Agent1PydanticAI()

    result = await agent.extract_qualification(QUALIFIED_CONVERSATION)

    # Check basis info
    assert result.full_name == "Sarah"
    assert result.years_experience >= 5
    assert "knippen" in result.skills
    assert "balayage" in result.skills

    # Check scoring
    assert result.technical_score >= 30  # Veel skills
    assert result.soft_skills_score >= 30  # Klantgericht, teamspeler
    assert result.experience_score >= 15  # 8 jaar ervaring
    assert result.overall_score >= 70  # Totaal qualified

    # Check status
    assert result.qualification_status == "qualified"
    assert result.extraction_confidence > 0.8

    print(f"✅ Qualified test: {result.full_name} - Score: {result.overall_score}/100")


@pytest.mark.asyncio
async def test_agent1_disqualified_extraction():
    """Test dat niet-gekwalificeerde kandidaat correct wordt afgewezen."""
    agent = Agent1PydanticAI()

    result = await agent.extract_qualification(DISQUALIFIED_CONVERSATION)

    # Check basis info
    assert result.full_name == "Jan"
    assert result.years_experience == 0 or result.years_experience is None

    # Check scoring
    assert result.technical_score < 20  # Geen skills
    assert result.experience_score < 10  # Geen ervaring
    assert result.overall_score < 30  # Totaal disqualified

    # Check status
    assert result.qualification_status == "disqualified"
    assert result.disqualification_reason is not None

    print(f"✅ Disqualified test: {result.full_name} - Score: {result.overall_score}/100")


@pytest.mark.asyncio
async def test_agent1_pending_extraction():
    """Test dat pending kandidaat correct wordt geïdentificeerd."""
    agent = Agent1PydanticAI()

    result = await agent.extract_qualification(PENDING_CONVERSATION)

    # Check basis info
    assert result.full_name == "Lisa"
    assert result.years_experience >= 2

    # Check scoring - tussen 30 en 70
    assert 30 <= result.overall_score < 70

    # Check status
    assert result.qualification_status == "pending_review"
    assert len(result.missing_info) > 0  # Moet info missen

    print(f"✅ Pending test: {result.full_name} - Score: {result.overall_score}/100 - Missing: {result.missing_info}")


@pytest.mark.asyncio
async def test_agent1_score_validation():
    """Test dat score berekening klopt (technical + soft + experience = overall)."""
    agent = Agent1PydanticAI()

    result = await agent.extract_qualification(QUALIFIED_CONVERSATION)

    # Bereken verwachte totaal
    expected_total = result.technical_score + result.soft_skills_score + result.experience_score

    # Check dat overall_score gelijk is aan som van componenten
    assert result.overall_score == expected_total

    # Check dat individuele scores binnen limieten blijven
    assert 0 <= result.technical_score <= 40
    assert 0 <= result.soft_skills_score <= 40
    assert 0 <= result.experience_score <= 20
    assert 0 <= result.overall_score <= 100

    print(f"✅ Score validation: {result.technical_score} + {result.soft_skills_score} + {result.experience_score} = {result.overall_score}")


@pytest.mark.asyncio
async def test_agent1_missing_info_detection():
    """Test dat missing info correct wordt gedetecteerd."""
    short_conversation = [
        ConversationMessage(
            sender="agent",
            content="Hoi! Wat is je naam?",
            timestamp=datetime.now()
        ),
        ConversationMessage(
            sender="candidate",
            content="Emma",
            timestamp=datetime.now()
        ),
    ]

    agent = Agent1PydanticAI()
    result = await agent.extract_qualification(short_conversation)

    # Met zo weinig info moeten er veel missing fields zijn
    assert len(result.missing_info) > 0

    # Check dat confidence laag is
    assert result.extraction_confidence < 0.5

    print(f"✅ Missing info test: {len(result.missing_info)} velden ontbreken - Confidence: {result.extraction_confidence}")


@pytest.mark.asyncio
async def test_agent1_skills_extraction():
    """Test dat skills correct worden geëxtraheerd."""
    agent = Agent1PydanticAI()

    result = await agent.extract_qualification(QUALIFIED_CONVERSATION)

    # Check dat belangrijke skills zijn geëxtraheerd
    expected_skills = ["knippen", "kleuren", "balayage"]
    for skill in expected_skills:
        assert skill in result.skills, f"Skill '{skill}' niet gevonden in {result.skills}"

    # Check dat skills niet leeg zijn
    assert len(result.skills) > 0

    print(f"✅ Skills extraction: {len(result.skills)} skills gevonden: {result.skills}")


# ============ RUN TESTS ============

if __name__ == "__main__":
    import asyncio

    print("\n" + "="*60)
    print("🧪 Agent 1 (Pydantic AI) Unit Tests")
    print("="*60 + "\n")

    async def run_all_tests():
        print("Test 1: Qualified Extraction")
        await test_agent1_qualified_extraction()

        print("\nTest 2: Disqualified Extraction")
        await test_agent1_disqualified_extraction()

        print("\nTest 3: Pending Review Extraction")
        await test_agent1_pending_extraction()

        print("\nTest 4: Score Validation")
        await test_agent1_score_validation()

        print("\nTest 5: Missing Info Detection")
        await test_agent1_missing_info_detection()

        print("\nTest 6: Skills Extraction")
        await test_agent1_skills_extraction()

        print("\n" + "="*60)
        print("✅ Alle Agent 1 tests geslaagd!")
        print("="*60)

    asyncio.run(run_all_tests())
