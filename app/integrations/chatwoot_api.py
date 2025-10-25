"""
Chatwoot API Integration - Assign conversations, send messages, add labels.

This module provides a simple interface to interact with Chatwoot CRM.
"""
import os
import requests
from typing import Dict, Any, Optional
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class ChatwootAPI:
    """Chatwoot API client for conversation management."""

    def __init__(self):
        """Initialize Chatwoot API client."""
        self.base_url = os.getenv("CHATWOOT_BASE_URL", "https://chatwoot.yourdomain.com")
        self.api_key = os.getenv("CHATWOOT_API_TOKEN", "")
        self.account_id = os.getenv("CHATWOOT_ACCOUNT_ID", "1")

        self.headers = {
            "api_access_token": self.api_key,
            "Content-Type": "application/json"
        }

        logger.info(
            "✅ ChatwootAPI initialized",
            extra={
                "base_url": self.base_url,
                "account_id": self.account_id,
                "api_token_set": bool(self.api_key)
            }
        )

    def assign_conversation(self, conversation_id: str, assignee_id: int) -> bool:
        """
        Assign conversation to a team member.

        Args:
            conversation_id: Chatwoot conversation ID
            assignee_id: User ID to assign to

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/assignments"
            payload = {"assignee_id": assignee_id}

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code in [200, 201]:
                logger.info(f"✅ Assigned conversation {conversation_id} to user {assignee_id}")
                return True
            else:
                logger.error(f"❌ Failed to assign conversation: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Chatwoot assignment error: {e}")
            return False

    def send_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str = "outgoing",
        private: bool = False
    ) -> bool:
        """
        Send message in conversation.

        Args:
            conversation_id: Chatwoot conversation ID
            content: Message text
            message_type: "incoming" or "outgoing"
            private: True for internal notes

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
            payload = {
                "content": content,
                "message_type": message_type,
                "private": private
            }

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code in [200, 201]:
                logger.info(f"✅ Sent message to conversation {conversation_id}")
                return True
            else:
                logger.error(f"❌ Failed to send message: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Chatwoot send message error: {e}")
            return False

    def add_label(self, conversation_id: str, label: str) -> bool:
        """
        Add label to conversation.

        Args:
            conversation_id: Chatwoot conversation ID
            label: Label name to add

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/labels"
            payload = {"labels": [label]}

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code in [200, 201]:
                logger.debug(f"✅ Added label '{label}' to conversation {conversation_id}")
                return True
            elif response.status_code == 404:
                # Label doesn't exist in Chatwoot - run setup script first
                logger.error(
                    f"❌ Label '{label}' not found in Chatwoot. "
                    f"Run: docker exec -it seldenrijk-api python scripts/setup_chatwoot_labels.py"
                )
                return False
            else:
                logger.error(f"❌ Failed to add label '{label}': HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Chatwoot add label error for '{label}': {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation details.

        Args:
            conversation_id: Chatwoot conversation ID

        Returns:
            Conversation data or None if failed
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get conversation: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Chatwoot get conversation error: {e}")
            return None

    def create_contact(self, phone: str, name: str, inbox_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Create a new contact in Chatwoot.

        Args:
            phone: Phone number (format: +31612345678 or 31612345678)
            name: Contact name
            inbox_id: Inbox ID to associate contact with (optional)

        Returns:
            Contact data with contact["id"] or None if failed
        """
        try:
            # Ensure phone has + prefix
            if not phone.startswith("+"):
                phone = f"+{phone}"

            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"
            payload = {
                "name": name,
                "phone_number": phone
            }

            # Only add inbox_id if provided and valid
            if inbox_id is not None:
                payload["inbox_id"] = inbox_id

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code in [200, 201]:
                contact = response.json().get("payload", {}).get("contact", {})
                logger.info(f"✅ Created contact: {name} ({phone}) - ID: {contact.get('id')}")
                return contact
            else:
                logger.error(f"❌ Failed to create contact: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Chatwoot create contact error: {e}")
            return None

    def get_contact_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Search for existing contact by phone number.

        Args:
            phone: Phone number (format: +31612345678 or 31612345678)

        Returns:
            Contact data or None if not found
        """
        try:
            # Try with and without + prefix
            phone_variants = [phone]
            if phone.startswith("+"):
                phone_variants.append(phone[1:])  # Remove +
            else:
                phone_variants.append(f"+{phone}")  # Add +

            # Search for contact
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"

            for phone_variant in phone_variants:
                params = {"q": phone_variant}
                response = requests.get(url, params=params, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    payload = data.get("payload", [])

                    if payload and len(payload) > 0:
                        contact = payload[0]
                        logger.debug(f"✅ Found existing contact: {contact.get('name')} - ID: {contact.get('id')}")
                        return contact

            logger.debug(f"ℹ️  No existing contact found for phone: {phone}")
            return None

        except Exception as e:
            logger.error(f"❌ Chatwoot search contact error: {e}")
            return None

    def create_conversation(self, contact_id: int, inbox_id: int) -> Optional[Dict[str, Any]]:
        """
        Create a new conversation for a contact.

        Args:
            contact_id: Chatwoot contact ID
            inbox_id: Inbox ID (WhatsApp inbox)

        Returns:
            Conversation data with conversation["id"] or None if failed
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
            payload = {
                "source_id": f"{contact_id}-{inbox_id}",
                "inbox_id": inbox_id,
                "contact_id": contact_id
            }

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code in [200, 201]:
                conversation = response.json()
                logger.info(f"✅ Created conversation: ID {conversation.get('id')} for contact {contact_id}")
                return conversation
            else:
                logger.error(f"❌ Failed to create conversation: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Chatwoot create conversation error: {e}")
            return None

    def get_conversation_by_contact(self, contact_id: int, inbox_id: int) -> Optional[Dict[str, Any]]:
        """
        Get existing conversation for a contact.

        Args:
            contact_id: Chatwoot contact ID
            inbox_id: Inbox ID to filter by

        Returns:
            Conversation data or None if not found
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
            params = {"inbox_id": inbox_id}

            response = requests.get(url, params=params, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                conversations = data.get("data", {}).get("payload", [])

                # Filter by contact_id
                for conv in conversations:
                    meta = conv.get("meta", {})
                    if meta.get("sender", {}).get("id") == contact_id:
                        logger.debug(f"✅ Found existing conversation: ID {conv.get('id')} for contact {contact_id}")
                        return conv

            logger.debug(f"ℹ️  No existing conversation found for contact {contact_id} in inbox {inbox_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Chatwoot get conversation by contact error: {e}")
            return None

    def update_contact_attributes(self, contact_id: int, custom_attributes: Dict[str, Any]) -> bool:
        """
        Update custom attributes on a contact.

        Args:
            contact_id: Chatwoot contact ID
            custom_attributes: Dictionary of custom attributes

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/{contact_id}"
            payload = {"custom_attributes": custom_attributes}

            response = requests.put(url, json=payload, headers=self.headers, timeout=10)

            if response.status_code == 200:
                logger.debug(f"✅ Updated contact {contact_id} custom attributes")
                return True
            else:
                logger.warning(f"⚠️ Failed to update contact attributes: {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Chatwoot update contact attributes error: {e}")
            return False
