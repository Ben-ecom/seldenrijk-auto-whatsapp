"""
CRM Agent - Chatwoot contact and conversation management.

Uses Claude 3.5 Sonnet for:
- Creating/updating Chatwoot contacts
- Setting custom attributes (extracted data)
- Adding tags for segmentation
- Labeling conversations
- Tracking lead quality

Integrates with Chatwoot API to maintain synchronized CRM data.
"""
import os
import json
from typing import Dict, Any, List, Optional
import requests
from anthropic import Anthropic

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import ConversationState, CRMOutput
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


# ============ CHATWOOT API CONFIGURATION ============

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")

if not all([CHATWOOT_BASE_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
    logger.warning("⚠️ Chatwoot credentials not fully configured - CRM updates will be mocked")


# ============ CRM DECISION PROMPT ============

CRM_DECISION_PROMPT = """You are a CRM automation expert deciding what contact updates to make in Chatwoot.

Based on the conversation and extracted data, determine:

1. **Custom Attributes to Set** (key-value pairs):
   - job_preferences_titles: List of job titles
   - job_preferences_locations: List of locations
   - job_preferences_industries: List of industries
   - job_preferences_remote: Remote preference (remote/hybrid/onsite)
   - salary_min: Minimum salary expectation
   - salary_max: Maximum salary expectation
   - salary_currency: Currency code
   - skills: Comma-separated list of skills
   - years_experience: Years of experience
   - current_title: Current job title
   - availability: When they can start
   - lead_quality: hot/warm/cold (based on engagement and clarity)

2. **Tags to Add**:
   - Intent-based: job-seeker, salary-inquiry, application-status
   - Status: new-lead, active, nurturing, qualified
   - Urgency: urgent, normal, low-priority
   - Source: whatsapp-bot

3. **Conversation Labels**:
   - needs-follow-up: Requires human recruiter attention
   - waiting-response: Waiting for candidate reply
   - qualified-lead: High-quality candidate
   - complaint: Issue escalation needed

**Lead Quality Scoring:**
- **hot**: Specific requirements, ready to interview, high urgency
- **warm**: Clear preferences, actively looking, medium urgency
- **cold**: Vague requirements, just exploring, low urgency

**Output Format (JSON):**
{
    "custom_attributes": {
        "job_preferences_titles": ["Software Engineer", "Data Scientist"],
        "job_preferences_locations": ["Amsterdam", "Rotterdam"],
        "salary_min": 60000,
        "salary_max": 80000,
        "lead_quality": "warm"
    },
    "tags_to_add": ["job-seeker", "active", "normal", "whatsapp-bot"],
    "conversation_labels": ["qualified-lead", "needs-follow-up"],
    "internal_note": "Candidate looking for software engineering roles in Amsterdam. Has 5 years experience in Python/React. Salary expectation €60-80k. Ready to start in 1 month."
}

**Rules:**
- Only include attributes that have concrete values from extraction
- Don't add tags that don't apply
- Keep internal_note concise (2-3 sentences max)
- Be conservative with "qualified-lead" label (only for strong candidates)
"""


class CRMAgent(BaseAgent):
    """
    CRM Agent for Chatwoot contact and conversation management.

    Features:
    - Automatic contact creation/update
    - Custom attributes mapping
    - Intelligent tagging
    - Lead quality scoring
    - Internal notes generation
    """

    def __init__(self):
        """Initialize CRM Agent with Claude 3.5 Sonnet and Chatwoot API."""
        config = AGENT_CONFIGS["crm"]

        super().__init__(
            agent_name="crm",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Initialize Anthropic client for decision-making
        self.client = Anthropic(**config["config"])
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.enable_prompt_caching = config.get("enable_prompt_caching", False)

        # Chatwoot API headers
        self.chatwoot_headers = {
            "api_access_token": CHATWOOT_API_TOKEN,
            "Content-Type": "application/json"
        }

        logger.info(f"✅ CRM Agent initialized with Chatwoot integration (caching: {self.enable_prompt_caching})")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute CRM agent to update Chatwoot contact/conversation.

        Args:
            state: Current conversation state

        Returns:
            Dict with CRMOutput and metadata
        """
        logger.info(
            "📋 Updating CRM data",
            extra={
                "message_id": state["message_id"],
                "contact_id": state.get("contact_id"),
                "conversation_id": state["conversation_id"]
            }
        )

        # Step 1: Decide what CRM updates to make (using Claude)
        crm_decisions = self._decide_crm_updates(state)

        # Step 2: Execute Chatwoot API calls
        crm_output = self._execute_chatwoot_updates(state, crm_decisions)

        # Token usage (for decision-making LLM call)
        tokens_used = crm_decisions.get("tokens_used", {
            "input": 500,
            "output": 200,
            "total": 700,
            "cache_read": 0,
            "cache_write": 0
        })

        cost_usd = self._calculate_cost(
            input_tokens=tokens_used["input"],
            output_tokens=tokens_used["output"],
            cache_read_tokens=tokens_used.get("cache_read", 0),
            cache_write_tokens=tokens_used.get("cache_write", 0)
        )

        logger.info(
            "✅ CRM update complete",
            extra={
                "contact_updated": crm_output["contact_updated"],
                "attributes_set": len(crm_output["custom_attributes_updated"]),
                "tags_added": len(crm_output["tags_added"]),
                "cost_usd": cost_usd
            }
        )

        return {
            "output": crm_output,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }

    def _decide_crm_updates(self, state: ConversationState) -> Dict[str, Any]:
        """
        Use Claude 3.5 Sonnet to decide what CRM updates to make.

        Args:
            state: Current conversation state

        Returns:
            Dict with CRM decisions and token usage
        """
        # Build decision prompt
        user_message = self._build_crm_prompt(state)

        # Build system message with prompt caching
        system_messages = []
        if self.enable_prompt_caching:
            system_messages.append({
                "type": "text",
                "text": CRM_DECISION_PROMPT,
                "cache_control": {"type": "ephemeral"}
            })
        else:
            system_messages.append({
                "type": "text",
                "text": CRM_DECISION_PROMPT
            })

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            system=system_messages,
            messages=[
                {"role": "user", "content": user_message}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        # Parse response
        output_text = response.content[0].text

        # Extract JSON from response (Claude may wrap it in markdown or return plain text)
        try:
            if "```json" in output_text:
                output_text = output_text.split("```json")[1].split("```")[0].strip()
            elif "```" in output_text:
                output_text = output_text.split("```")[1].split("```")[0].strip()

            # Try to find JSON in the text if direct parsing fails
            if not output_text.strip().startswith("{"):
                # Look for { ... } in the text
                import re
                json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
                if json_match:
                    output_text = json_match.group(0)
                else:
                    # No JSON found - return minimal update
                    logger.warning(f"⚠️ No JSON found in CRM response, using minimal update")
                    decisions = {
                        "custom_attributes": {},
                        "tags_to_add": [],
                        "conversation_labels": [],
                        "internal_note": "CRM agent could not parse response"
                    }
                    return {**decisions, "tokens_used": {
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                        "total": response.usage.input_tokens + response.usage.output_tokens,
                        "cache_read": 0,
                        "cache_write": 0
                    }}

            decisions = json.loads(output_text)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse CRM decision JSON: {e}", extra={"response": output_text[:500]})
            # Return minimal valid response
            decisions = {
                "custom_attributes": {},
                "tags_to_add": [],
                "conversation_labels": [],
                "internal_note": "CRM parsing failed - check logs"
            }

        # Token usage (Claude format)
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
            "cache_write": getattr(response.usage, "cache_creation_input_tokens", 0)
        }

        return {
            **decisions,
            "tokens_used": tokens_used
        }

    def _build_crm_prompt(self, state: ConversationState) -> str:
        """
        Build CRM decision prompt with all context.

        Args:
            state: Current conversation state

        Returns:
            Formatted prompt for GPT-4o-mini
        """
        parts = []

        # Router classification
        router = state.get("router_output") or {}
        if router.get("intent"):
            parts.append(f"**Intent:** {router.get('intent')}")
            parts.append(f"**Priority:** {router.get('priority')}")
            parts.append("")

        # Extracted data
        extraction = state.get("extraction_output")
        if extraction:
            parts.append("**Extracted Data:**")
            parts.append(json.dumps(extraction, indent=2))
            parts.append("")

        # Conversation output
        conversation = state.get("conversation_output") or {}
        if conversation.get("sentiment"):
            parts.append(f"**Sentiment:** {conversation.get('sentiment')}")
            parts.append(f"**Conversation Complete:** {conversation.get('conversation_complete')}")
            parts.append("")

        # Current message
        parts.append("**User Message:**")
        parts.append(state["content"])
        parts.append("")

        parts.append("Based on this information, what CRM updates should be made?")
        parts.append("")
        parts.append("IMPORTANT: Respond with ONLY a valid JSON object. No explanations, no markdown formatting, just pure JSON starting with { and ending with }.")

        return "\n".join(parts)

    def _execute_chatwoot_updates(
        self,
        state: ConversationState,
        decisions: Dict[str, Any]
    ) -> CRMOutput:
        """
        Execute Chatwoot API calls based on CRM decisions.

        Args:
            state: Current conversation state
            decisions: CRM decisions from GPT-4o-mini

        Returns:
            CRMOutput with update results
        """
        contact_id = state.get("contact_id")
        conversation_id = state["conversation_id"]

        crm_output: CRMOutput = {
            "contact_id": contact_id,
            "contact_created": False,
            "contact_updated": False,
            "custom_attributes_updated": {},
            "tags_added": [],
            "conversation_labeled": False,
            "crm_error": None
        }

        try:
            # If no contact_id, create contact first
            if not contact_id:
                contact_id = self._create_contact(state)
                crm_output["contact_id"] = contact_id
                crm_output["contact_created"] = True

            # Update custom attributes
            if decisions.get("custom_attributes"):
                self._update_custom_attributes(
                    contact_id,
                    decisions["custom_attributes"]
                )
                crm_output["custom_attributes_updated"] = decisions["custom_attributes"]
                crm_output["contact_updated"] = True

            # Add tags
            if decisions.get("tags_to_add"):
                self._add_conversation_tags(
                    conversation_id,
                    decisions["tags_to_add"]
                )
                crm_output["tags_added"] = decisions["tags_to_add"]

            # Add conversation labels
            if decisions.get("conversation_labels"):
                self._add_conversation_labels(
                    conversation_id,
                    decisions["conversation_labels"]
                )
                crm_output["conversation_labeled"] = True

            # Add internal note
            if decisions.get("internal_note"):
                self._add_internal_note(
                    conversation_id,
                    decisions["internal_note"]
                )

        except Exception as e:
            logger.error(f"❌ CRM update failed: {e}", exc_info=True)
            crm_output["crm_error"] = str(e)

        return crm_output

    def _create_contact(self, state: ConversationState) -> str:
        """Create new Chatwoot contact."""
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts"

        payload = {
            "name": state["sender_name"],
            "phone_number": state["sender_phone"],
            "inbox_id": state["inbox_id"]
        }

        response = requests.post(url, headers=self.chatwoot_headers, json=payload)
        response.raise_for_status()

        contact_id = response.json()["payload"]["contact"]["id"]
        logger.info(f"✅ Created Chatwoot contact: {contact_id}")

        return str(contact_id)

    def _update_custom_attributes(
        self,
        contact_id: str,
        attributes: Dict[str, Any]
    ) -> None:
        """Update contact custom attributes."""
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts/{contact_id}"

        payload = {
            "custom_attributes": attributes
        }

        response = requests.put(url, headers=self.chatwoot_headers, json=payload)
        response.raise_for_status()

        logger.info(f"✅ Updated {len(attributes)} custom attributes for contact {contact_id}")

    def _add_conversation_tags(
        self,
        conversation_id: str,
        tags: List[str]
    ) -> None:
        """Add tags to conversation."""
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/labels"

        for tag in tags:
            payload = {"labels": [tag]}
            response = requests.post(url, headers=self.chatwoot_headers, json=payload)
            # Chatwoot returns 200 even if tag already exists
            logger.debug(f"Added tag '{tag}' to conversation {conversation_id}")

        logger.info(f"✅ Added {len(tags)} tags to conversation {conversation_id}")

    def _add_conversation_labels(
        self,
        conversation_id: str,
        labels: List[str]
    ) -> None:
        """Add labels to conversation (same as tags in Chatwoot)."""
        self._add_conversation_tags(conversation_id, labels)

    def _add_internal_note(
        self,
        conversation_id: str,
        note: str
    ) -> None:
        """Add private internal note to conversation."""
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"

        payload = {
            "content": note,
            "message_type": "outgoing",
            "private": True  # Internal note, not visible to user
        }

        response = requests.post(url, headers=self.chatwoot_headers, json=payload)
        response.raise_for_status()

        logger.info(f"✅ Added internal note to conversation {conversation_id}")
