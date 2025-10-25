#!/usr/bin/env python3
"""
WhatsApp Message Testing Script
Simuleert WhatsApp berichten zonder API credentials nodig te hebben.
"""
import httpx
import json
from datetime import datetime

# Test messages voor automotive use case
TEST_MESSAGES = [
    {
        "name": "Echte koper - Test Drive",
        "message": "Hallo, ik heb interesse in de Mercedes C-Klasse 2020 van €28.500. Is deze nog beschikbaar? Ik zou graag een proefrit willen maken volgende week.",
        "expected_score": 85,  # High score: specific vehicle + test drive
    },
    {
        "name": "Tijd-verspiller - Eindeloos vragen",
        "message": "Hoi, wat voor auto's hebben jullie? Wat zijn de prijzen? Hebben jullie ook lease? En wat kosten de verzekeringen dan ongeveer?",
        "expected_score": 25,  # Low score: no specific interest, only questions
    },
    {
        "name": "Serieuze koper - Budget + Inruil",
        "message": "Ik zoek een hybride auto voor max €35.000. Hebben jullie een Toyota RAV4 Hybrid? Ik heb ook een auto om in te ruilen, een Volkswagen Golf 2018.",
        "expected_score": 75,  # Good score: budget + specific car + trade-in
    },
    {
        "name": "Lowballer",
        "message": "Die BMW 3-serie voor €22.000... kan dat voor €15.000? Anders ben ik niet geïnteresseerd.",
        "expected_score": 30,  # Low score: unrealistic offer
    },
    {
        "name": "HOT Lead - All signals",
        "message": "Goedemiddag, ik kom vandaag om 15:00 langs kijken naar de Audi A4 2021. Budget is €32.000, heb een VW Passat 2017 om in te ruilen. Kunnen we direct financiering regelen?",
        "expected_score": 95,  # Hot lead: urgent + budget + trade-in + financing
    },
]

def simulate_chatwoot_webhook(message: str, phone: str = "+31612345678"):
    """
    Simuleer een Chatwoot webhook voor testing.

    Args:
        message: Het WhatsApp bericht
        phone: Telefoonnummer (optioneel)
    """
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "id": f"msg_{datetime.now().timestamp()}",
        "conversation": {
            "id": 12345,
            "inbox_id": 1,
            "status": "open"
        },
        "sender": {
            "id": 67890,
            "name": "Test Customer",
            "phone_number": phone,
            "type": "contact"
        },
        "content": message,
        "created_at": datetime.now().isoformat(),
        "private": False,
        "content_type": "text",
        "content_attributes": {},
        "channel": "whatsapp"
    }

    return payload

def test_message(test_case: dict):
    """
    Test een enkel bericht via de webhook API.

    Args:
        test_case: Dict met name, message, expected_score
    """
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*80}")
    print(f"Bericht: {test_case['message']}")
    print(f"Verwachte score: {test_case['expected_score']}/100")

    # Maak payload
    payload = simulate_chatwoot_webhook(test_case['message'])

    # Verstuur naar webhook (zonder signature voor local testing)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "http://localhost:8000/webhooks/chatwoot",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    # Note: In productie zou hier X-Chatwoot-Signature header moeten staan
                    # Voor local testing kunnen we signature verificatie skippen
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"✅ Task ID: {result.get('task_id')}")
                print(f"✅ Conversation ID: {result.get('conversation_id')}")
                print(f"\n⏳ Bericht wordt nu verwerkt door LangGraph...")
                print(f"   - Router classificeert intent")
                print(f"   - Extraction haalt lead data eruit")
                print(f"   - Conversation genereert antwoord")
                print(f"   - CRM update naar Chatwoot")

            else:
                print(f"❌ Fout: {response.status_code}")
                print(f"   {response.text}")

    except httpx.ConnectError:
        print("❌ Kan niet verbinden met http://localhost:8000")
        print("   Zorg dat de API draait: docker compose up")
    except Exception as e:
        print(f"❌ Fout: {str(e)}")

def main():
    """Run all test cases."""
    print("🚀 WhatsApp Message Testing Tool")
    print("=" * 80)
    print("Dit script simuleert WhatsApp berichten via de Chatwoot webhook.")
    print("Geen WhatsApp API credentials nodig!")
    print("=" * 80)

    # Controleer of API draait
    try:
        with httpx.Client(timeout=5.0) as client:
            health = client.get("http://localhost:8000/health")
            if health.status_code == 200:
                print("✅ API is online en gezond\n")
            else:
                print("⚠️  API reageert maar health check faalt\n")
    except:
        print("❌ API is offline. Start eerst: docker compose up\n")
        return

    # Menu
    print("\nKies een optie:")
    print("1. Test alle scenarios (5 berichten)")
    print("2. Test één specifiek scenario")
    print("3. Verstuur custom bericht")

    choice = input("\nKeuze (1-3): ").strip()

    if choice == "1":
        # Test alle scenarios
        for i, test_case in enumerate(TEST_MESSAGES, 1):
            print(f"\n\n🧪 Test {i}/{len(TEST_MESSAGES)}")
            test_message(test_case)

            if i < len(TEST_MESSAGES):
                input("\nDruk op Enter voor volgende test...")

    elif choice == "2":
        # Kies specifiek scenario
        print("\nBeschikbare scenarios:")
        for i, test_case in enumerate(TEST_MESSAGES, 1):
            print(f"{i}. {test_case['name']} (verwacht: {test_case['expected_score']}/100)")

        scenario = int(input("\nKies scenario (1-5): ").strip()) - 1
        if 0 <= scenario < len(TEST_MESSAGES):
            test_message(TEST_MESSAGES[scenario])
        else:
            print("❌ Ongeldige keuze")

    elif choice == "3":
        # Custom bericht
        message = input("\nTyp je bericht: ").strip()
        if message:
            test_case = {
                "name": "Custom Test",
                "message": message,
                "expected_score": "?"
            }
            test_message(test_case)
        else:
            print("❌ Geen bericht ingevoerd")
    else:
        print("❌ Ongeldige keuze")

    print("\n\n✅ Testing voltooid!")
    print("\n📊 Bekijk resultaten in:")
    print("   - Dashboard: http://localhost:3002")
    print("   - Chatwoot: http://localhost:3001")
    print("   - Logs: docker compose logs -f api")

if __name__ == "__main__":
    main()
