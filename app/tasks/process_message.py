"""
Async message processing tasks using Celery.
Handles WhatsApp messages through LangGraph workflow.
"""
import asyncio
from typing import Dict, Any
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_app import celery_app
from app.monitoring.logging_config import get_logger
import httpx
import os
import hashlib
import redis
from datetime import timedelta

logger = get_logger(__name__)

# Initialize Redis client for message deduplication
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

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
    elif source == "waha":
        # WAHA messages: Get conversation ID from Chatwoot sync
        # We need to sync FIRST to get/create the Chatwoot conversation
        from app.integrations.chatwoot_sync import ChatwootSync

        sync = ChatwootSync()

        # For WAHA, the conversation ID IS the WhatsApp chat ID (e.g., "31639121747@c.us")
        whatsapp_chat_id = conversation.get("id")

        # Get or create contact
        contact_id = await sync.get_or_create_contact(
            phone_number=whatsapp_chat_id,
            name=sender.get("name", "WhatsApp User")
        )

        chatwoot_conversation_id = None
        if contact_id:
            # Get or create conversation
            chatwoot_conversation_id = await sync.get_or_create_conversation(
                contact_id=contact_id,
                source_id=whatsapp_chat_id
            )

        # CRITICAL FIX: Store Chatwoot conversation ID for later use
        # This is needed for _sync_waha_to_chatwoot to work properly
        payload["chatwoot_conversation_id"] = chatwoot_conversation_id

        if chatwoot_conversation_id:
            # HYBRID APPROACH: Try Redis cache first, fallback to Chatwoot API
            cache_key = f"conversation:{whatsapp_chat_id}:history"

            try:
                cached_history = redis_client.get(cache_key)
                if cached_history:
                    import json
                    conversation_history = json.loads(cached_history)
                    logger.info(
                        f"✅ Loaded {len(conversation_history)} messages from Redis cache",
                        extra={
                            "conversation_id": chatwoot_conversation_id,
                            "history_count": len(conversation_history),
                            "cache_key": cache_key,
                            "source": "redis_cache"
                        }
                    )
                else:
                    # Fetch from Chatwoot API
                    conversation_history = await _fetch_conversation_history(
                        str(chatwoot_conversation_id)
                    )
                    logger.info(
                        f"✅ Fetched {len(conversation_history)} messages from Chatwoot history",
                        extra={
                            "conversation_id": chatwoot_conversation_id,
                            "history_count": len(conversation_history),
                            "source": "chatwoot_api"
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Redis cache read failed, falling back to Chatwoot API: {e}",
                    extra={"cache_key": cache_key}
                )
                conversation_history = await _fetch_conversation_history(
                    str(chatwoot_conversation_id)
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

        if source == "waha":
            # Send directly via WAHA for messages from WAHA webhook
            await _send_to_waha(
                chat_id=final_state["conversation_id"],
                message=conversation_output["response_text"]
            )

            # ALSO sync to Chatwoot for visibility/history
            chatwoot_conv_id = payload.get("chatwoot_conversation_id")
            if chatwoot_conv_id:
                await _sync_waha_to_chatwoot(
                    chatwoot_conversation_id=chatwoot_conv_id,
                    phone_number=final_state["conversation_id"],  # WhatsApp chat ID
                    sender_name=final_state.get("sender_name", "WhatsApp User"),
                    incoming_message=final_state["content"],
                    outgoing_message=conversation_output["response_text"]
                )
            else:
                logger.warning("⚠️ No Chatwoot conversation ID - skipping Chatwoot sync")

            # UPDATE REDIS CACHE with latest conversation history
            # This ensures next message has immediate access to history
            await _update_conversation_cache(
                chat_id=final_state["conversation_id"],
                user_message=final_state["content"],
                assistant_message=conversation_output["response_text"],
                conversation_history=final_state.get("conversation_history", [])
            )
        elif source == "twilio":
            # Send directly via Twilio WhatsApp for Twilio-sourced messages
            await _send_to_twilio(
                phone_number=sender.get("phone_number", ""),
                message=conversation_output["response_text"]
            )

            # Optional: Sync to Chatwoot for unified view (future enhancement)
            # TODO: Implement Chatwoot sync for Twilio messages if needed

        elif source in ["chatwoot", None]:
            # Send via Chatwoot for Chatwoot messages (or fallback)
            await _send_to_chatwoot(
                conversation_id=final_state["conversation_id"],
                message=conversation_output["response_text"]
            )
        elif source == "360dialog":
            # TODO: Add 360Dialog direct sending if needed
            logger.warning("360Dialog direct response not implemented, using Chatwoot fallback")
            await _send_to_chatwoot(
                conversation_id=final_state["conversation_id"],
                message=conversation_output["response_text"]
            )

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

async def _send_to_waha(chat_id: str, message: str) -> None:
    """
    Send agent response directly to WhatsApp via WAHA API.

    DEDUPLICATION: Prevents duplicate sends within 30-second window using Redis cache.

    Args:
        chat_id: WhatsApp chat ID (e.g., "31612345678@c.us")
        message: Response message to send
    """
    waha_url = os.getenv("WAHA_BASE_URL", "http://waha:3000")
    waha_session = os.getenv("WAHA_SESSION", "default")
    waha_api_key = os.getenv("WAHA_API_KEY")

    # CRITICAL FIX: Ensure message is always a string, never a dict/object
    # If message is accidentally a dict (JSON object), extract text or stringify
    if isinstance(message, dict):
        logger.warning(
            "⚠️ WAHA message is dict, extracting response_text",
            extra={"message_keys": list(message.keys())}
        )
        # Try to extract response_text if it's a ConversationOutput dict
        message = message.get("response_text", str(message))

    # Ensure message is string type
    message = str(message)

    # ============ ENTERPRISE DEDUPLICATION LOGIC ============
    # Generate hash of message content + recipient (EVP-recommended pattern)
    message_hash = hashlib.sha256(f"{chat_id}:{message}".encode()).hexdigest()[:16]
    cache_key = f"waha:send:dedupe:{chat_id}:{message_hash}"

    # Check if this exact message was sent recently (last 30 seconds)
    if redis_client.get(cache_key):
        logger.info(
            "🚫 Duplicate WAHA send prevented (message already sent)",
            extra={
                "chat_id": chat_id,
                "message_hash": message_hash,
                "cache_key": cache_key,
                "reason": "duplicate_prevented_by_cache"
            }
        )
        return  # Skip sending - duplicate detected

    # Mark as sending (prevents concurrent duplicate sends from multiple workers)
    redis_client.setex(cache_key, timedelta(seconds=30), "sending")
    logger.debug(
        "📝 WAHA send marked in progress",
        extra={"cache_key": cache_key, "chat_id": chat_id}
    )
    # =========================================================

    url = f"{waha_url}/api/sendText"

    payload = {
        "session": waha_session,
        "chatId": chat_id,
        "text": message
    }

    headers = {
        "X-Api-Key": waha_api_key,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()

        # Update cache to "sent" status (successful send)
        redis_client.setex(cache_key, timedelta(seconds=30), "sent")

        logger.info(
            "✅ Message sent to WAHA",
            extra={
                "chat_id": chat_id,
                "message_length": len(message),
                "cache_key": cache_key
            }
        )

    except httpx.HTTPError as e:
        # On error, remove cache to allow retry
        redis_client.delete(cache_key)

        logger.error(
            f"❌ Failed to send message via WAHA: {e}",
            extra={"chat_id": chat_id, "error": str(e)},
            exc_info=True
        )
        raise

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

async def _sync_waha_to_chatwoot(
    chatwoot_conversation_id: int,
    phone_number: str,
    sender_name: str,
    incoming_message: str,
    outgoing_message: str
) -> None:
    """
    Sync WAHA messages to Chatwoot for chat history visibility.

    CRITICAL FIX: Now accepts chatwoot_conversation_id directly instead of creating it.
    This prevents 404 errors when trying to send to non-existent conversations.

    Args:
        chatwoot_conversation_id: Existing Chatwoot conversation ID (integer)
        phone_number: WhatsApp chat ID (e.g., "31612345678@c.us")
        sender_name: Sender's display name from WAHA
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
            "✅ Messages synced to Chatwoot",
            extra={
                "phone_number": phone_number,
                "chatwoot_conversation_id": chatwoot_conversation_id
            }
        )

    except Exception as e:
        logger.error(
            f"⚠️ Chatwoot sync failed (non-critical): {e}",
            extra={
                "phone_number": phone_number,
                "chatwoot_conversation_id": chatwoot_conversation_id
            },
            exc_info=True
        )
        # Don't raise - sync failure shouldn't break WAHA message flow

async def _update_conversation_cache(
    chat_id: str,
    user_message: str,
    assistant_message: str,
    conversation_history: list
) -> None:
    """
    Update Redis cache with latest conversation history.

    This ensures next message has immediate access to updated history,
    avoiding the timing issue where history is fetched before sync completes.

    Args:
        chat_id: WhatsApp chat ID (e.g., "31612345678@c.us")
        user_message: User's incoming message just processed
        assistant_message: AI's response just sent
        conversation_history: Previous conversation history from state
    """
    try:
        import json
        from datetime import datetime

        cache_key = f"conversation:{chat_id}:history"

        # Build updated history: previous + current exchange
        updated_history = list(conversation_history)  # Copy existing history

        # Add current user message
        updated_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # Add current assistant response
        updated_history.append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 10 messages (5 exchanges) to prevent cache bloat
        updated_history = updated_history[-10:]

        # Store in Redis with 1 hour TTL
        redis_client.setex(
            cache_key,
            timedelta(hours=1),
            json.dumps(updated_history)
        )

        logger.info(
            "✅ Updated conversation history cache",
            extra={
                "cache_key": cache_key,
                "history_count": len(updated_history),
                "chat_id": chat_id
            }
        )

    except Exception as e:
        logger.error(
            f"⚠️ Failed to update conversation cache (non-critical): {e}",
            extra={"chat_id": chat_id},
            exc_info=True
        )
        # Don't raise - cache failure shouldn't break message flow

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
