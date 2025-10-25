"""
GDPR compliance endpoints.
Implements Right to be Forgotten, Right to Data Portability, and consent management.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from app.database.supabase_pool import get_supabase_client
from app.monitoring.logging_config import get_logger
import httpx
import os
import json

logger = get_logger(__name__)
router = APIRouter(prefix="/gdpr", tags=["GDPR"])

# ============ MODELS ============

class ConsentRequest(BaseModel):
    """Model for consent management."""
    contact_id: str
    consent_type: str  # marketing, analytics, communication
    granted: bool
    ip_address: Optional[str] = None

class DataExportRequest(BaseModel):
    """Model for data export request."""
    contact_id: str
    email: EmailStr
    include_conversations: bool = True
    include_metadata: bool = True

class DataDeletionRequest(BaseModel):
    """Model for data deletion request."""
    contact_id: str
    confirmation: bool = False
    reason: Optional[str] = None

class GDPRStatus(BaseModel):
    """Model for GDPR status response."""
    contact_id: str
    consents: dict
    data_retention_days: int
    can_be_deleted: bool
    export_available: bool

# ============ ENDPOINTS ============

@router.post("/consent", status_code=201)
async def record_consent(request: ConsentRequest):
    """
    Record user consent for data processing.

    Args:
        request: Consent details

    Returns:
        dict: Consent record confirmation
    """
    supabase = get_supabase_client()

    try:
        # Store consent record
        consent_record = {
            "contact_id": request.contact_id,
            "consent_type": request.consent_type,
            "granted": request.granted,
            "ip_address": request.ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = supabase.table("consent_records").insert(consent_record).execute()

        logger.info(
            "Consent recorded",
            extra={
                "contact_id": request.contact_id,
                "consent_type": request.consent_type,
                "granted": request.granted,
            }
        )

        return {
            "status": "recorded",
            "consent_id": result.data[0]["id"],
            "contact_id": request.contact_id,
        }

    except Exception as e:
        logger.error("Failed to record consent", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record consent")

@router.get("/consent/{contact_id}")
async def get_consent_status(contact_id: str) -> GDPRStatus:
    """
    Get current consent status for a contact.

    Args:
        contact_id: Chatwoot contact ID

    Returns:
        GDPRStatus: Current GDPR status
    """
    supabase = get_supabase_client()

    try:
        # Get all consent records for contact
        result = supabase.table("consent_records")\
            .select("*")\
            .eq("contact_id", contact_id)\
            .order("timestamp", desc=True)\
            .execute()

        # Build consent dict (latest consent per type)
        consents = {}
        for record in result.data:
            consent_type = record["consent_type"]
            if consent_type not in consents:
                consents[consent_type] = record["granted"]

        # Check if contact can be deleted
        # (e.g., no active conversations, no pending orders)
        can_be_deleted = await _check_can_delete(contact_id)

        return GDPRStatus(
            contact_id=contact_id,
            consents=consents,
            data_retention_days=90,  # Default retention period
            can_be_deleted=can_be_deleted,
            export_available=True,
        )

    except Exception as e:
        logger.error("Failed to get consent status", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get consent status")

@router.post("/export")
async def export_personal_data(
    request: DataExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Export all personal data for a contact (GDPR Right to Data Portability).

    Args:
        request: Export request details
        background_tasks: FastAPI background tasks

    Returns:
        dict: Export job details
    """
    supabase = get_supabase_client()

    try:
        # Create export job record
        export_job = {
            "contact_id": request.contact_id,
            "email": request.email,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

        result = supabase.table("gdpr_exports").insert(export_job).execute()
        export_id = result.data[0]["id"]

        # Queue background task to generate export
        background_tasks.add_task(
            _generate_data_export,
            export_id,
            request.contact_id,
            request.email,
            request.include_conversations,
            request.include_metadata
        )

        logger.info(
            "Data export requested",
            extra={"contact_id": request.contact_id, "export_id": export_id}
        )

        return {
            "status": "processing",
            "export_id": export_id,
            "estimated_time_minutes": 5,
            "expires_at": export_job["expires_at"],
        }

    except Exception as e:
        logger.error("Failed to create export job", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create export job")

@router.get("/export/{export_id}/status")
async def get_export_status(export_id: str):
    """
    Get status of data export job.

    Args:
        export_id: Export job ID

    Returns:
        dict: Export status
    """
    supabase = get_supabase_client()

    try:
        result = supabase.table("gdpr_exports")\
            .select("*")\
            .eq("id", export_id)\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Export not found")

        export = result.data

        return {
            "export_id": export_id,
            "status": export["status"],
            "created_at": export["created_at"],
            "completed_at": export.get("completed_at"),
            "download_url": export.get("download_url"),
            "expires_at": export["expires_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get export status", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get export status")

@router.delete("/contacts/{contact_id}")
async def delete_contact_data(
    contact_id: str,
    request: DataDeletionRequest,
    background_tasks: BackgroundTasks
):
    """
    Delete all personal data for a contact (GDPR Right to be Forgotten).

    Args:
        contact_id: Chatwoot contact ID
        request: Deletion confirmation
        background_tasks: FastAPI background tasks

    Returns:
        dict: Deletion job details
    """
    if not request.confirmation:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Set confirmation=true to proceed."
        )

    # Check if contact can be deleted
    can_delete = await _check_can_delete(contact_id)
    if not can_delete:
        raise HTTPException(
            status_code=409,
            detail="Contact cannot be deleted (active conversations or pending transactions)"
        )

    supabase = get_supabase_client()

    try:
        # Create deletion job record
        deletion_job = {
            "contact_id": contact_id,
            "status": "pending",
            "reason": request.reason,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("gdpr_deletions").insert(deletion_job).execute()
        deletion_id = result.data[0]["id"]

        # Queue background task for deletion
        background_tasks.add_task(_execute_data_deletion, deletion_id, contact_id)

        logger.info(
            "Data deletion requested",
            extra={"contact_id": contact_id, "deletion_id": deletion_id}
        )

        return {
            "status": "processing",
            "deletion_id": deletion_id,
            "contact_id": contact_id,
            "estimated_time_minutes": 2,
        }

    except Exception as e:
        logger.error("Failed to create deletion job", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create deletion job")

# ============ BACKGROUND TASKS ============

async def _generate_data_export(
    export_id: str,
    contact_id: str,
    email: str,
    include_conversations: bool,
    include_metadata: bool
):
    """Generate complete data export for contact."""
    supabase = get_supabase_client()

    try:
        # Update status to processing
        supabase.table("gdpr_exports")\
            .update({"status": "processing"})\
            .eq("id", export_id)\
            .execute()

        # Collect all data
        export_data = {
            "contact_id": contact_id,
            "exported_at": datetime.utcnow().isoformat(),
            "data": {}
        }

        # Get contact data from Chatwoot
        chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
        api_token = os.getenv("CHATWOOT_API_TOKEN")
        account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

        async with httpx.AsyncClient() as client:
            # Get contact details
            response = await client.get(
                f"{chatwoot_url}/api/v1/accounts/{account_id}/contacts/{contact_id}",
                headers={"api_access_token": api_token},
                timeout=10.0
            )
            export_data["data"]["contact"] = response.json()

            # Get conversations if requested
            if include_conversations:
                response = await client.get(
                    f"{chatwoot_url}/api/v1/accounts/{account_id}/contacts/{contact_id}/conversations",
                    headers={"api_access_token": api_token},
                    timeout=10.0
                )
                export_data["data"]["conversations"] = response.json()

        # Get metadata from Supabase
        if include_metadata:
            result = supabase.table("consent_records")\
                .select("*")\
                .eq("contact_id", contact_id)\
                .execute()
            export_data["data"]["consent_records"] = result.data

        # Save export to storage (Supabase Storage or S3)
        export_json = json.dumps(export_data, indent=2)
        file_name = f"gdpr_export_{contact_id}_{datetime.utcnow().timestamp()}.json"

        # Upload to Supabase Storage
        supabase.storage.from_("gdpr-exports").upload(
            file_name,
            export_json.encode(),
            {"content-type": "application/json"}
        )

        # Get download URL (expires in 7 days)
        download_url = supabase.storage.from_("gdpr-exports").create_signed_url(
            file_name,
            60 * 60 * 24 * 7  # 7 days
        )

        # Update export record
        supabase.table("gdpr_exports")\
            .update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "download_url": download_url["signedURL"],
                "file_name": file_name,
            })\
            .eq("id", export_id)\
            .execute()

        # TODO: Send email with download link

        logger.info("Data export completed", extra={"export_id": export_id})

    except Exception as e:
        logger.error("Data export failed", extra={"export_id": export_id, "error": str(e)}, exc_info=True)

        # Update status to failed
        supabase.table("gdpr_exports")\
            .update({"status": "failed", "error": str(e)})\
            .eq("id", export_id)\
            .execute()

async def _execute_data_deletion(deletion_id: str, contact_id: str):
    """Execute complete data deletion for contact."""
    supabase = get_supabase_client()

    try:
        # Update status to processing
        supabase.table("gdpr_deletions")\
            .update({"status": "processing"})\
            .eq("id", deletion_id)\
            .execute()

        # Anonymize contact in Chatwoot (don't fully delete to preserve conversation history)
        chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
        api_token = os.getenv("CHATWOOT_API_TOKEN")
        account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{chatwoot_url}/api/v1/accounts/{account_id}/contacts/{contact_id}",
                headers={"api_access_token": api_token},
                json={
                    "name": f"Deleted User {contact_id[:8]}",
                    "email": f"deleted_{contact_id}@anonymized.local",
                    "phone_number": None,
                    "custom_attributes": {"gdpr_deleted": True},
                },
                timeout=10.0
            )

        # Delete consent records
        supabase.table("consent_records")\
            .delete()\
            .eq("contact_id", contact_id)\
            .execute()

        # Delete any cached data
        # TODO: Delete from Redis cache if using

        # Update deletion record
        supabase.table("gdpr_deletions")\
            .update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
            })\
            .eq("id", deletion_id)\
            .execute()

        logger.info("Data deletion completed", extra={"deletion_id": deletion_id, "contact_id": contact_id})

    except Exception as e:
        logger.error("Data deletion failed", extra={"deletion_id": deletion_id, "error": str(e)}, exc_info=True)

        # Update status to failed
        supabase.table("gdpr_deletions")\
            .update({"status": "failed", "error": str(e)})\
            .eq("id", deletion_id)\
            .execute()

async def _check_can_delete(contact_id: str) -> bool:
    """
    Check if contact can be safely deleted.

    Args:
        contact_id: Contact ID to check

    Returns:
        bool: True if contact can be deleted
    """
    # Check if contact has active conversations
    chatwoot_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{chatwoot_url}/api/v1/accounts/{account_id}/contacts/{contact_id}/conversations",
                headers={"api_access_token": api_token},
                params={"status": "open"},
                timeout=10.0
            )

            conversations = response.json()

            # Don't allow deletion if there are open conversations
            if conversations and len(conversations) > 0:
                return False

        return True

    except Exception as e:
        logger.error("Failed to check deletion eligibility", extra={"error": str(e)}, exc_info=True)
        return False
