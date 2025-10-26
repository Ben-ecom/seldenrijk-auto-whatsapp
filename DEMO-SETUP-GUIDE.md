# 🚀 DEMO SETUP GUIDE - Seldenrijk Auto WhatsApp Bot
## Demo-ready in 15 minuten!

**Datum:** 26 Oktober 2025
**Status:** ✅ Code klaar, testen nu!

---

## 📋 QUICK START (3 OPTIES)

### OPTIE A: Lokaal Testen (15 min) ⭐ AANBEVOLEN

**Stap 1: Start FastAPI app (2 min)**
```bash
cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp

# Activeer virtual environment (als je die hebt)
# source venv/bin/activate

# Start de app
python main.py
```

Je ziet:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Stap 2: Start ngrok (2 min)**

In nieuw terminal venster:
```bash
ngrok http 8000
```

Je krijgt een URL zoals: `https://abc123.ngrok.io`

**Stap 3: Configureer Twilio Sandbox Webhook (3 min)**

1. Ga naar: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
2. Log in met je Twilio account
3. Bij **"When a message comes in"** vul in:
   ```
   https://abc123.ngrok.io/webhook/twilio
   ```
4. **Method:** POST
5. Klik **Save**

**Stap 4: Join Sandbox met je WhatsApp (2 min)**

1. Open WhatsApp
2. Stuur bericht naar: **+1 415 523 8886**
3. Stuur: `join <jouw-sandbox-code>`
   - Code vind je op: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
   - Bijvoorbeeld: `join happy-elephant`

**Stap 5: TEST! (2 min)**

Stuur in WhatsApp:
- `hallo` → Welkomstbericht 🎉
- `auto` → Aanbod overzicht
- `1` → Volkswagen Golf details
- `proefrit` → Proefrit plannen
- `verkoper` → Human handoff trigger! 🤝

**Expected output:**
```
Terminal logs:
📨 Received: hallo | From: whatsapp:+31612345678
✅ Response sent: SM...
```

✅ **DEMO KLAAR!**

---

### OPTIE B: Railway Deploy (10 min)

**Als je al Railway project hebt:**

```bash
# Push naar git
git add main.py DEMO-SETUP-GUIDE.md
git commit -m "Add Twilio + Chatwoot demo"
git push

# Railway auto-deployt binnen 2 minuten!
```

**Je Railway URL:**
```
https://seldenrijk-auto-whatsapp.up.railway.app
```

**Configureer Twilio webhook:**
```
https://seldenrijk-auto-whatsapp.up.railway.app/webhook/twilio
```

---

### OPTIE C: Docker (als je Docker hebt)

```bash
# Build
docker build -t seldenrijk-auto-bot .

# Run
docker run -p 8000:8000 \
  -e TWILIO_ACCOUNT_SID=YOUR_ACCOUNT_SID \
  -e TWILIO_AUTH_TOKEN=YOUR_AUTH_TOKEN \
  seldenrijk-auto-bot
```

---

## 🤝 CHATWOOT SETUP (OPTIONEEL - 10 min)

**Voor bot-to-human handoff:**

### Stap 1: Chatwoot Account

**Optie A: Cloud (Snelst)**
1. Ga naar: https://app.chatwoot.com
2. Sign up (gratis trial)
3. Noteer je **Account ID** (zie URL: `/app/accounts/123456`)

**Optie B: Self-hosted (Meer controle)**
```bash
docker run -d \
  -p 3000:3000 \
  -e DATABASE_URL=postgresql://... \
  chatwoot/chatwoot:latest
```

### Stap 2: Create WhatsApp Inbox

1. In Chatwoot: **Settings → Inboxes → Add Inbox**
2. Select: **WhatsApp**
3. Name: "Seldenrijk Auto"
4. Click **Create**
5. Noteer **Inbox ID** (zie URL of API response)

### Stap 3: Get API Key

1. In Chatwoot: **Profile Settings → Access Token**
2. Click **Create New Token**
3. Copy token (bijv. `abc123def456...`)

### Stap 4: Configure Environment Variables

**Lokaal:**
```bash
# .env file
CHATWOOT_API_KEY=abc123def456...
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_ACCOUNT_ID=123456
CHATWOOT_INBOX_ID=789
```

**Railway:**
1. Ga naar je project → **Variables**
2. Add:
   - `CHATWOOT_API_KEY` = `abc123def456...`
   - `CHATWOOT_BASE_URL` = `https://app.chatwoot.com`
   - `CHATWOOT_ACCOUNT_ID` = `123456`
   - `CHATWOOT_INBOX_ID` = `789`
3. **Deploy** (Railway herstart automatically)

### Stap 5: Test Human Handoff

**In WhatsApp:**
1. Stuur: `hallo`
2. Stuur: `ik wil een verkoper spreken`
3. ✅ Bot antwoordt: "Ik verbind je nu door..."
4. ✅ Conversation verschijnt in Chatwoot!
5. In Chatwoot: Typ antwoord → **Send**
6. ✅ Customer ontvangt bericht via WhatsApp!

---

## 📊 DEMO SCENARIOS

### Scenario 1: Auto Zoeken
```
User: hallo
Bot: Welkom bij Seldenrijk Auto! [menu]

User: auto
Bot: [Toont 4 auto's met prijzen]

User: 1
Bot: [VW Golf details + opties]

User: proefrit
Bot: [Proefrit tijdslots]
```

### Scenario 2: Financiering
```
User: prijs
Bot: [Financieringsopties: contant, lease, financiering]

User: lease
Bot: [Lease details vanaf €299/maand]
```

### Scenario 3: Human Handoff
```
User: ik wil met iemand spreken
Bot: Ik verbind je door naar een verkoper...
[✅ Chatwoot conversation created]

[In Chatwoot]
Dealer: Hallo! Waarmee kan ik je helpen?
[✅ Message sent via WhatsApp]
```

---

## 🔍 TROUBLESHOOTING

### ❌ "No response in WhatsApp"

**Check:**
1. Is FastAPI app running? (`http://localhost:8000` → should show `{"status": "online"}`)
2. Is ngrok running? Check ngrok URL in browser
3. Is Twilio webhook URL correct? Check Twilio dashboard

**Fix:**
```bash
# Check app status
curl http://localhost:8000/health

# Check logs
# In terminal waar main.py draait, zie je logs
```

---

### ❌ "Forbidden" error in Twilio logs

**Check:**
Twilio credentials correct? Check `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`

**Fix:**
```bash
# Test credentials
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json" \
  --data-urlencode "From=whatsapp:+14155238886" \
  --data-urlencode "To=whatsapp:+31JOUWTELEFOON" \
  --data-urlencode "Body=Test" \
  -u YOUR_ACCOUNT_SID:YOUR_AUTH_TOKEN
```

---

### ❌ Chatwoot handoff not working

**Check:**
1. Chatwoot environment variables set? Check `/` endpoint:
   ```bash
   curl http://localhost:8000/
   # Should show: "chatwoot_configured": true
   ```

2. Chatwoot API key valid?
   ```bash
   curl https://app.chatwoot.com/api/v1/accounts/ACCOUNT_ID/conversations \
     -H "api_access_token: YOUR_API_KEY"
   ```

**Fix:**
Re-check environment variables spelling:
- `CHATWOOT_API_KEY` (not `CHATWOOT_TOKEN`)
- `CHATWOOT_ACCOUNT_ID` (numeric, not string with quotes)
- `CHATWOOT_INBOX_ID` (numeric)

---

### ❌ Railway deployment failed

**Check logs:**
```bash
railway logs
```

**Common issues:**
1. Missing environment variables → Add in Railway dashboard
2. Port binding → Railway auto-detects `PORT` env var (no action needed)
3. Build errors → Check `requirements.txt` has all dependencies

---

## 🎯 NEXT STEPS

### This Week (Demo):
- ✅ Twilio Sandbox working
- ✅ Basic Chatwoot handoff working
- ✅ Demo scenarios tested
- ⏳ Show to 1-2 autodealers for feedback

### Week 2 (Production):
- Multi-tenant architecture (per-dealer credentials)
- PostgreSQL database for chat history
- Better conversation flows (more auto models, better responses)
- Dealer admin panel (optional)

### Week 3+ (Scale):
- Migration guide for dealers with existing WhatsApp
- Analytics dashboard
- CRM integration (HubSpot/Salesforce)
- Advanced chatbot features (image recognition, voice messages)

---

## 📞 HELP NEEDED?

**Quick commands:**

```bash
# Check if app is running
curl http://localhost:8000/health

# View active human handoffs
curl http://localhost:8000/active-handoffs

# Reset a user's handoff mode (for testing)
curl -X POST http://localhost:8000/reset-handoff/+31612345678

# Test webhook directly
curl -X POST http://localhost:8000/webhook/twilio \
  -d "Body=hallo" \
  -d "From=whatsapp:+31612345678" \
  -d "To=whatsapp:+14155238886" \
  -d "MessageSid=TEST123"
```

---

## ✅ CHECKLIST

### Demo Ready:
- [ ] FastAPI app starts without errors
- [ ] Ngrok tunnel active OR Railway deployed
- [ ] Twilio webhook configured
- [ ] Joined Twilio Sandbox with WhatsApp
- [ ] Test: "hallo" → response received
- [ ] Test: "auto" → car list shown
- [ ] Test: "1" → VW Golf details shown

### Chatwoot Ready (Optional):
- [ ] Chatwoot account created
- [ ] Inbox ID obtained
- [ ] API key configured in environment
- [ ] Test: "verkoper" → conversation in Chatwoot
- [ ] Test: Dealer response → received in WhatsApp

---

**Demo Time:** 10-15 minutes from start to working WhatsApp bot! 🚀

**Questions?** Check logs in terminal or Railway dashboard.

**Succes! 🎉**
