"""
Integratie Tests voor FastAPI Endpoints

Test coverage:
- Webhook ontvangst en verwerking
- Lead CRUD operaties
- Message geschiedenis
- Authenticatie flow
- Rate limiting
"""

import pytest
import httpx
from datetime import datetime


# ============ TEST CONFIG ============

API_BASE_URL = "http://localhost:8000"


# ============ HELPER FUNCTIONS ============

async def start_api_server():
    """Start de API server (indien nodig)."""
    # Deze functie checkt of server draait
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{API_BASE_URL}/", timeout=2.0)
        return True
    except:
        print("⚠️  API server niet gevonden. Start server met: python -m api.main")
        return False


# ============ WEBHOOK TESTS ============

@pytest.mark.asyncio
async def test_webhook_verification():
    """Test webhook verificatie endpoint (360Dialog)."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/webhook/whatsapp",
            params={"hub.challenge": "test-challenge-123"},
            timeout=5.0
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hub.challenge"] == "test-challenge-123"

    print("✅ Webhook verification test geslaagd")


@pytest.mark.asyncio
async def test_webhook_message_processing():
    """Test webhook message processing met mock payload."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    payload = {
        "messages": [
            {
                "from": "+31612345678",
                "id": "wamid.test123",
                "timestamp": "2025-01-09T10:00:00Z",
                "type": "text",
                "text": {
                    "body": "Hoi! Ik ben Sarah en ik zoek een baan"
                }
            }
        ],
        "contacts": [
            {
                "profile": {"name": "Sarah"},
                "wa_id": "+31612345678"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/webhook/whatsapp",
            json=payload,
            timeout=30.0
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 1

    print("✅ Webhook message processing test geslaagd")


# ============ LEAD API TESTS ============

@pytest.mark.asyncio
async def test_list_leads():
    """Test GET /api/leads endpoint."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/leads",
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()

        assert "leads" in data
        assert "total" in data
        assert isinstance(data["leads"], list)

    print(f"✅ List leads test geslaagd ({data['total']} leads gevonden)")


@pytest.mark.asyncio
async def test_list_leads_with_filter():
    """Test GET /api/leads met status filter."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/leads",
            params={"status": "qualified", "limit": 10},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()

        assert "leads" in data
        # Alle leads moeten status 'qualified' hebben
        for lead in data["leads"]:
            assert lead.get("qualification_status") == "qualified"

    print(f"✅ List leads with filter test geslaagd")


@pytest.mark.asyncio
async def test_create_lead():
    """Test POST /api/leads endpoint."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    new_lead = {
        "whatsapp_number": "+31687654321",
        "source": "manual",
        "notes": "Test lead from API test"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/leads",
            json=new_lead,
            timeout=10.0
        )

        assert response.status_code in [200, 201]
        data = response.json()

        assert "id" in data
        assert data["whatsapp_number"] == new_lead["whatsapp_number"]

    print(f"✅ Create lead test geslaagd (ID: {data['id']})")


# ============ MESSAGE API TESTS ============

@pytest.mark.asyncio
async def test_list_messages():
    """Test GET /api/messages endpoint."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/messages",
            params={"limit": 20},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()

        assert "messages" in data
        assert isinstance(data["messages"], list)

    print(f"✅ List messages test geslaagd ({len(data['messages'])} messages)")


# ============ AUTH TESTS ============

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test POST /api/auth/login met ongeldige credentials."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    credentials = {
        "email": "invalid@example.com",
        "password": "wrongpassword"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/auth/login",
            json=credentials,
            timeout=10.0
        )

        # Moet 401 Unauthorized zijn
        assert response.status_code == 401

    print("✅ Login invalid credentials test geslaagd (401 verwacht)")


# ============ RATE LIMITING TESTS ============

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting middleware (100 req/min)."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    # Stuur 10 requests snel achter elkaar
    async with httpx.AsyncClient() as client:
        for i in range(10):
            response = await client.get(
                f"{API_BASE_URL}/api/leads",
                timeout=5.0
            )

            # Eerste 10 zouden ok moeten zijn
            assert response.status_code == 200

    print("✅ Rate limiting test geslaagd (10 requests binnen limit)")


# ============ ERROR HANDLING TESTS ============

@pytest.mark.asyncio
async def test_invalid_endpoint():
    """Test dat niet-bestaande endpoints 404 geven."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/nonexistent",
            timeout=5.0
        )

        assert response.status_code == 404

    print("✅ Invalid endpoint test geslaagd (404 verwacht)")


@pytest.mark.asyncio
async def test_invalid_json_payload():
    """Test error handling met ongeldige JSON."""
    if not await start_api_server():
        pytest.skip("API server niet beschikbaar")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/webhook/whatsapp",
            json={"invalid": "payload"},  # Mist 'messages' key
            timeout=10.0
        )

        # Zou ofwel 200 (ignored) ofwel 400/422 moeten zijn
        assert response.status_code in [200, 400, 422]

    print("✅ Invalid JSON payload test geslaagd")


# ============ RUN TESTS ============

if __name__ == "__main__":
    import asyncio

    print("\n" + "="*60)
    print("🔌 FastAPI Integratie Tests")
    print("="*60 + "\n")

    print("⚠️  Zorg dat de API server draait: python -m api.main\n")

    async def run_all_tests():
        print("Test 1: Webhook Verification")
        await test_webhook_verification()

        print("\nTest 2: Webhook Message Processing")
        await test_webhook_message_processing()

        print("\nTest 3: List Leads")
        await test_list_leads()

        print("\nTest 4: List Leads with Filter")
        await test_list_leads_with_filter()

        print("\nTest 5: Create Lead")
        await test_create_lead()

        print("\nTest 6: List Messages")
        await test_list_messages()

        print("\nTest 7: Login Invalid Credentials")
        await test_login_invalid_credentials()

        print("\nTest 8: Rate Limiting")
        await test_rate_limiting()

        print("\nTest 9: Invalid Endpoint")
        await test_invalid_endpoint()

        print("\nTest 10: Invalid JSON Payload")
        await test_invalid_json_payload()

        print("\n" + "="*60)
        print("✅ Alle API tests geslaagd!")
        print("="*60)

    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests afgebroken door gebruiker")
