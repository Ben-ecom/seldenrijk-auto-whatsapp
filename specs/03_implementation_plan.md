# Phase 3: Implementation Plan
## WAHA → Twilio Migration - Step-by-Step Execution Guide

**Project:** Seldenrijk Auto WhatsApp Bot
**Phase:** 3 of 5 - Implementation Plan
**Date:** 26 Oktober 2025
**Status:** 🔄 IN PROGRESS (60% complete)

---

## Implementation Approach

**Strategy:** Incremental migration with feature flags and zero downtime

**Timeline:**
- Phase 3A (Core Twilio): 2 hours
- Phase 3B (HubSpot CRM): 1 hour
- Phase 3C (Google Calendar): 1 hour
- Phase 3D (WAHA Removal): 30 minutes
- **Total:** ~4.5 hours

**Risk Level:** MEDIUM (existing Twilio webhook code reduces risk significantly)

---

## STEP 1: Add Dependencies (15 minutes)

### 1.1 Update requirements.txt

**Current Status:** ✅ Twilio SDK already present (8.10.0)

**Action Required:** Add HubSpot and Google Calendar SDKs

```bash
# Add to requirements.txt after line 31 (after Twilio):

# ============ CRM & CALENDAR INTEGRATION ============
hubspot-api-client==9.2.0   # HubSpot CRM API
google-auth==2.36.0          # Google OAuth
google-auth-oauthlib==1.2.1  # OAuth flow helpers
google-auth-httplib2==0.2.0  # HTTP client for Google APIs
google-api-python-client==2.154.0  # Google Calendar API
```

**Installation:**
```bash
cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp
pip install hubspot-api-client==9.2.0 \
  google-auth==2.36.0 \
  google-auth-oauthlib==1.2.1 \
  google-auth-httplib2==0.2.0 \
  google-api-python-client==2.154.0
```

---

## STEP 2: Create Utility Functions (30 minutes)

### 2.1 Phone Number Format Converter

**File:** `app/utils/phone_formatter.py` (NEW)

```python
"""
Phone number format conversion utilities for WhatsApp providers.
Handles conversion between WAHA, Twilio, and E.164 formats.
"""
import re
from typing import Tuple


def format_phone_for_twilio(phone: str) -> str:
    """
    Convert any phone format to Twilio WhatsApp format.

    Examples:
        "31612345678@c.us" → "whatsapp:+31612345678"
        "+31612345678" → "whatsapp:+31612345678"
        "31612345678" → "whatsapp:+31612345678"

    Args:
        phone: Phone number in any format

    Returns:
        Phone number in Twilio WhatsApp format (whatsapp:+E164)

    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number cannot be empty")

    # Remove @c.us suffix (WAHA format)
    phone = phone.replace("@c.us", "")

    # Remove existing whatsapp: prefix
    phone = phone.replace("whatsapp:", "")

    # Remove spaces and hyphens
    phone = phone.replace(" ", "").replace("-", "")

    # Ensure + prefix
    if not phone.startswith("+"):
        phone = f"+{phone}"

    # Validate E.164 format
    if not re.match(r'^\+[1-9]\d{9,14}$', phone):
        raise ValueError(f"Invalid phone number format: {phone}")

    # Add whatsapp: prefix
    return f"whatsapp:{phone}"


def format_phone_from_twilio(twilio_phone: str) -> str:
    """
    Convert Twilio format to E.164 standard for database.

    Example:
        "whatsapp:+31612345678" → "+31612345678"

    Args:
        twilio_phone: Phone number in Twilio format

    Returns:
        Phone number in E.164 format (+31612345678)
    """
    return twilio_phone.replace("whatsapp:", "")


def format_phone_to_waha(phone: str) -> str:
    """
    Convert E.164 format to WAHA format.
    (Used during migration period only - will be removed)

    Example:
        "+31612345678" → "31612345678@c.us"

    Args:
        phone: Phone number in E.164 format

    Returns:
        Phone number in WAHA format
    """
    # Remove + prefix
    phone = phone.replace("+", "")

    # Add @c.us suffix
    return f"{phone}@c.us"


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number for WhatsApp.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, formatted_phone or error_message)

    Rules:
        - Must be E.164 format: +[country][number]
        - Length: 10-15 digits
        - Must start with +
        - No spaces or special chars (except + prefix)
    """
    try:
        formatted = format_phone_for_twilio(phone)
        return True, formatted
    except ValueError as e:
        return False, str(e)


def normalize_phone_to_e164(phone: str) -> str:
    """
    Normalize any phone format to E.164 for database storage.

    Examples:
        "whatsapp:+31612345678" → "+31612345678"
        "31612345678@c.us" → "+31612345678"
        "31612345678" → "+31612345678"

    Args:
        phone: Phone number in any format

    Returns:
        Phone number in E.164 format
    """
    # Remove provider prefixes
    phone = phone.replace("whatsapp:", "").replace("@c.us", "")

    # Remove spaces and hyphens
    phone = phone.replace(" ", "").replace("-", "")

    # Ensure + prefix
    if not phone.startswith("+"):
        phone = f"+{phone}"

    return phone
```

**Tests:** `tests/test_phone_formatter.py` (NEW)

```python
import pytest
from app.utils.phone_formatter import (
    format_phone_for_twilio,
    format_phone_from_twilio,
    validate_phone_number,
    normalize_phone_to_e164
)


def test_format_phone_for_twilio_waha():
    """Test WAHA format conversion"""
    assert format_phone_for_twilio("31612345678@c.us") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_e164():
    """Test E.164 format conversion"""
    assert format_phone_for_twilio("+31612345678") == "whatsapp:+31612345678"


def test_format_phone_for_twilio_no_plus():
    """Test number without + prefix"""
    assert format_phone_for_twilio("31612345678") == "whatsapp:+31612345678"


def test_format_phone_from_twilio():
    """Test Twilio to E.164 conversion"""
    assert format_phone_from_twilio("whatsapp:+31612345678") == "+31612345678"


def test_validate_phone_number_valid():
    """Test valid phone number"""
    is_valid, result = validate_phone_number("+31612345678")
    assert is_valid is True
    assert result == "whatsapp:+31612345678"


def test_validate_phone_number_invalid():
    """Test invalid phone number"""
    is_valid, result = validate_phone_number("invalid")
    assert is_valid is False
    assert "Invalid" in result


def test_normalize_phone_to_e164_twilio():
    """Test Twilio format normalization"""
    assert normalize_phone_to_e164("whatsapp:+31612345678") == "+31612345678"


def test_normalize_phone_to_e164_waha():
    """Test WAHA format normalization"""
    assert normalize_phone_to_e164("31612345678@c.us") == "+31612345678"
```

---

## STEP 3: Create Twilio Send Functions (45 minutes)

### 3.1 Twilio Client Module

**File:** `app/integrations/twilio_client.py` (NEW)

```python
"""
Twilio WhatsApp Business API client.
Handles sending messages, media, and templates via Twilio.
"""
import os
import hashlib
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import structlog

from app.utils.phone_formatter import format_phone_for_twilio, format_phone_from_twilio
from app.database.redis_client import get_redis_client


logger = structlog.get_logger(__name__)


class TwilioWhatsAppClient:
    """Twilio WhatsApp Business API client with deduplication and error handling."""

    def __init__(self):
        """Initialize Twilio client from environment variables."""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g., "whatsapp:+31612345678"

        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Missing required Twilio environment variables")

        self.client = Client(self.account_sid, self.auth_token)
        self.redis_client = get_redis_client()

    async def send_message(
        self,
        to_phone: str,
        message: str,
        media_url: Optional[str] = None
    ) -> dict:
        """
        Send WhatsApp message via Twilio.

        Args:
            to_phone: Recipient phone number (any format, will be normalized)
            message: Message text
            media_url: Optional media URL (for images, videos, etc.)

        Returns:
            dict with success status and message SID or error

        Raises:
            TwilioRestException: If sending fails after retries
        """
        # Normalize phone number
        try:
            to_phone_formatted = format_phone_for_twilio(to_phone)
        except ValueError as e:
            logger.error("invalid_phone_number", phone=to_phone, error=str(e))
            return {"success": False, "error": f"Invalid phone number: {e}"}

        # Deduplication check
        message_hash = hashlib.sha256(f"{to_phone}:{message}".encode()).hexdigest()[:16]
        cache_key = f"twilio:send:dedupe:{to_phone_formatted}:{message_hash}"

        if self.redis_client.get(cache_key):
            logger.warning("duplicate_message_send_prevented", phone=to_phone_formatted)
            return {"success": False, "error": "Duplicate message (already sent in last hour)"}

        # Send message
        try:
            params = {
                "from_": self.whatsapp_number,
                "to": to_phone_formatted,
                "body": message
            }

            if media_url:
                params["media_url"] = [media_url]

            twilio_message = self.client.messages.create(**params)

            # Cache for deduplication (1 hour TTL)
            self.redis_client.setex(cache_key, 3600, "1")

            logger.info(
                "message_sent",
                message_sid=twilio_message.sid,
                to=to_phone_formatted,
                status=twilio_message.status
            )

            return {
                "success": True,
                "message_sid": twilio_message.sid,
                "status": twilio_message.status,
                "to": to_phone_formatted
            }

        except TwilioRestException as e:
            logger.error(
                "twilio_send_failed",
                phone=to_phone_formatted,
                error_code=e.code,
                error_message=e.msg,
                status=e.status
            )

            # Handle specific error codes
            if e.code == 21211:  # Invalid phone number
                return {"success": False, "error": "Invalid phone number"}
            elif e.code == 63016:  # Opt-out
                return {"success": False, "error": "User has opted out"}
            elif e.code in [20429, 20003]:  # Rate limit
                return {"success": False, "error": "Rate limit exceeded", "retry_after": 60}
            else:
                # Generic error
                return {"success": False, "error": f"Twilio error: {e.msg}"}

    async def send_template(
        self,
        to_phone: str,
        template_sid: str,
        content_variables: dict
    ) -> dict:
        """
        Send WhatsApp template message (for opt-in, confirmations, etc.)

        Args:
            to_phone: Recipient phone number
            template_sid: Twilio Content Template SID
            content_variables: Template variables (e.g., {"1": "John", "2": "27-10-2025"})

        Returns:
            dict with success status and message SID or error
        """
        to_phone_formatted = format_phone_for_twilio(to_phone)

        try:
            twilio_message = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_phone_formatted,
                content_sid=template_sid,
                content_variables=content_variables
            )

            logger.info(
                "template_sent",
                message_sid=twilio_message.sid,
                template_sid=template_sid,
                to=to_phone_formatted
            )

            return {
                "success": True,
                "message_sid": twilio_message.sid,
                "status": twilio_message.status
            }

        except TwilioRestException as e:
            logger.error(
                "template_send_failed",
                template_sid=template_sid,
                error=str(e)
            )
            return {"success": False, "error": str(e)}


# Singleton instance
_twilio_client: Optional[TwilioWhatsAppClient] = None


def get_twilio_client() -> TwilioWhatsAppClient:
    """Get or create Twilio client singleton."""
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = TwilioWhatsAppClient()
    return _twilio_client
```

### 3.2 Update Message Processing Task

**File:** `app/tasks/process_message.py` (MODIFY)

Find the existing `_send_to_waha()` function and ADD new Twilio function:

```python
# NEW IMPORTS (add to top of file)
from app.integrations.twilio_client import get_twilio_client
from app.utils.phone_formatter import normalize_phone_to_e164

# ... existing code ...

# NEW FUNCTION (add after _send_to_waha)
async def _send_to_twilio(phone: str, message: str) -> None:
    """
    Send message to WhatsApp via Twilio API.

    Args:
        phone: Phone number in any format (+31612345678 or 31612345678@c.us)
        message: Text message to send
    """
    try:
        # Get Twilio client
        twilio_client = get_twilio_client()

        # Normalize phone to E.164
        phone_normalized = normalize_phone_to_e164(phone)

        # Send message
        result = await twilio_client.send_message(
            to_phone=phone_normalized,
            message=message
        )

        if not result["success"]:
            logger.error(
                "twilio_send_failed_in_task",
                phone=phone_normalized,
                error=result.get("error")
            )
            # Don't raise - log and continue (prevents Celery retry loops)

    except Exception as e:
        logger.error(
            "twilio_send_exception",
            phone=phone,
            error=str(e),
            exc_info=True
        )
        # Don't raise - prevents Celery task failure
```

**MODIFY routing logic** (find existing source-based routing):

```python
# FIND THIS CODE (around line 150-200):
source = payload.get("source")  # "chatwoot", "waha", "twilio", or "360dialog"

if source == "waha":
    await _send_to_waha(chat_id, response_text)
    await _sync_waha_to_chatwoot(conversation_id, message_id, response_text)

# REPLACE WITH:
source = payload.get("source")

# Feature flag: WHATSAPP_PROVIDER env var (default: "twilio")
provider = os.getenv("WHATSAPP_PROVIDER", "twilio")

if provider == "twilio":
    # NEW: Use Twilio for all responses
    await _send_to_twilio(contact_phone, response_text)
    await _sync_twilio_to_chatwoot(conversation_id, message_id, response_text)
elif provider == "waha" and source == "waha":
    # LEGACY: Keep WAHA support during migration (will be removed)
    await _send_to_waha(chat_id, response_text)
    await _sync_waha_to_chatwoot(conversation_id, message_id, response_text)
else:
    logger.error("unsupported_provider", provider=provider, source=source)
```

---

## STEP 4: Update Chatwoot Integration (30 minutes)

### 4.1 Modify Chatwoot Webhook Handler

**File:** `app/api/webhooks.py` (MODIFY)

Find `_forward_chatwoot_to_waha()` function (around line 383-493) and ADD new Twilio version:

```python
# NEW FUNCTION (add after _forward_chatwoot_to_waha)
async def _forward_chatwoot_to_twilio(payload: dict) -> None:
    """
    Forward human agent message from Chatwoot to WhatsApp via Twilio.

    Args:
        payload: Chatwoot webhook payload with message_created event
    """
    try:
        # Extract data
        conversation_id = payload.get("conversation", {}).get("id")
        message_id = payload.get("id")
        content = payload.get("content")

        if not content or not conversation_id:
            logger.warning("chatwoot_to_twilio_missing_data", payload=payload)
            return

        # Get contact phone from conversation
        contact = payload.get("conversation", {}).get("meta", {}).get("sender", {})
        phone = contact.get("phone_number") or contact.get("identifier")

        if not phone:
            logger.error("chatwoot_to_twilio_no_phone", conversation_id=conversation_id)
            return

        # Deduplication check
        message_hash = hashlib.sha256(f"{conversation_id}:{message_id}:{content}".encode()).hexdigest()[:16]
        cache_key = f"chatwoot:twilio:dedupe:{conversation_id}:{message_hash}"

        if redis_client.get(cache_key):
            logger.warning("chatwoot_to_twilio_duplicate_prevented", message_id=message_id)
            return

        # Send via Twilio
        twilio_client = get_twilio_client()
        result = await twilio_client.send_message(
            to_phone=phone,
            message=content
        )

        if result["success"]:
            # Cache for deduplication (1 hour TTL)
            redis_client.setex(cache_key, 3600, "1")
            logger.info(
                "chatwoot_to_twilio_sent",
                conversation_id=conversation_id,
                message_sid=result["message_sid"]
            )
        else:
            logger.error(
                "chatwoot_to_twilio_failed",
                conversation_id=conversation_id,
                error=result.get("error")
            )

    except Exception as e:
        logger.error(
            "chatwoot_to_twilio_exception",
            error=str(e),
            exc_info=True
        )
```

**MODIFY Chatwoot webhook endpoint** to route based on provider:

```python
# FIND the @router.post("/chatwoot") endpoint

@router.post("/chatwoot")
@limiter.limit("20/minute")
async def chatwoot_webhook(request: Request):
    """Chatwoot webhook endpoint for bot-to-human handoff."""
    payload = await request.json()
    event = payload.get("event")

    # Only process outgoing messages from human agents
    if event == "message_created" and payload.get("message_type") == "outgoing":
        # Feature flag: WHATSAPP_PROVIDER env var
        provider = os.getenv("WHATSAPP_PROVIDER", "twilio")

        if provider == "twilio":
            # NEW: Use Twilio
            asyncio.create_task(_forward_chatwoot_to_twilio(payload))
        elif provider == "waha":
            # LEGACY: Keep WAHA during migration
            asyncio.create_task(_forward_chatwoot_to_waha(payload))
        else:
            logger.error("unsupported_provider_chatwoot", provider=provider)

    return {"status": "ok"}
```

### 4.2 Add Sync Function for Twilio

```python
# NEW FUNCTION (add after _sync_waha_to_chatwoot)
async def _sync_twilio_to_chatwoot(
    conversation_id: int,
    message_id: str,
    content: str
) -> None:
    """
    Sync bot response to Chatwoot after sending via Twilio.

    Args:
        conversation_id: Chatwoot conversation ID
        message_id: Twilio message SID
        content: Message content
    """
    try:
        chatwoot_url = os.getenv("CHATWOOT_BASE_URL", "https://app.chatwoot.com")
        chatwoot_api_key = os.getenv("CHATWOOT_API_KEY")
        account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

        if not all([chatwoot_api_key, account_id]):
            logger.warning("chatwoot_sync_disabled_no_credentials")
            return

        # Create message in Chatwoot
        url = f"{chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
        headers = {
            "api_access_token": chatwoot_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "content": content,
            "message_type": "outgoing",
            "private": False,
            "source_id": message_id  # Twilio MessageSid
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info(
            "twilio_to_chatwoot_synced",
            conversation_id=conversation_id,
            message_id=message_id
        )

    except Exception as e:
        logger.error(
            "twilio_to_chatwoot_sync_failed",
            conversation_id=conversation_id,
            error=str(e),
            exc_info=True
        )
```

---

## STEP 5: Add HubSpot CRM Integration (1 hour)

### 5.1 HubSpot Client Module

**File:** `app/integrations/hubspot_client.py` (NEW)

```python
"""
HubSpot CRM API client.
Handles contact creation, deal management, and lead scoring sync.
"""
import os
from typing import Optional, Dict, Any
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, ApiException
from hubspot.crm.deals import SimplePublicObjectInputForCreate as DealInput
import structlog

logger = structlog.get_logger(__name__)


class HubSpotCRMClient:
    """HubSpot CRM client for contact and deal management."""

    def __init__(self):
        """Initialize HubSpot client from environment variables."""
        self.api_key = os.getenv("HUBSPOT_API_KEY")

        if not self.api_key:
            raise ValueError("Missing HUBSPOT_API_KEY environment variable")

        self.client = HubSpot(access_token=self.api_key)

    async def find_contact_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Search for existing contact by phone number.

        Args:
            phone: Phone number in E.164 format (+31612345678)

        Returns:
            Contact dict if found, None otherwise
        """
        try:
            # Search contacts by phone
            search_request = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "phone",
                                "operator": "EQ",
                                "value": phone
                            }
                        ]
                    }
                ]
            }

            search_results = self.client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )

            if search_results.results:
                contact = search_results.results[0]
                logger.info("hubspot_contact_found", contact_id=contact.id, phone=phone)
                return {
                    "id": contact.id,
                    "properties": contact.properties
                }

            return None

        except ApiException as e:
            logger.error("hubspot_search_failed", phone=phone, error=str(e))
            return None

    async def create_contact(
        self,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        lead_score: int = 0,
        lead_status: str = "COLD"
    ) -> Optional[str]:
        """
        Create new HubSpot contact.

        Args:
            phone: Phone number in E.164 format
            first_name: First name
            last_name: Last name
            lead_score: Lead score (0-125)
            lead_status: Lead quality (COLD, LUKEWARM, WARM, HOT)

        Returns:
            Contact ID if created successfully, None otherwise
        """
        try:
            properties = {
                "phone": phone,
                "lead_score": str(lead_score),
                "lead_status": lead_status,
                "hs_lead_status": lead_status.lower(),
                "lifecyclestage": "lead"
            }

            if first_name:
                properties["firstname"] = first_name
            if last_name:
                properties["lastname"] = last_name

            contact_input = SimplePublicObjectInputForCreate(properties=properties)
            created_contact = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=contact_input
            )

            logger.info(
                "hubspot_contact_created",
                contact_id=created_contact.id,
                phone=phone,
                lead_score=lead_score
            )

            return created_contact.id

        except ApiException as e:
            logger.error("hubspot_contact_create_failed", phone=phone, error=str(e))
            return None

    async def update_contact(
        self,
        contact_id: str,
        lead_score: Optional[int] = None,
        lead_status: Optional[str] = None,
        custom_properties: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Update existing HubSpot contact.

        Args:
            contact_id: HubSpot contact ID
            lead_score: Updated lead score
            lead_status: Updated lead status
            custom_properties: Additional custom properties to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            properties = {}

            if lead_score is not None:
                properties["lead_score"] = str(lead_score)
            if lead_status:
                properties["lead_status"] = lead_status
                properties["hs_lead_status"] = lead_status.lower()
            if custom_properties:
                properties.update(custom_properties)

            self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={"properties": properties}
            )

            logger.info(
                "hubspot_contact_updated",
                contact_id=contact_id,
                properties=properties
            )

            return True

        except ApiException as e:
            logger.error(
                "hubspot_contact_update_failed",
                contact_id=contact_id,
                error=str(e)
            )
            return False

    async def create_deal(
        self,
        contact_id: str,
        deal_name: str,
        deal_stage: str = "appointmentscheduled",
        amount: float = 0.0,
        close_date: Optional[str] = None,
        pipeline: str = "default"
    ) -> Optional[str]:
        """
        Create deal and associate with contact.

        Args:
            contact_id: HubSpot contact ID
            deal_name: Deal name (e.g., "Proefrit VW Golf")
            deal_stage: Pipeline stage
            amount: Deal amount (optional for test drives)
            close_date: Expected close date (YYYY-MM-DD)
            pipeline: Pipeline name (default: "default")

        Returns:
            Deal ID if created successfully, None otherwise
        """
        try:
            properties = {
                "dealname": deal_name,
                "dealstage": deal_stage,
                "amount": str(amount),
                "pipeline": pipeline
            }

            if close_date:
                properties["closedate"] = close_date

            deal_input = DealInput(properties=properties)
            created_deal = self.client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=deal_input
            )

            # Associate deal with contact
            self.client.crm.deals.associations_api.create(
                deal_id=created_deal.id,
                to_object_type="contacts",
                to_object_id=contact_id,
                association_type="deal_to_contact"
            )

            logger.info(
                "hubspot_deal_created",
                deal_id=created_deal.id,
                contact_id=contact_id,
                deal_name=deal_name
            )

            return created_deal.id

        except ApiException as e:
            logger.error(
                "hubspot_deal_create_failed",
                contact_id=contact_id,
                error=str(e)
            )
            return None


# Singleton instance
_hubspot_client: Optional[HubSpotCRMClient] = None


def get_hubspot_client() -> HubSpotCRMClient:
    """Get or create HubSpot client singleton."""
    global _hubspot_client
    if _hubspot_client is None:
        _hubspot_client = HubSpotCRMClient()
    return _hubspot_client
```

### 5.2 Integrate with CRM Agent

**File:** `app/agents/enhanced_crm_agent.py` (MODIFY)

Add HubSpot sync after lead scoring:

```python
# ADD IMPORT
from app.integrations.hubspot_client import get_hubspot_client

# FIND the LeadScoringEngine.score_message() method (around line 100-200)
# ADD THIS CODE after scoring calculation:

# ... existing scoring code ...

# Sync to HubSpot CRM
if os.getenv("HUBSPOT_ENABLED", "false").lower() == "true":
    try:
        hubspot_client = get_hubspot_client()
        contact_phone = context.get("contact_phone")
        contact_name = context.get("contact_name", "")

        # Split name
        parts = contact_name.split(" ", 1)
        first_name = parts[0] if parts else None
        last_name = parts[1] if len(parts) > 1 else None

        # Check if contact exists
        existing_contact = await hubspot_client.find_contact_by_phone(contact_phone)

        if existing_contact:
            # Update existing contact
            await hubspot_client.update_contact(
                contact_id=existing_contact["id"],
                lead_score=total_score,
                lead_status=quality_level
            )
        else:
            # Create new contact
            await hubspot_client.create_contact(
                phone=contact_phone,
                first_name=first_name,
                last_name=last_name,
                lead_score=total_score,
                lead_status=quality_level
            )

    except Exception as e:
        logger.error("hubspot_sync_failed", error=str(e))
        # Don't raise - continue with agent flow
```

---

## STEP 6: Add Google Calendar Integration (1 hour)

### 6.1 Google Calendar Client

**File:** `app/integrations/google_calendar_client.py` (NEW)

```python
"""
Google Calendar API client.
Handles appointment scheduling, availability checks, and reminders.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import structlog

logger = structlog.get_logger(__name__)


class GoogleCalendarClient:
    """Google Calendar client for appointment management."""

    def __init__(self):
        """Initialize Google Calendar client from service account credentials."""
        credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not credentials_path:
            raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            self.service = build('calendar', 'v3', credentials=credentials)
            self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

        except Exception as e:
            logger.error("google_calendar_init_failed", error=str(e))
            raise

    async def get_available_slots(
        self,
        days_ahead: int = 14,
        slot_duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots.

        Args:
            days_ahead: Number of days to check (default: 14)
            slot_duration_minutes: Slot duration (default: 60)

        Returns:
            List of available slots with start/end times

        Business Rules:
            - Working hours: 09:00-18:00
            - Working days: Monday-Saturday
            - Lunch break: 12:00-13:00
            - No Sundays
        """
        try:
            # Get existing events
            time_min = datetime.utcnow().isoformat() + 'Z'
            time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            existing_events = events_result.get('items', [])

            # Generate all possible slots
            available_slots = []
            current_date = datetime.now().date()

            for day_offset in range(days_ahead):
                check_date = current_date + timedelta(days=day_offset)

                # Skip Sundays
                if check_date.weekday() == 6:
                    continue

                # Generate slots for this day
                for hour in range(9, 18):  # 09:00-18:00
                    # Skip lunch break (12:00-13:00)
                    if hour == 12:
                        continue

                    slot_start = datetime.combine(check_date, datetime.min.time()).replace(hour=hour)
                    slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

                    # Check if slot conflicts with existing events
                    is_available = True
                    for event in existing_events:
                        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                        event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))

                        # Check for overlap
                        if not (slot_end <= event_start or slot_start >= event_end):
                            is_available = False
                            break

                    if is_available:
                        # Format label (e.g., "Morgen 10:00", "Dinsdag 14:00")
                        if day_offset == 0:
                            day_label = "Vandaag"
                        elif day_offset == 1:
                            day_label = "Morgen"
                        else:
                            days_nl = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
                            day_label = days_nl[check_date.weekday()]

                        available_slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "label": f"{day_label} {slot_start.strftime('%H:%M')}",
                            "date": check_date.isoformat()
                        })

            logger.info("calendar_slots_generated", count=len(available_slots))
            return available_slots

        except HttpError as e:
            logger.error("calendar_slots_fetch_failed", error=str(e))
            return []

    async def create_appointment(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        customer_phone: str,
        customer_email: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Create appointment in Google Calendar.

        Args:
            summary: Event title (e.g., "Proefrit: VW Golf - Jan de Vries")
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            customer_phone: Customer phone number
            customer_email: Customer email (optional)
            description: Event description

        Returns:
            Event ID if created successfully, None otherwise
        """
        try:
            event = {
                'summary': summary,
                'description': description or f"Contact: {customer_phone}",
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Europe/Amsterdam'
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Europe/Amsterdam'
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'sms', 'minutes': 60},  # 1 hour before
                        {'method': 'email', 'minutes': 1440}  # 1 day before
                    ]
                }
            }

            if customer_email:
                event['attendees'] = [{'email': customer_email}]

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            logger.info(
                "calendar_event_created",
                event_id=created_event['id'],
                summary=summary,
                start=start_time
            )

            return created_event['id']

        except HttpError as e:
            logger.error("calendar_event_create_failed", error=str(e))
            return None

    async def cancel_appointment(self, event_id: str) -> bool:
        """
        Cancel appointment.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            logger.info("calendar_event_cancelled", event_id=event_id)
            return True

        except HttpError as e:
            logger.error("calendar_event_cancel_failed", event_id=event_id, error=str(e))
            return False


# Singleton instance
_calendar_client: Optional[GoogleCalendarClient] = None


def get_calendar_client() -> GoogleCalendarClient:
    """Get or create Google Calendar client singleton."""
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = GoogleCalendarClient()
    return _calendar_client
```

### 6.2 Integrate with Conversation Agent

**File:** `app/agents/conversation_agent.py` (MODIFY)

Add calendar booking flow for test drive requests:

```python
# ADD IMPORTS
from app.integrations.google_calendar_client import get_calendar_client
from app.integrations.hubspot_client import get_hubspot_client

# FIND the handle_test_drive_request() method (or similar)
# ADD THIS FLOW:

async def handle_test_drive_booking(
    customer_phone: str,
    customer_name: str,
    car_model: str,
    contact_id: Optional[str] = None
) -> str:
    """
    Handle test drive booking with calendar integration.

    Args:
        customer_phone: Customer phone number
        customer_name: Customer name
        car_model: Car model requested
        contact_id: HubSpot contact ID (if exists)

    Returns:
        Response message for customer
    """
    try:
        # Get available slots
        calendar_client = get_calendar_client()
        slots = await calendar_client.get_available_slots(days_ahead=7)

        if not slots:
            return "Sorry, er zijn momenteel geen beschikbare tijdslots. Bel ons op +31 XX XXX XXXX."

        # Format slots for user (show first 3)
        slot_options = "\n".join([
            f"{i+1}️⃣ {slot['label']}"
            for i, slot in enumerate(slots[:3])
        ])

        # Store slots in context for next message
        # (This would need session/context management - simplified here)

        return f"""
🚗 **Proefrit plannen: {car_model}**

Wanneer past het jou?

{slot_options}

Reageer met het nummer van je keuze (bijv. "1").
        """.strip()

    except Exception as e:
        logger.error("test_drive_booking_failed", error=str(e))
        return "Sorry, er ging iets mis bij het plannen. Bel ons op +31 XX XXX XXXX."


async def confirm_test_drive_booking(
    slot_index: int,
    slots: List[Dict],
    customer_phone: str,
    customer_name: str,
    car_model: str,
    contact_id: Optional[str] = None
) -> str:
    """
    Confirm test drive booking after user selects slot.

    Args:
        slot_index: Selected slot index (0-based)
        slots: Available slots list
        customer_phone: Customer phone
        customer_name: Customer name
        car_model: Car model
        contact_id: HubSpot contact ID

    Returns:
        Confirmation message
    """
    try:
        selected_slot = slots[slot_index]

        # Create calendar event
        calendar_client = get_calendar_client()
        event_id = await calendar_client.create_appointment(
            summary=f"Proefrit: {car_model} - {customer_name}",
            start_time=selected_slot["start"],
            end_time=selected_slot["end"],
            customer_phone=customer_phone,
            description=f"Contact: {customer_phone}\nLead Score: [from CRM Agent]"
        )

        if not event_id:
            return "Sorry, er ging iets mis bij het bevestigen. Probeer opnieuw."

        # Create HubSpot deal
        if contact_id:
            hubspot_client = get_hubspot_client()
            await hubspot_client.create_deal(
                contact_id=contact_id,
                deal_name=f"Proefrit {car_model}",
                deal_stage="appointmentscheduled",
                amount=0.0,
                close_date=selected_slot["date"]
            )

        # Confirmation message
        return f"""
✅ **Proefrit bevestigd!**

📅 {selected_slot["label"]}
🚗 {car_model}
📍 Seldenrijk Auto, Hoofdstraat 123

Je ontvangt een bevestiging per email en WhatsApp 1 uur voor je afspraak.

Tot dan! 👋
        """.strip()

    except Exception as e:
        logger.error("test_drive_confirm_failed", error=str(e))
        return "Sorry, er ging iets mis. Bel ons op +31 XX XXX XXXX."
```

---

## STEP 7: Remove WAHA Dependencies (30 minutes)

### 7.1 Remove WAHA Webhook Endpoint

**File:** `app/api/webhooks.py` (MODIFY)

**DELETE these functions:**
- `@router.post("/waha")` endpoint (lines 176-296)
- `_send_to_waha()` function
- `_forward_chatwoot_to_waha()` function
- `_sync_waha_to_chatwoot()` function

**File:** `app/security/webhook_auth.py` (MODIFY)

**DELETE:**
- `verify_waha_signature()` function

**File:** `app/tasks/process_message.py` (MODIFY)

**DELETE:**
- `_send_to_waha()` function
- Remove WAHA routing logic

### 7.2 Remove WAHA Docker Container

**File:** `docker-compose.yml` (MODIFY)

**DELETE waha service:**
```yaml
# DELETE THIS ENTIRE BLOCK:
  waha:
    image: devlikeapro/waha:latest
    ports:
      - "3000:3000"
    environment:
      - WAHA_SESSION=default
      - WAHA_API_KEY=${WAHA_API_KEY}
    restart: unless-stopped
```

### 7.3 Update Environment Variables

**File:** `.env.example` (MODIFY)

**DELETE WAHA variables:**
```bash
# DELETE THESE:
WAHA_BASE_URL=http://waha:3000
WAHA_SESSION=default
WAHA_API_KEY=your_waha_api_key
WAHA_WEBHOOK_SECRET=your_webhook_secret
```

**ADD Twilio, HubSpot, Calendar variables:**
```bash
# ============ WHATSAPP (TWILIO) ============
WHATSAPP_PROVIDER=twilio  # Options: "twilio", "waha" (during migration only)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+31612345678

# ============ HUBSPOT CRM ============
HUBSPOT_ENABLED=true
HUBSPOT_API_KEY=your_hubspot_api_key

# ============ GOOGLE CALENDAR ============
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
GOOGLE_CALENDAR_ID=primary
```

### 7.4 Delete Simple Demo

**DELETE FILE:**
```bash
rm /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp/main.py
```

---

## STEP 8: Update Configuration Files (15 minutes)

### 8.1 Railway Environment Variables

**Action:** Update Railway dashboard with new environment variables

**Navigate to:** https://railway.app/dashboard → seldenrijk-auto-whatsapp → Variables

**ADD:**
```
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=[from RAILWAY-VARIABLES.txt]
TWILIO_AUTH_TOKEN=[from RAILWAY-VARIABLES.txt]
TWILIO_WHATSAPP_NUMBER=whatsapp:+31612345678
HUBSPOT_ENABLED=true
HUBSPOT_API_KEY=[get from HubSpot dashboard]
GOOGLE_SERVICE_ACCOUNT_JSON=/app/credentials/google-service-account.json
GOOGLE_CALENDAR_ID=primary
```

**REMOVE:**
```
WAHA_BASE_URL
WAHA_SESSION
WAHA_API_KEY
WAHA_WEBHOOK_SECRET
```

### 8.2 Update Railway Deployment

**File:** `railway.toml` (NO CHANGES NEEDED - already configured)

**Current configuration is correct:**
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**UPDATE startCommand to use app module:**
```toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

---

## STEP 9: Database Migration (10 minutes)

### 9.1 Update Conversation IDs

**Execute SQL in Supabase:**

```sql
-- Migrate WAHA conversation IDs to Twilio format
-- From: "waha:31612345678" → To: "twilio:+31612345678"

UPDATE contacts
SET custom_attributes = jsonb_set(
    custom_attributes,
    '{whatsapp_provider}',
    '"twilio"'
)
WHERE custom_attributes->>'whatsapp_provider' = 'waha';

UPDATE contacts
SET custom_attributes = jsonb_set(
    custom_attributes,
    '{whatsapp_id}',
    to_jsonb(CONCAT('whatsapp:+', REPLACE(REPLACE(custom_attributes->>'whatsapp_id', '@c.us', ''), 'waha:', '')))
)
WHERE custom_attributes->>'whatsapp_id' LIKE '%@c.us%';
```

### 9.2 Clear Redis Cache

```bash
# Connect to Redis
redis-cli

# Clear WAHA-related cache
SCAN 0 MATCH waha:* COUNT 1000
# For each key returned, run: DEL <key>

# Or clear all (if safe):
FLUSHDB
```

---

## STEP 10: Testing & Validation (30 minutes)

### 10.1 Unit Tests

```bash
# Run phone formatter tests
pytest tests/test_phone_formatter.py -v

# Run Twilio client tests (mock)
pytest tests/test_twilio_client.py -v

# Run full test suite
pytest tests/ -v --cov=app
```

### 10.2 Integration Tests

**Test 1: End-to-End Message Flow**
```bash
# Send test message to Twilio webhook
curl -X POST https://your-railway-url.up.railway.app/webhooks/twilio/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "MessageSid=SM_test_001" \
  -d "From=whatsapp:+31612345678" \
  -d "To=whatsapp:+31612345678" \
  -d "Body=Hallo, test message" \
  -d "ProfileName=Test User"

# Expected: Bot response received via WhatsApp
```

**Test 2: Chatwoot → Twilio**
```bash
# Post Chatwoot webhook event
curl -X POST https://your-railway-url.up.railway.app/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message_created",
    "message_type": "outgoing",
    "conversation": {"id": 123},
    "content": "Test from human agent"
  }'

# Expected: Message sent via Twilio to user
```

**Test 3: HubSpot Sync**
- Send message with car inquiry
- Check HubSpot for new contact
- Verify lead score is calculated
- Verify properties are synced

**Test 4: Calendar Booking**
- Request test drive
- Verify available slots shown
- Select slot
- Verify Google Calendar event created
- Verify HubSpot deal created

---

## STEP 11: Deployment (15 minutes)

### 11.1 Git Commit & Push

```bash
cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp

# Stage all changes
git add .

# Commit migration
git commit -m "✅ WAHA → Twilio Migration Complete

- ✅ Replaced WAHA with Twilio WhatsApp Business API
- ✅ Added HubSpot CRM integration
- ✅ Added Google Calendar booking
- ✅ Removed WAHA dependencies completely
- ✅ Updated environment variables
- ✅ Migrated database conversation IDs
- ✅ Cleared Redis WAHA cache
- ✅ All tests passing

Cost savings: €75/month (€900/year)
Capacity increase: 5x (10 → 50 msg/min)
SLA improvement: 95% → 99.95%"

# Push to Railway
git push origin main
```

### 11.2 Railway Auto-Deploy

Railway will automatically deploy after push. Monitor:

```bash
# Check deployment status
railway status

# View logs
railway logs

# Get Railway URL
railway open
```

### 11.3 Configure Twilio Webhook

**Option 1: Automated (use configure-twilio.sh script)**
```bash
./configure-twilio.sh https://your-railway-url.up.railway.app
```

**Option 2: Manual**
1. Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
2. "When a message comes in": `https://your-railway-url.up.railway.app/webhooks/twilio/whatsapp`
3. Method: POST
4. Save

---

## Implementation Checklist

### Phase 3A: Core Twilio (2 hours)
- [x] Add dependencies (HubSpot, Google Calendar)
- [ ] Create phone formatter utility (`app/utils/phone_formatter.py`)
- [ ] Create Twilio client (`app/integrations/twilio_client.py`)
- [ ] Update message processing task (`app/tasks/process_message.py`)
- [ ] Update Chatwoot webhook handler (`app/api/webhooks.py`)
- [ ] Write unit tests
- [ ] Test end-to-end message flow

### Phase 3B: HubSpot CRM (1 hour)
- [ ] Create HubSpot client (`app/integrations/hubspot_client.py`)
- [ ] Integrate with CRM agent (`app/agents/enhanced_crm_agent.py`)
- [ ] Test contact creation
- [ ] Test lead scoring sync
- [ ] Verify HubSpot dashboard shows contacts

### Phase 3C: Google Calendar (1 hour)
- [ ] Create Calendar client (`app/integrations/google_calendar_client.py`)
- [ ] Integrate with conversation agent (`app/agents/conversation_agent.py`)
- [ ] Test availability check
- [ ] Test appointment creation
- [ ] Verify calendar events created
- [ ] Test HubSpot deal creation on booking

### Phase 3D: WAHA Removal (30 minutes)
- [ ] Remove WAHA webhook endpoint
- [ ] Remove WAHA functions
- [ ] Remove WAHA Docker container
- [ ] Update environment variables
- [ ] Delete simple demo (`main.py`)
- [ ] Migrate database conversation IDs
- [ ] Clear Redis cache

### Phase 3E: Deployment (30 minutes)
- [ ] Update Railway environment variables
- [ ] Git commit & push
- [ ] Monitor Railway auto-deploy
- [ ] Configure Twilio webhook URL
- [ ] Run live WhatsApp tests
- [ ] Verify HubSpot sync works
- [ ] Verify Calendar booking works
- [ ] Monitor error logs

---

## Success Criteria

**Technical:**
- ✅ All tests passing (unit + integration)
- ✅ Zero message loss during migration
- ✅ <4s average response time
- ✅ 99.9% webhook success rate
- ✅ Twilio signature validation 100% pass rate

**Business:**
- ✅ €75/month cost savings verified
- ✅ 50 messages/minute capacity tested
- ✅ HubSpot contacts created automatically
- ✅ Google Calendar appointments working
- ✅ Lead scoring synced to HubSpot

**Functional:**
- ✅ WhatsApp messages received via Twilio
- ✅ Bot responses sent via Twilio
- ✅ Chatwoot human handoff works
- ✅ Test drive booking flow complete
- ✅ Email/SMS reminders sent

---

**Phase 3 Status:** ✅ COMPLETE (60% total planning)

**Next Phase:** Phase 4 - Testing Strategy
