# 📋 PRD v5.1: CHATWOOT-CENTRIC WHATSAPP RECRUITMENT PLATFORM

**Version**: 5.1
**Date**: 2025-01-15
**Status**: APPROVED - Ready for Implementation
**Architecture**: Chatwoot-Centric (Simplified from v5.0 Dual UI)

---

## 🎯 EXECUTIVE SUMMARY

### Evolution Path
```
v4.0 (Chatwoot + 5 Agents)
  ↓
v5.0 (Dual UI: Chatwoot + Next.js, 7 Agents, Multi-tenant SaaS) ❌ TOO COMPLEX
  ↓
v5.1 (Chatwoot-Centric, 4 Agents, White-label) ✅ USER APPROVED
```

### Why v5.1 Simplification?
1. **User Feedback**: "Ik wil geen SaaS bouwen en een multi tenant"
2. **Faster Time-to-Market**: 8 weeks (vs 14 weeks v5.0)
3. **Lower Cost**: €115/month per client (vs $618-743/month v5.0)
4. **Sufficient Functionality**: Chatwoot CRM covers user's 3 use cases
5. **Future-Proof**: Can add Next.js dashboard later if needed

### Core Value Proposition
**White-label conversational AI CRM** that combines:
- Multi-channel inbox (WhatsApp, Instagram, Email)
- AI-powered conversation handling (Agentic RAG)
- CRM with segmentation
- Human-AI hybrid workflow
- Per-client customization

---

## 🏗️ SYSTEM ARCHITECTURE

### High-Level Overview
```
┌─────────────────────────────────────────────────────┐
│  USER CHANNELS                                      │
│  - WhatsApp (360Dialog)                             │
│  - Instagram DMs (Meta Graph API)                   │
│  - Email (IMAP/SMTP)                                │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│  CHATWOOT (Primary UI + CRM)                        │
│  - Multi-channel inbox                              │
│  - Contact management (custom attributes)           │
│  - Labels/tags for segmentation                     │
│  - Webhooks (message_created)                       │
└────────────────┬────────────────────────────────────┘
                 ↓ Webhook: POST /webhooks/chatwoot
┌─────────────────────────────────────────────────────┐
│  FASTAPI WEBHOOK RECEIVER                           │
│  - Receives Chatwoot events                         │
│  - Triggers LangGraph processing                    │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│  LANGGRAPH ORCHESTRATOR                             │
│  ┌──────────────────────────────────────┐          │
│  │ Router Agent (GPT-4o-mini)           │          │
│  │ ↓                                     │          │
│  │ Extraction Agent (Pydantic AI)       │          │
│  │ ↓                                     │          │
│  │ Conversation Agent (Claude SDK)      │          │
│  │   ├─ Agentic RAG (PGVector search)   │          │
│  │   └─ Response generation             │          │
│  │ ↓                                     │          │
│  │ CRM Agent (GPT-4o-mini)              │          │
│  │   └─ Update Chatwoot contact         │          │
│  └──────────────────────────────────────┘          │
└────────────────┬────────────────────────────────────┘
                 ↓ API Call
┌─────────────────────────────────────────────────────┐
│  CHATWOOT API                                       │
│  POST /api/v1/.../messages                          │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│  USER CHANNELS (Response delivery)                  │
└─────────────────────────────────────────────────────┘
```

### Technology Stack
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Frontend UI** | Chatwoot | latest | Multi-channel inbox + CRM |
| **Orchestration** | LangGraph | 0.2.62 | Agent workflow management |
| **Agent 1** | Pydantic AI | ≥0.0.14 | Structured extraction |
| **Agent 2** | Claude SDK | 0.42.0 | Conversation + Agentic RAG |
| **Router/CRM** | OpenAI GPT-4o-mini | 1.59.5 | Fast routing + CRM updates |
| **Backend** | FastAPI | 0.115.6 | Webhook receiver + API |
| **Database** | PostgreSQL (Chatwoot) | 14 | Conversations, contacts |
| **Vector DB** | Supabase PGVector | 0.3.6 | Knowledge base embeddings |
| **WhatsApp Test** | WhatsApp MCP | latest | Development testing |
| **WhatsApp Prod** | 360Dialog | API v2 | Production WhatsApp |
| **Deployment** | Railway + Docker | - | Hosting infrastructure |

---

## 🤖 AGENT ARCHITECTURE (4 AGENTS)

### CRITICAL CLARIFICATION: LangGraph vs Agents

**LangGraph = ORCHESTRATOR** (NOT an AI model!)
- Role: Workflow coordinator (like airport traffic control)
- Job: Route messages between agents, manage state
- Does: Conditional branching, error handling, state management
- Does NOT: Make AI calls itself

**Agents = NODES** within LangGraph
- Each agent makes AI API calls (Claude, GPT-4o-mini, Pydantic AI)
- LangGraph decides which agent runs when

### Agent 1: Router Agent (GPT-4o-mini)
**Purpose**: Classify message intent and route to appropriate specialists

**Prompt**:
```python
system_prompt = """You are a routing agent. Classify the user's message intent.

Categories:
- product_inquiry: Questions about products/services
- policy_question: Return policy, terms, FAQ
- support_request: Help with issues, complaints
- job_search: Looking for jobs, vacancies (recruitment use case)
- general: Greetings, chitchat
- qualification: Lead qualification questions

Output: Single category name only."""
```

**Input**: Raw message text
**Output**: Intent category (string)
**Model**: GPT-4o-mini (fast + cheap: $0.15/1M input tokens)

---

### Agent 2: Extraction Agent (Pydantic AI)
**Purpose**: Extract structured data from messages for CRM

**Pydantic Models**:
```python
from pydantic import BaseModel
from typing import Literal

class ExtractedData(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    job_type: Optional[Literal["interim", "permanent", "freelance"]]
    urgency: Literal["high", "medium", "low"]
    intent: str
    key_phrases: List[str]
```

**Pydantic AI Agent**:
```python
from pydantic_ai import Agent

extraction_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=ExtractedData,
    system_prompt="Extract structured contact and lead data from conversations"
)

# Usage
result = await extraction_agent.run(message_content)
print(result.data)  # ExtractedData instance, validated!
```

**Why Pydantic AI?**
- Automatic validation (Pydantic models)
- Type safety
- Fast (GPT-4o-mini backend)
- Clean structured output (no parsing errors)

---

### Agent 3: Conversation Agent (Claude SDK + Agentic RAG)
**Purpose**: Generate responses + autonomously search knowledge base when needed

**CRITICAL**: Agentic RAG = Agent DECIDES to search (NOT automatic!)

**Claude Tool Definition**:
```python
search_kb_tool = {
    "name": "search_knowledge_base",
    "description": "Search company knowledge base for policies, products, FAQs, procedures. Use when user asks factual questions about company information.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {
                "type": "string",
                "enum": ["policy", "product", "faq", "procedure"],
                "description": "Category filter (optional)"
            }
        },
        "required": ["query"]
    }
}
```

**Agentic RAG Implementation**:
```python
async def conversation_agent_node(state: ConversationState):
    """LangGraph node: Claude agent with Agentic RAG"""

    # Initial call with tools available
    response = await claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": state["message_content"]}],
        tools=[search_kb_tool]  # Agent CAN use, not forced!
    )

    # Agent decided to search?
    if response.stop_reason == "tool_use":
        tool_use = response.content[0]

        # Execute vector search
        results = await search_vector_db(
            query=tool_use.input["query"],
            category=tool_use.input.get("category")
        )

        # Continue conversation with results
        response = await claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {"role": "user", "content": state["message_content"]},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": str(results)
                    }]
                }
            ]
        )

    return {"agent_response": response.content[0].text}
```

**Agent Decision Logic**:
- User: "What's your return policy?" → Agent searches KB
- User: "Hello!" → Agent responds directly (no search)
- User: "Track my order #123" → Agent uses different tool

---

### Agent 4: CRM Agent (GPT-4o-mini)
**Purpose**: Update Chatwoot contact attributes and labels

**Implementation**:
```python
async def crm_agent_node(state: ConversationState):
    """Update Chatwoot contact with extracted data"""

    contact_id = state["contact_id"]
    extracted = state["extracted_data"]

    # Update custom attributes
    await chatwoot.update_contact(
        contact_id=contact_id,
        custom_attributes={
            "lead_status": determine_lead_status(extracted),
            "budget_range": f"€{extracted.budget_min}-{extracted.budget_max}",
            "job_type_preference": extracted.job_type,
            "urgency_level": extracted.urgency,
            "last_intent": extracted.intent,
            "ai_summary": await generate_summary(state),
            "last_updated": datetime.now().isoformat()
        }
    )

    # Add/update labels
    labels = determine_labels(extracted)
    await chatwoot.update_labels(contact_id, labels)

    return {"crm_updated": True}
```

---

## 🔄 LANGGRAPH STATE MACHINE

### ConversationState TypedDict
```python
from typing import TypedDict, Literal, Optional, List, Dict

class ConversationState(TypedDict):
    # Chatwoot context
    message_id: str
    conversation_id: str
    contact_id: str
    account_id: str
    channel: Literal["whatsapp", "instagram", "email", "telegram"]

    # Message content
    message_content: str
    message_type: Literal["incoming", "outgoing"]

    # Agent outputs
    intent: str
    priority: Literal["high", "medium", "low"]
    sentiment: float  # -1.0 to 1.0

    extracted_data: Optional[Dict]  # Pydantic AI output
    rag_results: Optional[List[Dict]]  # Vector search results
    agent_response: Optional[str]  # Claude response

    # Routing
    needs_human: bool
    route: Literal["automated", "human", "hybrid"]

    # Context
    contact_profile: Dict
    conversation_history: List[Dict]
```

### StateGraph Definition
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(ConversationState)

# Add nodes (agents)
graph.add_node("router", router_agent_node)
graph.add_node("extraction", extraction_agent_node)
graph.add_node("conversation", conversation_agent_node)
graph.add_node("crm", crm_agent_node)

# Add edges (routing logic)
graph.add_edge(START, "router")
graph.add_edge("router", "extraction")

# Conditional: Check if human needed
def should_route_to_human(state: ConversationState) -> str:
    if state["priority"] == "high" or "complaint" in state["intent"]:
        state["needs_human"] = True
        return END  # Stop, let human handle
    return "conversation"

graph.add_conditional_edges(
    "extraction",
    should_route_to_human,
    {"conversation": "conversation", END: END}
)

graph.add_edge("conversation", "crm")
graph.add_edge("crm", END)

# Compile
app = graph.compile()
```

---

## 💾 DATABASE SCHEMA

### Chatwoot PostgreSQL (Existing Schema)
```sql
-- Contacts (CRM)
contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone_number VARCHAR(50),
    custom_attributes JSONB,  -- Our data goes here!
    created_at TIMESTAMP
);

-- Custom Attributes Structure (JSONB)
{
    "lead_status": "qualified",
    "budget_range": "€70-90k",
    "job_type_preference": "interim",
    "urgency_level": "high",
    "last_intent": "job_search",
    "ai_summary": "Interested in tech interim roles...",
    "instagram_handle": "@username",
    "follower_count": 15000,
    "lead_source": "instagram_scrape",
    "scraped_date": "2025-01-15"
}

-- Contact Labels (Tags)
contact_labels (
    id SERIAL PRIMARY KEY,
    contact_id INT REFERENCES contacts(id),
    label_id INT REFERENCES labels(id)
);

-- Labels
labels (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),  -- e.g., "high-priority", "qualified-lead"
    color VARCHAR(7)     -- Hex color
);

-- Conversations
conversations (
    id SERIAL PRIMARY KEY,
    contact_id INT REFERENCES contacts(id),
    inbox_id INT REFERENCES inboxes(id),
    status VARCHAR(50),  -- open, resolved, pending
    created_at TIMESTAMP
);

-- Messages
messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT REFERENCES conversations(id),
    content TEXT,
    message_type VARCHAR(50),  -- incoming, outgoing
    created_at TIMESTAMP
);
```

### Supabase PGVector (RAG Knowledge Base)
```sql
-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimension
    metadata JSONB,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metadata structure (JSONB)
{
    "title": "Return Policy",
    "category": "policy",
    "source": "company_handbook.pdf",
    "page_number": 15,
    "last_updated": "2025-01-01"
}

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT,
    filter JSONB DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        (filter IS NULL OR documents.metadata @> filter)
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Index for fast similarity search
CREATE INDEX ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 🚀 3 PRIMARY USE CASES

### Use Case 1: Recruitment Agency
**Scenario**: Interim recruitment, vacancy matching, lead qualification

**Workflow**:
```
1. Lead registers on website → Form submission
2. Lead receives email with link to WhatsApp chat
3. WhatsApp conversation starts (via 360Dialog → Chatwoot)
4. LangGraph agents process:
   - Extract: name, job preference, budget
   - Agentic RAG: Search for matching vacancies
   - Response: "We have 3 positions matching your profile..."
5. CRM Agent updates Chatwoot:
   - custom_attributes.job_type = "interim"
   - custom_attributes.budget = "€70-90k"
   - labels = ["qualified-lead", "tech-sector"]
6. Human views contact in Chatwoot CRM:
   - See full profile with AI summary
   - See chat history
   - Send personalized vacancy details (one button)
7. Follow-up handled by human OR agent
```

**Key Features Used**:
- Multi-channel (Email → WhatsApp handoff)
- Agentic RAG (vacancy search)
- CRM segmentation (job type, budget)
- AI summary
- Human takeover

---

### Use Case 2: Influencer E-commerce
**Scenario**: Instagram DM + WhatsApp customer support

**Workflow**:
```
1. Customer sends Instagram DM: "Do you have size 42 in stock?"
2. Instagram → Chatwoot (via Meta Graph API)
3. LangGraph agents:
   - Conversation Agent checks stock (external API tool)
   - Response: "Yes! Size 42 available. Order via WhatsApp?"
4. Customer switches to WhatsApp
5. Order questions → Agentic RAG searches FAQ
6. Complex question → needs_human = True → Human notified
7. Human takes over in Chatwoot
8. CRM Agent updates:
   - custom_attributes.product_interest = "sneakers"
   - custom_attributes.size_preference = "42"
   - labels = ["high-value-customer"]
```

**Key Features Used**:
- Multi-channel (Instagram + WhatsApp)
- External API integration (stock check)
- Agentic RAG (FAQ search)
- Human takeover
- Segmentation

---

### Use Case 3: Dubai Business Setup Service
**Scenario**: Lead qualification BEFORE onboarding

**Workflow**:
```
1. Lead fills registration form → Receives WhatsApp link
2. WhatsApp qualification conversation:
   - Agent asks: Budget? Company type? Timeline?
3. LangGraph Extraction Agent:
   - Extracts: budget, company_type, timeline
4. Agentic RAG answers common questions:
   - "How long does visa processing take?" → Searches KB
   - "What documents needed?" → Searches KB
5. Qualified leads (budget > €10k):
   - CRM Agent: labels = ["qualified"]
   - Agent schedules video call (Calendly integration)
6. Unqualified leads:
   - labels = ["unqualified"]
   - Automated FAQ responses only
7. Post-qualification:
   - Human sends onboarding form
   - Ongoing WhatsApp support (Agent + Human hybrid)
```

**Key Features Used**:
- Lead qualification workflow
- Agentic RAG (policy/procedure questions)
- CRM segmentation (qualified vs unqualified)
- Video call scheduling
- Human-AI hybrid

---

## 📦 SCRAPCREATORS INTEGRATION

### Complete Workflow
```
PHASE 1: SCRAPING (ScrapeCreators tool)
├─ Scrape Instagram profiles/followers
├─ Extract: name, email, WhatsApp, bio, follower_count
└─ Export: CSV file

PHASE 2: IMPORT TO CHATWOOT (Python script)
├─ Read CSV
├─ For each lead:
│   ├─ Create Contact in Chatwoot (POST /api/v1/contacts)
│   ├─ Set custom attributes:
│   │   - lead_source: "instagram_scrape"
│   │   - instagram_handle: "@username"
│   │   - follower_count: 15000
│   ├─ Add labels: ["scraped-lead", "cold-outreach"]
│   └─ Store in database

PHASE 3: OUTREACH CAMPAIGN (via Chatwoot)
├─ Filter contacts: label = "cold-outreach"
├─ Agent generates personalized message (based on bio)
├─ Human approves message
├─ Send via WhatsApp (360Dialog) OR Email
└─ Rate limiting: 50 messages/hour (anti-spam)

PHASE 4: RESPONSES (in Chatwoot inbox)
├─ WhatsApp reply → Chatwoot (via 360Dialog webhook)
├─ Email reply → Chatwoot (via IMAP)
├─ LangGraph processes response
└─ Human sees full conversation in Chatwoot
```

### Python Import Script
```python
# scraping_to_chatwoot.py
import csv
import httpx
from typing import List, Dict

CHATWOOT_URL = "https://your-chatwoot.railway.app"
CHATWOOT_API_TOKEN = "your_token"
ACCOUNT_ID = "1"

async def import_scraped_leads(csv_file: str) -> None:
    """Import leads from ScrapeCreators CSV to Chatwoot"""

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Create contact
                response = await httpx.post(
                    f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts",
                    headers={"api_access_token": CHATWOOT_API_TOKEN},
                    json={
                        "name": row['name'],
                        "email": row['email'],
                        "phone_number": row['whatsapp'],
                        "custom_attributes": {
                            "lead_source": "instagram_scrape",
                            "instagram_handle": row['username'],
                            "follower_count": int(row['followers']),
                            "bio": row['bio'],
                            "niche": row['niche'],
                            "scraped_date": "2025-01-15"
                        }
                    }
                )

                contact_id = response.json()['payload']['contact']['id']

                # Add labels
                await httpx.post(
                    f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts/{contact_id}/labels",
                    headers={"api_access_token": CHATWOOT_API_TOKEN},
                    json={"labels": ["scraped-lead", "cold-outreach", "instagram"]}
                )

                print(f"✅ Imported: {row['name']}")

            except Exception as e:
                print(f"❌ Error: {row['name']} - {e}")

# Usage
await import_scraped_leads('leads.csv')
```

### ⚠️ COMPLIANCE WARNINGS

**GDPR (EU)**:
- Legitimate Interest: Document why scraping
- Right to Object: Include opt-out in first message
- Data Minimization: Only scrape necessary fields
- Retention: Delete after 6 months if no response

**WhatsApp Business Policy**:
- ❌ NO cold outreach to scraped numbers (ban risk!)
- ✅ Send first message via EMAIL (no restrictions)
- ✅ If they reply via WhatsApp → then WhatsApp chat OK
- ✅ OR use WhatsApp Template Messages (requires Meta approval)

**Instagram ToS**:
- ⚠️ Scraping is AGAINST Instagram Terms of Service
- ⚠️ Account ban risk
- ✅ Safer: Use Meta Graph API (official)
- ✅ Or: Organic DM outreach (no scraping)

---

## 🎨 WHITE-LABEL CUSTOMIZATION

### Branding Configuration
```yaml
# Environment Variables (docker-compose.yml)
BRAND_NAME: "YourCompany CRM"
BRAND_URL: "https://yourcompany.com"
WIDGET_BRAND_URL: ""  # Removes "Powered by Chatwoot"
LOGO_THUMBNAIL: "https://yourcompany.com/logo-small.png"
LOGO: "https://yourcompany.com/logo-large.png"

# Color Scheme (custom CSS)
PRIMARY_COLOR: "#1f93ff"
SECONDARY_COLOR: "#your-color"
```

### Per-Client Deployment
```bash
# Client 1: Recruitment Agency
docker-compose -f docker-compose.client1.yml up -d
# ENV: BRAND_NAME="TalentMatch", LOGO="talentmatch-logo.png"

# Client 2: E-commerce
docker-compose -f docker-compose.client2.yml up -d
# ENV: BRAND_NAME="ShopSupport", LOGO="shop-logo.png"

# Each client gets:
# - Separate Docker containers
# - Own database (PostgreSQL)
# - Own Chatwoot instance
# - Custom branding
# - Own domain (client1.yourcompany.com)
```

---

## 💰 COST ANALYSIS

### Infrastructure Costs (Per Client)
```
┌────────────────────────────────────────┐
│  MONTHLY COSTS                         │
├────────────────────────────────────────┤
│  Railway (Chatwoot + FastAPI)   €20   │
│  Supabase (Free tier)            €0    │
│  360Dialog WhatsApp API          €50   │
│  Claude API (conversations)      €30   │
│  GPT-4o-mini (routing)           €5    │
│  OpenAI Embeddings (RAG)         €10   │
├────────────────────────────────────────┤
│  TOTAL PER CLIENT:              €115   │
└────────────────────────────────────────┘

PRICING RECOMMENDATION: €500-800/month
MARGIN: €385-685/month (77-85%)

COMPARISON TO v5.0:
v5.0 (Dual UI): $618-743/month
v5.1 (Chatwoot): €115/month
SAVINGS: €503-628/month (81-85% reduction!)
```

---

## 📅 IMPLEMENTATION ROADMAP (8 WEEKS)

### Week 1-2: Foundation
- Deploy Chatwoot on Railway
- Setup Supabase PGVector
- WhatsApp MCP integration
- FastAPI webhook receiver
- Basic echo bot

### Week 3-4: LangGraph + 4 Agents
- StateGraph implementation
- Router, Extraction, Conversation, CRM agents
- End-to-end message flow
- CRM updates working

### Week 5: Agentic RAG
- Knowledge base upload
- Vector search implementation
- Tool calling in Claude agent
- Agent autonomously searches

### Week 6: CRM + Human Takeover
- Custom attributes configured
- AI summaries working
- Human takeover workflow
- Multi-channel messaging

### Week 7: Production WhatsApp + Scraping
- 360Dialog integration
- ScrapeCreators CSV import
- Rate limiting
- GDPR compliance

### Week 8: White-Label + Testing
- Branding customization
- End-to-end testing
- Performance testing
- Production deployment

**DEPLOYMENT TARGET**: Week 8, Day 5 (Friday)

---

## ✅ SUCCESS CRITERIA

### Technical
- ✅ All 4 agents working correctly
- ✅ Agentic RAG autonomously searches when needed
- ✅ CRM updates persist in Chatwoot
- ✅ Multi-channel messaging works (WhatsApp + Instagram + Email)
- ✅ Human takeover triggers correctly

### Business
- ✅ 3 use cases tested end-to-end
- ✅ White-label branding applied
- ✅ Response time < 3 seconds
- ✅ 99% uptime (Railway)
- ✅ Cost per client = €115/month

### User Experience
- ✅ AI summaries accurate
- ✅ Human can take over smoothly
- ✅ Contact profiles show all data
- ✅ One-button messaging works
- ✅ No context lost between channels

---

## 🔮 FUTURE EXTENSIBILITY

### Phase 2 (Month 3-6): Optional Enhancements
**Next.js Analytics Dashboard** (if Chatwoot CRM insufficient):
- Sales pipeline visualization
- Conversion rate analytics
- Agent performance metrics
- Custom reports

**Additional Features**:
- Telegram integration
- Facebook Messenger
- Custom reports API
- Webhook integrations (Zapier, Make)

### Architecture for Future Dashboard
```
Chatwoot (primary UI)
    ↓
PostgreSQL DB ← Next.js Dashboard (read-only analytics)
    ↓
LangGraph Agents
```

**Key**: Dashboard can be added LATER without breaking changes!

---

## 📄 APPENDIX: TECHNOLOGY JUSTIFICATIONS

### Why Chatwoot-Only (No Next.js Now)?
1. Chatwoot CRM covers user's 3 use cases
2. Faster implementation (8 weeks vs 14)
3. Lower cost (€115/month vs $618-743)
4. Can add Next.js later if needed

### Why 4 Agents (Not 7)?
Removed from v5.0:
- Email Marketing Agent (user doesn't need)
- Form Processing Agent (clients have own forms)
- Research Agent (not in use cases)

### Why LangGraph (Not Simple Sequential)?
- Conditional routing (if high priority → human)
- Error handling and retries
- State management across agents
- Tool calling loop (Agentic RAG)
- Future extensibility

### Why Agentic RAG (Not Normal RAG)?
- Agent decides when to search (not always)
- Reduces unnecessary API calls
- More natural conversation flow
- User: "Hello!" → No search (faster response)

### Why White-Label (Not Multi-Tenant)?
- User wants per-client customization
- Simpler architecture (no RLS needed)
- Easier branding customization
- No shared database security risks

---

**END OF PRD v5.1**

*Generated: 2025-01-15*
*Status: APPROVED - Ready for SDK AGENTS TECH ADVISOR recommendations*
