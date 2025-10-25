# 📋 Product Requirements Document (PRD)
# WhatsApp Recruitment Platform - Demo Build

**Version**: 1.0
**Date**: 2025-10-09
**Business Model**: Custom Builds (Not SaaS)
**Target**: Demo for client acquisition

---

## 🎯 Executive Summary

Building a **WhatsApp-based AI recruitment platform** that screens candidates via conversational AI, automatically qualifies them, and syncs to CRM systems.

**Business Model Pivot**: Moving from multi-tenant SaaS (€100/month) to **custom builds** (€7K-€12K upfront + €1K-€2K/month maintenance) due to better economics and 70% reusable foundation.

**Demo Goal**: Showcase core functionality to prospective clients with:
- ✅ Form submission → WhatsApp conversation
- ✅ AI qualification with LangGraph + Claude SDK
- ✅ Dashboard with login
- ✅ Live chat takeover (human-in-the-loop)
- ✅ CRM sync (at least one provider)

**Timeline**: 2-3 weeks for MVP demo

---

## 👥 Target Users

### Primary Users: HR Managers / Recruiters
**Pain Points:**
- Manually screening 50-100+ applicants per week (5-10 hours/week)
- WhatsApp conversations scattered across personal phones
- No centralized database of candidate conversations
- Missing qualified candidates due to slow response times

**Goals:**
- Automate initial screening (save 80% of time)
- Never miss a qualified candidate (24/7 availability)
- Centralized dashboard for all candidates
- Take over conversations when needed

### Secondary Users: Applicants
**Pain Points:**
- Long application forms (15-20 fields)
- Days of waiting for response
- Impersonal email-based communication

**Goals:**
- Quick application process (2-3 minutes)
- Instant feedback via WhatsApp
- Natural conversation (not form-filling)

---

## 🌟 Core Features (Demo Scope)

### 1. **Lead Capture Form** (P0 - Must Have)

**User Story**: As a company, I want applicants to submit their basic info via a web form so I can start the qualification process.

**Acceptance Criteria:**
- [ ] Form with 6 fields: full_name, email, whatsapp_number, job_title, years_experience, source
- [ ] Client-side validation (required fields, email format, phone format)
- [ ] Submits to `POST /api/leads`
- [ ] Returns success message with "You'll receive a WhatsApp message shortly"
- [ ] Stores in `leads` table with status `new`

**Technical Spec:**
```typescript
// Form Fields
interface LeadForm {
  full_name: string;          // Required, min 2 chars
  email: string;              // Required, valid email
  whatsapp_number: string;    // Required, E.164 format (+31612345678)
  job_title: string;          // Required
  years_experience: number;   // Required, 0-50
  source: string;             // Optional, default 'web_form'
}

// API Endpoint
POST /api/leads
Body: LeadForm
Response: { id: UUID, message: "Success" }
```

**UI Mockup**: Simple form with company branding (configurable colors/logo)

**Effort**: 4 hours (frontend + backend + validation)

---

### 2. **WhatsApp Integration** (P0 - Must Have)

**User Story**: As the system, I want to send WhatsApp messages to applicants so I can start the AI qualification conversation.

**Acceptance Criteria:**
- [ ] Trigger WhatsApp message after form submission
- [ ] Send initial greeting message: "Hoi {name}! 👋 Bedankt voor je interesse in [Company]. Ik ben de AI-assistent die je eerste gesprek zal leiden. Mag ik je een paar vragen stellen over je ervaring?"
- [ ] Receive webhook for inbound messages from 360Dialog
- [ ] Store all messages in `messages` table with direction (inbound/outbound)
- [ ] Support text messages only (no media for demo)

**Technical Spec:**
```python
# WhatsApp Provider Interface
class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_message(self, to: str, message: str) -> str:
        """Returns message_id"""
        pass

# 360Dialog Implementation
class Dialog360Provider(WhatsAppProvider):
    def __init__(self, api_key: str, phone_number_id: str):
        self.api_key = api_key
        self.base_url = "https://waba.360dialog.io/v1"

    async def send_message(self, to: str, message: str) -> str:
        response = await httpx.post(
            f"{self.base_url}/messages",
            headers={"D360-API-KEY": self.api_key},
            json={
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
        )
        return response.json()["messages"][0]["id"]

# Webhook Receiver
POST /webhook/whatsapp
Headers: X-Signature (for verification)
Body: {
  "messages": [{
    "from": "+31612345678",
    "id": "wamid.xxx",
    "text": {"body": "Ja, graag!"},
    "timestamp": "1696348800"
  }]
}
```

**Environment Variables:**
```bash
DIALOG360_API_KEY=xxx
DIALOG360_PHONE_NUMBER_ID=yyy
DIALOG360_WEBHOOK_SECRET=zzz
```

**Effort**: 6 hours (provider implementation + webhook + testing)

---

### 3. **LangGraph Agent System** (P0 - Must Have)

**User Story**: As the AI system, I want to conduct intelligent multi-turn conversations with applicants so I can extract qualification information.

**Acceptance Criteria:**
- [ ] Implement LangGraph state machine with 5 nodes
- [ ] Node 1: `greet` - Send initial greeting
- [ ] Node 2: `extract_basic_info` - Ask about job title, experience, skills
- [ ] Node 3: `extract_technical_skills` - Industry-specific technical questions
- [ ] Node 4: `extract_soft_skills` - Communication, teamwork, availability
- [ ] Node 5: `qualify` - Calculate score using Claude SDK, update `leads.qualification_score`
- [ ] Support human-in-the-loop: If score < 0.5, pause and create notification for recruiter
- [ ] Store checkpoints in `agent_checkpoints` table
- [ ] Use Claude 3.5 Sonnet for all LLM calls

**Technical Spec:**
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from anthropic import Anthropic
from pydantic import BaseModel

# State Definition
class RecruitmentState(BaseModel):
    lead_id: str
    whatsapp_number: str
    messages: list[dict] = []
    extracted_info: dict = {}
    qualification_score: float = 0.0
    current_step: str = "greet"
    requires_human: bool = False

# Nodes
async def greet_node(state: RecruitmentState):
    message = f"Hoi! 👋 Ik zie dat je interesse hebt in de functie {state.extracted_info.get('job_title', 'onze vacature')}. Mag ik je een paar vragen stellen?"
    await whatsapp_provider.send_message(state.whatsapp_number, message)
    await save_message(state.lead_id, "outbound", message)
    return {"current_step": "extract_basic_info"}

async def extract_basic_info_node(state: RecruitmentState):
    # Use Claude to generate contextual follow-up questions
    client = Anthropic()
    conversation_history = await get_conversation_history(state.lead_id)

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system="""Je bent een vriendelijke recruitment assistent voor [Company Name].
        Stel natuurlijke vragen om deze informatie te achterhalen:
        - Huidige functie
        - Aantal jaren ervaring
        - Belangrijkste vaardigheden
        Stel 1 vraag per keer, wees informeel en vriendelijk.""",
        messages=conversation_history
    )

    next_question = response.content[0].text
    await whatsapp_provider.send_message(state.whatsapp_number, next_question)
    await save_message(state.lead_id, "outbound", next_question)

    # Check if basic info is complete
    if all(k in state.extracted_info for k in ["job_title", "years_experience", "skills"]):
        return {"current_step": "extract_technical_skills"}
    else:
        return {"current_step": "extract_basic_info"}  # Continue

async def qualify_node(state: RecruitmentState):
    # Use Claude with structured output to calculate score
    client = Anthropic()

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=[{
            "name": "calculate_qualification_score",
            "description": "Calculate qualification score from 0.0 to 1.0",
            "input_schema": {
                "type": "object",
                "properties": {
                    "technical_skills_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "soft_skills_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "experience_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "overall_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string"}
                },
                "required": ["technical_skills_score", "soft_skills_score", "experience_score", "overall_score", "reasoning"]
            }
        }],
        messages=[{
            "role": "user",
            "content": f"Analyse deze kandidaat informatie en bereken qualification score:\n\n{json.dumps(state.extracted_info, indent=2)}"
        }]
    )

    tool_use = response.content[0]
    score_data = tool_use.input
    overall_score = score_data["overall_score"]

    # Update lead in database
    await update_lead_score(state.lead_id, overall_score, score_data["reasoning"])

    # Check if human review needed
    if overall_score < 0.5:
        await create_notification(
            type="human_review_needed",
            title=f"Low score candidate: {state.extracted_info.get('full_name')}",
            message=f"Score: {overall_score:.0%}. Please review.",
            link=f"/leads/{state.lead_id}"
        )
        return {"qualification_score": overall_score, "requires_human": True, "current_step": END}

    # Auto-qualify if score >= 0.7
    if overall_score >= 0.7:
        await update_lead_status(state.lead_id, "qualified")
        await send_qualified_message(state.whatsapp_number, state.extracted_info.get("full_name"))

    return {"qualification_score": overall_score, "current_step": END}

# Build Workflow
def build_recruitment_workflow():
    workflow = StateGraph(RecruitmentState)

    # Add nodes
    workflow.add_node("greet", greet_node)
    workflow.add_node("extract_basic_info", extract_basic_info_node)
    workflow.add_node("extract_technical_skills", extract_technical_skills_node)
    workflow.add_node("extract_soft_skills", extract_soft_skills_node)
    workflow.add_node("qualify", qualify_node)

    # Define edges
    workflow.set_entry_point("greet")
    workflow.add_edge("greet", "extract_basic_info")
    workflow.add_edge("extract_basic_info", "extract_technical_skills")
    workflow.add_edge("extract_technical_skills", "extract_soft_skills")
    workflow.add_edge("extract_soft_skills", "qualify")

    # Compile with checkpointing (enables human-in-the-loop)
    checkpointer = PostgresSaver(conn_string=SUPABASE_URL)
    return workflow.compile(checkpointer=checkpointer)
```

**Conversation Flow Example:**
```
Agent: Hoi! 👋 Ik zie dat je interesse hebt in de functie Kapper. Mag ik je een paar vragen stellen?
User: Ja hoor
Agent: Super! Hoeveel jaar ervaring heb je als kapper?
User: 3 jaar
Agent: Mooi! En wat zijn je specialiteiten? (bijv. knippen, kleuren, extensions)
User: Vooral knippen en kleuren
Agent: Top! Ben je bekend met biologische haarverzorgingsproducten?
User: Ja, ik werk er al mee
Agent: Geweldig! Hoe ga je om met moeilijke klanten?
User: Ik blijf altijd kalm en probeer te luisteren naar wat ze echt willen
Agent: Dankjewel! Ik heb genoeg informatie. Ik zie dat je een sterke kandidaat bent (score: 85%). Iemand van ons team neemt binnenkort contact met je op!
```

**Effort**: 12 hours (state machine + nodes + Claude integration + testing)

---

### 4. **RAG (Semantic Search)** (P1 - Nice to Have for Demo)

**User Story**: As the AI agent, I want to search similar past conversations so I can provide context-aware responses.

**Acceptance Criteria:**
- [ ] Generate embeddings for all messages using OpenAI ada-002
- [ ] Store embeddings in `messages.embedding` column (vector(1536))
- [ ] Implement semantic search: `SELECT * FROM messages WHERE embedding <-> query_embedding < 0.8 ORDER BY embedding <-> query_embedding LIMIT 5`
- [ ] Include top 3 similar conversations in Claude prompt context

**Technical Spec:**
```python
import openai
from pgvector.sqlalchemy import Vector

async def generate_embedding(text: str) -> list[float]:
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

async def semantic_search(query: str, lead_id: str, limit: int = 5):
    query_embedding = await generate_embedding(query)

    results = await db.execute("""
        SELECT content, created_at
        FROM messages
        WHERE lead_id = :lead_id
        ORDER BY embedding <-> :query_embedding
        LIMIT :limit
    """, {"lead_id": lead_id, "query_embedding": query_embedding, "limit": limit})

    return [{"content": row.content, "timestamp": row.created_at} for row in results]
```

**Cost**: ~$0.0001 per message (negligible for demo)

**Effort**: 4 hours (if included in demo, can be skipped)

---

### 5. **Dashboard (Reflex)** (P0 - Must Have)

**User Story**: As a recruiter, I want to see all applicants in a centralized dashboard so I can review their qualification status and take over conversations.

**Acceptance Criteria:**
- [ ] Login page with email/password (Supabase Auth)
- [ ] Leads list page with table:
  - Columns: Name, WhatsApp, Job Title, Score, Status, Created At
  - Filters: Status (all, new, qualified, disqualified, pending_review)
  - Sort: By score (descending), by date (descending)
  - Click row → Navigate to detail page
- [ ] Lead detail page:
  - Top: Candidate info card (name, email, phone, job title, score)
  - Middle: Full conversation history (chronological)
  - Bottom: Live chat takeover (text input + send button)
  - Real-time updates via WebSocket when new messages arrive
- [ ] Sidebar navigation: Leads, Settings, Logout

**Technical Spec:**
```python
import reflex as rx

class LoginState(rx.State):
    email: str = ""
    password: str = ""
    is_authenticated: bool = False

    async def handle_login(self):
        # Supabase Auth
        response = await supabase.auth.sign_in_with_password({
            "email": self.email,
            "password": self.password
        })
        if response.user:
            self.is_authenticated = True
            return rx.redirect("/leads")
        else:
            return rx.window_alert("Invalid credentials")

class LeadsListState(rx.State):
    leads: list[dict] = []
    status_filter: str = "all"

    async def load_leads(self):
        query = supabase.table("leads").select("*")
        if self.status_filter != "all":
            query = query.eq("qualification_status", self.status_filter)
        response = await query.order("created_at", desc=True).execute()
        self.leads = response.data

    def filter_by_status(self, status: str):
        self.status_filter = status
        return self.load_leads()

def leads_list_page():
    return rx.container(
        rx.heading("Applicants", size="lg"),
        rx.hstack(
            rx.button("All", on_click=LeadsListState.filter_by_status("all")),
            rx.button("New", on_click=LeadsListState.filter_by_status("new")),
            rx.button("Qualified", on_click=LeadsListState.filter_by_status("qualified")),
            rx.button("Pending Review", on_click=LeadsListState.filter_by_status("pending_review"))
        ),
        rx.table(
            headers=["Name", "WhatsApp", "Job Title", "Score", "Status", "Date"],
            rows=[
                [
                    lead["full_name"],
                    lead["whatsapp_number"],
                    lead["job_title"],
                    f"{lead['qualification_score']:.0%}" if lead["qualification_score"] else "N/A",
                    lead["qualification_status"],
                    lead["created_at"]
                ]
                for lead in LeadsListState.leads
            ],
            on_row_click=lambda lead_id: rx.redirect(f"/leads/{lead_id}")
        )
    )

class LiveChatState(rx.State):
    lead_id: str
    messages: list[dict] = []
    new_message: str = ""

    async def load_messages(self):
        response = await supabase.table("messages") \
            .select("*") \
            .eq("lead_id", self.lead_id) \
            .order("created_at", asc=True) \
            .execute()
        self.messages = response.data

    async def send_message(self):
        # Send via WhatsApp
        lead = await supabase.table("leads").select("whatsapp_number").eq("id", self.lead_id).single().execute()
        await whatsapp_provider.send_message(lead.data["whatsapp_number"], self.new_message)

        # Save to database
        await supabase.table("messages").insert({
            "lead_id": self.lead_id,
            "direction": "outbound",
            "content": self.new_message,
            "agent_name": "human_takeover"
        }).execute()

        self.new_message = ""
        return self.load_messages()

def lead_detail_page():
    return rx.container(
        # Candidate info card
        rx.card(
            rx.heading(f"{LeadDetailState.lead['full_name']} - {LeadDetailState.lead['job_title']}"),
            rx.text(f"Score: {LeadDetailState.lead['qualification_score']:.0%}"),
            rx.text(f"Status: {LeadDetailState.lead['qualification_status']}")
        ),

        # Conversation history
        rx.box(
            *[
                rx.hstack(
                    rx.text(msg["content"], bg="blue" if msg["direction"] == "outbound" else "gray"),
                    rx.spacer(),
                    rx.text(msg["created_at"], size="xs")
                )
                for msg in LiveChatState.messages
            ],
            height="400px",
            overflow_y="scroll"
        ),

        # Live chat input
        rx.hstack(
            rx.input(
                placeholder="Type your message...",
                value=LiveChatState.new_message,
                on_change=LiveChatState.set_new_message
            ),
            rx.button("Send", on_click=LiveChatState.send_message)
        )
    )
```

**Styling**: Company branding colors from `system_config.branding`

**Effort**: 10 hours (pages + state management + WebSocket + styling)

---

### 6. **CRM Integration** (P1 - Nice to Have for Demo)

**User Story**: As a recruiter, I want qualified candidates automatically synced to my CRM so I can follow up without manual data entry.

**Acceptance Criteria:**
- [ ] Implement at least ONE CRM provider (recommend: HubSpot or Custom Webhook)
- [ ] Trigger CRM sync when `qualification_score >= 0.7`
- [ ] Map fields: full_name → Contact Name, email → Email, whatsapp_number → Phone, qualification_score → Custom Property
- [ ] Store `crm_id` in `leads.crm_id` after successful sync
- [ ] Log sync status in `audit_logs`

**Technical Spec (HubSpot Example):**
```python
class HubSpotProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"

    async def create_contact(self, lead: dict) -> str:
        """Returns HubSpot contact ID"""
        response = await httpx.post(
            f"{self.base_url}/crm/v3/objects/contacts",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "properties": {
                    "firstname": lead["full_name"].split()[0],
                    "lastname": " ".join(lead["full_name"].split()[1:]),
                    "email": lead["email"],
                    "phone": lead["whatsapp_number"],
                    "jobtitle": lead["job_title"],
                    "recruitment_score": lead["qualification_score"]  # Custom property
                }
            }
        )
        return response.json()["id"]

# Trigger in qualify_node
if overall_score >= 0.7:
    crm = HubSpotProvider(api_key=os.getenv("HUBSPOT_API_KEY"))
    crm_id = await crm.create_contact(lead_data)
    await update_lead_crm_id(state.lead_id, crm_id)
```

**Effort**: 4 hours (provider + field mapping + testing) - Can be skipped for demo if tight on time

---

## 🏗️ Technical Architecture

### System Components
```
┌─────────────────┐
│   Applicant     │
│  (Web Browser)  │
└────────┬────────┘
         │ 1. Submit form
         ▼
┌─────────────────┐
│  Frontend Form  │
│   (HTML/CSS/JS) │
└────────┬────────┘
         │ 2. POST /api/leads
         ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌──────────────────────────────┐  │
│  │  Routes: /api/leads          │  │
│  │          /webhook/whatsapp   │  │
│  │          /api/auth/login     │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  Services: LeadService       │  │
│  │            MessageService    │  │
│  └──────────────────────────────┘  │
└─────────┬───────────────────┬───────┘
          │                   │
          │ 3. Save lead      │ 5. Webhook
          │                   │
          ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│   Supabase DB   │  │  360Dialog API  │
│  (PostgreSQL)   │  │   (WhatsApp)    │
└────────┬────────┘  └────────┬────────┘
         │ 4. Trigger          │
         │                     │ 6. Message
         ▼                     │
┌─────────────────────────────┴───────┐
│      LangGraph Agent System         │
│  ┌──────────────────────────────┐  │
│  │  State Machine:              │  │
│  │  - greet                     │  │
│  │  - extract_basic_info        │  │
│  │  - extract_technical_skills  │  │
│  │  - extract_soft_skills       │  │
│  │  - qualify                   │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  Claude 3.5 Sonnet API       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         │ 7. Update score
         ▼
┌─────────────────┐
│   Supabase DB   │
│ (qualification_ │
│  score updated) │
└────────┬────────┘
         │
         │ 8. Sync if qualified
         ▼
┌─────────────────┐
│   HubSpot CRM   │
│ (or other CRM)  │
└─────────────────┘

         │
         │ 9. View dashboard
         ▼
┌─────────────────┐
│ Reflex Dashboard│
│  - Leads list   │
│  - Lead detail  │
│  - Live chat    │
└─────────────────┘
```

### Tech Stack Summary
| Layer | Technology | Justification |
|-------|------------|---------------|
| Frontend | HTML/CSS/JS (form), Reflex (dashboard) | Simple form, Python-based dashboard |
| Backend API | FastAPI | Async, type hints, auto-docs |
| Database | Supabase (PostgreSQL + PGVector) | All-in-one: DB + Auth + Storage + Real-time |
| Orchestration | LangGraph | Multi-agent state machines, checkpointing |
| LLM | Claude 3.5 Sonnet | Best Dutch support, structured output |
| Validation | Pydantic v2 | Type safety, runtime validation |
| WhatsApp | 360Dialog | Official WhatsApp Business API |
| Deployment | Railway | Auto-scaling, simple deploy |
| Task Queue | Celery + Redis | Background jobs (optional for demo) |

---

## 📅 Implementation Roadmap (Demo Build)

### **Week 1: Foundation (40 hours)**

#### Day 1-2: Setup & Database (16 hours)
- [ ] Setup project structure
- [ ] Setup Supabase project
- [ ] Run `schema.sql` migration
- [ ] Setup FastAPI boilerplate
- [ ] Implement authentication (Supabase Auth JWT)
- [ ] Write database service layer (CRUD operations)
- [ ] Setup 360Dialog account + get API key

#### Day 3-4: Form & WhatsApp Integration (16 hours)
- [ ] Build lead capture form (HTML/CSS/JS)
- [ ] Implement `POST /api/leads` endpoint
- [ ] Implement WhatsAppProvider abstraction + 360Dialog provider
- [ ] Implement `POST /webhook/whatsapp` endpoint
- [ ] Test end-to-end: Form submit → WhatsApp message received

#### Day 5: Testing & Debugging (8 hours)
- [ ] Test form validation
- [ ] Test webhook signature verification
- [ ] Test message storage
- [ ] Fix any issues

---

### **Week 2: AI Agent System (40 hours)**

#### Day 6-7: LangGraph Setup (16 hours)
- [ ] Setup LangGraph state machine
- [ ] Implement `RecruitmentState` Pydantic model
- [ ] Implement `greet_node`
- [ ] Implement `extract_basic_info_node`
- [ ] Test state transitions

#### Day 8-9: Agent Nodes (16 hours)
- [ ] Implement `extract_technical_skills_node`
- [ ] Implement `extract_soft_skills_node`
- [ ] Implement `qualify_node` with Claude SDK
- [ ] Implement structured output (qualification score calculation)
- [ ] Test full conversation flow

#### Day 10: Human-in-the-Loop (8 hours)
- [ ] Implement checkpointing (PostgresSaver)
- [ ] Implement pause logic (score < 0.5)
- [ ] Create notification when human review needed
- [ ] Test resume conversation after human feedback

---

### **Week 3: Dashboard & Polish (40 hours)**

#### Day 11-12: Reflex Dashboard (16 hours)
- [ ] Setup Reflex project
- [ ] Implement login page
- [ ] Implement leads list page with filters
- [ ] Implement lead detail page
- [ ] Style with company branding

#### Day 13-14: Live Chat & Real-time (16 hours)
- [ ] Implement live chat takeover UI
- [ ] Implement WebSocket connection for real-time messages
- [ ] Test sending messages from dashboard → WhatsApp
- [ ] Test receiving messages WhatsApp → Dashboard

#### Day 15: CRM Integration (Optional) + Final Testing (8 hours)
- [ ] Implement HubSpot provider (if included)
- [ ] Test CRM sync for qualified leads
- [ ] End-to-end testing: Form → Conversation → Dashboard → CRM
- [ ] Fix any bugs
- [ ] Deploy to Railway

---

## 🚀 Deployment Checklist

### Railway Deployment
- [ ] Create Railway project
- [ ] Add PostgreSQL plugin (or use Supabase external connection)
- [ ] Set environment variables:
  ```bash
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_ANON_KEY=xxx
  SUPABASE_SERVICE_KEY=xxx
  ANTHROPIC_API_KEY=xxx
  DIALOG360_API_KEY=xxx
  DIALOG360_PHONE_NUMBER_ID=xxx
  DIALOG360_WEBHOOK_SECRET=xxx
  HUBSPOT_API_KEY=xxx (optional)
  ```
- [ ] Deploy FastAPI backend
- [ ] Deploy Reflex dashboard
- [ ] Configure custom domain (e.g., `demo.yourcompany.com`)
- [ ] Test production deployment

### Supabase Configuration
- [ ] Enable Row Level Security (optional for demo, but good practice)
- [ ] Create service account for backend
- [ ] Setup email templates for auth
- [ ] Configure CORS for frontend domain

### 360Dialog Configuration
- [ ] Register WhatsApp Business Number
- [ ] Configure webhook URL: `https://demo.yourcompany.com/webhook/whatsapp`
- [ ] Test webhook with test message

---

## 📊 Success Metrics (Demo Evaluation)

### Technical Metrics
- [ ] Form submission success rate: 100%
- [ ] WhatsApp message delivery rate: 100%
- [ ] Agent response time: < 5 seconds
- [ ] Dashboard load time: < 2 seconds
- [ ] Conversation completion rate: > 80% (applicants complete full conversation)

### Business Metrics (After Demo with Clients)
- [ ] Client interest: 5+ demo requests
- [ ] Conversion rate: 30%+ (demos → paid clients)
- [ ] Setup time per client: < 10 hours (proves 70/30 foundation works)

---

## 🎨 Customization Guide (Per Client)

After demo is built, here's what needs customization for each client:

### 1. **Configuration File** (30 minutes)
```python
# config/client_config.py

COMPANY_INFO = {
    "name": "Hair Treats",
    "logo_url": "https://cdn.hairtreats.nl/logo.png",
    "primary_color": "#FF6B9D",
    "secondary_color": "#C147E9"
}

QUALIFICATION_WEIGHTS = {
    "technical_skills": 0.4,
    "soft_skills": 0.4,
    "experience_years": 0.1,
    "education": 0.1
}

FORM_FIELDS = [
    {"name": "full_name", "type": "text", "required": True},
    {"name": "email", "type": "email", "required": True},
    {"name": "whatsapp_number", "type": "tel", "required": True},
    {"name": "years_experience", "type": "number", "required": True},
    {"name": "specializations", "type": "multiselect", "options": ["Knippen", "Kleuren", "Extensions"]}
]
```

### 2. **Expert Prompts** (2 hours)
```python
# config/expert_prompts.py

TECHNICAL_EXPERT_PROMPT = """
Je bent een kapper-expert met 15 jaar ervaring.
Stel vragen over:
- Knippen (klassiek, modern, baarden)
- Kleuren (highlights, balayage, toning)
- Haarverzorging producten (Olaplex, K18, biologisch)
"""

SOFT_SKILLS_EXPERT_PROMPT = """
Je bent een recruitment expert voor de schoonheidsbranche.
Stel vragen over:
- Klantgericht werken
- Omgaan met klachten
- Samenwerken in team
- Flexibiliteit (weekenden, avonden)
"""
```

### 3. **CRM Field Mapping** (2 hours)
```python
# config/crm_mapping.py

HUBSPOT_FIELD_MAPPING = {
    "full_name": "firstname + lastname",
    "email": "email",
    "whatsapp_number": "phone",
    "job_title": "jobtitle",
    "qualification_score": "recruitment_score"  # Custom property (must create in HubSpot first)
}
```

### 4. **Deployment** (6 hours)
- Clone foundation repo
- Update config files
- Create Supabase project
- Deploy to Railway
- Configure 360Dialog webhook
- Test end-to-end

**Total Customization Time**: 10-12 hours per client (justifies €7K-€12K upfront fee)

---

## 🔒 Security Considerations (Demo Scope)

### Must Have (Even for Demo):
- [ ] HTTPS-only (Railway provides free SSL)
- [ ] JWT authentication for dashboard
- [ ] Environment variables for secrets (not hardcoded)
- [ ] Webhook signature verification (360Dialog)
- [ ] SQL injection protection (parameterized queries via SQLAlchemy)
- [ ] Rate limiting (basic: 100 req/min per IP)

### Nice to Have (Skip for Demo):
- ❌ Encryption at rest (SQLCipher) - Skip for demo
- ❌ Audit logs - Skip for demo
- ❌ GDPR compliance (data deletion API) - Add for production
- ❌ Sentry error tracking - Skip for demo

---

## 💰 Cost Breakdown (Per Client)

### Infrastructure Costs (Monthly):
- **Supabase**: €25/month (Pro plan, 8GB database)
- **Railway**: €20-50/month (depends on usage, scales automatically)
- **360Dialog**: €49/month (WhatsApp Business API)
- **Claude API**: ~€10/month (assuming 100 conversations × 5K tokens × €15/1M tokens)
- **OpenAI Embeddings** (if RAG included): ~€5/month

**Total Infrastructure**: €109-139/month per client

### Revenue (Per Client):
- **Setup Fee**: €7,000 - €12,000 (one-time)
- **Monthly Maintenance**: €1,000 - €2,000 (recurring)

### Profit (Per Client):
- **First Month**: €7,000-€12,000 - €139 = €6,861-€11,861
- **Monthly Recurring**: €1,000-€2,000 - €139 = €861-€1,861
- **Annual Recurring Revenue**: €10,332-€22,332 per client

**Target**: 10 clients in first year = €103K-€223K annual recurring revenue (excluding setup fees)

---

## 🎯 Next Steps

1. ✅ **Architecture Documented** (`ARCHITECTURE.md`)
2. ✅ **Database Schema Created** (`database/schema.sql`)
3. ✅ **PRD Created** (this document)
4. **Start Week 1 Implementation** (after approval)
5. **Schedule Client Demos** (after Week 3)

---

## 📞 Questions for Stakeholder (You)

Before starting implementation, please confirm:

1. **CRM Choice**: Should demo include CRM sync? If yes, which provider? (HubSpot recommended for demo, easiest API)
2. **RAG Inclusion**: Should demo include semantic search (RAG)? Adds 4 hours, not critical for demo.
3. **Calendar Integration**: Skip for demo? (Can be added per-client later)
4. **Dashboard Framework**: Confirm Reflex? (Alternative: Streamlit is faster but less customizable)
5. **Timeline**: Is 2-3 weeks acceptable for demo completion?

---

**End of PRD**
