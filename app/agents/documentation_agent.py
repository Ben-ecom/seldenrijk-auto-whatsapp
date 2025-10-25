"""
Documentation Retrieval Agent - Conditional RAG for technical knowledge.

This agent decides WHETHER and WHAT to retrieve from the documentation database.
Different from rag_agent.py which handles car inventory scraping.
"""
from typing import Dict, Any
from anthropic import Anthropic
from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import ConversationState
from app.monitoring.logging_config import get_logger
from app.rag import get_retriever, format_retrieved_context
import json

logger = get_logger(__name__)


class DocumentationAgent(BaseAgent):
    """
    Documentation Agent - Conditional document retrieval for RAG.

    Analyzes the conversation and decides:
    1. Does this query need documentation retrieval?
    2. If yes, what category/query should be used?
    3. Retrieves relevant documents and formats context
    """

    def __init__(self):
        """Initialize Documentation agent."""
        # Use router config (fast Haiku for decision-making)
        config = AGENT_CONFIGS["router"]

        super().__init__(
            agent_name="documentation",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client
        self.client = Anthropic(**config["config"])
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 500)

        self.retriever = get_retriever()

        logger.info("✅ Documentation Agent initialized for RAG retrieval")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute Documentation agent - conditional document retrieval.

        Args:
            state: Current conversation state

        Returns:
            Dict with:
                - retrieved_docs: List of retrieved documents
                - retrieved_context: Formatted context string
                - needs_rag: Boolean
                - rag_query: Query used for retrieval
        """
        logger.info(
            "📚 Documentation Agent executing",
            extra={"message_id": state["message_id"]}
        )

        # Get user message and intent
        user_message = state["content"]
        intent = state.get("router_output", {}).get("intent", "unknown")

        # 1. Decision: Does this need documentation retrieval?
        rag_decision = self._decide_rag_need(
            message=user_message,
            intent=intent,
            conversation_history=state.get("conversation_history", [])
        )

        output = {
            "needs_rag": rag_decision["needs_rag"],
            "rag_query": rag_decision.get("rag_query"),
            "rag_category": rag_decision.get("rag_category"),
            "retrieved_docs": [],
            "retrieved_context": "",
            "reasoning": rag_decision.get("reasoning", "")
        }

        # 2. If RAG needed, retrieve documents
        if rag_decision["needs_rag"] and self.retriever.enabled:
            logger.info(
                "🔍 Retrieving documents",
                extra={
                    "query": rag_decision["rag_query"],
                    "category": rag_decision.get("rag_category")
                }
            )

            try:
                # Import asyncio for async retrieval
                import asyncio

                # Retrieve documents
                retrieved_docs = asyncio.run(
                    self.retriever.retrieve(
                        query=rag_decision["rag_query"],
                        category=rag_decision.get("rag_category"),
                        max_results=5,
                        threshold=0.7
                    )
                )

                output["retrieved_docs"] = retrieved_docs
                output["retrieved_context"] = format_retrieved_context(retrieved_docs)

                logger.info(
                    f"✅ Retrieved {len(retrieved_docs)} documents",
                    extra={"num_docs": len(retrieved_docs)}
                )

            except Exception as e:
                logger.error(f"❌ Document retrieval failed: {e}", exc_info=True)
                output["reasoning"] += f" | Retrieval error: {str(e)}"

        elif rag_decision["needs_rag"] and not self.retriever.enabled:
            logger.warning("⚠️ RAG retrieval disabled - continuing without docs")
            output["reasoning"] += " | RAG retrieval disabled (missing credentials)"

        return output

    def _decide_rag_need(
        self,
        message: str,
        intent: str,
        conversation_history: list
    ) -> Dict[str, Any]:
        """
        Decide if RAG retrieval is needed and formulate query.

        Args:
            message: User message
            intent: Classified intent
            conversation_history: Recent messages

        Returns:
            Dict with needs_rag, rag_query, rag_category, reasoning
        """
        # Recent context (last 3 messages)
        recent_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history[-3:]
        ]) if conversation_history else "No previous messages"

        system_prompt = """You decide if this query needs technical documentation retrieval.

Guidelines:
- RAG is needed for: API integration questions, technical implementation, error troubleshooting, architecture decisions
- RAG is NOT needed for: General greetings, job questions, availability questions, car interest questions

Available documentation categories:
- chatwoot: Chatwoot API (contacts, conversations, messages, webhooks)
- waha: WAHA/WhatsApp API (sending messages, webhook handling)
- langgraph: Multi-agent workflows, state management
- anthropic: Claude API best practices
- rag: RAG and Agentic RAG patterns
- supabase: Vector database, pgvector operations
- docker: Docker Compose networking

Output JSON only:
{
    "needs_rag": true/false,
    "rag_query": "reformulated search query (if needed)",
    "rag_category": "category name or null",
    "reasoning": "brief explanation"
}"""

        user_prompt = f"""User message: "{message}"
Intent: {intent}
Recent context:
{recent_context}

Does this need documentation retrieval?"""

        try:
            # Use Claude for decision
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Parse JSON response - Claude returns text in content blocks
            decision_text = response.content[0].text

            # Extract JSON from response (Claude may wrap it in markdown)
            if "```json" in decision_text:
                decision_text = decision_text.split("```json")[1].split("```")[0].strip()
            elif "```" in decision_text:
                decision_text = decision_text.split("```")[1].split("```")[0].strip()

            decision = json.loads(decision_text)

            logger.debug(
                "RAG decision made",
                extra={
                    "needs_rag": decision["needs_rag"],
                    "category": decision.get("rag_category")
                }
            )

            return decision

        except Exception as e:
            logger.error(f"RAG decision failed: {e}", exc_info=True)

            # Fallback: no RAG
            return {
                "needs_rag": False,
                "reasoning": f"Decision error: {str(e)}"
            }
