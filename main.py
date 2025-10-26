"""
Seldenrijk Auto WhatsApp Chatbot
FastAPI application met Twilio + Chatwoot integration
Demo-ready in 10 minuten!
"""

from fastapi import FastAPI, Request, Form, HTTPException, Header
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import httpx
from datetime import datetime
from typing import Optional
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Seldenrijk Auto WhatsApp Bot")

# Twilio credentials (from environment variables)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Chatwoot credentials (will be configured)
CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY", "")
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://app.chatwoot.com")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "")
CHATWOOT_INBOX_ID = os.getenv("CHATWOOT_INBOX_ID", "")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory session storage (later: use Redis/PostgreSQL)
active_sessions = {}
human_handoff_sessions = set()


# ============================================================================
# CHATBOT LOGIC - Auto Dealer Conversation Flow
# ============================================================================

def get_bot_response(user_message: str, from_number: str) -> tuple[str, bool]:
    """
    Main chatbot logic voor autodealers.

    Returns:
        (response_text, needs_human_handoff)
    """
    msg = user_message.lower()

    # Check for human handoff triggers
    if any(word in msg for word in ["mens", "verkoper", "bellen", "medewerker", "hulp van iemand"]):
        return (
            "🤝 Ik begrijp dat je graag met een verkoper wil spreken. "
            "Ik verbind je nu door naar ons team. Ze nemen zo snel mogelijk contact op!",
            True  # Trigger human handoff
        )

    # Greeting
    if any(word in msg for word in ["hallo", "hi", "hey", "goedemiddag", "goedemorgen"]):
        return (
            "🚗 Welkom bij Seldenrijk Auto!\n\n"
            "Ik ben je virtuele assistent en help je graag met:\n"
            "• Ons actuele aanbod bekijken\n"
            "• Proefrit plannen\n"
            "• Vragen over een specifieke auto\n"
            "• Financieringsmogelijkheden\n\n"
            "Wat kan ik voor je doen?",
            False
        )

    # Show cars/inventory
    if any(word in msg for word in ["auto", "aanbod", "beschikbaar", "voorraad", "autos"]):
        return (
            "🚙 **Ons actuele aanbod:**\n\n"
            "1️⃣ Volkswagen Golf (2022)\n"
            "   💶 €25.000 | ⛽ Benzine | 🛣️ 25.000 km\n\n"
            "2️⃣ Audi A4 (2021)\n"
            "   💶 €35.000 | ⛽ Diesel | 🛣️ 40.000 km\n\n"
            "3️⃣ BMW 3 Serie (2023)\n"
            "   💶 €40.000 | ⛽ Hybrid | 🛣️ 15.000 km\n\n"
            "4️⃣ Mercedes C-Klasse (2022)\n"
            "   💶 €45.000 | ⛽ Benzine | 🛣️ 30.000 km\n\n"
            "Typ een nummer voor meer details!",
            False
        )

    # Car details
    if "1" in msg or "golf" in msg:
        return (
            "🚗 **Volkswagen Golf (2022)**\n\n"
            "💶 Prijs: €25.000\n"
            "📅 Jaar: 2022\n"
            "⛽ Brandstof: Benzine (1.5 TSI)\n"
            "🚗 Kilometerstand: 25.000 km\n"
            "🎨 Kleur: Donkergrijs metallic\n"
            "⚙️ Vermogen: 150 PK\n"
            "🪑 Opties: Navigatie, Airco, Cruise control\n\n"
            "Interesse? Typ:\n"
            "• 'proefrit' om te plannen\n"
            "• 'financiering' voor betaalopties\n"
            "• 'verkoper' om direct te spreken",
            False
        )

    if "2" in msg or "audi" in msg:
        return (
            "🚗 **Audi A4 (2021)**\n\n"
            "💶 Prijs: €35.000\n"
            "📅 Jaar: 2021\n"
            "⛽ Brandstof: Diesel (2.0 TDI)\n"
            "🚗 Kilometerstand: 40.000 km\n"
            "🎨 Kleur: Zwart metallic\n"
            "⚙️ Vermogen: 190 PK\n"
            "🪑 Opties: Virtual Cockpit, LED, S-Line\n\n"
            "Interesse? Typ:\n"
            "• 'proefrit' om te plannen\n"
            "• 'financiering' voor betaalopties\n"
            "• 'verkoper' om direct te spreken",
            False
        )

    # Test drive booking
    if any(word in msg for word in ["proefrit", "proef", "testrit", "rijden"]):
        return (
            "📅 **Proefrit plannen**\n\n"
            "Super! Wanneer zou het je schikken?\n\n"
            "1️⃣ Morgen om 10:00\n"
            "2️⃣ Vrijdag om 14:00\n"
            "3️⃣ Zaterdag om 11:00\n"
            "4️⃣ Anders (zeg wanneer)\n\n"
            "Typ het nummer van je voorkeur!",
            False
        )

    # Financing
    if any(word in msg for word in ["prijs", "betalen", "financier", "lease", "maandelijks"]):
        return (
            "💰 **Financieringsmogelijkheden**\n\n"
            "We bieden flexibele opties:\n\n"
            "💵 **Contante betaling**\n"
            "   Direct eigenaar\n\n"
            "📊 **Financiering**\n"
            "   Vanaf 3.9% rente\n"
            "   Looptijd: 24-72 maanden\n\n"
            "🚗 **Lease**\n"
            "   Vanaf €299/maand\n"
            "   Zakelijk en privé\n\n"
            "Wil je een persoonlijk voorstel? Typ 'verkoper' om door te verbinden!",
            False
        )

    # Trade-in
    if any(word in msg for word in ["inruil", "oude auto", "verkopen"]):
        return (
            "🔄 **Auto inruilen**\n\n"
            "Natuurlijk! We nemen je huidige auto graag in.\n\n"
            "Wat heb ik nodig:\n"
            "• Merk en model\n"
            "• Bouwjaar\n"
            "• Kilometerstand\n"
            "• Algemene staat\n\n"
            "Typ bijvoorbeeld: 'VW Polo 2018, 60.000km, goede staat'\n\n"
            "Of spreek direct met een verkoper: typ 'verkoper'",
            False
        )

    # Default fallback
    return (
        f"Ik begrijp: '{user_message}'\n\n"
        "Typ:\n"
        "• 'auto' voor ons aanbod\n"
        "• 'proefrit' om te plannen\n"
        "• 'verkoper' voor persoonlijk advies\n"
        "• 'hallo' om opnieuw te beginnen",
        False
    )


# ============================================================================
# CHATWOOT INTEGRATION - Bot-to-Human Handoff
# ============================================================================

async def create_chatwoot_conversation(from_number: str, message: str) -> Optional[int]:
    """
    Create conversation in Chatwoot when human handoff is triggered.

    Returns conversation_id or None if failed.
    """
    if not CHATWOOT_API_KEY:
        logger.warning("Chatwoot not configured, skipping human handoff")
        return None

    try:
        async with httpx.AsyncClient() as client:
            # Create contact (or get existing)
            contact_response = await client.post(
                f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/contacts",
                headers={
                    "api_access_token": CHATWOOT_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "inbox_id": CHATWOOT_INBOX_ID,
                    "name": f"Customer {from_number[-4:]}",  # Last 4 digits
                    "phone_number": from_number.replace("whatsapp:", ""),
                    "identifier": from_number
                }
            )

            if contact_response.status_code not in [200, 201]:
                logger.error(f"Failed to create contact: {contact_response.text}")
                return None

            contact_data = contact_response.json()
            contact_id = contact_data.get("id") or contact_data.get("payload", {}).get("contact", {}).get("id")

            # Create conversation
            conv_response = await client.post(
                f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations",
                headers={
                    "api_access_token": CHATWOOT_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "inbox_id": CHATWOOT_INBOX_ID,
                    "contact_id": contact_id,
                    "status": "open",
                    "message": {
                        "content": f"🤖→🤝 Human handoff requested\n\nCustomer message:\n{message}",
                        "private": False
                    }
                }
            )

            if conv_response.status_code not in [200, 201]:
                logger.error(f"Failed to create conversation: {conv_response.text}")
                return None

            conv_data = conv_response.json()
            conversation_id = conv_data.get("id")

            logger.info(f"✅ Chatwoot conversation created: {conversation_id}")
            return conversation_id

    except Exception as e:
        logger.error(f"Chatwoot error: {str(e)}")
        return None


async def send_chatwoot_message(conversation_id: int, message: str) -> bool:
    """Send message from bot to Chatwoot conversation."""
    if not CHATWOOT_API_KEY:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages",
                headers={
                    "api_access_token": CHATWOOT_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "content": message,
                    "message_type": "outgoing",
                    "private": False
                }
            )
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Failed to send Chatwoot message: {str(e)}")
        return False


# ============================================================================
# TWILIO WEBHOOK - Incoming WhatsApp Messages
# ============================================================================

@app.post("/webhook/twilio", response_class=PlainTextResponse)
async def twilio_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Twilio Sandbox webhook - receives WhatsApp messages.

    Flow:
    1. Receive message from Twilio
    2. Check if human handoff is active for this user
    3. If yes → forward to Chatwoot
    4. If no → process with chatbot
    5. Send response back via Twilio
    """

    logger.info(f"📨 Received: {Body} | From: {From}")

    # Check if this user is in human handoff mode
    if From in human_handoff_sessions:
        # Forward to Chatwoot (human handles it)
        logger.info(f"🤝 Human handoff active for {From}, forwarding to Chatwoot")

        # Send acknowledgment to user
        response_text = "✅ Je bent verbonden met een verkoper. Ze reageren zo snel mogelijk!"
    else:
        # Process with chatbot
        response_text, needs_handoff = get_bot_response(Body, From)

        # If human handoff is triggered
        if needs_handoff:
            # Create Chatwoot conversation
            conv_id = await create_chatwoot_conversation(From, Body)

            if conv_id:
                # Mark this user as in human handoff mode
                human_handoff_sessions.add(From)
                logger.info(f"🤝 Human handoff activated for {From}")
            else:
                # Chatwoot failed, fallback message
                response_text += "\n\n(Let op: automatisch doorverbinden niet beschikbaar, een verkoper neemt zo contact op)"

    # Send response via Twilio
    try:
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=From,
            body=response_text
        )

        logger.info(f"✅ Response sent: {message.sid}")

        return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"❌ Twilio error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHATWOOT WEBHOOK - Dealer Responses
# ============================================================================

@app.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    """
    Chatwoot webhook - receives dealer responses.

    Flow:
    1. Dealer responds in Chatwoot
    2. Webhook receives message
    3. Send message to customer via Twilio WhatsApp
    """

    try:
        payload = await request.json()

        event = payload.get("event")

        # Only handle outgoing messages from dealer
        if event == "message_created":
            message_data = payload.get("message", {})

            # Skip bot messages
            if message_data.get("message_type") == "outgoing" and message_data.get("sender", {}).get("type") == "agent_bot":
                return {"status": "ignored", "reason": "bot message"}

            # Only process agent messages
            if message_data.get("sender", {}).get("type") != "user":
                content = message_data.get("content")
                conversation = payload.get("conversation", {})

                # Get customer phone number
                contact = conversation.get("meta", {}).get("sender", {})
                phone_number = contact.get("phone_number") or contact.get("identifier")

                if phone_number and content:
                    # Ensure phone number has whatsapp: prefix
                    if not phone_number.startswith("whatsapp:"):
                        phone_number = f"whatsapp:{phone_number}"

                    # Send via Twilio
                    message = twilio_client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        to=phone_number,
                        body=f"👤 Verkoper: {content}"
                    )

                    logger.info(f"✅ Dealer message forwarded to {phone_number}")

                    return {"status": "sent", "message_sid": message.sid}

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Chatwoot webhook error: {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Seldenrijk Auto WhatsApp Bot",
        "twilio_configured": bool(TWILIO_ACCOUNT_SID),
        "chatwoot_configured": bool(CHATWOOT_API_KEY),
        "sandbox_number": TWILIO_WHATSAPP_NUMBER
    }


@app.get("/health")
async def health():
    """Railway health check"""
    return {"status": "healthy"}


@app.post("/reset-handoff/{phone_number}")
async def reset_handoff(phone_number: str):
    """
    Reset human handoff mode for a phone number.
    Useful for testing.
    """
    full_number = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number

    if full_number in human_handoff_sessions:
        human_handoff_sessions.remove(full_number)
        return {"status": "reset", "phone_number": full_number}

    return {"status": "not_found", "phone_number": full_number}


@app.get("/active-handoffs")
async def active_handoffs():
    """View all active human handoffs"""
    return {
        "count": len(human_handoff_sessions),
        "sessions": list(human_handoff_sessions)
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
