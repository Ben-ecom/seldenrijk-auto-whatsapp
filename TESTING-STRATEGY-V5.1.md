# TESTING STRATEGY V5.1: CHATWOOT-CENTRIC WHATSAPP RECRUITMENT PLATFORM

**Version**: 5.1
**Date**: 2025-10-10
**Status**: APPROVED - Ready for Implementation
**Architecture**: Chatwoot + LangGraph + 4 Agents + Agentic RAG

---

## TABLE OF CONTENTS

1. [Testing Overview](#1-testing-overview)
2. [Unit Tests](#2-unit-tests)
3. [Integration Tests](#3-integration-tests)
4. [End-to-End Tests](#4-end-to-end-tests)
5. [Performance Tests](#5-performance-tests)
6. [Manual Test Cases](#6-manual-test-cases)
7. [CI/CD Integration](#7-cicd-integration)
8. [Test Data Management](#8-test-data-management)

---

## 1. TESTING OVERVIEW

### 1.1 Testing Pyramid Strategy

```
                    ┌──────────────┐
                    │     E2E      │  15% (Critical User Journeys)
                    │   10 tests   │  Playwright + WhatsApp MCP
                    └──────────────┘
                  ┌──────────────────┐
                  │   INTEGRATION    │  25% (Service Communication)
                  │    35 tests      │  Pytest + API Mocking
                  └──────────────────┘
              ┌────────────────────────┐
              │      UNIT TESTS        │  60% (Component-Level)
              │       80 tests         │  Pytest + Mocking
              └────────────────────────┘
```

### 1.2 Coverage Goals

| Component | Target Coverage | Priority | Test Count |
|-----------|----------------|----------|------------|
| **Router Agent** | 90% | Critical | 15 tests |
| **Extraction Agent** | 95% | Critical | 20 tests |
| **Conversation Agent** | 85% | Critical | 25 tests |
| **CRM Agent** | 90% | Critical | 20 tests |
| **LangGraph Orchestration** | 85% | High | 15 tests |
| **FastAPI Webhook** | 90% | High | 10 tests |
| **Vector Search** | 85% | Medium | 10 tests |
| **Overall Target** | **80%+** | - | **125+ tests** |

### 1.3 Test Automation Framework

**Primary Tools**:
- **pytest** (≥8.0.0): Unit, integration, and API testing
- **pytest-asyncio** (≥0.23.0): Async test support for FastAPI and agents
- **pytest-mock** (≥3.12.0): Mocking external APIs (Claude, OpenAI)
- **pytest-cov** (≥4.1.0): Coverage reporting
- **httpx** (≥0.26.0): HTTP client for API testing
- **Playwright** (≥1.40.0): End-to-end browser automation
- **WhatsApp MCP**: WhatsApp testing integration

**Test Structure**:
```
tests/
├── unit/
│   ├── test_router_agent.py
│   ├── test_extraction_agent.py
│   ├── test_conversation_agent.py
│   ├── test_crm_agent.py
│   └── test_vector_search.py
├── integration/
│   ├── test_langgraph_flow.py
│   ├── test_chatwoot_api.py
│   ├── test_webhook_receiver.py
│   └── test_database.py
├── e2e/
│   ├── test_recruitment_flow.py
│   ├── test_ecommerce_flow.py
│   └── test_dubai_business_flow.py
├── performance/
│   ├── test_load.py
│   └── test_response_time.py
├── conftest.py  # Shared fixtures
└── pytest.ini   # Configuration
```

### 1.4 Testing Environment Configuration

**pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
    --tb=short
    --strict-markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (medium speed, some external deps)
    e2e: End-to-end tests (slow, full system)
    performance: Performance and load tests
    slow: Tests that take >5 seconds
    skip_ci: Skip in CI environment
```

**Environment Variables** (`.env.test`):
```bash
# Test Environment
ENVIRONMENT=test
DEBUG=True

# Mock API Keys (not real)
ANTHROPIC_API_KEY=test_claude_key_mock
OPENAI_API_KEY=test_openai_key_mock
PYDANTIC_AI_API_KEY=test_pydantic_key_mock

# Chatwoot Test Instance
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_TOKEN=test_token

# Test Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatwoot_test
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Supabase Test Instance
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=test_key

# Test Configuration
MOCK_EXTERNAL_APIS=True
RATE_LIMIT_TESTING=False
```

---

## 2. UNIT TESTS

### 2.1 Pytest Setup and Fixtures

**conftest.py** (Shared fixtures):
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Fixtures for mocking external APIs
@pytest.fixture
def mock_claude_client():
    """Mock Claude API client"""
    with patch('anthropic.AsyncAnthropic') as mock:
        client = AsyncMock()

        # Mock successful response
        client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Test response from Claude")],
            stop_reason="end_turn"
        )

        mock.return_value = client
        yield client

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI API client"""
    with patch('openai.AsyncOpenAI') as mock:
        client = AsyncMock()

        # Mock GPT-4o-mini response
        client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="product_inquiry")
                )
            ]
        )

        mock.return_value = client
        yield client

@pytest.fixture
def mock_pydantic_ai_agent():
    """Mock Pydantic AI agent"""
    with patch('pydantic_ai.Agent') as mock:
        agent = AsyncMock()

        # Mock extraction result
        agent.run.return_value = MagicMock(
            data={
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+31612345678",
                "budget_min": 70000,
                "budget_max": 90000,
                "job_type": "interim",
                "urgency": "high",
                "intent": "job_search",
                "key_phrases": ["tech", "interim", "Amsterdam"]
            }
        )

        mock.return_value = agent
        yield agent

@pytest.fixture
def mock_chatwoot_api():
    """Mock Chatwoot API client"""
    with patch('httpx.AsyncClient') as mock:
        client = AsyncMock()

        # Mock contact update
        client.patch.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": 123, "custom_attributes": {}}
        )

        # Mock message creation
        client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": 456, "content": "Message sent"}
        )

        mock.return_value = client
        yield client

@pytest.fixture
def mock_vector_db():
    """Mock Supabase PGVector database"""
    with patch('supabase.create_client') as mock:
        client = MagicMock()

        # Mock vector search results
        client.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": 1,
                    "content": "Return policy: 30 days full refund",
                    "metadata": {"category": "policy", "title": "Returns"},
                    "similarity": 0.89
                },
                {
                    "id": 2,
                    "content": "Shipping: 2-3 business days",
                    "metadata": {"category": "policy", "title": "Shipping"},
                    "similarity": 0.75
                }
            ]
        )

        mock.return_value = client
        yield client

@pytest.fixture
def sample_conversation_state() -> Dict[str, Any]:
    """Sample LangGraph ConversationState for testing"""
    return {
        "message_id": "msg_123",
        "conversation_id": "conv_456",
        "contact_id": "contact_789",
        "account_id": "account_1",
        "channel": "whatsapp",
        "message_content": "I'm looking for an interim tech role in Amsterdam",
        "message_type": "incoming",
        "intent": None,
        "priority": None,
        "sentiment": None,
        "extracted_data": None,
        "rag_results": None,
        "agent_response": None,
        "needs_human": False,
        "route": "automated",
        "contact_profile": {},
        "conversation_history": []
    }

@pytest.fixture
def sample_chatwoot_webhook_payload() -> Dict[str, Any]:
    """Sample Chatwoot webhook payload"""
    return {
        "event": "message_created",
        "message_type": "incoming",
        "id": 123,
        "content": "What's your return policy?",
        "inbox": {"id": 1, "name": "WhatsApp"},
        "conversation": {
            "id": 456,
            "contact_id": 789,
            "account_id": 1
        },
        "sender": {
            "id": 789,
            "name": "Test User",
            "phone_number": "+31612345678"
        }
    }
```

### 2.2 Router Agent Tests (15 tests, 90% coverage)

**tests/unit/test_router_agent.py**:
```python
import pytest
from src.agents.router_agent import router_agent_node, classify_intent

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_product_inquiry(mock_openai_client, sample_conversation_state):
    """Test router correctly classifies product inquiry"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Do you have size 42 sneakers in stock?"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "product_inquiry"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "product_inquiry"
    assert result["priority"] == "medium"
    mock_openai_client.chat.completions.create.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_policy_question(mock_openai_client, sample_conversation_state):
    """Test router classifies policy questions"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "What's your return policy?"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "policy_question"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "policy_question"
    assert "priority" in result

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_job_search(mock_openai_client, sample_conversation_state):
    """Test router classifies job search queries"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "I'm looking for interim tech roles in Amsterdam"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "job_search"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "job_search"
    assert result["priority"] in ["high", "medium", "low"]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_support_request_high_priority(mock_openai_client, sample_conversation_state):
    """Test support requests get high priority"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "URGENT: My order is damaged and I need immediate replacement!"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "support_request"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "support_request"
    assert result["priority"] == "high"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_general_greeting(mock_openai_client, sample_conversation_state):
    """Test router classifies greetings as general"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Hello! How are you?"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "general"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "general"
    assert result["priority"] == "low"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_sentiment_analysis(mock_openai_client, sample_conversation_state):
    """Test router performs sentiment analysis"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "I'm very unhappy with your service!"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert "sentiment" in result
    assert -1.0 <= result["sentiment"] <= 1.0

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_empty_message(mock_openai_client, sample_conversation_state):
    """Test router handles empty messages gracefully"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = ""

    # Act & Assert
    with pytest.raises(ValueError, match="Empty message content"):
        await router_agent_node(state)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_api_failure_retry(mock_openai_client, sample_conversation_state):
    """Test router retries on API failure"""
    # Arrange
    state = sample_conversation_state.copy()
    mock_openai_client.chat.completions.create.side_effect = [
        Exception("API timeout"),
        MagicMock(choices=[MagicMock(message=MagicMock(content="product_inquiry"))])
    ]

    # Act
    result = await router_agent_node(state, max_retries=2)

    # Assert
    assert result["intent"] == "product_inquiry"
    assert mock_openai_client.chat.completions.create.call_count == 2

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_qualification_intent(mock_openai_client, sample_conversation_state):
    """Test router identifies lead qualification queries"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "My budget is €70-90k for interim roles"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "qualification"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "qualification"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_multi_language_support(mock_openai_client, sample_conversation_state):
    """Test router handles Dutch language"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Ik zoek een interim baan in tech"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "job_search"

    # Act
    result = await router_agent_node(state)

    # Assert
    assert result["intent"] == "job_search"
```

### 2.3 Extraction Agent Tests (20 tests, 95% coverage)

**tests/unit/test_extraction_agent.py**:
```python
import pytest
from src.agents.extraction_agent import extraction_agent_node, ExtractedData

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_complete_profile(mock_pydantic_ai_agent, sample_conversation_state):
    """Test extraction of complete contact profile"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = """
    Hi, I'm John Doe (john@example.com, +31612345678).
    Looking for interim tech roles in Amsterdam, budget €70-90k.
    Need to start ASAP.
    """

    # Act
    result = await extraction_agent_node(state)

    # Assert
    extracted = result["extracted_data"]
    assert extracted["name"] == "John Doe"
    assert extracted["email"] == "john@example.com"
    assert extracted["phone"] == "+31612345678"
    assert extracted["budget_min"] == 70000
    assert extracted["budget_max"] == 90000
    assert extracted["job_type"] == "interim"
    assert extracted["urgency"] == "high"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_partial_data(mock_pydantic_ai_agent, sample_conversation_state):
    """Test extraction with missing fields"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Looking for a job, budget around €50k"

    mock_pydantic_ai_agent.run.return_value.data = {
        "name": None,
        "email": None,
        "phone": None,
        "budget_min": 50000,
        "budget_max": None,
        "job_type": None,
        "urgency": "medium",
        "intent": "job_search",
        "key_phrases": ["job", "budget"]
    }

    # Act
    result = await extraction_agent_node(state)

    # Assert
    extracted = result["extracted_data"]
    assert extracted["budget_min"] == 50000
    assert extracted["name"] is None
    assert extracted["urgency"] == "medium"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_email_validation(mock_pydantic_ai_agent, sample_conversation_state):
    """Test email validation in extracted data"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "My email is invalid-email"

    mock_pydantic_ai_agent.run.return_value.data = {
        "email": "invalid-email",
        "urgency": "low",
        "intent": "general"
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid email format"):
        await extraction_agent_node(state, validate_email=True)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_phone_formatting(mock_pydantic_ai_agent, sample_conversation_state):
    """Test phone number formatting"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Call me at 0612345678"

    mock_pydantic_ai_agent.run.return_value.data = {
        "phone": "0612345678",
        "urgency": "low",
        "intent": "general"
    }

    # Act
    result = await extraction_agent_node(state, country_code="NL")

    # Assert
    # Should format to international format
    assert result["extracted_data"]["phone"] == "+31612345678"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_budget_ranges(mock_pydantic_ai_agent, sample_conversation_state):
    """Test budget range extraction"""
    # Arrange
    test_cases = [
        ("Budget €70-90k", 70000, 90000),
        ("Around €50000", 50000, None),
        ("Up to 100k", None, 100000),
        ("€60k-€80k per year", 60000, 80000)
    ]

    for message, expected_min, expected_max in test_cases:
        state = sample_conversation_state.copy()
        state["message_content"] = message

        mock_pydantic_ai_agent.run.return_value.data = {
            "budget_min": expected_min,
            "budget_max": expected_max,
            "urgency": "medium",
            "intent": "qualification"
        }

        # Act
        result = await extraction_agent_node(state)

        # Assert
        assert result["extracted_data"]["budget_min"] == expected_min
        assert result["extracted_data"]["budget_max"] == expected_max

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_job_types(mock_pydantic_ai_agent, sample_conversation_state):
    """Test job type classification"""
    # Arrange
    job_type_tests = [
        ("Looking for interim work", "interim"),
        ("Permanent position preferred", "permanent"),
        ("Freelance gigs", "freelance")
    ]

    for message, expected_type in job_type_tests:
        state = sample_conversation_state.copy()
        state["message_content"] = message

        mock_pydantic_ai_agent.run.return_value.data = {
            "job_type": expected_type,
            "urgency": "medium",
            "intent": "job_search"
        }

        # Act
        result = await extraction_agent_node(state)

        # Assert
        assert result["extracted_data"]["job_type"] == expected_type

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_urgency_levels(mock_pydantic_ai_agent, sample_conversation_state):
    """Test urgency level classification"""
    # Arrange
    urgency_tests = [
        ("URGENT! Need to start immediately!", "high"),
        ("Looking to start in a few months", "low"),
        ("Sometime next month", "medium")
    ]

    for message, expected_urgency in urgency_tests:
        state = sample_conversation_state.copy()
        state["message_content"] = message

        mock_pydantic_ai_agent.run.return_value.data = {
            "urgency": expected_urgency,
            "intent": "job_search"
        }

        # Act
        result = await extraction_agent_node(state)

        # Assert
        assert result["extracted_data"]["urgency"] == expected_urgency

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_key_phrases(mock_pydantic_ai_agent, sample_conversation_state):
    """Test key phrase extraction"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Tech interim role in Amsterdam with React and Python experience"

    mock_pydantic_ai_agent.run.return_value.data = {
        "key_phrases": ["tech", "interim", "Amsterdam", "React", "Python"],
        "urgency": "medium",
        "intent": "job_search"
    }

    # Act
    result = await extraction_agent_node(state)

    # Assert
    assert "React" in result["extracted_data"]["key_phrases"]
    assert "Python" in result["extracted_data"]["key_phrases"]
    assert "Amsterdam" in result["extracted_data"]["key_phrases"]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extraction_pydantic_validation(sample_conversation_state):
    """Test Pydantic model validation"""
    # Arrange
    invalid_data = {
        "urgency": "invalid_value",  # Should be "high", "medium", or "low"
        "intent": "job_search"
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid urgency level"):
        ExtractedData(**invalid_data)
```

### 2.4 Conversation Agent Tests (25 tests, 85% coverage)

**tests/unit/test_conversation_agent.py**:
```python
import pytest
from src.agents.conversation_agent import conversation_agent_node, should_search_kb

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_simple_response(mock_claude_client, sample_conversation_state):
    """Test conversation agent generates simple response without RAG"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Hello!"

    mock_claude_client.messages.create.return_value.stop_reason = "end_turn"
    mock_claude_client.messages.create.return_value.content[0].text = "Hello! How can I help you today?"

    # Act
    result = await conversation_agent_node(state)

    # Assert
    assert result["agent_response"] == "Hello! How can I help you today?"
    assert result.get("rag_results") is None  # No RAG triggered
    mock_claude_client.messages.create.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_with_agentic_rag(mock_claude_client, mock_vector_db, sample_conversation_state):
    """Test agentic RAG: Agent decides to search knowledge base"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "What's your return policy?"

    # First call: Agent decides to use search tool
    tool_use_response = MagicMock(
        stop_reason="tool_use",
        content=[
            MagicMock(
                type="tool_use",
                id="tool_123",
                name="search_knowledge_base",
                input={"query": "return policy", "category": "policy"}
            )
        ]
    )

    # Second call: Agent generates response with KB results
    final_response = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(text="We offer a 30-day return policy with full refund.")]
    )

    mock_claude_client.messages.create.side_effect = [tool_use_response, final_response]

    # Act
    result = await conversation_agent_node(state)

    # Assert
    assert "30-day" in result["agent_response"]
    assert result["rag_results"] is not None
    assert len(result["rag_results"]) > 0
    assert mock_claude_client.messages.create.call_count == 2  # Tool call + response

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_rag_no_results(mock_claude_client, mock_vector_db, sample_conversation_state):
    """Test RAG when no relevant documents found"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Do you sell unicorns?"

    # Mock empty search results
    mock_vector_db.rpc.return_value.execute.return_value.data = []

    tool_use_response = MagicMock(
        stop_reason="tool_use",
        content=[
            MagicMock(
                type="tool_use",
                id="tool_123",
                name="search_knowledge_base",
                input={"query": "unicorns"}
            )
        ]
    )

    final_response = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(text="I don't have information about that. Let me connect you with a human.")]
    )

    mock_claude_client.messages.create.side_effect = [tool_use_response, final_response]

    # Act
    result = await conversation_agent_node(state)

    # Assert
    assert "don't have information" in result["agent_response"]
    assert result["rag_results"] == []

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_context_preservation(mock_claude_client, sample_conversation_state):
    """Test conversation maintains context across turns"""
    # Arrange
    state = sample_conversation_state.copy()
    state["conversation_history"] = [
        {"role": "user", "content": "I'm looking for a job"},
        {"role": "assistant", "content": "What type of job are you interested in?"},
        {"role": "user", "content": "Tech roles"}
    ]
    state["message_content"] = "Do you have any interim positions?"

    # Act
    result = await conversation_agent_node(state)

    # Assert
    call_args = mock_claude_client.messages.create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) > 1  # Context included
    assert any("Tech roles" in str(msg) for msg in messages)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_max_tokens_limit(mock_claude_client, sample_conversation_state):
    """Test conversation respects max tokens limit"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Tell me everything about your company"

    # Act
    await conversation_agent_node(state, max_tokens=512)

    # Assert
    call_args = mock_claude_client.messages.create.call_args
    assert call_args.kwargs["max_tokens"] == 512

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_system_prompt_injection(mock_claude_client, sample_conversation_state):
    """Test system prompt is correctly injected"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "Hello"
    custom_system_prompt = "You are a helpful recruitment assistant."

    # Act
    await conversation_agent_node(state, system_prompt=custom_system_prompt)

    # Assert
    call_args = mock_claude_client.messages.create.call_args
    assert call_args.kwargs.get("system") == custom_system_prompt

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_tool_calling_error_handling(mock_claude_client, mock_vector_db, sample_conversation_state):
    """Test error handling when RAG search fails"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "What's your return policy?"

    # Mock vector DB error
    mock_vector_db.rpc.side_effect = Exception("Database connection error")

    tool_use_response = MagicMock(
        stop_reason="tool_use",
        content=[
            MagicMock(
                type="tool_use",
                id="tool_123",
                name="search_knowledge_base",
                input={"query": "return policy"}
            )
        ]
    )

    mock_claude_client.messages.create.return_value = tool_use_response

    # Act & Assert
    with pytest.raises(Exception, match="RAG search failed"):
        await conversation_agent_node(state)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_multi_turn_rag(mock_claude_client, mock_vector_db, sample_conversation_state):
    """Test RAG across multiple conversation turns"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "What about shipping?"
    state["conversation_history"] = [
        {"role": "user", "content": "What's your return policy?"},
        {"role": "assistant", "content": "30-day return policy"}
    ]

    tool_use_response = MagicMock(
        stop_reason="tool_use",
        content=[
            MagicMock(
                type="tool_use",
                id="tool_456",
                name="search_knowledge_base",
                input={"query": "shipping policy"}
            )
        ]
    )

    final_response = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(text="Shipping takes 2-3 business days.")]
    )

    mock_claude_client.messages.create.side_effect = [tool_use_response, final_response]

    # Act
    result = await conversation_agent_node(state)

    # Assert
    assert "2-3 business days" in result["agent_response"]
```

### 2.5 CRM Agent Tests (20 tests, 90% coverage)

**tests/unit/test_crm_agent.py**:
```python
import pytest
from src.agents.crm_agent import crm_agent_node, determine_lead_status, determine_labels

@pytest.mark.unit
@pytest.mark.asyncio
async def test_crm_update_contact_attributes(mock_chatwoot_api, sample_conversation_state):
    """Test CRM agent updates Chatwoot contact custom attributes"""
    # Arrange
    state = sample_conversation_state.copy()
    state["extracted_data"] = {
        "name": "John Doe",
        "email": "john@example.com",
        "budget_min": 70000,
        "budget_max": 90000,
        "job_type": "interim",
        "urgency": "high",
        "intent": "job_search"
    }
    state["contact_id"] = "contact_789"

    # Act
    result = await crm_agent_node(state)

    # Assert
    assert result["crm_updated"] is True
    mock_chatwoot_api.patch.assert_called_once()

    call_args = mock_chatwoot_api.patch.call_args
    payload = call_args.kwargs["json"]
    assert payload["custom_attributes"]["lead_status"] == "qualified"
    assert payload["custom_attributes"]["budget_range"] == "€70000-90000"
    assert payload["custom_attributes"]["job_type_preference"] == "interim"
    assert payload["custom_attributes"]["urgency_level"] == "high"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_crm_add_labels(mock_chatwoot_api, sample_conversation_state):
    """Test CRM agent adds appropriate labels"""
    # Arrange
    state = sample_conversation_state.copy()
    state["extracted_data"] = {
        "job_type": "interim",
        "urgency": "high",
        "intent": "job_search",
        "budget_min": 80000
    }
    state["contact_id"] = "contact_789"
    state["intent"] = "job_search"
    state["priority"] = "high"

    # Act
    result = await crm_agent_node(state)

    # Assert
    assert result["crm_updated"] is True
    # Labels call should be made
    assert mock_chatwoot_api.post.called or mock_chatwoot_api.patch.called

@pytest.mark.unit
def test_determine_lead_status_qualified():
    """Test lead status determination for qualified leads"""
    # Arrange
    extracted_data = {
        "budget_min": 70000,
        "urgency": "high",
        "job_type": "interim"
    }

    # Act
    status = determine_lead_status(extracted_data)

    # Assert
    assert status == "qualified"

@pytest.mark.unit
def test_determine_lead_status_unqualified():
    """Test lead status determination for unqualified leads"""
    # Arrange
    extracted_data = {
        "budget_min": None,
        "urgency": "low",
        "job_type": None
    }

    # Act
    status = determine_lead_status(extracted_data)

    # Assert
    assert status == "unqualified"

@pytest.mark.unit
def test_determine_labels_high_priority():
    """Test label determination for high priority leads"""
    # Arrange
    state = {
        "intent": "job_search",
        "priority": "high",
        "extracted_data": {
            "urgency": "high",
            "budget_min": 90000
        }
    }

    # Act
    labels = determine_labels(state)

    # Assert
    assert "high-priority" in labels
    assert "qualified-lead" in labels

@pytest.mark.unit
@pytest.mark.asyncio
async def test_crm_ai_summary_generation(mock_openai_client, mock_chatwoot_api, sample_conversation_state):
    """Test AI summary generation for CRM"""
    # Arrange
    state = sample_conversation_state.copy()
    state["extracted_data"] = {
        "name": "John Doe",
        "job_type": "interim",
        "budget_min": 70000,
        "urgency": "high"
    }
    state["conversation_history"] = [
        {"role": "user", "content": "Looking for tech interim role"},
        {"role": "assistant", "content": "What's your budget?"},
        {"role": "user", "content": "€70-90k"}
    ]

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = (
        "Qualified lead seeking interim tech role in Amsterdam, budget €70-90k, high urgency."
    )

    # Act
    result = await crm_agent_node(state)

    # Assert
    call_args = mock_chatwoot_api.patch.call_args
    payload = call_args.kwargs["json"]
    assert "ai_summary" in payload["custom_attributes"]
    assert "interim tech role" in payload["custom_attributes"]["ai_summary"]

@pytest.mark.unit
@pytest.mark.asyncio
async def test_crm_update_existing_contact(mock_chatwoot_api, sample_conversation_state):
    """Test CRM agent updates existing contact without overwriting"""
    # Arrange
    state = sample_conversation_state.copy()
    state["contact_profile"] = {
        "custom_attributes": {
            "previous_data": "should_not_be_lost",
            "lead_status": "warm"
        }
    }
    state["extracted_data"] = {
        "job_type": "interim",
        "urgency": "high"
    }

    # Act
    result = await crm_agent_node(state, merge_attributes=True)

    # Assert
    call_args = mock_chatwoot_api.patch.call_args
    payload = call_args.kwargs["json"]
    # Should preserve previous_data
    assert "previous_data" in payload.get("custom_attributes", {})
```

### 2.6 Vector Search Tests (10 tests, 85% coverage)

**tests/unit/test_vector_search.py**:
```python
import pytest
from src.services.vector_search import search_knowledge_base, embed_query, create_document

@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_policy_query(mock_vector_db, mock_openai_client):
    """Test vector search for policy questions"""
    # Arrange
    query = "What is your return policy?"

    mock_openai_client.embeddings.create.return_value.data[0].embedding = [0.1] * 1536

    # Act
    results = await search_knowledge_base(query, category="policy")

    # Assert
    assert len(results) > 0
    assert results[0]["metadata"]["category"] == "policy"
    assert results[0]["similarity"] > 0.7

@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_with_threshold(mock_vector_db):
    """Test vector search with similarity threshold"""
    # Arrange
    query = "shipping information"
    threshold = 0.8

    # Act
    results = await search_knowledge_base(query, match_threshold=threshold)

    # Assert
    # All results should meet threshold
    assert all(r["similarity"] >= threshold for r in results)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_query(mock_openai_client):
    """Test query embedding generation"""
    # Arrange
    query = "Test query"
    mock_openai_client.embeddings.create.return_value.data[0].embedding = [0.5] * 1536

    # Act
    embedding = await embed_query(query)

    # Assert
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_document(mock_vector_db, mock_openai_client):
    """Test document creation with embedding"""
    # Arrange
    content = "Our return policy is 30 days"
    metadata = {"category": "policy", "title": "Returns"}

    mock_openai_client.embeddings.create.return_value.data[0].embedding = [0.1] * 1536

    # Act
    doc_id = await create_document(content, metadata)

    # Assert
    assert doc_id is not None
    mock_vector_db.table.assert_called()
```

---

## 3. INTEGRATION TESTS

### 3.1 LangGraph End-to-End Flow (15 tests)

**tests/integration/test_langgraph_flow.py**:
```python
import pytest
from src.langgraph_app import app, ConversationState

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_agent_flow_job_search(
    mock_openai_client,
    mock_pydantic_ai_agent,
    mock_claude_client,
    mock_chatwoot_api,
    sample_conversation_state
):
    """Test complete flow: Router → Extraction → Conversation → CRM"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "I'm looking for interim tech role in Amsterdam, budget €70-90k"

    # Mock responses
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "job_search"

    mock_pydantic_ai_agent.run.return_value.data = {
        "job_type": "interim",
        "budget_min": 70000,
        "budget_max": 90000,
        "urgency": "high",
        "intent": "job_search",
        "key_phrases": ["tech", "Amsterdam", "interim"]
    }

    mock_claude_client.messages.create.return_value.stop_reason = "end_turn"
    mock_claude_client.messages.create.return_value.content[0].text = "Great! I found 3 matching positions..."

    # Act
    final_state = await app.ainvoke(state)

    # Assert
    assert final_state["intent"] == "job_search"
    assert final_state["extracted_data"] is not None
    assert final_state["agent_response"] is not None
    assert final_state["crm_updated"] is True

    # Verify all agents were called
    mock_openai_client.chat.completions.create.assert_called()
    mock_pydantic_ai_agent.run.assert_called()
    mock_claude_client.messages.create.assert_called()
    mock_chatwoot_api.patch.assert_called()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_human_takeover_flow(
    mock_openai_client,
    mock_pydantic_ai_agent,
    sample_conversation_state
):
    """Test flow stops and routes to human for high-priority issues"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "URGENT! My order is damaged and I need immediate help!"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "support_request"

    mock_pydantic_ai_agent.run.return_value.data = {
        "urgency": "high",
        "intent": "support_request"
    }

    # Act
    final_state = await app.ainvoke(state)

    # Assert
    assert final_state["needs_human"] is True
    assert final_state["priority"] == "high"
    # Conversation agent should NOT be called for human-routed messages
    assert final_state.get("agent_response") is None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agentic_rag_integration(
    mock_openai_client,
    mock_pydantic_ai_agent,
    mock_claude_client,
    mock_vector_db,
    sample_conversation_state
):
    """Test integration of agentic RAG in full flow"""
    # Arrange
    state = sample_conversation_state.copy()
    state["message_content"] = "What's your return policy?"

    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "policy_question"

    # Claude decides to search KB
    tool_use_response = MagicMock(
        stop_reason="tool_use",
        content=[
            MagicMock(
                type="tool_use",
                id="tool_123",
                name="search_knowledge_base",
                input={"query": "return policy", "category": "policy"}
            )
        ]
    )

    final_response = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(text="We offer a 30-day return policy.")]
    )

    mock_claude_client.messages.create.side_effect = [tool_use_response, final_response]

    # Act
    final_state = await app.ainvoke(state)

    # Assert
    assert final_state["intent"] == "policy_question"
    assert final_state["rag_results"] is not None
    assert len(final_state["rag_results"]) > 0
    assert "30-day" in final_state["agent_response"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_recovery_in_flow(
    mock_openai_client,
    mock_pydantic_ai_agent,
    sample_conversation_state
):
    """Test LangGraph error recovery and retry logic"""
    # Arrange
    state = sample_conversation_state.copy()

    # First call fails, second succeeds
    mock_openai_client.chat.completions.create.side_effect = [
        Exception("API timeout"),
        MagicMock(choices=[MagicMock(message=MagicMock(content="general"))])
    ]

    # Act
    final_state = await app.ainvoke(state, max_retries=2)

    # Assert
    assert final_state["intent"] == "general"
    assert mock_openai_client.chat.completions.create.call_count == 2

@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_channel_flow(
    mock_openai_client,
    mock_pydantic_ai_agent,
    mock_claude_client,
    sample_conversation_state
):
    """Test flow handles different channels (WhatsApp, Instagram, Email)"""
    # Test for each channel
    channels = ["whatsapp", "instagram", "email"]

    for channel in channels:
        state = sample_conversation_state.copy()
        state["channel"] = channel
        state["message_content"] = "Hello"

        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "general"

        # Act
        final_state = await app.ainvoke(state)

        # Assert
        assert final_state["channel"] == channel
        assert final_state["intent"] == "general"
```

### 3.2 Chatwoot API Integration (8 tests)

**tests/integration/test_chatwoot_api.py**:
```python
import pytest
import httpx
from src.services.chatwoot_client import ChatwootClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chatwoot_create_contact():
    """Test creating a new contact in Chatwoot"""
    # Arrange
    client = ChatwootClient(
        base_url="http://localhost:3000",
        api_token="test_token",
        account_id="1"
    )

    contact_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone_number": "+31612345678"
    }

    # Act
    async with httpx.AsyncClient() as http_client:
        with pytest.mock.patch.object(http_client, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "payload": {"contact": {"id": 123}}
            }

            contact_id = await client.create_contact(contact_data)

    # Assert
    assert contact_id == 123

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chatwoot_update_custom_attributes():
    """Test updating contact custom attributes"""
    # Arrange
    client = ChatwootClient(
        base_url="http://localhost:3000",
        api_token="test_token",
        account_id="1"
    )

    custom_attributes = {
        "lead_status": "qualified",
        "budget_range": "€70-90k"
    }

    # Act
    async with httpx.AsyncClient() as http_client:
        with pytest.mock.patch.object(http_client, 'patch') as mock_patch:
            mock_patch.return_value.status_code = 200

            success = await client.update_contact_attributes(
                contact_id=123,
                custom_attributes=custom_attributes
            )

    # Assert
    assert success is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chatwoot_send_message():
    """Test sending message via Chatwoot"""
    # Arrange
    client = ChatwootClient(
        base_url="http://localhost:3000",
        api_token="test_token",
        account_id="1"
    )

    # Act
    async with httpx.AsyncClient() as http_client:
        with pytest.mock.patch.object(http_client, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"id": 456}

            message_id = await client.send_message(
                conversation_id=123,
                content="Test message"
            )

    # Assert
    assert message_id == 456

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chatwoot_add_labels():
    """Test adding labels to contact"""
    # Arrange
    client = ChatwootClient(
        base_url="http://localhost:3000",
        api_token="test_token",
        account_id="1"
    )

    labels = ["qualified-lead", "high-priority"]

    # Act
    async with httpx.AsyncClient() as http_client:
        with pytest.mock.patch.object(http_client, 'post') as mock_post:
            mock_post.return_value.status_code = 200

            success = await client.add_labels(
                contact_id=123,
                labels=labels
            )

    # Assert
    assert success is True
```

### 3.3 FastAPI Webhook Integration (7 tests)

**tests/integration/test_webhook_receiver.py**:
```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.mark.integration
def test_chatwoot_webhook_message_created(sample_chatwoot_webhook_payload):
    """Test webhook receiver processes message_created event"""
    # Arrange
    payload = sample_chatwoot_webhook_payload

    # Act
    response = client.post("/webhooks/chatwoot", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

@pytest.mark.integration
def test_chatwoot_webhook_invalid_event():
    """Test webhook rejects invalid event types"""
    # Arrange
    payload = {
        "event": "invalid_event",
        "message_type": "incoming"
    }

    # Act
    response = client.post("/webhooks/chatwoot", json=payload)

    # Assert
    assert response.status_code == 400

@pytest.mark.integration
def test_chatwoot_webhook_outgoing_message():
    """Test webhook ignores outgoing messages (agent-sent)"""
    # Arrange
    payload = {
        "event": "message_created",
        "message_type": "outgoing",  # From agent
        "content": "Hello"
    }

    # Act
    response = client.post("/webhooks/chatwoot", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

@pytest.mark.integration
def test_chatwoot_webhook_authentication():
    """Test webhook requires authentication"""
    # Arrange
    payload = {"event": "message_created"}

    # Act
    response = client.post(
        "/webhooks/chatwoot",
        json=payload,
        headers={"Authorization": "Bearer invalid_token"}
    )

    # Assert
    assert response.status_code == 401

@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_triggers_langgraph(sample_chatwoot_webhook_payload):
    """Test webhook successfully triggers LangGraph processing"""
    # Arrange
    payload = sample_chatwoot_webhook_payload

    # Act
    response = client.post("/webhooks/chatwoot", json=payload)

    # Assert
    assert response.status_code == 200
    # Should trigger background task
    assert "task_id" in response.json()
```

### 3.4 Database Integration (5 tests)

**tests/integration/test_database.py**:
```python
import pytest
import asyncpg
from src.database import get_db_connection, execute_query

@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_connection():
    """Test PostgreSQL connection"""
    # Act
    conn = await get_db_connection()

    # Assert
    assert conn is not None

    # Cleanup
    await conn.close()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_search_function():
    """Test PGVector match_documents function"""
    # Arrange
    query_embedding = [0.1] * 1536

    # Act
    results = await execute_query(
        "SELECT * FROM match_documents($1, $2, $3)",
        query_embedding,
        0.7,  # threshold
        5  # limit
    )

    # Assert
    assert isinstance(results, list)
```

---

## 4. END-TO-END TESTS

### 4.1 Recruitment Flow E2E (Use Case 1)

**tests/e2e/test_recruitment_flow.py**:
```python
import pytest
from playwright.async_api import async_playwright
from src.mcp.whatsapp_mcp import WhatsAppMCP

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_recruitment_lead_qualification_flow():
    """
    Test complete recruitment flow:
    1. Lead registers on website
    2. Receives WhatsApp link
    3. Chats about job search
    4. AI qualifies lead
    5. Updates CRM
    6. Human reviews in Chatwoot
    """
    # Arrange
    whatsapp = WhatsAppMCP()
    lead_phone = "+31612345678"

    # Act: Send initial message
    await whatsapp.send_message(
        to=lead_phone,
        message="Hi! I'm looking for interim tech roles in Amsterdam. Budget €70-90k."
    )

    # Wait for agent response
    await asyncio.sleep(3)

    response = await whatsapp.get_latest_message(lead_phone)

    # Assert: Agent should respond with vacancy information
    assert response is not None
    assert "positions" in response.lower() or "vacancies" in response.lower()

    # Verify CRM update
    chatwoot = ChatwootClient(...)
    contact = await chatwoot.get_contact_by_phone(lead_phone)

    assert contact["custom_attributes"]["lead_status"] == "qualified"
    assert contact["custom_attributes"]["job_type_preference"] == "interim"
    assert "qualified-lead" in [label["title"] for label in contact["labels"]]

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_recruitment_rag_vacancy_search():
    """Test agentic RAG searches for matching vacancies"""
    # Arrange
    whatsapp = WhatsAppMCP()
    lead_phone = "+31612345678"

    # Upload test vacancy to knowledge base
    await create_document(
        content="Senior React Developer - Amsterdam - €80-100k - Interim 6 months",
        metadata={"category": "vacancy", "title": "React Dev", "location": "Amsterdam"}
    )

    # Act: Ask about vacancies
    await whatsapp.send_message(
        to=lead_phone,
        message="Do you have React developer positions in Amsterdam?"
    )

    await asyncio.sleep(3)
    response = await whatsapp.get_latest_message(lead_phone)

    # Assert: Should mention the vacancy
    assert "React" in response
    assert "Amsterdam" in response
    assert "80" in response or "100" in response  # Salary range

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_recruitment_human_takeover():
    """Test human takeover for complex questions"""
    # Arrange
    whatsapp = WhatsAppMCP()
    lead_phone = "+31612345678"

    # Act: Ask complex question requiring human
    await whatsapp.send_message(
        to=lead_phone,
        message="I need to negotiate contract terms and have specific requirements about remote work, benefits, and stock options."
    )

    await asyncio.sleep(3)

    # Assert: Check Chatwoot conversation status
    chatwoot = ChatwootClient(...)
    conversation = await chatwoot.get_conversation_by_phone(lead_phone)

    assert conversation["status"] == "pending"  # Waiting for human
    assert conversation["custom_attributes"]["needs_human"] is True
```

### 4.2 E-commerce Flow E2E (Use Case 2)

**tests/e2e/test_ecommerce_flow.py**:
```python
import pytest
from src.mcp.whatsapp_mcp import WhatsAppMCP
from src.mcp.instagram_mcp import InstagramMCP

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_instagram_to_whatsapp_handoff():
    """
    Test multi-channel flow:
    1. Customer DMs on Instagram
    2. Agent responds with product info
    3. Customer switches to WhatsApp
    4. Context preserved across channels
    """
    # Arrange
    instagram = InstagramMCP()
    whatsapp = WhatsAppMCP()
    customer_instagram = "@testcustomer"
    customer_phone = "+31612345678"

    # Act 1: Instagram DM
    await instagram.send_dm(
        to=customer_instagram,
        message="Do you have size 42 sneakers in stock?"
    )

    await asyncio.sleep(3)
    ig_response = await instagram.get_latest_dm(customer_instagram)

    # Assert: Instagram response
    assert "size 42" in ig_response.lower()

    # Act 2: Switch to WhatsApp
    await whatsapp.send_message(
        to=customer_phone,
        message="Hi, I asked about size 42 on Instagram. What's the price?"
    )

    await asyncio.sleep(3)
    wa_response = await whatsapp.get_latest_message(customer_phone)

    # Assert: Context preserved (agent knows about size 42 inquiry)
    assert "price" in wa_response.lower()

    # Verify CRM update
    chatwoot = ChatwootClient(...)
    contact = await chatwoot.get_contact_by_phone(customer_phone)

    assert contact["custom_attributes"]["product_interest"] == "sneakers"
    assert contact["custom_attributes"]["size_preference"] == "42"

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ecommerce_faq_rag():
    """Test agentic RAG for FAQ questions"""
    # Arrange
    whatsapp = WhatsAppMCP()
    customer_phone = "+31612345678"

    # Upload FAQ to knowledge base
    await create_document(
        content="Return Policy: 30 days full refund, no questions asked. Free return shipping.",
        metadata={"category": "faq", "title": "Returns"}
    )

    # Act: Ask FAQ question
    await whatsapp.send_message(
        to=customer_phone,
        message="What's your return policy?"
    )

    await asyncio.sleep(3)
    response = await whatsapp.get_latest_message(customer_phone)

    # Assert: Should answer from KB
    assert "30 days" in response
    assert "refund" in response.lower()
```

### 4.3 Dubai Business Flow E2E (Use Case 3)

**tests/e2e/test_dubai_business_flow.py**:
```python
import pytest
from src.mcp.whatsapp_mcp import WhatsAppMCP

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_dubai_lead_qualification():
    """
    Test Dubai business setup lead qualification:
    1. Lead fills form
    2. WhatsApp qualification conversation
    3. Budget-based filtering
    4. Qualified leads get video call scheduling
    """
    # Arrange
    whatsapp = WhatsAppMCP()
    lead_phone = "+971501234567"  # UAE number

    # Act: Initial qualification questions
    await whatsapp.send_message(
        to=lead_phone,
        message="I want to setup a tech company in Dubai. Budget is €50k. Need visa for 3 people."
    )

    await asyncio.sleep(3)
    response = await whatsapp.get_latest_message(lead_phone)

    # Assert: Should ask follow-up questions
    assert len(response) > 0

    # Verify CRM qualification
    chatwoot = ChatwootClient(...)
    contact = await chatwoot.get_contact_by_phone(lead_phone)

    # Budget > €10k = qualified
    assert contact["custom_attributes"]["lead_status"] == "qualified"
    assert "qualified" in [label["title"] for label in contact["labels"]]

    # Should include calendly link for qualified leads
    assert "calendly" in response.lower() or "schedule" in response.lower()

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_dubai_unqualified_lead():
    """Test unqualified leads get FAQ-only responses"""
    # Arrange
    whatsapp = WhatsAppMCP()
    lead_phone = "+971501234567"

    # Act: Low budget (unqualified)
    await whatsapp.send_message(
        to=lead_phone,
        message="I want to setup a company. My budget is €2k."
    )

    await asyncio.sleep(3)

    # Verify CRM
    chatwoot = ChatwootClient(...)
    contact = await chatwoot.get_contact_by_phone(lead_phone)

    # Assert: Unqualified status
    assert contact["custom_attributes"]["lead_status"] == "unqualified"
    assert "unqualified" in [label["title"] for label in contact["labels"]]
```

---

## 5. PERFORMANCE TESTS

### 5.1 Load Testing (Concurrent Messages)

**tests/performance/test_load.py**:
```python
import pytest
import asyncio
from locust import HttpUser, task, between
import time

@pytest.mark.performance
@pytest.mark.slow
class WhatsAppLoadTest(HttpUser):
    """Load test for WhatsApp webhook receiver"""
    wait_time = between(1, 3)

    @task
    def send_message_webhook(self):
        """Simulate incoming WhatsApp message"""
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "Test message for load testing",
            "conversation": {"id": 1, "contact_id": 1}
        }

        self.client.post("/webhooks/chatwoot", json=payload)

@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_message_processing():
    """Test system handles 50 concurrent messages"""
    # Arrange
    num_messages = 50
    messages = [
        {
            "message_content": f"Test message {i}",
            "conversation_id": f"conv_{i}",
            "contact_id": f"contact_{i}"
        }
        for i in range(num_messages)
    ]

    # Act
    start_time = time.time()

    tasks = [
        process_message(msg) for msg in messages
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    # Assert
    successful = sum(1 for r in results if not isinstance(r, Exception))
    assert successful >= num_messages * 0.95  # 95% success rate

    # Average processing time per message
    avg_time = duration / num_messages
    assert avg_time < 1.0  # Under 1 second average

@pytest.mark.performance
@pytest.mark.asyncio
async def test_response_time_sla():
    """Test response time meets SLA (<3 seconds)"""
    # Arrange
    test_messages = [
        "Hello",
        "What's your return policy?",
        "I'm looking for a job",
        "Do you have size 42?",
        "URGENT issue!"
    ]

    # Act & Assert
    for message in test_messages:
        start = time.time()

        state = {
            "message_content": message,
            "conversation_id": "test_conv",
            "contact_id": "test_contact"
        }

        result = await app.ainvoke(state)

        duration = time.time() - start

        # Assert: Sub-3 second response
        assert duration < 3.0, f"Message '{message}' took {duration}s (>3s SLA)"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_vector_search_performance():
    """Test vector search response time"""
    # Arrange
    queries = [
        "return policy",
        "shipping information",
        "payment methods",
        "contact support",
        "warranty terms"
    ]

    # Act & Assert
    for query in queries:
        start = time.time()

        results = await search_knowledge_base(query)

        duration = time.time() - start

        # Assert: Sub-200ms for vector search
        assert duration < 0.2, f"Vector search took {duration}s (>200ms)"

@pytest.mark.performance
@pytest.mark.asyncio
async def test_api_response_time():
    """Test API endpoints meet performance requirements"""
    # Arrange
    endpoints = [
        "/health",
        "/webhooks/chatwoot",
        "/api/contacts/123",
        "/api/conversations/456"
    ]

    # Act & Assert
    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            start = time.time()

            response = await client.get(f"http://localhost:8000{endpoint}")

            duration = time.time() - start

            # Assert: Sub-200ms API response
            assert duration < 0.2, f"{endpoint} took {duration}s (>200ms)"
```

### 5.2 Stress Testing

**tests/performance/test_stress.py**:
```python
import pytest
import asyncio
import time

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
async def test_system_breaking_point():
    """Test system under extreme load to find breaking point"""
    # Gradually increase load
    message_counts = [10, 50, 100, 200, 500]

    results = {}

    for count in message_counts:
        start = time.time()

        tasks = [
            process_message({"message_content": f"Test {i}"})
            for i in range(count)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start
        success_rate = sum(1 for r in responses if not isinstance(r, Exception)) / count

        results[count] = {
            "duration": duration,
            "success_rate": success_rate,
            "avg_time": duration / count
        }

        # Stop if success rate drops below 80%
        if success_rate < 0.8:
            break

    # Report findings
    print("\nStress Test Results:")
    for count, metrics in results.items():
        print(f"{count} messages: {metrics['success_rate']*100}% success, {metrics['avg_time']:.2f}s avg")
```

---

## 6. MANUAL TEST CASES

### 6.1 Primary Use Cases Manual Testing

**Test Case 1: Recruitment Lead Qualification**

**Objective**: Verify complete recruitment flow from initial contact to CRM update

**Preconditions**:
- Chatwoot instance running
- WhatsApp MCP connected
- Knowledge base has sample vacancies

**Test Steps**:
1. Send WhatsApp message: "Hi, I'm looking for interim tech roles in Amsterdam"
2. Verify agent responds with greeting and qualification questions
3. Reply: "Budget €70-90k, need to start in 2 weeks"
4. Verify agent extracts budget and urgency
5. Ask: "Do you have React developer positions?"
6. Verify agentic RAG searches knowledge base
7. Verify agent responds with matching vacancies
8. Login to Chatwoot
9. Verify contact shows:
   - Custom attributes: lead_status="qualified", job_type="interim"
   - Labels: "qualified-lead", "high-priority"
   - AI summary present

**Expected Results**:
- ✅ Agent responds within 3 seconds
- ✅ Budget extracted correctly
- ✅ RAG search finds relevant vacancies
- ✅ CRM updated with all attributes
- ✅ Human can see full context in Chatwoot

---

**Test Case 2: E-commerce Multi-Channel Support**

**Objective**: Verify context preservation across Instagram → WhatsApp

**Test Steps**:
1. Send Instagram DM: "Do you have size 42 sneakers?"
2. Verify agent responds on Instagram
3. Switch to WhatsApp, send: "What's the price for the size 42 I asked about?"
4. Verify agent knows context from Instagram
5. Ask: "What's your return policy?"
6. Verify agentic RAG searches FAQ
7. Check Chatwoot for complete conversation history

**Expected Results**:
- ✅ Context preserved across channels
- ✅ Product interest tracked (size 42, sneakers)
- ✅ FAQ answered from knowledge base
- ✅ Single contact record in CRM

---

**Test Case 3: Dubai Business Lead Filtering**

**Objective**: Verify budget-based qualification logic

**Test Steps**:
1. Send: "I want to setup a company in Dubai, budget €50k"
2. Verify agent qualifies as "qualified" (>€10k)
3. Verify response includes video call scheduling link
4. Send from different number: "Budget is €5k"
5. Verify agent qualifies as "unqualified" (<€10k)
6. Verify response is FAQ-only, no scheduling link
7. Check CRM labels for both contacts

**Expected Results**:
- ✅ Budget >€10k → qualified status + calendly link
- ✅ Budget <€10k → unqualified status + FAQ only
- ✅ CRM labels correctly applied

---

### 6.2 Edge Cases Manual Testing

**Edge Case 1: Empty Messages**
- Send empty WhatsApp message
- Expected: Graceful error handling, prompt for valid input

**Edge Case 2: Very Long Messages**
- Send 1000+ word message
- Expected: Agent processes correctly, no truncation errors

**Edge Case 3: Special Characters**
- Send message with emojis, Unicode, special chars
- Expected: Correct processing and storage

**Edge Case 4: Rapid Message Bursts**
- Send 10 messages in quick succession
- Expected: All processed in order, no lost messages

**Edge Case 5: Network Failures**
- Simulate API timeout
- Expected: Retry logic works, eventual success

---

### 6.3 Error Handling Manual Testing

**Error Scenario 1: Claude API Down**
- Mock Claude API failure
- Expected: Fallback to GPT-4o or graceful error message

**Error Scenario 2: Vector DB Unavailable**
- Stop Supabase instance
- Expected: Agent responds without RAG, notifies about limited knowledge

**Error Scenario 3: Chatwoot API Error**
- Invalid API token
- Expected: Error logged, message queued for retry

**Error Scenario 4: Invalid Webhook Payload**
- Send malformed JSON
- Expected: 400 Bad Request, clear error message

---

## 7. CI/CD INTEGRATION

### 7.1 GitHub Actions Workflow

**.github/workflows/test.yml**:
```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run integration tests
      env:
        POSTGRES_HOST: localhost
        POSTGRES_PORT: 5432
        POSTGRES_DB: test
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
      run: |
        pytest tests/integration -v --maxfail=3

  e2e-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        playwright install chromium

    - name: Run E2E tests
      env:
        CHATWOOT_URL: ${{ secrets.TEST_CHATWOOT_URL }}
        CHATWOOT_API_TOKEN: ${{ secrets.TEST_CHATWOOT_TOKEN }}
      run: |
        pytest tests/e2e -v --maxfail=1
```

### 7.2 Pre-commit Hooks

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit -v --maxfail=5
        language: system
        pass_filenames: false
        always_run: true

      - id: pytest-coverage
        name: Check test coverage
        entry: pytest tests/unit --cov=src --cov-fail-under=80
        language: system
        pass_filenames: false
        always_run: true
```

---

## 8. TEST DATA MANAGEMENT

### 8.1 Test Fixtures and Factories

**tests/factories.py**:
```python
from typing import Dict, Any
import factory
from factory import Faker, Sequence

class ConversationStateFactory(factory.DictFactory):
    """Factory for generating test ConversationState"""

    message_id = Sequence(lambda n: f"msg_{n}")
    conversation_id = Sequence(lambda n: f"conv_{n}")
    contact_id = Sequence(lambda n: f"contact_{n}")
    account_id = "1"
    channel = "whatsapp"
    message_content = Faker("sentence")
    message_type = "incoming"

class ChatwootWebhookFactory(factory.DictFactory):
    """Factory for Chatwoot webhook payloads"""

    event = "message_created"
    message_type = "incoming"
    id = Sequence(lambda n: n)
    content = Faker("sentence")

    class Params:
        conversation_id = Sequence(lambda n: n)
        contact_id = Sequence(lambda n: n)
```

### 8.2 Knowledge Base Test Data

**tests/data/test_knowledge_base.json**:
```json
[
  {
    "content": "Return Policy: 30 days full refund, no questions asked.",
    "metadata": {"category": "policy", "title": "Returns"}
  },
  {
    "content": "Shipping: 2-3 business days for domestic orders.",
    "metadata": {"category": "policy", "title": "Shipping"}
  },
  {
    "content": "Senior React Developer - Amsterdam - €80-100k - Interim 6 months",
    "metadata": {"category": "vacancy", "title": "React Dev", "location": "Amsterdam"}
  }
]
```

---

## SUMMARY

### Testing Coverage Summary

| Test Type | Tests | Coverage | Automation |
|-----------|-------|----------|------------|
| **Unit Tests** | 80 | 90% | ✅ Fully Automated |
| **Integration Tests** | 35 | 85% | ✅ Fully Automated |
| **E2E Tests** | 10 | N/A | ✅ Fully Automated |
| **Performance Tests** | 8 | N/A | ✅ Automated |
| **Manual Tests** | 15 | N/A | ⚠️ Manual Execution |
| **Total** | **148** | **80%+** | **95% Automated** |

### Quality Metrics

- **Test Execution Time**: <5 minutes (unit + integration)
- **E2E Test Time**: <15 minutes
- **CI/CD Pipeline**: Automated on every PR
- **Coverage Requirement**: 80% minimum (enforced)
- **Performance SLA**: <3 seconds response time
- **API SLA**: <200ms response time

### Next Steps

1. **Week 1-2**: Implement unit tests for all 4 agents
2. **Week 3-4**: Build integration tests for LangGraph flow
3. **Week 5**: Create E2E tests for 3 use cases
4. **Week 6**: Performance testing and optimization
5. **Week 7**: Manual testing and bug fixes
6. **Week 8**: Final validation and deployment

**Testing Strategy Status**: ✅ APPROVED - Ready for Implementation
