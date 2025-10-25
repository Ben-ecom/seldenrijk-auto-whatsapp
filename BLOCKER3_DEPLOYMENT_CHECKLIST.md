# ✅ BLOCKER 3 DEPLOYMENT CHECKLIST

**Critical P0 Security Fix - Webhook Signature Verification**

---

## PRE-DEPLOYMENT CHECKLIST

### 1. Secret Generation (5 minutes)

- [ ] Generate CHATWOOT webhook secret:
  ```bash
  openssl rand -hex 32
  ```

- [ ] Generate WAHA webhook secret:
  ```bash
  openssl rand -hex 32
  ```

- [ ] Generate 360DIALOG webhook secret:
  ```bash
  openssl rand -hex 32
  ```

- [ ] Store secrets in password manager (1Password, LastPass, etc.)
- [ ] Document secret rotation date (90 days from now)

**Expected Output Example:**
```
CHATWOOT: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
WAHA:     b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3
360DIAL:  c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4
```

---

### 2. Environment Configuration (5 minutes)

- [ ] Update `.env` file:
  ```bash
  CHATWOOT_WEBHOOK_SECRET=<generated-secret-1>
  WAHA_WEBHOOK_SECRET=<generated-secret-2>
  DIALOG360_WEBHOOK_SECRET=<generated-secret-3>
  ENVIRONMENT=production  # CRITICAL: Disable dev bypass
  ```

- [ ] Verify `.env` not committed to Git:
  ```bash
  git status  # Should NOT show .env
  ```

- [ ] Backup current `.env` before changes
- [ ] Verify all other environment variables still present

**Validation:**
```bash
# Check secrets are set
grep "WEBHOOK_SECRET" .env | wc -l
# Expected: 3 lines
```

---

### 3. Provider Configuration (10 minutes)

#### Chatwoot Setup
- [ ] Log into Chatwoot dashboard
- [ ] Navigate to: Settings → Integrations → Webhooks
- [ ] Add webhook URL: `https://your-api-domain.com/webhooks/chatwoot`
- [ ] Paste CHATWOOT_WEBHOOK_SECRET
- [ ] Enable HMAC verification
- [ ] Select events: `message_created`
- [ ] Save configuration
- [ ] Test webhook (use test button if available)

#### WAHA Setup
- [ ] Choose configuration method:

**Option A: Environment Variable (Recommended)**
```yaml
# docker-compose.yml
services:
  waha:
    environment:
      - WHATSAPP_HOOK_HMAC_KEY=<your-waha-secret>
```

**Option B: Session API**
```bash
curl -X POST http://waha:3000/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "default",
    "config": {
      "webhooks": [{
        "url": "https://your-api-domain.com/webhooks/waha",
        "events": ["message"],
        "hmac": {
          "key": "<your-waha-secret>",
          "algorithm": "sha512"
        }
      }]
    }
  }'
```

- [ ] Restart WAHA container: `docker-compose restart waha`
- [ ] Verify WAHA configuration: `curl http://waha:3000/api/sessions`

#### 360Dialog Setup
- [ ] Log into 360Dialog dashboard
- [ ] Navigate to: Webhooks configuration
- [ ] Add webhook URL: `https://your-api-domain.com/webhooks/360dialog`
- [ ] Paste DIALOG360_WEBHOOK_SECRET
- [ ] Enable signature verification
- [ ] Save configuration
- [ ] Test webhook (use test button if available)

---

### 4. Code Review (10 minutes)

- [ ] Review changes in `/app/security/webhook_auth.py`:
  ```bash
  git diff app/security/webhook_auth.py
  ```

- [ ] Review changes in `/app/api/webhooks.py`:
  ```bash
  git diff app/api/webhooks.py
  ```

- [ ] Verify `verify_waha_signature()` function exists
- [ ] Verify WAHA webhook endpoint calls signature verification
- [ ] Verify constant-time comparison used (`hmac.compare_digest`)
- [ ] Verify development mode bypass logic correct

**Expected Changes:**
- `webhook_auth.py`: +70 lines (WAHA verification function)
- `webhooks.py`: +30 lines (signature verification integration)
- `.env.example`: +5 lines (WAHA_WEBHOOK_SECRET)

---

### 5. Testing (15 minutes)

#### Unit Tests
- [ ] Run test suite:
  ```bash
  pytest tests/test_webhook_signature_verification.py -v
  ```

- [ ] Verify all tests pass (24+ tests)
- [ ] Check test coverage:
  ```bash
  pytest tests/test_webhook_signature_verification.py \
    --cov=app.security.webhook_auth \
    --cov-report=term-missing
  ```

- [ ] Expected coverage: >90%

**Expected Output:**
```
tests/test_webhook_signature_verification.py::TestChatwootSignatureVerification::test_valid_signature PASSED
tests/test_webhook_signature_verification.py::TestChatwootSignatureVerification::test_invalid_signature PASSED
...
======================== 24 passed in 2.34s ========================
```

#### Manual Testing (curl)
- [ ] Test Chatwoot invalid signature (should fail):
  ```bash
  curl -X POST http://localhost:8000/webhooks/chatwoot \
    -H "Content-Type: application/json" \
    -H "X-Chatwoot-Signature: invalid" \
    -d '{"test": "data"}'
  ```
  **Expected:** 403 Forbidden

- [ ] Test WAHA invalid signature (should fail):
  ```bash
  curl -X POST http://localhost:8000/webhooks/waha \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Hmac: invalid" \
    -H "X-Webhook-Hmac-Algorithm: sha512" \
    -d '{"test": "data"}'
  ```
  **Expected:** 403 Forbidden

- [ ] Test Chatwoot valid signature (should succeed):
  ```bash
  PAYLOAD='{"test":"data"}'
  SECRET="your-chatwoot-secret"
  SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

  curl -X POST http://localhost:8000/webhooks/chatwoot \
    -H "Content-Type: application/json" \
    -H "X-Chatwoot-Signature: $SIG" \
    -d "$PAYLOAD"
  ```
  **Expected:** 200 OK (or error unrelated to signature)

- [ ] Test WAHA valid signature (should succeed):
  ```bash
  PAYLOAD='{"event":"message","payload":{"id":"123"}}'
  SECRET="your-waha-secret"
  SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha512 -hmac "$SECRET" -hex | cut -d' ' -f2)

  curl -X POST http://localhost:8000/webhooks/waha \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Hmac: $SIG" \
    -H "X-Webhook-Hmac-Algorithm: sha512" \
    -d "$PAYLOAD"
  ```
  **Expected:** 200 OK

---

### 6. Documentation Review (5 minutes)

- [ ] Read `WEBHOOK_SECURITY_QUICKSTART.md` (5-minute setup guide)
- [ ] Skim `WEBHOOK_SETUP.md` (comprehensive guide)
- [ ] Review `BLOCKER3_IMPLEMENTATION_REPORT.md` (technical details)
- [ ] Check `WEBHOOK_SECURITY_FLOW.md` (security architecture)
- [ ] Verify all documentation files exist:
  ```bash
  ls -l WEBHOOK*.md BLOCKER3*.md
  ```

**Expected Files:**
```
WEBHOOK_SETUP.md (500+ lines)
WEBHOOK_SECURITY_QUICKSTART.md (200+ lines)
WEBHOOK_SECURITY_FLOW.md (400+ lines)
BLOCKER3_IMPLEMENTATION_REPORT.md (800+ lines)
BLOCKER3_SUMMARY.md (300+ lines)
BLOCKER3_DEPLOYMENT_CHECKLIST.md (this file)
```

---

### 7. Backup and Rollback Plan (5 minutes)

- [ ] Backup current production `.env`:
  ```bash
  cp .env .env.backup.$(date +%Y%m%d)
  ```

- [ ] Backup current `docker-compose.yml`:
  ```bash
  cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d)
  ```

- [ ] Document rollback procedure:
  ```bash
  # If deployment fails:
  cp .env.backup.YYYYMMDD .env
  cp docker-compose.yml.backup.YYYYMMDD docker-compose.yml
  docker-compose restart api
  docker-compose restart waha
  ```

- [ ] Verify backups created:
  ```bash
  ls -l *.backup.*
  ```

---

## DEPLOYMENT CHECKLIST

### 1. Code Deployment (5 minutes)

- [ ] Commit changes to Git:
  ```bash
  git add app/security/webhook_auth.py
  git add app/api/webhooks.py
  git add .env.example
  git add WEBHOOK*.md BLOCKER3*.md
  git add tests/test_webhook_signature_verification.py
  git commit -m "feat: Add webhook signature verification (P0 fix)"
  ```

- [ ] Push to repository:
  ```bash
  git push origin main
  ```

- [ ] Tag release (optional):
  ```bash
  git tag -a v5.1.0-blocker3 -m "Webhook signature verification"
  git push origin v5.1.0-blocker3
  ```

---

### 2. Infrastructure Update (5 minutes)

- [ ] Update production `.env` with new secrets
- [ ] Update `docker-compose.yml` with WAHA HMAC configuration
- [ ] Verify file permissions:
  ```bash
  chmod 600 .env  # Secure permissions
  ```

- [ ] Verify Docker Compose syntax:
  ```bash
  docker-compose config
  ```

---

### 3. Service Restart (3 minutes)

- [ ] Stop services gracefully:
  ```bash
  docker-compose stop api
  docker-compose stop waha
  ```

- [ ] Start services with new configuration:
  ```bash
  docker-compose up -d api
  docker-compose up -d waha
  ```

- [ ] Verify services started:
  ```bash
  docker-compose ps
  ```

**Expected Output:**
```
NAME     SERVICE   STATUS    PORTS
api      api       running   0.0.0.0:8000->8000/tcp
waha     waha      running   0.0.0.0:3000->3000/tcp
```

- [ ] Check service logs for errors:
  ```bash
  docker-compose logs api | tail -50
  docker-compose logs waha | tail -50
  ```

---

### 4. Health Checks (5 minutes)

- [ ] API health check:
  ```bash
  curl http://localhost:8000/health
  ```
  **Expected:** `{"status": "healthy"}`

- [ ] WAHA health check:
  ```bash
  curl http://localhost:3000/api/sessions
  ```
  **Expected:** JSON with session list

- [ ] Check API logs for startup errors:
  ```bash
  docker-compose logs api | grep -i error
  ```
  **Expected:** No critical errors

- [ ] Check WAHA logs for configuration:
  ```bash
  docker-compose logs waha | grep -i hmac
  ```
  **Expected:** HMAC configuration loaded

---

### 5. Functional Testing (10 minutes)

#### Test 1: Invalid Signature (Should Fail)
- [ ] Send webhook with invalid signature:
  ```bash
  curl -X POST https://your-api-domain.com/webhooks/waha \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Hmac: invalid-signature" \
    -H "X-Webhook-Hmac-Algorithm: sha512" \
    -d '{"event": "message", "payload": {"id": "test-123"}}'
  ```
  **Expected:** 403 Forbidden

- [ ] Check logs for signature error:
  ```bash
  docker-compose logs api | grep "Invalid.*signature"
  ```
  **Expected:** Error log with timestamp

#### Test 2: Valid Signature (Should Succeed)
- [ ] Calculate valid signature:
  ```bash
  PAYLOAD='{"event": "message", "payload": {"id": "test-456"}}'
  SECRET="your-waha-webhook-secret"
  SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha512 -hmac "$SECRET" -hex | cut -d' ' -f2)
  echo "Signature: $SIG"
  ```

- [ ] Send webhook with valid signature:
  ```bash
  curl -X POST https://your-api-domain.com/webhooks/waha \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Hmac: $SIG" \
    -H "X-Webhook-Hmac-Algorithm: sha512" \
    -d "$PAYLOAD"
  ```
  **Expected:** 200 OK

- [ ] Check logs for successful verification:
  ```bash
  docker-compose logs api | grep "webhook signature verified"
  ```
  **Expected:** Success log with timestamp

#### Test 3: End-to-End Webhook Flow
- [ ] Send test WhatsApp message to system
- [ ] Verify WAHA webhook received and processed
- [ ] Check message appears in Chatwoot
- [ ] Reply from Chatwoot
- [ ] Verify reply sent via WAHA to WhatsApp

**All steps should work without signature errors**

---

### 6. Monitoring Setup (10 minutes)

#### Prometheus Metrics
- [ ] Access Prometheus: `http://your-prometheus:9090`
- [ ] Query signature error metrics:
  ```promql
  webhook_signature_errors_total
  ```
  **Expected:** 0 errors

- [ ] Query webhook request rate:
  ```promql
  rate(webhook_requests_total[5m])
  ```
  **Expected:** Non-zero rate if webhooks active

#### Grafana Dashboard
- [ ] Access Grafana: `http://your-grafana:3000`
- [ ] Create alert for signature errors:
  ```yaml
  - alert: WebhookSignatureAttack
    expr: rate(webhook_signature_errors_total[5m]) > 5
    for: 5m
    annotations:
      summary: "Potential webhook attack"
      description: "{{ $value }} signature errors/sec"
  ```

- [ ] Test alert (trigger by sending invalid webhooks)
- [ ] Verify alert fires after 5 minutes
- [ ] Resolve test alert

#### Sentry Error Tracking
- [ ] Access Sentry dashboard
- [ ] Filter for webhook-related errors
- [ ] Verify no signature verification errors
- [ ] Set up alert for new webhook errors

---

### 7. Documentation (5 minutes)

- [ ] Update team wiki/documentation with:
  - Webhook security changes
  - Secret rotation schedule
  - Troubleshooting procedures
  - Contact for security issues

- [ ] Share deployment notes with team:
  - Changes deployed
  - Testing performed
  - Monitoring setup
  - Known issues (if any)

- [ ] Schedule training session on webhook security
- [ ] Document secret rotation procedure in runbook

---

## POST-DEPLOYMENT VALIDATION

### 1. Immediate Validation (15 minutes)

- [ ] Monitor logs for 15 minutes:
  ```bash
  docker-compose logs -f api | grep webhook
  ```

- [ ] Verify no signature errors in production traffic
- [ ] Check Prometheus metrics every 5 minutes
- [ ] Test webhook flow with real message (if possible)
- [ ] Verify no customer-reported issues

**Success Criteria:**
- ✅ No signature verification errors
- ✅ All webhooks processing normally
- ✅ Response times < 200ms
- ✅ No customer impact

---

### 2. Extended Monitoring (24 hours)

#### Hour 1
- [ ] Check logs every 15 minutes
- [ ] Verify webhook request rate normal
- [ ] Monitor signature error metrics
- [ ] Check for any anomalies

#### Hour 6
- [ ] Review Sentry errors (should be 0)
- [ ] Check Prometheus metrics
- [ ] Verify no performance degradation
- [ ] Review Grafana dashboard

#### Hour 24
- [ ] Full system health check
- [ ] Review all webhook logs
- [ ] Verify secret rotation reminders set
- [ ] Document any issues encountered

---

### 3. Performance Validation

- [ ] Compare webhook response times (before/after):
  ```bash
  # Query Prometheus
  histogram_quantile(0.95,
    rate(http_request_duration_seconds_bucket{
      endpoint=~"/webhooks/.*"
    }[5m])
  )
  ```

- [ ] Verify p95 latency < 200ms
- [ ] Check CPU/memory usage unchanged
- [ ] Verify no increased error rate

**Acceptable Overhead:**
- +1-5ms latency (HMAC calculation)
- No increase in CPU usage
- No increase in memory usage

---

## ROLLBACK PROCEDURE

**If Issues Detected:**

### 1. Immediate Rollback (2 minutes)

```bash
# Stop services
docker-compose stop api waha

# Restore backups
cp .env.backup.$(date +%Y%m%d) .env
cp docker-compose.yml.backup.$(date +%Y%m%d) docker-compose.yml

# Restart services
docker-compose up -d api waha

# Verify services healthy
docker-compose ps
curl http://localhost:8000/health
```

### 2. Provider Configuration Revert (5 minutes)

- [ ] Chatwoot: Disable HMAC verification temporarily
- [ ] WAHA: Remove HMAC configuration
- [ ] 360Dialog: Disable signature verification temporarily

### 3. Post-Rollback Actions

- [ ] Document rollback reason
- [ ] Identify root cause of failure
- [ ] Create incident report
- [ ] Schedule fix and re-deployment
- [ ] Notify stakeholders

---

## SIGN-OFF

### Pre-Deployment Sign-Off

- [ ] **Developer:** Code reviewed and tested
  - Name: ________________
  - Date: ________________

- [ ] **DevOps:** Infrastructure ready for deployment
  - Name: ________________
  - Date: ________________

- [ ] **Security:** Security requirements validated
  - Name: ________________
  - Date: ________________

### Post-Deployment Sign-Off

- [ ] **Developer:** Deployment successful, monitoring confirmed
  - Name: ________________
  - Date: ________________
  - Time: ________________

- [ ] **DevOps:** Infrastructure stable, no issues
  - Name: ________________
  - Date: ________________
  - Time: ________________

- [ ] **Security:** Security controls active and verified
  - Name: ________________
  - Date: ________________
  - Time: ________________

---

## COMPLETION CRITERIA

All criteria must be met for successful deployment:

- [x] All pre-deployment tests pass
- [x] Secrets generated and stored securely
- [x] Providers configured with HMAC
- [x] Code deployed and services restarted
- [x] Health checks pass
- [x] Functional tests pass (valid/invalid signatures)
- [x] Monitoring configured and active
- [x] Documentation updated
- [x] Team notified
- [x] 24-hour monitoring complete with no issues

**If all criteria met:**
✅ **DEPLOYMENT SUCCESSFUL - BLOCKER 3 RESOLVED**

---

## NEXT STEPS

### Immediate (Week 1)
- [ ] Schedule secret rotation reminder (90 days)
- [ ] Conduct team training on webhook security
- [ ] Review and optimize monitoring alerts
- [ ] Update incident response procedures

### Short-term (Month 1)
- [ ] Quarterly security review of webhook endpoints
- [ ] Penetration test webhook security
- [ ] Document lessons learned
- [ ] Implement automated secret rotation (if needed)

### Long-term (Quarter 1)
- [ ] Third-party security audit
- [ ] Consider mutual TLS for webhooks
- [ ] Evaluate additional security controls
- [ ] Update security compliance documentation

---

**Deployment Date:** ____________________
**Deployment Time:** ____________________
**Deployed By:** ____________________
**Status:** ⬜ Pending / ✅ Complete / ❌ Rolled Back

---

## Support Contacts

**During Deployment:**
- Developer: [Name] - [Email] - [Phone]
- DevOps: [Name] - [Email] - [Phone]
- Security: [Name] - [Email] - [Phone]

**Post-Deployment Issues:**
- On-call: [Pager/Phone Number]
- Slack: #webhook-security-incidents
- Email: security@your-company.com

**Documentation:**
- Quick Start: `WEBHOOK_SECURITY_QUICKSTART.md`
- Full Guide: `WEBHOOK_SETUP.md`
- Technical Report: `BLOCKER3_IMPLEMENTATION_REPORT.md`
- Security Flow: `WEBHOOK_SECURITY_FLOW.md`
