"""
WhatsApp Webhook Receiver

This endpoint receives incoming WhatsApp messages from 360Dialog
and orchestrates the 2-agent system response.

Flow:
1. Receive WhatsApp message
2. Get or create lead
3. Save inbound message
4. Run Agent 2 (conversation) - ALWAYS
5. Run Agent 1 (extraction) - CONDITIONALLY (every 5 messages)
6. Send reply via WhatsApp
"""

import os
from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from supabase import create_client, Client
import httpx

from agent import Agent2ClaudeSDK, Agent1PydanticAI, ConversationMessage


router = APIRouter()


# ============ PYDANTIC MODELS ============

class WhatsAppMessage(BaseModel):
    """
    Inbound WhatsApp message from 360Dialog webhook.
    """
    from_: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str
    text: dict[str, Any] | None = None
    image: dict[str, Any] | None = None
    document: dict[str, Any] | None = None


class WhatsAppWebhookPayload(BaseModel):
    """
    360Dialog webhook payload structure.
    """
    messages: list[WhatsAppMessage]
    contacts: list[dict[str, Any]] | None = None


# ============ HELPERS ============

def get_supabase() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


async def get_or_create_lead(whatsapp_number: str) -> dict[str, Any]:
    """
    Get existing lead or create new one.

    Args:
        whatsapp_number: WhatsApp phone number

    Returns:
        Lead record
    """
    supabase = get_supabase()

    # Try to find existing lead
    result = supabase.table("leads").select("*").eq("whatsapp_number", whatsapp_number).execute()

    if result.data:
        return result.data[0]

    # Create new lead
    new_lead = supabase.table("leads").insert({
        "whatsapp_number": whatsapp_number,
        "qualification_status": "new",
        "source": "whatsapp"
    }).execute()

    return new_lead.data[0]


async def save_message(
    lead_id: str,
    direction: str,
    content: str,
    whatsapp_message_id: str | None = None,
    agent_name: str | None = None
) -> dict[str, Any]:
    """
    Save message to database.

    Args:
        lead_id: UUID of lead
        direction: "inbound" or "outbound"
        content: Message text
        whatsapp_message_id: WhatsApp message ID
        agent_name: Agent that generated the message

    Returns:
        Message record
    """
    supabase = get_supabase()

    message = supabase.table("messages").insert({
        "lead_id": lead_id,
        "direction": direction,
        "content": content,
        "message_type": "text",
        "whatsapp_message_id": whatsapp_message_id,
        "agent_name": agent_name
    }).execute()

    return message.data[0]


async def get_conversation_history(lead_id: str) -> list[ConversationMessage]:
    """
    Get conversation history for a lead.

    Args:
        lead_id: UUID of lead

    Returns:
        List of ConversationMessage objects
    """
    supabase = get_supabase()

    messages = supabase.table("messages")\
        .select("*")\
        .eq("lead_id", lead_id)\
        .order("created_at")\
        .execute()

    # Convert to ConversationMessage format
    history = []
    for msg in messages.data:
        history.append(ConversationMessage(
            sender="candidate" if msg["direction"] == "inbound" else "agent",
            content=msg["content"],
            timestamp=datetime.fromisoformat(msg["created_at"])
        ))

    return history


async def send_whatsapp_message(to: str, text: str) -> dict[str, Any]:
    """
    Send WhatsApp message via 360Dialog API.

    Args:
        to: WhatsApp number (e.g., "+31612345678")
        text: Message text

    Returns:
        API response
    """
    api_key = os.getenv("THREESIXTY_DIALOG_API_KEY")
    if not api_key:
        raise ValueError("THREESIXTY_DIALOG_API_KEY not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://waba.360dialog.io/v1/messages",
            headers={
                "D360-API-KEY": api_key,
                "Content-Type": "application/json"
            },
            json={
                "to": to,
                "type": "text",
                "text": {"body": text}
            },
            timeout=30.0
        )

        if response.status_code != 200:
            print(f"❌ Failed to send WhatsApp message: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")

        return response.json()


async def should_run_extraction(lead_id: str) -> bool:
    """
    Determine if Agent 1 (extraction) should run.

    Logic:
    - Run after 5 messages (initial extraction)
    - Then run every 5 messages (updates)

    Args:
        lead_id: UUID of lead

    Returns:
        True if extraction should run
    """
    supabase = get_supabase()

    # Count messages
    result = supabase.table("messages")\
        .select("id", count="exact")\
        .eq("lead_id", lead_id)\
        .execute()

    message_count = result.count

    # Check if already has qualification
    qual_result = supabase.table("qualifications")\
        .select("id")\
        .eq("lead_id", lead_id)\
        .execute()

    has_qualification = bool(qual_result.data)

    # First extraction after 5 messages
    if message_count >= 5 and not has_qualification:
        return True

    # Update extraction every 5 messages after that
    if has_qualification and message_count % 5 == 0:
        return True

    return False


# ============ ORCHESTRATION LOGIC ============

async def orchestrate_agents(lead_id: str, user_message: str) -> str:
    """
    Orchestrate the 2-agent system.

    This is the core logic that decides which agents to run.

    Flow:
    1. Run Agent 2 (conversation) - ALWAYS
    2. Run Agent 1 (extraction) - CONDITIONALLY

    Args:
        lead_id: UUID of lead
        user_message: Latest message from candidate

    Returns:
        Agent response text
    """
    # Get conversation history
    history = await get_conversation_history(lead_id)

    # Convert to dict format for Agent 2
    history_dicts = [
        {"sender": msg.sender, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
        for msg in history
    ]

    # ============ AGENT 2: CONVERSATION (Always runs) ============
    print(f"🤖 Running Agent 2 (Claude SDK) for lead {lead_id}")
    agent_2 = Agent2ClaudeSDK()
    reply = await agent_2.send_message(
        lead_id=lead_id,
        user_message=user_message,
        conversation_history=history_dicts
    )

    # ============ AGENT 1: EXTRACTION (Conditional) ============
    if await should_run_extraction(lead_id):
        print(f"📊 Running Agent 1 (Pydantic AI) for lead {lead_id}")
        agent_1 = Agent1PydanticAI()

        # Add current message to history for extraction
        current_history = history + [ConversationMessage(
            sender="candidate",
            content=user_message,
            timestamp=datetime.now()
        )]

        # Extract qualification
        qualification = await agent_1.extract_qualification(current_history)

        # Save to database
        supabase = get_supabase()
        supabase.table("qualifications").upsert({
            "lead_id": lead_id,
            "full_name": qualification.full_name,
            "years_experience": qualification.years_experience,
            "skills": qualification.skills,
            "technical_score": qualification.technical_score,
            "soft_skills_score": qualification.soft_skills_score,
            "experience_score": qualification.experience_score,
            "overall_score": qualification.overall_score,
            "qualification_status": qualification.qualification_status,
            "disqualification_reason": qualification.disqualification_reason,
            "missing_info": qualification.missing_info,
            "extraction_confidence": qualification.extraction_confidence,
            "model_used": "gpt-4o-mini"
        }).execute()

        print(f"✅ Qualification saved: {qualification.overall_score}/100 ({qualification.qualification_status})")

        # Update lead qualification status
        supabase.table("leads").update({
            "qualification_status": qualification.qualification_status,
            "qualification_score": qualification.overall_score / 100.0
        }).eq("id", lead_id).execute()

        # Notify recruiter if high score
        if qualification.overall_score >= 70:
            # TODO: Create notification for recruiter
            print(f"🎯 High score candidate! {qualification.full_name}: {qualification.overall_score}/100")

    return reply


# ============ WEBHOOK ENDPOINT ============

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp webhook receiver for 360Dialog.

    This endpoint:
    1. Receives inbound WhatsApp messages
    2. Orchestrates Agent 1 + Agent 2
    3. Sends reply back to WhatsApp

    360Dialog webhook documentation:
    https://docs.360dialog.com/whatsapp-api/whatsapp-api/media
    """
    try:
        # Parse payload
        body = await request.json()
        print(f"📨 Received WhatsApp webhook: {body}")

        # Validate payload structure
        if "messages" not in body:
            return {"status": "ignored", "reason": "No messages in payload"}

        payload = WhatsAppWebhookPayload(**body)

        # Process each message
        for message in payload.messages:
            # Only handle text messages for now
            if message.type != "text" or not message.text:
                print(f"⏭️  Skipping non-text message: {message.type}")
                continue

            # Extract phone number and text
            whatsapp_number = message.from_
            text_content = message.text.get("body", "")

            print(f"👤 Message from {whatsapp_number}: {text_content}")

            # Get or create lead
            lead = await get_or_create_lead(whatsapp_number)
            lead_id = lead["id"]

            # Save inbound message
            await save_message(
                lead_id=lead_id,
                direction="inbound",
                content=text_content,
                whatsapp_message_id=message.id
            )

            # Orchestrate agents
            reply = await orchestrate_agents(lead_id, text_content)

            # Save outbound message
            await save_message(
                lead_id=lead_id,
                direction="outbound",
                content=reply,
                agent_name="agent_2_claude"
            )

            # Send reply via WhatsApp
            await send_whatsapp_message(whatsapp_number, reply)

            print(f"✅ Reply sent to {whatsapp_number}")

        return {"status": "ok", "processed": len(payload.messages)}

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Webhook verification endpoint for 360Dialog.

    360Dialog sends a GET request to verify the webhook URL.
    We need to echo back the 'hub.challenge' parameter.
    """
    query_params = request.query_params

    if "hub.challenge" in query_params:
        challenge = query_params["hub.challenge"]
        print(f"✅ Webhook verification successful: {challenge}")
        return {"hub.challenge": challenge}

    return {"status": "ok"}
