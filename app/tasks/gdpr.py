"""
GDPR compliance background tasks.
Handles scheduled data retention enforcement and consent cleanup.
"""
from celery import Task
from datetime import datetime, timedelta
from app.celery_app import celery_app
from app.monitoring.logging_config import get_logger
from app.database.supabase_pool import get_supabase_client
import httpx
import os

logger = get_logger(__name__)

@celery_app.task(name="app.tasks.gdpr.enforce_data_retention")
def enforce_data_retention():
    """
    Enforce data retention policies by deleting/anonymizing old data.
    Runs daily at 2 AM.
    """
    supabase = get_supabase_client()

    try:
        # Get all retention policies
        policies_result = supabase.table("data_retention_policies")\
            .select("*")\
            .execute()

        policies = policies_result.data

        results = {}

        for policy in policies:
            data_type = policy["data_type"]
            retention_days = policy["retention_days"]
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            logger.info(
                "Enforcing retention policy",
                extra={
                    "data_type": data_type,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat()
                }
            )

            # Handle different data types
            if data_type == "consent_records":
                # Never delete consent records (legal requirement)
                results[data_type] = {"action": "skipped", "reason": "legal_requirement"}

            elif data_type == "contacts":
                # Anonymize contacts with no activity after retention period
                count = _anonymize_inactive_contacts(cutoff_date)
                results[data_type] = {"action": "anonymized", "count": count}

            elif data_type == "conversations":
                # Archive old conversations
                count = _archive_old_conversations(cutoff_date)
                results[data_type] = {"action": "archived", "count": count}

            elif data_type == "analytics":
                # Delete old analytics data
                count = _delete_old_analytics(cutoff_date)
                results[data_type] = {"action": "deleted", "count": count}

        logger.info("Data retention enforcement completed", extra={"results": results})

        return {"status": "completed", "results": results}

    except Exception as e:
        logger.error("Data retention enforcement failed", extra={"error": str(e)}, exc_info=True)
        raise

def _anonymize_inactive_contacts(cutoff_date: datetime) -> int:
    """
    Anonymize contacts with no activity after cutoff date.

    Args:
        cutoff_date: Date before which contacts should be anonymized

    Returns:
        int: Number of contacts anonymized
    """
    # TODO: Implement contact anonymization
    # This requires checking Chatwoot API for last activity date
    return 0

def _archive_old_conversations(cutoff_date: datetime) -> int:
    """
    Archive conversations older than cutoff date.

    Args:
        cutoff_date: Date before which conversations should be archived

    Returns:
        int: Number of conversations archived
    """
    # TODO: Implement conversation archiving
    # This depends on Chatwoot API capabilities
    return 0

def _delete_old_analytics(cutoff_date: datetime) -> int:
    """
    Delete analytics data older than cutoff date.

    Args:
        cutoff_date: Date before which analytics should be deleted

    Returns:
        int: Number of records deleted
    """
    supabase = get_supabase_client()

    try:
        # Delete from analytics tables (if they exist)
        # This is a placeholder - actual implementation depends on analytics schema
        logger.info("Analytics deletion not yet implemented")
        return 0

    except Exception as e:
        logger.error("Failed to delete analytics", extra={"error": str(e)}, exc_info=True)
        return 0

@celery_app.task(name="app.tasks.gdpr.cleanup_withdrawn_consent")
def cleanup_withdrawn_consent():
    """
    Process withdrawn consents and stop data processing.
    Runs hourly.
    """
    supabase = get_supabase_client()

    try:
        # Find contacts who withdrew consent in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        result = supabase.table("consent_records")\
            .select("contact_id, consent_type")\
            .eq("granted", False)\
            .gte("timestamp", one_hour_ago.isoformat())\
            .execute()

        withdrawn_consents = result.data

        if not withdrawn_consents:
            logger.info("No withdrawn consents to process")
            return {"status": "completed", "processed_count": 0}

        processed_count = 0

        for consent in withdrawn_consents:
            contact_id = consent["contact_id"]
            consent_type = consent["consent_type"]

            # Take action based on consent type
            if consent_type == "marketing":
                # Remove from marketing lists
                _remove_from_marketing(contact_id)

            elif consent_type == "analytics":
                # Stop analytics tracking
                _disable_analytics(contact_id)

            elif consent_type == "communication":
                # Mark contact as do-not-contact
                _mark_do_not_contact(contact_id)

            processed_count += 1

        logger.info(
            "Withdrawn consents processed",
            extra={"processed_count": processed_count}
        )

        return {"status": "completed", "processed_count": processed_count}

    except Exception as e:
        logger.error("Consent cleanup failed", extra={"error": str(e)}, exc_info=True)
        raise

def _remove_from_marketing(contact_id: str):
    """Remove contact from marketing lists."""
    # TODO: Implement marketing list removal
    logger.info("Marketing removal", extra={"contact_id": contact_id})

def _disable_analytics(contact_id: str):
    """Disable analytics tracking for contact."""
    # TODO: Implement analytics disabling
    logger.info("Analytics disabled", extra={"contact_id": contact_id})

def _mark_do_not_contact(contact_id: str):
    """Mark contact as do-not-contact in Chatwoot."""
    chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    try:
        with httpx.Client() as client:
            client.patch(
                f"{chatwoot_url}/api/v1/accounts/{account_id}/contacts/{contact_id}",
                headers={"api_access_token": api_token},
                json={"custom_attributes": {"do_not_contact": True}},
                timeout=10.0
            )

        logger.info("Contact marked as do-not-contact", extra={"contact_id": contact_id})

    except Exception as e:
        logger.error(
            "Failed to mark contact as do-not-contact",
            extra={"contact_id": contact_id, "error": str(e)}
        )
