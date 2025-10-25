# Railway Deployment - Quick Start
## WhatsApp Recruitment Platform v5.1

**5-Minute Deployment Guide**

---

## Prerequisites Checklist

- [ ] Railway account ([railway.app](https://railway.app))
- [ ] Anthropic API key
- [ ] OpenAI API key
- [ ] Supabase project (URL + service role key)
- [ ] Chatwoot instance (URL + API token)
- [ ] 360Dialog API key

---

## Deploy in 5 Steps

### 1. Create Railway Project (1 min)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
cd whatsapp-recruitment-demo
railway init
```

### 2. Add Redis (1 min)

```bash
railway add redis
```

Wait for Redis to provision (~30 seconds).

### 3. Set Environment Variables (2 min)

```bash
# Copy template
cat .railway-env.template

# Set critical variables
railway variables set ANTHROPIC_API_KEY=sk-ant-xxx
railway variables set OPENAI_API_KEY=sk-xxx
railway variables set SUPABASE_URL=https://xxx.supabase.co
railway variables set SUPABASE_KEY=eyJxxx
railway variables set CHATWOOT_BASE_URL=https://app.chatwoot.com
railway variables set CHATWOOT_API_TOKEN=xxx
railway variables set CHATWOOT_ACCOUNT_ID=123456
railway variables set DIALOG360_API_KEY=xxx

# Generate webhook secrets (IMPORTANT!)
openssl rand -hex 32  # Copy output
railway variables set CHATWOOT_WEBHOOK_SECRET=<paste-output>

openssl rand -hex 32  # Copy output
railway variables set DIALOG360_WEBHOOK_SECRET=<paste-output>

openssl rand -hex 32  # Copy output
railway variables set WHATSAPP_VERIFY_TOKEN=<paste-output>

# Optional but recommended
railway variables set SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### 4. Deploy (1 min)

```bash
railway up
```

Wait for build and deployment (~2 minutes).

### 5. Verify (30 sec)

```bash
# Get your Railway URL
railway domain

# Test health check
curl https://your-service.railway.app/health

# Check detailed status
curl https://your-service.railway.app/health/detailed | jq
```

---

## Success Indicators

Your deployment is successful if:

✅ Health endpoint returns `{"status": "healthy"}`
✅ Redis shows `"status": "healthy"`
✅ Supabase shows `"status": "healthy"`
✅ No errors in logs: `railway logs`

---

## Common Issues

### Redis Connection Failed
```bash
# Check Redis is running
railway status

# Verify REDIS_URL is injected
railway variables get REDIS_URL

# Restart if needed
railway restart
```

### Supabase Connection Failed
```bash
# Verify Supabase credentials
railway variables get SUPABASE_URL
railway variables get SUPABASE_KEY

# IMPORTANT: Use service_role key, NOT anon key!
# Get from: Supabase Dashboard → Settings → API → service_role
```

### Build Failed
```bash
# Clear cache and rebuild
railway restart --clear-cache
```

---

## Next Steps

1. **Configure Webhooks:**
   - Chatwoot: Settings → Integrations → Webhooks
   - Add: `https://your-service.railway.app/webhooks/chatwoot`

   - 360Dialog: Partner Hub → Webhooks
   - Add: `https://your-service.railway.app/webhooks/360dialog`

2. **Enable Auto-Deploy:**
   ```bash
   # Enable auto-deploy on push to main
   railway config set autoDeploy=true
   ```

3. **Monitor Logs:**
   ```bash
   railway logs --follow
   ```

4. **Set Up Domain (Optional):**
   - Railway Dashboard → Service → Settings → Domains
   - Add custom domain

---

## Environment Variables Quick Reference

**Must Set:**
```bash
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_API_TOKEN=xxx
CHATWOOT_ACCOUNT_ID=123456
DIALOG360_API_KEY=xxx
CHATWOOT_WEBHOOK_SECRET=<32-random-chars>
DIALOG360_WEBHOOK_SECRET=<32-random-chars>
WHATSAPP_VERIFY_TOKEN=<random-string>
```

**Auto-Injected by Railway:**
```bash
REDIS_URL=redis://...              # From Redis addon
RAILWAY_GIT_COMMIT_SHA=xxx         # For version tracking
RAILWAY_PUBLIC_DOMAIN=xxx.railway.app
PORT=8000
```

**Optional:**
```bash
SENTRY_DSN=https://...             # Error tracking
ENVIRONMENT=production
LOG_LEVEL=INFO
WEB_CONCURRENCY=4                  # Uvicorn workers
```

---

## Useful Commands

```bash
# View logs
railway logs
railway logs --follow

# Check status
railway status

# Restart service
railway restart

# SSH into container
railway shell

# Open Railway dashboard
railway open

# View environment variables
railway variables

# Update single variable
railway variables set KEY=value
```

---

## Health Check Endpoints

```bash
# Basic health (fast)
curl https://your-service.railway.app/health

# Detailed health (all components)
curl https://your-service.railway.app/health/detailed

# Readiness check (for Railway)
curl https://your-service.railway.app/health/readiness

# Liveness check
curl https://your-service.railway.app/health/liveness

# Railway-specific
curl https://your-service.railway.app/health/railway
```

---

## Cost

**Typical Monthly Cost:**
- Railway Starter: $5/month (512MB RAM)
- Redis addon: $5/month (256MB)
- **Total: ~$10/month**

**Upgrade for more traffic:**
- Railway Pro: $20/month (8GB RAM, autoscaling)
- Redis Pro: $10/month (512MB+)

---

## Support

**Stuck?**
1. Check logs: `railway logs`
2. Check health: `curl https://your-service.railway.app/health/detailed | jq`
3. Railway Discord: [discord.gg/railway](https://discord.gg/railway)
4. Railway Docs: [docs.railway.app](https://docs.railway.app)

**Full Documentation:** See `RAILWAY-DEPLOYMENT.md`

---

**Your service is live! 🚀**

Railway URL: `https://your-service.railway.app`
Health Check: `https://your-service.railway.app/health`
API Docs: `https://your-service.railway.app/docs` (if enabled)
