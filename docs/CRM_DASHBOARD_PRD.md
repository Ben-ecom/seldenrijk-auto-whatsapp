# 🚀 CHATWOOT CRM DASHBOARD + AG-UI - PRODUCT REQUIREMENTS DOCUMENT

**Project:** Seldenrijk Auto - WhatsApp AI CRM Dashboard
**Version:** 1.0
**Date:** 16 Oktober 2025
**Status:** 🔨 PLANNING PHASE - Awaiting Approval

---

## 📋 EXECUTIVE SUMMARY

### Vision
Een premium CRM dashboard geïntegreerd in Chatwoot sidebar met een AI-powered conversational interface (AG-UI) die verkopers in realtime helpt met lead management, voorraad checks, en chat history analyse.

### Business Problem
- **87% van WhatsApp leads komt buiten kantooruren** (na 17:00)
- **€47.000/jaar gemiddeld verlies** door gemiste leads
- Verkopers hebben **geen overzicht** van hot leads, segmentatie, en voorraad
- **Geen AI-assistentie** voor snelle data opzoeking tijdens gesprekken

### Solution
Een **Chatwoot Sidebar Dashboard App** met:
1. ✅ **CRM Dashboard** - Real-time lead scores, segmentatie, analytics
2. 🤖 **AG-UI (AI Agent Interface)** - Conversational AI voor data queries
3. 🎨 **Premium Cyber Blue Design** - Modern, professional, high-end UX
4. 🔐 **Update-Proof Architecture** - Geen Chatwoot code wijzigingen
5. 📊 **Multi-Tenant Ready** - Schaalbaar voor meerdere klanten

---

## 🎯 PROJECT GOALS

### Primary Goals
1. **Lead Conversion +40%** - Snellere response op hot leads
2. **Time Savings 60%** - AG-UI automatiseert data lookups
3. **Zero Missed Leads** - Real-time notificaties voor hot leads
4. **Premium User Experience** - Modern, fast, intuitive interface

### Success Metrics
- Hot lead response time: **< 5 minuten** (was: 2+ uur)
- Average query time AG-UI: **< 3 seconden**
- User satisfaction: **> 4.5/5**
- System uptime: **99.9%**

---

## 👥 USER PERSONAS

### 1. Verkoper (Primary User)
**Naam:** Mark, 32 jaar
**Rol:** Sales Agent bij Seldenrijk Auto
**Needs:**
- Snel overzicht hot leads tijdens gesprek
- Check voorraad zonder systemen te switchen
- Zie chat history met klant
- Notificaties voor urgente leads

**Pain Points:**
- Moet tussen 5+ systemen switchen
- Mist leads buiten kantooruren
- Geen overzicht van lead prioriteit

### 2. Sales Manager (Secondary User)
**Naam:** Linda, 38 jaar
**Rol:** Team Lead Sales
**Needs:**
- Overzicht team performance
- Lead conversion funnel analytics
- Forecasting hot leads pipeline

---

## 🏗️ SYSTEM ARCHITECTURE

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│           CHATWOOT (Self-Hosted Docker)                 │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  SIDEBAR: CRM Dashboard App (Iframe)              │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │  🎨 DASHBOARD VIEW                           │ │ │
│  │  │  ├─ Lead Score Cards (Hot/Warm/Cold)        │ │ │
│  │  │  ├─ Segmentation Overview                   │ │ │
│  │  │  ├─ Active Conversations Timeline           │ │ │
│  │  │  └─ Quick Stats (Today's Performance)       │ │ │
│  │  ├──────────────────────────────────────────────┤ │ │
│  │  │  🤖 AG-UI CHAT INTERFACE                     │ │ │
│  │  │  ┌────────────────────────────────────────┐ │ │ │
│  │  │  │ 👤: "Show hot leads today"             │ │ │ │
│  │  │  │ 🤖: [Displays 5 hot leads + details]   │ │ │ │
│  │  │  │ 👤: "Audi A6 inventory?"                │ │ │ │
│  │  │  │ 🤖: "2 available: [specs + prices]"     │ │ │ │
│  │  │  └────────────────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  postMessage API ↕ Data Exchange                        │
└─────────────────────────────────────────────────────────┘
                         ↓
          ┌──────────────────────────────────┐
          │  CRM DASHBOARD APP (Next.js)     │
          │  Deployed on Railway             │
          │                                  │
          │  ├─ React UI Components          │
          │  ├─ AG-UI Logic (OpenAI)         │
          │  ├─ State Management (Zustand)   │
          │  └─ API Layer                    │
          └──────────────────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │  BACKEND APIs                      │
        │  ├─ Chatwoot REST API              │
        │  ├─ Inventory Database (Postgres)  │
        │  ├─ CRM Database (Lead Scores)     │
        │  └─ Analytics Engine               │
        └────────────────────────────────────┘
```

---

## 🎨 DESIGN SYSTEM - CYBER BLUE PREMIUM

### Color Palette
```css
/* Primary Colors */
--primary-navy: #001F3F;      /* Deep navy blue background */
--primary-cyan: #00D9FF;       /* Bright cyan accents */
--secondary-blue: #0066CC;     /* Medium blue */

/* Gradients */
--gradient-primary: linear-gradient(135deg, #001F3F 0%, #0066CC 100%);
--gradient-accent: linear-gradient(90deg, #00D9FF 0%, #0099FF 100%);
--gradient-card: linear-gradient(145deg, rgba(0,31,63,0.8) 0%, rgba(0,102,204,0.6) 100%);

/* Semantic Colors */
--success: #00FF88;            /* Green for hot leads */
--warning: #FFB800;            /* Orange for warm leads */
--info: #00D9FF;               /* Cyan for information */
--danger: #FF3366;             /* Red for alerts */

/* Neutrals */
--bg-dark: #000814;            /* Very dark background */
--bg-card: rgba(0,31,63,0.4);  /* Semi-transparent cards */
--text-primary: #FFFFFF;       /* White text */
--text-secondary: #A0AEC0;     /* Gray text */
--border: rgba(0,217,255,0.2); /* Cyan border with opacity */
```

### Typography
```css
/* Font Family */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'Fira Code', 'Courier New', monospace;

/* Font Sizes */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */
--text-4xl: 2.25rem;   /* 36px */
```

### Animations & Effects
```css
/* Smooth Transitions */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Glow Effects */
box-shadow:
  0 0 20px rgba(0, 217, 255, 0.3),
  0 0 40px rgba(0, 217, 255, 0.1);

/* Hover States */
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 217, 255, 0.4);
}

/* Loading Skeleton */
@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}
```

---

## 📊 FEATURE SPECIFICATIONS

### 1. CRM Dashboard View

#### 1.1 Lead Score Cards
**Visual:** 3 large cards (Hot/Warm/Cold) met gradients

**Data Display:**
```
┌─────────────────────────────────────┐
│  🔥 HOT LEADS             [15]      │
│  ═══════════════════════════════    │
│  Score: 80+                         │
│  Avg Response: 12 min               │
│  Conversion: 68%                    │
│  [View All →]                       │
└─────────────────────────────────────┘
```

**Interactions:**
- Click card → Filter conversations by segment
- Hover → Show trend graph (last 7 days)
- Badge → Real-time count updates

#### 1.2 Active Conversations Timeline
**Visual:** Scrollable list met conversation cards

**Card Contents:**
- Customer name + avatar
- Lead score badge (color-coded)
- Last message preview (50 chars)
- Time since last message
- Assigned tags (max 3 visible)
- Quick actions: Reply, Assign, Close

**Sorting Options:**
- By lead score (highest first)
- By recency (most recent)
- By response time (longest waiting)

#### 1.3 Segmentation Filters
**Filter Bar:**
```
[All Leads ▼] [Hot] [Warm] [Cold]
[Today ▼] [This Week] [This Month]
[Tags: ▼] [Audi] [BMW] [Mercedes] [+]
```

**Filter Combinations:**
- Lead quality + Time range + Car interest
- Saved filters: "My Hot Leads", "Urgent Follow-ups"

#### 1.4 Quick Stats Dashboard
**Metrics Display:**
```
┌────────────────────────────────────────────┐
│  📊 TODAY'S PERFORMANCE                    │
│  ────────────────────────────────────────  │
│  New Leads: 23        Conversions: 8       │
│  Avg Response: 8min   Hot Leads: 15        │
│  ───────────────────────────────────────── │
│  [↗ 12% vs yesterday]                      │
└────────────────────────────────────────────┘
```

---

### 2. AG-UI (AI Agent Interface)

#### 2.1 Chat Interface Design
**Visual Layout:**
```
┌──────────────────────────────────────────┐
│  🤖 Vraag me iets over je leads...       │
├──────────────────────────────────────────┤
│                                          │
│  👤: Show hot leads from today           │
│                                          │
│  🤖: Ik vond 5 hot leads:                │
│      ┌────────────────────────────┐      │
│      │ Jan de Vries - 95 pts      │      │
│      │ Audi A6 interesse          │      │
│      │ Budget: €30k               │      │
│      │ [Open Chat →]              │      │
│      └────────────────────────────┘      │
│      [Show 4 more...]                    │
│                                          │
│  [Type your question...]          [Send] │
└──────────────────────────────────────────┘
```

#### 2.2 AG-UI Capabilities

**Category 1: Lead Management**
- "Show hot leads"
- "Who needs follow-up?"
- "Leads with budget > €25k"
- "Customers waiting longest"

**Category 2: Inventory Queries**
- "Audi A6 inventory?"
- "Cars under €20k"
- "Diesel cars with <50k km"
- "Show BMW 3 series"

**Category 3: Chat History**
- "What did Jan say about budget?"
- "Show conversation with customer X"
- "Find mentions of 'proefrit'"
- "Last 5 conversations about Audi"

**Category 4: Analytics & Reports**
- "Today's conversion rate?"
- "Hot leads trend this week"
- "Most popular car brand"
- "Generate sales report"

**Category 5: Actions**
- "Assign hot lead to Mark"
- "Schedule follow-up for tomorrow"
- "Add note to conversation"
- "Send template message"

#### 2.3 Function Calling Architecture

**Available Functions:**
```javascript
const AG_UI_FUNCTIONS = [
  // Lead Management
  {
    name: "get_hot_leads",
    description: "Fetch conversations with lead score >= 80",
    parameters: {
      time_range: "today|week|month",
      limit: "number"
    }
  },

  // Inventory
  {
    name: "search_inventory",
    description: "Search car inventory by filters",
    parameters: {
      brand: "string",
      model: "string",
      fuel_type: "diesel|benzine|elektrisch|hybride",
      max_price: "number",
      max_km: "number"
    }
  },

  // Chat History
  {
    name: "search_conversations",
    description: "Search through conversation messages",
    parameters: {
      query: "string",
      contact_id: "number (optional)",
      date_range: "string"
    }
  },

  // Analytics
  {
    name: "get_analytics",
    description: "Get analytics data",
    parameters: {
      metric: "conversions|lead_scores|response_time",
      time_range: "today|week|month"
    }
  },

  // Actions
  {
    name: "assign_conversation",
    description: "Assign conversation to agent",
    parameters: {
      conversation_id: "number",
      agent_id: "number"
    }
  }
];
```

#### 2.4 Response Formatting

**Structured Responses:**
```typescript
interface AG_UI_Response {
  type: 'data' | 'chart' | 'action_result' | 'error';
  content: {
    text: string;           // Natural language response
    data?: any[];           // Structured data (for tables)
    chart?: ChartConfig;    // Chart configuration
    actions?: Action[];     // Suggested follow-up actions
  };
  metadata: {
    query_time: number;     // Response time in ms
    data_source: string;    // Which API was called
    confidence: number;     // AI confidence (0-1)
  };
}
```

**Example Response:**
```json
{
  "type": "data",
  "content": {
    "text": "Ik vond 5 hot leads van vandaag:",
    "data": [
      {
        "name": "Jan de Vries",
        "score": 95,
        "interest": "Audi A6",
        "budget": 30000,
        "conversation_id": 12345
      }
    ],
    "actions": [
      {
        "label": "Open Chat",
        "type": "navigate",
        "target": "/conversations/12345"
      }
    ]
  },
  "metadata": {
    "query_time": 234,
    "data_source": "chatwoot_api",
    "confidence": 0.95
  }
}
```

---

## 🔧 TECHNICAL STACK

### Frontend (CRM Dashboard App)
```json
{
  "framework": "Next.js 14 (App Router)",
  "ui_library": "React 18",
  "styling": "Tailwind CSS + Framer Motion",
  "state": "Zustand (lightweight, fast)",
  "charts": "Recharts (customizable, responsive)",
  "forms": "React Hook Form + Zod",
  "http": "Axios (with interceptors)",
  "realtime": "Socket.io-client (optional)",
  "testing": "Vitest + React Testing Library"
}
```

### AI Layer (AG-UI)
```json
{
  "model": "OpenAI GPT-4-Turbo (function calling)",
  "sdk": "openai ^4.0",
  "fallback": "Anthropic Claude 3 Sonnet",
  "streaming": "Server-Sent Events (SSE)",
  "context_window": "128k tokens",
  "temperature": 0.3,
  "max_tokens": 2000
}
```

**Why OpenAI GPT-4-Turbo?**
- ✅ Best function calling accuracy (95%+)
- ✅ Fast response time (<2s average)
- ✅ Large context window (hele chat history)
- ✅ Reliable structured outputs
- ✅ Good Dutch language support

**Fallback Strategy:**
```
GPT-4-Turbo (primary)
    ↓ (if fails)
Claude 3 Sonnet (fallback)
    ↓ (if fails)
Static response (error message)
```

### Backend APIs
```json
{
  "chatwoot_api": {
    "base_url": "http://chatwoot:3000/api/v1",
    "auth": "api_access_token header",
    "rate_limit": "60 req/min"
  },
  "inventory_db": {
    "type": "PostgreSQL",
    "orm": "Prisma",
    "connection": "pooled"
  },
  "crm_db": {
    "type": "PostgreSQL (same as inventory)",
    "tables": ["lead_scores", "notes", "analytics"]
  }
}
```

### Deployment
```json
{
  "crm_app": {
    "platform": "Railway",
    "domain": "crm-dashboard.yourdomain.com",
    "ssl": "automatic (Railway)",
    "env": "production"
  },
  "chatwoot": {
    "platform": "Docker (self-hosted)",
    "version": "latest (locked)",
    "compose": "docker-compose.yml"
  }
}
```

---

## 🔐 SECURITY MODEL

### Authentication Flow
```
1. User logs in to Chatwoot (native auth)
   ↓
2. Chatwoot loads sidebar iframe (CRM app)
   ↓
3. CRM app receives Chatwoot API token via postMessage
   ↓
4. CRM app validates token with Chatwoot API
   ↓
5. Store token in sessionStorage (iframe-scoped)
   ↓
6. All API calls use validated token
```

### API Security
```javascript
// Token validation middleware
async function validateChatwootToken(token) {
  try {
    const response = await axios.get(
      `${CHATWOOT_BASE_URL}/api/v1/profile`,
      { headers: { 'api_access_token': token } }
    );
    return response.status === 200;
  } catch {
    return false;
  }
}

// Rate limiting (per user)
const rateLimiter = rateLimit({
  windowMs: 60 * 1000,  // 1 minute
  max: 60,               // 60 requests per minute
  keyGenerator: (req) => req.user.id
});
```

### Data Privacy
- ❌ **No data storage** in CRM app (stateless)
- ✅ **All data fetched on-demand** from Chatwoot API
- ✅ **No logs** of customer conversations
- ✅ **AG-UI context** cleared after each query
- ✅ **GDPR compliant** (data resides in Chatwoot)

### Iframe Security
```javascript
// Secure postMessage handling
window.addEventListener('message', (event) => {
  // Validate origin
  if (event.origin !== CHATWOOT_ORIGIN) {
    console.error('Invalid origin:', event.origin);
    return;
  }

  // Validate message structure
  if (!isValidChatwootMessage(event.data)) {
    console.error('Invalid message format');
    return;
  }

  // Process message
  handleChatwootMessage(event.data);
});
```

---

## 📈 DATA FLOW DIAGRAMS

### Flow 1: Dashboard Load
```
User opens conversation in Chatwoot
  ↓
Chatwoot loads CRM sidebar iframe
  ↓
CRM app sends postMessage: 'fetch-info'
  ↓
Chatwoot responds with conversation data
  ↓
CRM app extracts:
  - conversation_id
  - contact_id
  - labels (tags)
  - messages
  ↓
Fetch additional data from Chatwoot API:
  - All conversations by label (hot-lead, warm-lead)
  - Conversation counts
  - Agent assignments
  ↓
Render dashboard with data
```

### Flow 2: AG-UI Query
```
User types: "Show hot leads today"
  ↓
Send to OpenAI GPT-4-Turbo:
  - User message
  - Available functions
  - Conversation context
  ↓
GPT-4 decides to call: get_hot_leads({time_range: "today"})
  ↓
Execute function:
  - Fetch conversations from Chatwoot API
  - Filter: labels=["hot-lead"], created_at >= today
  - Sort by lead_score DESC
  ↓
Return structured data to GPT-4
  ↓
GPT-4 generates natural language response
  ↓
Stream response to UI (character by character)
  ↓
Display response with interactive cards
```

### Flow 3: Inventory Query
```
User: "Audi A6 voorraad?"
  ↓
AG-UI calls: search_inventory({brand: "Audi", model: "A6"})
  ↓
Query Postgres inventory database
  ↓
Return: [2 cars with details]
  ↓
AG-UI formats response:
  "2 Audi A6 beschikbaar:
   1. 2020, Diesel, 45k km, €28.500
   2. 2021, Benzine, 30k km, €32.000"
  ↓
Display with [View Details] buttons
```

---

## 🎯 IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1 - 8 hours)
**Tasks:**
- ✅ Setup Next.js project structure
- ✅ Configure Tailwind with Cyber Blue theme
- ✅ Create base layout components
- ✅ Setup Chatwoot postMessage integration
- ✅ Implement authentication flow
- ✅ Deploy to Railway (dev environment)

**Deliverables:**
- Working iframe that loads in Chatwoot sidebar
- Authentication with Chatwoot API tokens
- Basic layout with navigation

### Phase 2: Dashboard UI (Week 1-2 - 12 hours)
**Tasks:**
- ✅ Build Lead Score Cards component
- ✅ Implement Conversations Timeline
- ✅ Create Filter Bar with state management
- ✅ Add Quick Stats dashboard
- ✅ Implement real-time data fetching
- ✅ Add loading states & error handling

**Deliverables:**
- Fully functional CRM dashboard
- All filters working
- Real-time updates from Chatwoot

### Phase 3: AG-UI Core (Week 2 - 10 hours)
**Tasks:**
- ✅ Setup OpenAI GPT-4-Turbo integration
- ✅ Implement function calling architecture
- ✅ Create chat interface UI
- ✅ Build streaming response handler
- ✅ Add context management
- ✅ Implement error handling & fallbacks

**Deliverables:**
- Working AI chat interface
- Basic queries functional (hot leads, inventory)
- Streaming responses

### Phase 4: AG-UI Functions (Week 2-3 - 12 hours)
**Tasks:**
- ✅ Implement all 15+ AG-UI functions
- ✅ Connect to Chatwoot API (conversations, labels)
- ✅ Connect to Inventory Database
- ✅ Build analytics aggregation functions
- ✅ Add action execution (assign, note, schedule)
- ✅ Test all query patterns

**Deliverables:**
- All AG-UI capabilities working
- Inventory queries functional
- Analytics queries working

### Phase 5: Polish & Optimization (Week 3 - 8 hours)
**Tasks:**
- ✅ Add animations (Framer Motion)
- ✅ Implement loading skeletons
- ✅ Optimize API calls (caching, debouncing)
- ✅ Add keyboard shortcuts
- ✅ Mobile responsive (if needed)
- ✅ Performance testing

**Deliverables:**
- Smooth animations
- Fast load times (<2s)
- Polished user experience

### Phase 6: Testing & Deployment (Week 4 - 6 hours)
**Tasks:**
- ✅ Write unit tests (critical paths)
- ✅ Manual testing (all features)
- ✅ Load testing (100+ conversations)
- ✅ Security audit
- ✅ Production deployment
- ✅ Documentation

**Deliverables:**
- Production-ready application
- User documentation
- Deployment guide

---

## ⏱️ TIMELINE & EFFORT ESTIMATE

### Total Effort: 56 hours (~7 working days)

**Breakdown:**
- Phase 1 (Foundation): 8 hours
- Phase 2 (Dashboard UI): 12 hours
- Phase 3 (AG-UI Core): 10 hours
- Phase 4 (AG-UI Functions): 12 hours
- Phase 5 (Polish): 8 hours
- Phase 6 (Testing & Deploy): 6 hours

**Working Schedule:**
- Days 1-2: Phase 1 + start Phase 2
- Days 3-4: Complete Phase 2 + Phase 3
- Days 5-6: Phase 4 + Phase 5
- Day 7: Phase 6 (testing & deployment)

---

## 🧪 TESTING STRATEGY

### Unit Tests (Vitest)
```javascript
// Example: Test AG-UI function calling
describe('AG-UI Functions', () => {
  it('should call get_hot_leads with correct parameters', async () => {
    const result = await agui.query("Show hot leads today");
    expect(result.function_call).toBe('get_hot_leads');
    expect(result.parameters.time_range).toBe('today');
  });

  it('should handle inventory search', async () => {
    const result = await agui.query("Audi A6 voorraad?");
    expect(result.function_call).toBe('search_inventory');
    expect(result.parameters.brand).toBe('Audi');
  });
});
```

### Integration Tests
- ✅ Chatwoot API integration
- ✅ PostgreSQL database queries
- ✅ OpenAI function calling
- ✅ postMessage communication

### Manual Testing Checklist
- [ ] Load dashboard in Chatwoot sidebar
- [ ] All filters work correctly
- [ ] Lead score cards display accurate data
- [ ] AG-UI responds to queries
- [ ] Inventory searches return correct results
- [ ] Chat history searches work
- [ ] Analytics queries accurate
- [ ] Actions execute successfully
- [ ] Error states display properly
- [ ] Loading states smooth

### Performance Testing
- [ ] Dashboard loads in < 2s
- [ ] AG-UI response time < 3s
- [ ] Handles 100+ conversations
- [ ] No memory leaks after 1 hour usage
- [ ] Smooth animations 60fps

---

## 🚀 DEPLOYMENT STRATEGY

### Railway Deployment
```yaml
# railway.json
{
  "build": {
    "builder": "nixpacks",
    "buildCommand": "npm run build"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/api/health",
    "restartPolicyType": "on_failure"
  },
  "env": {
    "NODE_ENV": "production",
    "CHATWOOT_BASE_URL": "${{CHATWOOT_BASE_URL}}",
    "OPENAI_API_KEY": "${{OPENAI_API_KEY}}",
    "DATABASE_URL": "${{DATABASE_URL}}"
  }
}
```

### Chatwoot Dashboard App Configuration
```javascript
// In Chatwoot UI: Settings → Integrations → Dashboard Apps
{
  "name": "Seldenrijk CRM Dashboard",
  "content": [
    {
      "url": "https://crm-dashboard.yourdomain.com",
      "type": "frame"
    }
  ]
}
```

### Environment Variables
```bash
# Required
CHATWOOT_BASE_URL=http://chatwoot:3000
CHATWOOT_API_TOKEN=your_api_token
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...

# Optional
ANTHROPIC_API_KEY=sk-ant-...  # Fallback
SENTRY_DSN=https://...         # Error tracking
LOG_LEVEL=info
```

---

## 📚 DOCUMENTATION DELIVERABLES

### User Documentation
1. **User Guide** (PDF/Markdown)
   - How to use CRM dashboard
   - AG-UI query examples
   - Best practices

2. **AG-UI Cheat Sheet**
   - Common queries
   - Advanced filters
   - Pro tips

### Developer Documentation
1. **Setup Guide** (README.md)
   - Installation steps
   - Environment configuration
   - Deployment instructions

2. **API Reference**
   - AG-UI functions
   - Data structures
   - Error codes

3. **Architecture Document**
   - System design
   - Data flows
   - Security model

---

## 🎨 UI MOCKUPS (Text-Based Previews)

### Mockup 1: Dashboard View
```
┌─────────────────────────────────────────────────────────┐
│  🚀 Seldenrijk CRM Dashboard                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │ 🔥 HOT     │ │ 🔶 WARM    │ │ 🧊 COLD    │          │
│  │ 15 leads   │ │ 28 leads   │ │ 42 leads   │          │
│  │ ────────── │ │ ────────── │ │ ────────── │          │
│  │ Score: 80+ │ │ Score: 50+ │ │ Score: <50 │          │
│  │ Resp: 12m  │ │ Resp: 45m  │ │ Resp: 2h   │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  🤖 Vraag me iets...                     [Send]  │   │
│  ├──────────────────────────────────────────────────┤   │
│  │  👤: Show hot leads                              │   │
│  │  🤖: 5 hot leads found:                          │   │
│  │      • Jan de Vries (95 pts) - Audi A6          │   │
│  │      • Lisa Peters (88 pts) - BMW 3 Series      │   │
│  │      [Show 3 more...]                            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  📊 ACTIVE CONVERSATIONS                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 🔥 Jan de Vries              [95]  8 min ago    │   │
│  │ Audi A6 interesse • €30k budget                  │   │
│  │ Tags: hot-lead, interesse-audi, intent-budget    │   │
│  │ [Reply] [Assign] [View]                          │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ 🔶 Lisa Peters               [72]  23 min ago   │   │
│  │ BMW 3 Series vraag over leasing                  │   │
│  │ Tags: warm-lead, interesse-bmw                   │   │
│  │ [Reply] [Assign] [View]                          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Mockup 2: AG-UI Detailed Interaction
```
┌──────────────────────────────────────────────────────┐
│  🤖 AG-UI Assistant                                  │
├──────────────────────────────────────────────────────┤
│                                                       │
│  👤: Audi A6 voorraad?                               │
│                                                       │
│  🤖: Ik vond 2 Audi A6 in voorraad:                 │
│                                                       │
│      ┌────────────────────────────────────────┐      │
│      │ 📌 2020 Audi A6 Avant                 │      │
│      │ ────────────────────────────────────── │      │
│      │ Brandstof: Diesel                      │      │
│      │ KM Stand: 45.000 km                    │      │
│      │ Prijs: €28.500                         │      │
│      │ Locatie: Showroom A                    │      │
│      │ [Meer Info] [Klant Koppelen]          │      │
│      └────────────────────────────────────────┘      │
│                                                       │
│      ┌────────────────────────────────────────┐      │
│      │ 📌 2021 Audi A6 Sedan                 │      │
│      │ ────────────────────────────────────── │      │
│      │ Brandstof: Benzine                     │      │
│      │ KM Stand: 30.000 km                    │      │
│      │ Prijs: €32.000                         │      │
│      │ Locatie: Showroom B                    │      │
│      │ [Meer Info] [Klant Koppelen]          │      │
│      └────────────────────────────────────────┘      │
│                                                       │
│  💡 Suggested: "Vergelijk deze 2 auto's"            │
│                                                       │
│  [Type your next question...]            [Send]     │
└──────────────────────────────────────────────────────┘
```

---

## ❓ RISKS & MITIGATION

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OpenAI API rate limits | High | Medium | Implement fallback to Claude, queue system |
| Chatwoot updates breaking iframe | Medium | Low | Use only stable Dashboard Apps API, version lock |
| Performance issues with 500+ conversations | Medium | Medium | Pagination, lazy loading, caching |
| iframe security vulnerabilities | High | Low | Strict origin validation, CSP headers |
| Database query performance | Medium | Medium | Index optimization, query caching |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users don't adopt AG-UI | High | Low | Training, clear examples, tooltips |
| Cost of OpenAI API calls | Medium | Medium | Smart caching, optimize prompts |
| Data privacy concerns | High | Low | Clear documentation, GDPR compliance |

---

## 💰 COST ANALYSIS

### Development Costs
- **Developer Time:** 56 hours × €75/hour = €4.200
- **Design (if external):** €500 (optional)
- **Testing:** Included in developer time

**Total Development:** €4.200 - €4.700

### Operational Costs (Monthly)
```
OpenAI API (GPT-4-Turbo):
  - 1000 queries/day × €0.03/query = €30/day
  - Monthly: €900

Railway Hosting (CRM App):
  - Starter plan: €5/month
  - OR usage-based: ~€20/month

Chatwoot (Self-Hosted):
  - Infrastructure: €50-100/month (VPS)

Total Monthly: €975 - €1.020
```

### Cost Optimization
- **Caching:** Reduce API calls by 40% → Save €360/month
- **Prompt Optimization:** Smaller tokens → Save 20% = €180/month
- **Smart Routing:** Use Claude for simple queries → Save €100/month

**Optimized Monthly:** €475 - €520

### ROI Calculation
```
Current Loss: €47.000/year (87% missed leads)

After CRM Dashboard:
  - Lead conversion: +40%
  - Missed leads: -70%
  - Revenue increase: €32.900/year

Cost:
  - Development: €4.200 (one-time)
  - Operations: €520/month = €6.240/year

Net Gain Year 1: €32.900 - €4.200 - €6.240 = €22.460
ROI: 535% in first year
Payback period: 1.9 months
```

---

## ✅ APPROVAL CHECKLIST

### Before Development Starts

**Design Approval:**
- [ ] Cyber Blue color scheme approved
- [ ] Dashboard layout approved
- [ ] AG-UI chat interface design approved
- [ ] Animations & effects acceptable

**Technical Approval:**
- [ ] Architecture diagram reviewed
- [ ] Tech stack confirmed (Next.js, OpenAI, etc.)
- [ ] Security model approved
- [ ] Deployment strategy accepted

**Functional Approval:**
- [ ] All CRM dashboard features confirmed
- [ ] AG-UI capabilities list approved
- [ ] Integration points validated

**Business Approval:**
- [ ] Timeline acceptable (7 days)
- [ ] Budget approved (€4.200 + €520/month)
- [ ] ROI projections reasonable
- [ ] Risk mitigation strategies acceptable

---

## 📞 NEXT STEPS

### Immediate Actions
1. **Review this PRD** - Read thoroughly, ask questions
2. **Approve or Request Changes** - Provide feedback
3. **Confirm Tech Stack** - Especially OpenAI vs alternatives
4. **Set Timeline** - When to start development?

### Questions for You
1. Do you want **any additional features** in the dashboard?
2. Are there **specific AG-UI queries** you want prioritized?
3. Do you have **existing inventory database schema** we should see?
4. Do you need **multi-language support** (beyond Dutch)?
5. Should we add **mobile app** later (separate project)?

### Contact
**Project Lead:** Claude (SDK AGENTS)
**Review Date:** 16 Oktober 2025
**Status:** ⏳ **AWAITING YOUR APPROVAL**

---

## 🎯 READY TO BUILD?

**Zeg gewoon "APPROVED - LET'S BUILD!" en we starten met Phase 1! 🚀**

Of vraag eerst:
- "Ik heb vragen over X"
- "Kan je Y aanpassen?"
- "Ik wil feature Z toevoegen"

**Jij beslist wanneer we beginnen!** ✅
