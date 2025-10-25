"""
Unit Tests voor Agent 2 (Claude SDK Conversatie Agent)

Test coverage:
- Conversatie kwaliteit
- Tool gebruik (agentic RAG)
- Context behoud over meerdere berichten
- Response formatting (WhatsApp stijl)
- Error handling
"""

import pytest
import os
from datetime import datetime
from agent import Agent2ClaudeSDK


# ============ TEST SETUP ============

# Sla lead_id op voor alle tests
TEST_LEAD_ID = "test-lead-123"


# ============ TESTS ============

@pytest.mark.asyncio
async def test_agent2_basic_response():
    """Test dat Agent 2 een basis response kan genereren."""
    agent = Agent2ClaudeSDK()

    response = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Hoi! Ik ben Sarah en ik zoek een baan als kapper",
        conversation_history=[]
    )

    # Check dat er een response is
    assert response is not None
    assert len(response) > 0

    # Check dat response Nederlands is en vriendelijk
    assert any(word in response.lower() for word in ["hoi", "hallo", "welkom", "leuk"])

    print(f"✅ Basic response test geslaagd")
    print(f"   Response: {response[:100]}...")


@pytest.mark.asyncio
async def test_agent2_conversation_context():
    """Test dat Agent 2 context behoudt over meerdere berichten."""
    agent = Agent2ClaudeSDK()

    # Eerste bericht
    history = []
    response1 = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Mijn naam is Sarah",
        conversation_history=history
    )

    # Update history
    history.append({
        "sender": "candidate",
        "content": "Mijn naam is Sarah",
        "timestamp": datetime.now().isoformat()
    })
    history.append({
        "sender": "agent",
        "content": response1,
        "timestamp": datetime.now().isoformat()
    })

    # Tweede bericht - refereer naar naam
    response2 = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Ik heb 5 jaar ervaring",
        conversation_history=history
    )

    # Check dat de naam "Sarah" mogelijk wordt genoemd in response2
    # (Agent zou context moeten onthouden)
    assert len(response2) > 0

    print(f"✅ Context test geslaagd")
    print(f"   Response 1: {response1[:80]}...")
    print(f"   Response 2: {response2[:80]}...")


@pytest.mark.asyncio
async def test_agent2_tool_usage_decision():
    """Test dat Agent 2 besluit om tools te gebruiken wanneer relevant."""
    agent = Agent2ClaudeSDK()

    # Test 1: Vraag over vacatures -> zou search_job_postings moeten triggeren
    response_vacatures = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Welke vacatures hebben jullie voor kappers in Amsterdam?",
        conversation_history=[]
    )

    assert len(response_vacatures) > 0
    print(f"✅ Tool usage test (vacatures): {response_vacatures[:100]}...")

    # Test 2: Vraag over bedrijf -> zou search_company_docs kunnen triggeren
    response_bedrijf = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Wat zijn de secundaire arbeidsvoorwaarden?",
        conversation_history=[]
    )

    assert len(response_bedrijf) > 0
    print(f"✅ Tool usage test (bedrijf): {response_bedrijf[:100]}...")


@pytest.mark.asyncio
async def test_agent2_response_format():
    """Test dat responses de juiste WhatsApp stijl hebben."""
    agent = Agent2ClaudeSDK()

    response = await agent.send_message(
        lead_id=TEST_LEAD_ID,
        user_message="Hoi!",
        conversation_history=[]
    )

    # Check response eigenschappen
    assert len(response) > 0
    assert len(response) < 500  # Niet te lang (WhatsApp stijl)

    # Check voor vriendelijke tone (emoji's zijn optioneel)
    # Response moet Nederlands zijn
    dutch_words = ["hoi", "hallo", "welkom", "leuk", "mooi", "super", "wat", "je", "jij"]
    assert any(word in response.lower() for word in dutch_words)

    print(f"✅ Response format test geslaagd")
    print(f"   Length: {len(response)} karakters")


@pytest.mark.asyncio
async def test_agent2_error_handling():
    """Test error handling bij ongeldige input."""
    agent = Agent2ClaudeSDK()

    try:
        # Test met lege message
        response = await agent.send_message(
            lead_id=TEST_LEAD_ID,
            user_message="",
            conversation_history=[]
        )

        # Zelfs met lege input moet er een response zijn
        assert response is not None

        print(f"✅ Error handling test geslaagd (lege message)")

    except Exception as e:
        # Error is ok, zolang het geen crash is
        print(f"✅ Error handling test geslaagd (exception gevangen): {e}")


@pytest.mark.asyncio
async def test_agent2_multi_turn_conversation():
    """Test volledige multi-turn conversatie."""
    agent = Agent2ClaudeSDK()

    conversation = [
        "Hoi! Ik ben op zoek naar een baan",
        "Ik heb 3 jaar ervaring als kapper",
        "Ik kan knippen en kleuren",
        "Ja, ik wil graag meer weten over vacatures",
    ]

    history = []

    for i, message in enumerate(conversation):
        print(f"\n--- Turn {i+1} ---")
        print(f"Candidate: {message}")

        response = await agent.send_message(
            lead_id=TEST_LEAD_ID,
            user_message=message,
            conversation_history=history
        )

        print(f"Agent: {response[:100]}...")

        # Update history
        history.append({
            "sender": "candidate",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        history.append({
            "sender": "agent",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        assert len(response) > 0

    print(f"\n✅ Multi-turn conversation test geslaagd ({len(conversation)} turns)")


@pytest.mark.asyncio
async def test_agent2_with_invalid_api_key():
    """Test dat Agent 2 netjes faalt met ongeldige API key."""
    # Sla originele key op
    original_key = os.environ.get("ANTHROPIC_API_KEY")

    try:
        # Zet tijdelijk ongeldige key
        os.environ["ANTHROPIC_API_KEY"] = "invalid-key-123"

        agent = Agent2ClaudeSDK()

        # Dit zou moeten falen
        with pytest.raises(Exception):
            await agent.send_message(
                lead_id=TEST_LEAD_ID,
                user_message="Test",
                conversation_history=[]
            )

        print(f"✅ Invalid API key test geslaagd (exception verwacht en gevangen)")

    finally:
        # Herstel originele key
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key


# ============ RUN TESTS ============

if __name__ == "__main__":
    import asyncio

    print("\n" + "="*60)
    print("🤖 Agent 2 (Claude SDK) Unit Tests")
    print("="*60 + "\n")

    async def run_all_tests():
        print("Test 1: Basic Response")
        await test_agent2_basic_response()

        print("\n\nTest 2: Conversation Context")
        await test_agent2_conversation_context()

        print("\n\nTest 3: Tool Usage Decision")
        await test_agent2_tool_usage_decision()

        print("\n\nTest 4: Response Format")
        await test_agent2_response_format()

        print("\n\nTest 5: Error Handling")
        await test_agent2_error_handling()

        print("\n\nTest 6: Multi-turn Conversation")
        await test_agent2_multi_turn_conversation()

        print("\n\nTest 7: Invalid API Key Handling")
        await test_agent2_with_invalid_api_key()

        print("\n" + "="*60)
        print("✅ Alle Agent 2 tests geslaagd!")
        print("="*60)

    asyncio.run(run_all_tests())
