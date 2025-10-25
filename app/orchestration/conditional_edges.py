"""
Conditional Edge Functions - Routing logic for LangGraph StateGraph.

These functions determine which agent to execute next based on current state.
Implements the conditional branching logic defined in architecture.
"""
from typing import Literal
from app.orchestration.state import ConversationState
from app.config.langgraph_config import (
    PRIORITY_LEVELS_SKIP_EXTRACTION,
    INTENTS_REQUIRING_EXTRACTION,
    INTENTS_REQUIRING_ESCALATION,
    ROUTER_CONFIDENCE_THRESHOLD,
    MAX_RAG_ITERATIONS
)
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


def route_after_router(
    state: ConversationState
) -> Literal["escalate", "extraction", "conversation"]:
    """
    Decide next step after Router Agent.

    Logic:
    1. If escalate_to_human flag → END (escalate)
    2. If low confidence → END (escalate)
    3. If intent requires escalation → END (escalate)
    4. If high priority → conversation (skip extraction for speed)
    5. If intent requires extraction AND needs_extraction → extraction
    6. Otherwise → conversation

    Args:
        state: Current conversation state

    Returns:
        Next node: "escalate", "extraction", or "conversation"
    """
    router_output = state.get("router_output", {})

    # Check escalation flag
    if router_output.get("escalate_to_human"):
        logger.info("🚨 Escalating to human (router flag)")
        return "escalate"

    # Check confidence threshold
    if router_output.get("confidence", 0) < ROUTER_CONFIDENCE_THRESHOLD:
        logger.info(
            f"🚨 Escalating to human (low confidence: {router_output.get('confidence')})"
        )
        state["escalate_to_human"] = True
        return "escalate"

    # Check intent-based escalation
    intent = router_output.get("intent")
    if intent in INTENTS_REQUIRING_ESCALATION:
        logger.info(f"🚨 Escalating to human (intent: {intent})")
        state["escalate_to_human"] = True
        return "escalate"

    # High priority messages skip extraction for speed
    priority = router_output.get("priority")
    if priority in PRIORITY_LEVELS_SKIP_EXTRACTION:
        logger.info(f"⚡ Skipping extraction (high priority: {priority})")
        return "conversation"

    # Check if extraction is needed
    needs_extraction = router_output.get("needs_extraction", False)
    if needs_extraction and intent in INTENTS_REQUIRING_EXTRACTION:
        logger.info(f"📊 Routing to extraction (intent: {intent})")
        return "extraction"

    # Default: go to conversation
    logger.info("💬 Routing directly to conversation")
    return "conversation"


def route_after_conversation(
    state: ConversationState
) -> Literal["rag", "crm", "end"]:
    """
    Decide next step after Conversation Agent.

    Logic:
    1. If escalate_to_human → END (skip CRM)
    2. If needs_rag AND iterations < MAX → conversation (RAG loop)
    3. Otherwise → crm

    Args:
        state: Current conversation state

    Returns:
        Next node: "rag" (loop back), "crm", or "end"
    """
    # Check for escalation
    if state.get("escalate_to_human"):
        logger.info("🚨 Escalation detected, skipping CRM")
        return "end"

    # Check for RAG loop
    conversation_output = state.get("conversation_output", {})
    needs_rag = conversation_output.get("needs_rag", False)
    rag_iterations = state.get("rag_iterations", 0)

    if needs_rag and rag_iterations < MAX_RAG_ITERATIONS:
        logger.info(
            f"🔍 Looping back for RAG search (iteration {rag_iterations + 1}/{MAX_RAG_ITERATIONS})"
        )
        return "rag"

    # Check if max RAG iterations reached
    if rag_iterations >= MAX_RAG_ITERATIONS:
        logger.warning(f"⚠️ Max RAG iterations reached ({MAX_RAG_ITERATIONS}), proceeding to CRM")

    # Default: proceed to CRM
    logger.info("📋 Routing to CRM update")
    return "crm"


def should_continue_to_crm(state: ConversationState) -> Literal["end"]:
    """
    Decide if CRM update should continue or end.

    This is a simple edge that always ends after CRM.
    Kept as a function for consistency and future extensibility.

    Args:
        state: Current conversation state

    Returns:
        Always "end"
    """
    logger.info("✅ CRM complete, ending workflow")
    return "end"


# ============ HELPER FUNCTIONS ============

def should_skip_extraction(state: ConversationState) -> bool:
    """
    Check if extraction should be skipped.

    Args:
        state: Current conversation state

    Returns:
        True if extraction should be skipped
    """
    router_output = state.get("router_output", {})

    # Skip if high priority
    if router_output.get("priority") in PRIORITY_LEVELS_SKIP_EXTRACTION:
        return True

    # Skip if router says no extraction needed
    if not router_output.get("needs_extraction"):
        return True

    # Skip if intent doesn't require extraction
    if router_output.get("intent") not in INTENTS_REQUIRING_EXTRACTION:
        return True

    return False


def should_escalate(state: ConversationState) -> bool:
    """
    Check if conversation should escalate to human.

    Args:
        state: Current conversation state

    Returns:
        True if escalation is needed
    """
    # Check explicit escalation flag
    if state.get("escalate_to_human"):
        return True

    # Check router output
    router_output = state.get("router_output", {})
    if router_output.get("escalate_to_human"):
        return True

    # Check confidence threshold
    if router_output.get("confidence", 0) < ROUTER_CONFIDENCE_THRESHOLD:
        return True

    # Check intent
    if router_output.get("intent") in INTENTS_REQUIRING_ESCALATION:
        return True

    return False


def get_rag_iterations(state: ConversationState) -> int:
    """
    Get current RAG iteration count.

    Args:
        state: Current conversation state

    Returns:
        Number of RAG iterations completed
    """
    return state.get("rag_iterations", 0)


def can_continue_rag(state: ConversationState) -> bool:
    """
    Check if RAG loop can continue.

    Args:
        state: Current conversation state

    Returns:
        True if RAG can continue (under max iterations)
    """
    return get_rag_iterations(state) < MAX_RAG_ITERATIONS


# ============ ENHANCED WORKFLOW ROUTING (Phase 3.5) ============

def route_after_enhanced_conversation(
    state: ConversationState
) -> Literal["escalation", "end"]:
    """
    Decide next step after Enhanced Conversation Agent.

    Logic:
    1. If escalate_to_human flag set by ExpertiseAgent → escalation_router
    2. Otherwise → END

    Args:
        state: Current conversation state

    Returns:
        Next node: "escalation" or "end"
    """
    # Check for escalation flag
    if state.get("escalate_to_human"):
        logger.info(
            "🚨 Routing to escalation_router",
            extra={
                "escalation_type": state.get("escalation_type"),
                "urgency": state.get("escalation_urgency"),
                "reason": state.get("escalation_reason")
            }
        )
        return "escalation"

    # Normal completion
    logger.info("✅ Conversation complete, ending workflow")
    return "end"
