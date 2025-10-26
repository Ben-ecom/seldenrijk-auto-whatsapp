# Phase 1: System Architecture Analysis
## WAHA to Twilio Migration - Deep Planning

**Date:** 2025-10-26
**Status:** 🔍 Analysis Complete
**Migration Type:** WhatsApp Provider Replacement (WAHA → Twilio)
**Risk Level:** Medium (Existing Twilio code present, clear migration path)

---

## 1. EXECUTIVE SUMMARY

### Current State
- **Complete backend system** in `app/` folder with 53 Python files
- **WAHA integration** for WhatsApp messaging (Docker-based, €135/month)
- **LangGraph orchestration** with multiple specialized agents
- **Supabase database** with PGVector for RAG
- **Chatwoot CRM** integration for human handoff
- **Redis** for caching and deduplication
- **Celery** for async task processing

### Target State
- **Replace WAHA** with Twilio WhatsApp Business API (€60/month, 99.95% SLA)
- **Keep all existing** agent logic, database, Chatwoot integration
- **Add HubSpot CRM** integration (from PRD)
- **Add Google Calendar** integration (from PRD)
- **Remove** simple `main.py` demo (consolidate into app/)
- **Zero downtime** migration strategy

### Cost & Business Impact
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **WhatsApp Cost** | €135/month | €60/month | -€75/month (-56%) |
| **Uptime SLA** | ~95% (Docker) | 99.95% (Twilio) | +4.95% |
| **Lead Tracking** | Chatwoot only | Chatwoot + HubSpot | Enhanced |
| **Appointment Booking** | Manual | Automated (Google Calendar) | +95% faster |

---

## 2. SYSTEM ARCHITECTURE ANALYSIS

### 2.1 Current Architecture Map

```
┌─────────────────────────────────────────────────────────────┐
│                  CURRENT SYSTEM ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  WhatsApp User  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     HTTP Webhook      ┌──────────────────┐
│  WAHA Container │ ──────────────────────▶│ FastAPI Webhooks │
│ (Docker/Railway)│                        │  /webhooks/waha  │
└─────────────────┘                        └────────┬─────────┘
                                                    │
                           ┌────────────────────────┴────────────────────┐
                           │         Redis Deduplication Check           │
                           └────────────────────────┬────────────────────┘
                                                    │
                           ┌────────────────────────▼────────────────────┐
                           │       Celery Task Queue (Async)             │
                           │     process_message_async.delay()           │
                           └────────────────────────┬────────────────────┘
                                                    │
┌───────────────────────────────────────────────────▼─────────────────────────────┐
│                        LANGGRAPH AGENT WORKFLOW                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ RAG Agent    │───│ CRM Agent    │───│ Expertise    │───│ Fallback     │   │
│  │ (Supabase    │   │ (Lead Score) │   │ Agent        │   │ Agent        │   │
│  │  PGVector)   │   │              │   │              │   │              │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   │
│                                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                      │
│  │ Escalation   │   │ Documentation│   │ Others...    │                      │
│  │ Router       │   │ Agent        │   │              │                      │
│  └──────────────┘   └──────────────┘   └──────────────┘                      │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
         ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
         │ Send via WAHA    │ │ Sync to      │ │ Log to Supabase │
         │ _send_to_waha()  │ │ Chatwoot     │ │ conversations   │
         └──────────────────┘ └──────────────┘ └─────────────────┘
```

### 2.2 Component Inventory

#### Core Components (KEEP - No Changes)
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| **LangGraph Workflow** | `app/orchestration/` | Agent coordination | ✅ Keep |
| **Agent System** | `app/agents/` | 8+ specialized agents | ✅ Keep |
| **RAG System** | `app/rag/` | PGVector semantic search | ✅ Keep |
| **Supabase DB** | `app/database/supabase_pool.py` | PostgreSQL + PGVector | ✅ Keep |
| **Chatwoot Integration** | `app/integrations/chatwoot_sync.py` | CRM sync | ✅ Keep |
| **Redis Cache** | Throughout | Deduplication | ✅ Keep |
| **Celery Workers** | `app/celery_app.py` | Async processing | ✅ Keep |
| **Monitoring** | `app/monitoring/` | Logs, metrics | ✅ Keep |

#### WAHA-Specific Components (REPLACE with Twilio)
| Component | Location | WAHA Code | Action Required |
|-----------|----------|-----------|-----------------|
| **WAHA Webhook** | `app/api/webhooks.py:176-296` | `/webhooks/waha` endpoint | 🔄 Replace with Twilio |
| **WAHA Send Function** | `app/tasks/process_message.py` | `_send_to_waha()` | 🔄 Replace with `_send_to_twilio()` |
| **WAHA Auth** | `app/security/webhook_auth.py` | `verify_waha_signature()` | ✅ Already has `validate_twilio_webhook()` |
| **WAHA Forward** | `app/api/webhooks.py:383-493` | `_forward_chatwoot_to_waha()` | 🔄 Replace with `_forward_chatwoot_to_twilio()` |
| **WAHA Sync** | `app/integrations/chatwoot_sync.py` | `sync_waha_to_chatwoot()` | 🔄 Replace with `sync_twilio_to_chatwoot()` |
| **WAHA Escalation** | `app/agents/escalation_router.py` | Direct WAHA API call | 🔄 Replace with Twilio |

#### NEW Components (ADD per PRD)
| Component | Purpose | Status | Priority |
|-----------|---------|--------|----------|
| **HubSpot Integration** | Sales CRM, deal tracking | ❌ Not exists | 🔴 High |
| **Google Calendar** | Appointment scheduling | ❌ Not exists | 🔴 High |
| **Twilio Client** | WhatsApp message sending | ⚠️ Partial (webhook only) | 🔴 High |

---

## 3. WAHA DEPENDENCY MAP

### 3.1 Direct WAHA Dependencies

#### File: `app/api/webhooks.py`
**Lines 176-296: WAHA Webhook Endpoint**
```python
@router.post("/waha")
async def waha_webhook(request: Request):
    # Receives WhatsApp messages from WAHA
    # - Signature verification: X-Webhook-Hmac header
    # - Transforms WAHA format to Chatwoot-compatible
    # - Deduplication via Redis
    # - Filters outgoing messages (fromMe: True)
```
**Impact:** HIGH - Primary message reception point
**Replacement:** Use existing `/webhooks/twilio/whatsapp` (lines 498-644)

**Lines 383-493: Forward Chatwoot → WAHA**
```python
async def _forward_chatwoot_to_waha(payload: dict):
    # Sends human agent messages from Chatwoot to WhatsApp
    # - URL: WAHA_BASE_URL/api/sendText
    # - Format: {"session": "...", "chatId": "...", "text": "..."}
```
**Impact:** HIGH - Human handoff messaging
**Replacement:** Create `_forward_chatwoot_to_twilio()`

#### File: `app/tasks/process_message.py`
**Function: `_send_to_waha()`**
```python
async def _send_to_waha(chat_id: str, message: str):
    # Bot sends automated responses to WhatsApp
    # - Environment: WAHA_BASE_URL, WAHA_SESSION, WAHA_API_KEY
    # - Endpoint: /api/sendText
    # - ChatID format: "31612345678@c.us"
```
**Impact:** CRITICAL - All bot responses go through here
**Replacement:** Create `_send_to_twilio()`

**Function: `_sync_waha_to_chatwoot()`**
```python
async def _sync_waha_to_chatwoot(...):
    # Syncs bot messages to Chatwoot for agent visibility
    # - Creates Chatwoot conversation
    # - Marks with "synced_from_waha" cache key
```
**Impact:** MEDIUM - Agent UI sync
**Replacement:** Rename to `_sync_twilio_to_chatwoot()`

#### File: `app/security/webhook_auth.py`
**Function: `verify_waha_signature()`**
```python
def verify_waha_signature(body: bytes, signature: str, algorithm: str):
    # HMAC-SHA512 verification for WAHA webhooks
```
**Impact:** LOW - Security verification
**Replacement:** Already have `validate_twilio_webhook()` ✅

#### File: `app/agents/escalation_router.py`
**Direct WAHA API call**
```python
waha_url = os.getenv("WAHA_URL", "http://waha:3000/api/sendText")
response = requests.post(waha_url, json=payload, timeout=10)
```
**Impact:** LOW - Escalation messaging
**Replacement:** Use `_send_to_twilio()` utility

### 3.2 Indirect WAHA Dependencies

#### Environment Variables
```bash
WAHA_BASE_URL=http://waha:3000
WAHA_SESSION=default
WAHA_API_KEY=your_secret_key
WAHA_WEBHOOK_SECRET=hmac_secret
```
**Action:** Remove and replace with Twilio credentials

#### Redis Cache Keys
```python
"waha:message:{message_id}"          # Deduplication
"waha:send:dedupe:{chat_id}:{hash}"  # Send deduplication
"chatwoot:synced:{conv_id}:{msg_id}" # Sync tracking (references WAHA)
```
**Action:** Rename to `twilio:*` pattern

#### Docker Compose (if exists)
```yaml
services:
  waha:
    image: devlikeapro/waha:latest
    ports:
      - "3000:3000"
```
**Action:** Remove WAHA service completely

### 3.3 Data Format Dependencies

#### Phone Number Formats
| Source | Format | Example |
|--------|--------|---------|
| **WAHA** | `chatId: "31612345678@c.us"` | WhatsApp internal format |
| **Twilio** | `From: "whatsapp:+31612345678"` | E.164 with prefix |

**Action:** Create format converter utility

#### Message Payload Structures
| Field | WAHA | Twilio |
|-------|------|--------|
| **Message ID** | `payload.id` | `MessageSid` |
| **Sender** | `payload.from` | `From` (with whatsapp: prefix) |
| **Content** | `payload.body` | `Body` |
| **Profile** | `payload._data.notifyName` | `ProfileName` |
| **Media** | `payload.hasMedia` | `NumMedia` |

**Action:** Update transformation logic in webhook handler

---

## 4. EXISTING TWILIO CODE ASSESSMENT

### 4.1 What's Already Built ✅

#### Twilio Webhook Endpoint (app/api/webhooks.py:498-644)
```python
@router.post("/twilio/whatsapp")
async def twilio_whatsapp_webhook(request: Request, x_twilio_signature: str):
    # ✅ Signature verification
    # ✅ Deduplication (Redis)
    # ✅ Rate limiting (50/min)
    # ✅ Transform to Chatwoot-compatible format
    # ✅ Queue via Celery
    # ✅ Source tracking (source="twilio")
```
**Status:** COMPLETE - Ready to use!

#### Twilio Security (app/security/webhook_auth.py)
```python
async def validate_twilio_webhook(request: Request, signature: str):
    # ✅ HMAC-SHA256 signature validation
    # ✅ Parses form data
    # ✅ Environment: TWILIO_AUTH_TOKEN
```
**Status:** COMPLETE - Production-ready!

#### Simple Demo (main.py)
```python
# ✅ Basic Twilio Sandbox integration
# ✅ Chatwoot handoff logic
# ✅ Auto dealer flows
# ❌ NOT integrated with app/ backend
```
**Status:** DEMO ONLY - Will be replaced by app/ system

### 4.2 What's Missing ❌

#### Twilio Send Function
```python
async def _send_to_twilio(phone_number: str, message: str):
    # ❌ Does not exist yet
    # Need to implement Twilio Messages API call
```
**Action:** CREATE new function

#### Chatwoot → Twilio Forward
```python
async def _forward_chatwoot_to_twilio(payload: dict):
    # ❌ Does not exist yet
    # Replace _forward_chatwoot_to_waha()
```
**Action:** CREATE new function

#### Twilio → Chatwoot Sync
```python
async def _sync_twilio_to_chatwoot(...):
    # ❌ Does not exist yet
    # Replace _sync_waha_to_chatwoot()
```
**Action:** CREATE new function

---

## 5. INTEGRATION ASSESSMENT

### 5.1 Existing Integrations (KEEP)

#### Chatwoot API
- **Location:** `app/integrations/chatwoot_sync.py`
- **Status:** ✅ Complete
- **Features:**
  - Create conversations
  - Send messages
  - Sync contacts
  - Custom attributes (JSONB)
- **Action:** NO CHANGES NEEDED

#### Supabase Database
- **Location:** `app/database/supabase_pool.py`
- **Status:** ✅ Complete
- **Tables:**
  - Contacts (via Chatwoot)
  - Conversations
  - Documents (PGVector)
- **Action:** NO CHANGES NEEDED

#### Redis Cache
- **Status:** ✅ Active
- **Usage:**
  - Message deduplication
  - Rate limiting
  - Send deduplication
- **Action:** Update cache key prefixes only

### 5.2 NEW Integrations (ADD per PRD)

#### HubSpot Free CRM
- **Status:** ❌ NOT IMPLEMENTED
- **Required Features:**
  - Contact sync
  - Deal creation
  - Pipeline stages
  - Lead scoring integration
- **Priority:** HIGH
- **Estimated Effort:** 8-12 hours

#### Google Calendar API
- **Status:** ❌ NOT IMPLEMENTED
- **Required Features:**
  - Appointment creation
  - Availability checking
  - Event updates
  - Reminders
- **Priority:** HIGH
- **Estimated Effort:** 6-10 hours

---

## 6. RISK ASSESSMENT

### 6.1 Technical Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Message Loss During Migration** | 🔴 HIGH | 🟡 MEDIUM | Parallel running + gradual cutover |
| **Phone Number Format Issues** | 🟡 MEDIUM | 🟢 LOW | Format converter + extensive testing |
| **Twilio Rate Limiting** | 🟡 MEDIUM | 🟢 LOW | Implement retry logic + monitoring |
| **Redis Cache Key Conflicts** | 🟢 LOW | 🟡 MEDIUM | Namespace separation + migration script |
| **Agent Logic Breaks** | 🔴 HIGH | 🟢 LOW | No agent changes needed |
| **Database Schema Issues** | 🟢 LOW | 🟢 LOW | No schema changes needed |

### 6.2 Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Customer Experience Disruption** | 🔴 HIGH | Migrate during low-traffic hours |
| **Lost Conversations** | 🔴 HIGH | Export WAHA history before migration |
| **Dealer Notification** | 🟡 MEDIUM | Pre-announce migration, provide docs |
| **Support Load Increase** | 🟡 MEDIUM | Prepare FAQs, monitoring dashboard |

---

## 7. DEPENDENCIES & PREREQUISITES

### 7.1 Required Environment Variables

#### Twilio (NEW)
```bash
# Required
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+...

# Optional (for enhanced features)
TWILIO_API_KEY=...
TWILIO_API_SECRET=...
```

#### HubSpot (NEW)
```bash
HUBSPOT_API_KEY=...
HUBSPOT_PORTAL_ID=...
```

#### Google Calendar (NEW)
```bash
GOOGLE_CALENDAR_CREDENTIALS=... # Service account JSON
GOOGLE_CALENDAR_ID=...
```

#### Remove (WAHA)
```bash
❌ WAHA_BASE_URL
❌ WAHA_SESSION
❌ WAHA_API_KEY
❌ WAHA_WEBHOOK_SECRET
```

### 7.2 External Service Setup

1. **Twilio Account**
   - ✅ Already have sandbox access
   - ⏳ Upgrade to production (if not already)
   - ⏳ Configure webhook: `https://[railway-url]/webhooks/twilio/whatsapp`

2. **HubSpot Free CRM**
   - ⏳ Create account
   - ⏳ Get API key
   - ⏳ Configure deal pipeline

3. **Google Cloud Project**
   - ⏳ Enable Calendar API
   - ⏳ Create service account
   - ⏳ Download credentials JSON

---

## 8. FILE MODIFICATION SUMMARY

### Files to MODIFY
1. `app/api/webhooks.py`
   - Remove `/waha` endpoint (lines 176-296)
   - Remove `_forward_chatwoot_to_waha()` (lines 383-493)
   - Add `_forward_chatwoot_to_twilio()`
   - Keep `/twilio/whatsapp` endpoint ✅

2. `app/tasks/process_message.py`
   - Replace `_send_to_waha()` with `_send_to_twilio()`
   - Rename `_sync_waha_to_chatwoot()` to `_sync_twilio_to_chatwoot()`
   - Update `source` routing logic

3. `app/agents/escalation_router.py`
   - Replace direct WAHA API call with `_send_to_twilio()`

4. `app/security/webhook_auth.py`
   - Remove `verify_waha_signature()` (no longer needed)

5. `app/integrations/chatwoot_sync.py`
   - Update sync method names
   - Update cache keys

6. `app/orchestration/state.py`
   - Update `source` type hint: remove "waha", keep "twilio"

### Files to ADD
1. `app/integrations/hubspot_sync.py`
   - Contact sync
   - Deal management
   - Pipeline tracking

2. `app/integrations/google_calendar.py`
   - Appointment creation
   - Availability checking
   - Event management

3. `app/integrations/twilio_client.py`
   - Twilio SDK wrapper
   - Message sending
   - Error handling
   - Rate limiting

### Files to DELETE
1. `main.py` (simple demo - no longer needed)
2. Any WAHA-specific config files

---

## 9. TESTING STRATEGY

### 9.1 Unit Tests
- [ ] Phone number format conversion
- [ ] Twilio signature validation
- [ ] Message transformation logic
- [ ] Redis cache operations

### 9.2 Integration Tests
- [ ] Twilio webhook → Agent workflow
- [ ] Agent response → Twilio send
- [ ] Chatwoot → Twilio forwarding
- [ ] HubSpot contact sync
- [ ] Google Calendar appointment creation

### 9.3 End-to-End Tests
- [ ] Customer sends WhatsApp message → Bot responds
- [ ] Bot → Human handoff → Agent responds
- [ ] Appointment booking flow
- [ ] Lead creation in HubSpot

---

## 10. ROLLBACK STRATEGY

### Immediate Rollback (< 5 minutes)
1. Switch Railway/DNS back to WAHA endpoint
2. Restart WAHA container
3. Verify message flow

### Partial Rollback
- Keep Twilio for new conversations
- Route existing conversations to WAHA
- Gradual migration over 1 week

### Emergency Procedures
- [ ] WAHA backup container on standby
- [ ] Redis cache preserved
- [ ] Chatwoot conversations intact
- [ ] Supabase data unchanged

---

## NEXT STEPS

📋 **Continue to Phase 2: Data Flow Architecture**
   - Detailed sequence diagrams
   - Message flow mapping
   - Error handling paths
   - Performance considerations

**Estimated Analysis Completion:** 20% complete (Phase 1 of 5)
