"""
Sentry error tracking and performance monitoring configuration.
Captures exceptions, performance metrics, and breadcrumbs.
"""
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry() -> None:
    """
    Initialize Sentry SDK with all integrations.
    Only initializes if SENTRY_DSN is set.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        print("⚠️ SENTRY_DSN not set. Error tracking disabled.")
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,

        # Performance monitoring
        traces_sample_rate=0.1 if environment == "production" else 1.0,

        # Error sampling (capture all errors)
        sample_rate=1.0,

        # Include local variables in stack traces
        attach_stacktrace=True,

        # Include source code in stack traces
        enable_tracing=True,

        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # Group by endpoint
                failed_request_status_codes=[500, 599],  # Track 5xx errors
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,  # Monitor Celery Beat periodic tasks
                exclude_beat_tasks=[],  # Don't exclude any tasks
            ),
            RedisIntegration(),
            HttpxIntegration(),
            SqlalchemyIntegration(),
        ],

        # GDPR compliance - don't send PII
        send_default_pii=False,

        # Max breadcrumbs to store
        max_breadcrumbs=50,

        # Custom filters
        before_send=before_send_filter,
        before_breadcrumb=before_breadcrumb_filter,

        # Release tracking (use git commit SHA or version)
        release=os.getenv("GIT_COMMIT_SHA", "unknown"),

        # Debug mode (only in development)
        debug=environment == "development",
    )

    print(f"✅ Sentry initialized (environment: {environment})")

def before_send_filter(event, hint):
    """
    Filter events before sending to Sentry.
    Remove sensitive data and apply custom logic.

    Args:
        event: Sentry event dict
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    # Don't send health check errors
    if "healthcheck" in str(event.get("transaction", "")):
        return None

    # Remove sensitive data from request bodies
    if "request" in event:
        request = event["request"]

        # Remove sensitive headers
        if "headers" in request:
            sensitive_headers = ["authorization", "api_access_token", "cookie"]
            for header in sensitive_headers:
                request["headers"].pop(header, None)

        # Remove sensitive query params
        if "query_string" in request:
            sensitive_params = ["token", "password", "api_key"]
            for param in sensitive_params:
                if param in request["query_string"]:
                    request["query_string"] = "[FILTERED]"
                    break

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["project"] = "whatsapp-recruitment"

    return event

def before_breadcrumb_filter(crumb, hint):
    """
    Filter breadcrumbs before adding to event.

    Args:
        crumb: Breadcrumb dict
        hint: Additional context

    Returns:
        Modified breadcrumb or None to drop it
    """
    # Don't log Redis GET operations (too noisy)
    if crumb.get("category") == "redis" and crumb.get("data", {}).get("command") == "GET":
        return None

    # Remove sensitive data from HTTP breadcrumbs
    if crumb.get("category") == "httplib":
        crumb.setdefault("data", {})
        if "url" in crumb["data"]:
            # Remove query params from URLs
            crumb["data"]["url"] = crumb["data"]["url"].split("?")[0]

    return crumb

def capture_exception(error: Exception, **extra_context) -> str:
    """
    Manually capture an exception with additional context.

    Args:
        error: Exception to capture
        **extra_context: Additional context dict

    Returns:
        str: Sentry event ID
    """
    with sentry_sdk.push_scope() as scope:
        # Add extra context
        for key, value in extra_context.items():
            scope.set_extra(key, value)

        # Capture exception
        event_id = sentry_sdk.capture_exception(error)

    return event_id

def capture_message(message: str, level: str = "info", **extra_context) -> str:
    """
    Manually capture a message with additional context.

    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **extra_context: Additional context dict

    Returns:
        str: Sentry event ID
    """
    with sentry_sdk.push_scope() as scope:
        # Add extra context
        for key, value in extra_context.items():
            scope.set_extra(key, value)

        # Capture message
        event_id = sentry_sdk.capture_message(message, level=level)

    return event_id

def set_user_context(user_id: str, email: str = None, username: str = None) -> None:
    """
    Set user context for current scope.

    Args:
        user_id: User identifier
        email: User email (optional, filtered if GDPR mode)
        username: Username (optional)
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email if os.getenv("SENTRY_SEND_PII", "false") == "true" else None,
        "username": username,
    })

def set_context(context_name: str, context_data: dict) -> None:
    """
    Set custom context for current scope.

    Args:
        context_name: Context identifier
        context_data: Context data dict
    """
    sentry_sdk.set_context(context_name, context_data)

def add_breadcrumb(message: str, category: str, level: str = "info", **data) -> None:
    """
    Add a breadcrumb to the current scope.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "http", "db", "auth")
        level: Severity level
        **data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data,
    )
