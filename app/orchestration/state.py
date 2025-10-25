"""
ConversationState TypedDict - Central state management for LangGraph workflow.

This state object is passed between all agents in the StateGraph and contains
all necessary context for processing WhatsApp messages.
"""
from typing import TypedDict, Optional, Literal, List, Dict, Any
from datetime import datetime


class CarPreferences(TypedDict, total=False):
    """Extracted car preferences from user messages."""
    make: Optional[str]  # e.g., "Volkswagen", "BMW"
    model: Optional[str]  # e.g., "Golf 8", "3-serie"
    fuel_type: Optional[str]  # "diesel", "benzine", "hybride", "elektrisch"
    min_price: Optional[float]
    max_price: Optional[float]
    max_mileage: Optional[int]  # Maximum km
    min_year: Optional[int]  # Minimum build year
    preferred_color: Optional[str]
    transmission: Optional[Literal["automaat", "handgeschakeld"]]
    body_type: Optional[str]  # "SUV", "sedan", "hatchback", etc.


class RouterOutput(TypedDict):
    """Output from Router Agent."""
    intent: Literal[
        # Automotive intents
        "car_inquiry",  # Looking for specific car
        "price_question",  # Asking about price/budget
        "appointment_request",  # Wants to schedule viewing
        "trade_in_inquiry",  # Has car to trade in
        "financing_inquiry",  # Asking about financing
        # Legacy job search intents (for backwards compatibility)
        "job_search",
        "salary_inquiry",
        "application_status",
        # General intents
        "complaint",
        "general_inquiry",
        "unclear"
    ]
    priority: Literal["high", "medium", "low"]
    needs_extraction: bool
    escalate_to_human: bool
    confidence: float
    reasoning: str


class ExtractionOutput(TypedDict, total=False):
    """Output from Extraction Agent - Automotive Domain Only."""
    car_preferences: Optional[CarPreferences]  # Extracted car preferences (make, model, fuel, price, etc.)
    extraction_confidence: float  # Confidence score 0.0-1.0


class ConversationOutput(TypedDict):
    """Output from Conversation Agent."""
    response_text: str
    needs_rag: bool
    rag_query: Optional[str]
    rag_results: Optional[List[Dict[str, Any]]]
    follow_up_questions: List[str]
    conversation_complete: bool
    sentiment: Literal["positive", "neutral", "negative"]
    recommended_action: Optional[str]  # Added: Action recommendation for user (e.g., "schedule_appointment", "send_brochure")


class CRMOutput(TypedDict):
    """Output from CRM Agent."""
    contact_id: Optional[str]
    contact_created: bool
    contact_updated: bool
    custom_attributes_updated: Dict[str, Any]
    tags_added: List[str]
    conversation_labeled: bool
    crm_error: Optional[str]


class DocumentationOutput(TypedDict, total=False):
    """Output from Documentation Agent (RAG retrieval)."""
    needs_rag: bool
    rag_query: Optional[str]
    rag_category: Optional[str]
    retrieved_docs: List[Dict[str, Any]]
    retrieved_context: str
    reasoning: str


class ConversationState(TypedDict, total=False):
    """
    Central state object passed through LangGraph StateGraph.

    This state is updated by each agent and persists throughout the conversation flow.
    All agents read from and write to this shared state.
    """
    # ============ INPUT (from Chatwoot webhook) ============
    message_id: str
    conversation_id: str
    contact_id: Optional[str]
    sender_type: Literal["contact", "agent", "bot"]
    message_type: Literal["incoming", "outgoing"]
    content: str
    sender_name: str
    sender_phone: str
    timestamp: datetime
    account_id: str
    inbox_id: str
    source: Optional[Literal["chatwoot", "waha", "360dialog"]]  # Track message source for response routing

    # ============ CONVERSATION HISTORY ============
    conversation_history: List[Dict[str, str]]  # [{"role": "user", "content": "..."}, ...]
    previous_intents: List[str]

    # ============ ROUTER OUTPUT ============
    router_output: Optional[RouterOutput]

    # ============ DOCUMENTATION OUTPUT (RAG) ============
    documentation_output: Optional[DocumentationOutput]

    # ============ EXTRACTION OUTPUT ============
    extraction_output: Optional[ExtractionOutput]

    # ============ CONVERSATION OUTPUT ============
    conversation_output: Optional[ConversationOutput]

    # ============ CRM OUTPUT ============
    crm_output: Optional[CRMOutput]

    # ============ GRAPH CONTROL ============
    next_agent: Optional[Literal["router", "extraction", "conversation", "crm", "end"]]
    escalate_to_human: bool
    error_occurred: bool
    error_message: Optional[str]
    retry_count: int

    # ============ METADATA ============
    processing_start_time: datetime
    processing_end_time: Optional[datetime]
    total_tokens_used: int
    total_cost_usd: float


# ============ HELPER FUNCTIONS ============

def create_initial_state(
    message_id: str,
    conversation_id: str,
    contact_id: Optional[str],
    content: str,
    sender_name: str,
    sender_phone: str,
    account_id: str,
    inbox_id: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    source: Optional[str] = None
) -> ConversationState:
    """
    Create initial state object from webhook payload.

    Args:
        message_id: Unique message identifier
        conversation_id: Conversation ID (Chatwoot numeric or WhatsApp ID)
        contact_id: Contact ID (may be None for new contacts)
        content: Message text content
        sender_name: Name of message sender
        sender_phone: WhatsApp phone number
        account_id: Chatwoot account ID
        inbox_id: Inbox ID
        conversation_history: Previous messages in conversation (optional)
        source: Message source ("chatwoot", "waha", "360dialog") for response routing

    Returns:
        ConversationState object ready for StateGraph processing
    """
    return ConversationState(
        # Input
        message_id=message_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        sender_type="contact",
        message_type="incoming",
        content=content,
        sender_name=sender_name,
        sender_phone=sender_phone,
        timestamp=datetime.utcnow(),
        account_id=account_id,
        inbox_id=inbox_id,
        source=source,

        # History
        conversation_history=conversation_history or [],
        previous_intents=[],

        # Outputs (None until agents run)
        router_output=None,
        extraction_output=None,
        conversation_output=None,
        crm_output=None,

        # Control
        next_agent="router",  # Always start with router
        escalate_to_human=False,
        error_occurred=False,
        error_message=None,
        retry_count=0,

        # Metadata
        processing_start_time=datetime.utcnow(),
        processing_end_time=None,
        total_tokens_used=0,
        total_cost_usd=0.0
    )


def add_message_to_history(
    state: ConversationState,
    role: Literal["user", "assistant", "system"],
    content: str
) -> ConversationState:
    """
    Add a message to conversation history.

    Args:
        state: Current conversation state
        role: Message role (user/assistant/system)
        content: Message content

    Returns:
        Updated state with message added to history
    """
    state["conversation_history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })
    return state


def calculate_processing_time(state: ConversationState) -> float:
    """
    Calculate total processing time in seconds.

    Args:
        state: Conversation state with timestamps

    Returns:
        Processing time in seconds
    """
    if state.get("processing_end_time"):
        return (state["processing_end_time"] - state["processing_start_time"]).total_seconds()
    return (datetime.utcnow() - state["processing_start_time"]).total_seconds()
