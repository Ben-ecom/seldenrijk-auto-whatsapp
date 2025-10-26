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
