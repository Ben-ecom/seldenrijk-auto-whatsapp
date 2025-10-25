# 🔐 API KEY ROTATION GUIDE

## Overview

This guide provides step-by-step instructions for rotating all API keys and secrets in the Seldenrijk Auto WhatsApp system.

**Frequency**: Rotate keys every 90 days or immediately if compromised.

---

## 1. ANTHROPIC CLAUDE API KEY

**Current Key Location**: `.env` → `ANTHROPIC_API_KEY`

### Steps to Rotate:

1. **Generate New Key**:
   - Go to https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Copy the new key (starts with `sk-ant-api03-...`)

2. **Update Application**:
   ```bash
   # Edit .env file
   nano .env
   
   # Replace old key:
   ANTHROPIC_API_KEY=sk-ant-api03-NEW_KEY_HERE
   ```

3. **Restart Services**:
   ```bash
   cd /path/to/seldenrijk-auto-whatsapp
   docker-compose restart api celery-worker celery-beat
   ```

4. **Verify**:
   ```bash
   # Check API logs for successful requests
   docker logs seldenrijk-api --tail 50
   ```

5. **Revoke Old Key**:
   - Return to Anthropic Console
   - Delete the old key

---

## 2. SUPABASE KEYS

**Current Keys**: `.env` → `SUPABASE_URL`, `SUPABASE_KEY`

### Steps to Rotate:

1. **Generate New Key**:
   - Go to Supabase Dashboard → Settings → API
   - Click "Reset" next to `service_role` key
   - Copy new key (starts with `eyJ...`)

2. **Update Application**:
   ```bash
   nano .env
   
   # Update:
   SUPABASE_KEY=eyJNEW_SERVICE_ROLE_KEY_HERE
   ```

3. **Restart Services**:
   ```bash
   docker-compose restart api celery-worker
   ```

4. **Verify**:
   ```bash
   # Test Supabase connection
   docker-compose exec api python -c "
   from app.services.vector_store import get_vector_store
   vs = get_vector_store()
   print('✅ Supabase connected successfully')
   "
   ```

---

## 3. CHATWOOT API TOKEN

**Current Keys**: `.env` → `CHATWOOT_API_TOKEN`, `CHATWOOT_SECRET_KEY_BASE`

### Steps to Rotate:

#### 3.1 API Token

1. **Generate New Token**:
   - Go to Chatwoot → Profile Settings → Access Token
   - Click "Add Personal Access Token"
   - Copy new token

2. **Update Application**:
   ```bash
   nano .env
   
   # Update:
   CHATWOOT_API_TOKEN=NEW_TOKEN_HERE
   ```

3. **Restart Services**:
   ```bash
   docker-compose restart api celery-worker
   ```

#### 3.2 Secret Key Base

1. **Generate New Secret**:
   ```bash
   openssl rand -hex 64
   ```

2. **Update Application**:
   ```bash
   nano .env
   
   # Update:
   CHATWOOT_SECRET_KEY_BASE=NEW_SECRET_HERE
   ```

3. **Restart Services**:
   ```bash
   docker-compose restart api
   ```

4. **Verify**:
   ```bash
   # Check webhook authentication
   docker logs seldenrijk-api --tail 50 | grep "HMAC"
   ```

---

## 4. WAHA API KEY

**Current Key**: `.env` → `WAHA_API_KEY`

### Steps to Rotate:

1. **Generate New Key**:
   ```bash
   # Generate random key
   openssl rand -hex 32
   ```

2. **Update WAHA Container**:
   ```bash
   # Edit docker-compose.yml
   nano docker-compose.yml
   
   # Update WAHA service:
   environment:
     WHATSAPP_API_KEY: "new-key-here"
   ```

3. **Update Application**:
   ```bash
   nano .env
   
   # Update:
   WAHA_API_KEY=new-key-here
   ```

4. **Restart Services**:
   ```bash
   docker-compose down waha
   docker-compose up -d waha
   docker-compose restart api celery-worker
   ```

---

## 5. EMERGENCY ROTATION (Key Compromised)

If a key is compromised, **rotate immediately**:

### Quick Steps:

1. **Revoke Compromised Key** (at provider dashboard)
2. **Generate New Key**
3. **Update `.env` file**
4. **Restart services**:
   ```bash
   docker-compose restart api celery-worker celery-beat
   ```
5. **Check logs for errors**:
   ```bash
   docker logs seldenrijk-api --tail 100
   docker logs seldenrijk-celery-worker --tail 100
   ```

---

## 6. Rotation Checklist

Use this checklist for scheduled rotations:

- [ ] **Anthropic Claude API Key** (every 90 days)
- [ ] **Supabase Service Role Key** (every 90 days)
- [ ] **Chatwoot API Token** (every 90 days)
- [ ] **Chatwoot Secret Key Base** (every 180 days)
- [ ] **WAHA API Key** (every 90 days)
- [ ] **Document rotation date** in changelog
- [ ] **Verify all services are working** after rotation

---

## 7. Verification Commands

After rotating keys, verify everything works:

```bash
# 1. Test Anthropic API
docker-compose exec api python -c "
from app.agents.router_agent import RouterAgent
router = RouterAgent()
print('✅ Anthropic API working')
"

# 2. Test Supabase
docker-compose exec api python -c "
from app.services.vector_store import get_vector_store
vs = get_vector_store()
print('✅ Supabase working')
"

# 3. Test Chatwoot
docker-compose exec api python -c "
from app.integrations.chatwoot_sync import sync_conversation_to_chatwoot
print('✅ Chatwoot API working')
"

# 4. Test WAHA
curl -H "X-Api-Key: YOUR_NEW_WAHA_KEY" http://localhost:3003/api/default/auth/qr
```

---

## 8. Troubleshooting

### Services Won't Start After Rotation

```bash
# Check for syntax errors in .env
cat .env | grep "="

# Restart all services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Authentication Errors

```bash
# Verify key format (no spaces, quotes, newlines)
cat .env | grep "API_KEY"

# Test individual service
docker-compose exec api python -c "import os; print(os.getenv('ANTHROPIC_API_KEY'))"
```

---

## 9. Security Best Practices

1. **Never commit `.env` to git** (only `.env.example`)
2. **Use secure key generation**:
   ```bash
   openssl rand -hex 32  # For secrets
   openssl rand -hex 64  # For longer secrets
   ```
3. **Document rotation dates** in team calendar
4. **Test before revoking old keys** (during business hours)
5. **Keep old keys for 24 hours** before deletion (rollback window)
6. **Rotate all keys after team member departure**
7. **Monitor logs for failed auth attempts**:
   ```bash
   docker logs seldenrijk-api | grep "401\|403\|Unauthorized"
   ```

---

## 10. Rotation Schedule

| Service | Frequency | Next Rotation | Owner |
|---------|-----------|---------------|-------|
| Anthropic Claude | 90 days | [DATE] | [NAME] |
| Supabase | 90 days | [DATE] | [NAME] |
| Chatwoot API Token | 90 days | [DATE] | [NAME] |
| Chatwoot Secret Key | 180 days | [DATE] | [NAME] |
| WAHA API Key | 90 days | [DATE] | [NAME] |

---

**Last Updated**: 2025-10-19  
**Version**: 1.0  
**Contact**: [YOUR_EMAIL_HERE]
