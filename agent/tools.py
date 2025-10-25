"""
Agent 2 Tools: RAG Search, Calendar, and Escalation

These tools are used by Agent 2 (Claude SDK) for:
- Semantic search in job postings (RAG)
- Semantic search in company docs (RAG)
- Calendar availability checking
- Human escalation
"""

import os
from typing import Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from openai import OpenAI


# ============ SUPABASE CLIENT ============
def get_supabase_client() -> Client:
    """Get Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

    return create_client(url, key)


# ============ OPENAI CLIENT (for embeddings) ============
def get_openai_client() -> OpenAI:
    """Get OpenAI client for embeddings."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")
    return OpenAI(api_key=api_key)


# ============ TOOL 1: SEARCH JOB POSTINGS ============

async def search_job_postings_impl(
    lead_id: str,
    query: str
) -> str:
    """
    Search job postings using semantic search (RAG).

    Args:
        lead_id: UUID of lead (for logging)
        query: Search query (e.g., "kapper amsterdam fulltime")

    Returns:
        Formatted job postings results
    """
    try:
        # Generate embedding for query
        openai_client = get_openai_client()
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding

        # Search using PGVector
        supabase = get_supabase_client()
        results = supabase.rpc(
            "vector_search_jobs",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": 3
            }
        ).execute()

        # Log tool execution
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="search_job_postings",
            tool_input={"query": query},
            tool_output=f"Found {len(results.data)} jobs",
            success=True
        )

        # Format results
        if not results.data:
            return "Geen passende vacatures gevonden op dit moment."

        formatted = []
        for idx, job in enumerate(results.data, 1):
            formatted.append(
                f"{idx}. **{job['title']}** - {job['location']}\n"
                f"   Type: {job['job_type']}\n"
                f"   {job['chunk_text'][:200]}..."
            )

        return "\n\n".join(formatted)

    except Exception as e:
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="search_job_postings",
            tool_input={"query": query},
            tool_output=str(e),
            success=False
        )
        return f"Sorry, er ging iets mis bij het zoeken naar vacatures: {str(e)}"


search_job_postings_tool = {
    "name": "search_job_postings",
    "description": "Search available job postings using semantic search. Use when candidate asks about vacatures, available positions, or when you want to show matching jobs based on their skills/location.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing what to look for (e.g., 'kapper amsterdam fulltime', 'junior stylist', 'kleuren specialist')"
            }
        },
        "required": ["query"]
    }
}


# ============ TOOL 2: SEARCH COMPANY DOCS ============

async def search_company_docs_impl(
    lead_id: str,
    query: str
) -> str:
    """
    Search company documentation using semantic search (RAG).

    Args:
        lead_id: UUID of lead (for logging)
        query: Search query (e.g., "sollicitatieprocedure", "salaris")

    Returns:
        Formatted company docs results
    """
    try:
        # Generate embedding
        openai_client = get_openai_client()
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding

        # Search using PGVector
        supabase = get_supabase_client()
        results = supabase.rpc(
            "vector_search_company_docs",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": 2
            }
        ).execute()

        # Log tool execution
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="search_company_docs",
            tool_input={"query": query},
            tool_output=f"Found {len(results.data)} docs",
            success=True
        )

        # Format results
        if not results.data:
            return "Ik heb geen specifieke informatie over dat onderwerp. Laat me een collega inschakelen die je verder kan helpen."

        formatted = []
        for doc in results.data:
            formatted.append(
                f"**{doc['title']}**\n{doc['chunk_text']}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="search_company_docs",
            tool_input={"query": query},
            tool_output=str(e),
            success=False
        )
        return f"Sorry, ik kan die informatie niet vinden: {str(e)}"


search_company_docs_tool = {
    "name": "search_company_docs",
    "description": "Search company documentation (FAQs, policies, benefits, culture). Use when candidate asks about salary, benefits, application process, company culture, work environment, etc.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for company information (e.g., 'sollicitatieprocedure', 'salaris benefits', 'werktijden', 'bedrijfscultuur')"
            }
        },
        "required": ["query"]
    }
}


# ============ TOOL 3: CHECK CALENDAR AVAILABILITY ============

async def check_calendar_availability_impl(
    lead_id: str,
    preferred_date: str | None = None,
    timezone: str = "Europe/Amsterdam"
) -> str:
    """
    Check available interview time slots.

    Args:
        lead_id: UUID of lead
        preferred_date: Preferred date in YYYY-MM-DD format (optional)
        timezone: Timezone (default: Europe/Amsterdam)

    Returns:
        Available time slots
    """
    try:
        # TODO: Integrate with Calendly API
        # For now, return mock availability

        # Parse preferred date or use next week
        if preferred_date:
            try:
                date_obj = datetime.strptime(preferred_date, "%Y-%m-%d")
            except ValueError:
                date_obj = datetime.now() + timedelta(days=7)
        else:
            date_obj = datetime.now() + timedelta(days=7)

        # Generate 3 time slots
        slots = []
        for i in range(3):
            slot_date = date_obj + timedelta(days=i)
            slots.append(
                f"- {slot_date.strftime('%A %d %B')}: 10:00-10:30 of 14:00-14:30"
            )

        # Log tool execution
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="check_calendar_availability",
            tool_input={"preferred_date": preferred_date, "timezone": timezone},
            tool_output=f"Found {len(slots)} available slots",
            success=True
        )

        return "Beschikbare tijdsloten:\n" + "\n".join(slots)

    except Exception as e:
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="check_calendar_availability",
            tool_input={"preferred_date": preferred_date},
            tool_output=str(e),
            success=False
        )
        return f"Sorry, ik kan de agenda niet checken: {str(e)}"


check_calendar_availability_tool = {
    "name": "check_calendar_availability",
    "description": "Check available interview time slots. Use when candidate is ready for an interview and wants to schedule a meeting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "preferred_date": {
                "type": "string",
                "description": "Preferred date in YYYY-MM-DD format (optional)"
            },
            "timezone": {
                "type": "string",
                "description": "Timezone (default: Europe/Amsterdam)"
            }
        },
        "required": []
    }
}


# ============ TOOL 4: ESCALATE TO HUMAN ============

async def escalate_to_human_impl(
    lead_id: str,
    reason: str,
    urgency: str = "medium"
) -> str:
    """
    Escalate conversation to human recruiter.

    Args:
        lead_id: UUID of lead
        reason: Reason for escalation
        urgency: Urgency level (low/medium/high)

    Returns:
        Confirmation message
    """
    try:
        # Create notification for recruiter
        supabase = get_supabase_client()

        # Get lead info
        lead = supabase.table("leads").select("*").eq("id", lead_id).single().execute()

        # Create notification
        supabase.table("notifications").insert({
            "user_id": lead.data.get("assigned_recruiter_id"),  # TODO: assign recruiter
            "type": "human_review_needed",
            "title": f"Escalatie nodig: {lead.data.get('full_name', 'Onbekend')}",
            "message": f"Reden: {reason}\nUrgentie: {urgency}",
            "link": f"/leads/{lead_id}"
        }).execute()

        # Log tool execution
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="escalate_to_human",
            tool_input={"reason": reason, "urgency": urgency},
            tool_output="Escalation created",
            success=True
        )

        return f"Ik heb een collega ingeschakeld die je verder helpt met: {reason}"

    except Exception as e:
        await _log_tool_execution(
            lead_id=lead_id,
            tool_name="escalate_to_human",
            tool_input={"reason": reason, "urgency": urgency},
            tool_output=str(e),
            success=False
        )
        return f"Sorry, ik kan momenteel geen collega inschakelen: {str(e)}"


escalate_to_human_tool = {
    "name": "escalate_to_human",
    "description": "Transfer conversation to a human recruiter. Use when: candidate asks complex questions about salary negotiation, wants to speak with manager, has technical issues, or situation requires human judgment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why human assistance is needed (e.g., 'Kandidaat wil salaris bespreken', 'Technisch probleem met WhatsApp')"
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Urgency level: low (routine question), medium (needs response today), high (immediate attention needed)"
            }
        },
        "required": ["reason"]
    }
}


# ============ TOOLS DEFINITION (for Claude SDK) ============

TOOLS_DEFINITION = [
    search_job_postings_tool,
    search_company_docs_tool,
    check_calendar_availability_tool,
    escalate_to_human_tool
]


# ============ TOOL EXECUTION LOGGING ============

async def _log_tool_execution(
    lead_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: str,
    success: bool
) -> None:
    """
    Log tool execution to database for audit trail.

    Args:
        lead_id: UUID of lead
        tool_name: Name of executed tool
        tool_input: Input parameters
        tool_output: Tool result
        success: Whether execution succeeded
    """
    try:
        supabase = get_supabase_client()
        supabase.table("tools_log").insert({
            "lead_id": lead_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output[:1000],  # Limit size
            "success": success,
            "execution_time_ms": 0  # TODO: measure actual time
        }).execute()
    except Exception as e:
        print(f"Failed to log tool execution: {e}")
