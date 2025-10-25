# Chatwoot Integration Testing Guide

## Changes Made

### 1. ChatwootAPI Class (`app/integrations/chatwoot_api.py`)
Added 5 new methods:

- **`create_contact(phone, name, inbox_id)`** - Creates new contact from phone number
- **`get_contact_by_phone(phone)`** - Searches for existing contact by phone
- **`create_conversation(contact_id, inbox_id)`** - Creates conversation for contact
- **`get_conversation_by_contact(contact_id, inbox_id)`** - Finds existing conversation
- **`update_contact_attributes(contact_id, custom_attributes)`** - Updates contact metadata

### 2. EnhancedCRMAgent (`app/agents/enhanced_crm_agent.py`)
Updated `_update_chatwoot()` method with complete flow:

```python
WhatsApp Message → Extract Phone → Get/Create Contact → Get/Create Conversation → Add Labels → Update Attributes
```

---

## Testing Prerequisites

1. **Chatwoot is running:**
   ```bash
   cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp
   docker-compose ps | grep chatwoot
   ```
   Should show `chatwoot:3000` running

2. **WhatsApp inbox configured in Chatwoot:**
   - Login: http://localhost:3001
   - Go to Settings → Inboxes
   - Note the **Inbox ID** (usually 1 or 2)
   - Update `EnhancedCRMAgent._update_chatwoot()` line 565 if not ID 1

3. **Celery worker running:**
   ```bash
   docker-compose ps | grep celery
   ```

---

## Test 1: Manual API Test

### Step 1: Create Contact Directly
```bash
curl -X POST http://localhost:3001/api/v1/accounts/1/contacts \
  -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  -H "Content-Type: application/json" \
  -d '{
    "inbox_id": 1,
    "name": "Test WhatsApp User",
    "phone_number": "+31612345678"
  }'
```

**Expected Output:**
```json
{
  "payload": {
    "contact": {
      "id": 1,
      "name": "Test WhatsApp User",
      "phone_number": "+31612345678",
      ...
    }
  }
}
```

### Step 2: Verify Contact Created
```bash
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  "http://localhost:3001/api/v1/accounts/1/contacts/search?q=%2B31612345678"
```

**Expected:** Should return the contact with `id: 1`

### Step 3: Create Conversation
```bash
curl -X POST http://localhost:3001/api/v1/accounts/1/conversations \
  -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "1-1",
    "inbox_id": 1,
    "contact_id": 1
  }'
```

**Expected Output:**
```json
{
  "id": 1,
  "inbox_id": 1,
  "contact": {
    "id": 1,
    "name": "Test WhatsApp User"
  },
  ...
}
```

---

## Test 2: End-to-End WhatsApp Webhook Test

### Step 1: Send Test Webhook Message
```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "from": "31612345678",
      "id": "test-message-001",
      "timestamp": "1736945123",
      "type": "text",
      "text": {
        "body": "Hallo, ik ben geïnteresseerd in een Golf GTI. Kan ik vandaag nog een proefrit maken?"
      }
    }]
  }'
```

### Step 2: Monitor Celery Logs
```bash
docker-compose logs -f celery-worker
```

**Look for:**
```
✅ Contact resolved: ID 1 (+31612345678)
✅ Conversation resolved: ID 1
✅ Added 5/8 labels to conversation 1
✅ Updated custom attributes for contact 1
```

### Step 3: Verify in Chatwoot UI
1. Open: http://localhost:3001
2. Go to "Conversations"
3. Should see:
   - **Contact:** Test WhatsApp User (+31612345678)
   - **Conversation:** With incoming message
   - **Labels:**
     - `journey:first-contact`
     - `interest:volkswagen`
     - `intent:ready-to-buy`
     - `behavior:test-drive-requested`
     - `engagement:hot-lead`
     - `source:whatsapp-ai-agent`

### Step 4: Verify Custom Attributes
1. Click on contact name in conversation
2. Go to "Contact Attributes" tab
3. Should see:
   - `lead_score`: 70+ (HOT lead)
   - `lead_quality`: "HOT"
   - `urgency`: "critical"
   - `test_drive_requested`: true

---

## Test 3: API Verification

### Check All Contacts
```bash
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  http://localhost:3001/api/v1/accounts/1/contacts | jq '.payload | length'
```

**Expected:** Should show 1+ contacts

### Check All Conversations
```bash
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  http://localhost:3001/api/v1/accounts/1/conversations | jq '.data.payload | length'
```

**Expected:** Should show 1+ conversations

---

## Troubleshooting

### Issue: Contact not created
**Symptoms:** Logs show "Failed to create contact"

**Debug:**
```bash
# Check if Chatwoot API is accessible
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  http://localhost:3001/api/v1/accounts/1/contacts

# Check inbox ID
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  http://localhost:3001/api/v1/accounts/1/inboxes | jq '.payload[].id'
```

**Fix:** Update `inbox_id` in `EnhancedCRMAgent._update_chatwoot()` line 565

---

### Issue: Labels not added
**Symptoms:** Logs show "Failed to add label"

**Debug:**
```bash
# Check if labels exist in Chatwoot
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  http://localhost:3001/api/v1/accounts/1/labels
```

**Fix:** Create labels manually in Chatwoot:
1. Go to Settings → Labels
2. Add labels:
   - `journey:first-contact`
   - `intent:ready-to-buy`
   - `behavior:test-drive-requested`
   - `engagement:hot-lead`
   - `source:whatsapp-ai-agent`

---

### Issue: Conversation not found
**Symptoms:** "No existing conversation found"

**Debug:**
```bash
# List all conversations
curl -H "api_access_token: EbYQQ6DviXokyw1kuSA5ANQe" \
  "http://localhost:3001/api/v1/accounts/1/conversations?inbox_id=1" | jq '.data.payload'
```

**Fix:** This is normal for first message - conversation will be created automatically

---

## Success Criteria

- [ ] Contact created in Chatwoot with phone number
- [ ] Conversation created for contact
- [ ] Labels added to conversation (at least 3)
- [ ] Custom attributes updated on contact
- [ ] No errors in Celery logs
- [ ] Lead score visible in Chatwoot contact attributes

---

## Next Steps

1. **Environment Variable for Inbox ID:**
   ```bash
   # Add to .env
   CHATWOOT_WHATSAPP_INBOX_ID=1
   ```

2. **Label Pre-creation Script:**
   Create script to auto-create all 25+ labels in Chatwoot

3. **Contact Name Enhancement:**
   Extract real name from WhatsApp profile if available

4. **Multiple Inbox Support:**
   Handle different inbox IDs for multiple WhatsApp numbers

---

## Code References

- **ChatwootAPI:** `/Users/benomarlaamiri/Claude code project/seldenrijk-auto-whatsapp/app/integrations/chatwoot_api.py` (lines 161-334)
- **EnhancedCRMAgent:** `/Users/benomarlaamiri/Claude code project/seldenrijk-auto-whatsapp/app/agents/enhanced_crm_agent.py` (lines 538-627)
- **Environment Config:** `.env` (lines 23-27)
