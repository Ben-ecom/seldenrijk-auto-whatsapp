# 🚂 Railway Environment Variables Configuration Guide

**Project:** Seldenrijk Auto WhatsApp AI Platform
**Date:** 2025-10-26
**Migration:** WAHA → Twilio WhatsApp Complete

---

## 📋 How to Add Variables in Railway

1. Go to your Railway project: https://railway.app
2. Click on your service (e.g., `seldenrijk-api`)
3. Go to **Variables** tab
4. Click **+ New Variable**
5. Add each variable below with your actual values

---

## 🔴 CRITICAL Variables (Required for Basic Operation)

### 1️⃣ Anthropic Claude API
```
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXX
```
**Where to get:** https://console.anthropic.com/settings/keys

---

### 2️⃣ Supabase (Vector Database)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.XXXXXXXX
```
**Where to get:**
- Login to https://supabase.com
- Go to Project Settings → API
- Copy `URL` and `service_role key` (NOT anon key!)

---

### 3️⃣ Twilio WhatsApp (Primary Provider)
```
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_WHATSAPP_NUMBER=whatsapp:+31850000000
TWILIO_WEBHOOK_URL=https://seldenrijk-auto-whatsapp-production.up.railway.app/webhooks/twilio/whatsapp
```
**Where to get:**
- Login to https://console.twilio.com
- Go to Account → Account Info
- Copy `Account SID` and `Auth Token`
- For WhatsApp number: Go to Messaging → Try it out → WhatsApp sandbox
- **IMPORTANT:** Replace `seldenrijk-auto-whatsapp-production` with YOUR Railway domain!

---

### 4️⃣ Chatwoot (Customer Support - Optional but Recommended)
```
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_API_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXX
CHATWOOT_ACCOUNT_ID=2
CHATWOOT_INBOX_ID=1
CHATWOOT_SECRET_KEY_BASE=XXXXXXXXXXXXXXXX
```
**Where to get:**
- Login to https://app.chatwoot.com
- Go to Settings → Integrations → API Access Tokens
- Create new token or copy existing
- Account ID: Check URL when logged in (e.g., `/app/accounts/2/`)
- Inbox ID: Go to Settings → Inboxes → Click your inbox → Check URL

---

### 5️⃣ Redis & Celery (Auto-configured by Docker)
```
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```
**Note:** These are automatically set by Docker Compose. Only add if Railway doesn't use Docker Compose.

---

## 🟡 OPTIONAL Variables (Enhanced Features)

### 6️⃣ HubSpot CRM (Lead Management)
```
HUBSPOT_API_KEY=pat-na1-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
HUBSPOT_ENABLED=true
```
**Where to get:**
- Login to https://app.hubspot.com
- Go to Settings → Integrations → Private Apps
- Create new app with scopes: `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.objects.deals.read`, `crm.objects.deals.write`
- Copy access token

**What it does:**
- Automatically creates/updates contacts from WhatsApp leads
- Creates deals for test drive requests
- Syncs lead scores to HubSpot

---

### 7️⃣ Google Calendar (Appointment Scheduling)
```
GOOGLE_SERVICE_ACCOUNT_JSON=/app/service-account.json
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_ENABLED=true
```
**Where to get:**
- Go to https://console.cloud.google.com
- Create new project or select existing
- Enable Google Calendar API
- Create Service Account
- Download JSON key file
- Upload to Railway as secret file or use base64 encoded string

**What it does:**
- Real-time availability checking for test drives
- Automatic appointment booking
- Google Calendar event creation
- Business hours enforcement (Mon-Sat 09:00-18:00)

---

### 8️⃣ Logging & Monitoring
```
LOG_LEVEL=INFO
ENVIRONMENT=production
PLAYWRIGHT_HEADLESS=true
```
**Options:**
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `ENVIRONMENT`: development, staging, production
- `PLAYWRIGHT_HEADLESS`: true (for production), false (for debugging)

---

## 🔧 Railway Service-Specific Variables

**For `api` service:**
- Add ALL variables from sections 1-8

**For `celery-worker` service:**
- Add same variables as API service (workers need access to all integrations)

**For `celery-beat` service:**
- Add: REDIS_URL, SUPABASE_URL, SUPABASE_KEY, CHATWOOT_BASE_URL, CHATWOOT_API_TOKEN

**For `redis` service:**
- No environment variables needed

**For `dashboard` service:**
- Add: `API_BASE_URL=http://api:8000`

---

## ✅ Verification Checklist

After adding all variables:

1. **Check Deployment Logs:**
   ```
   Railway Dashboard → Deployments → View Logs
   ```

2. **Test Health Endpoint:**
   ```bash
   curl https://your-railway-domain.up.railway.app/health
   ```

3. **Test Twilio Webhook:**
   - Send test WhatsApp message to your Twilio sandbox number
   - Check Railway logs for incoming webhook

4. **Check Services Status:**
   - API: Should show "Running"
   - Celery Worker: Should show "Running"
   - Celery Beat: Should show "Running"
   - Redis: Should show "Running"

---

## 🚨 Security Best Practices

1. **NEVER commit `.env` to Git** ✅ (Already handled)
2. **Use Railway's secret variables** for sensitive data
3. **Rotate credentials regularly** (every 90 days)
4. **Enable 2FA** on all service accounts
5. **Monitor API usage** to detect unauthorized access

---

## 📞 Next Steps After Configuration

1. ✅ Add all environment variables in Railway
2. ✅ Wait for deployment to complete (check logs)
3. ✅ Test health endpoint
4. ✅ Configure Twilio webhook URL in Twilio Console:
   ```
   https://your-railway-domain.up.railway.app/webhooks/twilio/whatsapp
   ```
5. ✅ Send test WhatsApp message
6. ✅ Verify AI responds correctly

---

## 🆘 Troubleshooting

**Problem:** Deployment fails with "Missing environment variable"
- **Solution:** Check Railway logs, add missing variable

**Problem:** Twilio webhook returns 403 Forbidden
- **Solution:** Check signature verification in logs, verify TWILIO_AUTH_TOKEN is correct

**Problem:** No response from AI
- **Solution:** Check ANTHROPIC_API_KEY, check Celery worker logs

**Problem:** HubSpot sync fails
- **Solution:** Verify HUBSPOT_API_KEY has correct scopes, check HubSpot enabled flag

**Problem:** Calendar slots not showing
- **Solution:** Verify GOOGLE_SERVICE_ACCOUNT_JSON is uploaded, check Calendar API enabled

---

## 📚 Additional Resources

- Railway Docs: https://docs.railway.app
- Twilio WhatsApp Docs: https://www.twilio.com/docs/whatsapp
- HubSpot API Docs: https://developers.hubspot.com
- Google Calendar API: https://developers.google.com/calendar
- Supabase Docs: https://supabase.com/docs

---

**Generated:** 2025-10-26
**Project:** Seldenrijk Auto WhatsApp AI Platform
**Status:** Production-Ready ✅
