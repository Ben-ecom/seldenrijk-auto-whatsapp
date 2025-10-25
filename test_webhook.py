"""
Test Webhook Script

This script simulates a WhatsApp message from 360Dialog to test the webhook endpoint.

Usage:
    python test_webhook.py
"""

import asyncio
import httpx


# Mock WhatsApp webhook payload (360Dialog format)
MOCK_PAYLOAD = {
    "messages": [
        {
            "from": "+31612345678",
            "id": "wamid.test123",
            "timestamp": "2025-01-09T10:00:00Z",
            "type": "text",
            "text": {
                "body": "Hoi! Ik ben Sarah en ik zoek een baan als kapper in Amsterdam"
            }
        }
    ],
    "contacts": [
        {
            "profile": {
                "name": "Sarah"
            },
            "wa_id": "+31612345678"
        }
    ]
}


async def test_webhook():
    """
    Test the webhook endpoint with a mock payload.
    """
    print("🧪 Testing WhatsApp webhook endpoint...\n")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/webhook/whatsapp",
                json=MOCK_PAYLOAD,
                timeout=30.0
            )

            print(f"Status Code: {response.status_code}")

            try:
                response_data = response.json()
                print(f"Response: {response_data}\n")

                if response.status_code == 200:
                    print("✅ Webhook test successful!")
                    print(f"   Processed {response_data.get('processed', 0)} message(s)")
                else:
                    print(f"❌ Webhook test failed: {response.text}")
            except Exception as parse_error:
                print(f"Response text: {response.text}\n")
                if response.status_code == 200:
                    print("✅ Webhook test successful (non-JSON response)")
                else:
                    print(f"❌ Webhook test failed: {response.text}")

        except httpx.ConnectError:
            print("❌ Could not connect to API. Is the server running?")
            print("   Run: python -m api.main")
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_full_conversation():
    """
    Test a full conversation flow with multiple messages.
    """
    print("\n🧪 Testing full conversation flow...\n")

    messages = [
        "Hoi! Ik ben Sarah",
        "Ik heb 5 jaar ervaring als kapper",
        "Ik kan knippen, kleuren, en balayage",
        "Ik werk fulltime, 40 uur per week",
        "Welke vacatures hebben jullie in Amsterdam?",
        "Wat is de sollicitatieprocedure?",
        "Klinkt goed! Wanneer kan ik langskomen?"
    ]

    for idx, message in enumerate(messages, 1):
        print(f"\n--- Message {idx}/{len(messages)} ---")
        print(f"Candidate: {message}")

        payload = {
            "messages": [
                {
                    "from": "+31612345678",
                    "id": f"wamid.test{idx}",
                    "timestamp": f"2025-01-09T10:{idx:02d}:00Z",
                    "type": "text",
                    "text": {"body": message}
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "http://localhost:8000/webhook/whatsapp",
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    print(f"✅ Response received")
                else:
                    print(f"❌ Error: {response.status_code}")

            except Exception as e:
                print(f"❌ Error: {e}")
                break

        # Small delay between messages
        await asyncio.sleep(2)

    print("\n✅ Full conversation test complete!")


async def test_get_leads():
    """
    Test the GET /api/leads endpoint.
    """
    print("\n🧪 Testing GET /api/leads...\n")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8000/api/leads",
                timeout=10.0
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Total leads: {data['total']}")
                print(f"Returned: {len(data['leads'])} leads")

                if data['leads']:
                    print("\nFirst lead:")
                    lead = data['leads'][0]
                    print(f"  ID: {lead['id']}")
                    print(f"  WhatsApp: {lead['whatsapp_number']}")
                    print(f"  Status: {lead['qualification_status']}")
                    print(f"  Score: {lead.get('qualification_score', 'N/A')}")

                print("\n✅ GET leads test successful!")
            else:
                print(f"❌ Error: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """
    Run all tests.
    """
    print("=" * 60)
    print("🚀 WhatsApp Recruitment Platform - API Tests")
    print("=" * 60)

    # Test 1: Single webhook message
    await test_webhook()

    # Wait a bit
    await asyncio.sleep(2)

    # Test 2: Get leads
    await test_get_leads()

    # Optionally test full conversation (commented out by default)
    # Uncomment to test full flow:
    # await test_full_conversation()

    print("\n" + "=" * 60)
    print("✅ All tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
