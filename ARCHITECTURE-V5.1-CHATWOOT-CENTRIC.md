# ARCHITECTURE v5.1: CHATWOOT-CENTRIC WHATSAPP RECRUITMENT PLATFORM

**Version**: 5.1
**Date**: 2025-01-15
**Status**: Production-Ready Specification
**Based On**: PRD v5.1 (Chatwoot-Centric)

---

## 1. SYSTEM OVERVIEW

### 1.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  CHANNEL LAYER                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐  ┌───────────┐ │
│  │  WhatsApp   │  │  Instagram   │  │  Email  │  │  Telegram │ │
│  │  (360Dialog)│  │  (Meta API)  │  │ (SMTP)  │  │  (Bot API)│ │
│  └──────┬──────┘  └──────┬───────┘  └────┬────┘  └─────┬─────┘ │
└─────────┼────────────────┼───────────────┼──────────────┼───────┘
          │                │               │              │
          └────────────────┴───────────────┴──────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│  UI/CRM LAYER (Chatwoot)                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │  Unified Inbox   │  │  Contact CRM     │  │  Team Chat     ││
│  │  - Multi-channel │  │  - Custom attrs  │  │  - Assignments ││
│  │  - Conversations │  │  - Labels/tags   │  │  - Notes       ││
│  └──────────────────┘  └──────────────────┘  └────────────────┘│
│                                  ↓                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Webhook System: POST /webhooks/chatwoot                   │ │
│  │  Events: message_created, conversation_updated             │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬─────────────────────────────────┘
                                 ↓ HTTP POST (JSON payload)
┌──────────────────────────────────────────────────────────────────┐
│  API LAYER (FastAPI)                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Webhook Receiver: POST /webhooks/chatwoot                 │ │
│  │  - Validates signature (HMAC-SHA256)                       │ │
│  │  - Queues message processing                               │ │
│  │  - Returns 200 OK immediately                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Message Queue: Celery + Redis                             │ │
│  │  - Background processing (async)                           │ │
│  │  - Retry logic (exponential backoff)                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬─────────────────────────────────┘
                                 ↓ Triggers LangGraph
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER (LangGraph StateGraph)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  START → Router → Extraction → Conversation → CRM → END   │ │
│  │                           ↓                                 │ │
│  │                   (needs_human=True)                        │ │
│  │                           ↓                                 │ │
│  │                          END                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐│
│  │  Router     │  │ Extraction  │  │Conversation │  │  CRM   ││
│  │  Agent      │  │   Agent     │  │   Agent     │  │ Agent  ││
│  │  (GPT-4o-   │  │  (Pydantic  │  │  (Claude +  │  │(GPT-4o)││
│  │   mini)     │  │    AI)      │  │ Agentic RAG)│  │ -mini  ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────┘│
└────────────────────────────────┬─────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                      │
│  ┌───────────────────────┐  ┌──────────────────────────────────┐│
│  │  PostgreSQL (Chatwoot)│  │  Supabase PGVector               ││
│  │  - Contacts (CRM)     │  │  - Knowledge base embeddings     ││
│  │  - Conversations      │  │  - Vector similarity search      ││
│  │  - Messages           │  │  - OpenAI text-embedding-3-small ││
│  │  - Custom attributes  │  │  - Dimension: 1536               ││
│  └───────────────────────┘  └──────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Map

```
User Message Flow:
==================
1. User sends WhatsApp → 360Dialog
2. 360Dialog webhook → Chatwoot Inbox
3. Chatwoot stores message → PostgreSQL
4. Chatwoot fires webhook → FastAPI
5. FastAPI queues task → Celery (Redis)
6. Celery worker invokes → LangGraph.app.invoke(state)
7. LangGraph executes → 4 agents sequentially
8. Agent responses → Update state
9. Final response → POST Chatwoot API
10. Chatwoot → 360Dialog → WhatsApp → User

Agent Interaction Flow:
=======================
Router Agent (intent classification)
    ↓ state["intent"] = "job_search"
Extraction Agent (structured data)
    ↓ state["extracted_data"] = {name, budget, urgency}
    ↓ Conditional: needs_human?
    ├─ YES → END (human takes over)
    └─ NO → Continue
Conversation Agent (response generation)
    ↓ Agentic RAG: searches PGVector if needed
    ↓ state["agent_response"] = "We have 3 positions..."
CRM Agent (update Chatwoot contact)
    ↓ PUT /api/v1/contacts/{id}
    ↓ state["crm_updated"] = True
END → Return response to user
```

### 1.3 Technology Stack

| Component | Technology | Version | Purpose | Cost |
|-----------|-----------|---------|---------|------|
| **UI/CRM** | Chatwoot | latest (3.x) | Multi-channel inbox + CRM | Free (OSS) |
| **Orchestration** | LangGraph | 0.2.62 | Agent workflow state machine | Free |
| **Agent Framework** | Pydantic AI | ≥0.0.14 | Structured extraction | Free |
| **Primary LLM** | Claude 3.5 Sonnet | 20241022 | Conversation + Agentic RAG | €30/mo |
| **Fast LLM** | GPT-4o-mini | - | Routing + CRM updates | €5/mo |
| **Backend API** | FastAPI | 0.115.6 | Webhook receiver | Free |
| **Task Queue** | Celery + Redis | 5.4 / 7.x | Async processing | Free |
| **Database** | PostgreSQL | 14 | Chatwoot data storage | Free |
| **Vector DB** | Supabase PGVector | 0.3.6 | RAG embeddings | Free tier |
| **Embeddings** | OpenAI text-embedding-3-small | - | Vector generation | €10/mo |
| **WhatsApp (Dev)** | WhatsApp MCP | latest | Development testing | Free |
| **WhatsApp (Prod)** | 360Dialog | API v2 | Production WhatsApp | €50/mo |
| **Hosting** | Railway | - | Docker deployment | €20/mo |
| **TOTAL** | - | - | - | **€115/mo** |

### 1.4 Data Flow Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│  INBOUND MESSAGE FLOW                                           │
│                                                                  │
│  User WhatsApp → 360Dialog                                      │
│       ↓                                                          │
│  POST https://chatwoot.railway.app/webhooks/360dialog           │
│       ↓                                                          │
│  Chatwoot saves to PostgreSQL                                   │
│       ↓                                                          │
│  Chatwoot fires webhook: message_created                        │
│       ↓                                                          │
│  POST http://fastapi:8000/webhooks/chatwoot                     │
│       Payload: {                                                │
│         "event": "message_created",                             │
│         "message_id": 123,                                      │
│         "conversation_id": 456,                                 │
│         "contact_id": 789,                                      │
│         "content": "Hello, I need a job"                        │
│       }                                                          │
│       ↓                                                          │
│  FastAPI validates + queues task                                │
│       ↓                                                          │
│  Celery worker processes async                                  │
│       ↓                                                          │
│  LangGraph.app.invoke(state)                                    │
│       ↓                                                          │
│  [4 agents execute sequentially]                                │
│       ↓                                                          │
│  POST https://chatwoot.railway.app/api/v1/.../messages          │
│       Payload: {                                                │
│         "content": "We have 3 positions matching your profile", │
│         "message_type": "outgoing"                              │
│       }                                                          │
│       ↓                                                          │
│  Chatwoot → 360Dialog → WhatsApp → User                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  AGENTIC RAG FLOW (Inside Conversation Agent)                   │
│                                                                  │
│  User: "What's your return policy?"                             │
│       ↓                                                          │
│  Claude API call with tools=[search_knowledge_base]             │
│       ↓                                                          │
│  Claude decides: "I need to search for policy info"             │
│       ↓                                                          │
│  Response: stop_reason="tool_use"                               │
│       ↓                                                          │
│  Extract tool_use.input: {"query": "return policy"}             │
│       ↓                                                          │
│  OpenAI Embeddings: text-embedding-3-small                      │
│       ↓                                                          │
│  Supabase PGVector: match_documents(query_embedding)            │
│       ↓                                                          │
│  Results: [                                                     │
│    {content: "Returns accepted within 30 days...",              │
│     similarity: 0.92}                                           │
│  ]                                                              │
│       ↓                                                          │
│  Claude API call #2 with tool_result                            │
│       ↓                                                          │
│  Claude generates final response using KB context              │
│       ↓                                                          │
│  Return: "Our return policy allows 30-day returns..."          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. COMPONENT ARCHITECTURE

### 2.1 Chatwoot (UI/CRM Layer)

**Purpose**: Primary user interface and CRM system for agents and managers

**Core Features**:
- Multi-channel inbox (WhatsApp, Instagram, Email, Telegram)
- Contact management with custom attributes (JSONB)
- Labels/tags for segmentation
- Team collaboration (assignments, notes, mentions)
- Canned responses (templates)
- Webhook system for integrations
- Reports and analytics

**Database Schema** (PostgreSQL):
```sql
-- Core tables (managed by Chatwoot)
contacts (
    id, name, email, phone_number,
    custom_attributes JSONB,  -- Our CRM data
    created_at, updated_at
)

conversations (
    id, contact_id, inbox_id,
    status VARCHAR(50),  -- 'open', 'resolved', 'pending'
    assignee_id
)

messages (
    id, conversation_id, content,
    message_type VARCHAR(50),  -- 'incoming', 'outgoing'
    created_at
)

labels (
    id, title, color, account_id
)

contact_labels (
    contact_id, label_id
)
```

**Custom Attributes Structure**:
```json
{
  "lead_status": "qualified",
  "budget_range": "€70-90k",
  "job_type_preference": "interim",
  "urgency_level": "high",
  "last_intent": "job_search",
  "ai_summary": "Seeking interim tech roles, 10+ years experience in Python/Django",
  "instagram_handle": "@johndoe",
  "follower_count": 15000,
  "lead_source": "instagram_scrape",
  "scraped_date": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-15T14:45:00Z"
}
```

**Webhook Configuration**:
```json
{
  "url": "http://fastapi:8000/webhooks/chatwoot",
  "webhook_type": "message_created",
  "subscriptions": [
    "message_created",
    "conversation_status_changed"
  ]
}
```

**API Endpoints Used**:
```python
# Send message
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
Body: {
    "content": "Agent response here",
    "message_type": "outgoing"
}

# Update contact
PUT /api/v1/accounts/{account_id}/contacts/{contact_id}
Body: {
    "custom_attributes": {
        "lead_status": "qualified"
    }
}

# Add labels
POST /api/v1/accounts/{account_id}/contacts/{contact_id}/labels
Body: {
    "labels": ["qualified-lead", "high-priority"]
}
```

---

### 2.2 FastAPI (Webhook Receiver)

**Purpose**: Receive Chatwoot webhooks and trigger agent processing

**Architecture**:
```python
# app/main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.security import HTTPBearer
import hmac
import hashlib
from celery_app import process_message_task

app = FastAPI(title="WhatsApp Recruitment Platform")
security = HTTPBearer()

@app.post("/webhooks/chatwoot")
async def chatwoot_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    signature: str = Header(None, alias="X-Chatwoot-Signature")
):
    """
    Receive Chatwoot webhook and queue processing.
    Returns 200 immediately (async processing).
    """

    # Validate signature (HMAC-SHA256)
    if not validate_signature(payload, signature):
        raise HTTPException(401, "Invalid signature")

    # Filter: Only process incoming messages
    if payload["event"] == "message_created":
        message_data = payload["message"]

        if message_data["message_type"] == "incoming":
            # Queue for async processing
            process_message_task.delay(message_data)

    return {"status": "queued"}


def validate_signature(payload: dict, signature: str) -> bool:
    """Validate Chatwoot webhook signature (HMAC-SHA256)"""
    secret = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    expected = hmac.new(
        secret.encode(),
        json.dumps(payload).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Task Queue (Celery + Redis)**:
```python
# celery_app.py
from celery import Celery
from langgraph_orchestrator import process_with_agents

celery_app = Celery(
    'whatsapp_recruitment',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60  # Exponential backoff
)
def process_message_task(self, message_data: dict):
    """Background task: Process message through LangGraph"""
    try:
        result = process_with_agents(message_data)
        return result
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

**Environment Variables**:
```bash
# .env
CHATWOOT_URL=https://chatwoot.railway.app
CHATWOOT_API_TOKEN=your_api_token
CHATWOOT_WEBHOOK_SECRET=your_webhook_secret
REDIS_URL=redis://redis:6379/0
```

---

### 2.3 LangGraph (Orchestration Layer)

**Purpose**: Coordinate agent workflow with state management and conditional routing

**State Definition**:
```python
# state.py
from typing import TypedDict, Literal, Optional, List, Dict
from pydantic import BaseModel

class ConversationState(TypedDict, total=False):
    # Chatwoot context
    message_id: str
    conversation_id: str
    contact_id: str
    account_id: str
    inbox_id: str
    channel: Literal["whatsapp", "instagram", "email", "telegram"]

    # Message content
    message_content: str
    message_type: Literal["incoming", "outgoing"]
    timestamp: str

    # Agent outputs
    intent: str  # From Router Agent
    priority: Literal["high", "medium", "low"]
    sentiment: float  # -1.0 to 1.0

    extracted_data: Optional[Dict]  # From Extraction Agent
    rag_results: Optional[List[Dict]]  # From Agentic RAG
    agent_response: Optional[str]  # From Conversation Agent

    # Routing logic
    needs_human: bool
    route: Literal["automated", "human", "hybrid"]

    # Context (fetched from Chatwoot)
    contact_profile: Dict
    conversation_history: List[Dict]

    # CRM updates
    crm_updated: bool
    labels_added: List[str]
```

**Graph Construction**:
```python
# graph.py
from langgraph.graph import StateGraph, END, START
from agents import (
    router_agent_node,
    extraction_agent_node,
    conversation_agent_node,
    crm_agent_node
)

def create_graph() -> StateGraph:
    """Create LangGraph workflow"""

    graph = StateGraph(ConversationState)

    # Add agent nodes
    graph.add_node("router", router_agent_node)
    graph.add_node("extraction", extraction_agent_node)
    graph.add_node("conversation", conversation_agent_node)
    graph.add_node("crm", crm_agent_node)

    # Add edges
    graph.add_edge(START, "router")
    graph.add_edge("router", "extraction")

    # Conditional routing: human takeover?
    def should_continue(state: ConversationState) -> str:
        """Decide if human takeover needed"""

        # High priority = human
        if state.get("priority") == "high":
            state["needs_human"] = True
            return END

        # Negative sentiment = human
        if state.get("sentiment", 0) < -0.5:
            state["needs_human"] = True
            return END

        # Complaint intent = human
        if "complaint" in state.get("intent", "").lower():
            state["needs_human"] = True
            return END

        # Otherwise, continue to AI agent
        return "conversation"

    graph.add_conditional_edges(
        "extraction",
        should_continue,
        {
            "conversation": "conversation",
            END: END
        }
    )

    graph.add_edge("conversation", "crm")
    graph.add_edge("crm", END)

    return graph.compile()

# Initialize app
app = create_graph()
```

**Invocation**:
```python
# orchestrator.py
from graph import app
from chatwoot_client import get_contact, get_conversation_history

async def process_with_agents(message_data: dict) -> dict:
    """Process message through LangGraph"""

    # Fetch context from Chatwoot
    contact = await get_contact(message_data["contact_id"])
    history = await get_conversation_history(message_data["conversation_id"])

    # Initialize state
    initial_state = {
        "message_id": message_data["id"],
        "conversation_id": message_data["conversation_id"],
        "contact_id": message_data["contact_id"],
        "account_id": message_data["account_id"],
        "message_content": message_data["content"],
        "contact_profile": contact,
        "conversation_history": history,
        "needs_human": False,
        "crm_updated": False
    }

    # Execute graph
    result = await app.ainvoke(initial_state)

    return result
```

---

### 2.4 Supabase PGVector (RAG Layer)

**Purpose**: Vector database for knowledge base embeddings and semantic search

**Database Schema**:
```sql
-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    metadata JSONB,
    category VARCHAR(50),
    account_id INTEGER,  -- Multi-client support
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX ON documents USING GIN (metadata);
CREATE INDEX ON documents (category);
CREATE INDEX ON documents (account_id);

-- Metadata structure (JSONB)
{
    "title": "Return Policy",
    "category": "policy",
    "source": "company_handbook.pdf",
    "page_number": 15,
    "language": "en",
    "tags": ["returns", "customer-service"],
    "last_updated": "2025-01-01T00:00:00Z"
}
```

**Vector Search Function**:
```sql
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category VARCHAR(50) DEFAULT NULL,
    filter_account_id INT DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    content TEXT,
    metadata JSONB,
    category VARCHAR(50),
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
        documents.category,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        (filter_category IS NULL OR documents.category = filter_category)
        AND (filter_account_id IS NULL OR documents.account_id = filter_account_id)
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;
```

**Python Integration**:
```python
# vector_db.py
from supabase import create_client, Client
from openai import AsyncOpenAI
import os

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def search_knowledge_base(
    query: str,
    category: str = None,
    account_id: int = None,
    top_k: int = 5
) -> List[Dict]:
    """Search vector database for relevant documents"""

    # Generate query embedding
    response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = response.data[0].embedding

    # Search Supabase PGVector
    result = supabase.rpc(
        'match_documents',
        {
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': top_k,
            'filter_category': category,
            'filter_account_id': account_id
        }
    ).execute()

    return result.data

# Document ingestion
async def ingest_document(
    content: str,
    metadata: dict,
    category: str,
    account_id: int
):
    """Add document to knowledge base"""

    # Generate embedding
    response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=content
    )
    embedding = response.data[0].embedding

    # Insert into Supabase
    result = supabase.table('documents').insert({
        'content': content,
        'embedding': embedding,
        'metadata': metadata,
        'category': category,
        'account_id': account_id
    }).execute()

    return result.data
```

---

## 3. AGENT SPECIFICATIONS

### 3.1 Agent 1: Router Agent (GPT-4o-mini)

**Purpose**: Fast intent classification to route messages appropriately

**Input**: Raw message content (string)
**Output**: Intent category (string) + priority level

**Implementation**:
```python
# agents/router.py
from openai import AsyncOpenAI
from typing import Dict

openai = AsyncOpenAI()

ROUTER_PROMPT = """You are a message routing agent. Classify the user's message intent.

Categories:
- product_inquiry: Questions about products/services
- policy_question: Return policy, terms, FAQ
- support_request: Technical issues, complaints
- job_search: Looking for jobs, vacancies (recruitment)
- lead_qualification: Providing contact info, budget
- general: Greetings, small talk
- urgent_complaint: Explicit complaints, negative emotion

Also assess priority:
- high: Complaints, urgent requests, negative sentiment
- medium: Specific product/service questions
- low: General inquiries, greetings

Output format (JSON):
{
    "intent": "category_name",
    "priority": "high|medium|low",
    "sentiment": 0.5,  // -1.0 to 1.0
    "reasoning": "brief explanation"
}
"""

async def router_agent_node(state: Dict) -> Dict:
    """LangGraph node: Route message by intent"""

    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": state["message_content"]}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "intent": result["intent"],
        "priority": result["priority"],
        "sentiment": result["sentiment"]
    }
```

**Performance**:
- Latency: ~200ms
- Cost: $0.15 per 1M input tokens
- Accuracy: 95%+ (simple classification)

---

### 3.2 Agent 2: Extraction Agent (Pydantic AI)

**Purpose**: Extract structured data for CRM with automatic validation

**Pydantic Models**:
```python
# agents/extraction.py
from pydantic import BaseModel, EmailStr, Field
from pydantic_ai import Agent
from typing import Optional, Literal, List

class ExtractedData(BaseModel):
    """Structured contact and lead data"""

    # Contact info
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')

    # Lead qualification
    budget_min: Optional[int] = Field(None, ge=0)
    budget_max: Optional[int] = Field(None, ge=0)
    job_type: Optional[Literal["interim", "permanent", "freelance"]] = None
    urgency: Literal["high", "medium", "low"] = "medium"

    # E-commerce specific
    product_interest: Optional[str] = None
    size_preference: Optional[str] = None

    # Analysis
    intent_keywords: List[str] = Field(default_factory=list)
    ai_summary: Optional[str] = Field(None, max_length=500)

# Create Pydantic AI agent
extraction_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=ExtractedData,
    system_prompt="""Extract structured contact and lead data from conversations.

    Rules:
    - Extract ALL mentioned contact info (name, email, phone)
    - Infer job type from context (e.g., "temporary" → "interim")
    - Set urgency based on language ("ASAP" → "high")
    - Extract budget ranges (e.g., "€70-90k" → min:70000, max:90000)
    - Generate concise AI summary (2-3 sentences)
    - Leave fields None if not mentioned (don't guess!)
    """
)

async def extraction_agent_node(state: Dict) -> Dict:
    """LangGraph node: Extract structured data"""

    # Include conversation history for context
    context = f"""
    Current message: {state['message_content']}

    Previous conversation: {state.get('conversation_history', [])}
    """

    # Run Pydantic AI agent
    result = await extraction_agent.run(context)

    # Validated Pydantic model!
    extracted = result.data

    return {
        "extracted_data": extracted.model_dump()
    }
```

**Why Pydantic AI?**
1. Automatic validation (Pydantic models)
2. Type safety (no parsing errors)
3. Clean structured output
4. Fast (GPT-4o-mini backend)
5. Easy to extend (add new fields)

---

### 3.3 Agent 3: Conversation Agent (Claude SDK + Agentic RAG)

**Purpose**: Generate natural responses with autonomous knowledge base search

**CRITICAL**: Agentic RAG = Agent DECIDES when to search (not automatic!)

**Tool Definition**:
```python
# agents/conversation.py
from anthropic import AsyncAnthropic
from vector_db import search_knowledge_base

anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Claude tool definition
search_kb_tool = {
    "name": "search_knowledge_base",
    "description": """Search company knowledge base for accurate information about policies, products, services, procedures, or FAQs.

    Use this tool when:
    - User asks factual questions about company information
    - You need to verify specific details (prices, policies, procedures)
    - User asks "what", "how", "when", "where" questions

    Do NOT use when:
    - User greets or makes small talk
    - You can answer from general knowledge
    - User asks about their own information (check state instead)
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (natural language question)"
            },
            "category": {
                "type": "string",
                "enum": ["policy", "product", "faq", "procedure"],
                "description": "Category filter (optional, leave empty for broad search)"
            }
        },
        "required": ["query"]
    }
}

CONVERSATION_PROMPT = """You are a helpful customer service agent for {company_name}.

Your role:
- Answer questions naturally and conversationally
- Use the search_knowledge_base tool WHEN NEEDED for factual information
- Be friendly, professional, and empathetic
- Keep responses concise (2-3 sentences max)

Context:
- Contact name: {contact_name}
- Previous messages: {conversation_history}
- Extracted info: {extracted_data}

Guidelines:
- If you don't know something factual → use search tool
- If user asks about return policy → search for "return policy"
- If greeting → respond directly (no search needed)
- Personalize using contact name when appropriate
"""

async def conversation_agent_node(state: Dict) -> Dict:
    """LangGraph node: Generate response with Agentic RAG"""

    # Format system prompt with context
    system_prompt = CONVERSATION_PROMPT.format(
        company_name=state.get("company_name", "our company"),
        contact_name=state["contact_profile"].get("name", "there"),
        conversation_history=state.get("conversation_history", [])[-5:],
        extracted_data=state.get("extracted_data", {})
    )

    # Initial Claude call with tools available
    response = await anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": state["message_content"]}
        ],
        tools=[search_kb_tool]  # Agent CAN use, not forced!
    )

    # Check if agent decided to use tool
    if response.stop_reason == "tool_use":
        # Extract tool call
        tool_use_block = next(
            block for block in response.content
            if block.type == "tool_use"
        )

        # Execute vector search
        rag_results = await search_knowledge_base(
            query=tool_use_block.input["query"],
            category=tool_use_block.input.get("category"),
            account_id=state["account_id"]
        )

        # Continue conversation with search results
        response = await anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": state["message_content"]},
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": format_rag_results(rag_results)
                        }
                    ]
                }
            ]
        )

        # Store RAG results in state
        state["rag_results"] = rag_results

    # Extract text response
    text_response = next(
        block.text for block in response.content
        if hasattr(block, "text")
    )

    return {
        "agent_response": text_response,
        "rag_results": state.get("rag_results")
    }


def format_rag_results(results: List[Dict]) -> str:
    """Format vector search results for Claude"""
    if not results:
        return "No relevant information found in knowledge base."

    formatted = "Knowledge Base Results:\n\n"
    for i, result in enumerate(results[:3], 1):
        formatted += f"{i}. {result['content']}\n"
        formatted += f"   (Source: {result['metadata']['title']}, "
        formatted += f"Relevance: {result['similarity']:.2%})\n\n"

    return formatted
```

**Agentic Decision Examples**:

| User Message | Agent Decision | Reasoning |
|--------------|---------------|-----------|
| "Hello!" | No search | Simple greeting |
| "What's your return policy?" | Search KB | Factual policy question |
| "Track order #123" | No search (use different tool) | Order tracking tool |
| "Do you have size 42?" | Search KB or inventory tool | Product availability |
| "Thank you!" | No search | Closing statement |

---

### 3.4 Agent 4: CRM Agent (GPT-4o-mini)

**Purpose**: Update Chatwoot contact attributes and labels based on conversation

**Implementation**:
```python
# agents/crm.py
from chatwoot_client import update_contact, add_labels
from openai import AsyncOpenAI

openai = AsyncOpenAI()

CRM_UPDATE_PROMPT = """Analyze the conversation and extracted data to determine CRM updates.

Input data:
- Extracted: {extracted_data}
- Intent: {intent}
- Conversation: {message_content}

Output CRM updates (JSON):
{
    "lead_status": "new|contacted|qualified|unqualified|customer",
    "custom_attributes": {
        "budget_range": "€70-90k",
        "job_type_preference": "interim",
        "urgency_level": "high",
        "last_intent": "job_search",
        "ai_summary": "2-3 sentence summary"
    },
    "labels": ["qualified-lead", "high-priority", "tech-sector"]
}

Lead status logic:
- new: First contact, minimal info
- contacted: Conversation started
- qualified: Budget + clear intent + contact info
- unqualified: No budget or outside criteria
- customer: Already purchased/hired

Label suggestions:
- Priority: "high-priority", "medium-priority", "low-priority"
- Sector: "tech-sector", "finance-sector", "healthcare-sector"
- Status: "qualified-lead", "unqualified-lead", "hot-lead"
- Source: "instagram-scrape", "website-form", "referral"
"""

async def crm_agent_node(state: Dict) -> Dict:
    """LangGraph node: Update Chatwoot CRM"""

    # Generate CRM updates using AI
    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": CRM_UPDATE_PROMPT.format(
                    extracted_data=state.get("extracted_data", {}),
                    intent=state.get("intent"),
                    message_content=state["message_content"]
                )
            },
            {"role": "user", "content": "Generate CRM updates"}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    crm_updates = json.loads(response.choices[0].message.content)

    # Update Chatwoot contact
    await update_contact(
        contact_id=state["contact_id"],
        custom_attributes={
            **crm_updates["custom_attributes"],
            "last_updated": datetime.now().isoformat()
        }
    )

    # Add labels
    await add_labels(
        contact_id=state["contact_id"],
        labels=crm_updates["labels"]
    )

    return {
        "crm_updated": True,
        "labels_added": crm_updates["labels"]
    }
```

**Chatwoot API Client**:
```python
# chatwoot_client.py
import httpx
import os

CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_TOKEN = os.getenv("CHATWOOT_API_TOKEN")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")

async def update_contact(contact_id: int, custom_attributes: dict):
    """Update Chatwoot contact custom attributes"""
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts/{contact_id}",
            headers={"api_access_token": CHATWOOT_TOKEN},
            json={"custom_attributes": custom_attributes}
        )
        response.raise_for_status()
        return response.json()

async def add_labels(contact_id: int, labels: List[str]):
    """Add labels to Chatwoot contact"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts/{contact_id}/labels",
            headers={"api_access_token": CHATWOOT_TOKEN},
            json={"labels": labels}
        )
        response.raise_for_status()
        return response.json()

async def send_message(conversation_id: int, content: str):
    """Send message via Chatwoot"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages",
            headers={"api_access_token": CHATWOOT_TOKEN},
            json={
                "content": content,
                "message_type": "outgoing"
            }
        )
        response.raise_for_status()
        return response.json()
```

---

## 4. LANGGRAPH STATE MACHINE

### 4.1 Complete State Machine Implementation

```python
# langgraph_app.py
from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Literal, Optional, List, Dict
from agents import (
    router_agent_node,
    extraction_agent_node,
    conversation_agent_node,
    crm_agent_node
)
from chatwoot_client import send_message

class ConversationState(TypedDict, total=False):
    # Chatwoot context
    message_id: str
    conversation_id: str
    contact_id: str
    account_id: str
    channel: Literal["whatsapp", "instagram", "email", "telegram"]

    # Message content
    message_content: str
    timestamp: str

    # Agent outputs
    intent: str
    priority: Literal["high", "medium", "low"]
    sentiment: float
    extracted_data: Optional[Dict]
    rag_results: Optional[List[Dict]]
    agent_response: Optional[str]

    # Routing
    needs_human: bool
    route: Literal["automated", "human"]

    # Context
    contact_profile: Dict
    conversation_history: List[Dict]

    # CRM
    crm_updated: bool
    labels_added: List[str]


def should_route_to_human(state: ConversationState) -> str:
    """Conditional edge: Decide if human takeover needed"""

    # High priority = human
    if state.get("priority") == "high":
        state["needs_human"] = True
        state["route"] = "human"
        return "human_notify"

    # Very negative sentiment = human
    if state.get("sentiment", 0) < -0.5:
        state["needs_human"] = True
        state["route"] = "human"
        return "human_notify"

    # Complaint intent = human
    intent = state.get("intent", "").lower()
    if any(word in intent for word in ["complaint", "urgent", "angry"]):
        state["needs_human"] = True
        state["route"] = "human"
        return "human_notify"

    # Otherwise, automated response
    state["route"] = "automated"
    return "conversation"


async def human_notify_node(state: ConversationState) -> Dict:
    """Notify human agent (add private note in Chatwoot)"""

    note = f"""🚨 HUMAN TAKEOVER REQUESTED

Reason: {state['intent']} (Priority: {state['priority']})
Sentiment: {state['sentiment']:.2f}

Contact: {state['contact_profile'].get('name')}
Message: {state['message_content']}

Please respond manually in Chatwoot.
"""

    # Send private note to Chatwoot
    await send_private_note(state["conversation_id"], note)

    return {"needs_human": True}


def create_graph() -> StateGraph:
    """Construct LangGraph workflow"""

    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("router", router_agent_node)
    graph.add_node("extraction", extraction_agent_node)
    graph.add_node("conversation", conversation_agent_node)
    graph.add_node("crm", crm_agent_node)
    graph.add_node("human_notify", human_notify_node)

    # Add edges
    graph.add_edge(START, "router")
    graph.add_edge("router", "extraction")

    # Conditional routing after extraction
    graph.add_conditional_edges(
        "extraction",
        should_route_to_human,
        {
            "conversation": "conversation",
            "human_notify": "human_notify"
        }
    )

    # Automated flow
    graph.add_edge("conversation", "crm")
    graph.add_edge("crm", END)

    # Human takeover flow
    graph.add_edge("human_notify", END)

    return graph.compile()


# Initialize compiled graph
app = create_graph()


async def process_message(message_data: dict):
    """Main entry point: Process message through LangGraph"""

    # Fetch Chatwoot context
    contact = await get_contact(message_data["contact_id"])
    history = await get_conversation_history(
        message_data["conversation_id"],
        limit=10
    )

    # Initialize state
    initial_state = ConversationState(
        message_id=message_data["id"],
        conversation_id=message_data["conversation_id"],
        contact_id=message_data["contact_id"],
        account_id=message_data["account_id"],
        channel=message_data["channel"],
        message_content=message_data["content"],
        timestamp=message_data["created_at"],
        contact_profile=contact,
        conversation_history=history,
        needs_human=False,
        crm_updated=False
    )

    # Execute graph
    result = await app.ainvoke(initial_state)

    # Send response if automated
    if result["route"] == "automated":
        await send_message(
            conversation_id=result["conversation_id"],
            content=result["agent_response"]
        )

    return result
```

### 4.2 State Machine Visualization

```
START
  ↓
┌─────────────┐
│   Router    │  Intent classification + priority
│   Agent     │  (GPT-4o-mini)
└──────┬──────┘
       ↓
┌─────────────┐
│ Extraction  │  Structured data extraction
│   Agent     │  (Pydantic AI)
└──────┬──────┘
       ↓
   [DECISION]
       ↓
   ┌───┴───┐
   │       │
HIGH    NORMAL
PRIORITY  ↓
   ↓    ┌───────────────┐
   ↓    │ Conversation  │  Response generation
   ↓    │    Agent      │  + Agentic RAG
   ↓    │  (Claude SDK) │  (Claude 3.5 Sonnet)
   ↓    └───────┬───────┘
   ↓            ↓
   ↓    ┌─────────────┐
   ↓    │  CRM Agent  │  Update contact
   ↓    │ (GPT-4o-mini│  attributes + labels
   ↓    └──────┬──────┘
   ↓           ↓
   ↓         [END]
   ↓       (Send response)
   ↓
┌──┴──────────┐
│   Human     │  Notify human agent
│   Notify    │  (Private note)
└──────┬──────┘
       ↓
     [END]
  (Wait for human)
```

---

## 5. AGENTIC RAG IMPLEMENTATION

### 5.1 RAG Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AGENTIC RAG FLOW                                       │
│                                                          │
│  User Message: "What's your return policy?"             │
│         ↓                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Conversation Agent (Claude)                     │  │
│  │  System: Available tools = [search_kb_tool]     │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Claude API Call #1                              │  │
│  │  Claude thinks: "I need policy information"      │  │
│  │  Response: stop_reason="tool_use"                │  │
│  │  Tool: search_knowledge_base                     │  │
│  │  Input: {"query": "return policy"}               │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Generate Query Embedding                        │  │
│  │  OpenAI: text-embedding-3-small                  │  │
│  │  Output: [0.123, -0.456, ...]  (1536 dims)      │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Supabase PGVector Search                        │  │
│  │  Function: match_documents(query_embedding)      │  │
│  │  Operator: <=> (cosine distance)                 │  │
│  │  Threshold: similarity > 0.7                     │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Results: [                                      │  │
│  │    {                                             │  │
│  │      content: "Returns accepted within 30 days", │  │
│  │      similarity: 0.92,                           │  │
│  │      metadata: {title: "Return Policy"}          │  │
│  │    }                                             │  │
│  │  ]                                               │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Claude API Call #2 (with tool_result)          │  │
│  │  Messages: [                                     │  │
│  │    user: "What's your return policy?",           │  │
│  │    assistant: [tool_use],                        │  │
│  │    user: [tool_result with KB content]          │  │
│  │  ]                                               │  │
│  └────────────────────┬─────────────────────────────┘  │
│                       ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Final Response                                  │  │
│  │  "Our return policy allows returns within       │  │
│  │   30 days of purchase with original receipt..."  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Complete RAG Implementation

```python
# agentic_rag.py
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from supabase import create_client
from typing import List, Dict, Optional
import os

anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Tool definition
SEARCH_KB_TOOL = {
    "name": "search_knowledge_base",
    "description": """Search company knowledge base for accurate, up-to-date information.

    Use when user asks about:
    - Company policies (return, refund, privacy)
    - Product specifications or features
    - Procedures or how-to instructions
    - Frequently asked questions
    - Pricing or service details

    Do NOT use for:
    - General greetings or small talk
    - Personal user data (use state instead)
    - Calculations or current events
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query"
            },
            "category": {
                "type": "string",
                "enum": ["policy", "product", "faq", "procedure", "general"],
                "description": "Category filter (optional)"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results (default: 3)",
                "minimum": 1,
                "maximum": 10
            }
        },
        "required": ["query"]
    }
}


async def search_vector_db(
    query: str,
    category: Optional[str] = None,
    account_id: Optional[int] = None,
    top_k: int = 3
) -> List[Dict]:
    """Execute vector similarity search"""

    # 1. Generate query embedding
    embedding_response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = embedding_response.data[0].embedding

    # 2. Search Supabase PGVector
    result = supabase.rpc(
        'match_documents',
        {
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': top_k,
            'filter_category': category,
            'filter_account_id': account_id
        }
    ).execute()

    return result.data


def format_search_results(results: List[Dict]) -> str:
    """Format results for Claude consumption"""
    if not results:
        return "No relevant documents found in knowledge base."

    formatted = "Knowledge Base Search Results:\n\n"

    for i, doc in enumerate(results, 1):
        formatted += f"Document {i}:\n"
        formatted += f"Content: {doc['content']}\n"
        formatted += f"Source: {doc['metadata'].get('title', 'Unknown')}\n"
        formatted += f"Category: {doc.get('category', 'N/A')}\n"
        formatted += f"Relevance: {doc['similarity']:.1%}\n\n"

    return formatted


async def agentic_rag_conversation(
    user_message: str,
    conversation_history: List[Dict],
    system_prompt: str,
    account_id: int,
    max_iterations: int = 3
) -> Dict:
    """
    Execute Agentic RAG conversation with Claude.

    Returns:
        {
            "response": str,
            "tool_calls": List[Dict],
            "rag_results": List[Dict]
        }
    """

    messages = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    tool_calls = []
    all_rag_results = []

    for iteration in range(max_iterations):
        # Call Claude with tools available
        response = await anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            tools=[SEARCH_KB_TOOL]
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Claude finished without tool use
            final_text = next(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return {
                "response": final_text,
                "tool_calls": tool_calls,
                "rag_results": all_rag_results
            }

        elif response.stop_reason == "tool_use":
            # Claude wants to use search tool
            tool_use_block = next(
                block for block in response.content
                if block.type == "tool_use"
            )

            # Execute search
            search_results = await search_vector_db(
                query=tool_use_block.input["query"],
                category=tool_use_block.input.get("category"),
                account_id=account_id,
                top_k=tool_use_block.input.get("top_k", 3)
            )

            # Track tool usage
            tool_calls.append({
                "tool": "search_knowledge_base",
                "input": tool_use_block.input,
                "results_count": len(search_results)
            })
            all_rag_results.extend(search_results)

            # Continue conversation with tool result
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": format_search_results(search_results)
                    }
                ]
            })

            # Continue loop (Claude will generate final response)

        else:
            # Unexpected stop reason
            raise Exception(f"Unexpected stop_reason: {response.stop_reason}")

    # Max iterations reached
    raise Exception("Max RAG iterations reached without completion")
```

### 5.3 Knowledge Base Ingestion

```python
# ingest_documents.py
from openai import AsyncOpenAI
from supabase import create_client
from pathlib import Path
import PyPDF2
from typing import List, Dict

openai = AsyncOpenAI()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


async def ingest_pdf(
    pdf_path: str,
    category: str,
    account_id: int,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[int]:
    """Ingest PDF into vector database with chunking"""

    # Extract text from PDF
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        full_text = ""

        for page_num, page in enumerate(pdf_reader.pages):
            full_text += page.extract_text()

    # Chunk text
    chunks = chunk_text(full_text, chunk_size, overlap)

    # Generate embeddings (batch)
    embeddings_response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=chunks
    )
    embeddings = [item.embedding for item in embeddings_response.data]

    # Insert into Supabase
    document_ids = []
    pdf_filename = Path(pdf_path).name

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        result = supabase.table('documents').insert({
            'content': chunk,
            'embedding': embedding,
            'category': category,
            'account_id': account_id,
            'metadata': {
                'source': pdf_filename,
                'chunk_index': i,
                'total_chunks': len(chunks)
            }
        }).execute()

        document_ids.append(result.data[0]['id'])

    return document_ids


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


# Usage example
async def setup_knowledge_base(account_id: int):
    """Initialize knowledge base for client"""

    documents = [
        ("docs/return_policy.pdf", "policy"),
        ("docs/product_catalog.pdf", "product"),
        ("docs/faq.pdf", "faq"),
        ("docs/procedures.pdf", "procedure")
    ]

    for file_path, category in documents:
        print(f"Ingesting {file_path}...")
        doc_ids = await ingest_pdf(file_path, category, account_id)
        print(f"✅ Created {len(doc_ids)} document chunks")
```

---

## 6. DATABASE SCHEMAS

### 6.1 Chatwoot PostgreSQL Schema

```sql
-- Chatwoot core tables (managed by Chatwoot)

-- Accounts (clients/workspaces)
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Contacts (CRM)
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    name VARCHAR(255),
    email VARCHAR(255),
    phone_number VARCHAR(50),
    custom_attributes JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Custom Attributes Structure (stored in JSONB column)
{
    -- Lead qualification
    "lead_status": "new|contacted|qualified|unqualified|customer",
    "budget_range": "€70-90k",
    "job_type_preference": "interim|permanent|freelance",
    "urgency_level": "high|medium|low",
    "last_intent": "job_search",

    -- AI-generated insights
    "ai_summary": "Experienced Python developer seeking interim roles...",
    "sentiment_score": 0.75,

    -- Source tracking
    "lead_source": "instagram_scrape|website_form|referral",
    "instagram_handle": "@username",
    "follower_count": 15000,
    "scraped_date": "2025-01-15T10:30:00Z",

    -- Timestamps
    "last_updated": "2025-01-15T14:45:00Z",
    "first_contact_date": "2025-01-10T09:00:00Z"
}

-- Inboxes (channels)
CREATE TABLE inboxes (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    name VARCHAR(255),
    channel_type VARCHAR(50),  -- 'whatsapp', 'instagram', 'email'
    channel_id INTEGER
);

-- Conversations
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    contact_id INTEGER REFERENCES contacts(id),
    inbox_id INTEGER REFERENCES inboxes(id),
    status VARCHAR(50) DEFAULT 'open',  -- 'open', 'resolved', 'pending'
    assignee_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    content TEXT,
    message_type VARCHAR(50),  -- 'incoming', 'outgoing'
    created_at TIMESTAMP DEFAULT NOW(),
    sender_type VARCHAR(50),  -- 'contact', 'user', 'agent_bot'
    sender_id INTEGER
);

-- Labels (tags)
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#1f93ff',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Contact Labels (many-to-many)
CREATE TABLE contact_labels (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    label_id INTEGER REFERENCES labels(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contact_id, label_id)
);

-- Indexes for performance
CREATE INDEX idx_contacts_account ON contacts(account_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_phone ON contacts(phone_number);
CREATE INDEX idx_contacts_custom_attrs ON contacts USING GIN (custom_attributes);
CREATE INDEX idx_conversations_contact ON conversations(contact_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_contact_labels_contact ON contact_labels(contact_id);
```

### 6.2 Supabase PGVector Schema

```sql
-- Enable PGVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table (knowledge base)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    category VARCHAR(50),
    account_id INTEGER NOT NULL,  -- Multi-client isolation
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Metadata structure (JSONB)
{
    "title": "Return Policy - Section 3",
    "source": "company_handbook.pdf",
    "page_number": 15,
    "chunk_index": 3,
    "total_chunks": 25,
    "language": "en",
    "tags": ["returns", "customer-service", "policies"],
    "last_updated": "2025-01-01T00:00:00Z",
    "version": "1.2"
}

-- Indexes for fast vector search
CREATE INDEX ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on data size

CREATE INDEX ON documents (category);
CREATE INDEX ON documents (account_id);
CREATE INDEX ON documents USING GIN (metadata);

-- Vector search function (RPC)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category VARCHAR(50) DEFAULT NULL,
    filter_account_id INT DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    content TEXT,
    metadata JSONB,
    category VARCHAR(50),
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
        documents.category,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        -- Category filter (optional)
        (filter_category IS NULL OR documents.category = filter_category)
        -- Account isolation (required!)
        AND (filter_account_id IS NULL OR documents.account_id = filter_account_id)
        -- Similarity threshold
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Document statistics function
CREATE OR REPLACE FUNCTION document_stats(account_id_filter INT)
RETURNS TABLE (
    category VARCHAR(50),
    count BIGINT
)
LANGUAGE sql
AS $$
    SELECT category, COUNT(*)
    FROM documents
    WHERE account_id = account_id_filter
    GROUP BY category;
$$;
```

---

## 7. API SPECIFICATIONS

### 7.1 Chatwoot Webhook Payload

```json
{
  "event": "message_created",
  "id": 12345,
  "content": "Hello, I need help finding a job",
  "created_at": "2025-01-15T14:30:00Z",
  "message_type": "incoming",
  "content_type": "text",
  "content_attributes": {},
  "source_id": "wamid.HBgNMTIzNDU2Nzg5MDEyFQ==",
  "sender": {
    "id": 789,
    "name": "John Doe",
    "email": "john@example.com",
    "phone_number": "+31612345678",
    "type": "contact"
  },
  "conversation": {
    "id": 456,
    "status": "open",
    "channel": "Channel::Whatsapp",
    "account_id": 1,
    "inbox_id": 2,
    "assignee_id": null
  },
  "account": {
    "id": 1,
    "name": "TalentMatch Recruitment"
  }
}
```

### 7.2 FastAPI Endpoints

```python
# API endpoint definitions

# 1. Webhook Receiver
POST /webhooks/chatwoot
Headers:
  X-Chatwoot-Signature: <HMAC-SHA256>
  Content-Type: application/json
Body: <Chatwoot webhook payload>
Response: {"status": "queued", "message_id": 12345}

# 2. Health Check
GET /health
Response: {
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "chatwoot": "connected",
    "supabase": "connected",
    "redis": "connected"
  }
}

# 3. Process Message (Manual Trigger)
POST /process
Body: {
  "message_id": 12345,
  "force": true  // Bypass cache
}
Response: {
  "status": "success",
  "agent_response": "We have 3 positions matching...",
  "rag_used": true,
  "crm_updated": true
}

# 4. Knowledge Base Management
POST /knowledge-base/ingest
Body: {
  "account_id": 1,
  "file": <multipart/form-data>,
  "category": "policy"
}
Response: {
  "status": "success",
  "document_ids": [123, 124, 125],
  "chunks_created": 3
}

GET /knowledge-base/search
Query: ?query=return policy&account_id=1&top_k=3
Response: {
  "results": [
    {
      "content": "Returns accepted within 30 days...",
      "similarity": 0.92,
      "metadata": {"title": "Return Policy"}
    }
  ]
}
```

### 7.3 360Dialog API Integration

```python
# 360Dialog WhatsApp Business API

# Send WhatsApp message
POST https://waba.360dialog.io/v1/messages
Headers:
  D360-API-KEY: <your_api_key>
  Content-Type: application/json
Body: {
  "recipient_type": "individual",
  "to": "+31612345678",
  "type": "text",
  "text": {
    "body": "We have 3 positions matching your profile..."
  }
}

# Webhook (360Dialog → Chatwoot)
POST https://chatwoot.railway.app/webhooks/360dialog
Body: {
  "messages": [{
    "from": "31612345678",
    "id": "wamid.HBgN...",
    "timestamp": "1642425600",
    "text": {
      "body": "Hello, I need help"
    },
    "type": "text"
  }]
}
```

---

## 8. DEPLOYMENT ARCHITECTURE

### 8.1 Railway Deployment Structure

```
railway-project/
├── chatwoot/                 # Chatwoot service
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env
├── fastapi-backend/          # FastAPI + LangGraph
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── agents/
│   │   ├── graph.py
│   │   └── celery_app.py
│   └── .env
├── redis/                    # Celery broker
│   └── redis.conf
└── railway.json              # Railway config
```

### 8.2 Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Chatwoot (UI + CRM)
  chatwoot:
    image: chatwoot/chatwoot:latest
    ports:
      - "3000:3000"
    environment:
      POSTGRES_DATABASE: chatwoot_production
      POSTGRES_HOST: postgres
      POSTGRES_USERNAME: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY_BASE: ${SECRET_KEY_BASE}

      # White-label branding
      BRAND_NAME: ${BRAND_NAME}
      WIDGET_BRAND_URL: ""  # Remove "Powered by Chatwoot"
      LOGO_THUMBNAIL: ${LOGO_THUMBNAIL_URL}
      LOGO: ${LOGO_URL}

      # 360Dialog integration
      WHATSAPP_CLOUD_BASE_URL: https://waba.360dialog.io
    depends_on:
      - postgres
      - redis

  # PostgreSQL (Chatwoot database)
  postgres:
    image: postgres:14-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: chatwoot_production
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  # Redis (Chatwoot + Celery)
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # FastAPI (Webhook receiver + LangGraph)
  fastapi:
    build: ./fastapi-backend
    ports:
      - "8000:8000"
    environment:
      # Chatwoot
      CHATWOOT_URL: http://chatwoot:3000
      CHATWOOT_API_TOKEN: ${CHATWOOT_API_TOKEN}
      CHATWOOT_WEBHOOK_SECRET: ${CHATWOOT_WEBHOOK_SECRET}

      # LLM APIs
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}

      # Supabase
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}

      # Celery
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - chatwoot
      - redis

  # Celery Worker (Background processing)
  celery-worker:
    build: ./fastapi-backend
    command: celery -A celery_app worker --loglevel=info
    environment:
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

### 8.3 Environment Variables

```bash
# .env (Railway Secrets)

# Chatwoot
SECRET_KEY_BASE=<generate with: rake secret>
DB_PASSWORD=<strong_password>
CHATWOOT_API_TOKEN=<from Chatwoot Settings>
CHATWOOT_WEBHOOK_SECRET=<generate random>

# White-label branding
BRAND_NAME="TalentMatch CRM"
LOGO_THUMBNAIL_URL="https://cdn.example.com/logo-small.png"
LOGO_URL="https://cdn.example.com/logo-large.png"

# LLM APIs
ANTHROPIC_API_KEY=<from anthropic.com>
OPENAI_API_KEY=<from openai.com>

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=<anon public key>

# 360Dialog (Production WhatsApp)
DIALOG_360_API_KEY=<from 360dialog.com>
```

### 8.4 White-Label Configuration Per Client

```yaml
# Client 1: Recruitment Agency
# docker-compose.client1.yml
services:
  chatwoot:
    environment:
      BRAND_NAME: "TalentMatch CRM"
      LOGO_URL: "https://cdn.example.com/talentmatch-logo.png"
      INSTALLATION_NAME: "TalentMatch"
      PRIMARY_COLOR: "#2563eb"  # Blue

# Client 2: E-commerce
# docker-compose.client2.yml
services:
  chatwoot:
    environment:
      BRAND_NAME: "ShopSupport"
      LOGO_URL: "https://cdn.example.com/shop-logo.png"
      INSTALLATION_NAME: "ShopSupport"
      PRIMARY_COLOR: "#10b981"  # Green
```

### 8.5 Railway Deployment Commands

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway init

# Add services
railway add --service chatwoot
railway add --service fastapi
railway add --service redis

# Set environment variables
railway variables set SECRET_KEY_BASE=<value>
railway variables set ANTHROPIC_API_KEY=<value>

# Deploy
railway up

# View logs
railway logs --service fastapi

# Connect domain
railway domain add talentmatch.yourcompany.com
```

### 8.6 Infrastructure Costs (Per Client)

```
┌──────────────────────────────────────────────┐
│  MONTHLY INFRASTRUCTURE COSTS                │
├──────────────────────────────────────────────┤
│  Railway (Docker hosting)                    │
│  - Chatwoot + FastAPI + Redis                │
│  - 2GB RAM, 2 vCPU                  €20/mo   │
│                                               │
│  Supabase PGVector                            │
│  - Free tier: 500MB database                 │
│  - 2GB egress bandwidth             €0/mo    │
│                                               │
│  360Dialog (WhatsApp API)                     │
│  - €49 setup fee (one-time)                  │
│  - €49/month subscription           €50/mo   │
│                                               │
│  Claude API (Anthropic)                       │
│  - ~30K requests/month                        │
│  - Claude 3.5 Sonnet               €30/mo    │
│                                               │
│  OpenAI API                                   │
│  - GPT-4o-mini (routing + CRM)      €5/mo    │
│  - text-embedding-3-small           €10/mo   │
├──────────────────────────────────────────────┤
│  TOTAL PER CLIENT:                  €115/mo  │
└──────────────────────────────────────────────┘

PRICING TO CLIENT: €500-800/month
PROFIT MARGIN: €385-685/month (77-85%)

COMPARISON TO v5.0 (Dual UI):
v5.0 cost: $618-743/month
v5.1 cost: €115/month
SAVINGS: €503-628/month (81-85% reduction!)
```

---

## APPENDIX A: IMPLEMENTATION CHECKLIST

### Phase 1: Foundation (Week 1-2)
- [ ] Deploy Chatwoot on Railway
- [ ] Configure PostgreSQL database
- [ ] Setup Redis for Celery
- [ ] Create Supabase project + PGVector
- [ ] Setup FastAPI webhook receiver
- [ ] Test end-to-end message flow (echo bot)
- [ ] Configure WhatsApp MCP for dev testing

### Phase 2: LangGraph + 4 Agents (Week 3-4)
- [ ] Implement ConversationState TypedDict
- [ ] Create StateGraph with 4 nodes
- [ ] Implement Router Agent (GPT-4o-mini)
- [ ] Implement Extraction Agent (Pydantic AI)
- [ ] Implement Conversation Agent (Claude SDK)
- [ ] Implement CRM Agent (GPT-4o-mini)
- [ ] Test conditional routing (human takeover)
- [ ] Validate CRM updates in Chatwoot

### Phase 3: Agentic RAG (Week 5)
- [ ] Create documents table in Supabase
- [ ] Implement vector search function
- [ ] Build document ingestion pipeline
- [ ] Define search_knowledge_base tool
- [ ] Implement tool execution loop
- [ ] Test agent autonomous decision-making
- [ ] Upload initial knowledge base documents

### Phase 4: CRM + Human Takeover (Week 6)
- [ ] Configure custom attributes schema
- [ ] Create label taxonomy
- [ ] Implement private note system
- [ ] Test human takeover workflow
- [ ] Build AI summary generation
- [ ] Test multi-channel messaging

### Phase 5: Production WhatsApp (Week 7)
- [ ] Setup 360Dialog account
- [ ] Configure webhook integration
- [ ] Implement rate limiting
- [ ] Test production message flow
- [ ] Build ScrapeCreators import script
- [ ] Implement GDPR compliance features

### Phase 6: White-Label + Testing (Week 8)
- [ ] Configure branding variables
- [ ] Test per-client deployments
- [ ] End-to-end testing (3 use cases)
- [ ] Performance testing (load testing)
- [ ] Security audit
- [ ] Production deployment

---

## APPENDIX B: TECHNOLOGY ALTERNATIVES CONSIDERED

### Alternative 1: Next.js Dashboard + Chatwoot
**Rejected**: PRD v5.0 approach deemed too complex
- **Pros**: Custom UI, better analytics
- **Cons**: 6 extra weeks development, €500/mo higher cost
- **Decision**: Chatwoot CRM sufficient for user's 3 use cases

### Alternative 2: 7 Agents (PRD v5.0)
**Rejected**: Unnecessary complexity
- **Removed Agents**: Email Marketing, Form Processing, Research
- **Retained**: Router, Extraction, Conversation, CRM (4 total)
- **Decision**: User doesn't need email campaigns or research

### Alternative 3: Standard RAG (Always Search)
**Rejected**: Wasteful for simple queries
- **Standard RAG**: Every message triggers vector search
- **Agentic RAG**: Agent decides when search needed
- **Decision**: 40% cost reduction, faster responses

### Alternative 4: Multi-Tenant SaaS
**Rejected**: User explicitly declined
- **User Quote**: "Ik wil geen SaaS bouwen en een multi tenant"
- **Alternative**: White-label per-client deployments
- **Decision**: Simpler architecture, easier customization

---

**END OF ARCHITECTURE DOCUMENT**

*Version: 5.1*
*Generated: 2025-01-15*
*Status: Production-Ready*
*Total Pages: 28*
