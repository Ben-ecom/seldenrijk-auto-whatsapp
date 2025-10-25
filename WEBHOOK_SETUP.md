# 🔐 Webhook Signature Verification Setup Guide

## Overview

This guide covers webhook signature verification for all three webhook providers:
- **Chatwoot** - HMAC-SHA256
- **WAHA** - HMAC-SHA512 (default) or HMAC-SHA256
- **360Dialog** - HMAC-SHA256 (X-Hub-Signature-256)

## Security Benefits

Webhook signature verification protects against:
- **Malicious webhook attacks** - Reject forged webhooks from unauthorized sources
- **Man-in-the-middle attacks** - Detect tampered webhook payloads
- **Replay attacks** - Prevent reuse of captured webhook requests

## Generate Webhook Secrets

Use strong random secrets (32 bytes = 64 hex characters):

```bash
# Generate CHATWOOT webhook secret
openssl rand -hex 32

# Generate WAHA webhook secret
openssl rand -hex 32

# Generate 360DIALOG webhook secret
openssl rand -hex 32
```

Example output:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

## Configuration

### 1. Update .env File

Add the generated secrets to your `.env` file:

```bash
# Chatwoot
CHATWOOT_WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# WAHA
WAHA_WEBHOOK_SECRET=b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3

# 360Dialog
DIALOG360_WEBHOOK_SECRET=c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4

# WhatsApp token verification
WHATSAPP_VERIFY_TOKEN=your-verify-token-here
```

### 2. Configure Chatwoot

1. Go to Chatwoot Settings → Integrations → Webhooks
2. Add webhook URL: `https://your-api-domain.com/webhooks/chatwoot`
3. Add secret key: `<your-generated-secret>`
4. Enable HMAC verification
5. Select events: `message_created`

Chatwoot will send HMAC-SHA256 signature in the `X-Chatwoot-Signature` header.

### 3. Configure WAHA

WAHA supports HMAC signature verification via environment variable or API configuration.

#### Option A: Environment Variable (Global)

Add to WAHA container environment:

```bash
# docker-compose.yml
services:
  waha:
    environment:
      - WHATSAPP_HOOK_HMAC_KEY=<your-generated-secret>
```

#### Option B: Session Configuration (Per Session)

Configure HMAC when starting a session:

```bash
curl -X POST http://waha:3000/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "name": "default",
    "config": {
      "webhooks": [
        {
          "url": "https://your-api-domain.com/webhooks/waha",
          "events": ["message"],
          "hmac": {
            "key": "<your-generated-secret>",
            "algorithm": "sha512"
          }
        }
      ]
    }
  }'
```

WAHA will send:
- `X-Webhook-Hmac` - HMAC signature (hex format)
- `X-Webhook-Hmac-Algorithm` - Algorithm used (sha512 or sha256)

### 4. Configure 360Dialog

1. Go to 360Dialog Dashboard → Webhooks
2. Add webhook URL: `https://your-api-domain.com/webhooks/360dialog`
3. Add app secret: `<your-generated-secret>`
4. Enable signature verification

360Dialog will send HMAC-SHA256 signature in the `X-Hub-Signature-256` header (format: `sha256=<hex>`).

## Testing

### Test Chatwoot Webhook

Test with valid signature:

```bash
# Calculate signature
PAYLOAD='{"test": "data"}'
SECRET="your-chatwoot-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Send webhook with signature
curl -X POST https://your-api-domain.com/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -H "X-Chatwoot-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response: `{"status": "ignored", "event": null}` (200 OK)

Test with invalid signature (should return 403):

```bash
curl -X POST https://your-api-domain.com/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -H "X-Chatwoot-Signature: invalid-signature" \
  -d '{"test": "data"}'
```

Expected response: `{"detail": "Invalid webhook signature"}` (403 Forbidden)

### Test WAHA Webhook

Test with valid signature (SHA512):

```bash
# Calculate signature
PAYLOAD='{"test": "data"}'
SECRET="your-waha-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha512 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Send webhook with signature
curl -X POST https://your-api-domain.com/webhooks/waha \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Hmac: $SIGNATURE" \
  -H "X-Webhook-Hmac-Algorithm: sha512" \
  -d "$PAYLOAD"
```

Expected response: `{"status": "ignored", "event": null}` (200 OK)

Test with invalid signature (should return 403):

```bash
curl -X POST https://your-api-domain.com/webhooks/waha \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Hmac: invalid-signature" \
  -H "X-Webhook-Hmac-Algorithm: sha512" \
  -d '{"test": "data"}'
```

Expected response: `{"detail": "Invalid webhook signature"}` (403 Forbidden)

### Test 360Dialog Webhook

Test with valid signature:

```bash
# Calculate signature
PAYLOAD='{"test": "data"}'
SECRET="your-360dialog-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Send webhook with signature
curl -X POST https://your-api-domain.com/webhooks/360dialog \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response: `{"status": "ignored", "reason": "no_messages"}` (200 OK)

Test with invalid signature (should return 403):

```bash
curl -X POST https://your-api-domain.com/webhooks/360dialog \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=invalid-signature" \
  -d '{"test": "data"}'
```

Expected response: `{"detail": "Invalid webhook signature"}` (403 Forbidden)

## Development Mode

For local development, signature verification has development bypasses:

### Chatwoot
- If `ENVIRONMENT=development` and no signature header provided → bypass enabled
- Logs warning: `⚠️ CHATWOOT_WEBHOOK_SECRET bypass (development mode)`

### WAHA
- If `ENVIRONMENT=development` and `WAHA_WEBHOOK_SECRET` not configured → bypass enabled
- Logs warning: `⚠️ WAHA_WEBHOOK_SECRET not set - skipping verification (development mode)`

### 360Dialog
- No development bypass - signature always required

**WARNING:** Never use `ENVIRONMENT=development` in production!

## Monitoring

All signature verification failures are logged and tracked:

```python
# Logs
logger.error("❌ Invalid WAHA webhook signature (algorithm: sha512)")
logger.error("❌ Missing X-Chatwoot-Signature header")

# Metrics (Prometheus)
webhook_signature_errors_total{source="waha"} 5
webhook_signature_errors_total{source="chatwoot"} 2
```

Monitor these metrics in Grafana to detect potential attacks.

## Security Best Practices

### Secret Management
- ✅ Use strong random secrets (32+ bytes)
- ✅ Store secrets in environment variables (never in code)
- ✅ Use different secrets for each webhook provider
- ✅ Rotate secrets quarterly or after security incident
- ❌ Never commit secrets to Git
- ❌ Never share secrets in plain text (email, Slack, etc.)

### Signature Verification
- ✅ Always use constant-time comparison (`hmac.compare_digest`)
- ✅ Verify signature before processing webhook payload
- ✅ Log all signature verification failures
- ✅ Monitor for repeated failures (potential attack)
- ✅ Use HTTPS for webhook endpoints (prevent eavesdropping)

### Secret Rotation

To rotate webhook secrets:

1. Generate new secret: `openssl rand -hex 32`
2. Update provider configuration (Chatwoot/WAHA/360Dialog) with new secret
3. Update `.env` file with new secret
4. Restart API service: `docker-compose restart api`
5. Verify webhooks work with new secret
6. Revoke old secret from provider

**Zero-downtime rotation** (if supported):
- Configure provider with multiple secrets
- Add new secret to API
- Remove old secret after transition period

## Troubleshooting

### 403 Forbidden - Invalid webhook signature

**Possible causes:**
1. Secret mismatch between provider and API
2. Incorrect algorithm (SHA256 vs SHA512)
3. Signature header name mismatch
4. Request body modified in transit

**Solution:**
1. Verify secret in `.env` matches provider configuration
2. Check algorithm (WAHA: SHA512 default, others: SHA256)
3. Verify header name matches API implementation
4. Enable DEBUG logging to see actual vs expected signature
5. Test with curl to eliminate provider issues

### Missing signature header

**Possible causes:**
1. Provider not configured to send signature
2. Reverse proxy stripping headers
3. Development bypass not working

**Solution:**
1. Verify provider webhook configuration includes HMAC
2. Check reverse proxy/load balancer preserves headers
3. For development: set `ENVIRONMENT=development` and omit secret

### Signature works in curl but not from provider

**Possible causes:**
1. Request body formatting differs
2. Character encoding issues (UTF-8)
3. Trailing newlines in payload

**Solution:**
1. Enable DEBUG logging to see raw body bytes
2. Verify provider sends `Content-Type: application/json`
3. Check for byte-order-marks (BOM) in payload
4. Compare curl payload with actual webhook payload

## Support

For issues or questions:
1. Check logs: `docker-compose logs api | grep webhook`
2. Enable DEBUG logging: `LOG_LEVEL=DEBUG`
3. Verify secrets match between provider and API
4. Test with curl to isolate provider issues
5. Check Prometheus metrics for signature error patterns

## References

- [WAHA Security Documentation](https://waha.devlike.pro/docs/how-to/security/)
- [Chatwoot Webhooks](https://www.chatwoot.com/docs/product/features/webhooks)
- [360Dialog Webhooks](https://docs.360dialog.com/whatsapp-api/whatsapp-api/webhooks)
- [HMAC Authentication Best Practices](https://hookdeck.com/webhooks/guides/how-to-implement-sha256-webhook-signature-verification)
