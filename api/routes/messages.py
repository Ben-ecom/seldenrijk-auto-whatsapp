"""
Message History Endpoints

REST API for retrieving conversation history:
- GET /api/messages - List messages with filters
- GET /api/messages/lead/{lead_id} - Get conversation for specific lead
"""

import os
from typing import Any
from fastapi import APIRouter, Query
from supabase import create_client, Client


router = APIRouter()


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
async def list_messages(
    lead_id: str | None = Query(None, description="Filter by lead ID"),
    direction: str | None = Query(None, description="Filter by direction (inbound/outbound)"),
    limit: int = Query(50, le=200, description="Max results"),
    offset: int = Query(0, description="Pagination offset")
) -> dict[str, Any]:
    """
    List messages with optional filters.

    Query Parameters:
    - lead_id: Filter by lead UUID
    - direction: Filter by direction (inbound/outbound)
    - limit: Maximum results (default: 50, max: 200)
    - offset: Pagination offset

    Returns:
    - messages: List of message objects
    - total: Total count
    - limit: Limit used
    - offset: Offset used
    """
    supabase = get_supabase()

    # Build query
    query = supabase.table("messages").select("*", count="exact")

    # Apply filters
    if lead_id:
        query = query.eq("lead_id", lead_id)
    if direction:
        query = query.eq("direction", direction)

    # Apply pagination
    query = query.range(offset, offset + limit - 1).order("created_at", desc=True)

    # Execute
    result = query.execute()

    return {
        "messages": result.data,
        "total": result.count,
        "limit": limit,
        "offset": offset
    }


@router.get("/lead/{lead_id}")
async def get_lead_conversation(lead_id: str) -> dict[str, Any]:
    """
    Get full conversation history for a specific lead.

    Returns messages in chronological order (oldest first) for display in chat UI.

    Returns:
    - messages: List of message objects (ordered chronologically)
    - lead: Lead object
    - message_count: Total messages
    """
    supabase = get_supabase()

    # Get lead
    lead_result = supabase.table("leads").select("*").eq("id", lead_id).execute()

    if not lead_result.data:
        return {"error": "Lead not found", "messages": [], "message_count": 0}

    lead = lead_result.data[0]

    # Get all messages (chronological order)
    messages_result = supabase.table("messages")\
        .select("*")\
        .eq("lead_id", lead_id)\
        .order("created_at", desc=False)\
        .execute()

    return {
        "messages": messages_result.data,
        "lead": lead,
        "message_count": len(messages_result.data)
    }
