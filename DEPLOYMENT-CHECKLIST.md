# 🚀 Deployment Checklist - Twilio WhatsApp Integration

**Enterprise-grade deployment workflow for Seldenrijk Auto WhatsApp System**

Based on: `ENTERPRISE-SAAS-DEPLOYMENT-GUIDE.md` research

---

## ✅ Pre-Deployment Checklist

### 1. Prerequisites Verification (5 minutes)

- [ ] **Twilio Account Active**
  - Account SID available
  - Auth Token available
  - WhatsApp sandbox configured
  - Phone number assigned

- [ ] **Railway Account Active**
  - Account created
  - Credit card added (if not on free tier)
  - Project linked

- [ ] **Doppler Account Setup** (Recommended Option)
  - Account created (https://doppler.com)
  - CLI installed (`brew install dopplerhq/cli/doppler`)
  - Authenticated (`doppler login`)

- [ ] **Development Tools Installed**
  ```bash
  ✓ Python 3.11+
  ✓ Poetry
  ✓ Railway CLI
  ✓ Doppler CLI (optional but recommended)
  ✓ jq (JSON parser)
  ```

### 2. Codebase Validation (10 minutes)

- [ ] **All Tests Passing**
  ```bash
  poetry run pytest tests/ -v --cov=app --cov-report=term-missing
  ```
  - Expected: 51 tests passed
  - Coverage: >80%

- [ ] **Linting & Type Checking**
  ```bash
  poetry run ruff check app/
  poetry run mypy app/
  ```

- [ ] **Security Scan**
  ```bash
  poetry run bandit -r app/
  ```

- [ ] **Dependencies Up-to-Date**
  ```bash
  poetry update
  poetry check
  ```

### 3. Environment Configuration Files (5 minutes)

- [ ] **`.env.example` Present & Complete**
  ```bash
  # Verify all required variables documented
  cat .env.example
  ```

- [ ] **`railway.toml` Configured**
  ```toml
  [build]
  builder = "NIXPACKS"
  buildCommand = "poetry install --no-dev"

  [deploy]
  numReplicas = 1
  restartPolicyType = "ON_FAILURE"
  restartPolicyMaxRetries = 3
  startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

  [env]
  PYTHON_VERSION = "3.11"
  ```

- [ ] **`Procfile` or Railway Start Command**
  ```
  web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

---

## 🔧 Deployment Execution - Option A: Doppler + Railway (Recommended)

**Total Time:** ~15 minutes
**Cost:** $0 (Doppler Free + Railway Free Tier)
**Security:** ⭐⭐⭐⭐⭐ Enterprise-grade

### Step 1: Install & Setup Doppler (5 minutes)

```bash
# Install Doppler CLI
brew install dopplerhq/cli/doppler

# Login
doppler login

# Create project
doppler projects create seldenrijk-auto

# Create environments
doppler configs create staging --project seldenrijk-auto
doppler configs create production --project seldenrijk-auto
```

**Checklist:**
- [ ] Doppler CLI installed
- [ ] Authenticated successfully
- [ ] Project created
- [ ] Staging config created
- [ ] Production config created

### Step 2: Add Secrets to Doppler (2 minutes)

```bash
# Setup staging
doppler setup --project seldenrijk-auto --config staging

# Add Twilio secrets
doppler secrets set TWILIO_ACCOUNT_SID="AC..."
doppler secrets set TWILIO_AUTH_TOKEN="..."
doppler secrets set TWILIO_WHATSAPP_NUMBER="whatsapp:+31850000000"

# Add other secrets
doppler secrets set ANTHROPIC_API_KEY="sk-ant-..."
doppler secrets set CHATWOOT_API_KEY="..."
doppler secrets set CHATWOOT_BASE_URL="https://app.chatwoot.com"
doppler secrets set CHATWOOT_ACCOUNT_ID="123456"

# Optional: Database
doppler secrets set DATABASE_URL="postgresql://..."

# Verify
doppler secrets
```

**Checklist:**
- [ ] All Twilio secrets added
- [ ] Anthropic API key added
- [ ] Chatwoot credentials added
- [ ] Secrets verified with `doppler secrets`

### Step 3: Integrate Doppler with Railway (5 minutes)

**Option A: Railway Dashboard (Easiest)**

1. Open Railway: https://railway.app/dashboard
2. Select project: `seldenrijk-auto-whatsapp`
3. Go to: **Settings → Integrations**
4. Click: **Add Integration → Doppler**
5. Authorize Railway in Doppler
6. Select:
   - Project: `seldenrijk-auto`
   - Config: `staging` (for staging environment)
   - Config: `production` (for production environment)

**Option B: Doppler CLI**

```bash
# Install Railway integration
doppler integrations railway setup --project seldenrijk-auto --config staging

# Follow prompts to authenticate
```

**Checklist:**
- [ ] Integration added in Railway dashboard
- [ ] Secrets auto-syncing (check Railway variables)
- [ ] Both staging and production configured

### Step 4: Deploy to Railway Staging (1 minute)

```bash
# Link Railway project (first time only)
railway link

# Switch to staging environment
railway environment use staging

# Deploy
railway up

# Wait for deployment (usually 2-3 minutes)
railway status
```

**Checklist:**
- [ ] Railway project linked
- [ ] Staging environment selected
- [ ] Deployment successful
- [ ] Health check passing

### Step 5: Get Webhook URL & Configure Twilio (2 minutes)

```bash
# Get Railway domain
railway domain

# Webhook URL format:
# https://your-project.railway.app/api/webhooks/twilio
```

**Configure in Twilio Console:**

1. Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
2. Find: **"When a message comes in"**
3. Set URL: `https://your-project.railway.app/api/webhooks/twilio`
4. Method: **POST**
5. Click: **Save**

**Checklist:**
- [ ] Webhook URL retrieved
- [ ] URL configured in Twilio console
- [ ] Method set to POST
- [ ] Configuration saved

---

## 🔧 Deployment Execution - Option B: Railway Sealed Variables (Alternative)

**Total Time:** ~12 minutes
**Cost:** $0 (Railway Free Tier)
**Security:** ⭐⭐⭐ Good (manual rotation required)

### Step 1: Railway Login & Link (2 minutes)

```bash
# Login
railway login

# Link project
railway link
```

### Step 2: Create Staging Environment (1 minute)

```bash
# Create staging (if not exists)
railway environment create staging

# Use staging
railway environment use staging
```

### Step 3: Set Sealed Variables (2 minutes)

```bash
# Twilio credentials (SEALED = never visible in UI)
railway variables set TWILIO_ACCOUNT_SID="AC..." --sealed
railway variables set TWILIO_AUTH_TOKEN="..." --sealed
railway variables set TWILIO_WHATSAPP_NUMBER="whatsapp:+31850000000"

# Other secrets
railway variables set ANTHROPIC_API_KEY="sk-ant-..." --sealed
railway variables set CHATWOOT_API_KEY="..." --sealed
railway variables set CHATWOOT_BASE_URL="https://app.chatwoot.com"
railway variables set CHATWOOT_ACCOUNT_ID="123456"

# Optional
railway variables set DATABASE_URL="postgresql://..." --sealed

# Verify (values hidden)
railway variables
```

### Step 4: Deploy (1 minute)

```bash
railway up
```

### Step 5: Configure Twilio Webhook (2 minutes)

Same as Option A, Step 5.

### Step 6: Validate Deployment (5 minutes)

```bash
# Run validation script
./scripts/validate-deployment.sh staging
```

**Checklist:**
- [ ] All 10 validation checks passed
- [ ] Health endpoint responding
- [ ] Webhook endpoint exists
- [ ] Environment variables configured
- [ ] Logs showing no errors

---

## ✅ Post-Deployment Validation

### 1. Automated Validation (5 minutes)

```bash
# Run validation script
cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp
./scripts/validate-deployment.sh staging
```

**Expected Output:**
```
✓ Health check passed (HTTP 200)
✓ Twilio webhook endpoint exists (HTTP 405)
✓ Environment variables configured
✓ Twilio signature verification active (HTTP 401)
✓ Database check skipped (not configured)
✓ Response time acceptable (<1000ms)
✓ Webhook uses HTTPS
✓ Logs retrieved successfully
✓ SSL certificate valid
✓ Doppler integration active

Passed: 10 / 10
✓ ALL CHECKS PASSED
```

**Checklist:**
- [ ] 10/10 checks passed
- [ ] No errors in validation output

### 2. Manual WhatsApp Testing (10 minutes)

**Prerequisites:**
1. Join Twilio Sandbox
   - Send: `join <sandbox-word>` to your Twilio number
   - Confirm: "You are all set!"

2. Run E2E test script:
   ```bash
   ./scripts/test-whatsapp-e2e.sh staging
   ```

**Test Scenarios:**

1. **Car Inquiry Test**
   ```
   Send: "Hallo, ik zoek een Volkswagen Golf"
   Expected:
   - Intent: car_inquiry
   - Extraction: make=Volkswagen, model=Golf
   - Response: Helpful reply about Golf availability
   ```

2. **Price Question Test**
   ```
   Send: "Ik wil graag een auto kopen tussen 20k en 30k"
   Expected:
   - Intent: price_question
   - Extraction: min_price=20000, max_price=30000
   - Response: Cars in that price range
   ```

3. **Financing Test**
   ```
   Send: "Wat zijn de mogelijkheden voor financiering?"
   Expected:
   - Intent: financing_inquiry
   - Response: Financing options information
   ```

4. **Appointment Test**
   ```
   Send: "Kan ik een afspraak maken voor een proefrit?"
   Expected:
   - Intent: appointment_request
   - Response: Appointment scheduling info
   ```

5. **Complex Query Test**
   ```
   Send: "Zoek een diesel SUV met automaat onder de 150000 km"
   Expected:
   - Intent: car_inquiry
   - Extraction: fuel_type=diesel, body_type=SUV, transmission=automaat, max_mileage=150000
   - Response: Matching vehicle suggestions
   ```

**Checklist:**
- [ ] All 5 test scenarios passed
- [ ] Responses received within 3-5 seconds
- [ ] Intent detection accurate
- [ ] Extraction working correctly
- [ ] Chatwoot conversation created

### 3. Log Monitoring (Continuous)

```bash
# Monitor logs in real-time
railway logs --environment staging --follow

# Or with filtering
railway logs --environment staging | grep -E "ERROR|WARNING|🚗|✅"
```

**What to Look For:**
- ✅ No `ERROR` or `Exception` messages
- ✅ Twilio webhook signature verified
- ✅ Intent detection logs: "🧭 Router Agent"
- ✅ Extraction logs: "🚗 Extracting car preferences"
- ✅ Response sent logs: "✅ WhatsApp response sent"

**Checklist:**
- [ ] No errors in logs
- [ ] All agents running successfully
- [ ] Message flow complete (webhook → agents → response)

### 4. Performance Benchmarking (5 minutes)

```bash
# Response time test
for i in {1..10}; do
  curl -s -o /dev/null -w "Response $i: %{time_total}s\n" https://$(railway domain)/health
  sleep 1
done
```

**Expected Performance:**
- Health endpoint: <500ms
- Webhook processing: 2-5 seconds (includes LLM calls)
- Total user wait time: 3-6 seconds

**Checklist:**
- [ ] Average response time <500ms for health
- [ ] WhatsApp responses arriving within 3-6 seconds
- [ ] No timeout errors

---

## 🔄 Rollback Plan (Emergency)

If deployment fails or critical issues occur:

### Quick Rollback (1 minute)

```bash
# Option 1: Revert to previous deployment
railway rollback

# Option 2: Pause service
railway service pause

# Option 3: Re-enable WAHA temporarily
# (if you haven't removed it yet)
railway service resume waha-service
```

### Investigate & Fix

```bash
# Check logs
railway logs --environment staging | tail -100

# Check variables
railway variables

# Check deployment status
railway status

# Re-run validation
./scripts/validate-deployment.sh staging
```

**Checklist:**
- [ ] Rollback plan documented
- [ ] WAHA still available as backup (during migration)
- [ ] Contact information for Twilio support ready

---

## 🚀 Production Deployment (After Staging Validated)

**Only proceed when:**
- ✅ All staging tests passed
- ✅ 24 hours of staging stability
- ✅ User/stakeholder approval received

### Production Deployment Steps:

1. **Add Production Secrets to Doppler**
   ```bash
   doppler setup --project seldenrijk-auto --config production

   # Add production Twilio credentials
   doppler secrets set TWILIO_ACCOUNT_SID="AC..."
   doppler secrets set TWILIO_AUTH_TOKEN="..."
   doppler secrets set TWILIO_WHATSAPP_NUMBER="whatsapp:+31600000000"

   # Add production Chatwoot credentials
   doppler secrets set CHATWOOT_API_KEY="..."
   ```

2. **Deploy to Production**
   ```bash
   railway environment use production
   railway up
   ```

3. **Configure Production Webhook**
   - Go to Twilio Console
   - Update webhook URL to production domain
   - Test with production phone number

4. **Run Validation**
   ```bash
   ./scripts/validate-deployment.sh production
   ./scripts/test-whatsapp-e2e.sh production
   ```

5. **Monitor Closely**
   ```bash
   railway logs --environment production --follow
   ```

**Production Checklist:**
- [ ] Production secrets configured
- [ ] Deployment successful
- [ ] Webhook URL updated
- [ ] Validation passed (10/10 checks)
- [ ] Manual testing passed (5/5 scenarios)
- [ ] Monitoring active
- [ ] Alerts configured (if applicable)

---

## 📊 Success Criteria

### Technical Metrics

- ✅ **Uptime:** 99.9% (Railway guarantee)
- ✅ **Response Time:** <5 seconds end-to-end
- ✅ **Test Coverage:** >80%
- ✅ **Error Rate:** <0.1%

### Functional Requirements

- ✅ **Message Processing:** 100% of messages processed
- ✅ **Intent Detection:** >90% accuracy
- ✅ **Extraction:** >80% accuracy for car preferences
- ✅ **Response Quality:** Contextually appropriate responses

### Security Requirements

- ✅ **Signature Verification:** Twilio signature validated on every request
- ✅ **Secrets Management:** All secrets sealed/encrypted (Doppler or Railway Sealed)
- ✅ **HTTPS:** All communication over TLS 1.2+
- ✅ **Audit Logs:** Available (Doppler Team+ tier or Railway logs)

---

## 📞 Support & Troubleshooting

### Common Issues

1. **"401 Unauthorized" on Webhook**
   - **Cause:** Twilio signature verification failing
   - **Fix:**
     ```bash
     # Verify Auth Token is correct
     railway variables get TWILIO_AUTH_TOKEN

     # Check webhook URL (no trailing slash!)
     echo "https://$(railway domain)/api/webhooks/twilio"
     ```

2. **"No Response in WhatsApp"**
   - **Cause:** Webhook not configured or deployment failed
   - **Fix:**
     ```bash
     # Check deployment status
     railway status

     # Check logs for errors
     railway logs | grep ERROR

     # Re-run validation
     ./scripts/validate-deployment.sh staging
     ```

3. **"Slow Responses (>10 seconds)"**
   - **Cause:** Cold start or Anthropic API latency
   - **Fix:**
     - Check Anthropic API status
     - Consider upgrading Railway plan (more resources)
     - Enable keep-warm endpoint

4. **"Wrong Intent Detection"**
   - **Cause:** Router Agent needs tuning
   - **Fix:** Update prompts in `app/agents/router_agent.py`

### Support Contacts

- **Railway Support:** https://railway.app/help
- **Doppler Support:** support@doppler.com
- **Twilio Support:** https://support.twilio.com
- **Anthropic Support:** support@anthropic.com

---

## ✅ Final Sign-Off

**Deployment Completed By:** _________________
**Date:** _________________
**Environment:** Staging / Production
**Version:** v1.0.0 (Twilio Migration)

**Checklist:**
- [ ] All pre-deployment checks passed
- [ ] Deployment successful
- [ ] All validation tests passed (10/10)
- [ ] Manual testing completed (5/5 scenarios)
- [ ] Performance benchmarking acceptable
- [ ] Monitoring active
- [ ] Documentation updated
- [ ] Stakeholders notified

**Notes:**
_______________________________________________________________________
_______________________________________________________________________
_______________________________________________________________________

**Approved By:** _________________
**Date:** _________________

---

**Next Phase:** Day 4 - Production Deployment & WAHA Removal
