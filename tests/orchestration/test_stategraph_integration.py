"""
Integration tests for complete LangGraph StateGraph workflow.

Tests:
- Full workflow execution (Router → Extraction → Conversation → CRM)
- Conditional routing paths (all 7 paths)
- Escalation workflow
- RAG loop iteration
- Error handling + retries
- State persistence (checkpointing)
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.orchestration.graph_builder import execute_graph
from app.orchestration.state import create_initial_state, ConversationState


class TestStateGraphIntegration:
    """Integration tests for complete StateGraph workflow."""

    @pytest.fixture
    def mock_all_agents(self):
        """Mock all 4 agents to return predictable outputs."""
        with patch('app.orchestration.graph_builder.RouterAgent') as mock_router, \
             patch('app.orchestration.graph_builder.ExtractionAgent') as mock_extraction, \
             patch('app.orchestration.graph_builder.ConversationAgent') as mock_conversation, \
             patch('app.orchestration.graph_builder.CRMAgent') as mock_crm:

            # Mock Router Agent
            mock_router_instance = Mock()
            mock_router_instance.execute.return_value = {
                "output": {
                    "intent": "job_search",
                    "priority": "medium",
                    "needs_extraction": True,
                    "escalate_to_human": False,
                    "confidence": 0.95,
                    "reasoning": "Job search intent"
                },
                "tokens_used": {"input": 200, "output": 100, "total": 300},
                "cost_usd": 0.0001
            }
            mock_router.return_value = mock_router_instance

            # Mock Extraction Agent
            mock_extraction_instance = Mock()
            mock_extraction_instance.execute.return_value = {
                "output": {
                    "job_preferences": {
                        "job_titles": ["Software Engineer"],
                        "locations": ["Amsterdam"]
                    },
                    "salary_expectations": {
                        "min_salary": 60000.0,
                        "max_salary": 80000.0
                    },
                    "skills": ["Python", "React"],
                    "extraction_confidence": 0.85
                },
                "tokens_used": {"input": 500, "output": 200, "total": 700},
                "cost_usd": 0.0002
            }
            mock_extraction.return_value = mock_extraction_instance

            # Mock Conversation Agent
            mock_conversation_instance = Mock()
            mock_conversation_instance.execute.return_value = {
                "output": {
                    "response_text": "Great! I found several software engineer positions in Amsterdam matching your salary range.",
                    "needs_rag": False,
                    "rag_query": None,
                    "rag_results": None,
                    "follow_up_questions": ["Would you like to see remote opportunities too?"],
                    "conversation_complete": False,
                    "sentiment": "positive"
                },
                "tokens_used": {"input": 2000, "output": 500, "total": 2500},
                "cost_usd": 0.008
            }
            mock_conversation.return_value = mock_conversation_instance

            # Mock CRM Agent
            mock_crm_instance = Mock()
            mock_crm_instance.execute.return_value = {
                "output": {
                    "contact_id": "contact-789",
                    "contact_created": False,
                    "contact_updated": True,
                    "custom_attributes_updated": {
                        "job_preferences_titles": ["Software Engineer"],
                        "job_preferences_locations": ["Amsterdam"],
                        "salary_min": 60000,
                        "salary_max": 80000,
                        "lead_quality": "warm"
                    },
                    "tags_added": ["job-seeker", "active", "normal"],
                    "conversation_labeled": True,
                    "crm_error": None
                },
                "tokens_used": {"input": 300, "output": 100, "total": 400},
                "cost_usd": 0.0001
            }
            mock_crm.return_value = mock_crm_instance

            yield {
                "router": mock_router_instance,
                "extraction": mock_extraction_instance,
                "conversation": mock_conversation_instance,
                "crm": mock_crm_instance
            }

    @pytest.mark.asyncio
    async def test_full_workflow_job_search(self, mock_all_agents):
        """Test complete workflow: Router → Extraction → Conversation → CRM."""
        # Create initial state
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I'm looking for a software engineer job in Amsterdam, €60-80k",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        # Execute full graph
        final_state = await execute_graph(state)

        # Verify all agents executed
        assert mock_all_agents["router"].execute.called
        assert mock_all_agents["extraction"].execute.called
        assert mock_all_agents["conversation"].execute.called
        assert mock_all_agents["crm"].execute.called

        # Verify state updates
        assert final_state["router_output"]["intent"] == "job_search"
        assert final_state["extraction_output"]["extraction_confidence"] >= 0.8
        assert final_state["conversation_output"]["response_text"] is not None
        assert final_state["crm_output"]["contact_updated"] is True

        # Verify no errors
        assert final_state["error_occurred"] is False
        assert final_state["escalate_to_human"] is False

    @pytest.mark.asyncio
    async def test_escalation_path_complaint(self, mock_all_agents):
        """Test escalation path: Router detects complaint → immediate END."""
        # Override router to return escalation
        mock_all_agents["router"].execute.return_value = {
            "output": {
                "intent": "complaint",
                "priority": "high",
                "needs_extraction": False,
                "escalate_to_human": True,
                "confidence": 0.98,
                "reasoning": "Complaint requires human"
            },
            "tokens_used": {"input": 200, "output": 100, "total": 300},
            "cost_usd": 0.0001
        }

        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="This is unacceptable!",
            sender_name="Angry User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        final_state = await execute_graph(state)

        # Verify escalation occurred
        assert final_state["escalate_to_human"] is True
        assert final_state["router_output"]["intent"] == "complaint"

        # Verify other agents NOT executed
        assert not mock_all_agents["extraction"].execute.called
        assert not mock_all_agents["conversation"].execute.called
        assert not mock_all_agents["crm"].execute.called

    @pytest.mark.asyncio
    async def test_high_priority_skip_extraction(self, mock_all_agents):
        """Test high priority path: Router → Conversation (skip Extraction)."""
        # Override router to return high priority
        mock_all_agents["router"].execute.return_value = {
            "output": {
                "intent": "complaint",
                "priority": "high",
                "needs_extraction": False,
                "escalate_to_human": False,  # Handle but don't escalate
                "confidence": 0.92,
                "reasoning": "High priority"
            },
            "tokens_used": {"input": 200, "output": 100, "total": 300},
            "cost_usd": 0.0001
        }

        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I need urgent help",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        final_state = await execute_graph(state)

        # Verify extraction was skipped
        assert not mock_all_agents["extraction"].execute.called

        # Verify conversation and CRM executed
        assert mock_all_agents["conversation"].execute.called
        assert mock_all_agents["crm"].execute.called

    @pytest.mark.asyncio
    async def test_rag_loop_iteration(self, mock_all_agents):
        """Test RAG loop: Conversation → RAG search → Conversation (max 3 iterations)."""
        # First conversation call needs RAG
        mock_all_agents["conversation"].execute.side_effect = [
            {
                "output": {
                    "response_text": "Let me search for that information...",
                    "needs_rag": True,
                    "rag_query": "software engineer salaries Amsterdam",
                    "rag_results": None,
                    "follow_up_questions": [],
                    "conversation_complete": False,
                    "sentiment": "neutral"
                },
                "tokens_used": {"input": 2000, "output": 300, "total": 2300},
                "cost_usd": 0.006
            },
            # Second call after RAG (mock that RAG was executed)
            {
                "output": {
                    "response_text": "Based on our database, software engineers in Amsterdam earn €60-90k",
                    "needs_rag": False,
                    "rag_query": None,
                    "rag_results": ["Result 1", "Result 2"],
                    "follow_up_questions": ["Would you like details on specific companies?"],
                    "conversation_complete": False,
                    "sentiment": "positive"
                },
                "tokens_used": {"input": 2000, "output": 500, "total": 2500},
                "cost_usd": 0.008
            }
        ]

        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="What's the typical salary for software engineers in Amsterdam?",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        final_state = await execute_graph(state)

        # Verify conversation called twice (RAG loop)
        assert mock_all_agents["conversation"].execute.call_count == 2

        # Verify RAG iterations tracked
        assert final_state.get("rag_iterations", 0) > 0

    @pytest.mark.asyncio
    async def test_token_and_cost_accumulation(self, mock_all_agents):
        """Test total tokens and cost are accumulated across all agents."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I need a job",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        final_state = await execute_graph(state)

        # Verify token accumulation
        # Router: 300 + Extraction: 700 + Conversation: 2500 + CRM: 400 = 3900
        expected_tokens = 300 + 700 + 2500 + 400
        assert final_state["total_tokens_used"] == expected_tokens

        # Verify cost accumulation
        # Router: 0.0001 + Extraction: 0.0002 + Conversation: 0.008 + CRM: 0.0001
        expected_cost = 0.0001 + 0.0002 + 0.008 + 0.0001
        assert abs(final_state["total_cost_usd"] - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, mock_all_agents):
        """Test processing time is calculated correctly."""
        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="Test message",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        start_time = state["processing_start_time"]

        final_state = await execute_graph(state)

        # Verify processing times set
        assert final_state["processing_start_time"] == start_time
        assert final_state["processing_end_time"] is not None
        assert final_state["processing_end_time"] > start_time

    @pytest.mark.asyncio
    async def test_error_recovery_with_retry(self, mock_all_agents):
        """Test error recovery: Agent fails → retries → succeeds."""
        # Mock extraction to fail first, then succeed
        mock_all_agents["extraction"].execute.side_effect = [
            Exception("Temporary API error"),  # First call fails
            {  # Second call succeeds after retry
                "output": {
                    "job_preferences": {"job_titles": ["Engineer"]},
                    "extraction_confidence": 0.7
                },
                "tokens_used": {"input": 500, "output": 200, "total": 700},
                "cost_usd": 0.0002
            }
        ]

        state = create_initial_state(
            message_id="test-123",
            conversation_id="conv-456",
            contact_id="contact-789",
            content="I need a job",
            sender_name="Test User",
            sender_phone="+31612345678",
            account_id="1",
            inbox_id="1"
        )

        final_state = await execute_graph(state)

        # Should eventually succeed after retry
        assert final_state["extraction_output"] is not None
        assert final_state["error_occurred"] is False


class TestConditionalRouting:
    """Tests for conditional routing logic."""

    @pytest.mark.asyncio
    async def test_route_after_router_logic(self):
        """Test all routing decisions after Router Agent."""
        from app.orchestration.conditional_edges import route_after_router

        # Test: Escalation
        state_escalate = {"router_output": {"escalate_to_human": True}}
        assert route_after_router(state_escalate) == "escalate"

        # Test: Needs extraction
        state_extraction = {
            "router_output": {
                "escalate_to_human": False,
                "confidence": 0.9,
                "intent": "job_search",
                "priority": "medium",
                "needs_extraction": True
            }
        }
        assert route_after_router(state_extraction) == "extraction"

        # Test: Direct to conversation (high priority)
        state_direct = {
            "router_output": {
                "escalate_to_human": False,
                "confidence": 0.9,
                "intent": "complaint",
                "priority": "high",
                "needs_extraction": False
            }
        }
        assert route_after_router(state_direct) == "conversation"

    @pytest.mark.asyncio
    async def test_route_after_conversation_logic(self):
        """Test routing decisions after Conversation Agent."""
        from app.orchestration.conditional_edges import route_after_conversation

        # Test: RAG needed
        state_rag = {
            "escalate_to_human": False,
            "conversation_output": {"needs_rag": True},
            "rag_iterations": 1
        }
        assert route_after_conversation(state_rag) == "rag"

        # Test: Max RAG iterations reached
        state_max_rag = {
            "escalate_to_human": False,
            "conversation_output": {"needs_rag": True},
            "rag_iterations": 3  # Max reached
        }
        assert route_after_conversation(state_max_rag) == "crm"

        # Test: Go to CRM
        state_crm = {
            "escalate_to_human": False,
            "conversation_output": {"needs_rag": False}
        }
        assert route_after_conversation(state_crm) == "crm"

        # Test: Escalation skips CRM
        state_escalate = {
            "escalate_to_human": True,
            "conversation_output": {"needs_rag": False}
        }
        assert route_after_conversation(state_escalate) == "end"
