"""
Chatwoot Contact/Conversation Synchronization.

This module handles synchronization between WAHA and Chatwoot:
- Get or create Chatwoot contacts from WhatsApp numbers
- Get or create Chatwoot conversations for contacts
- Sync messages from WAHA to Chatwoot for visibility
"""
import os
import redis
import httpx
from typing import Dict, Any, Optional, Tuple
from datetime import timedelta
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Redis client for deduplication
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.

    Returns:
        Redis client for caching and deduplication
    """
    return redis_client


class ChatwootSync:
    """Synchronization between WAHA and Chatwoot."""

    def __init__(self):
        """Initialize Chatwoot sync client."""
        self.base_url = os.getenv("CHATWOOT_BASE_URL", "http://localhost:3001")
        self.api_token = os.getenv("CHATWOOT_API_TOKEN", "")
        self.account_id = os.getenv("CHATWOOT_ACCOUNT_ID", "1")
        self.inbox_id = os.getenv("CHATWOOT_INBOX_ID", "1")

        self.headers = {
            "api_access_token": self.api_token,
            "Content-Type": "application/json"
        }

        logger.info(
            "ChatwootSync initialized",
            extra={
                "base_url": self.base_url,
                "account_id": self.account_id,
                "inbox_id": self.inbox_id
            }
        )

    async def get_or_create_contact(
        self,
        phone_number: str,
        name: str = "WhatsApp User"
    ) -> Optional[int]:
        """
        Get existing contact or create new one.

        Args:
            phone_number: Phone number (e.g., "31612345678" or "31612345678@c.us")
            name: Contact name (default: "WhatsApp User")

        Returns:
            Contact ID if successful, None otherwise
        """
        try:
            # Clean phone number (remove @c.us suffix if present)
            clean_phone = phone_number.replace("@c.us", "")

            # Format with + prefix
            if not clean_phone.startswith("+"):
                clean_phone = f"+{clean_phone}"

            # 1. Search for existing contact
            contact_id = await self._search_contact(clean_phone)

            if contact_id:
                logger.info(f"✅ Found existing contact: {contact_id}")
                return contact_id

            # 2. Create new contact
            contact_id = await self._create_contact(clean_phone, name)

            if contact_id:
                logger.info(f"✅ Created new contact: {contact_id}")
                return contact_id

            logger.error("❌ Failed to get or create contact")
            return None

        except Exception as e:
            logger.error(f"❌ Contact sync error: {e}", exc_info=True)
            return None

    async def _search_contact(self, phone_number: str) -> Optional[int]:
        """Search for existing contact by phone number."""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"
            params = {"q": phone_number}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    contacts = data.get("payload", [])

                    if contacts:
                        return contacts[0]["id"]

                return None

        except Exception as e:
            logger.warning(f"Contact search failed: {e}")
            return None

    async def _create_contact(
        self,
        phone_number: str,
        name: str
    ) -> Optional[int]:
        """Create new Chatwoot contact."""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"

            # Use phone number without + as identifier (for WAHA compatibility)
            identifier = phone_number.replace("+", "") + "@c.us"

            payload = {
                "name": name,
                "phone_number": phone_number,
                "identifier": identifier,
                "inbox_id": int(self.inbox_id)
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return data["id"]
                else:
                    logger.error(
                        f"Failed to create contact: {response.status_code}",
                        extra={"response": response.text}
                    )
                    return None

        except Exception as e:
            logger.error(f"Contact creation failed: {e}", exc_info=True)
            return None

    async def get_or_create_conversation(
        self,
        contact_id: int,
        source_id: str
    ) -> Optional[int]:
        """
        Get existing conversation or create new one.

        Args:
            contact_id: Chatwoot contact ID
            source_id: WhatsApp chat ID (e.g., "31612345678@c.us")

        Returns:
            Conversation ID if successful, None otherwise
        """
        try:
            # 1. Search for existing conversation
            conversation_id = await self._search_conversation(contact_id)

            if conversation_id:
                logger.info(f"✅ Found existing conversation: {conversation_id}")
                return conversation_id

            # 2. Create new conversation
            conversation_id = await self._create_conversation(contact_id, source_id)

            if conversation_id:
                logger.info(f"✅ Created new conversation: {conversation_id}")
                return conversation_id

            logger.error("❌ Failed to get or create conversation")
            return None

        except Exception as e:
            logger.error(f"❌ Conversation sync error: {e}", exc_info=True)
            return None

    async def _search_conversation(self, contact_id: int) -> Optional[int]:
        """Search for existing open conversation for contact."""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
            params = {
                "inbox_id": self.inbox_id,
                "status": "open"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    conversations = data.get("data", {}).get("payload", [])

                    # Find conversation for this contact
                    for conv in conversations:
                        sender = conv.get("meta", {}).get("sender", {})
                        if sender.get("id") == contact_id:
                            return conv["id"]

                return None

        except Exception as e:
            logger.warning(f"Conversation search failed: {e}")
            return None

    async def _create_conversation(
        self,
        contact_id: int,
        source_id: str
    ) -> Optional[int]:
        """Create new Chatwoot conversation."""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"

            payload = {
                "source_id": source_id,
                "inbox_id": int(self.inbox_id),
                "contact_id": contact_id,
                "status": "open"
            }

            logger.info(
                "🔍 Creating conversation",
                extra={
                    "url": url,
                    "payload": payload,
                    "contact_id": contact_id,
                    "source_id": source_id
                }
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return data["id"]
                else:
                    logger.error(
                        f"Failed to create conversation: {response.status_code}",
                        extra={"response": response.text}
                    )
                    return None

        except Exception as e:
            logger.error(f"Conversation creation failed: {e}", exc_info=True)
            return None

    async def sync_waha_to_chatwoot(
        self,
        phone_number: str,
        sender_name: str,
        message_content: str,
        message_type: str = "incoming"
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Complete WAHA to Chatwoot sync workflow.

        Args:
            phone_number: WhatsApp number (e.g., "31612345678@c.us")
            sender_name: Name from WAHA (from _data.notifyName)
            message_content: Message text
            message_type: "incoming" or "outgoing"

        Returns:
            Tuple of (contact_id, conversation_id) if successful
        """
        try:
            # 1. Get or create contact
            contact_id = await self.get_or_create_contact(
                phone_number=phone_number,
                name=sender_name
            )

            if not contact_id:
                logger.error("Failed to get/create contact")
                return None, None

            # 2. Get or create conversation
            conversation_id = await self.get_or_create_conversation(
                contact_id=contact_id,
                source_id=phone_number
            )

            if not conversation_id:
                logger.error("Failed to get/create conversation")
                return contact_id, None

            # 3. Send message to Chatwoot
            await self._send_message_to_chatwoot(
                conversation_id=conversation_id,
                content=message_content,
                message_type=message_type
            )

            logger.info(
                "✅ WAHA message synced to Chatwoot",
                extra={
                    "contact_id": contact_id,
                    "conversation_id": conversation_id,
                    "message_type": message_type
                }
            )

            return contact_id, conversation_id

        except Exception as e:
            logger.error(f"❌ WAHA sync failed: {e}", exc_info=True)
            return None, None

    async def _send_message_to_chatwoot(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "incoming"
    ) -> Optional[int]:
        """
        Send message to Chatwoot conversation.

        Returns:
            Chatwoot message ID if successful, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"

            payload = {
                "content": content,
                "message_type": message_type,
                "private": False
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    chatwoot_message_id = data.get("id")

                    logger.debug(
                        f"✅ Message sent to Chatwoot conversation {conversation_id}",
                        extra={"message_id": chatwoot_message_id}
                    )

                    # CRITICAL: Mark message as synced from WAHA to prevent duplicate processing
                    # When Chatwoot sends webhook for this message, we'll ignore it
                    if chatwoot_message_id:
                        cache_key = f"chatwoot:synced:{conversation_id}:{chatwoot_message_id}"
                        redis_client.setex(cache_key, timedelta(hours=1), "synced_from_waha")

                        logger.debug(
                            "📝 Message marked as synced from WAHA",
                            extra={
                                "cache_key": cache_key,
                                "message_id": chatwoot_message_id,
                                "conversation_id": conversation_id
                            }
                        )

                    return chatwoot_message_id
                else:
                    logger.error(
                        f"Failed to send message: {response.status_code}",
                        extra={"response": response.text}
                    )
                    return None

        except Exception as e:
            logger.error(f"Message send failed: {e}", exc_info=True)
            return None
