# 🏗️ WhatsApp Recruitment Platform - Custom Build Architecture

## 🎯 Business Model: Custom Builds (Not SaaS)

**Key Decision**: Building custom instances per client with 70% reusable foundation + 30% customization per client.

**Revenue Model:**
- **Upfront Build Fee**: €7,000 - €12,000 per client (one-time)
- **Monthly Maintenance**: €1,000 - €2,000 per client (recurring)
- **Total Annual Revenue per Client**: €19,000 - €36,000

**Why This Approach:**
- Better economics than €100/month SaaS (€1,200/year vs €19K-€36K/year)
- 70% foundation is identical across clients → fast customization
- 30% customization allows premium pricing
- Each client gets dedicated Supabase project + Railway deployment
- No multi-tenant complexity needed

---

## 📦 70% REUSABLE FOUNDATION

These components are identical across all client deployments:

### 1. **Core Agent System (100% Reusable)**
```
agent/
├── orchestration/
│   ├── langgraph_workflow.py       # State machine definition
│   ├── nodes/                      # Agent nodes (extract_info, qualify, notify)
│   └── checkpointing.py            # Human-in-the-loop logic
├── llm/
│   ├── claude_client.py            # Anthropic SDK wrapper
│   ├── gpt4_client.py              # OpenAI SDK wrapper (alternative)
│   └── prompts/                    # Prompt templates (industry-agnostic)
├── validation/
│   └── pydantic_models.py          # CandidateInfo, JobRequirements schemas
└── rag/
    ├── embeddings.py               # Vector generation
    └── semantic_search.py          # PGVector queries
```

### 2. **Integration Abstraction Layers (100% Reusable)**
```
integrations/
├── message_provider.py             # ABC for WhatsApp/Email/SMS
│   ├── WhatsAppProvider (360Dialog)
│   ├── EmailProvider (Resend)
│   └── SMSProvider (Twilio)
├── crm_provider.py                 # ABC for CRM systems
│   ├── SalesforceProvider
│   ├── HubSpotProvider
│   ├── PipedriveProvider
│   └── CustomCRMProvider           # Generic webhook-based
├── calendar_provider.py            # ABC for calendar systems
│   ├── CalendlyProvider
│   ├── GoogleCalendarProvider
│   └── OutlookCalendarProvider
└── ai_provider.py                  # ABC for LLM switching
    ├── AnthropicProvider (Claude)
    ├── OpenAIProvider (GPT-4)
    └── OllamaProvider (Llama 3 local)
```

### 3. **Database Layer (90% Reusable)**
- Schema definition (see `database/schema.sql`)
- Migration scripts
- Query abstraction layer
- **Customizable**: Field validation rules per industry

### 4. **API Backend (100% Reusable)**
```
api/
├── main.py                         # FastAPI application
├── routes/
│   ├── leads.py                    # POST /api/leads (form submission)
│   ├── messages.py                 # GET/POST /api/messages (chat history)
│   ├── webhooks.py                 # POST /webhook/whatsapp (360Dialog)
│   └── auth.py                     # POST /api/auth/login
├── middleware/
│   ├── auth.py                     # JWT validation
│   └── rate_limiting.py            # Per-client rate limits
└── services/
    ├── lead_service.py
    ├── message_service.py
    └── notification_service.py
```

### 5. **Dashboard Foundation (80% Reusable)**
```
dashboard/
├── pages/
│   ├── login.py                    # Authentication
│   ├── leads_list.py               # Table with filters
│   ├── lead_detail.py              # Individual lead view
│   └── live_chat.py                # WebSocket-based takeover
├── components/
│   ├── sidebar.py                  # Navigation (reusable)
│   ├── header.py                   # Top bar (reusable)
│   └── charts/                     # Analytics widgets
└── state/
    └── app_state.py                # Reflex state management
```
**Customizable**: Branding (colors, logo, company name)

### 6. **Deployment Configuration (95% Reusable)**
```
deployment/
├── Dockerfile                      # Same for all clients
├── docker-compose.yml              # Local development
├── railway.toml                    # Railway deployment config
└── nginx.conf                      # Reverse proxy config
```
**Customizable**: Environment variables (API keys, domain names)

---

## 🎨 30% CUSTOMIZABLE PER CLIENT

These components require customization for each client:

### 1. **Expert System Prompts (Industry-Specific)**
```python
# Example: Hair Salon vs Tech Company

# Hair Treats (Beauty Industry)
EXPERT_PROMPTS = {
    "technical_expert": """
    Je bent een kapper-expert met 15 jaar ervaring in de haarbranche.
    Vraag naar: knippen, kleuren, behandelingen, productkennis.
    """,
    "soft_skills_expert": """
    Je bent een klantenservice-expert. Vraag naar omgang met klanten,
    telefoonvaardigheden, kassaervaring.
    """
}

# Tech Company (Software Industry)
EXPERT_PROMPTS = {
    "technical_expert": """
    You're a senior software architect with 15 years experience.
    Ask about: programming languages, frameworks, system design, testing.
    """,
    "soft_skills_expert": """
    You're a tech team lead. Ask about collaboration, Agile experience,
    code review practices, mentoring.
    """
}
```

**Customization Effort**: 2-3 hours (writing + testing prompts)

### 2. **Qualification Criteria**
```python
# Example: Different scoring weights per industry

# Hair Treats
QUALIFICATION_WEIGHTS = {
    "technical_skills": 0.4,        # Knippen, kleuren (40%)
    "soft_skills": 0.4,             # Klantgericht (40%)
    "experience_years": 0.1,        # Ervaring (10%)
    "education": 0.1                # Diploma (10%)
}

# Tech Company
QUALIFICATION_WEIGHTS = {
    "technical_skills": 0.6,        # Programming (60%)
    "soft_skills": 0.2,             # Collaboration (20%)
    "experience_years": 0.1,        # Years (10%)
    "portfolio": 0.1                # GitHub/projects (10%)
}
```

**Customization Effort**: 1-2 hours (defining criteria + testing thresholds)

### 3. **CRM Integration Mapping**
```python
# Example: Different field mappings per CRM

# Client A: Salesforce
CRM_FIELD_MAPPING = {
    "full_name": "Contact.Name",
    "email": "Contact.Email",
    "whatsapp_number": "Contact.Phone",
    "job_title": "Contact.Title",
    "qualification_score": "Contact.Recruitment_Score__c"  # Custom field
}

# Client B: HubSpot
CRM_FIELD_MAPPING = {
    "full_name": "firstname + lastname",
    "email": "email",
    "whatsapp_number": "phone",
    "job_title": "jobtitle",
    "qualification_score": "recruitment_score"  # Custom property
}
```

**Customization Effort**: 3-4 hours (CRM setup + field mapping + testing sync)

### 4. **Form Fields Configuration**
```python
# Example: Different data collection per industry

# Hair Treats
FORM_FIELDS = [
    {"name": "full_name", "type": "text", "required": True},
    {"name": "email", "type": "email", "required": True},
    {"name": "whatsapp_number", "type": "tel", "required": True},
    {"name": "years_experience", "type": "number", "required": True},
    {"name": "specializations", "type": "multiselect", "options": ["Knippen", "Kleuren", "Extensions", "Behandelingen"]},
    {"name": "availability", "type": "select", "options": ["Fulltime", "Parttime", "Weekenden"]},
    {"name": "cv_upload", "type": "file", "required": False}
]

# Tech Company
FORM_FIELDS = [
    {"name": "full_name", "type": "text", "required": True},
    {"name": "email", "type": "email", "required": True},
    {"name": "github_url", "type": "url", "required": False},
    {"name": "linkedin_url", "type": "url", "required": True},
    {"name": "tech_stack", "type": "multiselect", "options": ["Python", "React", "Node.js", "Go", "Rust"]},
    {"name": "years_experience", "type": "number", "required": True},
    {"name": "portfolio_link", "type": "url", "required": False}
]
```

**Customization Effort**: 1-2 hours (form builder + validation)

### 5. **Branding & Styling**
```python
# system_config table entry

BRANDING_CONFIG = {
    "company_name": "Hair Treats",
    "logo_url": "https://cdn.hairtreats.nl/logo.png",
    "primary_color": "#FF6B9D",        # Pink
    "secondary_color": "#C147E9",      # Purple
    "dashboard_title": "Hair Treats Recruitment Dashboard",
    "whatsapp_greeting": "Hoi! 👋 Bedankt voor je interesse in Hair Treats."
}
```

**Customization Effort**: 30 minutes (uploading logo + color selection)

### 6. **Calendar Integration (Optional)**
```python
# Optional per client

# Client A: Uses Calendly
CALENDAR_CONFIG = {
    "provider": "calendly",
    "api_key": "...",
    "calendar_link": "https://calendly.com/hairtreats/interview",
    "default_duration": 30  # minutes
}

# Client B: No calendar (manual scheduling)
CALENDAR_CONFIG = None
```

**Customization Effort**: 2-3 hours (only if requested)

---

## 🚀 TECH STACK (Consistent Across All Clients)

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Orchestration** | LangGraph | Multi-agent state machines, human-in-the-loop, checkpointing |
| **LLM** | Claude 3.5 Sonnet / GPT-4 Turbo | High-quality Dutch support, structured output |
| **Validation** | Pydantic v2 | Type safety, runtime validation |
| **Database** | Supabase (PostgreSQL) | Auth + Database + Storage + Real-time all-in-one |
| **Vector DB** | PGVector (Supabase extension) | No additional service needed for MVP |
| **WhatsApp API** | 360Dialog | Official WhatsApp Business API (€49/month) |
| **Backend API** | FastAPI | Async, auto-docs, type hints |
| **Dashboard** | Reflex | Full-stack Python, compiles to React |
| **Auth** | Supabase Auth (JWT) | Built-in, supports SSO |
| **Deployment** | Railway | Auto-scaling, simple deploy |
| **Task Queue** | Celery + Redis | Background jobs (email, CRM sync) |
| **Email** | Resend | Developer-friendly, good deliverability |
| **Monitoring** | (Optional) Sentry | Error tracking (skip for demo) |

---

## 📊 DEPLOYMENT MODEL

Each client gets:
1. **Dedicated Supabase Project** (€25/month)
   - Isolated database
   - Separate auth users
   - Own backup schedule

2. **Dedicated Railway Deployment** (€20-50/month)
   - Auto-scaling based on load
   - Custom domain (e.g., `recruit.hairtreats.nl`)
   - Environment variables per client

3. **360Dialog WhatsApp Number** (€49/month)
   - Client's branded WhatsApp number
   - Dedicated API key

**Total Infrastructure Cost per Client**: €94-124/month
**Monthly Maintenance Fee Charged**: €1,000-€2,000/month
**Profit Margin**: €876-€1,906/month per client

---

## 🔐 SECURITY & DATA ISOLATION

**Since NOT Multi-Tenant:**
- ✅ No RLS complexity
- ✅ Physical database isolation (separate Supabase projects)
- ✅ Separate API deployments (no tenant context leakage risk)
- ✅ Separate encryption keys per client
- ✅ Separate backup schedules

**Security Measures (Same Across All Clients):**
- JWT authentication with short expiration (15 minutes)
- Refresh token rotation
- Rate limiting per IP
- CORS configuration
- SQL injection protection (parameterized queries)
- XSS protection (output sanitization)
- HTTPS-only (TLS 1.3)

---

## 📈 SCALING STRATEGY

**Per-Client Scaling:**
- Each Railway deployment auto-scales independently
- Supabase automatically handles connection pooling
- PGVector performs well up to 50K-100K vectors per client

**When to Migrate Vector DB:**
- If a single client exceeds 50K candidates → Migrate their PGVector to dedicated Qdrant instance (€20/month)

**Adding More Clients:**
- No performance impact on existing clients (isolated deployments)
- Can serve 50+ clients with this architecture
- Total infrastructure: €94-124/month × 50 clients = €4,700-€6,200/month
- Total revenue: €50,000-€100,000/month (50 clients × €1K-€2K/month)

---

## 🛠️ DEVELOPMENT WORKFLOW

**For Each New Client:**

1. **Clone Foundation Repository** (5 minutes)
   ```bash
   git clone https://github.com/yourcompany/recruitment-foundation.git client-name
   cd client-name
   ```

2. **Customize Configuration** (2-4 hours)
   - Update `config/expert_prompts.py`
   - Update `config/qualification_weights.py`
   - Update `config/form_fields.json`
   - Update `config/branding.json`
   - Set environment variables

3. **Create Supabase Project** (10 minutes)
   - Run `supabase init`
   - Run `supabase db push` (apply schema)
   - Create service account

4. **Setup 360Dialog** (15 minutes)
   - Register client's WhatsApp number
   - Get API key
   - Configure webhook URL

5. **Deploy to Railway** (15 minutes)
   ```bash
   railway init
   railway up
   ```

6. **Configure CRM Integration** (1-2 hours)
   - Test CRM API connection
   - Map fields
   - Test sync

7. **Test End-to-End** (2-3 hours)
   - Submit test form
   - Verify WhatsApp message
   - Test agent conversation
   - Verify CRM sync
   - Test dashboard login
   - Test live chat takeover

**Total Setup Time per Client**: 6-10 hours (justifies €7K-€12K upfront fee)

---

## 🔄 FUTURE SAAS MIGRATION PATH

If you decide to offer a SaaS version later for lower-budget clients:

**Changes Needed:**
1. Add `tenant_id` column to all tables
2. Implement RLS policies in Supabase
3. Add tenant context middleware
4. Implement subdomain routing (`tenant1.platform.com`)
5. Add subscription billing (Stripe)
6. Add tenant onboarding flow

**Reusability**: 80% of custom-build code can be reused for SaaS version.

---

## 📝 NEXT STEPS FOR DEMO

1. ✅ **Database Schema Created** (`database/schema.sql`)
2. **Build Core Agent System** (LangGraph + Claude SDK)
3. **Build FastAPI Backend** (leads API, webhook receiver)
4. **Build Reflex Dashboard** (login, leads list, live chat)
5. **Integrate 360Dialog** (WhatsApp provider)
6. **Test End-to-End Flow**

**Timeline for Demo**: 2-3 weeks full-time development.
