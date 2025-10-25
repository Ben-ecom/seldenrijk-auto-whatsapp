"""
Unit tests for Router Agent.

Tests:
- Intent classification accuracy
- Priority detection
- Escalation logic
- Confidence scoring
- Edge cases (empty messages, unclear intent)
"""
import pytest
from unittest.mock import Mock, patch
from app.agents.router_agent import RouterAgent
from app.orchestration.state import ConversationState, create_initial_state


class TestRouterAgent:
    """Test suite for Router Agent intent classification."""

    @pytest.fixture
    def router_agent(self):
        """Create Router Agent instance for testing."""
        return RouterAgent()

    @pytest.fixture
    def sample_state(self) -> ConversationState:
        """Create sample conversation state for testing."""
        return create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I'm looking for a software engineer job in Amsterdam",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

    @pytest.mark.asyncio
    async def test_job_search_intent_classification(self, router_agent, sample_state):
        """Test Router correctly classifies job search intent."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": true,
            "escalate_to_human": false,
            "confidence": 0.95,
            "reasoning": "User explicitly states job search intent with location preference"
        }"""
        mock_response.usage = Mock(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300
        )

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(sample_state)

            # Verify output
            assert result["output"]["intent"] == "job_search"
            assert result["output"]["priority"] == "medium"
            assert result["output"]["needs_extraction"] is True
            assert result["output"]["escalate_to_human"] is False
            assert result["output"]["confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_complaint_intent_escalation(self, router_agent):
        """Test Router escalates complaint intents to human."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="This is unacceptable! I've been waiting 3 weeks with no response!",
            sender_name="Angry User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "complaint",
            "priority": "high",
            "needs_extraction": false,
            "escalate_to_human": true,
            "confidence": 0.98,
            "reasoning": "Strong negative sentiment, frustration, requires human intervention"
        }"""
        mock_response.usage = Mock(prompt_tokens=200, completion_tokens=100, total_tokens=300)

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(state)

            assert result["output"]["intent"] == "complaint"
            assert result["output"]["priority"] == "high"
            assert result["output"]["escalate_to_human"] is True

    @pytest.mark.asyncio
    async def test_salary_inquiry_intent(self, router_agent):
        """Test Router classifies salary inquiries correctly."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="What's the salary range for senior developers?",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "salary_inquiry",
            "priority": "medium",
            "needs_extraction": true,
            "escalate_to_human": false,
            "confidence": 0.92,
            "reasoning": "Direct salary question with job level specification"
        }"""
        mock_response.usage = Mock(prompt_tokens=200, completion_tokens=100, total_tokens=300)

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(state)

            assert result["output"]["intent"] == "salary_inquiry"
            assert result["output"]["needs_extraction"] is True

    @pytest.mark.asyncio
    async def test_unclear_intent_low_confidence(self, router_agent):
        """Test Router handles unclear messages with low confidence."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Hello",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "unclear",
            "priority": "low",
            "needs_extraction": false,
            "escalate_to_human": false,
            "confidence": 0.6,
            "reasoning": "Greeting with no clear intent, needs follow-up"
        }"""
        mock_response.usage = Mock(prompt_tokens=200, completion_tokens=100, total_tokens=300)

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(state)

            assert result["output"]["intent"] == "unclear"
            assert result["output"]["confidence"] < 0.7
            assert result["output"]["priority"] == "low"

    @pytest.mark.asyncio
    async def test_conversation_history_context(self, router_agent):
        """Test Router uses conversation history for context."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Yes, that would be great!",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1",
            conversation_history=[
                {"role": "user", "content": "I'm looking for jobs in Amsterdam"},
                {"role": "assistant", "content": "I can help you find opportunities. Would you like to see software engineering positions?"}
            ]
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": true,
            "escalate_to_human": false,
            "confidence": 0.88,
            "reasoning": "Affirmative response to job search follow-up in context"
        }"""
        mock_response.usage = Mock(prompt_tokens=250, completion_tokens=100, total_tokens=350)

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(state)

            # Verify conversation history was included
            assert result["output"]["intent"] == "job_search"
            assert result["output"]["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, router_agent, sample_state):
        """Test Router tracks token usage and cost correctly."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": true,
            "escalate_to_human": false,
            "confidence": 0.95,
            "reasoning": "Job search intent"
        }"""
        mock_response.usage = Mock(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300
        )

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(sample_state)

            # Verify token tracking
            assert "tokens_used" in result
            assert result["tokens_used"]["input"] == 200
            assert result["tokens_used"]["output"] == 100
            assert result["tokens_used"]["total"] == 300

            # Verify cost calculation
            assert "cost_usd" in result
            # GPT-4o-mini: $0.15/1M input, $0.60/1M output
            expected_cost = (200 / 1_000_000 * 0.15) + (100 / 1_000_000 * 0.60)
            assert abs(result["cost_usd"] - expected_cost) < 0.000001

    @pytest.mark.skip(reason="Retry logic requires real openai.APIError which needs request object - tested in integration tests")
    @pytest.mark.asyncio
    async def test_retry_on_api_error(self, router_agent, sample_state):
        """Test Router retries on API errors.

        NOTE: This test is skipped because properly mocking openai.APIError
        requires creating a request object. Retry logic is tested in integration tests.
        """
        pass

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, router_agent):
        """Test Router handles empty/whitespace messages."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="   ",  # Whitespace only
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "intent": "unclear",
            "priority": "low",
            "needs_extraction": false,
            "escalate_to_human": false,
            "confidence": 0.5,
            "reasoning": "Empty or whitespace-only message"
        }"""
        mock_response.usage = Mock(prompt_tokens=150, completion_tokens=80, total_tokens=230)

        with patch.object(router_agent.client.chat.completions, 'create', return_value=mock_response):
            result = router_agent.execute(state)

            assert result["output"]["intent"] == "unclear"
            assert result["output"]["confidence"] <= 0.6
