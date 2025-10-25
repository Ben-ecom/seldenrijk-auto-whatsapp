# TWILIO WHATSAPP INTEGRATION ARCHITECTURE

## SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TWILIO WHATSAPP INTEGRATION                  │
│                         (Day 2 Implementation)                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   WhatsApp      │
│   User          │  "Ik zoek een Volkswagen Golf"
│  +31612345678   │
└────────┬────────┘
         │
         │ WhatsApp Message
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         TWILIO PLATFORM                             │
│  - Receives WhatsApp message                                        │
│  - Adds metadata (MessageSid, ProfileName, etc.)                    │
│  - Signs request with HMAC-SHA256                                   │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ POST /webhooks/twilio/whatsapp
         │ X-Twilio-Signature: <base64_signature>
         │ Form Data: { MessageSid, From, To, Body, ProfileName }
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI WEBHOOK ENDPOINT                         │
│                  app/api/webhooks.py                                │
│                                                                     │
│  1. SECURITY VALIDATION                                             │
│     ✓ Verify HMAC-SHA256 signature                                 │
│     ✓ Rate limit: 50 req/min per IP                                │
│                                                                     │
│  2. DEDUPLICATION CHECK                                             │
│     ✓ Redis cache: twilio:message:{MessageSid}                     │
│     ✓ TTL: 1 hour                                                   │
│                                                                     │
│  3. PAYLOAD TRANSFORMATION                                          │
│     Twilio Format → Chatwoot-Compatible Format                     │
│     {                                                               │
│       "id": "SM123456789",                                          │
│       "source": "twilio",  ← CRITICAL FIELD                        │
│       "sender": { "phone_number": "+31612345678" },                │
│       "content": "Ik zoek een Volkswagen Golf"                     │
│     }                                                               │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ Celery task queued
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     CELERY WORKER                                   │
│               app/tasks/process_message.py                          │
│                                                                     │
│  process_message_async(payload)                                    │
│    ↓                                                                │
│  Create ConversationState(source="twilio")                         │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ Execute LangGraph workflow
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH MULTI-AGENT WORKFLOW                    │
│              app/orchestration/graph_builder.py                     │
│                                                                     │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐  │
│  │ Router Agent │ → │ Extraction Agent │ → │ Conversation Agent│  │
│  │ (Intent)     │    │ (Extract data)  │    │ (Generate reply) │  │
│  └──────────────┘    └─────────────────┘    └──────────────────┘  │
│         ↓                                             ↓            │
│  ┌──────────────┐                            ┌──────────────────┐  │
│  │  CRM Agent   │                            │  Response Ready  │  │
│  │ (Update DB)  │                            │  "Bedankt voor..." │
│  └──────────────┘                            └──────────────────┘  │
│                                                       ↓            │
│  ZERO CHANGES TO EXISTING AGENTS ✅                              │
└───────────────────────────────────────────────────────┬─────────────┘
                                                        │
                                                        │ final_state
                                                        ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    RESPONSE ROUTING LOGIC                           │
│               app/tasks/process_message.py                          │
│                                                                     │
│  Check: final_state["source"]                                      │
│                                                                     │
│  if source == "twilio":                                             │
│      await _send_to_twilio(phone_number, response_text)            │
│  elif source == "waha":                                             │
│      await _send_to_waha(chat_id, response_text)                   │
│  elif source == "chatwoot":                                         │
│      await _send_to_chatwoot(conversation_id, response_text)       │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ _send_to_twilio() called
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   TWILIO SERVICE CLIENT                             │
│             app/integrations/twilio_client.py                       │
│                                                                     │
│  send_message(to_number="+31612345678", message="Bedankt...")      │
│                                                                     │
│  1. RATE LIMITING CHECK                                             │
│     ✓ Max 80 messages/second                                        │
│     ✓ Sliding window (1 second)                                     │
│                                                                     │
│  2. RETRY LOGIC                                                     │
│     ✓ Max 3 attempts                                                │
│     ✓ Exponential backoff (1s, 2s, 4s)                             │
│     ✓ Skip retry on permanent errors (21211, 21612)                │
│                                                                     │
│  3. TWILIO REST API CALL                                            │
│     POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages │
│     {                                                               │
│       "From": "whatsapp:+14155238886",                              │
│       "To": "whatsapp:+31612345678",                                │
│       "Body": "Bedankt voor uw interesse! Welke auto zoekt u?"     │
│     }                                                               │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ Response: { "sid": "SM987654321", "status": "queued" }
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         TWILIO PLATFORM                             │
│  - Queues message for delivery                                      │
│  - Sends to WhatsApp Business API                                   │
│  - Handles delivery status updates                                  │
└────────┬────────────────────────────────────────────────────────────┘
         │
         │ WhatsApp Business API
         ↓
┌─────────────────┐
│   WhatsApp      │
│   User          │  ← "Bedankt voor uw interesse! Welke auto zoekt u?"
│  +31612345678   │
└─────────────────┘
```

---

## DATA FLOW DETAILS

### 1. INCOMING MESSAGE (Twilio → FastAPI)

```
TWILIO WEBHOOK PAYLOAD:
{
  "MessageSid": "SM123456789",
  "From": "whatsapp:+31612345678",
  "To": "whatsapp:+31850000000",
  "Body": "Ik zoek een Volkswagen Golf",
  "ProfileName": "John Doe",
  "NumMedia": "0",
  "MediaContentType0": "",
  "MediaUrl0": ""
}

↓ TRANSFORM ↓

CHATWOOT-COMPATIBLE PAYLOAD:
{
  "id": "SM123456789",
  "conversation": {
    "id": "whatsapp:+31612345678"
  },
  "sender": {
    "id": "whatsapp:+31612345678",
    "name": "John Doe",
    "phone_number": "+31612345678"
  },
  "content": "Ik zoek een Volkswagen Golf",
  "message_type": "incoming",
  "channel": "whatsapp",
  "source": "twilio"  ← ROUTING KEY
}
```

---

### 2. LANGGRAPH PROCESSING (No Changes)

```
CONVERSATION STATE:
{
  "message_id": "SM123456789",
  "conversation_id": "whatsapp:+31612345678",
  "content": "Ik zoek een Volkswagen Golf",
  "sender_name": "John Doe",
  "sender_phone": "+31612345678",
  "source": "twilio",  ← ROUTING KEY
  "conversation_history": [],
  ...
}

↓ ROUTER AGENT ↓

{
  "router_output": {
    "intent": "car_inquiry",
    "confidence": 0.95,
    "next_agent": "extraction"
  }
}

↓ EXTRACTION AGENT ↓

{
  "extraction_output": {
    "car_make": "Volkswagen",
    "car_model": "Golf",
    "intent": "car_inquiry"
  }
}

↓ CONVERSATION AGENT ↓

{
  "conversation_output": {
    "response_text": "Bedankt voor uw interesse! Welke auto zoekt u?",
    "sentiment": "positive",
    "should_escalate": false
  }
}

↓ CRM AGENT ↓

{
  "crm_output": {
    "contact_created": true,
    "contact_id": 123,
    "lead_created": true
  }
}
```

---

### 3. OUTGOING MESSAGE (FastAPI → Twilio)

```
ROUTING DECISION:
if source == "twilio":
    _send_to_twilio("+31612345678", "Bedankt...")

↓

TWILIO API REQUEST:
POST https://api.twilio.com/2010-04-01/Accounts/ACtest123/Messages.json
Authorization: Basic <base64(SID:AUTH_TOKEN)>
{
  "From": "whatsapp:+14155238886",
  "To": "whatsapp:+31612345678",
  "Body": "Bedankt voor uw interesse! Welke auto zoekt u?"
}

↓

TWILIO API RESPONSE:
{
  "sid": "SM987654321",
  "status": "queued",
  "to": "whatsapp:+31612345678",
  "from": "whatsapp:+14155238886",
  "body": "Bedankt voor uw interesse! Welke auto zoekt u?",
  "price": null,
  "price_unit": "USD"
}

↓

RETURNED TO CALLER:
{
  "status": "sent",
  "message_sid": "SM987654321",
  "to": "+31612345678",
  "twilio_status": "queued"
}
```

---

## SECURITY LAYERS

```
┌─────────────────────────────────────────────────────────────┐
│                     SECURITY STACK                          │
└─────────────────────────────────────────────────────────────┘

LAYER 1: SIGNATURE VERIFICATION (HMAC-SHA256)
┌──────────────────────────────────────────┐
│ Twilio signs: URL + sorted(params)      │
│ We compute: HMAC-SHA256(auth_token, ...)│
│ Compare: constant-time comparison        │
│ Result: 403 Forbidden if mismatch        │
└──────────────────────────────────────────┘
         ↓ PASS
LAYER 2: RATE LIMITING
┌──────────────────────────────────────────┐
│ Max: 50 requests/minute per IP           │
│ Implementation: slowapi + Redis          │
│ Result: 429 Too Many Requests if exceeded│
└──────────────────────────────────────────┘
         ↓ PASS
LAYER 3: DEDUPLICATION
┌──────────────────────────────────────────┐
│ Check: twilio:message:{MessageSid}       │
│ Cache: Redis with 1-hour TTL             │
│ Result: Ignore if duplicate              │
└──────────────────────────────────────────┘
         ↓ PASS
LAYER 4: INPUT VALIDATION
┌──────────────────────────────────────────┐
│ Validate: phone number format (E.164)    │
│ Validate: message length (<1600 chars)   │
│ Sanitize: XSS prevention                 │
└──────────────────────────────────────────┘
         ↓ PASS
┌─────────────────────────────────────────┐
│         SECURE PROCESSING               │
└─────────────────────────────────────────┘
```

---

## ERROR HANDLING & RETRY

```
┌─────────────────────────────────────────────────────────────┐
│                   ERROR HANDLING FLOW                       │
└─────────────────────────────────────────────────────────────┘

TWILIO API CALL
       ↓
┌──────────────┐
│  Attempt 1   │
└──────┬───────┘
       │
       ├─ SUCCESS → Return { status: "sent", message_sid: "..." }
       │
       ├─ PERMANENT ERROR (21211, 21612, 21614)
       │    ↓
       │  Log error + Return { status: "failed", error: "..." }
       │  (NO RETRY)
       │
       └─ TEMPORARY ERROR (500, timeout, network)
            ↓
       ┌──────────────┐
       │  Wait 1s     │
       │  Attempt 2   │
       └──────┬───────┘
              │
              ├─ SUCCESS → Return { status: "sent", ... }
              │
              └─ STILL FAILING
                   ↓
              ┌──────────────┐
              │  Wait 2s     │
              │  Attempt 3   │
              └──────┬───────┘
                     │
                     ├─ SUCCESS → Return { status: "sent", ... }
                     │
                     └─ FINAL FAILURE
                          ↓
                        Return {
                          status: "failed",
                          error: "...",
                          attempts: 3
                        }
                          ↓
                        Raise exception → Celery retry
```

---

## RATE LIMITING

```
┌─────────────────────────────────────────────────────────────┐
│               RATE LIMITING IMPLEMENTATION                  │
└─────────────────────────────────────────────────────────────┘

SLIDING WINDOW (1 second):
┌─────────────────────────────────────────────────────────────┐
│ Timestamp buffer: [t1, t2, t3, ..., t80]                   │
│                                                             │
│ On each send:                                               │
│   1. Remove timestamps older than 1 second                  │
│   2. Check: len(buffer) < 80?                               │
│   3. If YES: Add current timestamp, send message            │
│   4. If NO:  Return { status: "rate_limited" }              │
└─────────────────────────────────────────────────────────────┘

EXAMPLE:
Time: 12:00:00.000
Buffer: [12:00:00.010, 12:00:00.020, ..., 12:00:00.800]  ← 80 messages
New message arrives at 12:00:00.850

Step 1: Remove old timestamps
  12:00:00.010 < (12:00:00.850 - 1s) → REMOVE
  ...
  Buffer after cleanup: [12:00:00.020, ..., 12:00:00.800]  ← 79 messages

Step 2: Check limit
  len(buffer) = 79 < 80 → OK

Step 3: Add new timestamp
  Buffer: [12:00:00.020, ..., 12:00:00.800, 12:00:00.850]  ← 80 messages

Step 4: Send message
  Return { status: "sent", message_sid: "..." }
```

---

## MONITORING POINTS

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING METRICS                       │
└─────────────────────────────────────────────────────────────┘

PROMETHEUS METRICS:
┌──────────────────────────────────────────────────────────┐
│ webhook_requests_total{source="twilio", status="received"} │
│ webhook_requests_total{source="twilio", status="queued"}   │
│ webhook_requests_total{source="twilio", status="duplicate"}│
│ webhook_requests_total{source="twilio", status="error"}    │
│ webhook_signature_errors_total{source="twilio"}            │
└──────────────────────────────────────────────────────────┘

CUSTOM LOGS:
┌──────────────────────────────────────────────────────────┐
│ INFO: "Twilio webhook received" { message_sid, from, ... }│
│ INFO: "Message sent to Twilio" { phone, message_sid }    │
│ WARNING: "Twilio rate limit reached" { phone, error }    │
│ ERROR: "Twilio send failed" { phone, error, attempts }   │
└──────────────────────────────────────────────────────────┘

ALERTS:
┌──────────────────────────────────────────────────────────┐
│ ⚠️  Rate limit exceeded > 5/min                          │
│ ⚠️  Send failures > 5%                                    │
│ ⚠️  Signature errors > 1/min (possible attack)           │
└──────────────────────────────────────────────────────────┘
```

---

## DEPLOYMENT CHECKLIST

```
┌─────────────────────────────────────────────────────────────┐
│                  PRODUCTION DEPLOYMENT                      │
└─────────────────────────────────────────────────────────────┘

ENVIRONMENT VARIABLES:
[x] TWILIO_ACCOUNT_SID
[x] TWILIO_AUTH_TOKEN
[x] TWILIO_WHATSAPP_NUMBER
[x] REDIS_HOST
[x] REDIS_PORT

INFRASTRUCTURE:
[ ] Deploy to Railway
[ ] Configure public webhook URL (https://...)
[ ] Set up SSL/TLS certificate
[ ] Configure Redis (Railway addon)
[ ] Set up Celery worker

TWILIO CONFIGURATION:
[ ] Verify WhatsApp sender number
[ ] Configure webhook URL in Twilio console
[ ] Test webhook with Twilio debugger
[ ] Enable webhook retries (optional)

MONITORING:
[ ] Set up Prometheus metrics
[ ] Configure Grafana dashboards
[ ] Set up alerting (PagerDuty/Slack)
[ ] Enable structured logging

TESTING:
[ ] Send test message from WhatsApp
[ ] Verify signature validation
[ ] Test rate limiting (load test)
[ ] Test error recovery (network failures)
```

---

**Status:** Day 2 Complete ✅
**Next:** [DAY-3-DEPLOYMENT.md](./DAY-3-DEPLOYMENT.md)
