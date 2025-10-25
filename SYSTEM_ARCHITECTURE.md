# 🏗️ SPARC Phase 3: System Architecture
# World-Class Auto Sales Agent - Technical Design

**Project**: Seldenrijk Auto WhatsApp AI Agent
**Phase**: Architecture (System Design)
**Date**: 2025-01-13

---

## 📊 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          WHATSAPP MESSAGE INPUT                           │
│                    (Customer sends message via WhatsApp)                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         WAHA WEBHOOK RECEIVER                             │
│                      (FastAPI endpoint: /webhook/waha)                    │
│                    Converts WhatsApp → ConversationState                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         CELERY TASK QUEUE                                 │
│                    (Async processing with Redis)                          │
│                 Task: process_whatsapp_message_enhanced()                 │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                     ▼                       ▼
        ┌────────────────────┐  ┌────────────────────┐
        │   AGENT PIPELINE   │  │  STATE MANAGEMENT  │
        │   (Sequential)     │  │  (ConversationState)│
        └────────────────────┘  └────────────────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
    ┌─────────┐ ┌────────┐ ┌──────────┐
    │ ROUTER  │ │EXTRACT │ │EXPERTISE │ ← NEW
    │ AGENT   │ │ AGENT  │ │ AGENT    │
    └─────┬───┘ └────┬───┘ └────┬─────┘
          │          │          │
          └──────────┴──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ ESCALATION DECISION │
          │   (if needed)       │
          └──────┬──────┬───────┘
                 │      │
       ┌─────────┘      └─────────┐
       │ NO ESCALATION            │ ESCALATION NEEDED
       ▼                          ▼
┌──────────────┐        ┌──────────────────────┐
│  RAG AGENT   │        │ ESCALATION ROUTER    │ ← NEW
│ (if car_inq) │        │ • WhatsApp notify    │
└──────┬───────┘        │ • Email notify       │
       │                │ • Chatwoot assign    │
       │                └──────────┬───────────┘
       │                           │
       └───────────┬───────────────┘
                   ▼
        ┌──────────────────────┐
        │ CONVERSATION AGENT   │ ← ENHANCED
        │ • Expert responses   │
        │ • Human-like tone    │
        │ • RAG integration    │
        │ • Graceful handoffs  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │    CRM AGENT         │ ← ENHANCED
        │ • 20+ tags           │
        │ • Lead scoring       │
        │ • Custom attributes  │
        └──────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────┐    ┌──────────────────┐
│  CHATWOOT    │    │  WHATSAPP REPLY  │
│  CRM UPDATE  │    │  (via WAHA API)  │
└──────────────┘    └──────────────────┘
```

---

## 🔌 Component Details

### 1. **WAHA (WhatsApp HTTP API)**

**Purpose**: WhatsApp Business API interface
**Technology**: Docker container (devlikeapro/waha)
**Port**: 3000

**Endpoints Used**:
- `POST /api/sendText` - Send messages to customers
- `POST /webhook` - Receive incoming messages

**Configuration**:
```yaml
# docker-compose.yml
waha:
  image: devlikeapro/waha
  ports:
    - "3000:3000"
  environment:
    - WHATSAPP_API_KEY=${WAHA_API_KEY}
```

---

### 2. **FastAPI Webhook Receiver**

**Purpose**: Receive WhatsApp webhooks and trigger processing
**File**: `app/api/webhooks.py`
**Port**: 8000

**Endpoint**:
```python
@router.post("/webhook/waha")
async def waha_webhook(payload: Dict):
    """
    Receive WhatsApp message → Create state → Queue Celery task
    """

    # Parse message
    message_data = parse_waha_payload(payload)

    # Create initial state
    state = create_initial_state(
        message_id=message_data["id"],
        conversation_id=message_data["conversation_id"],
        content=message_data["body"],
        sender_phone=message_data["from"],
        sender_name=message_data["name"],
        account_id=CHATWOOT_ACCOUNT_ID,
        inbox_id=CHATWOOT_INBOX_ID,
        source="waha"
    )

    # Queue async processing
    process_whatsapp_message_enhanced.delay(state)

    return {"status": "queued"}
```

---

### 3. **Celery Task Queue**

**Purpose**: Async message processing (prevents webhook timeouts)
**Broker**: Redis
**Worker**: `app/celery_worker.py`

**Configuration**:
```python
# app/celery_app.py
app = Celery(
    "seldenrijk",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# Task
@app.task
def process_whatsapp_message_enhanced(state: Dict):
    """
    Main processing task - runs all agents in sequence
    """
    # See workflow in pseudocode section
```

**Why Celery?**
- WhatsApp webhooks have 5-second timeout
- Our agent pipeline takes 3-8 seconds
- Celery allows async processing without webhook timeout

---

### 4. **Agent Pipeline** (Sequential Execution)

#### 4.1 RouterAgent
**File**: `app/agents/router_agent.py`
**Model**: Claude 3.5 Haiku (fast)
**Purpose**: Classify intent

**Input**: User message
**Output**:
```python
{
    "intent": "car_inquiry" | "financing_inquiry" | "complaint" | ...,
    "priority": "high" | "medium" | "low",
    "needs_extraction": True/False,
    "confidence": 0.95
}
```

#### 4.2 ExtractionAgent
**File**: `app/agents/extraction_agent.py`
**Model**: Claude 3.5 Haiku
**Purpose**: Extract structured data

**Input**: User message
**Output**:
```python
{
    "car_preferences": {
        "make": "Volkswagen",
        "model": "Golf 8",
        "fuel_type": "diesel",
        "max_price": 25000
    },
    "urgency_level": "high",
    "has_trade_in": False,
    "needs_financing": False
}
```

#### 4.3 ExpertiseAgent (NEW)
**File**: `app/agents/expertise_agent.py`
**Model**: Claude 3.5 Haiku
**Purpose**: Determine knowledge module + escalation

**Input**: User message + state
**Output**:
```python
{
    "classification": {
        "primary_domain": "financial",
        "complexity_level": "complex",
        "confidence": 0.92
    },
    "escalation_decision": {
        "escalate": True,
        "escalation_type": "finance_advisor",
        "urgency": "high",
        "reason": "complex_financing"
    },
    "knowledge": {...}  # Or None if escalating
}
```

**Knowledge Modules** (embedded in class):
- `TechnicalKnowledgeModule` - Motor types, features, fuel consumption
- `FinancialKnowledgeModule` - Financing options, monthly payments, trade-in
- `ServiceKnowledgeModule` - Test drives, warranty, delivery

#### 4.4 EscalationRouter (NEW)
**File**: `app/agents/escalation_router.py`
**Purpose**: Notify humans via WhatsApp + Email

**Channels**:
1. **WhatsApp** (via WAHA API)
   - Target: Specialist phone numbers
   - Format: Short, urgent notification
   - Example: "🚨 ESCALATIE: Finance Advisor\nKlant: Jan\nVraag: BKR-registratie financiering"

2. **Email** (via SMTP)
   - Target: Team email addresses
   - Format: Detailed formal email
   - CC: Manager (if urgent)

3. **Chatwoot**
   - Assign conversation to specialist
   - Add internal note
   - Tag with "escalated"

**Configuration**:
```python
# .env
ESCALATION_WHATSAPP_FINANCE=+31612345678
ESCALATION_WHATSAPP_TECHNICAL=+31687654321
ESCALATION_WHATSAPP_MANAGER=+31611111111

ESCALATION_EMAIL_FINANCE=finance@seldenrijk.nl
ESCALATION_EMAIL_TECHNICAL=techniek@seldenrijk.nl
ESCALATION_EMAIL_MANAGER=manager@seldenrijk.nl

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=notifications@seldenrijk.nl
SMTP_PASSWORD=${SMTP_PASS}
```

#### 4.5 RAGAgent
**File**: `app/agents/rag_agent.py`
**Purpose**: Search inventory (Marktplaats + Website)

**Currently**: Playwright-based scraping (needs architecture fix)
**Recommendation**: Switch to Python `requests` + `BeautifulSoup`

**Flow**:
1. Check 10-minute cache
2. If miss: Scrape Marktplaats dealer page
3. Parse listings (make, model, price, year, mileage)
4. Filter by criteria (price, fuel type, mileage)
5. Rank by relevance (exact match = higher score)
6. Cache results
7. Return top 3 matches

#### 4.6 ConversationAgent (ENHANCED)
**File**: `app/agents/conversation_agent.py`
**Model**: Claude 3.5 Sonnet (high quality)
**Purpose**: Generate world-class responses

**Features**:
- Integrates expertise knowledge
- Uses RAG results for car info
- Generates graceful escalation messages
- Human-like tone (Dutch colloquialisms)
- Emoji usage (subtle)
- Response templates

**System Prompt**: See `ENHANCED_SYSTEM_PROMPT` in pseudocode

#### 4.7 CRMAgent (ENHANCED)
**File**: `app/agents/crm_agent.py`
**Purpose**: Tag + score leads + update Chatwoot

**Functions**:
1. **Tag Generation** (20+ tags):
   - Interest: `interest:browsing`, `interest:ready-to-buy`
   - Urgency: `urgency:low`, `urgency:critical`
   - Channel: `channel:whatsapp-direct`, `channel:marktplaats`
   - Car: `car:volkswagen`, `fuel:diesel`, `budget:15k-25k`
   - Stage: `stage:test-drive-requested`, `stage:financing-discussion`
   - Special: `escalated`, `complaint`, `vip`

2. **Lead Scoring** (0-100):
   - 80-100: HOT (ready to buy)
   - 60-79: WARM (serious consideration)
   - 40-59: LUKEWARM (gathering info)
   - 0-39: COLD (just browsing)

3. **Custom Attributes**:
   ```python
   {
       "interested_in_make": "Volkswagen",
       "interested_in_model": "Golf 8",
       "budget_max": 25000,
       "lead_quality": "WARM",
       "lead_score": 75,
       "urgency_level": "high",
       "has_trade_in": False,
       "financing_needed": False,
       "test_drive_requested": True,
       "source_channel": "marktplaats",
       "conversation_sentiment": "positive"
   }
   ```

---

### 5. **Chatwoot CRM**

**Purpose**: Customer conversation management
**Technology**: Self-hosted Chatwoot instance
**Port**: 3100

**API Integration**:
```python
# app/integrations/chatwoot_api.py
class ChatwootAPI:
    def __init__(self):
        self.base_url = "https://chatwoot.yourdomain.com/api/v1"
        self.api_token = os.getenv("CHATWOOT_API_TOKEN")

    def update_contact_attributes(self, contact_id: str, attributes: Dict):
        """Update custom attributes"""

    def add_label(self, conversation_id: str, label: str):
        """Add tag to conversation"""

    def assign_conversation(self, conversation_id: str, assignee_id: int):
        """Assign to team member"""

    def add_message(self, conversation_id: str, content: str, private: bool):
        """Add internal note or public message"""
```

**Custom Attributes Schema**:
```javascript
// Chatwoot Admin → Settings → Custom Attributes
{
  "interested_in_make": { "type": "text" },
  "interested_in_model": { "type": "text" },
  "interested_in_fuel_type": { "type": "text" },
  "budget_max": { "type": "number" },
  "budget_min": { "type": "number" },
  "lead_quality": { "type": "list", "values": ["HOT", "WARM", "LUKEWARM", "COLD"] },
  "lead_score": { "type": "number" },
  "urgency_level": { "type": "list", "values": ["low", "medium", "high", "critical"] },
  "has_trade_in": { "type": "checkbox" },
  "financing_needed": { "type": "checkbox" },
  "test_drive_requested": { "type": "checkbox" },
  "source_channel": { "type": "text" },
  "conversation_sentiment": { "type": "list", "values": ["positive", "neutral", "negative"] },
  "last_interest_date": { "type": "date" },
  "total_conversations": { "type": "number" }
}
```

---

### 6. **State Management**

**File**: `app/orchestration/state.py`
**Pattern**: TypedDict (shared state across agents)

**Enhanced State Structure**:
```python
class ConversationState(TypedDict):
    # Input
    message_id: str
    conversation_id: str
    contact_id: Optional[str]
    content: str
    sender_name: str
    sender_phone: str
    timestamp: datetime
    source: str  # "waha", "chatwoot", "marktplaats"

    # Agent outputs
    router_output: Optional[RouterOutput]
    extraction_output: Optional[ExtractionOutput]
    expertise_output: Optional[ExpertiseOutput]  # NEW
    escalation_result: Optional[EscalationResult]  # NEW
    rag_results: Optional[List[Dict]]
    conversation_output: Optional[ConversationOutput]
    crm_output: Optional[CRMOutput]

    # Control flow
    needs_escalation: bool  # NEW
    escalation_type: Optional[str]  # NEW
    next_agent: str
    error_occurred: bool

    # Metadata
    processing_start_time: datetime
    total_tokens_used: int
    total_cost_usd: float
```

---

## 📦 Database Schema (Optional - Future)

Currently using in-memory caching. For production scale:

### Escalations Table
```sql
CREATE TABLE escalations (
    id VARCHAR(50) PRIMARY KEY,
    escalation_type VARCHAR(50) NOT NULL,
    urgency VARCHAR(20) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(100),
    conversation_id VARCHAR(100),
    reason TEXT,
    whatsapp_sent BOOLEAN,
    email_sent BOOLEAN,
    assigned_to VARCHAR(100),
    status VARCHAR(20),  -- pending, in_progress, resolved
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);
```

### RAG Cache Table
```sql
CREATE TABLE rag_cache (
    cache_key VARCHAR(200) PRIMARY KEY,
    search_query TEXT,
    results JSONB,
    total_found INT,
    cached_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    hit_count INT DEFAULT 0
);
```

### Lead Scores Table
```sql
CREATE TABLE lead_scores (
    customer_phone VARCHAR(20) PRIMARY KEY,
    lead_score INT,
    lead_quality VARCHAR(20),
    last_updated TIMESTAMP DEFAULT NOW(),
    score_history JSONB
);
```

---

## 🔐 Security & Configuration

### Environment Variables
```bash
# .env file structure

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
CHATWOOT_API_TOKEN=...
WAHA_API_KEY=...

# Chatwoot Config
CHATWOOT_BASE_URL=https://chatwoot.yourdomain.com
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Escalation Config
ESCALATION_WHATSAPP_FINANCE=+31612345678
ESCALATION_WHATSAPP_TECHNICAL=+31687654321
ESCALATION_WHATSAPP_MANAGER=+31611111111
ESCALATION_EMAIL_FINANCE=finance@seldenrijk.nl
ESCALATION_EMAIL_TECHNICAL=techniek@seldenrijk.nl
ESCALATION_EMAIL_MANAGER=manager@seldenrijk.nl

# SMTP Config
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=notifications@seldenrijk.nl
SMTP_PASSWORD=...

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Feature Flags
ENABLE_ESCALATION=true
ENABLE_RAG=true
ENABLE_LEAD_SCORING=true
RAG_CACHE_DURATION_SECONDS=600
```

### Secrets Management
- Use `.env` file for local development
- Use Docker secrets for production
- NEVER commit `.env` to git
- Use environment-specific configs

---

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│              DOCKER COMPOSE STACK                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   FastAPI   │  │   Celery    │  │   Redis    │ │
│  │  (webhook)  │  │   Worker    │  │  (broker)  │ │
│  │   Port 8000 │  │             │  │            │ │
│  └─────────────┘  └─────────────┘  └────────────┘ │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐                 │
│  │  Chatwoot   │  │    WAHA     │                 │
│  │   (CRM)     │  │  (WhatsApp) │                 │
│  │  Port 3100  │  │  Port 3000  │                 │
│  └─────────────┘  └─────────────┘                 │
│                                                     │
└─────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────────┐
   │ Internet │        │  WhatsApp    │
   │  (Web)   │        │   Business   │
   └──────────┘        └──────────────┘
```

### docker-compose.yml (Updated)
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  fastapi:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CHATWOOT_API_TOKEN=${CHATWOOT_API_TOKEN}
      - REDIS_HOST=redis
    depends_on:
      - redis

  celery-worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CHATWOOT_API_TOKEN=${CHATWOOT_API_TOKEN}
      - REDIS_HOST=redis
      - ENABLE_ESCALATION=true
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    depends_on:
      - redis

  chatwoot:
    image: chatwoot/chatwoot:latest
    ports:
      - "3100:3000"
    environment:
      - SECRET_KEY_BASE=${CHATWOOT_SECRET}
      - POSTGRES_HOST=chatwoot-postgres
    depends_on:
      - chatwoot-postgres

  waha:
    image: devlikeapro/waha
    ports:
      - "3000:3000"
    environment:
      - WHATSAPP_API_KEY=${WAHA_API_KEY}

volumes:
  redis_data:
  chatwoot_postgres_data:
```

---

## 📈 Performance Considerations

### Response Time Targets
- WhatsApp webhook response: < 200ms (immediate 200 OK)
- Total processing time: 3-8 seconds
- RAG search (cold): 2-4 seconds
- RAG search (cached): < 100ms
- Escalation notification: < 1 second

### Scalability
- Celery workers: Scale horizontally (add more workers)
- Redis: Single instance sufficient for < 10k messages/day
- Agent API calls: Parallel where possible
- Database: Add if caching needs persist beyond 10 minutes

### Cost Optimization
- Use prompt caching (90% cost reduction on repeated prompts)
- Use Claude Haiku for fast agents (Router, Extraction, Expertise)
- Use Claude Sonnet only for Conversation (quality matters)
- RAG caching reduces scraping frequency

**Estimated Costs per 1000 messages**:
- Router Agent (Haiku): $0.25
- Extraction Agent (Haiku): $0.30
- Expertise Agent (Haiku): $0.25
- Conversation Agent (Sonnet): $3.00
- Total: ~$4.00 per 1000 messages

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/agents/test_expertise_agent.py
def test_expertise_classification():
    agent = ExpertiseAgent()
    result = agent._classify_query("Wat is het brandstofverbruik?")
    assert result["primary_domain"] == "technical"
    assert result["complexity_level"] == "simple"

def test_escalation_trigger_complex_financing():
    agent = ExpertiseAgent()
    result = agent._check_escalation_triggers(
        message="Kan ik financieren met BKR?",
        classification={"complexity_level": "complex"},
        conversation_history=[]
    )
    assert result["escalate"] == True
    assert result["escalation_type"] == "finance_advisor"
```

### Integration Tests
```python
# tests/integration/test_full_pipeline.py
def test_car_inquiry_flow():
    """Test complete flow: car inquiry → RAG → response"""

    state = create_test_state("Ik zoek een Golf 8 diesel, €25.000")

    # Run full pipeline
    result = process_whatsapp_message_enhanced(state)

    # Assertions
    assert result["router_output"]["intent"] == "car_inquiry"
    assert result["extraction_output"]["car_preferences"]["make"] == "Volkswagen"
    assert result["expertise_output"]["escalation_decision"]["escalate"] == False
    assert len(result["rag_results"]) > 0
    assert result["crm_output"]["lead_score"] > 60  # WARM lead

def test_escalation_flow():
    """Test escalation: complex question → notify humans"""

    state = create_test_state("Ik heb BKR, kan ik financieren?")

    result = process_whatsapp_message_enhanced(state)

    assert result["expertise_output"]["escalation_decision"]["escalate"] == True
    assert result["escalation_result"]["whatsapp_sent"] == True
    assert result["escalation_result"]["email_sent"] == True
    assert "escalated" in result["crm_output"]["tags_added"]
```

### E2E Tests (Manual)
1. Send WhatsApp message via real phone
2. Verify webhook received
3. Check Celery logs for agent execution
4. Verify response sent back
5. Check Chatwoot for tags + attributes
6. Test escalation notification received

---

## 📊 Monitoring & Observability

### Logging Strategy
```python
# All agents log at key points
logger.info("✅ ExpertiseAgent: Classification complete", extra={
    "message_id": state["message_id"],
    "domain": classification["primary_domain"],
    "escalate": escalation_decision["escalate"],
    "confidence": classification["confidence"]
})

logger.warning("⚠️ RAG cache miss, scraping websites", extra={
    "cache_key": cache_key
})

logger.error("❌ Escalation WhatsApp failed", extra={
    "recipient": recipient,
    "error": str(e)
}, exc_info=True)
```

### Metrics to Track
- Total messages processed
- Average response time
- Escalation rate (%)
- Lead score distribution
- RAG cache hit rate
- Agent token usage
- Cost per message

### Dashboards (Future)
- Grafana dashboard with:
  - Messages per hour
  - Agent performance
  - Escalation trends
  - Lead quality distribution
  - Cost tracking

---

**✅ Phase 3 Complete!**

System architecture is fully designed. Ready for **Phase 4: Code Implementation**.
