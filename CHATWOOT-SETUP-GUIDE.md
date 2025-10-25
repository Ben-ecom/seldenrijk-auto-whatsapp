# 🎨 Chatwoot Setup & Branding Guide

**Complete guide voor self-hosted Chatwoot configuratie en custom branding**

---

## 📋 Overzicht

Deze guide helpt je met:
- ✅ Eerste keer Chatwoot setup (admin account, API token)
- ✅ WhatsApp inbox configuratie
- ✅ Custom branding toepassen (logo, kleuren, naam)
- ✅ Email notificaties instellen
- ✅ Team members toevoegen
- ✅ Webhooks configureren

---

## 🚀 Eerste Keer Setup

### Stap 1: Start Chatwoot Container

**Via start-demo.sh (aanbevolen):**
```bash
./start-demo.sh
```

**Of handmatig:**
```bash
docker-compose -f docker-compose.full.yml up -d chatwoot-postgres chatwoot-redis chatwoot
```

**Wacht tot Chatwoot klaar is:**
```bash
# Check of Chatwoot bereikbaar is (kan 30-60 seconden duren)
curl -sf http://localhost:3001/api
```

### Stap 2: Create Admin Account

1. **Open Chatwoot:**
   ```
   http://localhost:3001
   ```

2. **Create eerste admin account:**
   - Full Name: (bijv. "Admin Recruitment")
   - Email: (bijv. "admin@recruitment.local")
   - Password: (veilig wachtwoord - opslaan in password manager!)
   - Company Name: (bijv. "WhatsApp Recruitment Platform")

3. **Complete onboarding wizard:**
   - Skip team member invites (doe je later)
   - Skip integrations (doe je later)

### Stap 3: Generate API Token

**In Chatwoot dashboard:**
1. Ga naar: **Settings** (⚙️ icon) → **Integrations** → **API**
2. Click: **Create new Access Token**
3. Name: `Recruitment Platform API`
4. Copy de gegenereerde token

**Update .env file:**
```bash
nano .env

# Add de API token:
CHATWOOT_API_TOKEN=<your-generated-token>

# Save en exit (Ctrl+X → Y → Enter)
```

### Stap 4: Restart Services

**Restart API services om nieuwe token te laden:**
```bash
docker-compose -f docker-compose.full.yml restart api celery-worker celery-beat
```

**Verify:**
```bash
# Check logs
docker-compose -f docker-compose.full.yml logs -f api | grep -i chatwoot

# Should see: "Chatwoot API token configured"
```

---

## 📬 Inbox Setup

### WhatsApp Inbox (via API channel)

**In Chatwoot dashboard:**
1. Ga naar: **Settings** → **Inboxes** → **Add Inbox**

2. **Select channel:**
   - Click "API"
   - Inbox Name: `WhatsApp Recruitment`

3. **Get webhook URL:**
   - Voor internal (Docker network): `http://api:8000/webhooks/chatwoot`
   - Voor external (via ngrok): `https://<ngrok-url>/webhooks/chatwoot`

4. **Configure features:**
   - ✅ Enable CSAT (customer satisfaction surveys)
   - ✅ Enable continuity via email
   - ✅ Allow messages after conversation resolved

5. **Assign team:**
   - Select default team (of create nieuwe team eerst)
   - Set business hours (optioneel)

---

## 🎨 Custom Branding (na setup)

### Logo & App Name

**In Chatwoot dashboard:**
1. Ga naar: **Settings** → **Account Settings**

2. **Upload logo:**
   - Click "Update logo"
   - Upload je logo (PNG/SVG, max 2MB)
   - Recommended size: 200x40px

3. **Update app name:**
   - Installation Name: `WhatsApp Recruitment Platform`
   - Domain: `recruitment.local` (voor nu, later je echte domain)

### Custom Kleuren

**Chatwoot ondersteunt custom CSS via environment variables.**

**Update docker-compose.full.yml:**
```yaml
chatwoot:
  environment:
    # Add custom branding
    - BRAND_COLOR=#FF6B6B  # Primary color (buttons, links)
    - BRAND_NAME=WhatsApp Recruitment
```

**Of via custom CSS (advanced):**

1. **Create custom CSS file:**
```bash
mkdir -p ./chatwoot-custom
nano ./chatwoot-custom/custom.css
```

2. **Add branding CSS:**
```css
/* Primary brand color */
:root {
  --color-woot: #FF6B6B;  /* Your brand color */
  --color-primary: #FF6B6B;
}

/* Custom logo size */
.app-logo {
  max-height: 40px;
}

/* Sidebar branding */
.sidebar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

3. **Mount CSS in docker-compose:**
```yaml
chatwoot:
  volumes:
    - ./chatwoot-custom/custom.css:/app/public/custom.css
```

4. **Restart Chatwoot:**
```bash
docker-compose -f docker-compose.full.yml restart chatwoot
```

### Widget Customization

**Voor de chat widget (als je die gebruikt):**

**In Chatwoot:**
1. Settings → Inboxes → Select inbox → Widget Configuration

2. **Customize widget:**
   - Widget color: (je brand color)
   - Welcome heading: "Hallo! Hoe kunnen we helpen?"
   - Welcome tagline: "We antwoorden meestal binnen een paar minuten"
   - Reply time: "typically replies in a few minutes"

3. **Pre-chat form (optioneel):**
   - Enable pre-chat form
   - Ask for: Name, Email
   - Fields: Full Name (required), Email (optional)

---

## 👥 Team Members

### Add Team Members

**In Chatwoot:**
1. Settings → Agents → Add Agent

2. **Fill in:**
   - Name: (naam team member)
   - Email: (email team member)
   - Role:
     - **Agent**: Can only view assigned conversations
     - **Administrator**: Can view all conversations + settings

3. **Send invite:**
   - Team member krijgt email met login link
   - Als je geen SMTP hebt geconfigureerd: copy invite link en stuur handmatig

### Create Teams

**Voor grotere organisaties:**
1. Settings → Teams → Create Team

2. **Configure:**
   - Team name: (bijv. "Senior Recruiters")
   - Description: (bijv. "Handles senior level positions")
   - Allow auto assignment: ✅

3. **Assign agents to team:**
   - Select agents
   - Set assignment rules

---

## 📧 Email Notifications (optioneel)

### SMTP Setup

**Voor email notificaties naar team:**

**Update .env:**
```bash
# SMTP settings
MAILER_SENDER_EMAIL=noreply@recruitment.com
SMTP_ADDRESS=smtp.gmail.com  # Of je SMTP server
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Voor Gmail:**
1. Create App Password: https://myaccount.google.com/apppasswords
2. Use app password in SMTP_PASSWORD

**Restart Chatwoot:**
```bash
docker-compose -f docker-compose.full.yml restart chatwoot
```

### Test Email

**In Chatwoot:**
1. Settings → Account Settings → Email Notifications
2. Enable notifications voor:
   - ✅ New conversation assigned
   - ✅ New message in assigned conversation
   - ✅ Conversation mention

---

## 🔧 Advanced Configuration

### Auto-Assignment Rules

**In Chatwoot:**
1. Settings → Automation → Add Automation Rule

2. **Example: Auto-assign by skill:**
   - Name: "Assign Python jobs to specialists"
   - When: Message created
   - Conditions: Message contains "Python"
   - Actions: Assign to team "Tech Recruiters"

### Canned Responses

**Snelle antwoorden voor team:**
1. Settings → Canned Responses → Add Response

2. **Example:**
   - Short Code: `welcome`
   - Content: "Bedankt voor je bericht! Een van onze recruiters neemt zo snel mogelijk contact met je op."

3. **Usage in conversation:**
   - Type `/` in message box
   - Select canned response

### Custom Attributes

**Voor extra kandidaat data:**
1. Settings → Custom Attributes → Add Attribute

2. **Example attributes:**
   - `job_preferences_titles` (List)
   - `salary_min` (Number)
   - `salary_max` (Number)
   - `years_experience` (Number)
   - `skills` (List)

---

## 🔒 Security Best Practices

### Webhook Signature Verification

**Ensure webhook security is enabled:**

**In .env:**
```bash
# Generate secure webhook secret
openssl rand -hex 32

# Add to .env
CHATWOOT_WEBHOOK_SECRET=<generated-secret>
```

**In Chatwoot webhook settings:**
- Set same secret in webhook configuration

### API Token Security

**Best practices:**
- ✅ Use dedicated API token per integration
- ✅ Revoke unused tokens
- ✅ Rotate tokens every 90 days
- ✅ Never commit tokens to git

**Revoke token:**
1. Settings → Integrations → API
2. Click delete icon next to token
3. Generate new token
4. Update .env

### Data Retention

**Configure data retention:**
1. Settings → Account Settings → Data Retention

2. **Recommended settings:**
   - Auto-resolve conversations: 7 days
   - Auto-delete resolved: 90 days
   - Audit log retention: 365 days

---

## 🐛 Troubleshooting

### Chatwoot niet bereikbaar

**Check container status:**
```bash
docker-compose -f docker-compose.full.yml ps chatwoot

# Should show: "Up" status
```

**Check logs:**
```bash
docker-compose -f docker-compose.full.yml logs -f chatwoot
```

**Common issues:**
- PostgreSQL not ready → Wait 30-60 seconds
- SECRET_KEY_BASE missing → Check .env
- Port 3000 already in use → Stop conflicting service

### API calls failing

**Verify API token:**
```bash
# Test API token
curl -X GET http://localhost:3001/api/v1/accounts/1/inboxes \
  -H "api_access_token: $CHATWOOT_API_TOKEN"

# Should return JSON with inboxes
```

**Common issues:**
- Wrong CHATWOOT_API_TOKEN → Regenerate token
- Wrong CHATWOOT_ACCOUNT_ID → Check in Chatwoot settings (usually 1)

### Email niet verzonden

**Check SMTP settings:**
```bash
docker-compose -f docker-compose.full.yml logs -f chatwoot | grep -i smtp
```

**Common issues:**
- Wrong credentials → Verify SMTP_USERNAME/PASSWORD
- Gmail blocks → Use App Password
- Port blocked → Try port 465 (SSL) instead of 587

---

## 📚 Next Steps

**Na complete setup:**
1. ✅ Test volledige WhatsApp flow
2. ✅ Train team members op Chatwoot
3. ✅ Setup automation rules
4. ✅ Configure canned responses
5. ✅ Apply custom branding
6. ✅ Test email notifications

**Voor productie:**
- Migrate naar cloud-hosted Chatwoot (optioneel)
- Setup SSL certificate voor https
- Configure backup voor Chatwoot database
- Setup monitoring (Sentry, Prometheus)

---

## 🔗 Useful Links

**Chatwoot Resources:**
- Documentation: https://www.chatwoot.com/docs
- API Reference: https://www.chatwoot.com/developers/api
- GitHub: https://github.com/chatwoot/chatwoot
- Community: https://discord.gg/chatwoot

**Your Setup:**
- Chatwoot Dashboard: http://localhost:3001
- API Base URL: http://localhost:8000
- Metrics Dashboard: http://localhost:3002

---

**Laatst Updated:** 2025-10-10
**Status:** ✅ Complete setup guide voor self-hosted Chatwoot
