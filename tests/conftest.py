"""
Pytest configuration and fixtures for all tests.

This file automatically loads .env.test before running any tests.
"""
import sys
import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load test environment variables BEFORE any app imports
env_test_path = project_root / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"✅ Loaded test environment from {env_test_path}")
else:
    print(f"⚠️  Warning: {env_test_path} not found")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment before running any tests.
    This fixture runs once per test session.
    """
    # Verify critical env vars are loaded
    required_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CHATWOOT_API_KEY"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.fail(f"Missing required test environment variables: {missing_vars}")

    print("✅ Test environment setup complete")
    yield
    print("✅ Test environment teardown complete")


@pytest.fixture
def mock_openai_response():
    """
    Fixture providing a mock OpenAI API response.

    Usage:
        def test_something(mock_openai_response):
            with patch('openai.Client.chat.completions.create', return_value=mock_openai_response):
                ...
    """
    from unittest.mock import Mock

    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = '{"test": "response"}'
    response.usage = Mock(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    return response


@pytest.fixture
def mock_anthropic_response():
    """
    Fixture providing a mock Anthropic API response.
    """
    from unittest.mock import Mock

    response = Mock()
    response.content = [Mock()]
    response.content[0].text = "Mock Claude response"
    response.usage = Mock(
        input_tokens=500,
        output_tokens=200,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0
    )
    return response


@pytest.fixture
def sample_conversation_state():
    """
    Fixture providing a sample ConversationState for testing.
    """
    from app.orchestration.state import create_initial_state

    return create_initial_state(
        message_id="test-msg-123",
        conversation_id="test-conv-456",
        contact_id="test-contact-789",
        content="Test message content",
        sender_name="Test User",
        sender_phone="+31612345678",
        account_id="1",
        inbox_id="1"
    )
