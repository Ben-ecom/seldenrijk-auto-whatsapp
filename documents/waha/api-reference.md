# WAHA API Reference

WAHA (WhatsApp HTTP API) - Open-source WhatsApp Business API for self-hosted deployments.

## Overview

WAHA provides HTTP API endpoints for WhatsApp operations without official Business API costs.

**GitHub:** https://github.com/devlikeapro/waha
**Docker Image:** devlikeapro/waha:latest (or devlikeapro/waha:arm for ARM64)

## Base URL

```
http://waha:3000  # Docker service name
http://localhost:3000  # Local development
```

## Authentication

WAHA supports API key authentication (optional):

```http
Headers:
  X-Api-Key: YOUR_API_KEY
```

For local/Docker deployments, authentication is often disabled.

## Sessions

WAHA uses "sessions" to manage multiple WhatsApp accounts.

**Default session:** `default`

### Start Session

```http
POST /api/sessions/start
```

**Payload:**
```json
{
  "name": "default",
  "config": {
    "proxy": null,
    "noweb": {
      "store": {
        "enabled": true,
        "fullSync": false
      }
    }
  }
}
```

### Get Session Status

```http
GET /api/sessions/{session}
```

**Response:**
```json
{
  "name": "default",
  "status": "WORKING",
  "me": {
    "id": "31612345678@c.us",
    "pushName": "Your Name"
  }
}
```

**Session States:**
- `STOPPED`: Not running
- `STARTING`: Initializing
- `SCAN_QR_CODE`: Waiting for QR scan
- `WORKING`: Connected and ready
- `FAILED`: Connection failed

### Stop Session

```http
POST /api/sessions/stop
```

**Payload:**
```json
{
  "name": "default"
}
```

## Sending Messages

### Send Text Message

```http
POST /api/sendText
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "31612345678@c.us",
  "text": "Hello from WAHA!"
}
```

**Response:**
```json
{
  "id": "true_31612345678@c.us_3EB0...",
  "timestamp": 1673456789,
  "ack": 0,
  "ackName": "PENDING"
}
```

**ACK States:**
- `0` (PENDING): Message sent to server
- `1` (SERVER): Message received by server
- `2` (DEVICE): Message delivered to device
- `3` (READ): Message read by recipient
- `4` (PLAYED): Voice/video played

### Send Media Message

```http
POST /api/sendImage
POST /api/sendFile
POST /api/sendVoice
POST /api/sendVideo
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "31612345678@c.us",
  "file": {
    "mimetype": "image/jpeg",
    "filename": "photo.jpg",
    "data": "base64_encoded_data"
  },
  "caption": "Optional caption"
}
```

### Send Location

```http
POST /api/sendLocation
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "31612345678@c.us",
  "latitude": 52.3676,
  "longitude": 4.9041,
  "title": "Amsterdam"
}
```

## Receiving Messages (Webhooks)

WAHA sends webhooks for incoming messages and events.

### Webhook Configuration

Set webhook URL in WAHA environment:

```bash
WHATSAPP_HOOK_URL=http://your-api:8000/webhooks/waha
WHATSAPP_HOOK_EVENTS=message,message.any,session.status
```

### Webhook Event: message

```json
{
  "event": "message",
  "session": "default",
  "me": {
    "id": "31628129028@c.us",
    "pushName": "Your Business"
  },
  "payload": {
    "id": "false_31612345678@c.us_AC...",
    "timestamp": 1673456789,
    "from": "31612345678@c.us",
    "fromMe": false,
    "to": "31628129028@c.us",
    "body": "I'm looking for a car",
    "hasMedia": false,
    "ack": 1,
    "ackName": "SERVER",
    "_data": {
      "notifyName": "John Doe"
    }
  },
  "engine": "WEBJS",
  "environment": {
    "version": "2025.10.1",
    "tier": "CORE"
  }
}
```

### Webhook Event: message.any

**Note:** WAHA sends BOTH `message` and `message.any` for the same message!

```json
{
  "event": "message.any",
  "session": "default",
  "payload": {
    "id": "false_31612345678@c.us_AC...",
    "from": "31612345678@c.us",
    "fromMe": false,
    "body": "I'm looking for a car"
  }
}
```

**⚠️ Important:** Filter webhooks to process only ONE event type to avoid duplicates!

### Webhook Event: session.status

```json
{
  "event": "session.status",
  "session": "default",
  "me": {
    "id": "31628129028@c.us"
  },
  "status": "WORKING"
}
```

### Filtering Outgoing Messages

Messages sent BY your system have `fromMe: true`:

```python
if message_data.get("fromMe") is True:
    # Ignore - this is our own message
    return
```

### Filtering Status Broadcasts

WhatsApp Status updates come from `status@broadcast`:

```python
if message_data.get("from") == "status@broadcast":
    # Ignore - this is a WhatsApp Status
    return
```

## Chat Operations

### Get Chats

```http
GET /api/{session}/chats
```

**Response:**
```json
[
  {
    "id": "31612345678@c.us",
    "name": "John Doe",
    "isGroup": false,
    "timestamp": 1673456789,
    "unreadCount": 2
  }
]
```

### Get Messages from Chat

```http
GET /api/{session}/chats/{chatId}/messages?limit=50
```

**Response:**
```json
[
  {
    "id": "false_31612345678@c.us_AC...",
    "body": "Hello",
    "fromMe": false,
    "timestamp": 1673456789
  }
]
```

### Mark as Read

```http
POST /api/sendSeen
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "31612345678@c.us"
}
```

## Contact Operations

### Get Contact

```http
GET /api/{session}/contacts/{contactId}
```

**Response:**
```json
{
  "id": "31612345678@c.us",
  "name": "John Doe",
  "pushname": "John",
  "isMyContact": true
}
```

### Check if Number Exists on WhatsApp

```http
POST /api/checkNumberStatus
```

**Payload:**
```json
{
  "session": "default",
  "phone": "31612345678"
}
```

**Response:**
```json
{
  "numberExists": true,
  "chatId": "31612345678@c.us"
}
```

## Presence & Typing

### Set Presence

```http
POST /api/sendPresenceUpdate
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "31612345678@c.us",
  "presence": "composing"
}
```

**Presence Types:**
- `available`: Online
- `unavailable`: Offline
- `composing`: Typing...
- `recording`: Recording audio
- `paused`: Stopped typing

## QR Code

### Get QR Code

```http
GET /api/{session}/auth/qr
```

Returns QR code image (PNG) for scanning with WhatsApp mobile app.

## Groups

### Create Group

```http
POST /api/{session}/groups
```

**Payload:**
```json
{
  "name": "My Group",
  "participants": ["31612345678@c.us", "31687654321@c.us"]
}
```

### Send Group Message

```http
POST /api/sendText
```

**Payload:**
```json
{
  "session": "default",
  "chatId": "123456789@g.us",
  "text": "Hello group!"
}
```

## Chat ID Format

WAHA uses specific ID formats:

- **Individual:** `31612345678@c.us`
- **Group:** `123456789@g.us`
- **Status:** `status@broadcast`

**Extracting Phone Number:**
```python
phone_number = chat_id.replace("@c.us", "")
# "31612345678@c.us" -> "31612345678"
```

## Docker Deployment

### Docker Compose

```yaml
services:
  waha:
    image: devlikeapro/waha:arm  # or :latest for x86_64
    ports:
      - "3000:3000"
    environment:
      - WHATSAPP_HOOK_URL=http://seldenrijk-api:8000/webhooks/waha
      - WHATSAPP_HOOK_EVENTS=message,message.any,session.status
      - WAHA_LOG_LEVEL=info
    volumes:
      - waha_data:/app/.wwebjs_auth
    networks:
      - seldenrijk-network
```

### Environment Variables

```bash
# Webhook configuration
WHATSAPP_HOOK_URL=http://your-api:8000/webhooks/waha
WHATSAPP_HOOK_EVENTS=message,session.status

# API Key (optional)
WHATSAPP_API_KEY=your-secret-key

# Log level
WAHA_LOG_LEVEL=info  # debug, info, warn, error

# Session store
WHATSAPP_RESTART_ALL_SESSIONS=true
```

## Common Integration Patterns

### Message Processing Workflow

```python
@app.post("/webhooks/waha")
async def waha_webhook(request: Request):
    payload = await request.json()

    event_type = payload.get("event")

    # Filter event type
    if event_type != "message":
        return {"status": "ignored"}

    message_data = payload.get("payload", {})

    # Filter outgoing messages
    if message_data.get("fromMe") is True:
        return {"status": "ignored"}

    # Filter status broadcasts
    if message_data.get("from") == "status@broadcast":
        return {"status": "ignored"}

    # Process message
    chat_id = message_data.get("from")
    content = message_data.get("body")

    # Send to AI/workflow
    response = await process_message(chat_id, content)

    # Send response via WAHA
    await send_waha_message(chat_id, response)

    return {"status": "processed"}

async def send_waha_message(chat_id: str, text: str):
    url = "http://waha:3000/api/sendText"
    payload = {
        "session": "default",
        "chatId": chat_id,
        "text": text
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
```

### Session Health Check

```python
async def check_waha_status():
    url = "http://waha:3000/api/sessions/default"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

        if data.get("status") == "WORKING":
            return True
        elif data.get("status") == "SCAN_QR_CODE":
            # Get QR code
            qr_url = "http://waha:3000/api/default/auth/qr"
            print(f"Scan QR code: {qr_url}")
            return False
        else:
            return False
```

## Error Handling

### Common Errors

**Session Not Found:**
```json
{
  "error": "Session 'default' not found"
}
```

**Session Not Connected:**
```json
{
  "error": "Session not ready",
  "status": "STOPPED"
}
```

**Invalid Chat ID:**
```json
{
  "error": "Chat not found"
}
```

### Best Practices

1. **Check session status** before sending messages
2. **Filter webhook events** to avoid duplicates (use only `message`, not `message.any`)
3. **Ignore outgoing messages** (`fromMe: true`)
4. **Ignore status broadcasts** (`status@broadcast`)
5. **Handle connection drops** - implement reconnection logic
6. **Store session data** in volumes for persistence

## Rate Limits

WhatsApp enforces rate limits:
- **~80 messages per minute** per number
- **Avoid spam** - wait 1-2 seconds between messages
- **Use message queues** for bulk sending

## Testing

### Test Session Status

```bash
curl http://localhost:3000/api/sessions/default
```

### Test Send Message

```bash
curl -X POST http://localhost:3000/api/sendText \
  -H "Content-Type: application/json" \
  -d '{
    "session": "default",
    "chatId": "31612345678@c.us",
    "text": "Test message from WAHA"
  }'
```

### Test Webhook

```bash
# Simulate webhook
curl -X POST http://localhost:8000/webhooks/waha \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message",
    "session": "default",
    "payload": {
      "id": "test_message",
      "from": "31612345678@c.us",
      "fromMe": false,
      "body": "Test message",
      "_data": {"notifyName": "Test User"}
    }
  }'
```

## Troubleshooting

### Session Stuck in STARTING

```bash
# Restart session
curl -X POST http://localhost:3000/api/sessions/stop \
  -H "Content-Type: application/json" \
  -d '{"name": "default"}'

curl -X POST http://localhost:3000/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"name": "default"}'
```

### Messages Not Sending

1. Check session status: `GET /api/sessions/default`
2. Verify chat ID format: `31612345678@c.us`
3. Check WhatsApp number is registered
4. Verify webhook URL is accessible

### Duplicate Messages

Filter webhooks to use only `message` event:

```python
if event_type != "message":
    return {"status": "ignored"}
```

## Source

Documentation compiled from:
- https://github.com/devlikeapro/waha
- https://waha.devlike.pro/docs/
- WAHA API examples and GitHub issues
