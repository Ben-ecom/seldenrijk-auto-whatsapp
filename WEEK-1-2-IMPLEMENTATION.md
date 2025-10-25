# 🚀 Week 1-2 Implementation: Chatwoot Setup + WhatsApp MCP

**Timeline:** Week 1-2 (14 days)
**Status:** 🟡 In Progress
**Prerequisites:** ✅ P0 fixes completed

---

## 📋 Overview

Week 1-2 focust op het opzetten van de complete messaging infrastructuur:
- Chatwoot deployment op Railway
- WhatsApp MCP configuratie voor development
- FastAPI integratie met Chatwoot webhooks
- End-to-end message flow testing

**Deliverables:**
1. ✅ Werkende Chatwoot instance (Railway)
2. ✅ WhatsApp MCP voor development testing
3. ✅ FastAPI webhook endpoints (met P0 security)
4. ✅ Test script voor complete message flow
5. ✅ Deployment documentatie

---

## 🎯 Week 1: Chatwoot Deployment

### Day 1-2: Railway Setup

**Stap 1: Creëer Railway Project**
1. Ga naar [Railway.app](https://railway.app)
2. Klik "New Project"
3. Select "Deploy from Template"
4. Zoek "Chatwoot" of gebruik deze link: https://railway.app/template/chatwoot

**Stap 2: Configureer Environment Variables**
```env
# Railway zet automatisch:
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
RAILS_ENV=production

# Jij moet toevoegen:
FRONTEND_URL=https://your-app.railway.app
INSTALLATION_NAME=YourCompany Recruitment

# Email (voor notificaties)
MAILER_SENDER_EMAIL=support@yourdomain.com
SMTP_ADDRESS=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key

# Storage (Cloudinary of S3)
ACTIVE_STORAGE_SERVICE=local  # Voor nu lokaal

# Security
SECRET_KEY_BASE=<railway-genereert-automatisch>
```

**Stap 3: Deploy & Verify**
```bash
# Railway deploy automatisch, wacht 5-10 minuten

# Test of Chatwoot live is:
curl https://your-app.railway.app/api
# Verwacht: {"version": "..."}
```

**Kosten:** ~€5-10/maand (Starter plan)

---

### Day 3-4: Chatwoot Configuratie

**Stap 1: Maak Admin Account**
1. Ga naar `https://your-app.railway.app`
2. Klik "Sign up"
3. Vul in:
   - Email: jouw admin email
   - Full Name: jouw naam
   - Password: sterk wachtwoord
4. Verifieer email (check spam folder)

**Stap 2: Creëer Inbox voor WhatsApp**
1. Ga naar Settings → Inboxes
2. Klik "Add Inbox"
3. Select "WhatsApp"
4. Kies "360Dialog" als provider
5. Vul in:
   - Inbox Name: "WhatsApp Recruitment"
   - API Key: `<laat leeg voor nu, we gebruiken WhatsApp MCP eerst>`
   - Phone Number: `<laat leeg voor nu>`
6. Save

**Stap 3: Genereer API Token**
1. Ga naar Settings → Profile
2. Scroll naar "Access Token"
3. Klik "Generate new token"
4. Kopieer token → dit wordt `CHATWOOT_API_TOKEN`

**Stap 4: Vind Account ID**
```bash
# In browser console (F12):
console.log(window.chatwootConfig.accountId)
# Of via API:
curl https://your-app.railway.app/api/v1/accounts \
  -H "api_access_token: YOUR_TOKEN"
```

**Stap 5: Configureer Webhook**
1. Ga naar Settings → Webhooks
2. Klik "Add Webhook"
3. Vul in:
   - URL: `https://your-fastapi-url/webhooks/chatwoot`
   - Events: Select "Message Created"
4. Klik "Create Webhook"
5. Kopieer "Webhook Secret" → dit wordt `CHATWOOT_WEBHOOK_SECRET`

---

### Day 5: WhatsApp MCP Setup (Development)

**Wat is WhatsApp MCP?**
WhatsApp MCP is een Model Context Protocol server die WhatsApp Web emuleert voor development testing. Je hoeft geen WhatsApp Business API aan te vragen tot je klaar bent voor productie.

**Stap 1: Installeer WhatsApp MCP**

Eerst, laten we checken of je al een WhatsApp MCP server hebt:

```bash
# Check MCP servers in Claude Code config
ls -la ~/.config/claude-code/
```

Als je nog geen WhatsApp MCP hebt, laten we de Chatwoot MCP installeren die we al gemaakt hebben:

```bash
cd /Users/benomarlaamiri/Claude\ code\ project/whatsapp-recruitment-demo/chatwoot_mcp

# Installeer dependencies
npm install

# Build
npm run build

# Test
npm run dev
```

**Stap 2: Configureer MCP in Claude Code**

Voeg toe aan `~/.config/claude-code/mcp_config.json`:
```json
{
  "mcpServers": {
    "chatwoot": {
      "command": "node",
      "args": [
        "/Users/benomarlaamiri/Claude code project/whatsapp-recruitment-demo/chatwoot_mcp/build/index.js"
      ],
      "env": {
        "CHATWOOT_BASE_URL": "https://your-app.railway.app",
        "CHATWOOT_API_TOKEN": "your-api-token",
        "CHATWOOT_ACCOUNT_ID": "your-account-id"
      }
    }
  }
}
```

**Stap 3: Test MCP Connection**
```bash
# In Claude Code, run:
# (Dit zal je kunnen doen via MCP tools)

# Setup Chatwoot connection
chatwoot_setup(
  baseUrl="https://your-app.railway.app",
  apiToken="your-token",
  accountId="your-account-id"
)

# List inboxes
chatwoot_list_inboxes()

# Send test message
chatwoot_send_message(
  conversation_id=123,
  message="Test from MCP!",
  message_type="outgoing"
)
```

---

## 🎯 Week 2: FastAPI Integration

### Day 6-7: FastAPI Startup Configuration

**Stap 1: Creëer Main Application File**

```bash
cd /Users/benomarlaamiri/Claude\ code\ project/whatsapp-recruitment-demo
```

Ik ga nu `app/main.py` maken:

