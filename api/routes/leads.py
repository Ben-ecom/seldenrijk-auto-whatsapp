"""
Lead Management Endpoints

REST API for managing leads:
- GET /api/leads - List all leads with filters
- GET /api/leads/{id} - Get single lead details
- POST /api/leads - Create new lead (manual entry)
- PATCH /api/leads/{id} - Update lead
"""

import os
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from supabase import create_client, Client


router = APIRouter()


# ============ PYDANTIC MODELS ============

class LeadCreate(BaseModel):
    """Create new lead (manual entry from dashboard)."""
    whatsapp_number: str
    email: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    years_experience: int | None = None
    source: str = "manual"


class LeadUpdate(BaseModel):
    """Update lead details."""
    email: str | None = None
    full_name: str | None = None
    job_title: str | None = None
    years_experience: int | None = None
    qualification_status: str | None = None


# ============ HELPERS ============

def get_supabase() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


# ============ ENDPOINTS ============

@router.get("/")
async def list_leads(
    status: str | None = Query(None, description="Filter by qualification status"),
    limit: int = Query(50, le=100, description="Max results"),
    offset: int = Query(0, description="Pagination offset")
) -> dict[str, Any]:
    """
    List all leads with optional filters.

    Query Parameters:
    - status: Filter by qualification_status (new, in_progress, qualified, disqualified, pending_review)
    - limit: Maximum number of results (default: 50, max: 100)
    - offset: Pagination offset (default: 0)

    Returns:
    - leads: List of lead objects
    - total: Total count (for pagination)
    - limit: Limit used
    - offset: Offset used
    """
    supabase = get_supabase()

    # Build query
    query = supabase.table("leads").select("*", count="exact")

    # Apply status filter
    if status:
        query = query.eq("qualification_status", status)

    # Apply pagination
    query = query.range(offset, offset + limit - 1).order("created_at", desc=True)

    # Execute
    result = query.execute()

    return {
        "leads": result.data,
        "total": result.count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{lead_id}")
async def get_lead(lead_id: str) -> dict[str, Any]:
    """
    Get single lead with qualification data and message count.

    Returns:
    - Lead object
    - Qualification data (if exists)
    - Message statistics
    """
    supabase = get_supabase()

    # Get lead
    lead_result = supabase.table("leads").select("*").eq("id", lead_id).execute()

    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = lead_result.data[0]

    # Get qualification (if exists)
    qual_result = supabase.table("qualifications").select("*").eq("lead_id", lead_id).execute()
    qualification = qual_result.data[0] if qual_result.data else None

    # Get message stats
    msg_result = supabase.table("messages").select("id", count="exact").eq("lead_id", lead_id).execute()
    message_count = msg_result.count

    return {
        "lead": lead,
        "qualification": qualification,
        "message_count": message_count
    }


@router.post("/")
async def create_lead(lead_data: LeadCreate) -> dict[str, Any]:
    """
    Create new lead manually (from dashboard).

    This is for recruiters to manually add leads that didn't come via WhatsApp.
    """
    supabase = get_supabase()

    # Check if lead with this WhatsApp number already exists
    existing = supabase.table("leads").select("id").eq("whatsapp_number", lead_data.whatsapp_number).execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="Lead with this WhatsApp number already exists")

    # Create lead
    result = supabase.table("leads").insert({
        "whatsapp_number": lead_data.whatsapp_number,
        "email": lead_data.email,
        "full_name": lead_data.full_name,
        "job_title": lead_data.job_title,
        "years_experience": lead_data.years_experience,
        "source": lead_data.source,
        "qualification_status": "new"
    }).execute()

    return {"lead": result.data[0]}


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, lead_data: LeadUpdate) -> dict[str, Any]:
    """
    Update lead details.

    Only updates fields that are provided (partial update).
    """
    supabase = get_supabase()

    # Build update dict (only non-None fields)
    update_data = {k: v for k, v in lead_data.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Update lead
    result = supabase.table("leads").update(update_data).eq("id", lead_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    return {"lead": result.data[0]}
