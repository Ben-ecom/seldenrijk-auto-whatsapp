"""
LangGraph Configuration - StateGraph settings and timeouts.

This module configures the LangGraph StateGraph orchestration layer.
"""
import os
from typing import Literal


# ============ STATEGRAPH SETTINGS ============

# Maximum total execution time for entire graph (all agents combined)
GRAPH_TIMEOUT_SECONDS = 120  # 2 minutes max per message

# Checkpointing (enables fault tolerance + conversation resumption)
ENABLE_CHECKPOINTING = True
CHECKPOINT_BACKEND = "redis"  # Options: "memory", "redis", "postgres"

# Redis connection for checkpointing
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


# ============ CONDITIONAL ROUTING SETTINGS ============

# High priority messages skip extraction and go straight to conversation
PRIORITY_LEVELS_SKIP_EXTRACTION = ["high"]

# Intents that require extraction (automotive dealership)
INTENTS_REQUIRING_EXTRACTION = [
    "car_inquiry",      # Questions about specific cars need extraction
    "appointment",      # Appointment requests need date/time extraction
    "financing",        # Financing questions need budget extraction
    "trade_in",         # Trade-in needs current car details extraction
]

# Intents that should escalate to human immediately
INTENTS_REQUIRING_ESCALATION = [
    "complaint",        # Always escalate complaints
]

# Confidence threshold for router decisions
ROUTER_CONFIDENCE_THRESHOLD = 0.7  # If < 0.7, escalate to human


# ============ RAG SETTINGS ============

# Enable Agentic RAG in Conversation Agent (Week 5 feature)
ENABLE_RAG = False  # Set to True after Week 5 implementation

# Maximum RAG search iterations
MAX_RAG_ITERATIONS = 3

# Similarity threshold for RAG results
RAG_SIMILARITY_THRESHOLD = 0.7


# ============ CRM UPDATE SETTINGS ============

# Always update CRM for these intents (automotive dealership)
INTENTS_REQUIRING_CRM_UPDATE = [
    "car_inquiry",          # Track which cars customers are interested in
    "appointment",          # Track appointment requests
    "financing",            # Track financing inquiries
    "trade_in",             # Track trade-in inquiries
    "service_maintenance",  # Track service requests
]

# Minimum confidence to create new contact
CRM_CREATE_CONTACT_CONFIDENCE = 0.8


# ============ ERROR HANDLING ============

# Maximum retries per agent before failing entire graph
MAX_AGENT_RETRIES = 3

# Fallback responses when agents fail (automotive dealership context)
FALLBACK_RESPONSES = {
    "router_failed": "Excuses, ik heb moeite om uw vraag te begrijpen. Laat me u doorverbinden met een medewerker.",
    "extraction_failed": "Ik help u graag verder. Kunt u mij iets meer vertellen over waar u naar op zoek bent?",
    "conversation_failed": "Excuses, ik ondervind technische problemen. Een van onze medewerkers neemt zo snel mogelijk contact met u op.",
    "crm_failed": "Ik heb uw verzoek genoteerd en zorg ervoor dat ons team contact met u opneemt.",
}


# ============ MONITORING ============

# Log all state transitions (for debugging)
LOG_STATE_TRANSITIONS = True

# Log full state object (can be verbose)
LOG_FULL_STATE = os.getenv("ENVIRONMENT") == "development"


# ============ GRAPH STRUCTURE ============
# Defines the flow: START → Router → [extraction/conversation] → CRM → END

GRAPH_FLOW = {
    "START": "router",
    "router": {
        "escalate": "END",  # Escalate to human
        "extraction": "extraction",  # Needs data extraction
        "conversation": "conversation",  # Direct to conversation
    },
    "extraction": "conversation",  # Always go to conversation after extraction
    "conversation": {
        "rag": "conversation",  # Loop back for RAG iterations
        "crm": "crm",  # Continue to CRM update
    },
    "crm": "END",  # Always end after CRM update
}


# ============ CIRCUIT BREAKER SETTINGS ============
# Prevents cascading failures by tracking agent health

# Number of consecutive failures before opening circuit
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5

# Time window for counting failures (seconds)
CIRCUIT_BREAKER_WINDOW_SECONDS = 60

# Time to wait before attempting to close circuit (seconds)
CIRCUIT_BREAKER_RESET_TIMEOUT = 30


# ============ RATE LIMITING ============
# Per-user rate limits to prevent abuse

# Maximum messages per user per minute
MAX_MESSAGES_PER_USER_PER_MINUTE = 10

# Maximum messages per user per hour
MAX_MESSAGES_PER_USER_PER_HOUR = 100


# ============ HELPER FUNCTIONS ============

def get_next_agent(current_agent: str, state: dict) -> Literal["extraction", "conversation", "crm", "end"]:
    """
    Determine next agent based on current agent and state.

    This implements the conditional routing logic defined in GRAPH_FLOW.

    Args:
        current_agent: Name of agent that just executed
        state: Current ConversationState

    Returns:
        Next agent to execute ("extraction", "conversation", "crm", "end")
    """
    # Check for escalation
    if state.get("escalate_to_human"):
        return "end"

    # Check for errors
    if state.get("error_occurred"):
        return "end"

    # Router routing
    if current_agent == "router":
        router_output = state.get("router_output", {})

        if router_output.get("escalate_to_human"):
            return "end"

        if router_output.get("needs_extraction"):
            return "extraction"

        return "conversation"

    # Extraction always goes to conversation
    if current_agent == "extraction":
        return "conversation"

    # Conversation routing
    if current_agent == "conversation":
        conv_output = state.get("conversation_output", {})

        # Check if RAG loop needed
        if conv_output.get("needs_rag") and state.get("rag_iterations", 0) < MAX_RAG_ITERATIONS:
            return "conversation"  # Loop back for RAG

        return "crm"

    # CRM always ends
    if current_agent == "crm":
        return "end"

    # Default fallback
    return "end"


def should_update_crm(state: dict) -> bool:
    """
    Determine if CRM should be updated based on state.

    Args:
        state: Current ConversationState

    Returns:
        True if CRM update is needed
    """
    router_output = state.get("router_output", {})
    intent = router_output.get("intent")

    # Always update for these intents
    if intent in INTENTS_REQUIRING_CRM_UPDATE:
        return True

    # Update if extraction found data
    extraction_output = state.get("extraction_output", {})
    if extraction_output and extraction_output.get("extraction_confidence", 0) > CRM_CREATE_CONTACT_CONFIDENCE:
        return True

    return False
