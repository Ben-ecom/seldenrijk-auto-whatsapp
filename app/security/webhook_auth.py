"""
Webhook authentication and security for Chatwoot, 360Dialog, WAHA, and Twilio webhooks.
Implements HMAC signature verification (SHA256 and SHA512) and rate limiting.
"""
import hmac
import hashlib
import os
import base64
from typing import Optional, Dict
from fastapi import HTTPException, Header, Request
from functools import wraps
import time
from collections import defaultdict
import threading
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

# Rate limiting storage (in-memory, for production use Redis)
rate_limit_store = defaultdict(list)
rate_limit_lock = threading.Lock()


# ============================================
# TWILIO WEBHOOK SIGNATURE VERIFICATION
# ============================================

def verify_twilio_signature(
    auth_token: str,
    url: str,
    params: Dict[str, str],
    signature: str
) -> bool:
    """
    Verify Twilio webhook signature using HMAC-SHA256.

    Twilio signs all webhook requests with your auth token. This function
    verifies the signature to ensure the request genuinely came from Twilio.

    Args:
        auth_token: Your Twilio auth token (from environment variable)
        url: Full webhook URL (e.g., "https://example.com/webhooks/twilio/whatsapp")
        params: Dictionary of all POST parameters from the webhook request
        signature: Value from X-Twilio-Signature header

    Returns:
        True if signature is valid, False otherwise

    Security Notes:
        - Uses constant-time comparison to prevent timing attacks
        - All parameters must be included (even empty ones)
        - URL must match exactly (including protocol, host, path, query string)

    Reference:
        https://www.twilio.com/docs/usage/security#validating-requests

    Example:
        >>> auth_token = "your_auth_token"
        >>> url = "https://example.com/webhook"
        >>> params = {"From": "whatsapp:+31612345678", "Body": "Hello"}
        >>> signature = "abcd1234..."
        >>> verify_twilio_signature(auth_token, url, params, signature)
        True
    """
    try:
        # Step 1: Sort parameters alphabetically by key
        sorted_params = sorted(params.items())

        # Step 2: Concatenate URL and all parameters (key+value pairs)
        # Example: "https://example.comFrom+31612345678BodyHello"
        data = url + ''.join([f'{k}{v}' for k, v in sorted_params])

        # Step 3: Compute HMAC-SHA256 hash
        computed_hash = hmac.new(
            auth_token.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Step 4: Base64 encode the hash
        computed_signature = base64.b64encode(computed_hash).decode('utf-8')

        # Step 5: Compare signatures using constant-time comparison
        # This prevents timing attacks where attackers measure response time
        is_valid = hmac.compare_digest(computed_signature, signature)

        if not is_valid:
            logger.warning(
                "Twilio signature verification failed",
                extra={
                    "url": url,
                    "expected_signature": signature[:20] + "...",
                    "computed_signature": computed_signature[:20] + "..."
                }
            )

        return is_valid

    except Exception as e:
        logger.error(f"Twilio signature verification error: {e}", exc_info=True)
        return False


async def validate_twilio_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature")
) -> Dict[str, str]:
    """
    FastAPI dependency for validating Twilio webhook requests.

    This function can be used as a FastAPI dependency to automatically
    validate all incoming Twilio webhook requests.

    Args:
        request: FastAPI Request object
        x_twilio_signature: Value from X-Twilio-Signature header

    Returns:
        Dictionary of parsed form parameters if signature is valid

    Raises:
        HTTPException: 403 if signature is invalid or missing

    Usage in FastAPI endpoint:
        @router.post("/webhooks/twilio/whatsapp")
        async def webhook(params: dict = Depends(validate_twilio_webhook)):
            # params is guaranteed to be from valid Twilio request
            pass
    """
    # Get auth token from environment
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN not set in environment")
        raise HTTPException(
            status_code=500,
            detail="Twilio authentication not configured"
        )

    # Check signature header exists
    if not x_twilio_signature:
        logger.warning("Missing X-Twilio-Signature header")
        raise HTTPException(
            status_code=403,
            detail="Missing signature header"
        )

    # Get full URL (including query string if present)
    url = str(request.url)

    # Parse form data
    form_data = await request.form()
    params = dict(form_data)

    # Verify signature
    if not verify_twilio_signature(auth_token, url, params, x_twilio_signature):
        logger.error(
            "Invalid Twilio signature",
            extra={
                "url": url,
                "remote_addr": request.client.host if request.client else "unknown"
            }
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    logger.info(
        "Twilio webhook verified successfully",
        extra={
            "message_sid": params.get("MessageSid"),
            "from": params.get("From")
        }
    )

    return params


# ============================================
# CHATWOOT WEBHOOK SIGNATURE VERIFICATION
# ============================================

def verify_chatwoot_signature(
    payload: bytes,
    signature: Optional[str] = Header(None, alias="X-Chatwoot-Signature")
) -> bool:
    """
    Verify HMAC-SHA256 signature from Chatwoot webhook.

    Args:
        payload: Raw request body as bytes
        signature: Signature from X-Chatwoot-Signature header

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is missing or invalid
    """
    webhook_secret = os.getenv("CHATWOOT_WEBHOOK_SECRET")

    # Development bypass: Allow testing without signature in development mode
    if os.getenv("ENVIRONMENT") == "development" and not signature:
        logger.warning("⚠️ CHATWOOT_WEBHOOK_SECRET bypass (development mode)")
        return True

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="CHATWOOT_WEBHOOK_SECRET not configured"
        )

    if not signature:
        logger.error("❌ Missing X-Chatwoot-Signature header")
        raise HTTPException(
            status_code=403,
            detail="Missing X-Chatwoot-Signature header"
        )

    # Generate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(signature, expected_signature):
        logger.error("❌ Invalid Chatwoot webhook signature")
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    logger.debug("✅ Chatwoot webhook signature verified")
    return True

def verify_waha_signature(
    payload: bytes,
    signature: Optional[str] = Header(None, alias="X-Webhook-Hmac"),
    algorithm: Optional[str] = Header(None, alias="X-Webhook-Hmac-Algorithm")
) -> bool:
    """
    Verify HMAC signature from WAHA webhook.

    WAHA uses HMAC-SHA512 by default (can be configured).

    Headers:
        X-Webhook-Hmac: HMAC signature (hex format)
        X-Webhook-Hmac-Algorithm: "sha512" or "sha256"

    Args:
        payload: Raw request body as bytes
        signature: HMAC signature from X-Webhook-Hmac header
        algorithm: Algorithm used (sha512 or sha256)

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is invalid or missing
    """
    webhook_secret = os.getenv("WAHA_WEBHOOK_SECRET")

    # Development bypass: Allow testing without signature if secret not configured
    if os.getenv("ENVIRONMENT") == "development" and not webhook_secret:
        logger.warning("⚠️ WAHA_WEBHOOK_SECRET not set - skipping verification (development mode)")
        return True

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="WAHA_WEBHOOK_SECRET not configured"
        )

    # Require signature header
    if not signature:
        logger.error("❌ Missing X-Webhook-Hmac header")
        raise HTTPException(
            status_code=403,
            detail="Missing X-Webhook-Hmac header"
        )

    # Determine hash algorithm (default: sha512)
    hash_algorithm = hashlib.sha512
    if algorithm and algorithm.lower() == "sha256":
        hash_algorithm = hashlib.sha256

    # Calculate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hash_algorithm
    ).hexdigest()

    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        logger.error(f"❌ Invalid WAHA webhook signature (algorithm: {algorithm or 'sha512'})")
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    logger.debug(f"✅ WAHA webhook signature verified (algorithm: {algorithm or 'sha512'})")
    return True

def verify_360dialog_signature(
    payload: bytes,
    signature: Optional[str] = Header(None, alias="X-Hub-Signature-256")
) -> bool:
    """
    Verify HMAC-SHA256 signature from 360Dialog webhook.

    Args:
        payload: Raw request body as bytes
        signature: Signature from X-Hub-Signature-256 header (format: sha256=<hex>)

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is missing or invalid
    """
    webhook_secret = os.getenv("DIALOG360_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="DIALOG360_WEBHOOK_SECRET not configured"
        )

    if not signature:
        logger.error("❌ Missing X-Hub-Signature-256 header")
        raise HTTPException(
            status_code=403,
            detail="Missing X-Hub-Signature-256 header"
        )

    # Parse signature (format: "sha256=<hex>")
    if not signature.startswith("sha256="):
        logger.error("❌ Invalid signature format (missing sha256= prefix)")
        raise HTTPException(
            status_code=403,
            detail="Invalid signature format"
        )

    received_signature = signature[7:]  # Remove "sha256=" prefix

    # Generate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(received_signature, expected_signature):
        logger.error("❌ Invalid 360Dialog webhook signature")
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    logger.debug("✅ 360Dialog webhook signature verified")
    return True

def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Rate limiting decorator for webhook endpoints.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds

    Raises:
        HTTPException: If rate limit is exceeded
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client IP
            client_ip = request.client.host
            current_time = time.time()

            with rate_limit_lock:
                # Clean old entries
                rate_limit_store[client_ip] = [
                    timestamp for timestamp in rate_limit_store[client_ip]
                    if current_time - timestamp < window_seconds
                ]

                # Check rate limit
                if len(rate_limit_store[client_ip]) >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds"
                    )

                # Add current request
                rate_limit_store[client_ip].append(current_time)

            return await func(request, *args, **kwargs)

        return wrapper
    return decorator

def verify_whatsapp_token(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None
) -> str:
    """
    Verify WhatsApp webhook setup token.
    Used for initial webhook verification by WhatsApp/360Dialog.

    Args:
        hub_mode: Should be "subscribe"
        hub_verify_token: Token to verify
        hub_challenge: Challenge string to return

    Returns:
        Challenge string if verification succeeds

    Raises:
        HTTPException: If verification fails
    """
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="WHATSAPP_VERIFY_TOKEN not configured"
        )

    if hub_mode != "subscribe":
        raise HTTPException(
            status_code=403,
            detail="Invalid hub.mode"
        )

    if hub_verify_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid verification token"
        )

    return hub_challenge
