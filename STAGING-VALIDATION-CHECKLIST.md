# Staging Validation Checklist - Day 3
## WhatsApp AI Agent - Twilio Integration Testing

**Date:** 2025-10-25
**Environment:** Railway Staging
**Duration:** 8 hours (estimated)

---

## PHASE 1: DEPLOYMENT PREPARATION (1.5 HOURS)

### Railway Setup
- [ ] Railway CLI installed and authenticated
- [ ] Railway project linked successfully
- [ ] Staging environment exists (or created)
- [ ] Currently on staging environment (`railway environment`)

### Environment Variables - Core (Existing)
- [ ] ANTHROPIC_API_KEY set
- [ ] OPENAI_API_KEY set
- [ ] SUPABASE_URL set
- [ ] SUPABASE_KEY set
- [ ] CHATWOOT_BASE_URL set
- [ ] CHATWOOT_API_TOKEN set
- [ ] REDIS_URL auto-injected (Railway addon)
- [ ] DATABASE_URL set (Supabase PostgreSQL)

### Environment Variables - Twilio (New)
- [ ] TWILIO_ACCOUNT_SID set (starts with AC...)
- [ ] TWILIO_AUTH_TOKEN set (secret token)
- [ ] TWILIO_WHATSAPP_NUMBER set (format: whatsapp:+14155238886)
- [ ] TWILIO_WEBHOOK_SECRET set (optional, 32 random chars)

### Deployment Files
- [ ] `railway.toml` exists and configured
- [ ] `Dockerfile.production` exists
- [ ] `docker-compose.yml` configured
- [ ] `start.sh` script exists
- [ ] All Twilio integration code committed (Day 1 & Day 2)

---

## PHASE 2: DEPLOYMENT (1 HOUR)

### Build & Deploy
- [ ] Code deployed to Railway: `railway up`
- [ ] Build completed successfully (check logs)
- [ ] Docker image built without errors
- [ ] Dependencies installed (twilio==8.10.0)
- [ ] All services started (API, Redis, Celery, Beat)

### Service Health
- [ ] API service running (port 8000)
- [ ] Redis connected successfully
- [ ] Supabase database connected
- [ ] Celery worker running
- [ ] Celery Beat scheduler running

### Domain Configuration
- [ ] Railway domain generated (`railway domain`)
- [ ] Domain format: `https://<project>-staging.up.railway.app`
- [ ] Domain accessible via browser
- [ ] SSL certificate valid (HTTPS working)

### Health Check Endpoints
- [ ] `/health` returns 200 OK
- [ ] `/health/detailed` shows all services healthy
- [ ] `/health/readiness` returns ready
- [ ] `/webhooks/twilio/whatsapp` endpoint exists (returns 403 without signature)

---

## PHASE 3: TWILIO CONFIGURATION (30 MINUTES)

### Twilio Console Setup
- [ ] Logged into Twilio Console (https://console.twilio.com/)
- [ ] Account SID and Auth Token verified
- [ ] WhatsApp Sandbox configured

### Webhook Configuration
- [ ] Navigate to: Messaging → Settings → WhatsApp sandbox settings
- [ ] Set "When a message comes in": POST `https://<staging-domain>/webhooks/twilio/whatsapp`
- [ ] Webhook URL saved successfully
- [ ] Webhook method set to POST

### Sandbox Testing Setup
- [ ] Join command sent to sandbox: `join <keyword>` to +1 415 523 8886
- [ ] Confirmation received from Twilio
- [ ] Ready to send test messages

---

## PHASE 4: FUNCTIONAL TESTING (2 HOURS)

### Test 1: Basic Message Reception
**Test Message:** "Hallo"
**Expected:**
- [ ] Twilio receives message
- [ ] Webhook endpoint called
- [ ] Signature verified successfully
- [ ] Message logged in Railway logs
- [ ] Response sent within 2-6 seconds
- [ ] User receives response via WhatsApp

**Result:** ____________
**Latency:** ________ seconds
**Notes:** ____________________

---

### Test 2: Car Inquiry Intent
**Test Message:** "Ik zoek een Volkswagen Golf"
**Expected:**
- [ ] Message routed through LangGraph
- [ ] Router classifies intent: `car_inquiry`
- [ ] Extraction extracts: `{make: "Volkswagen", model: "Golf"}`
- [ ] Conversation agent generates relevant response
- [ ] Response mentions Volkswagen Golf inventory
- [ ] Response sent successfully

**Result:** ____________
**Latency:** ________ seconds
**Extracted Data:** ____________________
**Notes:** ____________________

---

### Test 3: Appointment Request
**Test Message:** "Ik wil graag een afspraak maken"
**Expected:**
- [ ] Intent classified: `appointment_request`
- [ ] Appointment agent invoked
- [ ] Available time slots suggested
- [ ] Response includes booking options

**Result:** ____________
**Notes:** ____________________

---

### Test 4: Price Question
**Test Message:** "Wat kost een Golf 8 van 2020?"
**Expected:**
- [ ] Intent classified: `price_inquiry`
- [ ] Extraction extracts: `{make: "Golf", model: "8", year: "2020"}`
- [ ] Database queried for price range
- [ ] Response includes price information

**Result:** ____________
**Extracted Data:** ____________________
**Notes:** ____________________

---

### Test 5: Edge Cases
**Test 5a: Empty Message**
- [ ] Webhook receives empty body
- [ ] Error handled gracefully
- [ ] User receives friendly error message

**Test 5b: Special Characters**
**Message:** "Auto met €25.000 🚗"
- [ ] Special characters handled (€, emoji)
- [ ] Response generated correctly

**Test 5c: Very Long Message (>1600 chars)**
- [ ] Long message accepted
- [ ] Response generated (not truncated incorrectly)

**Test 5d: Rapid Messages (3 in a row)**
**Messages:** "Test 1", "Test 2", "Test 3" (sent 1 second apart)
- [ ] All 3 messages received
- [ ] All 3 processed independently
- [ ] All 3 responses sent
- [ ] No race conditions or duplicates

**Results:** ____________________
**Notes:** ____________________

---

## PHASE 5: DEDUPLICATION TESTING (30 MINUTES)

### Test 6: Duplicate Message Prevention
**Setup:** Send same MessageSid twice

**Step 1: First message**
```bash
MessageSid=SM_TEST_12345
Body="Test deduplication"
```
- [ ] First message processed successfully
- [ ] Response sent to user
- [ ] MessageSid cached in Redis (TTL: 300s)

**Step 2: Duplicate message (same MessageSid)**
- [ ] Webhook receives duplicate
- [ ] Deduplication check detects duplicate
- [ ] Message NOT processed again
- [ ] Response: 200 OK (but logs show "duplicate ignored")
- [ ] User does NOT receive duplicate response

**Step 3: Verify Redis cache**
- [ ] Redis key exists: `twilio:dedup:SM_TEST_12345`
- [ ] TTL is ~300 seconds (5 minutes)
- [ ] Key expires after TTL

**Result:** ____________
**Notes:** ____________________

---

## PHASE 6: PERFORMANCE TESTING (2 HOURS)

### Test 7: Single Message Latency
**Objective:** Measure end-to-end latency

**Method:**
```bash
time curl -X POST "${STAGING_URL}/webhooks/twilio/whatsapp" \
  -H "X-Twilio-Signature: ${VALID_SIGNATURE}" \
  -d "MessageSid=SM_LATENCY_TEST&From=whatsapp:+31612345678&Body=Test"
```

**Results:**
- [ ] Total latency: ________ seconds
- [ ] Target: < 3 seconds
- [ ] Status: PASS / FAIL

**Breakdown:**
- Webhook reception: ________ ms
- Deduplication check: ________ ms
- LangGraph processing: ________ ms
- Twilio API send: ________ ms

---

### Test 8: Concurrent Messages (10 simultaneous)
**Objective:** Test handling of concurrent requests

**Method:**
```bash
for i in {1..10}; do
  curl -X POST "${STAGING_URL}/webhooks/twilio/whatsapp" \
    -H "X-Twilio-Signature: ${VALID_SIGNATURE}" \
    -d "MessageSid=SM_CONCURRENT_${i}&From=whatsapp:+316123456${i}&Body=Test" &
done
wait
```

**Results:**
- [ ] All 10 requests accepted (200 OK)
- [ ] All 10 messages processed
- [ ] All 10 responses sent
- [ ] No errors in logs
- [ ] No database connection pool exhaustion
- [ ] Average latency: ________ seconds

**Status:** PASS / FAIL
**Notes:** ____________________

---

### Test 9: Rate Limiting (60 requests in 1 second)
**Objective:** Verify rate limiting prevents abuse

**Method:**
```bash
for i in {1..60}; do
  curl -X POST "${STAGING_URL}/webhooks/twilio/whatsapp" \
    -H "X-Twilio-Signature: ${VALID_SIGNATURE}" \
    -d "MessageSid=SM_RATE_${i}&From=whatsapp:+31612345678&Body=Test" &
done
wait
```

**Expected:**
- [ ] First ~50 requests: 200 OK
- [ ] Remaining requests: 429 Too Many Requests
- [ ] Rate limit message: "Too many requests, please slow down"
- [ ] Rate limit resets after 1 minute

**Results:**
- Successful requests: ________ / 60
- Rate limited requests: ________ / 60
- Status: PASS (if ~50 succeeded, ~10 rate limited)

**Notes:** ____________________

---

### Test 10: Error Recovery & Retry Logic
**Objective:** Test retry logic for Twilio API failures

**Scenarios:**

**10a: Twilio API Temporary Failure (simulate with invalid token)**
- [ ] First attempt fails (401 Unauthorized)
- [ ] Retry after 1 second (exponential backoff)
- [ ] Second attempt fails
- [ ] Retry after 2 seconds
- [ ] Third attempt fails
- [ ] Error logged to Sentry
- [ ] User receives fallback error message

**10b: Network Timeout**
- [ ] Request times out after 10 seconds
- [ ] Retry logic activates
- [ ] Maximum 3 retry attempts
- [ ] Error logged

**Results:** ____________________
**Notes:** ____________________

---

## PHASE 7: SECURITY VALIDATION (1 HOUR)

### Test 11: Signature Verification
**Objective:** Ensure all requests are verified

**11a: Valid Signature**
- [ ] Request with valid Twilio signature accepted
- [ ] Message processed successfully

**11b: Invalid Signature**
```bash
curl -X POST "${STAGING_URL}/webhooks/twilio/whatsapp" \
  -H "X-Twilio-Signature: INVALID_SIGNATURE" \
  -d "MessageSid=SM_TEST&From=whatsapp:+31612345678&Body=Test"
```
- [ ] Request rejected: 403 Forbidden
- [ ] Error message: "Invalid signature"
- [ ] Message NOT processed
- [ ] Incident logged (potential attack)

**11c: Missing Signature**
```bash
curl -X POST "${STAGING_URL}/webhooks/twilio/whatsapp" \
  -d "MessageSid=SM_TEST&From=whatsapp:+31612345678&Body=Test"
```
- [ ] Request rejected: 403 Forbidden
- [ ] Error message: "Missing signature"
- [ ] Message NOT processed

**Results:** ____________________
**Notes:** ____________________

---

### Test 12: Injection Attack Prevention
**12a: SQL Injection Attempt**
**Message:** `'; DROP TABLE users; --`
- [ ] Message escaped properly
- [ ] No SQL execution
- [ ] Safe response generated

**12b: XSS Attempt**
**Message:** `<script>alert('XSS')</script>`
- [ ] HTML tags escaped
- [ ] Safe response generated
- [ ] No script execution

**12c: Command Injection Attempt**
**Message:** `; rm -rf /`
- [ ] Command NOT executed
- [ ] Safe response generated

**Results:** ALL PASS (no vulnerabilities)
**Notes:** ____________________

---

## PHASE 8: MONITORING & OBSERVABILITY (1.5 HOURS)

### Test 13: Logging
- [ ] Railway logs accessible: `railway logs`
- [ ] All webhook requests logged
- [ ] Twilio signature verification logged
- [ ] LangGraph processing logged
- [ ] Errors logged with stack traces
- [ ] Log format: JSON (structured logging)

**Sample log entry:**
```json
{
  "timestamp": "2025-10-25T14:30:00Z",
  "level": "INFO",
  "message": "Twilio webhook received",
  "message_sid": "SM12345",
  "from": "whatsapp:+31612345678",
  "body": "Test message",
  "signature_verified": true
}
```

- [ ] Logs searchable by MessageSid
- [ ] Logs searchable by phone number
- [ ] Logs include latency metrics

---

### Test 14: Metrics & Alerts
**Railway Metrics Dashboard:**
- [ ] CPU usage < 50% (under normal load)
- [ ] Memory usage < 80%
- [ ] Request rate visible (messages/minute)
- [ ] Error rate < 1%
- [ ] Response time (p95) < 3 seconds

**Sentry Configuration:**
- [ ] Sentry DSN configured
- [ ] Errors auto-reported to Sentry
- [ ] Twilio context included in error reports
- [ ] Error grouping working (by error type)
- [ ] Alerts configured for critical errors

**Health Check Monitoring:**
- [ ] Automated health checks every 30 seconds
- [ ] Health endpoint: `/health/detailed`
- [ ] Redis health monitored
- [ ] Supabase health monitored
- [ ] Twilio connectivity monitored

**Alert Configuration:**
- [ ] Alert: Error rate > 5% for 5 minutes
- [ ] Alert: Latency > 5 seconds for 5 minutes
- [ ] Alert: CPU > 80% for 10 minutes
- [ ] Alert: Memory > 90% for 5 minutes

**Notes:** ____________________

---

## PHASE 9: INTEGRATION VALIDATION (1 HOUR)

### Test 15: End-to-End User Journey
**Scenario:** New user inquires about a car and books an appointment

**Step 1: Initial inquiry**
**Message:** "Ik ben op zoek naar een gebruikte auto"
- [ ] Welcome response received
- [ ] Conversation state created (LangGraph)
- [ ] State saved to Redis/Supabase

**Step 2: Car specification**
**Message:** "Ik wil graag een Volkswagen Golf, niet ouder dan 2020"
- [ ] Preferences extracted: `{make: "Volkswagen", model: "Golf", year: ">= 2020"}`
- [ ] Database query executed
- [ ] Matching cars suggested

**Step 3: Price question**
**Message:** "Wat kost de Golf uit 2022?"
- [ ] Specific car identified
- [ ] Price information provided
- [ ] Additional details offered

**Step 4: Appointment request**
**Message:** "Ik wil deze auto graag komen bekijken"
- [ ] Appointment agent activated
- [ ] Available time slots retrieved
- [ ] Calendar checked (Chatwoot integration)
- [ ] Time slots suggested

**Step 5: Appointment confirmation**
**Message:** "Morgen om 14:00 graag"
- [ ] Appointment created in system
- [ ] Confirmation sent to user
- [ ] Chatwoot conversation updated
- [ ] Notification sent to sales team

**End-to-End Validation:**
- [ ] All 5 steps completed successfully
- [ ] Conversation state maintained throughout
- [ ] Context preserved between messages
- [ ] Total interaction time: ________ minutes
- [ ] User experience: Smooth / Good / Needs Improvement

**Notes:** ____________________

---

## PHASE 10: PRODUCTION READINESS (30 MINUTES)

### Code Quality
- [ ] All 51 tests passing (pytest)
- [ ] Code coverage > 80%
- [ ] No critical security vulnerabilities
- [ ] No hardcoded credentials
- [ ] Environment variables properly configured

### Performance
- [ ] Average latency < 3 seconds
- [ ] Can handle 10 concurrent messages
- [ ] Rate limiting working (50 requests/minute)
- [ ] No memory leaks (stable memory usage over time)

### Reliability
- [ ] Deduplication prevents duplicate processing
- [ ] Retry logic works (3 attempts with exponential backoff)
- [ ] Error handling graceful (no crashes)
- [ ] Health checks passing consistently

### Security
- [ ] Signature verification mandatory (no bypass)
- [ ] No injection vulnerabilities
- [ ] Rate limiting prevents abuse
- [ ] Redis TTL prevents cache bloat

### Monitoring
- [ ] All logs accessible and searchable
- [ ] Sentry error tracking configured
- [ ] Alerts configured for critical issues
- [ ] Metrics dashboard available

### Documentation
- [ ] README updated with Twilio setup
- [ ] Environment variables documented
- [ ] API endpoints documented
- [ ] Deployment process documented
- [ ] Rollback plan documented

---

## FINAL VALIDATION SCORECARD

### Deployment
- **Railway Setup:** PASS / FAIL
- **Environment Variables:** PASS / FAIL
- **Service Health:** PASS / FAIL
- **Domain Configuration:** PASS / FAIL

### Functional Testing
- **Message Reception:** PASS / FAIL
- **Intent Classification:** PASS / FAIL
- **Appointment Handling:** PASS / FAIL
- **Edge Cases:** PASS / FAIL

### Performance
- **Latency:** PASS / FAIL (< 3s)
- **Concurrent Handling:** PASS / FAIL (10+ messages)
- **Rate Limiting:** PASS / FAIL

### Security
- **Signature Verification:** PASS / FAIL
- **Injection Prevention:** PASS / FAIL

### Monitoring
- **Logging:** PASS / FAIL
- **Metrics:** PASS / FAIL
- **Alerts:** PASS / FAIL

### Integration
- **End-to-End Journey:** PASS / FAIL

---

## OVERALL STATUS

**PASS CRITERIA:** All sections PASS

- [ ] **PASSED - READY FOR PRODUCTION**
- [ ] **CONDITIONAL PASS - Minor issues to fix**
- [ ] **FAILED - Major issues to resolve**

**Issues Found:**
1. ____________________
2. ____________________
3. ____________________

**Remediation Plan:**
1. ____________________
2. ____________________
3. ____________________

---

## SIGN-OFF

**Tested By:** ____________________
**Date:** 2025-10-25
**Environment:** Railway Staging
**Version:** Twilio Integration v1.0.0
**Test Duration:** ________ hours

**Production Deployment Approved:** YES / NO
**Approved By:** ____________________
**Date:** ____________________

---

## NEXT STEPS (DAY 4)

If validation PASSED:
1. Deploy to production environment
2. Configure production Twilio webhook
3. Monitor for 24 hours
4. Gradual rollout to users

If validation FAILED:
1. Fix critical issues
2. Re-run failed tests
3. Re-validate
4. Approve for production

---

**End of Staging Validation Checklist**
