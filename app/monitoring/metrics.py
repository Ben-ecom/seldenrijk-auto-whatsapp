"""
Prometheus metrics for monitoring application performance.
Tracks requests, errors, task processing, and resource usage.
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Callable
from functools import wraps
import time

# Create registry
registry = CollectorRegistry()

# ============ HTTP METRICS ============

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"],
    registry=registry
)

# ============ AGENT METRICS ============

# BaseAgent metrics (used by all 4 agents)
AGENT_CALLS = Counter(
    "agent_calls_total",
    "Total agent calls",
    ["agent", "model"],
    registry=registry
)

AGENT_LATENCY = Histogram(
    "agent_latency_seconds",
    "Agent latency in seconds",
    ["agent", "model"],
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

AGENT_ERRORS = Counter(
    "agent_execution_errors_total",
    "Total agent execution errors",
    ["agent", "error_type"],
    registry=registry
)

AGENT_TOKENS = Counter(
    "agent_tokens_total",
    "Total tokens used by agents",
    ["agent", "model", "token_type"],  # token_type: input, output, cache_read, cache_write
    registry=registry
)

AGENT_COST = Counter(
    "agent_cost_usd_total",
    "Total cost in USD for agent calls",
    ["agent", "model"],
    registry=registry
)

# Legacy metrics (kept for backwards compatibility)
agent_invocations_total = Counter(
    "agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],
    registry=registry
)

agent_duration_seconds = Histogram(
    "agent_duration_seconds",
    "Agent processing duration in seconds",
    ["agent_name"],
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

agent_errors_total = Counter(
    "agent_errors_total",
    "Total agent errors",
    ["agent_name", "error_type"],
    registry=registry
)

# ============ MESSAGE PROCESSING METRICS ============

messages_processed_total = Counter(
    "messages_processed_total",
    "Total messages processed",
    ["channel", "intent", "status"],
    registry=registry
)

messages_processing_duration_seconds = Histogram(
    "messages_processing_duration_seconds",
    "Message processing duration in seconds",
    ["channel"],
    registry=registry,
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
)

messages_queued = Gauge(
    "messages_queued",
    "Number of messages in processing queue",
    registry=registry
)

messages_escalated_total = Counter(
    "messages_escalated_total",
    "Total messages escalated to human agents",
    ["reason"],
    registry=registry
)

# ============ RAG METRICS ============

rag_searches_total = Counter(
    "rag_searches_total",
    "Total RAG searches performed",
    ["status"],
    registry=registry
)

rag_search_duration_seconds = Histogram(
    "rag_search_duration_seconds",
    "RAG search duration in seconds",
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

rag_documents_retrieved = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per RAG search",
    registry=registry,
    buckets=(0, 1, 3, 5, 10, 20, 50)
)

# ============ CELERY TASK METRICS ============

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks processed",
    ["task_name", "status"],
    registry=registry
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0)
)

celery_tasks_queued = Gauge(
    "celery_tasks_queued",
    "Number of Celery tasks in queue",
    ["queue_name"],
    registry=registry
)

# ============ DATABASE METRICS ============

db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table"],
    registry=registry
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    registry=registry,
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    registry=registry
)

db_connection_pool_available = Gauge(
    "db_connection_pool_available",
    "Available database connections in pool",
    registry=registry
)

# ============ WEBHOOK METRICS ============

webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total webhook requests received",
    ["source", "status"],
    registry=registry
)

webhook_signature_errors_total = Counter(
    "webhook_signature_errors_total",
    "Total webhook signature verification failures",
    ["source"],
    registry=registry
)

# ============ GDPR METRICS ============

gdpr_requests_total = Counter(
    "gdpr_requests_total",
    "Total GDPR requests processed",
    ["request_type", "status"],
    registry=registry
)

gdpr_data_deletions_total = Counter(
    "gdpr_data_deletions_total",
    "Total GDPR data deletions",
    registry=registry
)

gdpr_data_exports_total = Counter(
    "gdpr_data_exports_total",
    "Total GDPR data exports",
    registry=registry
)

# ============ DECORATORS FOR AUTOMATIC TRACKING ============

def track_agent_execution(agent_name: str):
    """
    Decorator to track agent execution metrics.

    Usage:
        @track_agent_execution("router_agent")
        async def router_agent_node(state):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                agent_errors_total.labels(
                    agent_name=agent_name,
                    error_type=type(e).__name__
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                agent_invocations_total.labels(
                    agent_name=agent_name,
                    status=status
                ).inc()
                agent_duration_seconds.labels(agent_name=agent_name).observe(duration)

        return wrapper
    return decorator

def track_rag_search(func: Callable):
    """
    Decorator to track RAG search metrics.

    Usage:
        @track_rag_search
        async def search_knowledge_base(query):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"

        try:
            results = await func(*args, **kwargs)
            rag_documents_retrieved.observe(len(results))
            return results
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            rag_searches_total.labels(status=status).inc()
            rag_search_duration_seconds.observe(duration)

    return wrapper

def track_db_query(operation: str, table: str):
    """
    Decorator to track database query metrics.

    Usage:
        @track_db_query("select", "conversations")
        async def get_conversation(conversation_id):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_queries_total.labels(operation=operation, table=table).inc()
                db_query_duration_seconds.labels(operation=operation).observe(duration)

        return wrapper
    return decorator

# ============ HELPER FUNCTIONS ============

def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus format.

    Returns:
        bytes: Metrics in Prometheus exposition format
    """
    return generate_latest(registry)

def track_message_processed(channel: str, intent: str, status: str, duration: float):
    """
    Track message processing metrics manually.

    Args:
        channel: Message channel (whatsapp, instagram, etc.)
        intent: Detected intent
        status: Processing status (success, error, escalated)
        duration: Processing duration in seconds
    """
    messages_processed_total.labels(
        channel=channel,
        intent=intent,
        status=status
    ).inc()

    messages_processing_duration_seconds.labels(channel=channel).observe(duration)

def track_message_escalated(reason: str):
    """
    Track message escalation to human agent.

    Args:
        reason: Escalation reason
    """
    messages_escalated_total.labels(reason=reason).inc()

def update_queue_size(queue_size: int):
    """
    Update message queue size gauge.

    Args:
        queue_size: Current queue size
    """
    messages_queued.set(queue_size)
