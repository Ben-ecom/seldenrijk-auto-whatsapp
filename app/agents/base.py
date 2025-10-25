"""
Base Agent Class - Foundation for all LangGraph agents.

Provides retry logic, error handling, token tracking, and cost calculation.
All agents (Router, Extraction, Conversation, CRM) inherit from this class.
"""
import time
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import openai
from anthropic import APIError as AnthropicAPIError

from app.monitoring.logging_config import get_logger
from app.monitoring.sentry_config import capture_exception
from app.monitoring.metrics import (
    AGENT_CALLS,
    AGENT_ERRORS,
    AGENT_LATENCY,
    AGENT_TOKENS,
    AGENT_COST
)

logger = get_logger(__name__)


# ============ PRICING (as of Jan 2025) ============
# Source: https://openai.com/api/pricing/ and https://www.anthropic.com/pricing

MODEL_PRICING = {
    # OpenAI GPT-4o-mini
    "gpt-4o-mini": {
        "input_per_1m": 0.150,   # $0.15 per 1M input tokens
        "output_per_1m": 0.600,  # $0.60 per 1M output tokens
    },
    # OpenAI GPT-4o
    "gpt-4o": {
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
    },
    # Anthropic Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
        "cache_write_per_1m": 3.75,   # Prompt caching (write)
        "cache_read_per_1m": 0.30,    # Prompt caching (read) - 90% discount!
    },
}


class BaseAgent:
    """
    Base class for all agents with retry logic and monitoring.

    Features:
    - Automatic retries with exponential backoff
    - Token usage tracking
    - Cost calculation
    - Prometheus metrics
    - Sentry error tracking
    - Circuit breaker pattern (via metrics)

    Usage:
        class MyAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_name="my_agent",
                    model="gpt-4o-mini"
                )

            def _execute(self, state: ConversationState) -> Dict[str, Any]:
                # Agent-specific logic here
                return result
    """

    def __init__(
        self,
        agent_name: Literal["router", "extraction", "conversation", "crm"],
        model: str,
        max_retries: int = 3,
        timeout_seconds: int = 30
    ):
        """
        Initialize base agent.

        Args:
            agent_name: Agent identifier for metrics/logging
            model: Model name (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
            max_retries: Maximum retry attempts on failure
            timeout_seconds: Timeout for agent execution
        """
        self.agent_name = agent_name
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        # Pricing info
        self.pricing = MODEL_PRICING.get(model, {
            "input_per_1m": 0.0,
            "output_per_1m": 0.0
        })

        logger.info(
            f"✅ Initialized {agent_name} agent",
            extra={
                "agent": agent_name,
                "model": model,
                "max_retries": max_retries,
                "timeout": timeout_seconds
            }
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, AnthropicAPIError)),
        reraise=True
    )
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent with retry logic and monitoring.

        This method wraps the agent-specific _execute() method with:
        - Retry logic (exponential backoff)
        - Latency tracking
        - Token/cost tracking
        - Error handling
        - Prometheus metrics

        Args:
            state: ConversationState dict

        Returns:
            Updated state dict with agent output

        Raises:
            Exception: After max retries exceeded
        """
        start_time = time.time()

        try:
            # Increment call counter
            AGENT_CALLS.labels(agent=self.agent_name, model=self.model).inc()

            logger.info(
                f"🚀 Executing {self.agent_name} agent",
                extra={
                    "agent": self.agent_name,
                    "model": self.model,
                    "message_id": state.get("message_id"),
                    "conversation_id": state.get("conversation_id")
                }
            )

            # Execute agent-specific logic (implemented by subclass)
            result = self._execute(state)

            # Calculate latency
            latency = time.time() - start_time
            AGENT_LATENCY.labels(agent=self.agent_name, model=self.model).observe(latency)

            # Track tokens and cost if available
            if "tokens_used" in result:
                tokens = result["tokens_used"]
                # Track each token type separately
                for token_type in ["input", "output", "cache_read", "cache_write"]:
                    token_count = tokens.get(token_type, 0)
                    if token_count > 0:
                        AGENT_TOKENS.labels(
                            agent=self.agent_name,
                            model=self.model,
                            token_type=token_type
                        ).inc(token_count)

                # Calculate cost
                cost = self._calculate_cost(
                    input_tokens=tokens.get("input", 0),
                    output_tokens=tokens.get("output", 0),
                    cache_read_tokens=tokens.get("cache_read", 0),
                    cache_write_tokens=tokens.get("cache_write", 0)
                )
                AGENT_COST.labels(agent=self.agent_name, model=self.model).inc(cost)

                # Add to state
                state["total_tokens_used"] = state.get("total_tokens_used", 0) + tokens.get("total", 0)
                state["total_cost_usd"] = state.get("total_cost_usd", 0.0) + cost

            logger.info(
                f"✅ {self.agent_name} agent completed",
                extra={
                    "agent": self.agent_name,
                    "latency_ms": round(latency * 1000, 2),
                    "tokens": result.get("tokens_used"),
                    "cost_usd": result.get("cost_usd")
                }
            )

            return result

        except Exception as e:
            # Increment error counter
            AGENT_ERRORS.labels(
                agent=self.agent_name,
                error_type=type(e).__name__
            ).inc()

            logger.error(
                f"❌ {self.agent_name} agent failed",
                extra={
                    "agent": self.agent_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message_id": state.get("message_id")
                },
                exc_info=True
            )

            # Send to Sentry
            capture_exception(e, extra={
                "agent": self.agent_name,
                "model": self.model,
                "state": state
            })

            # Update state with error
            state["error_occurred"] = True
            state["error_message"] = f"{self.agent_name} failed: {str(e)}"
            state["retry_count"] = state.get("retry_count", 0) + 1

            # Re-raise for retry logic
            raise

    def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent-specific execution logic.

        This method MUST be implemented by subclasses.

        Args:
            state: ConversationState dict

        Returns:
            Dict with agent output and metadata:
            {
                "output": {...},  # Agent-specific output
                "tokens_used": {
                    "input": 100,
                    "output": 50,
                    "total": 150,
                    "cache_read": 0,  # Optional (Anthropic only)
                    "cache_write": 0  # Optional (Anthropic only)
                },
                "cost_usd": 0.0015,
                "latency_ms": 250.5
            }
        """
        raise NotImplementedError("Subclass must implement _execute()")

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0
    ) -> float:
        """
        Calculate cost in USD for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_read_tokens: Cached tokens read (Anthropic only)
            cache_write_tokens: Cached tokens written (Anthropic only)

        Returns:
            Total cost in USD
        """
        cost = 0.0

        # Input tokens
        cost += (input_tokens / 1_000_000) * self.pricing.get("input_per_1m", 0.0)

        # Output tokens
        cost += (output_tokens / 1_000_000) * self.pricing.get("output_per_1m", 0.0)

        # Cache tokens (Anthropic only)
        if cache_read_tokens > 0:
            cost += (cache_read_tokens / 1_000_000) * self.pricing.get("cache_read_per_1m", 0.0)
        if cache_write_tokens > 0:
            cost += (cache_write_tokens / 1_000_000) * self.pricing.get("cache_write_per_1m", 0.0)

        return round(cost, 6)  # Round to 6 decimal places ($0.000001)
