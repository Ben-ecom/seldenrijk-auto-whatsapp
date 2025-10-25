# 🚀 Quick Start Guide - WhatsApp Recruitment Platform v5.1

**Geschat voor setup:** 30-60 minuten
**Kosten:** ~€15/maand (Railway + Sentry free tier)

---

## ✅ Prerequisites

Voordat je begint, zorg dat je het volgende hebt:

- [ ] Python 3.11+ geïnstalleerd
- [ ] Docker & Docker Compose geïnstalleerd
- [ ] Railway account (gratis: railway.app)
- [ ] Sentry account (gratis: sentry.io)
- [ ] Supabase project (gratis: supabase.com)
- [ ] Git geïnstalleerd

---

## 📦 Stap 1: Repository Setup (5 minuten)

```bash
# Clone repository
cd /Users/benomarlaamiri/Claude\ code\ project/whatsapp-recruitment-demo

# Installeer dependencies
pip install -r requirements.txt

# Genereer veilige secrets
python scripts/generate_secrets.py
```

**Output:**
```
🔐 Generating Secure Secrets...
CHATWOOT_WEBHOOK_SECRET=xxx
DIALOG360_WEBHOOK_SECRET=xxx
WHATSAPP_VERIFY_TOKEN=xxx
```

**⚠️ Bewaar deze secrets veilig!** Je hebt ze nodig in stap 3.

---

## 🗄️ Stap 2: Database Setup (10 minuten)

### A. Supabase Project Aanmaken

1. Ga naar [supabase.com](https://supabase.com)
2. Klik "New Project"
3. Vul in:
   - Name: `whatsapp-recruitment`
   - Database Password: **Bewaar dit!**
   - Region: `West EU (Frankfurt)`
4. Wacht 2 minuten voor setup

### B. Database Connection Info

1. Ga naar Settings → Database
2. Kopieer:
   - `Connection string` → dit wordt `DATABASE_URL`
   - Vervang `[YOUR-PASSWORD]` met je database password

3. Ga naar Settings → API
4. Kopieer:
   - `URL` → dit wordt `SUPABASE_URL`
   - `service_role key` → dit wordt `SUPABASE_KEY`

### C. Run Migrations

```bash
# Vervang connection string met jouw gegevens
export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres"

# Run GDPR tables migratie
psql $DATABASE_URL < migrations/001_gdpr_tables.sql
```

**Verwacht output:**
```
CREATE TABLE
CREATE INDEX
CREATE TABLE
...
✅ Migratie succesvol!
```

---

## 🚂 Stap 3: Railway Deployment - Chatwoot (15 minuten)

### A. Deploy Chatwoot

1. Ga naar [railway.app](https://railway.app)
2. Klik "New Project"
3. Select "Deploy from Template"
4. Zoek "Chatwoot" of gebruik: https://railway.app/template/chatwoot
5. Klik "Deploy Now"

**Railway zet automatisch:**
- PostgreSQL database
- Redis instance
- Chatwoot applicatie

### B. Configureer Environment Variables

Na deployment, ga naar Chatwoot service → Variables:

```env
# Railway zet automatisch:
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
RAILS_ENV=production

# JIJ MOET TOEVOEGEN:
FRONTEND_URL=https://your-chatwoot-app.up.railway.app
INSTALLATION_NAME=YourCompany Recruitment

# Email (optioneel voor notificaties)
MAILER_SENDER_EMAIL=support@yourdomain.com
SMTP_ADDRESS=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-key

# Storage
ACTIVE_STORAGE_SERVICE=local
```

### C. Wacht op Deploy & Test

```bash
# Wacht 5-10 minuten
# Test of Chatwoot live is:
curl https://your-chatwoot-app.up.railway.app/api

# Verwacht:
{"version": "3.x.x", "timestamp": "..."}
```

### D. Chatwoot Initial Setup

1. Ga naar `https://your-chatwoot-app.up.railway.app`
2. Klik "Sign up"
3. Creëer admin account:
   - Email: jouw admin email
   - Full Name: jouw naam
   - Password: sterk wachtwoord
4. Verifieer email

### E. API Token & Account ID

**API Token:**
1. Ga naar Settings → Profile
2. Scroll naar "Access Token"
3. Klik "Generate new token"
4. Kopieer → dit wordt `CHATWOOT_API_TOKEN`

**Account ID:**
```bash
# Method 1: Browser console (F12)
console.log(window.chatwootConfig.accountId)

# Method 2: API call
curl https://your-chatwoot-app.up.railway.app/api/v1/accounts \
  -H "api_access_token: YOUR_TOKEN"

# Response:
[{"id": 123456, "name": "YourCompany"}]
```

Kopieer `id` → dit wordt `CHATWOOT_ACCOUNT_ID`

### F. Configureer Webhook

1. Ga naar Settings → Webhooks
2. Klik "Add Webhook"
3. Vul in:
   - URL: `https://your-fastapi-url/webhooks/chatwoot` (komt in stap 4)
   - Events: ✅ "Message Created"
4. Klik "Create Webhook"
5. Kopieer "Webhook Secret" → **BEWAAR DEZE!**

**⚠️ Let op:** Je hebt de FastAPI URL nodig uit stap 4. Kom hier terug na stap 4!

---

## 🔧 Stap 4: Environment Variables (5 minuten)

```bash
cd /Users/benomarlaamiri/Claude\ code\ project/whatsapp-recruitment-demo

# Kopieer template
cp .env.example .env

# Bewerk .env
nano .env  # of gebruik VSCode/je favoriete editor
```

Vul in:

```env
# ============ AI MODELS ============
ANTHROPIC_API_KEY=sk-ant-xxx  # Van console.anthropic.com
OPENAI_API_KEY=sk-xxx  # Van platform.openai.com

# ============ DATABASE (VAN STAP 2) ============
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres

# ============ CHATWOOT (VAN STAP 3) ============
CHATWOOT_BASE_URL=https://your-chatwoot-app.up.railway.app
CHATWOOT_API_TOKEN=xxx  # Van Settings → Profile
CHATWOOT_ACCOUNT_ID=123456  # Van console.log(window.chatwootConfig.accountId)
CHATWOOT_WEBHOOK_SECRET=xxx  # Van stap 1 (generate_secrets.py)

# ============ WHATSAPP (VAN STAP 1) ============
DIALOG360_API_KEY=xxx  # Laat leeg voor nu (komt later)
DIALOG360_WEBHOOK_SECRET=xxx  # Van stap 1
WHATSAPP_VERIFY_TOKEN=xxx  # Van stap 1

# ============ CELERY/REDIS ============
REDIS_URL=redis://redis:6379/0  # Lokaal, Railway wijzigt dit automatisch

# ============ MONITORING ============
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx  # Zie hieronder
ENVIRONMENT=development  # development | staging | production
LOG_LEVEL=INFO
```

### Sentry Setup (optioneel maar aanbevolen):

1. Ga naar [sentry.io](https://sentry.io)
2. Sign up (gratis tier)
3. Create new project:
   - Platform: Python
   - Project name: `whatsapp-recruitment`
4. Kopieer DSN → dit is `SENTRY_DSN`

---

## 🐳 Stap 5: Local Testing (10 minuten)

```bash
# Start alle services
docker-compose up -d

# Check of alles draait
docker-compose ps

# Verwacht:
# recruitment-api          running
# recruitment-redis        running
# recruitment-celery-worker running
# recruitment-celery-beat  running
```

### Test Endpoints

```bash
# Run test script
./scripts/test_deployment.sh

# Of handmatig:
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
```

**Verwacht output:**
```
🧪 Testing WhatsApp Recruitment Platform Deployment
================================
1️⃣  Testing basic health check... ✅ PASSED
2️⃣  Testing detailed health check... ✅ PASSED
3️⃣  Testing liveness probe... ✅ PASSED
4️⃣  Testing readiness probe... ✅ PASSED
5️⃣  Testing Prometheus metrics... ✅ PASSED
6️⃣  Testing webhook security... ✅ PASSED
================================
✅ All tests passed!
```

### Test Webhook Security

```bash
# Test zonder signature (moet falen)
curl -X POST http://localhost:8000/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Verwacht: 403 Forbidden
{"detail":"Missing X-Chatwoot-Signature header"}
```

### Run Unit Tests

```bash
# Installeer test dependencies (als niet gedaan)
pip install pytest pytest-cov pytest-asyncio

# Run tests
pytest tests/ -v

# Met coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🔗 Stap 6: Connect Chatwoot → FastAPI (5 minuten)

### A. Deploy FastAPI naar Railway

1. Ga naar Railway dashboard
2. Klik "New Service" in je project
3. Select "GitHub Repo" of "Docker Image"
4. Connect repo: `whatsapp-recruitment-demo`
5. Railway detecteert `Dockerfile.api` automatisch

### B. Configureer Environment Variables

Kopieer ALLE variabelen uit je lokale `.env` naar Railway:

```
ANTHROPIC_API_KEY=xxx
OPENAI_API_KEY=xxx
SUPABASE_URL=xxx
SUPABASE_KEY=xxx
DATABASE_URL=xxx
CHATWOOT_BASE_URL=xxx
CHATWOOT_API_TOKEN=xxx
CHATWOOT_ACCOUNT_ID=xxx
CHATWOOT_WEBHOOK_SECRET=xxx
DIALOG360_WEBHOOK_SECRET=xxx
WHATSAPP_VERIFY_TOKEN=xxx
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=xxx
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### C. Get FastAPI URL

Na deployment:
```
https://your-fastapi-app.up.railway.app
```

### D. Update Chatwoot Webhook

1. Ga terug naar Chatwoot → Settings → Webhooks
2. Edit je webhook
3. Update URL naar: `https://your-fastapi-app.up.railway.app/webhooks/chatwoot`
4. Save

### E. Test Webhook Connection

```bash
# Send test message in Chatwoot
# Check FastAPI logs:
docker-compose logs -f api

# Of in Railway:
# Klik op FastAPI service → Logs tab
```

---

## ✅ Stap 7: Verification Checklist

- [ ] **Database:** Supabase connection werkt
- [ ] **Chatwoot:** Deployed en accessible
- [ ] **FastAPI:** Health endpoints returnen 200
- [ ] **Redis:** Celery workers connected
- [ ] **Sentry:** Errors worden getracked
- [ ] **Webhook:** Chatwoot → FastAPI verbinding werkt
- [ ] **Tests:** `pytest tests/` passed

---

## 🎉 Je bent Klaar voor Week 3-8!

Wat je nu hebt:
- ✅ Chatwoot deployment (Railway)
- ✅ FastAPI backend met P0 fixes
- ✅ Database met GDPR compliance
- ✅ Webhook security (HMAC + rate limiting)
- ✅ Celery async processing
- ✅ Sentry error tracking
- ✅ Prometheus metrics
- ✅ Health checks

**Volgende stappen:**
1. Week 3-4: LangGraph met 4 agents implementeren
2. Week 5: Agentic RAG toevoegen
3. Week 6: CRM integratie
4. Week 7: 360Dialog productie WhatsApp
5. Week 8: White-label branding

---

## 🆘 Troubleshooting

### "Database connection failed"
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check if IP is whitelisted in Supabase
# Supabase → Settings → Database → Connection Pooling → Add your IP
```

### "Chatwoot webhook not working"
```bash
# Check FastAPI logs
docker-compose logs api | grep webhook

# Verify signature secret matches
echo $CHATWOOT_WEBHOOK_SECRET

# Test manually
curl -X POST http://localhost:8000/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -H "X-Chatwoot-Signature: <calculate-hmac>" \
  -d '{"event":"message_created"}'
```

### "Celery tasks not processing"
```bash
# Check Celery worker
docker-compose logs celery-worker

# Check Redis connection
docker-compose exec redis redis-cli ping
# Verwacht: PONG

# Restart workers
docker-compose restart celery-worker celery-beat
```

### "Sentry not receiving errors"
```bash
# Test Sentry manually
python -c "
from app.monitoring.sentry_config import init_sentry, capture_message
init_sentry()
capture_message('Test message from WhatsApp Platform', level='info')
print('✅ Test sent to Sentry')
"

# Check Sentry dashboard: sentry.io/organizations/your-org/issues/
```

---

## 📚 Volgende Documentatie

- **WEEK-1-2-IMPLEMENTATION.md** - Complete Week 1-2 guide
- **P0-FIXES-IMPLEMENTATION-SUMMARY.md** - P0 fixes details
- **PRD-V5.1-CHATWOOT-CENTRIC.md** - Complete product requirements
- **IMPLEMENTATION-ROADMAP-V5.1.md** - Full 8-week roadmap

---

**Kosten Overzicht:**

| Service | Prijs/maand | Status |
|---------|-------------|--------|
| Railway (Chatwoot) | ~€5-10 | ✅ Running |
| Railway (FastAPI) | ~€5-10 | ✅ Running |
| Supabase | €0 (free tier) | ✅ Running |
| Sentry | €0 (free tier) | ✅ Running |
| **Totaal** | **~€10-20/maand** | **✅** |

*360Dialog WhatsApp (~€50/maand) komt in Week 7*

---

**Vragen? Check de troubleshooting sectie of raadpleeg de volledige documentatie!** 🚀
