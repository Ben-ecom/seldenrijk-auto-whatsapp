"""
Unit tests for Extraction Agent.

Tests:
- Job preferences extraction
- Salary expectations extraction
- Personal info extraction (GDPR-compliant)
- Skills extraction
- Confidence calculation
- Pydantic validation
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.extraction_agent import ExtractionAgent
from app.orchestration.state import ConversationState, create_initial_state


class TestExtractionAgent:
    """Test suite for Extraction Agent structured data extraction."""

    @pytest.fixture
    def extraction_agent(self):
        """Create Extraction Agent instance for testing."""
        return ExtractionAgent()

    @pytest.fixture
    def job_search_state(self) -> ConversationState:
        """State with job search message."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I'm looking for a senior software engineer job in Amsterdam or Rotterdam. I have 5 years experience with Python and React. Salary expectation: €60-80k per year. I can start in 1 month.",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )
        # Add router output
        state["router_output"] = {
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": True,
            "escalate_to_human": False,
            "confidence": 0.95,
            "reasoning": "Job search intent"
        }
        return state

    @pytest.mark.asyncio
    async def test_extract_job_preferences(self, extraction_agent, job_search_state):
        """Test extraction of job preferences (titles, locations, etc.)."""
        # Mock Pydantic AI response
        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": {
                "job_titles": ["Senior Software Engineer"],
                "industries": [],
                "locations": ["Amsterdam", "Rotterdam"],
                "employment_type": "full-time",
                "remote_preference": None,
                "experience_level": "senior"
            },
            "salary_expectations": {
                "min_salary": 60000.0,
                "max_salary": 80000.0,
                "currency": "EUR",
                "period": "yearly",
                "negotiable": True
            },
            "personal_info": {
                "years_experience": 5
            },
            "skills": ["Python", "React"],
            "availability": "1 month"
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(job_search_state)

            # Verify job preferences
            job_prefs = result["output"]["job_preferences"]
            assert "Senior Software Engineer" in job_prefs["job_titles"]
            assert "Amsterdam" in job_prefs["locations"]
            assert "Rotterdam" in job_prefs["locations"]
            assert job_prefs["experience_level"] == "senior"

    @pytest.mark.asyncio
    async def test_extract_salary_expectations(self, extraction_agent, job_search_state):
        """Test extraction of salary expectations."""
        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": {
                "min_salary": 60000.0,
                "max_salary": 80000.0,
                "currency": "EUR",
                "period": "yearly",
                "negotiable": True
            },
            "personal_info": None,
            "skills": [],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(job_search_state)

            # Verify salary expectations
            salary = result["output"]["salary_expectations"]
            assert salary["min_salary"] == 60000.0
            assert salary["max_salary"] == 80000.0
            assert salary["currency"] == "EUR"
            assert salary["period"] == "yearly"
            assert salary["negotiable"] is True

    @pytest.mark.asyncio
    async def test_extract_skills(self, extraction_agent, job_search_state):
        """Test extraction of technical and soft skills."""
        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": None,
            "personal_info": None,
            "skills": ["Python", "React", "TypeScript", "Docker", "Leadership"],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(job_search_state)

            # Verify skills extraction
            skills = result["output"]["skills"]
            assert "Python" in skills
            assert "React" in skills
            assert "Leadership" in skills
            assert len(skills) >= 3

    @pytest.mark.asyncio
    async def test_extract_personal_info_gdpr_compliant(self, extraction_agent):
        """Test GDPR-compliant personal info extraction (only explicit data)."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Hi, I'm John Doe. My email is john@example.com and I have 8 years experience as a Data Scientist at Google.",
            sender_name="John Doe",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )
        # Add router output
        state["router_output"] = {
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": True,
            "escalate_to_human": False,
            "confidence": 0.95,
            "reasoning": "Job search intent with personal information"
        }

        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": None,
            "personal_info": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": None,
                "linkedin_url": None,
                "years_experience": 8,
                "current_job_title": "Data Scientist",
                "current_company": "Google"
            },
            "skills": [],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(state)

            # Verify GDPR-compliant extraction
            personal_info = result["output"]["personal_info"]
            assert personal_info["name"] == "John Doe"
            assert personal_info["email"] == "john@example.com"
            assert personal_info["years_experience"] == 8
            # Should NOT infer data not explicitly stated
            assert personal_info["phone"] is None

    @pytest.mark.asyncio
    async def test_confidence_calculation_high(self, extraction_agent, job_search_state):
        """Test confidence calculation when many fields are filled."""
        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": {
                "job_titles": ["Software Engineer"],
                "locations": ["Amsterdam"],
                "industries": [],
                "employment_type": "full-time",
                "remote_preference": None,
                "experience_level": "senior"
            },
            "salary_expectations": {
                "min_salary": 60000.0,
                "max_salary": 80000.0,
                "currency": "EUR",
                "period": "yearly",
                "negotiable": True
            },
            "personal_info": {
                "name": None,
                "email": None,
                "phone": None,
                "linkedin_url": None,
                "years_experience": 5,
                "current_job_title": None,
                "current_company": None
            },
            "skills": ["Python", "React"],
            "availability": "1 month"
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(job_search_state)

            # Confidence calculation:
            # job_prefs: 4/6 filled = 4
            # salary: 3/3 filled = 3
            # personal: 1/7 filled = 1
            # skills + availability: 2/2 = 2
            # Total: 10/18 = 0.555 ≈ 0.56
            assert result["output"]["extraction_confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_confidence_calculation_low(self, extraction_agent):
        """Test confidence calculation when few fields are filled."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I'm looking for a job",  # Vague, little extractable data
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )
        # Add router output
        state["router_output"] = {
            "intent": "job_search",
            "priority": "medium",
            "needs_extraction": True,
            "escalate_to_human": False,
            "confidence": 0.7,
            "reasoning": "Vague job search intent"
        }

        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": None,
            "personal_info": None,
            "skills": [],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(state)

            # Low confidence when few/no fields filled
            assert result["output"]["extraction_confidence"] <= 0.5

    @pytest.mark.asyncio
    async def test_conversation_history_context(self, extraction_agent):
        """Test extraction uses conversation history for context."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Yes, €70k would be perfect",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1",
            conversation_history=[
                {"role": "user", "content": "I'm looking for software engineer jobs"},
                {"role": "assistant", "content": "What's your salary expectation?"}
            ]
        )
        # Add router output
        state["router_output"] = {
            "intent": "salary_inquiry",
            "priority": "medium",
            "needs_extraction": True,
            "escalate_to_human": False,
            "confidence": 0.92,
            "reasoning": "Salary response in context of job search"
        }

        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": {
                "job_titles": ["Software Engineer"]  # From history
            },
            "salary_expectations": {
                "min_salary": 70000.0,
                "max_salary": 70000.0,
                "currency": "EUR",
                "period": "yearly"
            },
            "personal_info": None,
            "skills": [],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(state)

            # Should extract job title from history
            assert "Software Engineer" in result["output"]["job_preferences"]["job_titles"]
            assert result["output"]["salary_expectations"]["min_salary"] == 70000.0

    @pytest.mark.asyncio
    async def test_no_extraction_needed(self, extraction_agent):
        """Test extraction returns empty when message has no extractable data."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Hello, how are you?",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )
        # Add router output
        state["router_output"] = {
            "intent": "greeting",
            "priority": "low",
            "needs_extraction": False,
            "escalate_to_human": False,
            "confidence": 0.85,
            "reasoning": "Simple greeting with no extractable data"
        }

        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": None,
            "personal_info": None,
            "skills": [],
            "availability": None
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(state)

            # All fields should be None/empty
            assert result["output"]["job_preferences"] is None
            assert result["output"]["salary_expectations"] is None
            assert result["output"]["skills"] == []

    @pytest.mark.asyncio
    async def test_availability_extraction(self, extraction_agent):
        """Test extraction of availability/start date."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I can start immediately, or with 2 weeks notice if needed",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )
        # Add router output
        state["router_output"] = {
            "intent": "availability_inquiry",
            "priority": "medium",
            "needs_extraction": True,
            "escalate_to_human": False,
            "confidence": 0.90,
            "reasoning": "Availability information provided"
        }

        mock_result = Mock()
        mock_result.data.model_dump.return_value = {
            "job_preferences": None,
            "salary_expectations": None,
            "personal_info": None,
            "skills": [],
            "availability": "immediately or 2 weeks notice"
        }

        with patch.object(extraction_agent.pydantic_agent, 'run_sync', return_value=mock_result):
            result = extraction_agent.execute(state)

            assert result["output"]["availability"] is not None
            assert "immediately" in result["output"]["availability"].lower()
