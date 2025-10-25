# 360Dialog WhatsApp Integration Setup

This guide explains how to set up 360Dialog for WhatsApp Business API integration.

---

## 📋 Prerequisites

1. **Business Information**:
   - Registered business name
   - Business website
   - Business address

2. **Phone Number**:
   - Dedicated phone number (not used for personal WhatsApp)
   - Must be able to receive SMS verification

3. **Facebook Business Manager** (optional but recommended):
   - Facebook Business Manager account
   - WhatsApp Business Account

---

## 🚀 Step-by-Step Setup

### 1. Create 360Dialog Account

1. Go to [360dialog.com](https://www.360dialog.com)
2. Click "Get Started" or "Sign Up"
3. Choose your plan:
   - **Free Trial**: 1000 free conversations (7 days)
   - **Pay-as-you-go**: €0.005 - €0.15 per conversation
   - **Business Plan**: Starting at €49/month

### 2. Connect WhatsApp Business Number

1. In the 360Dialog dashboard, click "Add Channel"
2. Choose "WhatsApp Business API"
3. Enter your phone number (with country code)
4. Verify via SMS code
5. Set up your business profile:
   - Business name
   - Business description
   - Profile photo
   - Business category

### 3. Get API Credentials

1. Navigate to "API Keys" in the 360Dialog dashboard
2. Copy your **API Key** (starts with `D360-...`)
3. Copy your **Phone Number ID** (usually your WhatsApp number)

### 4. Configure Webhook

1. In 360Dialog dashboard, go to "Webhooks"
2. Add webhook URL: `https://yourdomain.com/webhook/whatsapp`
3. Select events to receive:
   - ✅ Messages
   - ✅ Message Status
   - ✅ Account Review Update
4. Save webhook configuration
5. 360Dialog will send a GET request to verify your webhook

### 5. Update Environment Variables

Add your credentials to `.env`:

```bash
THREESIXTY_DIALOG_API_KEY=D360-your-api-key-here
THREESIXTY_DIALOG_PHONE_NUMBER=+31612345678
```

### 6. Webhook Verification

Your API automatically handles webhook verification with this endpoint:

```python
@router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """Webhook verification for 360Dialog."""
    query_params = request.query_params
    if "hub.challenge" in query_params:
        return {"hub.challenge": query_params["hub.challenge"]}
```

When 360Dialog sends a verification request, your API responds with the challenge token.

---

## 🧪 Testing

### Local Testing with ngrok

For local development, use ngrok to expose your localhost:

```bash
# Install ngrok
brew install ngrok

# Start your API
python -m api.main

# In another terminal, start ngrok
ngrok http 8000

# Copy the ngrok URL (e.g., https://abc123.ngrok.io)
# Set this as your webhook URL in 360Dialog: https://abc123.ngrok.io/webhook/whatsapp
```

### Send Test Message

1. Send a WhatsApp message to your business number
2. Check your API logs for webhook receipt
3. Verify the response is sent back to WhatsApp

### Test with Mock Payload

Run the included test script:

```bash
python test_webhook.py
```

This sends a mock 360Dialog payload to test orchestration logic without WhatsApp.

---

## 📊 360Dialog Message Format

### Inbound Message (from customer)

```json
{
  "messages": [
    {
      "from": "+31612345678",
      "id": "wamid.HBgNMzE2MTIzNDU2NzgVAgA...",
      "timestamp": "1710123456",
      "type": "text",
      "text": {
        "body": "Hoi! Ik ben op zoek naar een baan als kapper"
      }
    }
  ],
  "contacts": [
    {
      "profile": {
        "name": "Sarah"
      },
      "wa_id": "+31612345678"
    }
  ]
}
```

### Outbound Message (to customer)

```bash
curl -X POST "https://waba.360dialog.io/v1/messages" \
  -H "D360-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+31612345678",
    "type": "text",
    "text": {
      "body": "Hoi Sarah! Leuk dat je interesse hebt. Wat is je ervaring als kapper?"
    }
  }'
```

### Message Types Supported

- ✅ **Text**: Plain text messages
- ✅ **Image**: Photos with captions
- ✅ **Document**: PDF, Word, etc.
- ✅ **Audio**: Voice messages
- ✅ **Video**: Video files
- ✅ **Location**: Geographic coordinates
- ✅ **Contacts**: vCard format
- ✅ **Interactive**: Buttons and lists (templates)

---

## 💰 Pricing

### Conversation-Based Pricing

360Dialog charges per 24-hour conversation window:

| Category | Price per Conversation |
|----------|----------------------|
| **Marketing** | €0.05 - €0.15 |
| **Utility** | €0.005 - €0.05 |
| **Authentication** | €0.005 - €0.02 |
| **Service** | €0.01 - €0.08 |

**Our use case**: Service conversations (recruitment) = ~€0.02 per conversation

**Example calculation**:
- 200 leads/week = 800 leads/month
- Average 2 conversations per lead = 1600 conversations
- Cost: 1600 × €0.02 = **€32/month** (messages only)

### 360Dialog Platform Fee

- **Free Tier**: 1000 free conversations (7 days trial)
- **Pay-as-you-go**: No monthly fee, pay per message
- **Business Plan**: €49/month + message costs (includes support)

---

## 🔧 Troubleshooting

### Webhook Not Receiving Messages

1. Check webhook URL is correct in 360Dialog dashboard
2. Verify your API is running and accessible
3. Check firewall/security group allows inbound HTTPS
4. Test with ngrok for local development

### Messages Not Sending

1. Verify API key is correct in `.env`
2. Check phone number format (include `+` and country code)
3. Ensure WhatsApp number is verified in 360Dialog
4. Check API logs for error messages

### Rate Limiting

360Dialog has rate limits:
- **1000 messages per second** (burst)
- **250,000 messages per day** (sustained)

Our rate limiter: 100 req/min, 1000 req/hour per IP

---

## 📚 Resources

- [360Dialog Documentation](https://docs.360dialog.com/)
- [WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp)
- [360Dialog Pricing](https://www.360dialog.com/pricing)
- [360Dialog Support](https://support.360dialog.com/)

---

## ✅ Production Checklist

Before going live:

- [ ] Business profile is complete (name, description, logo)
- [ ] Webhook URL is HTTPS (not HTTP)
- [ ] Environment variables are set correctly
- [ ] Tested sending and receiving messages
- [ ] Rate limiting is configured
- [ ] Error handling is in place
- [ ] Monitoring/logging is set up
- [ ] Privacy policy is linked (if required)
- [ ] Terms of service are linked (if required)

---

## 🚀 Next Steps

After setup:

1. **Test End-to-End Flow**: Send test messages and verify responses
2. **Monitor Conversations**: Check 360Dialog dashboard for insights
3. **Optimize Prompts**: Refine agent responses based on real conversations
4. **Scale Up**: Increase message volume gradually
5. **Add Features**: Implement media handling, templates, etc.
