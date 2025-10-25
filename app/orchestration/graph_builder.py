"""
LangGraph StateGraph Builder - Multi-agent orchestration.

This module builds the complete LangGraph StateGraph that orchestrates
all 8 agents in a world-class sales workflow.

Enhanced Flow (Phase 3.5 + RAG + PHASE 9):
START → router (classify intent)
     → documentation (conditional RAG retrieval)
     → expertise (knowledge + escalation detection)
     → extraction (structured data)
     → [rag (Supabase vector search - if car_inquiry intent)] ← PHASE 9 NEW!
     → enhanced_crm (lead scoring + tagging)
     → enhanced_conversation (humanized response)
     → [escalation_router (if escalation needed)]
     → END
"""
from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Try to import RedisSaver, fallback to None if not available
try:
    from langgraph.checkpoint.redis import RedisSaver
except ImportError:
    RedisSaver = None

from app.orchestration.state import ConversationState, add_message_to_history
from app.orchestration.conditional_edges import (
    route_after_router,
    route_after_conversation,
    should_continue_to_crm,
    route_after_enhanced_conversation  # Phase 3.5
)
from app.agents.router_agent import RouterAgent
from app.agents.documentation_agent import DocumentationAgent
from app.agents.expertise_agent import ExpertiseAgent
from app.agents.extraction_agent import ExtractionAgent
from app.agents.enhanced_crm_agent import EnhancedCRMAgent
from app.agents.enhanced_conversation_agent import EnhancedConversationAgent
from app.agents.escalation_router import EscalationRouter
from app.agents.rag_agent import RAGAgent  # PHASE 9: Added RAG agent import
# Legacy agents (kept for backward compatibility)
from app.agents.conversation_agent import ConversationAgent
from app.agents.crm_agent import CRMAgent
from app.config.langgraph_config import (
    ENABLE_CHECKPOINTING,
    CHECKPOINT_BACKEND,
    REDIS_URL
)
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


# ============ AGENT NODE FUNCTIONS ============

def router_node(state: ConversationState) -> ConversationState:
    """
    Router Agent node - Classify intent and priority.

    Args:
        state: Current conversation state

    Returns:
        Updated state with router_output
    """
    logger.info("🔀 Router node executing", extra={"message_id": state["message_id"]})

    agent = RouterAgent()
    result = agent.execute(state)

    # Update state
    state["router_output"] = result["output"]

    # Track intent history
    if "previous_intents" not in state:
        state["previous_intents"] = []
    state["previous_intents"].append(result["output"]["intent"])

    # Check for escalation
    if result["output"]["escalate_to_human"]:
        state["escalate_to_human"] = True

    logger.info(
        "✅ Router classification complete",
        extra={
            "intent": result["output"]["intent"],
            "escalate": result["output"]["escalate_to_human"]
        }
    )

    return state


def documentation_node(state: ConversationState) -> ConversationState:
    """
    Documentation Agent node - Conditional RAG retrieval.

    Args:
        state: Current conversation state

    Returns:
        Updated state with documentation_output
    """
    logger.info("📚 Documentation node executing", extra={"message_id": state["message_id"]})

    agent = DocumentationAgent()
    result = agent.execute(state)

    # Update state with retrieved docs
    # DocumentationAgent returns output dict directly (no nested "output" key)
    state["documentation_output"] = result["output"] if "output" in result else result

    logger.info(
        "✅ Documentation retrieval complete",
        extra={
            "needs_rag": state["documentation_output"]["needs_rag"],
            "num_docs": len(state["documentation_output"]["retrieved_docs"]),
            "category": state["documentation_output"].get("rag_category")
        }
    )

    return state


def expertise_node(state: ConversationState) -> ConversationState:
    """
    Expertise Agent node - Provide knowledge and detect escalation needs.

    Args:
        state: Current conversation state

    Returns:
        Updated state with expertise_output
    """
    logger.info("💡 Expertise node executing", extra={"message_id": state["message_id"]})

    agent = ExpertiseAgent()
    result = agent.execute(state)

    # Update state
    state["expertise_output"] = result["output"]

    # Check for escalation decision
    escalation_decision = result["output"].get("escalation_decision", {})
    if escalation_decision.get("escalate"):
        state["escalate_to_human"] = True
        state["escalation_type"] = escalation_decision.get("escalation_type")
        state["escalation_urgency"] = escalation_decision.get("urgency")
        state["escalation_reason"] = escalation_decision.get("reason")

    logger.info(
        "✅ Expertise classification complete",
        extra={
            "domain": result["output"]["domain"],
            "escalate": escalation_decision.get("escalate", False),
            "has_knowledge": bool(result["output"].get("knowledge"))
        }
    )

    return state


def extraction_node(state: ConversationState) -> ConversationState:
    """
    Extraction Agent node - Extract structured data.

    Args:
        state: Current conversation state

    Returns:
        Updated state with extraction_output
    """
    logger.info("📊 Extraction node executing", extra={"message_id": state["message_id"]})

    agent = ExtractionAgent()
    result = agent.execute(state)

    # Update state
    state["extraction_output"] = result["output"]

    logger.info(
        "✅ Extraction complete",
        extra={
            "confidence": result["output"]["extraction_confidence"],
            "fields_extracted": sum([
                bool(result["output"].get("job_preferences")),
                bool(result["output"].get("salary_expectations")),
                bool(result["output"].get("personal_info")),
                len(result["output"].get("skills", []))
            ])
        }
    )

    return state


def enhanced_crm_node(state: ConversationState) -> ConversationState:
    """
    Enhanced CRM Agent node - Lead scoring (0-100) + intelligent tagging.

    Args:
        state: Current conversation state

    Returns:
        Updated state with enhanced crm_output
    """
    logger.info("📊 Enhanced CRM node executing", extra={"message_id": state["message_id"]})

    agent = EnhancedCRMAgent()
    result = agent.execute(state)

    # Update state with enhanced CRM output
    state["crm_output"] = result["output"]

    # Update contact_id if new contact was created
    if result["output"].get("contact_created"):
        state["contact_id"] = result["output"]["contact_id"]

    logger.info(
        "✅ Enhanced CRM complete",
        extra={
            "lead_score": result["output"]["lead_score"],
            "lead_quality": result["output"]["lead_quality"],
            "tags_added": len(result["output"]["tags_added"]),
            "contact_updated": result["output"].get("contact_updated", False)
        }
    )

    return state


def conversation_node(state: ConversationState) -> ConversationState:
    """
    Conversation Agent node - Generate response.

    Args:
        state: Current conversation state

    Returns:
        Updated state with conversation_output and response message
    """
    logger.info("💬 Conversation node executing", extra={"message_id": state["message_id"]})

    agent = ConversationAgent()
    result = agent.execute(state)

    # Update state
    state["conversation_output"] = result["output"]

    # Add assistant response to history
    state = add_message_to_history(
        state,
        role="assistant",
        content=result["output"]["response_text"]
    )

    # Track RAG iterations if needed
    if result["output"]["needs_rag"]:
        state["rag_iterations"] = state.get("rag_iterations", 0) + 1

    logger.info(
        "✅ Conversation response generated",
        extra={
            "response_length": len(result["output"]["response_text"]),
            "needs_rag": result["output"]["needs_rag"],
            "sentiment": result["output"]["sentiment"]
        }
    )

    return state


def enhanced_conversation_node(state: ConversationState) -> ConversationState:
    """
    Enhanced Conversation Agent node - Humanized Dutch responses with context awareness.

    Args:
        state: Current conversation state

    Returns:
        Updated state with conversation_output and response message
    """
    logger.info("💬 Enhanced Conversation node executing", extra={"message_id": state["message_id"]})

    agent = EnhancedConversationAgent()
    result = agent.execute(state)

    # Update state
    state["conversation_output"] = result["output"]

    # Add assistant response to history
    state = add_message_to_history(
        state,
        role="assistant",
        content=result["output"]["response_text"]
    )

    # Track RAG iterations if needed
    if result["output"].get("needs_rag"):
        state["rag_iterations"] = state.get("rag_iterations", 0) + 1

    logger.info(
        "✅ Enhanced conversation response generated",
        extra={
            "response_length": len(result["output"]["response_text"]),
            "needs_rag": result["output"].get("needs_rag", False),
            "sentiment": result["output"]["sentiment"],
            "recommended_action": result["output"].get("recommended_action")
        }
    )

    return state


def rag_node(state: ConversationState) -> ConversationState:
    """
    RAG Agent node - Search Supabase vector store for matching vehicles.

    PHASE 9: Added RAG node for car_inquiry intent routing.
    Uses semantic search with hybrid filtering (price, fuel, mileage, year).

    Args:
        state: Current conversation state

    Returns:
        Updated state with rag_output
    """
    logger.info("🔍 RAG node executing", extra={"message_id": state["message_id"]})

    agent = RAGAgent()
    result = agent.execute(state)

    # Update state with RAG search results
    state["rag_output"] = result["output"]

    logger.info(
        "✅ RAG search complete",
        extra={
            "num_vehicles": len(result["output"]["vehicles"]),
            "sources_searched": result["output"]["sources_searched"],
            "message_id": state["message_id"]
        }
    )

    return state


def escalation_router_node(state: ConversationState) -> ConversationState:
    """
    Escalation Router node - Handle escalations to human staff.

    Args:
        state: Current conversation state

    Returns:
        Updated state with escalation_output
    """
    logger.info("🚨 Escalation Router node executing", extra={"message_id": state["message_id"]})

    router = EscalationRouter()
    result = router.execute(state)

    # Update state
    state["escalation_output"] = result["output"]

    logger.info(
        "✅ Escalation routing complete",
        extra={
            "escalation_id": result["output"].get("escalation_id"),
            "channels_used": result["output"].get("channels_used", []),
            "escalation_type": state.get("escalation_type"),
            "urgency": state.get("escalation_urgency")
        }
    )

    return state


def crm_node(state: ConversationState) -> ConversationState:
    """
    CRM Agent node - Update Chatwoot contact/conversation.

    Args:
        state: Current conversation state

    Returns:
        Updated state with crm_output
    """
    logger.info("📋 CRM node executing", extra={"message_id": state["message_id"]})

    agent = CRMAgent()
    result = agent.execute(state)

    # Update state
    state["crm_output"] = result["output"]

    # Update contact_id if new contact was created
    if result["output"]["contact_created"]:
        state["contact_id"] = result["output"]["contact_id"]

    logger.info(
        "✅ CRM update complete",
        extra={
            "contact_updated": result["output"]["contact_updated"],
            "tags_added": len(result["output"]["tags_added"])
        }
    )

    return state


# ============ GRAPH BUILDER ============

def build_graph() -> StateGraph:
    """
    Build complete LangGraph StateGraph with all agents and conditional routing.

    Enhanced workflow with 8 agents (including RAG):
    1. router - Classify intent
    2. documentation - Conditional RAG retrieval (NEW)
    3. expertise - Provide knowledge + detect escalation
    4. extraction - Extract structured data
    5. enhanced_crm - Lead scoring + tagging
    6. enhanced_conversation - Humanized response
    7. escalation_router - Handle escalations (conditional)
    8. (legacy crm node kept for backward compatibility)

    Returns:
        Configured StateGraph ready for execution
    """
    logger.info("🔨 Building Enhanced LangGraph StateGraph with 8 agents (including RAG)...")

    # Initialize graph with ConversationState
    graph = StateGraph(ConversationState)

    # Add NEW agent nodes (Phase 3.5 + RAG)
    graph.add_node("router", router_node)
    graph.add_node("documentation", documentation_node)  # RAG retrieval
    graph.add_node("expertise", expertise_node)
    graph.add_node("extraction", extraction_node)
    graph.add_node("rag", rag_node)  # PHASE 9: RAG vector search node
    graph.add_node("enhanced_crm", enhanced_crm_node)
    graph.add_node("enhanced_conversation", enhanced_conversation_node)
    graph.add_node("escalation_router", escalation_router_node)

    # Legacy nodes (kept for backward compatibility)
    graph.add_node("conversation", conversation_node)
    graph.add_node("crm", crm_node)

    # Set entry point
    graph.set_entry_point("router")

    # ========== ENHANCED WORKFLOW (Phase 3.5 + RAG) ==========

    # Router → Documentation (check if RAG needed)
    graph.add_edge("router", "documentation")

    # Documentation → Expertise (pass retrieved docs to expertise)
    graph.add_edge("documentation", "expertise")

    # Expertise → Extraction (always - needed for car interest, budget, etc.)
    graph.add_edge("expertise", "extraction")

    # PHASE 9: Extraction → RAG (for car_inquiry intent) OR Enhanced CRM (other intents)
    # Check router_output intent to decide if RAG search is needed
    def route_after_extraction(state: ConversationState) -> Literal["rag", "enhanced_crm"]:
        """Route after extraction based on intent."""
        router_output = state.get("router_output", {})
        intent = router_output.get("intent", "unknown")

        # Invoke RAG for car inquiry intents
        if intent in ["car_inquiry", "product_inquiry", "inventory_search"]:
            logger.info(f"🔍 Routing to RAG node (intent={intent})")
            return "rag"

        # Skip RAG for other intents
        logger.info(f"⏭️ Skipping RAG (intent={intent})")
        return "enhanced_crm"

    graph.add_conditional_edges(
        "extraction",
        route_after_extraction,
        {
            "rag": "rag",  # Car inquiry → RAG search
            "enhanced_crm": "enhanced_crm"  # Other intents → Skip RAG
        }
    )

    # RAG → Enhanced CRM (pass vehicle results to CRM)
    graph.add_edge("rag", "enhanced_crm")

    # Enhanced CRM → Enhanced Conversation (always - for response generation)
    graph.add_edge("enhanced_crm", "enhanced_conversation")

    # Enhanced Conversation → Conditional routing
    graph.add_conditional_edges(
        "enhanced_conversation",
        route_after_enhanced_conversation,
        {
            "escalation": "escalation_router",  # If escalation needed
            "end": END  # Normal completion
        }
    )

    # Escalation Router → END (always after escalation handling)
    graph.add_edge("escalation_router", END)

    # Compile graph with checkpointing
    if ENABLE_CHECKPOINTING:
        if CHECKPOINT_BACKEND == "redis" and RedisSaver is not None:
            checkpointer = RedisSaver.from_conn_string(REDIS_URL)
            logger.info("✅ Using Redis checkpointer for fault tolerance")
        else:
            checkpointer = MemorySaver()
            if CHECKPOINT_BACKEND == "redis":
                logger.warning("⚠️ RedisSaver not available, falling back to MemorySaver")
            logger.info("✅ Using in-memory checkpointer")

        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        compiled_graph = graph.compile()
        logger.info("⚠️ Checkpointing disabled - no fault tolerance")

    logger.info("✅ Enhanced LangGraph StateGraph built successfully (Phase 3.5 + RAG)")
    logger.info(
        "Enhanced workflow: START → router → documentation → expertise → extraction → enhanced_crm → enhanced_conversation → [escalation_router] → END"
    )

    return compiled_graph


# ============ GRAPH EXECUTION ============

async def execute_graph(
    state: ConversationState,
    config: Dict[str, Any] = None
) -> ConversationState:
    """
    Execute LangGraph StateGraph for a message.

    Args:
        state: Initial conversation state
        config: Optional LangGraph config (for checkpointing, recursion limits, etc.)

    Returns:
        Final conversation state after all agents executed
    """
    logger.info(
        "🚀 Executing LangGraph workflow",
        extra={
            "message_id": state["message_id"],
            "conversation_id": state["conversation_id"]
        }
    )

    # Build graph
    graph = build_graph()

    # Default config
    if config is None:
        config = {
            "recursion_limit": 25,  # Max steps to prevent infinite loops
            "thread_id": state["conversation_id"]  # For checkpointing
        }

    try:
        # Execute graph
        final_state = await graph.ainvoke(state, config)

        # Mark processing complete
        from datetime import datetime
        final_state["processing_end_time"] = datetime.utcnow()

        # Calculate metrics
        from app.orchestration.state import calculate_processing_time
        processing_time = calculate_processing_time(final_state)

        logger.info(
            "✅ LangGraph workflow complete",
            extra={
                "message_id": final_state["message_id"],
                "processing_time_s": round(processing_time, 2),
                "total_tokens": final_state.get("total_tokens_used", 0),
                "total_cost_usd": final_state.get("total_cost_usd", 0.0),
                "response_sent": bool(final_state.get("conversation_output"))
            }
        )

        return final_state

    except Exception as e:
        logger.error(
            "❌ LangGraph workflow failed",
            extra={
                "message_id": state["message_id"],
                "error": str(e)
            },
            exc_info=True
        )

        # Mark error in state
        state["error_occurred"] = True
        state["error_message"] = str(e)

        # Return fallback state
        return state


# ============ HELPER: Visualize Graph ============

def visualize_graph(output_path: str = "langgraph_flow.png") -> None:
    """
    Generate visual diagram of LangGraph flow.

    Requires: pip install pygraphviz

    Args:
        output_path: Path to save diagram image
    """
    try:
        graph = build_graph()
        graph_image = graph.get_graph().draw_mermaid_png()

        with open(output_path, "wb") as f:
            f.write(graph_image)

        logger.info(f"✅ Graph diagram saved to {output_path}")

    except ImportError:
        logger.warning("⚠️ pygraphviz not installed - cannot generate diagram")
    except Exception as e:
        logger.error(f"❌ Failed to generate diagram: {e}")
