# Railway Deployment Guide
## WhatsApp Recruitment Platform v5.1

Complete guide for deploying the WhatsApp recruitment automation tool to Railway.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Environment Variables Setup](#environment-variables-setup)
5. [Railway Addons Configuration](#railway-addons-configuration)
6. [Health Checks & Monitoring](#health-checks--monitoring)
7. [Troubleshooting](#troubleshooting)
8. [CI/CD & Auto-Deployment](#cicd--auto-deployment)
9. [Scaling & Performance](#scaling--performance)
10. [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required Accounts & API Keys

1. **Railway Account** - [railway.app](https://railway.app)
2. **Anthropic API Key** - [console.anthropic.com](https://console.anthropic.com/)
3. **OpenAI API Key** - [platform.openai.com](https://platform.openai.com/)
4. **Supabase Project** - [supabase.com](https://supabase.com)
5. **Chatwoot Instance** - [chatwoot.com](https://chatwoot.com) or self-hosted
6. **360Dialog Account** - [360dialog.com](https://www.360dialog.com/)
7. **Sentry Account** (optional) - [sentry.io](https://sentry.io)

### Local Development Tools

```bash
# Install Railway CLI (optional but recommended)
npm install -g @railway/cli

# Or using Homebrew (macOS)
brew install railway

# Login to Railway
railway login
```

---

## Quick Start

### 1-Click Deploy (Fastest Method)

Click the button below to deploy automatically:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

**Then:**
1. Connect your GitHub repository
2. Add Redis addon
3. Configure environment variables (see [Environment Variables Setup](#environment-variables-setup))
4. Deploy!

---

## Step-by-Step Deployment

### Step 1: Create Railway Project

```bash
# From your project directory
railway init

# Link to existing project (if already created)
railway link
```

Or via Railway Dashboard:
1. Go to [railway.app/new](https://railway.app/new)
2. Select "Deploy from GitHub repo"
3. Connect GitHub and select your repository
4. Choose `main` branch

### Step 2: Add Redis Addon

**Via Railway CLI:**
```bash
railway add redis
```

**Via Railway Dashboard:**
1. Open your project
2. Click "New" → "Database" → "Add Redis"
3. Wait for provisioning (1-2 minutes)
4. Railway will automatically inject `REDIS_URL` environment variable

### Step 3: Configure Environment Variables

**Copy the template:**
```bash
# Copy .railway-env.template contents to Railway Dashboard
cat .railway-env.template
```

**Via Railway Dashboard:**
1. Go to your service → "Variables"
2. Click "Raw Editor"
3. Paste environment variables from `.railway-env.template`
4. Replace all placeholder values (see [Environment Variables Setup](#environment-variables-setup))

**Via Railway CLI:**
```bash
# Set individual variables
railway variables set ANTHROPIC_API_KEY=sk-ant-xxx
railway variables set OPENAI_API_KEY=sk-xxx
railway variables set SUPABASE_URL=https://xxx.supabase.co
# ... etc
```

### Step 4: Deploy

**Via Railway CLI:**
```bash
railway up
```

**Via Railway Dashboard:**
- Push to `main` branch (auto-deploys if enabled)
- Or click "Deploy" → "Redeploy"

### Step 5: Verify Deployment

```bash
# Get your Railway URL
railway domain

# Test health endpoint
curl https://your-service.railway.app/health

# Check detailed health
curl https://your-service.railway.app/health/detailed
```

---

## Environment Variables Setup

### Critical Variables (MUST SET)

```bash
# ============ AI MODELS ============
ANTHROPIC_API_KEY=sk-ant-xxx              # Get from: https://console.anthropic.com/
OPENAI_API_KEY=sk-xxx                     # Get from: https://platform.openai.com/

# ============ DATABASE ============
SUPABASE_URL=https://xxx.supabase.co      # Supabase Project Settings → API
SUPABASE_KEY=eyJxxx                       # Supabase → Project Settings → API → service_role key
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres

# ============ CHATWOOT ============
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_API_TOKEN=xxx                    # Chatwoot → Settings → Integrations → API
CHATWOOT_ACCOUNT_ID=123456                # Found in Chatwoot URL

# ============ WEBHOOK SECRETS ============
# IMPORTANT: Generate secure random strings!
# Run: openssl rand -hex 32

CHATWOOT_WEBHOOK_SECRET=<generate-32-char-random-string>
DIALOG360_WEBHOOK_SECRET=<generate-32-char-random-string>
WHATSAPP_VERIFY_TOKEN=<any-random-string>

# ============ WHATSAPP / 360DIALOG ============
DIALOG360_API_KEY=xxx                     # 360Dialog Partner Hub
```

### Generate Secure Webhook Secrets

```bash
# Generate 3 secure random strings
openssl rand -hex 32  # Use for CHATWOOT_WEBHOOK_SECRET
openssl rand -hex 32  # Use for DIALOG360_WEBHOOK_SECRET
openssl rand -hex 32  # Use for WHATSAPP_VERIFY_TOKEN
```

### Optional but Recommended

```bash
# ============ MONITORING ============
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx  # Sentry error tracking
ENVIRONMENT=production
LOG_LEVEL=INFO

# ============ PERFORMANCE ============
WEB_CONCURRENCY=4              # Number of Uvicorn workers (adjust for your plan)
DB_POOL_SIZE=20                # Database connection pool size
```

### Auto-Injected by Railway (DO NOT SET)

```bash
# These are automatically provided by Railway:
# - REDIS_URL (from Redis addon)
# - RAILWAY_ENVIRONMENT
# - RAILWAY_GIT_COMMIT_SHA
# - RAILWAY_PUBLIC_DOMAIN
# - PORT (defaults to 8000)
```

---

## Railway Addons Configuration

### Redis (Required)

**Add Redis addon:**
```bash
railway add redis
```

**Configuration:**
- Plan: Hobby ($5/month) or Pro ($10/month)
- Memory: 256MB (Hobby) or 512MB+ (Pro)
- Required for: LangGraph checkpointing, Celery task queue

**Verify Redis:**
```bash
# After deployment, check health endpoint
curl https://your-service.railway.app/health/detailed | jq '.components.redis'
```

### PostgreSQL (Optional)

If not using Supabase, add Railway PostgreSQL:

```bash
railway add postgresql
```

Railway will inject `DATABASE_URL` automatically.

---

## Health Checks & Monitoring

### Health Check Endpoints

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/health` | Basic health check (fast) | Railway, Docker, Load balancers |
| `/health/detailed` | Comprehensive status | Monitoring dashboards |
| `/health/liveness` | Process alive check | Railway container restarts |
| `/health/readiness` | Traffic routing decision | Railway load balancer |
| `/health/startup` | Initial startup check | Railway deployment |
| `/health/railway` | Railway-optimized check | Railway platform |

### Configure Railway Health Checks

Railway automatically uses `/health` endpoint from `railway.toml`:

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300

[services.main.healthcheck]
path = "/health/readiness"
port = 8000
intervalSeconds = 30
timeoutSeconds = 10
failureThreshold = 3
successThreshold = 1
```

### Test Health Checks Locally

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health (shows all components)
curl http://localhost:8000/health/detailed | jq

# Readiness check
curl http://localhost:8000/health/readiness
```

### Monitoring with Sentry

1. Create Sentry project: [sentry.io](https://sentry.io)
2. Copy DSN from Sentry project settings
3. Add to Railway variables:
   ```bash
   railway variables set SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   railway variables set GIT_COMMIT_SHA=$RAILWAY_GIT_COMMIT_SHA
   ```

### View Logs

**Via Railway Dashboard:**
1. Open your service
2. Click "Deployments" → Select deployment → "Logs"

**Via Railway CLI:**
```bash
railway logs
railway logs --follow  # Stream logs in real-time
```

**Log Filtering:**
```bash
# Filter by level
railway logs | grep ERROR
railway logs | grep WARNING

# Filter by component
railway logs | grep "LangGraph"
railway logs | grep "Redis"
```

---

## Troubleshooting

### Common Issues

#### 1. Redis Connection Failed

**Symptoms:**
```
RedisError: Error connecting to Redis
```

**Solutions:**
```bash
# Check Redis addon is provisioned
railway status

# Verify REDIS_URL is injected
railway variables get REDIS_URL

# Restart service
railway restart
```

#### 2. Supabase Connection Timeout

**Symptoms:**
```
HTTPException: 503 Service Unavailable
Readiness check failed - Supabase
```

**Solutions:**
```bash
# Check Supabase URL and key
railway variables get SUPABASE_URL
railway variables get SUPABASE_KEY

# Verify Supabase project is active
# Go to: https://app.supabase.com/

# Check Supabase service role key (not anon key)
# Supabase Dashboard → Settings → API → service_role (secret)
```

#### 3. Build Fails

**Symptoms:**
```
Error: Could not find a version that satisfies requirement...
```

**Solutions:**
```bash
# Clear build cache
railway restart --clear-cache

# Check Python version in Dockerfile.production
# Should be: FROM python:3.11-slim

# Verify requirements.txt is present
railway run cat requirements.txt
```

#### 4. High Memory Usage

**Symptoms:**
```
Container killed (OOM)
Memory percent: 95%
```

**Solutions:**
```bash
# Reduce Uvicorn workers
railway variables set WEB_CONCURRENCY=2

# Reduce database pool size
railway variables set DB_POOL_SIZE=10

# Upgrade Railway plan (more memory)
# Go to: Project Settings → Plan
```

#### 5. LangGraph Checkpointing Disabled

**Symptoms:**
```json
{
  "langgraph": {
    "status": "degraded",
    "message": "Checkpointing disabled"
  }
}
```

**Solutions:**
```bash
# Verify Redis is running
curl https://your-service.railway.app/health/detailed | jq '.components.redis'

# Check configuration
railway variables set ENABLE_CHECKPOINTING=true
railway variables set CHECKPOINT_BACKEND=redis
```

### Debug Mode

Enable debug logging temporarily:

```bash
railway variables set LOG_LEVEL=DEBUG
railway restart

# View logs
railway logs --follow

# IMPORTANT: Disable after debugging
railway variables set LOG_LEVEL=INFO
railway restart
```

### Access Railway Shell

```bash
# SSH into running container
railway shell

# Check environment
env | grep REDIS_URL
env | grep SUPABASE_URL

# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check disk space
df -h

# Check memory
free -h
```

---

## CI/CD & Auto-Deployment

### Enable Auto-Deployment

**Via Railway Dashboard:**
1. Open service → "Settings"
2. "Source" section
3. Enable "Auto Deploy: On Push"
4. Select branch: `main`

**Via `railway.toml`:**
```toml
[railway]
autoDeploy = true
branch = "main"
```

### GitHub Actions Integration

Create `.github/workflows/railway-deploy.yml`:

```yaml
name: Railway Deployment

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: |
          railway up --detach

      - name: Verify Deployment
        run: |
          sleep 30
          curl -f https://your-service.railway.app/health || exit 1
```

**Setup:**
1. Get Railway token: `railway login --browserless`
2. Add to GitHub Secrets: `Settings → Secrets → RAILWAY_TOKEN`

### Preview Environments (PR Deployments)

**Enable in `railway.toml`:**
```toml
[railway]
previewEnvironments = true
```

**How it works:**
- Each PR creates temporary deployment
- Separate environment variables
- Auto-deleted when PR closes
- Great for testing!

---

## Scaling & Performance

### Vertical Scaling (More Resources)

**Upgrade Railway Plan:**
- Hobby: $5/month (512MB RAM, 1 vCPU)
- Pro: $20/month (8GB RAM, 8 vCPU)

### Horizontal Scaling (More Replicas)

**Configure in `railway.toml`:**
```toml
[services.main.autoscaling]
enabled = true
minReplicas = 1
maxReplicas = 3
targetCPUPercent = 80
targetMemoryPercent = 80
```

**Or via Railway Dashboard:**
1. Service → "Settings" → "Scaling"
2. Enable "Autoscaling"
3. Set min/max replicas

### Performance Optimization

**Increase Workers:**
```bash
# More workers = more concurrent requests
railway variables set WEB_CONCURRENCY=8  # For Pro plan
```

**Connection Pooling:**
```bash
# Optimize database connections
railway variables set DB_POOL_SIZE=30
railway variables set DB_MAX_OVERFLOW=20
```

**Redis Memory:**
```bash
# Upgrade Redis addon to Pro for more memory
# Railway Dashboard → Redis Service → Settings → Plan
```

### Load Testing

```bash
# Install k6 (load testing tool)
brew install k6

# Create load test
cat > load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 50,        // 50 virtual users
  duration: '30s', // Run for 30 seconds
};

export default function() {
  let res = http.get('https://your-service.railway.app/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
EOF

# Run load test
k6 run load-test.js
```

---

## Cost Optimization

### Railway Pricing Overview

- **Starter Plan**: $5/month (1 service, 512MB RAM)
- **Pro Plan**: $20/month (unlimited services, 8GB RAM)
- **Pay-as-you-go**: $0.000231/GB-second

### Optimize Costs

**1. Right-Size Your Service:**
```bash
# Monitor resource usage
curl https://your-service.railway.app/health/detailed | jq '.system'

# Reduce workers if CPU < 50%
railway variables set WEB_CONCURRENCY=2
```

**2. Use Railway Redis (vs External):**
- Railway Redis: $5/month (256MB)
- External Redis (Upstash/Redis Cloud): $10+/month

**3. Enable Sleep Mode (Staging):**
```toml
[deploy]
sleepApplication = true  # Sleep after 1 hour inactivity
```

**4. Optimize Build Cache:**
```dockerfile
# Multi-stage builds reduce final image size
FROM python:3.11-slim as builder
# ... build stage ...

FROM python:3.11-slim as production
COPY --from=builder /opt/venv /opt/venv
```

**5. Monitor Costs:**
- Railway Dashboard → "Usage"
- Set up billing alerts
- Review monthly usage

---

## Production Checklist

### Before Going Live

- [ ] All environment variables configured
- [ ] Webhook secrets are 32+ random characters
- [ ] Redis addon provisioned and healthy
- [ ] Sentry configured for error tracking
- [ ] Health checks returning 200
- [ ] Logs showing no errors
- [ ] Database migrations applied (if any)
- [ ] API documentation disabled (`ENABLE_DOCS=false`)
- [ ] CORS origins restricted (not `*`)
- [ ] Rate limiting enabled
- [ ] Webhook signature validation enabled
- [ ] SSL/TLS enabled (Railway does this automatically)
- [ ] Custom domain configured (optional)
- [ ] Monitoring alerts configured
- [ ] Backup strategy in place (Supabase auto-backups)

### Post-Deployment Verification

```bash
# 1. Health checks
curl https://your-service.railway.app/health
curl https://your-service.railway.app/health/detailed
curl https://your-service.railway.app/health/readiness

# 2. Test webhook endpoint
curl -X POST https://your-service.railway.app/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -H "X-Chatwoot-Signature: test" \
  -d '{"event":"test"}'

# 3. Check logs
railway logs --follow

# 4. Monitor Sentry
# Go to: https://sentry.io/projects/your-project/

# 5. Test end-to-end flow
# Send WhatsApp message → Verify Chatwoot webhook → Check response
```

---

## Webhook Configuration

### Chatwoot Webhook Setup

1. Go to Chatwoot → Settings → Integrations → Webhooks
2. Add webhook:
   ```
   URL: https://your-service.railway.app/webhooks/chatwoot
   Events: message_created, conversation_status_changed
   ```
3. Use `CHATWOOT_WEBHOOK_SECRET` for signature validation

### 360Dialog Webhook Setup

1. Go to 360Dialog Partner Hub
2. Configure webhook URL:
   ```
   https://your-service.railway.app/webhooks/360dialog
   ```
3. Use `DIALOG360_WEBHOOK_SECRET` for signature validation
4. Set `WHATSAPP_VERIFY_TOKEN` for verification

---

## Rollback & Recovery

### Rollback to Previous Deployment

**Via Railway Dashboard:**
1. Go to "Deployments"
2. Find working deployment
3. Click "⋯" → "Redeploy"

**Via Railway CLI:**
```bash
# List deployments
railway deployments

# Rollback to specific deployment
railway redeploy <deployment-id>
```

### Database Backup & Restore

**Supabase (Automatic):**
- Daily backups (7 days retention on free tier)
- Go to: Supabase → Database → Backups

**Manual Backup:**
```bash
# Export database
railway run pg_dump $DATABASE_URL > backup.sql

# Restore database
railway run psql $DATABASE_URL < backup.sql
```

### Disaster Recovery Plan

1. **Service Down:**
   - Check Railway status page
   - View deployment logs
   - Rollback to previous deployment
   - Contact Railway support

2. **Database Corruption:**
   - Restore from Supabase backup
   - Verify data integrity
   - Test application

3. **Redis Data Loss:**
   - LangGraph will recreate checkpoints
   - Conversations may lose state
   - Users can restart conversation

---

## Support & Resources

### Railway Resources

- **Documentation**: [docs.railway.app](https://docs.railway.app)
- **Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Status Page**: [status.railway.app](https://status.railway.app)
- **GitHub**: [github.com/railwayapp](https://github.com/railwayapp)

### Project-Specific Support

- **Health Check**: `https://your-service.railway.app/health/detailed`
- **Logs**: `railway logs --follow`
- **Metrics**: `https://your-service.railway.app/metrics`

### Useful Commands

```bash
# Check status
railway status

# View environment variables
railway variables

# Open Railway dashboard
railway open

# SSH into container
railway shell

# View logs
railway logs

# Restart service
railway restart

# Delete service
railway down
```

---

## Appendix

### Complete Environment Variables Reference

See `.railway-env.template` for full list with descriptions.

### Architecture Diagram

```
┌─────────────────┐
│   WhatsApp      │
│   (360Dialog)   │
└────────┬────────┘
         │ Webhook
         ▼
┌─────────────────────────────────────────┐
│  Railway Service (FastAPI + Uvicorn)    │
│  ┌─────────────────────────────────┐   │
│  │  LangGraph Multi-Agent System    │   │
│  │  ├─ Router Agent                │   │
│  │  ├─ Extraction Agent            │   │
│  │  ├─ Conversation Agent          │   │
│  │  └─ CRM Agent                   │   │
│  └─────────────────────────────────┘   │
└────────┬──────────────┬─────────────────┘
         │              │
         ▼              ▼
┌─────────────┐  ┌──────────────┐
│   Redis     │  │   Supabase   │
│  (Railway)  │  │  (External)  │
│             │  │              │
│ - LangGraph │  │ - PostgreSQL │
│   Checkpts  │  │ - Auth       │
│ - Celery    │  │ - Storage    │
└─────────────┘  └──────────────┘
         │
         ▼
┌─────────────────┐
│    Chatwoot     │
│  (CRM/Inbox)    │
└─────────────────┘
```

### File Structure

```
whatsapp-recruitment-demo/
├── railway.toml                    # Railway deployment config
├── Dockerfile.production           # Production Docker image
├── start.sh                        # Startup script
├── .railway-env.template           # Environment variables template
├── requirements.txt                # Python dependencies
├── RAILWAY-DEPLOYMENT.md          # This file
├── app/
│   ├── main.py                    # FastAPI app
│   ├── api/
│   │   ├── health.py              # Health check endpoints
│   │   └── webhooks.py            # Webhook handlers
│   ├── agents/                    # LangGraph agents
│   ├── orchestration/             # LangGraph state machine
│   └── config/                    # Configuration
└── tests/                         # Test suite
```

---

## Version History

- **v5.1.0** (2025-01-10) - Railway deployment support added
- **v5.0.0** (2024-12-15) - LangGraph multi-agent orchestration
- **v4.0.0** (2024-11-01) - Chatwoot integration
- **v3.0.0** (2024-10-01) - WhatsApp automation

---

**Questions?** Check Railway logs or health endpoint first:
```bash
railway logs
curl https://your-service.railway.app/health/detailed | jq
```

**Need Help?** Railway Discord: [discord.gg/railway](https://discord.gg/railway)
