"""
Webhook endpoints for Chatwoot, 360Dialog, WAHA, and Twilio.
Includes P0 security fixes: signature verification and rate limiting.
"""
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from typing import Optional
from datetime import timedelta
from app.limiter import limiter
from app.security.webhook_auth import (
    verify_chatwoot_signature,
    verify_waha_signature,
    verify_360dialog_signature,
    verify_whatsapp_token,
    validate_twilio_webhook,
)
from app.tasks.process_message import process_message_async
from app.monitoring.logging_config import get_logger
from app.monitoring.metrics import webhook_requests_total, webhook_signature_errors_total
from app.database.redis_client import get_redis_client
import os
import hashlib

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Get centralized Redis client instance
redis_client = get_redis_client()

@router.get("/whatsapp/verify")
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None
):
    """
    WhatsApp webhook verification endpoint.
    Called by WhatsApp/360Dialog during webhook setup.

    Args:
        hub_mode: Should be "subscribe"
        hub_verify_token: Verification token
        hub_challenge: Challenge string to echo back

    Returns:
        str: Challenge string if verification succeeds
    """
    try:
        challenge = verify_whatsapp_token(hub_mode, hub_verify_token, hub_challenge)

        logger.info("WhatsApp webhook verified")

        return challenge

    except HTTPException:
        webhook_signature_errors_total.labels(source="whatsapp").inc()
        raise

@router.post("/chatwoot")
@limiter.limit("30/minute")
async def chatwoot_webhook(
    request: Request
):
    """
    Chatwoot webhook endpoint with P0 security fixes.

    Security:
    - HMAC-SHA256 signature verification
    - Rate limiting (30 req/min per IP)

    Args:
        request: FastAPI request

    Returns:
        dict: Acknowledgment response
    """

    try:
        # Get raw body for signature verification
        body_bytes = await request.body()

        logger.debug(f"Received body length: {len(body_bytes)}")
        logger.debug(f"Body content: {body_bytes[:500]}")  # Log first 500 bytes

        # Verify signature (with dev bypass)
        signature = request.headers.get("X-Chatwoot-Signature")
        verify_chatwoot_signature(body_bytes, signature)

        # Parse JSON from body bytes
        import json
        if not body_bytes:
            raise HTTPException(status_code=400, detail="Empty request body")
        payload = json.loads(body_bytes.decode('utf-8'))

        # Track webhook request
        webhook_requests_total.labels(source="chatwoot", status="received").inc()

        # Extract message event (may be None for direct API calls)
        event_type = payload.get("event")

        # Support both webhook formats:
        # 1. Webhook subscription: has "event" field
        # 2. Direct API message: NO "event" field
        if event_type and event_type != "message_created":
            logger.info("Ignoring non-message event", extra={"event": event_type})
            return {"status": "ignored", "event": event_type}

        # DEDUPLICATION CHECK (MUST BE BEFORE OUTGOING MESSAGE HANDLING!)
        # Check if this is a message we just synced from WAHA to prevent duplicate forwarding
        chatwoot_message_id = str(payload.get("id"))
        chatwoot_conversation_id = str(payload.get("conversation", {}).get("id"))
        cache_key = f"chatwoot:synced:{chatwoot_conversation_id}:{chatwoot_message_id}"

        if redis_client.get(cache_key):
            logger.info(
                "Ignoring Chatwoot message (already synced from WAHA)",
                extra={
                    "message_id": chatwoot_message_id,
                    "conversation_id": chatwoot_conversation_id,
                    "reason": "synced_from_waha"
                }
            )
            webhook_requests_total.labels(source="chatwoot", status="duplicate").inc()
            return {"status": "ignored", "reason": "synced_from_waha"}

        # Handle outgoing messages from human agents in Chatwoot
        # Check if this is an outgoing message (human agent or bot)
        message_type = payload.get("message_type")

        if message_type == "outgoing":
            # For messages WITHOUT sender field (direct API format),
            # we assume ALL outgoing messages are from human agents
            # Bot messages are caught by deduplication check above (synced cache key)
            logger.info(
                "✉️ Human agent outgoing message detected",
                extra={
                    "conversation_id": payload.get("conversation", {}).get("id"),
                    "content_preview": payload.get("content", "")[:50]
                }
            )

            # Forward human agent message to WhatsApp via Twilio
            await _forward_chatwoot_to_twilio(payload)
            logger.info("✅ Human agent message forwarded to Twilio")

            return {"status": "forwarded", "reason": "human_agent_message", "provider": "twilio"}

        # Queue message processing (async via Celery)
        task = process_message_async.delay(payload)

        logger.info(
            "Message queued for processing",
            extra={
                "conversation_id": payload.get("conversation", {}).get("id"),
                "task_id": task.id
            }
        )

        webhook_requests_total.labels(source="chatwoot", status="queued").inc()

        return {
            "status": "queued",
            "task_id": task.id,
            "conversation_id": payload.get("conversation", {}).get("id")
        }

    except Exception as e:
        logger.error("Webhook processing failed", extra={"error": str(e)}, exc_info=True)
        webhook_requests_total.labels(source="chatwoot", status="error").inc()

        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/360dialog")
@limiter.limit("20/minute")
async def dialog360_webhook(
    request: Request,
    signature_valid: bool = Depends(
        lambda request: verify_360dialog_signature(
            request.body(),
            request.headers.get("X-Hub-Signature-256")
        )
    )
):
    """
    360Dialog webhook endpoint with P0 security fixes.

    Security:
    - HMAC-SHA256 signature verification (X-Hub-Signature-256)
    - Rate limiting (20 req/min per IP)

    Args:
        request: FastAPI request
        signature_valid: Signature verification result

    Returns:
        dict: Acknowledgment response
    """

    try:
        payload = await request.json()

        # Track webhook request
        webhook_requests_total.labels(source="360dialog", status="received").inc()

        # 360Dialog webhook format differs from Chatwoot
        # Extract WhatsApp message data
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            logger.info("No messages in 360Dialog webhook")
            return {"status": "ignored", "reason": "no_messages"}

        # Process first message (usually only one)
        message = messages[0]

        # Transform to Chatwoot-compatible format
        transformed_payload = {
            "id": message.get("id"),
            "conversation": {
                "id": message.get("from")  # Use phone number as conversation ID
            },
            "sender": {
                "id": message.get("from")
            },
            "content": message.get("text", {}).get("body", ""),
            "message_type": "incoming",
            "channel": "whatsapp"
        }

        # Queue message processing
        task = process_message_async.delay(transformed_payload)

        logger.info(
            "360Dialog message queued",
            extra={"message_id": message.get("id"), "task_id": task.id}
        )

        webhook_requests_total.labels(source="360dialog", status="queued").inc()

        return {
            "status": "queued",
            "task_id": task.id,
            "message_id": message.get("id")
        }

    except Exception as e:
        logger.error("360Dialog webhook failed", extra={"error": str(e)}, exc_info=True)
        webhook_requests_total.labels(source="360dialog", status="error").inc()

        raise HTTPException(status_code=500, detail="Internal server error")


# ============ HELPER FUNCTIONS ============

async def _forward_chatwoot_to_twilio(payload: dict) -> None:
    """
    Forward human agent message from Chatwoot to WhatsApp via Twilio.

    Args:
        payload: Chatwoot webhook payload with outgoing message
    """
    try:
        from app.integrations.twilio_client import get_twilio_client

        # Extract conversation and message details
        conversation = payload.get("conversation", {})
        content = payload.get("content", "")

        # Get phone number from conversation
        conversation_id = str(conversation.get("id", ""))

        # Try to get phone number from conversation meta or contact_inbox
        phone_number = conversation.get("meta", {}).get("sender", {}).get("phone_number", "")

        if not phone_number:
            # Alternative: try contact_inbox source_id
            contact_inbox = conversation.get("contact_inbox", {})
            phone_number = contact_inbox.get("source_id", "")

        if not phone_number:
            logger.warning(
                "Cannot forward message: no phone number found",
                conversation_id=conversation_id
            )
            return

        # Get Twilio client
        twilio_client = get_twilio_client()

        # Send message (deduplication handled by client)
        result = await twilio_client.send_message(
            to_number=phone_number,
            message=content
        )

        if result["status"] == "sent":
            logger.info(
                "✅ Human agent message sent via Twilio",
                phone_number=phone_number,
                conversation_id=conversation_id,
                message_sid=result.get("message_sid")
            )
        elif result["status"] == "duplicate":
            logger.info(
                "🚫 Human agent message NOT forwarded (duplicate)",
                phone_number=phone_number,
                conversation_id=conversation_id
            )
        else:
            logger.error(
                "❌ Failed to forward message via Twilio",
                phone_number=phone_number,
                error=result.get("error")
            )

    except Exception as e:
        logger.error(
            "❌ Failed to forward message to Twilio",
            error=str(e),
            exc_info=True
        )


# ============ TWILIO WHATSAPP WEBHOOK ============

@router.post("/twilio/whatsapp")
@limiter.limit("50/minute")
async def twilio_whatsapp_webhook(
    request: Request,
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature")
):
    """
    Twilio WhatsApp webhook endpoint.

    Receives incoming WhatsApp messages from Twilio and processes them
    through the LangGraph agent workflow.

    Security:
        - Verifies Twilio signature (HMAC-SHA256)
        - Implements deduplication (Redis)
        - Rate limiting (50 messages/minute per IP)

    Flow:
        1. Validate signature
        2. Parse message data
        3. Check for duplicates
        4. Transform to Chatwoot-compatible format
        5. Queue for async processing via Celery

    Returns:
        200 OK with message status
        403 Forbidden if signature invalid
    """
    try:
        # Validate signature and parse form data
        params = await validate_twilio_webhook(request, x_twilio_signature)

        # Extract Twilio message data
        message_sid = params.get("MessageSid")
        from_number = params.get("From")  # Format: "whatsapp:+31612345678"
        to_number = params.get("To")  # Format: "whatsapp:+31850000000"
        body = params.get("Body", "")
        profile_name = params.get("ProfileName", "Unknown")
        num_media = int(params.get("NumMedia", "0"))

        logger.info(
            "Twilio webhook received",
            extra={
                "message_sid": message_sid,
                "from": from_number,
                "profile_name": profile_name,
                "body_length": len(body),
                "has_media": num_media > 0
            }
        )

        # Track webhook request
        webhook_requests_total.labels(source="twilio", status="received").inc()

        # Deduplication check (prevent processing same message twice)
        cache_key = f"twilio:message:{message_sid}"
        if redis_client.get(cache_key):
            logger.warning(
                "Duplicate message ignored",
                extra={"message_sid": message_sid}
            )
            webhook_requests_total.labels(source="twilio", status="duplicate").inc()
            return {
                "status": "ignored",
                "reason": "duplicate",
                "message_sid": message_sid
            }

        # Mark as processed (1 hour TTL)
        redis_client.setex(cache_key, timedelta(hours=1), "processed")

        # Clean phone number (remove "whatsapp:" prefix)
        phone_number = from_number.replace("whatsapp:", "") if from_number else "unknown"

        # Handle media messages (future enhancement)
        if num_media > 0:
            logger.info(
                f"Message contains {num_media} media attachment(s) - not yet supported",
                extra={"message_sid": message_sid}
            )
            # For now, acknowledge but don't process media
            # TODO: Implement media handling in future iteration

        # Transform to Chatwoot-compatible format for existing workflow
        transformed_payload = {
            "id": message_sid,
            "conversation": {
                "id": from_number  # Use Twilio From as conversation ID
            },
            "sender": {
                "id": from_number,
                "name": profile_name,
                "phone_number": phone_number
            },
            "content": body,
            "message_type": "incoming",
            "channel": "whatsapp",
            "source": "twilio"  # CRITICAL: Set source to "twilio" for response routing
        }

        logger.info(
            "Processing Twilio message through existing workflow",
            extra={
                "message_sid": message_sid,
                "conversation_id": from_number,
                "intent": "pending_classification"
            }
        )

        # Queue message processing (async via Celery)
        task = process_message_async.delay(transformed_payload)

        logger.info(
            "Twilio message queued",
            extra={"message_sid": message_sid, "task_id": task.id}
        )

        webhook_requests_total.labels(source="twilio", status="queued").inc()

        return {
            "status": "queued",
            "task_id": task.id,
            "message_sid": message_sid,
            "conversation_id": from_number
        }

    except HTTPException:
        # Re-raise HTTP exceptions (signature validation failures)
        webhook_signature_errors_total.labels(source="twilio").inc()
        raise

    except Exception as e:
        logger.error(
            f"Twilio webhook processing error: {e}",
            exc_info=True,
            extra={"message_sid": params.get("MessageSid") if 'params' in locals() else "unknown"}
        )

        webhook_requests_total.labels(source="twilio", status="error").inc()

        # Return 200 OK to prevent Twilio retries
        # (We log the error but don't want Twilio to keep retrying)
        return {
            "status": "error",
            "message": "Internal processing error",
            "error": str(e)
        }
