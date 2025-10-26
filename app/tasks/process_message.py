"""
Async message processing tasks using Celery.
Handles WhatsApp messages through LangGraph workflow.
"""
import asyncio
from typing import Dict, Any
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_app import celery_app
import structlog
import httpx
import os
import hashlib
import redis
from datetime import timedelta

from app.database.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

# Get centralized Redis client instance
redis_client = get_redis_client()

class CallbackTask(Task):
    """Base task with error handling and retries."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 5}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True

@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.tasks.process_message.process_message_async"
)
def process_message_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming WhatsApp message through LangGraph workflow.

    Args:
        payload: Webhook payload from Chatwoot or 360Dialog

    Returns:
        dict: Processing result with status and response

    Raises:
        Exception: If processing fails after retries
    """
    try:
        logger.info(
            "Processing message",
            extra={
                "task_id": self.request.id,
                "conversation_id": payload.get("conversation", {}).get("id"),
                "message_id": payload.get("id"),
            }
        )

        # Run async LangGraph workflow
        result = asyncio.run(_process_with_langgraph(payload))

        logger.info(
            "Message processed successfully",
            extra={
                "task_id": self.request.id,
                "result": result,
            }
        )

        return result

    except SoftTimeLimitExceeded:
        logger.error(
            "Task soft time limit exceeded",
            extra={"task_id": self.request.id}
        )
        # Route to human agent
        asyncio.run(_escalate_to_human(payload))
        raise

    except Exception as e:
        logger.error(
            "Message processing failed",
            extra={
                "task_id": self.request.id,
                "error": str(e),
                "retry_count": self.request.retries,
            },
            exc_info=True
        )

        # If max retries exceeded, escalate to human
        if self.request.retries >= self.max_retries:
            asyncio.run(_escalate_to_human(payload, error=str(e)))

        raise

async def _process_with_langgraph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process message through LangGraph multi-agent workflow.

    Args:
        payload: Message payload from Chatwoot webhook

    Returns:
        dict: Processing result with response and metadata
    """
    # Import here to avoid circular imports
    from app.orchestration.graph_builder import execute_graph
    from app.orchestration.state import create_initial_state

    # Extract message details from webhook
    conversation = payload.get("conversation", {})
    sender = payload.get("sender", {})
    message_content = payload.get("content", "")
    source = payload.get("source")

    # Get conversation history from Chatwoot
    conversation_history = []

    if source == "chatwoot":
        # Chatwoot messages: Use conversation ID from payload
        conversation_history = await _fetch_conversation_history(
            conversation.get("id")
        )

    # Create initial state using helper function
    initial_state = create_initial_state(
        message_id=str(payload.get("id")),
        conversation_id=str(conversation.get("id")),
        contact_id=str(sender.get("id")) if sender.get("id") else None,
        content=message_content,
        sender_name=sender.get("name", "Unknown"),
        sender_phone=sender.get("phone_number", ""),
        account_id=str(payload.get("account", {}).get("id", os.getenv("CHATWOOT_ACCOUNT_ID", "2"))),
        inbox_id=str(conversation.get("inbox_id", "")),
        conversation_history=conversation_history,
        source=payload.get("source")  # "chatwoot", "waha", or "360dialog"
    )

    # Execute LangGraph StateGraph workflow
    final_state = await execute_graph(initial_state)

    # Send response back via appropriate channel if agent handled it
    conversation_output = final_state.get("conversation_output")
    if conversation_output and not final_state.get("escalate_to_human"):
        # Route response based on message source
        source = final_state.get("source")

        # DEBUG: Log conversation_output structure
        logger.debug(
            "🐛 DEBUG conversation_output structure",
            extra={
                "type": type(conversation_output).__name__,
                "is_dict": isinstance(conversation_output, dict),
                "keys": list(conversation_output.keys()) if isinstance(conversation_output, dict) else None,
                "response_text_type": type(conversation_output.get("response_text")).__name__ if isinstance(conversation_output, dict) else None,
                "response_text_preview": conversation_output.get("response_text", "")[:100] if isinstance(conversation_output, dict) else str(conversation_output)[:100]
            }
        )

        # Send via Twilio WhatsApp Business API
        phone_number = final_state["conversation_id"]  # Should be E.164 format

        await _send_to_twilio(
            phone_number=phone_number,
            message=conversation_output["response_text"]
        )

        # Sync to Chatwoot for unified view
        chatwoot_conv_id = payload.get("chatwoot_conversation_id")
        if chatwoot_conv_id:
            await _sync_twilio_to_chatwoot(
                chatwoot_conversation_id=chatwoot_conv_id,
                phone_number=phone_number,
                sender_name=final_state.get("sender_name", "WhatsApp User"),
                incoming_message=final_state["content"],
                outgoing_message=conversation_output["response_text"]
            )
        else:
            logger.warning("⚠️ No Chatwoot conversation ID - skipping Chatwoot sync")

    # Return processing summary
    # Safe None handling for router_output
    router_output = final_state.get("router_output") or {}

    return {
        "message_id": final_state["message_id"],
        "conversation_id": final_state["conversation_id"],
        "intent": router_output.get("intent"),
        "response_sent": bool(conversation_output),
        "escalated": final_state.get("escalate_to_human", False),
        "error": final_state.get("error_occurred", False),
        "processing_time_s": final_state.get("processing_time_s", 0),
        "total_cost_usd": final_state.get("total_cost_usd", 0.0),
        "total_tokens": final_state.get("total_tokens_used", 0),
    }


async def _fetch_conversation_history(conversation_id: str, limit: int = 10) -> list:
    """
    Fetch recent messages from Chatwoot conversation for context.

    Args:
        conversation_id: Chatwoot conversation ID
        limit: Maximum number of messages to fetch

    Returns:
        List of message dicts with role and content
    """
    chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    url = f"{chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"

    headers = {
        "api_access_token": api_token,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()

            messages = response.json()

            # Convert to conversation history format
            history = []
            for msg in messages[-limit:]:  # Last N messages
                role = "user" if msg["message_type"] == "incoming" else "assistant"
                history.append({
                    "role": role,
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at")
                })

            return history

    except Exception as e:
        logger.warning(
            f"Failed to fetch conversation history: {e}",
            extra={"conversation_id": conversation_id}
        )
        return []  # Return empty history on error

async def _send_to_chatwoot(conversation_id: int, message: str) -> None:
    """
    Send agent response to Chatwoot API.

    Args:
        conversation_id: Chatwoot conversation ID
        message: Response message to send
    """
    chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    url = f"{chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"

    headers = {
        "api_access_token": api_token,
        "Content-Type": "application/json",
    }

    payload = {
        "content": message,
        "message_type": "outgoing",
        "private": False,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()

    logger.info(
        "Message sent to Chatwoot",
        extra={"conversation_id": conversation_id}
    )

async def _send_to_twilio(phone_number: str, message: str) -> None:
    """
    Send agent response directly to WhatsApp via Twilio API.

    Args:
        phone_number: Recipient phone number (E.164 format, e.g., "+31612345678")
        message: Response message to send
    """
    try:
        from app.integrations.twilio_client import get_twilio_client

        # Get Twilio client singleton
        twilio_client = get_twilio_client()

        # Send message with retry logic built into client
        result = await twilio_client.send_message(
            to_number=phone_number,
            message=message
        )

        if result["status"] == "sent":
            logger.info(
                "Message sent to Twilio",
                extra={
                    "phone_number": phone_number,
                    "message_sid": result.get("message_sid"),
                    "message_length": len(message)
                }
            )
        elif result["status"] == "rate_limited":
            logger.warning(
                "Twilio rate limit reached",
                extra={"phone_number": phone_number, "error": result.get("error")}
            )
            raise Exception(f"Twilio rate limited: {result.get('error')}")
        else:
            logger.error(
                "Failed to send message via Twilio",
                extra={
                    "phone_number": phone_number,
                    "error": result.get("error"),
                    "attempts": result.get("attempts")
                }
            )
            raise Exception(f"Twilio send failed: {result.get('error')}")

    except Exception as e:
        logger.error(
            f"Failed to send message via Twilio: {e}",
            extra={"phone_number": phone_number, "error": str(e)},
            exc_info=True
        )
        raise

async def _sync_twilio_to_chatwoot(
    chatwoot_conversation_id: int,
    phone_number: str,
    sender_name: str,
    incoming_message: str,
    outgoing_message: str
) -> None:
    """
    Sync Twilio WhatsApp messages to Chatwoot for chat history visibility.

    Args:
        chatwoot_conversation_id: Existing Chatwoot conversation ID (integer)
        phone_number: WhatsApp phone number (E.164 format, e.g., "+31612345678")
        sender_name: Sender's display name
        incoming_message: User's incoming message
        outgoing_message: AI's response message
    """
    try:
        from app.integrations.chatwoot_sync import ChatwootSync

        sync = ChatwootSync()

        # Sync incoming message directly to known conversation
        await sync._send_message_to_chatwoot(
            conversation_id=chatwoot_conversation_id,
            content=incoming_message,
            message_type="incoming"
        )

        # Sync outgoing message directly to known conversation
        await sync._send_message_to_chatwoot(
            conversation_id=chatwoot_conversation_id,
            content=outgoing_message,
            message_type="outgoing"
        )

        logger.info(
            "✅ Twilio messages synced to Chatwoot",
            phone_number=phone_number,
            chatwoot_conversation_id=chatwoot_conversation_id
        )

    except Exception as e:
        logger.error(
            "⚠️ Chatwoot sync failed (non-critical)",
            phone_number=phone_number,
            chatwoot_conversation_id=chatwoot_conversation_id,
            error=str(e),
            exc_info=True
        )
        # Don't raise - sync failure shouldn't break Twilio message flow

async def _escalate_to_human(payload: Dict[str, Any], error: str = None) -> None:
    """
    Escalate conversation to human agent.

    Args:
        payload: Original message payload
        error: Error message if processing failed
    """
    # Safe dict access with None handling
    conversation = payload.get("conversation") or {}
    conversation_id = conversation.get("id")

    if not conversation_id:
        logger.error("Cannot escalate: missing conversation_id", extra={"payload": payload})
        return

    escalation_message = (
        "⚠️ Escalated to human agent.\n"
        f"Reason: {'Processing error' if error else 'Agent requires human assistance'}\n"
    )

    if error:
        escalation_message += f"Error details: {error}"

    # Send internal note to Chatwoot
    await _send_to_chatwoot(conversation_id, escalation_message)

    # Update conversation status
    chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    url = f"{chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}"

    headers = {
        "api_access_token": api_token,
        "Content-Type": "application/json",
    }

    payload_update = {
        "status": "open",
        "priority": "high",
    }

    async with httpx.AsyncClient() as client:
        await client.patch(url, json=payload_update, headers=headers, timeout=10.0)

    logger.info(
        "Conversation escalated to human",
        extra={"conversation_id": conversation_id, "error": error}
    )

@celery_app.task(name="app.tasks.process_message.process_batch_messages")
def process_batch_messages(payloads: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process multiple messages in batch (for bulk imports).

    Args:
        payloads: List of message payloads

    Returns:
        dict: Batch processing summary
    """
    results = []

    for payload in payloads:
        try:
            # Queue individual message processing
            task = process_message_async.delay(payload)
            results.append({
                "message_id": payload.get("id"),
                "task_id": task.id,
                "status": "queued"
            })
        except Exception as e:
            logger.error(
                "Failed to queue message",
                extra={"message_id": payload.get("id"), "error": str(e)}
            )
            results.append({
                "message_id": payload.get("id"),
                "status": "failed",
                "error": str(e)
            })

    return {
        "total": len(payloads),
        "queued": sum(1 for r in results if r["status"] == "queued"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
