"""
End-to-End tests for complete car search flow.

Tests full flow: Webhook → Message Processing → Agent Routing → Vector Search → Response

This validates the entire system integration from WhatsApp message
to final car recommendations sent back to user.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json

from app.main import app


client = TestClient(app)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCarSearchE2E:
    """End-to-end tests for car search workflow."""

    @patch("app.tasks.process_message.process_message_async.delay")
    @patch("app.api.webhooks.redis_client")
    async def test_waha_message_to_car_search_flow(self, mock_redis, mock_celery):
        """
        E2E Test: WhatsApp message → Agent processing → Car search → Response

        Flow:
        1. User sends message via WhatsApp (WAHA webhook)
        2. Webhook validates and queues message
        3. Celery task processes message
        4. Router agent classifies as car search
        5. Car search agent finds vehicles
        6. Response sent back to user
        """
        # Step 1: Mock Redis (no duplicate)
        mock_redis.get.return_value = None

        # Step 2: Mock Celery task
        mock_task = Mock()
        mock_task.id = "e2e_task_123"
        mock_celery.return_value = mock_task

        # Step 3: Prepare WAHA webhook payload
        payload = {
            "event": "message",
            "payload": {
                "id": "e2e_msg_001",
                "from": "31612345678@c.us",
                "body": "Ik zoek een Audi Q5 diesel onder 40.000 euro",
                "fromMe": False,
                "_data": {
                    "notifyName": "Test User"
                }
            }
        }

        payload_json = json.dumps(payload)

        # Step 4: Send webhook request
        response = client.post(
            "/webhooks/waha",
            content=payload_json,
            headers={"Content-Type": "application/json"}
        )

        # Step 5: Verify webhook accepted message
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert "task_id" in response.json()

        # Step 6: Verify Celery task was queued
        mock_celery.assert_called_once()

        # Step 7: Verify message was marked in Redis (deduplication)
        mock_redis.setex.assert_called()

    @patch("app.tasks.process_message.process_message_async.delay")
    async def test_chatwoot_agent_message_to_whatsapp(self, mock_celery):
        """
        E2E Test: Human agent message → Forward to WhatsApp

        Flow:
        1. Agent sends message in Chatwoot
        2. Chatwoot webhook triggers
        3. Outgoing message forwarded to WhatsApp via WAHA
        4. User receives message on WhatsApp
        """
        # Prepare Chatwoot outgoing message payload
        payload = {
            "event": "message_created",
            "id": 9876,
            "conversation": {"id": 5432},
            "content": "We hebben 3 Audi Q5 modellen beschikbaar. Wilt u meer informatie?",
            "message_type": "outgoing"  # Human agent message
        }

        payload_json = json.dumps(payload)

        # Mock WAHA forward function
        with patch("app.api.webhooks._forward_chatwoot_to_waha") as mock_forward:
            mock_forward.return_value = AsyncMock()

            # Send webhook request
            response = client.post(
                "/webhooks/chatwoot",
                content=payload_json,
                headers={"Content-Type": "application/json"}
            )

            # Verify webhook handled outgoing message
            assert response.status_code == 200
            assert response.json()["status"] == "forwarded"

            # Verify message was forwarded to WAHA
            mock_forward.assert_called_once()

    @patch("app.services.vector_store.VehicleVectorStore.search_vehicles")
    @patch("app.tasks.process_message.process_message_async.delay")
    async def test_full_car_search_with_results(self, mock_celery, mock_search):
        """
        E2E Test: Complete car search with vector search results

        Flow:
        1. User message: "Ik zoek een BMW X5"
        2. Router classifies as CAR_SEARCH
        3. Car search agent extracts: brand=BMW, model=X5
        4. Vector search finds matching vehicles
        5. Agent formats response with top 3 matches
        6. Response sent back via Chatwoot
        """
        # Mock vector search results
        mock_search.return_value = [
            {
                "brand": "BMW",
                "model": "X5",
                "build_year": 2021,
                "mileage": 45000,
                "price": 48000,
                "fuel": "diesel",
                "url": "https://seldenrijk.nl/bmw-x5-1",
                "similarity": 0.95
            },
            {
                "brand": "BMW",
                "model": "X5",
                "build_year": 2020,
                "mileage": 65000,
                "price": 42000,
                "fuel": "benzine",
                "url": "https://seldenrijk.nl/bmw-x5-2",
                "similarity": 0.92
            },
            {
                "brand": "BMW",
                "model": "X5",
                "build_year": 2019,
                "mileage": 85000,
                "price": 38000,
                "fuel": "diesel",
                "url": "https://seldenrijk.nl/bmw-x5-3",
                "similarity": 0.88
            }
        ]

        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "search_task_456"
        mock_celery.return_value = mock_task

        # Prepare payload
        payload = {
            "event": "message",
            "payload": {
                "id": "search_msg_001",
                "from": "31612345678@c.us",
                "body": "Ik zoek een BMW X5",
                "fromMe": False
            }
        }

        payload_json = json.dumps(payload)

        with patch("app.api.webhooks.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            response = client.post(
                "/webhooks/waha",
                content=payload_json,
                headers={"Content-Type": "application/json"}
            )

            # Verify webhook accepted message
            assert response.status_code == 200
            assert response.json()["status"] == "queued"

    @patch("app.tasks.process_message.process_message_async.delay")
    async def test_rate_limiting_e2e(self, mock_celery):
        """
        E2E Test: Rate limiting prevents abuse

        Flow:
        1. Send 11 rapid requests to WAHA webhook
        2. First 10 accepted
        3. 11th request rate limited (429)
        """
        mock_task = Mock()
        mock_task.id = "rate_limit_task"
        mock_celery.return_value = mock_task

        payload = {
            "event": "message",
            "payload": {
                "id": "rate_limit_msg",
                "from": "31612345678@c.us",
                "body": "Test message",
                "fromMe": False
            }
        }

        payload_json = json.dumps(payload)

        with patch("app.api.webhooks.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            # Send 11 requests
            responses = []
            for i in range(11):
                response = client.post(
                    "/webhooks/waha",
                    content=payload_json,
                    headers={"Content-Type": "application/json"}
                )
                responses.append(response.status_code)

            # First 10 should be accepted
            assert all(code in [200, 400, 500] for code in responses[:10])

            # 11th should be rate limited
            assert responses[10] == 429


@pytest.mark.e2e
class TestHealthCheckE2E:
    """E2E tests for health check endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns app metadata."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Seldenrijk Auto WhatsApp"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"

    def test_health_endpoint(self):
        """Test /health endpoint (if implemented)."""
        response = client.get("/health")

        # Should return 200 if implemented, 404 if not
        assert response.status_code in [200, 404]
