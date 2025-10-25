"""
Enhanced CRM Agent - Advanced lead scoring and intelligent tagging for car dealership.

Features:
- Lead scoring algorithm (0-100 points)
- 20+ intelligent tags for car sales
- Integration with ExpertiseAgent escalation data
- Behavioral tracking (test drive requests, trade-in, financing)
- Customer journey stage tracking
- Sentiment analysis integration
"""
import os
import json
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import ConversationState
from app.monitoring.logging_config import get_logger
from app.integrations.chatwoot_api import ChatwootAPI

# Import centralized tag registry
from config.tag_registry import get_label_title, LEAD_QUALITY_MAP, BEHAVIOR_MAP, JOURNEY_MAP

logger = get_logger(__name__)


class LeadScoringEngine:
    """
    Lead scoring algorithm for automotive sales.

    Scores customers 0-125+ based on:
    - Car inquiry specificity (30 points max)
    - Budget mentioned (20 points max)
    - Urgency signals (20 points max)
    - Test drive requests (20 points max - includes urgency bonus)
    - Trade-in mentioned (10 points max)
    - Financing interest (10 points max)
    - COMBINATION BONUSES (15 points max):
      * Test drive + urgency + specific car: +15 points
      * Test drive + budget: +10 points
      * Urgency + specific car + budget: +10 points

    Total possible: 125 points (allows for HOT leads to exceed 100)
    """

    def calculate_score(
        self,
        message: str,
        extraction: Optional[Dict],
        expertise_output: Optional[Dict],
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculate lead score and quality.

        Returns:
            {
                "lead_score": 0-100,
                "lead_quality": "HOT" | "WARM" | "LUKEWARM" | "COLD",
                "score_breakdown": {...},
                "interest_level": "browsing" | "considering" | "ready-to-buy",
                "urgency": "low" | "medium" | "high" | "critical"
            }
        """
        score = 0
        breakdown = {}
        message_lower = message.lower()

        # 1. Car Inquiry Specificity (30 points)
        car_inquiry_score = self._score_car_inquiry(message_lower, extraction)
        score += car_inquiry_score
        breakdown["car_inquiry"] = car_inquiry_score

        # 1.5. APEX v3.0: Price Inquiry (25 points) - HOT signal
        price_inquiry_score = self._score_price_inquiry(message_lower)
        score += price_inquiry_score
        breakdown["price_inquiry"] = price_inquiry_score

        # 1.6. APEX v3.0: Website Reference (20 points) - HOT signal
        website_score = self._score_website_reference(message_lower)
        score += website_score
        breakdown["website_reference"] = website_score

        # 2. Budget Mentioned (20 points)
        budget_score = self._score_budget(message_lower, extraction)
        score += budget_score
        breakdown["budget_mentioned"] = budget_score

        # 3. Urgency Signals (15 points)
        urgency_score, urgency_level = self._score_urgency(message_lower, conversation_history)
        score += urgency_score
        breakdown["urgency_signals"] = urgency_score

        # 4. Test Drive Requests (15 points)
        test_drive_score = self._score_test_drive(message_lower)
        score += test_drive_score
        breakdown["test_drive_request"] = test_drive_score

        # 5. Trade-in Mentioned (10 points)
        trade_in_score = self._score_trade_in(message_lower)
        score += trade_in_score
        breakdown["trade_in_interest"] = trade_in_score

        # 6. Financing Interest (10 points)
        financing_score = self._score_financing(message_lower)
        score += financing_score
        breakdown["financing_interest"] = financing_score

        # 7. COMBINATION BONUSES (15 points max)
        # Award extra points when high-intent signals appear together
        combination_bonus = 0

        # Test drive + urgency combo (already maxed at 20 in _score_test_drive)
        # But add extra 15 points if ALSO has specific car mention
        if test_drive_score >= 20 and car_inquiry_score >= 15:
            combination_bonus += 15  # Test drive + urgency + specific car = 15 bonus points
            breakdown["hot_lead_combo"] = 15

        # Test drive + budget mention combo
        elif test_drive_score >= 15 and budget_score >= 10:
            combination_bonus += 10  # Test drive + budget = ready to buy
            breakdown["serious_buyer_combo"] = 10

        # Urgency + specific car + budget combo
        elif urgency_score >= 15 and car_inquiry_score >= 15 and budget_score >= 10:
            combination_bonus += 10  # All purchase signals present
            breakdown["purchase_ready_combo"] = 10

        score += combination_bonus

        # Determine lead quality
        if score >= 70:
            lead_quality = "HOT"
            interest_level = "ready-to-buy"
        elif score >= 50:
            lead_quality = "WARM"
            interest_level = "considering"
        elif score >= 30:
            lead_quality = "LUKEWARM"
            interest_level = "considering"
        else:
            lead_quality = "COLD"
            interest_level = "browsing"

        return {
            "lead_score": score,
            "lead_quality": lead_quality,
            "score_breakdown": breakdown,
            "interest_level": interest_level,
            "urgency": urgency_level
        }

    def _score_car_inquiry(self, message: str, extraction: Optional[Dict]) -> int:
        """Score car inquiry specificity (0-30 points)."""
        score = 0
        message_lower = message.lower()

        # APEX v3.0: Specific car model mentioned = HOT signal (25 points)
        specific_models = [
            "bmw x3", "bmw x5", "bmw x1", "bmw x4", "bmw 3-serie", "bmw 5-serie",
            "audi a4", "audi a6", "audi q3", "audi q5", "audi q7",
            "mercedes c-klasse", "mercedes e-klasse", "mercedes glc", "mercedes gle",
            "golf", "polo", "passat", "tiguan", "touran",
            "volvo v60", "volvo xc60", "volvo xc90",
            "x3", "x5", "x1", "x4", "3-serie", "5-serie"  # Short versions
        ]
        if any(model in message_lower for model in specific_models):
            score += 25
        # Otherwise check for generic make mention (15 points)
        elif any(make in message_lower for make in ["volkswagen", "vw", "audi", "bmw", "mercedes", "skoda", "seat", "ford", "opel", "peugeot", "renault", "toyota", "honda", "volvo"]):
            score += 15

        # Specific year/fuel type mentioned (10 points)
        if any(term in message_lower for term in ["2019", "2020", "2021", "2022", "2023", "2024", "diesel", "benzine", "hybride", "elektrisch"]):
            score += 10

        # Specific features mentioned (5 points)
        if any(term in message_lower for term in ["automaat", "cruise control", "navi", "leder", "trekhaak", "panoramadak"]):
            score += 5

        return min(score, 30)

    def _score_price_inquiry(self, message: str) -> int:
        """
        APEX v3.0: Score price inquiry (0-25 points).

        Price inquiry = HOT signal (serious buyer).
        Examples: "wat kost", "prijs", "kosten", "hoeveel kost"
        """
        price_keywords = [
            "wat kost", "hoeveel kost", "kosten", "prijs", "prijzen",
            "wat is de prijs", "hoeveel is", "wat zijn de prijzen"
        ]

        if any(keyword in message for keyword in price_keywords):
            return 25  # HOT signal - asking about price = ready to buy

        return 0

    def _score_website_reference(self, message: str) -> int:
        """
        APEX v3.0: Score website reference (0-20 points).

        Website reference = HOT signal (saw car on website, specific interest).
        Examples: "op jullie website", "op de site", "gezien op", "op jullie site"
        """
        website_keywords = [
            "website", "site", "gezien op", "zag op",
            "op jullie site", "op de site", "jullie website"
        ]

        if any(keyword in message for keyword in website_keywords):
            return 20  # HOT signal - saw on website = specific interest

        return 0

    def _score_budget(self, message: str, extraction: Optional[Dict]) -> int:
        """Score budget mentioned (0-20 points)."""
        score = 0

        # Budget keywords with specific amount (20 points)
        if any(term in message for term in ["budget", "maximaal", "max", "euro", "€"]):
            if any(char.isdigit() for char in message):
                score += 20
            else:
                score += 10  # Budget keyword but no amount

        return min(score, 20)

    def _score_urgency(self, message: str, conversation_history: List[Dict]) -> tuple[int, str]:
        """Score urgency signals (0-20 points). Returns (score, urgency_level)."""
        score = 0
        urgency_level = "low"
        message_lower = message.lower()

        # Critical urgency (20 points) - INCREASED from 15
        if any(term in message_lower for term in ["vandaag", "morgen", "nu", "direct", "zo snel mogelijk", "spoedig", "vandaag nog"]):
            score += 20
            urgency_level = "critical"

        # High urgency (15 points) - INCREASED from 10
        elif any(term in message_lower for term in ["deze week", "volgende week", "komende dagen", "dringend"]):
            score += 15
            urgency_level = "high"

        # Medium urgency (8 points) - INCREASED from 5
        elif any(term in message_lower for term in ["binnenkort", "snel", "graag", "interesse", "geïnteresseerd"]):
            score += 8
            urgency_level = "medium"

        # Check conversation length - longer = more serious
        if len(conversation_history) > 5:
            score += 5  # INCREASED from 3
            if urgency_level == "low":
                urgency_level = "medium"

        return min(score, 20), urgency_level

    def _score_test_drive(self, message: str) -> int:
        """Score test drive requests (0-20 points)."""
        message_lower = message.lower()
        test_drive_keywords = ["proefrit", "testrit", "proefrijden", "testen"]

        if any(keyword in message_lower for keyword in test_drive_keywords):
            # Extra points if combined with urgency
            if any(term in message_lower for term in ["vandaag", "morgen", "nu", "direct", "vandaag nog"]):
                return 20  # HOT - test drive + urgent timing
            return 15  # WARM - test drive requested

        return 0

    def _score_trade_in(self, message: str) -> int:
        """Score trade-in interest (0-10 points)."""
        trade_in_keywords = ["inruil", "huidige auto", "oude auto", "trade in", "inwisselen"]

        if any(keyword in message for keyword in trade_in_keywords):
            return 10

        return 0

    def _score_financing(self, message: str) -> int:
        """Score financing interest (0-10 points)."""
        financing_keywords = ["financier", "lening", "maandlasten", "aflossen", "betalen in termijnen", "lease"]

        if any(keyword in message for keyword in financing_keywords):
            return 10

        return 0


class IntelligentTagging:
    """
    20+ intelligent tags for car dealership CRM.

    Tag Categories:
    1. Customer Journey (5 tags)
    2. Car Interest (6 tags)
    3. Purchase Intent (5 tags)
    4. Behavioral (6 tags)
    5. Engagement (3 tags)
    """

    @staticmethod
    def generate_tags(
        message: str,
        lead_score_data: Dict,
        expertise_output: Optional[Dict],
        conversation_history: List[Dict]
    ) -> List[str]:
        """Generate intelligent tags based on conversation context."""
        tags = []
        message_lower = message.lower()

        # === 0. LEAD QUALITY TAGS (PRIORITY - Voor Chatwoot CRM filtering) ===
        # Use centralized registry for lead quality tags
        lead_quality = lead_score_data["lead_quality"]
        lead_score = lead_score_data["lead_score"]

        # Add lead quality tag (hot/warm/cold)
        if lead_quality in LEAD_QUALITY_MAP:
            tags.append(get_label_title(LEAD_QUALITY_MAP[lead_quality]))

        # === 0.1 BEHAVIORAL SEGMENTATION TAGS ===
        # Detect tijdverspilling patronen
        is_time_waster = IntelligentTagging._detect_time_waster(message_lower, conversation_history)

        if is_time_waster:
            # Tijdverspilling - niet-serieuze klanten
            tags.append(get_label_title("time_waster"))
        elif lead_quality == "HOT" or lead_score >= 70:
            # Serieuze koopinteresse - ready to buy
            tags.append(get_label_title("serious_buyer"))
        elif lead_quality in ["WARM", "COLD"] and lead_score >= 40:
            # Algemene interesse
            tags.append(get_label_title("serious_buyer"))
        else:
            # Algemene vragen - oriënterend
            tags.append(get_label_title("general_inquiry"))

        # === 1. CUSTOMER JOURNEY TAGS (5) ===
        # Based on conversation stage
        if len(conversation_history) == 0:
            tags.append(get_label_title("first_contact"))
        elif len(conversation_history) <= 3:
            tags.append(get_label_title("initial_inquiry"))
        elif len(conversation_history) <= 6:
            tags.append(get_label_title("information_gathering"))
        elif len(conversation_history) <= 10:
            tags.append(get_label_title("comparison_shopping"))
        else:
            tags.append(get_label_title("ready_to_buy"))

        # === 2. CAR INTEREST TAGS (6) ===
        # Specific make interest
        if any(make in message_lower for make in ["golf", "polo"]):
            tags.append(get_label_title("volkswagen"))
        elif "audi" in message_lower:
            tags.append(get_label_title("audi"))
        elif "bmw" in message_lower:
            tags.append(get_label_title("bmw"))
        elif "mercedes" in message_lower:
            tags.append(get_label_title("mercedes"))

        # Fuel type preference
        if "diesel" in message_lower:
            tags.append(get_label_title("diesel"))
        elif "benzine" in message_lower:
            tags.append(get_label_title("benzine"))
        elif "elektrisch" in message_lower:
            tags.append(get_label_title("elektrisch"))
        elif "hybride" in message_lower:
            tags.append(get_label_title("hybride"))

        # === 3. PURCHASE INTENT TAGS (6) ===
        # Purchase intent signals from message content
        if any(term in message_lower for term in ["kopen", "aanschaffen", "koop"]):
            tags.append(get_label_title("immediate_purchase"))

        # Budget specified
        if any(term in message_lower for term in ["budget", "maximaal", "max", "euro", "€"]) and any(char.isdigit() for char in message_lower):
            tags.append(get_label_title("budget_specified"))

        # Urgent timeline
        if any(term in message_lower for term in ["vandaag", "morgen", "nu", "direct", "zo snel mogelijk", "spoedig"]):
            tags.append(get_label_title("urgent_timeline"))

        # Trade-in mentioned
        if any(term in message_lower for term in ["inruil", "huidige auto", "oude auto", "trade in", "inwisselen"]):
            tags.append(get_label_title("trade_in_mentioned"))

        # Financing inquiry
        if any(term in message_lower for term in ["financier", "lening", "maandlasten", "aflossen", "betalen in termijnen", "lease"]):
            tags.append(get_label_title("financing_inquiry"))

        # === 4. BEHAVIORAL TAGS (4) ===
        # Test drive requested - already covered in INTENT tags above
        if any(term in message_lower for term in ["proefrit", "testrit"]):
            tags.append(get_label_title("test_drive_requested"))

        # Price-sensitive behavior
        if any(term in message_lower for term in ["prijs", "kosten", "goedkoop", "budget", "vergelijk", "goedkope"]):
            tags.append(get_label_title("price_shopper"))

        # Technical/Detail-oriented buyer
        if any(term in message_lower for term in ["specificatie", "motor", "verbruik", "vermogen", "koppel", "technische", "spec"]):
            tags.append(get_label_title("detail_oriented"))

        # Impulsive behavior (quick decision making)
        if any(term in message_lower for term in ["vandaag", "nu", "direct", "meteen"]) and lead_score_data["lead_score"] >= 70:
            tags.append(get_label_title("impulsive"))

        # Researcher behavior (detailed questions, multiple messages)
        if len(conversation_history) > 5 and lead_score_data["lead_score"] >= 40:
            tags.append(get_label_title("researcher"))

        # === 5. ENGAGEMENT TAGS (4) ===
        # Based on lead score and conversation activity
        if lead_score_data["lead_score"] >= 70:
            tags.append(get_label_title("high_engagement"))
        elif lead_score_data["lead_score"] >= 40:
            tags.append(get_label_title("medium_engagement"))
        else:
            tags.append(get_label_title("low_engagement"))

        # Repeat visitor (multiple conversations)
        if len(conversation_history) > 8:
            tags.append(get_label_title("repeat_visitor"))

        # === 6. ESCALATION TAGS (from ExpertiseAgent) ===
        if expertise_output and expertise_output.get("escalation_decision", {}).get("escalate"):
            escalation_type = expertise_output["escalation_decision"]["escalation_type"]
            tags.append(f"escalated:{escalation_type}")
            tags.append("status:needs-human-attention")

        # === 7. SOURCE TAG ===
        tags.append(get_label_title("whatsapp_ai"))

        return tags

    @staticmethod
    def _detect_time_waster(message: str, conversation_history: List[Dict]) -> bool:
        """
        Detect time-wasting behavior patterns.

        Returns:
            True if customer shows time-wasting behavior
        """
        # 1. Very short messages with no substance
        if len(message) < 10 and not any(char.isdigit() for char in message):
            return True

        # 2. Non-sensical or spam-like content
        spam_patterns = [
            "test", "testing", "hoi", "hallo", "hey", "yo",
            "lol", "haha", "hmm", "ok", "oke", "ja", "nee"
        ]
        # If ONLY spam pattern (no other content)
        message_words = message.lower().split()
        if all(word in spam_patterns for word in message_words) and len(message_words) <= 2:
            return True

        # 3. Repeated identical messages (spam behavior)
        if len(conversation_history) >= 2:
            recent_messages = [msg["content"] for msg in conversation_history[-3:]]
            if recent_messages.count(message) >= 2:
                return True

        # 4. Completely off-topic (no auto-related content)
        auto_keywords = [
            "auto", "wagen", "car", "voertuig", "golf", "polo", "audi", "bmw",
            "diesel", "benzine", "elektrisch", "prijs", "kopen", "proefrit",
            "financier", "lease", "km", "kilometerstand", "onderhoud"
        ]
        # If NO auto keywords AND minimal effort message
        if not any(keyword in message.lower() for keyword in auto_keywords):
            if len(message) < 30:
                return True

        # 5. Long conversation (>5 messages) but no progress
        if len(conversation_history) > 5:
            # Check if any purchase signal was ever mentioned
            all_messages = " ".join([msg["content"].lower() for msg in conversation_history])
            purchase_signals = [
                "kopen", "proefrit", "prijs", "budget", "financier",
                "interesse", "bekijken", "afspraak", "bezoek"
            ]
            if not any(signal in all_messages for signal in purchase_signals):
                return True  # Long conversation with zero purchase intent = time waster

        return False


class EnhancedCRMAgent(BaseAgent):
    """
    Enhanced CRM Agent with lead scoring and intelligent tagging.

    Features:
    - Lead scoring (0-100 points) with quality classification
    - 20+ intelligent tags for segmentation
    - Integration with ExpertiseAgent escalation data
    - Behavioral tracking (test drive, trade-in, financing)
    - Customer journey stage tracking
    - Database persistence for lead scores
    """

    def __init__(self):
        """Initialize Enhanced CRM Agent."""
        config = AGENT_CONFIGS["crm"]

        super().__init__(
            agent_name="enhanced_crm",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        self.scoring_engine = LeadScoringEngine()
        self.tagging_engine = IntelligentTagging()
        self.chatwoot_api = ChatwootAPI()

        logger.info("✅ Enhanced CRM Agent initialized with lead scoring and intelligent tagging")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute enhanced CRM updates.

        Args:
            state: Current conversation state

        Returns:
            {
                "output": {
                    "contact_updated": bool,
                    "lead_score": int,
                    "lead_quality": str,
                    "tags_added": List[str],
                    "custom_attributes": Dict
                },
                "tokens_used": {...},
                "cost_usd": 0.0
            }
        """
        logger.info(
            "🎯 Enhanced CRM: Lead scoring and tagging",
            extra={
                "message_id": state["message_id"],
                "conversation_id": state["conversation_id"]
            }
        )

        # Step 1: Calculate lead score
        lead_score_data = self.scoring_engine.calculate_score(
            message=state["content"],
            extraction=state.get("extraction_output"),
            expertise_output=state.get("expertise_output"),
            conversation_history=state.get("conversation_history", [])
        )

        # Step 2: Generate intelligent tags
        tags = self.tagging_engine.generate_tags(
            message=state["content"],
            lead_score_data=lead_score_data,
            expertise_output=state.get("expertise_output"),
            conversation_history=state.get("conversation_history", [])
        )

        # Step 3: Extract behavioral flags
        behavioral_flags = self._extract_behavioral_flags(state["content"])

        # Step 4: Prepare custom attributes
        custom_attributes = self._prepare_custom_attributes(
            state=state,
            lead_score_data=lead_score_data,
            behavioral_flags=behavioral_flags
        )

        # Step 5: Update Chatwoot (if credentials available)
        import asyncio
        chatwoot_success = asyncio.run(self._update_chatwoot(
            conversation_id=state["conversation_id"],
            tags=tags,
            custom_attributes=custom_attributes,
            sender_name=state.get("sender_name", "Unknown")
        ))

        # Step 6: Save lead score to database
        self._save_lead_score_to_db(
            customer_phone=state["sender_phone"],
            conversation_id=state["conversation_id"],
            lead_score_data=lead_score_data,
            behavioral_flags=behavioral_flags,
            extraction=state.get("extraction_output")
        )

        logger.info(
            f"✅ Enhanced CRM complete: Score={lead_score_data['lead_score']}, Quality={lead_score_data['lead_quality']}, Tags={len(tags)}",
            extra={
                "lead_score": lead_score_data["lead_score"],
                "lead_quality": lead_score_data["lead_quality"],
                "tags_count": len(tags)
            }
        )

        return {
            "output": {
                "contact_updated": chatwoot_success,
                "lead_score": lead_score_data["lead_score"],
                "lead_quality": lead_score_data["lead_quality"],
                "interest_level": lead_score_data["interest_level"],
                "urgency": lead_score_data["urgency"],
                "score_breakdown": lead_score_data["score_breakdown"],
                "tags_added": tags,
                "custom_attributes": custom_attributes,
                "behavioral_flags": behavioral_flags
            },
            "tokens_used": {
                "input": 0,  # No LLM call for scoring (rule-based)
                "output": 0,
                "total": 0
            },
            "cost_usd": 0.0
        }

    def _extract_behavioral_flags(self, message: str) -> Dict[str, bool]:
        """Extract behavioral flags from message."""
        message_lower = message.lower()

        return {
            "test_drive_requested": any(term in message_lower for term in ["proefrit", "testrit"]),
            "has_trade_in": any(term in message_lower for term in ["inruil", "inwisselen"]),
            "needs_financing": any(term in message_lower for term in ["financier", "lening", "maandlasten"]),
            "escalated": False  # Will be set if ExpertiseAgent escalated
        }

    def _prepare_custom_attributes(
        self,
        state: ConversationState,
        lead_score_data: Dict,
        behavioral_flags: Dict
    ) -> Dict[str, Any]:
        """Prepare custom attributes for Chatwoot."""
        attributes = {
            "lead_score": lead_score_data["lead_score"],
            "lead_quality": lead_score_data["lead_quality"],
            "interest_level": lead_score_data["interest_level"],
            "urgency": lead_score_data["urgency"]
        }

        # Add extraction data if available
        extraction = state.get("extraction_output")
        if extraction:
            if extraction.get("car_interest"):
                attributes["interested_in_make"] = extraction["car_interest"].get("make")
                attributes["interested_in_model"] = extraction["car_interest"].get("model")
                attributes["interested_in_fuel_type"] = extraction["car_interest"].get("fuel_type")

            if extraction.get("budget"):
                attributes["budget_max"] = extraction["budget"].get("max_amount")

        # Add behavioral flags
        attributes.update({
            "test_drive_requested": behavioral_flags["test_drive_requested"],
            "has_trade_in": behavioral_flags["has_trade_in"],
            "needs_financing": behavioral_flags["needs_financing"]
        })

        # Add conversation stage
        history_length = len(state.get("conversation_history", []))
        if history_length == 0:
            attributes["conversation_stage"] = "first-contact"
        elif history_length <= 3:
            attributes["conversation_stage"] = "initial-inquiry"
        elif history_length <= 6:
            attributes["conversation_stage"] = "information-gathering"
        else:
            attributes["conversation_stage"] = "consideration"

        return attributes

    async def _update_chatwoot(
        self,
        conversation_id: str,
        tags: List[str],
        custom_attributes: Dict,
        sender_name: str = "Unknown"
    ) -> bool:
        """
        Update Chatwoot with tags and attributes.

        Flow:
        1. Extract phone from conversation_id (format: "31612345678@c.us")
        2. Get or create contact
        3. Update custom attributes on contact
        4. Get or create conversation
        5. Add tags/labels to conversation

        Args:
            conversation_id: WhatsApp chat ID (e.g., "31612345678@c.us")
            tags: List of tags to add
            custom_attributes: Custom attributes to update
            sender_name: Sender's display name

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            # Extract phone from WhatsApp conversation_id
            # Format: "31612345678@c.us" → "31612345678"
            phone = conversation_id.replace("@c.us", "").replace("@s.whatsapp.net", "")

            # Ensure phone has + prefix for Chatwoot
            if not phone.startswith("+"):
                phone = f"+{phone}"

            # Step 1: Get or create contact (NO inbox_id required)
            contact = self.chatwoot_api.get_contact_by_phone(phone)
            if not contact:
                # Create new contact WITHOUT inbox_id
                contact_name = custom_attributes.get("name", f"WhatsApp {phone}")
                contact = self.chatwoot_api.create_contact(
                    phone=phone,
                    name=contact_name,
                    inbox_id=None  # Create without inbox
                )

                if not contact:
                    logger.warning(f"⚠️ Failed to create contact for {phone} (non-critical)")
                    return False

            contact_id = contact.get("id")
            logger.debug(f"✅ Contact resolved: ID {contact_id} ({phone})")

            # Step 2: Update custom attributes on contact
            attributes_updated = self.chatwoot_api.update_contact_attributes(
                contact_id=contact_id,
                custom_attributes=custom_attributes
            )

            if attributes_updated:
                logger.info(f"✅ Updated contact {contact_id} with lead score and attributes")
            else:
                logger.debug(f"⚠️ Failed to update attributes for contact {contact_id}")

            # Step 3: Get or create conversation and add labels
            if tags:
                try:
                    from app.integrations.chatwoot_sync import ChatwootSync

                    sync = ChatwootSync()

                    # FIRST: Get or create contact to obtain contact_id
                    chatwoot_contact_id = await sync.get_or_create_contact(
                        phone_number=conversation_id,  # WhatsApp chat ID (e.g., "31612345678@c.us")
                        name=sender_name
                    )

                    if not chatwoot_contact_id:
                        logger.warning(f"⚠️ Could not get/create contact for {phone}")
                        return True  # Non-critical failure

                    # THEN: Get or create conversation using contact_id
                    chatwoot_conversation_id = await sync.get_or_create_conversation(
                        contact_id=chatwoot_contact_id,  # ✅ Correct parameter
                        source_id=conversation_id          # ✅ Correct parameter
                    )

                    if chatwoot_conversation_id:
                        logger.info(f"📝 Adding {len(tags)} labels to conversation {chatwoot_conversation_id}")

                        # Add each label to the conversation
                        labels_added = 0
                        for tag in tags:
                            success = self.chatwoot_api.add_label(
                                conversation_id=str(chatwoot_conversation_id),
                                label=tag
                            )
                            if success:
                                labels_added += 1
                                logger.debug(f"✅ Tag '{tag}' added to conversation")
                            else:
                                logger.warning(f"⚠️ Failed to add tag '{tag}' (may not exist in Chatwoot - run setup_chatwoot_labels.py)")

                        logger.info(f"✅ Added {labels_added}/{len(tags)} labels to Chatwoot conversation {chatwoot_conversation_id}")
                    else:
                        logger.warning(f"⚠️ Could not get/create Chatwoot conversation for {phone}")

                except Exception as e:
                    logger.error(f"❌ Failed to add labels to Chatwoot: {e}", exc_info=True)

            return True

        except Exception as e:
            logger.warning(f"⚠️ Chatwoot update failed (non-critical): {e}")
            return False

    def _save_lead_score_to_db(
        self,
        customer_phone: str,
        conversation_id: str,
        lead_score_data: Dict,
        behavioral_flags: Dict,
        extraction: Optional[Dict]
    ) -> None:
        """Save lead score to database (migrations/005_add_lead_scores_table.sql)."""
        try:
            # TODO: Insert into lead_scores table
            # For now, just log it
            logger.info(
                f"📊 Lead score recorded: {customer_phone} = {lead_score_data['lead_score']} ({lead_score_data['lead_quality']})",
                extra={
                    "customer_phone": customer_phone,
                    "lead_score": lead_score_data["lead_score"],
                    "lead_quality": lead_score_data["lead_quality"],
                    "conversation_id": conversation_id
                }
            )
        except Exception as e:
            logger.error(f"❌ Failed to save lead score to DB: {e}")
