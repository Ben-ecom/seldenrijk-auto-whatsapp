# ⚡ Railway Quick Setup - 5 Minuten

**Laatste Update:** 2025-10-26
**Status:** Production-Ready ✅

---

## 🚀 Snelstart (Copy-Paste Ready)

### Stap 1: Railway Dashboard Openen
```
https://railway.app → Jouw Project → Variables Tab
```

### Stap 2: Kopieer & Plak Deze Variabelen

**Minimaal Vereist (5 variabelen):**

```bash
# 1. AI Provider
ANTHROPIC_API_KEY=sk-ant-api03-JOUW_KEY_HIER

# 2. Database
SUPABASE_URL=https://JOUW-PROJECT.supabase.co
SUPABASE_KEY=JOUW_SUPABASE_SERVICE_ROLE_KEY

# 3. WhatsApp
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=JOUW_TWILIO_TOKEN
TWILIO_WHATSAPP_NUMBER=whatsapp:+31850000000
```

**Waar vind ik deze keys?**
- **Anthropic:** https://console.anthropic.com/settings/keys
- **Supabase:** https://supabase.com → Project Settings → API → `service_role` key
- **Twilio:** https://console.twilio.com → Account Info

---

## 📋 Checklist (Vink af wat klaar is)

- [ ] **Railway account aangemaakt**
- [ ] **GitHub repo connected** (Auto-deploy ingeschakeld)
- [ ] **ANTHROPIC_API_KEY toegevoegd**
- [ ] **SUPABASE_URL + SUPABASE_KEY toegevoegd**
- [ ] **TWILIO credentials toegevoegd** (SID, Token, Number)
- [ ] **Deployment logs gecheckt** (Geen errors)
- [ ] **Health endpoint getest:** `curl https://jouw-domain.up.railway.app/health`
- [ ] **Twilio webhook geconfigureerd** in Twilio Console
- [ ] **Test WhatsApp bericht verstuurd**
- [ ] **AI response ontvangen** ✅

---

## 🔧 Extra Features (Optioneel)

### Chatwoot (Chat History)
```bash
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_API_TOKEN=JOUW_TOKEN
CHATWOOT_ACCOUNT_ID=2
```
**Waar:** Chatwoot → Settings → API Access Tokens

### HubSpot CRM (Lead Management)
```bash
HUBSPOT_API_KEY=pat-na1-XXXXXXXX
HUBSPOT_ENABLED=true
```
**Waar:** HubSpot → Settings → Private Apps

### Google Calendar (Afspraken)
```bash
GOOGLE_SERVICE_ACCOUNT_JSON=/app/service-account.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_ENABLED=true
```
**Waar:** Google Cloud Console → Service Accounts

---

## 🎯 Verification Steps

### 1. Check Deployment Status
```bash
Railway Dashboard → Deployments → Latest Build → View Logs
```
**Zoek naar:** `Application startup complete` of `Started successfully`

### 2. Test Health Endpoint
```bash
curl https://JOUW-DOMAIN.up.railway.app/health
```
**Verwachte output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-26T...",
  "services": {
    "api": "running",
    "celery": "running",
    "redis": "connected"
  }
}
```

### 3. Check Services
```bash
Railway Dashboard → Services
```
**Alle services moeten "Running" zijn:**
- ✅ api (FastAPI)
- ✅ celery-worker (Message processing)
- ✅ celery-beat (Scheduled tasks)
- ✅ redis (Cache)

---

## 🔗 Twilio Webhook Setup

**Ga naar:** https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox

**Configureer:**
```
When a message comes in:
https://JOUW-RAILWAY-DOMAIN.up.railway.app/webhooks/twilio/whatsapp

Method: POST
```

**BELANGRIJK:** Vervang `JOUW-RAILWAY-DOMAIN` met je echte Railway URL!

**Voorbeeld Railway URL:**
```
https://seldenrijk-auto-whatsapp-production.up.railway.app/webhooks/twilio/whatsapp
```

---

## 🧪 Test Flow

1. **Join Twilio WhatsApp Sandbox:**
   - Ga naar Twilio Console → Messaging → WhatsApp Sandbox
   - Stuur join code naar Twilio nummer (bijv. "join happy-tiger")

2. **Verstuur test bericht:**
   ```
   Hallo, ik wil graag een proefrit maken!
   ```

3. **Check Railway Logs:**
   ```
   Railway → api service → Logs
   ```
   **Zoek naar:**
   - `Twilio webhook received`
   - `Message queued for processing`
   - `Message sent to Twilio`

4. **Ontvang AI Response:**
   ```
   Leuk dat je interesse hebt! Voor welke auto wil je een proefrit maken?
   ```

---

## ❌ Troubleshooting

| Probleem | Oplossing |
|----------|-----------|
| **Deployment fails** | Check logs, kijk welke env var ontbreekt |
| **403 Forbidden** | Controleer TWILIO_AUTH_TOKEN |
| **Geen response** | Check ANTHROPIC_API_KEY, kijk Celery logs |
| **Health check fails** | Wacht 2-3 minuten na deployment |
| **Twilio webhook fails** | Controleer URL eindigt op `/webhooks/twilio/whatsapp` |

---

## 📞 Support

**Documentatie:**
- 📖 Complete guide: `RAILWAY-CONFIG-GUIDE.md`
- 🔍 Environment checker: `./check-env.py`

**Logs checken:**
```bash
Railway Dashboard → Service → Logs → Real-time
```

**Quick Health Check:**
```bash
python3 check-env.py
```

---

## ✅ Production Checklist

- [ ] Alle CRITICAL env vars toegevoegd
- [ ] Deployment succesvol (geen errors in logs)
- [ ] Health endpoint reageert (200 OK)
- [ ] Alle services draaien (api, celery-worker, celery-beat, redis)
- [ ] Twilio webhook geconfigureerd
- [ ] Test WhatsApp bericht werkt
- [ ] AI antwoordt correct
- [ ] Chatwoot sync werkt (optioneel)
- [ ] HubSpot sync werkt (optioneel)
- [ ] Google Calendar werkt (optioneel)

---

**🎉 SUCCESS = AI WhatsApp bot reageert op klantberichten!**

**Deployment tijd:** ~5-10 minuten
**Status:** Production-Ready ✅
**Versie:** 2025-10-26
