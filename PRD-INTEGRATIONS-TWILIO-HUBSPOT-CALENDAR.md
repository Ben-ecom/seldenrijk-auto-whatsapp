# 📋 PRODUCT REQUIREMENTS DOCUMENT (PRD)
**Seldenrijk Auto WhatsApp Agent - Integrations Upgrade**

---

## DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| **Project Name** | Seldenrijk Auto WhatsApp Agent - Integrations Upgrade |
| **Version** | 2.0.0 |
| **Status** | ✅ READY FOR IMPLEMENTATION |
| **Last Updated** | 2025-10-24 |
| **Owner** | Seldenrijk Auto + SDK AGENTS Framework Team |
| **Approval Status** | Pending Implementation |

---

## EXECUTIVE SUMMARY

This PRD outlines the integration upgrade for the Seldenrijk Auto WhatsApp Agent system, transitioning from WAHA to Twilio WhatsApp Business API and adding HubSpot Free CRM + Google Calendar integrations for comprehensive lead management and appointment scheduling.

### Key Objectives
1. **Replace WAHA with Twilio** - Reduce cost (€75/month savings), improve reliability (99.95% SLA)
2. **Integrate HubSpot Free CRM** - Add sales pipeline tracking, deal management, lead scoring
3. **Integrate Google Calendar** - Automate appointment scheduling for test drives and viewings
4. **Enhance CRM Agent Logic** - Multi-system routing (Chatwoot + HubSpot + Calendar)

### Success Metrics
- ✅ Cost reduction: €75/month (€900/year)
- ✅ Reliability improvement: 99.95% SLA vs previous Docker issues
- ✅ Lead conversion increase: +20-30% (with proper pipeline management)
- ✅ Appointment booking: 100% automated (no manual calendar management)
- ✅ Implementation time: 4 weeks (26 days)

---

## 1. STRATEGIC CONTEXT

### 1.1 Problem Statement

**Current Limitations:**
- ❌ WAHA costs €135/month with Docker reliability issues
- ❌ No sales CRM (leads tracked only operationally in Chatwoot)
- ❌ No pipeline management (can't track deal stages: Inquiry → Test Drive → Negotiation → Closed)
- ❌ Manual appointment scheduling (sales team uses personal calendars)
- ❌ No centralized lead data (car preferences, budget, trade-in data scattered)

**Business Impact:**
- Lost leads due to manual follow-up delays
- Inefficient sales process (no pipeline visibility)
- Double bookings and scheduling conflicts
- €75/month wasted on expensive WhatsApp provider
- No sales performance metrics (conversion rates, deal values)

**Solution: Integrated System Upgrade**
- Twilio WhatsApp Business API (€60/month, 99.95% SLA)
- HubSpot Free CRM (€0/month, full sales pipeline)
- Google Calendar API (€0/month, automated scheduling)
- Enhanced CRM Agent (intelligent multi-system routing)

### 1.2 Target Users

**Primary: Sales Team (2-5 reps)**
- Need centralized lead management
- Want automated appointment scheduling
- Require pipeline visibility
- Need mobile access to customer data

**Secondary: Management**
- Want sales performance metrics
- Need conversion rate tracking
- Require ROI measurement

### 1.3 Success Criteria

**Technical:**
- 99.95% uptime (Twilio SLA)
- <2 second response time
- 100% message delivery rate
- Zero double bookings

**Business:**
- €900/year cost savings
- +20-30% lead conversion rate
- 95% faster appointment booking
- 100% lead data capture

---

## 2. TECHNICAL ARCHITECTURE

### 2.1 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│             SELDENRIJK AUTO WHATSAPP AGENT v2.0              │
│         (Twilio + HubSpot + Google Calendar Integration)     │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  WhatsApp Customer  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│          TWILIO WHATSAPP BUSINESS API 🆕                    │
│  - Webhook: POST /webhooks/twilio/whatsapp                 │
│  - Signature validation (X-Twilio-Signature header)        │
│  - Cost: €60/month + €0.0042/message                       │
│  - SLA: 99.95% uptime                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             FASTAPI BACKEND (Python + LangGraph)            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       INCOMING MESSAGE WEBHOOK HANDLER               │  │
│  │  1. Validate Twilio signature                        │  │
│  │  2. Parse Twilio JSON → Internal schema              │  │
│  │  3. Send to Chatwoot (operational tracking)          │  │
│  │  4. Trigger LangGraph orchestration                  │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           LANGGRAPH AGENT ORCHESTRATION                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  ┌──────────┐ │
│  │  ROUTER  │──▶│EXTRACTION│──▶│CONVERSATION│▶│ENHANCED  │ │
│  │ GPT-4o-  │   │Pydantic  │   │Claude 4.5 │  │CRM AGENT │ │
│  │  mini    │   │    AI    │   │    +RAG   │  │  🔥NEW   │ │
│  └──────────┘   └──────────┘   └──────────┘  └────┬─────┘ │
└───────────────────────────────────────────────────┼─────────┘
                                                    │
             ┌──────────────────────────────────────┼──────────────────┐
             │                                      │                  │
             ▼                                      ▼                  ▼
┌──────────────────────┐  ┌────────────────────────────┐  ┌────────────────────┐
│  CHATWOOT CRM        │  │    HUBSPOT FREE CRM 🆕     │  │GOOGLE CALENDAR 🆕  │
│  (Operational)       │  │    (Sales Pipeline)        │  │(Appointments)      │
│                      │  │                            │  │                    │
│ - Conversations      │  │ REST API v3:               │  │ REST API v3:       │
│ - Team inbox         │  │ - Contacts (leads)         │  │ - Events (appts)   │
│ - Agent notes        │  │ - Deals (pipeline)         │  │ - Availability     │
│ - Labels/tags        │  │ - Tasks (follow-ups)       │  │ - Email invites    │
│                      │  │ - Notes (history)          │  │ - Conflict check   │
│                      │  │ - Custom properties:       │  │                    │
│                      │  │   * car_preference         │  │ Service Account:   │
│                      │  │   * budget_range           │  │ - Manages shared   │
│                      │  │   * trade_in_car_model     │  │   calendar         │
│                      │  │   * urgency_level          │  │ - No token refresh │
│                      │  │ - Pipelines:               │  │                    │
│                      │  │   * Car Sales              │  │                    │
│                      │  │ - Stages:                  │  │                    │
│                      │  │   * Inquiry                │  │                    │
│                      │  │   * Qualified              │  │                    │
│                      │  │   * Appointment Scheduled  │  │                    │
│                      │  │   * Test Drive Completed   │  │                    │
│                      │  │   * Negotiation            │  │                    │
│                      │  │   * Closed Won/Lost        │  │                    │
└──────────────────────┘  └────────────────────────────┘  └────────────────────┘
             │                      │                                │
             └──────────────────────┴────────────────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ SUPABASE POSTGRESQL  │
                         │                      │
                         │ - leads              │
                         │ - conversations      │
                         │ - integrations_log🆕 │
                         │ - calendar_events 🆕 │
                         └──────────────────────┘
```

### 2.2 Enhanced CRM Agent Decision Tree

```
┌──────────────────────────────────────────────────────────────┐
│             ENHANCED CRM AGENT DECISION TREE 🔥              │
└──────────────────────────────────────────────────────────────┘

INPUT: {
  intent: string,              // From Router Agent
  extracted_data: {           // From Extraction Agent
    customer_name: string,
    phone: string,
    car_preference: string,
    budget_range: string,
    urgency_level: string,
    appointment_type: string,
    preferred_date: string,
    email: string
  }
}

DECISION TREE:

1. CHECK INTENT
   │
   ├─▶ IF intent == "car_inquiry" AND high_engagement == TRUE
   │   │
   │   ├─▶ ACTION: Create HubSpot Contact
   │   │   - name, phone, email
   │   │   - custom properties: car_preference, budget_range, lead_source="WhatsApp"
   │   │
   │   ├─▶ ACTION: Create HubSpot Deal
   │   │   - contact_id: from above
   │   │   - pipeline: "Car Sales"
   │   │   - stage: "Inquiry"
   │   │   - amount: budget_range
   │   │   - properties: car_preference, urgency_level
   │   │
   │   └─▶ ACTION: Create HubSpot Note
   │       - object_id: deal_id
   │       - content: "Customer interested in {car_preference}"
   │
   ├─▶ IF intent == "appointment_request"
   │   │
   │   ├─▶ ACTION: Check Google Calendar Availability
   │   │   - date_range: parse(preferred_date)
   │   │   - Get available slots
   │   │
   │   ├─▶ IF available_slots.length > 0
   │   │   │
   │   │   ├─▶ ACTION: Create Google Calendar Event
   │   │   │   - summary: "Test Drive: {car_preference} - {customer_name}"
   │   │   │   - start: available_slots[0].start
   │   │   │   - end: available_slots[0].end
   │   │   │   - attendees: [customer_email, sales@seldenrijk.nl]
   │   │   │   - location: "Seldenrijk Auto Showroom, [address]"
   │   │   │
   │   │   ├─▶ ACTION: Update HubSpot Deal
   │   │   │   - deal_id: from state
   │   │   │   - stage: "Appointment Scheduled"
   │   │   │   - appointment_date: event.start
   │   │   │
   │   │   ├─▶ ACTION: Create HubSpot Task
   │   │   │   - title: "Follow up: Test Drive - {customer_name}"
   │   │   │   - due_date: event.start
   │   │   │   - associated_deal_id: deal_id
   │   │   │   - reminder: 1 hour before
   │   │   │
   │   │   └─▶ ACTION: Save to PostgreSQL
   │   │       - table: calendar_events
   │   │       - data: {lead_id, calendar_event_id, start_time, end_time, status}
   │   │
   │   └─▶ ELSE (no availability)
   │       └─▶ RETURN: {calendar_error: "No availability for {preferred_date}"}
   │
   ├─▶ IF intent == "trade_in_inquiry"
   │   │
   │   └─▶ ACTION: Update HubSpot Contact
   │       - contact_id: from state
   │       - custom_property: trade_in_car_model = extracted_data.trade_in_model
   │       - update_deal_stage: "Trade-in Evaluation"
   │
   └─▶ ALWAYS (for all intents)
       │
       ├─▶ ACTION: Update Chatwoot Conversation
       │   - conversation_id: from state
       │   - add_note: Summary of CRM actions taken
       │   - add_tag: Based on intent (e.g., "appointment_scheduled", "hot_lead")
       │
       └─▶ ACTION: Log Integration Activity
           - table: integrations_log
           - data: {
               timestamp,
               message_id,
               hubspot_contact_id,
               hubspot_deal_id,
               calendar_event_id,
               chatwoot_conversation_id,
               status: "success" | "failed",
               error_message: if failed
             }

OUTPUT: {
  hubspot_contact_id: string | null,
  hubspot_deal_id: string | null,
  calendar_event_id: string | null,
  chatwoot_conversation_id: string,
  integration_log_id: number,
  errors: string[]
}
```

### 2.3 Data Flow: Complete Message Lifecycle

```
[1] Customer Sends WhatsApp Message
    "Ik wil graag meer informatie over de BMW X5"
         │
         ▼
[2] Twilio Receives Message
     - Parse content: "Ik wil graag meer informatie over de BMW X5"
     - Metadata: {from: "+31612345678", to: "+31850000000", timestamp: "2025-10-26T14:30:00Z"}
     - POST /webhooks/twilio/whatsapp
     - Headers: {X-Twilio-Signature: "sha256=..."}
         │
         ▼
[3] FastAPI Webhook Handler
     - Validate signature: HMAC-SHA256(body, auth_token)
     - Parse Twilio JSON:
       {
         "From": "whatsapp:+31612345678",
         "To": "whatsapp:+31850000000",
         "Body": "Ik wil graag meer informatie over de BMW X5",
         "MessageSid": "SM1234567890abcdef",
         "AccountSid": "AC...",
         "NumMedia": "0"
       }
     - Convert to internal schema:
       {
         "from_number": "+31612345678",
         "message_text": "Ik wil graag meer informatie over de BMW X5",
         "timestamp": "2025-10-26T14:30:00Z"
       }
     - Save to PostgreSQL: INSERT INTO conversations (from_number, message_text, ...)
         │
         ▼
[4] Send to Chatwoot (async background task)
     - POST /api/v1/accounts/{account_id}/conversations
     - Body: {
         "source_id": "+31612345678",
         "inbox_id": 123,
         "contact_id": auto-create-or-find,
         "additional_attributes": {...}
       }
     - Response: {conversation_id: 456}
     - POST /api/v1/accounts/{account_id}/conversations/456/messages
     - Body: {content: "Ik wil graag meer informatie over de BMW X5"}
         │
         ▼
[5] Trigger LangGraph Orchestration
     ┌─────────────────────────────────────────────────────────┐
     │ [5a] Router Agent (GPT-4o-mini)                         │
     │  Input: "Ik wil graag meer informatie over de BMW X5"   │
     │  Output: {intent: "car_inquiry", confidence: 0.95}      │
     │         │                                               │
     │         ▼                                               │
     │ [5b] Extraction Agent (Pydantic AI)                     │
     │  Input: message + context                              │
     │  Output: {                                             │
     │    customer_name: "Jan de Vries",  // if in history    │
     │    car_preference: "BMW X5",                           │
     │    budget_range: null,  // not provided yet            │
     │    urgency_level: "medium"                             │
     │  }                                                      │
     │         │                                               │
     │         ▼                                               │
     │ [5c] Conversation Agent (Claude Sonnet 4.5 + RAG)       │
     │  - RAG Query: Search Seldenrijk inventory for "BMW X5" │
     │  - Found: 3 BMW X5 models (2021, 2022, 2023)           │
     │  - Generate response:                                  │
     │    "Goedemiddag! We hebben momenteel 3 BMW X5          │
     │     modellen op voorraad:                              │
     │     - 2021 BMW X5 xDrive40i - €48.950                  │
     │     - 2022 BMW X5 M50i - €72.500                       │
     │     - 2023 BMW X5 xDrive30d - €68.900                  │
     │     Welk model interesseert u het meest?"              │
     │         │                                               │
     │         ▼                                               │
     │ [5d] Enhanced CRM Agent 🔥                              │
     │  Decision Tree Execution:                              │
     │  - intent = "car_inquiry" ✅                            │
     │  - high_engagement = FALSE (first message, no budget)  │
     │  → SKIP HubSpot contact creation (wait for engagement) │
     │  → UPDATE Chatwoot only                                │
     │                                                        │
     │  Chatwoot Update:                                      │
     │  - POST /conversations/456/messages                    │
     │  - Body: {                                             │
     │      content: "Customer inquired about BMW X5",        │
     │      private: true,  // Internal note                  │
     │      message_type: "incoming"                          │
     │    }                                                   │
     │  - PATCH /conversations/456                            │
     │  - Body: {labels: ["car_inquiry", "bmw_x5"]}           │
     └─────────────────────────────────────────────────────────┘
         │
         ▼
[6] Send Response via Twilio
     - POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages
     - Headers: {Authorization: "Basic {base64(sid:token)}"}
     - Body: {
         "From": "whatsapp:+31850000000",
         "To": "whatsapp:+31612345678",
         "Body": "Goedemiddag! We hebben momenteel 3 BMW X5 modellen..."
       }
     - Response: {sid: "SM9876543210fedcba", status: "queued"}
         │
         ▼
[7] Customer Receives Response
    "Goedemiddag! We hebben momenteel 3 BMW X5 modellen op voorraad..."

┌─────────────────────────────────────────────────────────────┐
│              FOLLOW-UP MESSAGE (HIGH ENGAGEMENT)            │
└─────────────────────────────────────────────────────────────┘

[8] Customer Responds with Budget
    "De 2022 BMW X5 M50i lijkt me interessant! Mijn budget is €70.000"
         │
         ▼
[9] Repeat Steps 2-5 with NEW Extraction
     - Extraction Agent Output: {
         customer_name: "Jan de Vries",
         car_preference: "2022 BMW X5 M50i",
         budget_range: "€70.000",
         urgency_level: "high"  // Specific model + budget = high
       }
         │
         ▼
[10] Enhanced CRM Agent Decision
      - intent = "car_inquiry" ✅
      - high_engagement = TRUE ✅ (budget provided, specific model)

      → CREATE HUBSPOT CONTACT
        POST /crm/v3/objects/contacts
        Body: {
          "properties": {
            "firstname": "Jan",
            "lastname": "de Vries",
            "phone": "+31612345678",
            "car_preference": "2022 BMW X5 M50i",
            "budget_range": "€70.000",
            "lead_source": "WhatsApp",
            "urgency_level": "high"
          }
        }
        Response: {id: "contact_123"}

      → CREATE HUBSPOT DEAL
        POST /crm/v3/objects/deals
        Body: {
          "properties": {
            "dealname": "BMW X5 M50i - Jan de Vries",
            "pipeline": "Car Sales",
            "dealstage": "Inquiry",
            "amount": "70000",
            "car_model": "2022 BMW X5 M50i",
            "urgency": "high"
          },
          "associations": [
            {
              "to": {"id": "contact_123"},
              "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
            }
          ]
        }
        Response: {id: "deal_456"}

      → CREATE HUBSPOT NOTE
        POST /crm/v3/objects/notes
        Body: {
          "properties": {
            "hs_note_body": "Customer interested in 2022 BMW X5 M50i. Budget: €70.000. High urgency.",
            "hs_timestamp": "2025-10-26T14:35:00Z"
          },
          "associations": [
            {
              "to": {"id": "deal_456"},
              "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}]
            }
          ]
        }
        Response: {id: "note_789"}

      → UPDATE CHATWOOT
        PATCH /conversations/456
        Body: {
          "labels": ["car_inquiry", "bmw_x5_m50i", "hot_lead"],
          "custom_attributes": {
            "hubspot_contact_id": "contact_123",
            "hubspot_deal_id": "deal_456",
            "lead_score": 85
          }
        }

      → LOG INTEGRATION ACTIVITY
        INSERT INTO integrations_log (
          timestamp, message_id, hubspot_contact_id, hubspot_deal_id,
          calendar_event_id, chatwoot_conversation_id, status
        ) VALUES (
          NOW(), 'SM1234567890abcdef', 'contact_123', 'deal_456',
          NULL, 456, 'success'
        )
         │
         ▼
[11] Conversation Agent Response
      "Perfect! De 2022 BMW X5 M50i is een geweldige keuze. Het is
       een zeer gewilde auto met veel vermogen. Wilt u een proefrit
       inplannen om deze zelf te ervaren?"
         │
         ▼
[12] Customer Responds: "Ja graag! Zaterdag zou goed uitkomen"
         │
         ▼
[13] Enhanced CRM Agent - Appointment Flow
      - intent = "appointment_request" ✅
      - extracted_data: {
          appointment_type: "test_drive",
          car_model: "2022 BMW X5 M50i",
          preferred_date: "Saturday",
          customer_email: "jan@example.com"  // Ask if not in history
        }

      → CHECK GOOGLE CALENDAR AVAILABILITY
        GET /calendars/{calendar_id}/events
        - timeMin: "2025-10-26T10:00:00+02:00"  // Saturday 10am
        - timeMax: "2025-10-26T18:00:00+02:00"  // Saturday 6pm
        - Check for free slots

        Available Slots:
        - 10:00-11:00
        - 14:00-15:00
        - 16:00-17:00

      → CREATE GOOGLE CALENDAR EVENT
        POST /calendars/{calendar_id}/events
        Body: {
          "summary": "Test Drive: 2022 BMW X5 M50i - Jan de Vries",
          "start": {
            "dateTime": "2025-10-26T14:00:00+02:00",
            "timeZone": "Europe/Amsterdam"
          },
          "end": {
            "dateTime": "2025-10-26T15:00:00+02:00",
            "timeZone": "Europe/Amsterdam"
          },
          "attendees": [
            {"email": "jan@example.com", "displayName": "Jan de Vries"},
            {"email": "sales@seldenrijk.nl", "displayName": "Seldenrijk Sales Team"}
          ],
          "description": "Test drive for 2022 BMW X5 M50i\\nCustomer: Jan de Vries\\nBudget: €70.000",
          "location": "Seldenrijk Auto, [Showroom Address]",
          "reminders": {
            "useDefault": false,
            "overrides": [
              {"method": "email", "minutes": 60},
              {"method": "popup", "minutes": 30}
            ]
          }
        }
        Response: {id: "event_xyz", htmlLink: "https://calendar.google.com/event?eid=..."}

      → UPDATE HUBSPOT DEAL
        PATCH /crm/v3/objects/deals/deal_456
        Body: {
          "properties": {
            "dealstage": "Appointment Scheduled",
            "appointment_date": "2025-10-26T14:00:00+02:00",
            "close_date": "2025-11-02"  // Estimated 1 week after appointment
          }
        }

      → CREATE HUBSPOT TASK
        POST /crm/v3/objects/tasks
        Body: {
          "properties": {
            "hs_task_subject": "Follow up: Test Drive - Jan de Vries",
            "hs_task_body": "Test drive scheduled for 2022 BMW X5 M50i on Saturday 14:00. Prepare car, review financing options.",
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "HIGH",
            "hs_timestamp": "2025-10-26T14:00:00+02:00"
          },
          "associations": [
            {
              "to": {"id": "deal_456"},
              "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 216}]
            }
          ]
        }
        Response: {id: "task_abc"}

      → SAVE TO POSTGRESQL
        INSERT INTO calendar_events (
          lead_id, calendar_event_id, event_type, start_time, end_time,
          location, status, created_at
        ) VALUES (
          123, 'event_xyz', 'test_drive', '2025-10-26 14:00:00+02', '2025-10-26 15:00:00+02',
          'Seldenrijk Auto Showroom', 'scheduled', NOW()
        )

      → UPDATE CHATWOOT
        POST /conversations/456/messages
        Body: {
          "content": "Appointment scheduled: Saturday 26 Oct, 14:00-15:00. Calendar invite sent to jan@example.com",
          "private": true,
          "message_type": "activity"
        }

        PATCH /conversations/456
        Body: {
          "labels": ["appointment_scheduled"],
          "custom_attributes": {
            "appointment_date": "2025-10-26T14:00:00+02:00",
            "calendar_event_id": "event_xyz"
          }
        }
         │
         ▼
[14] Conversation Agent Response
      "Perfect! Uw proefrit voor de 2022 BMW X5 M50i is gepland voor
       zaterdag 26 oktober om 14:00 uur.

       U ontvangt een e-mail met een kalenderuitnodiging op jan@example.com.

       📍 Locatie: Seldenrijk Auto, [Showroom Address]
       ⏰ Tijd: 14:00 - 15:00 uur

       We kijken ernaar uit u zaterdag te zien! Heeft u nog vragen?"
         │
         ▼
[15] Customer Receives:
      - WhatsApp confirmation message
      - Email with Google Calendar .ics invite
      - Automatic calendar sync (if using Gmail/Google Calendar)

      Sales Team Receives:
      - Google Calendar event notification
      - HubSpot task notification (1 hour before appointment)
      - Chatwoot conversation update
```

---

## 3. FEATURE SPECIFICATIONS

### 3.1 FEATURE: Twilio WhatsApp Business API Integration

**Feature ID:** INT-001
**Priority:** P0 (Must-have - CRITICAL)
**Complexity:** Medium
**Owner:** Backend Expert + Integration Expert

#### Requirements

**REQ-001: Replace WAHA with Twilio**
- Remove WAHA container from Docker Compose
- Implement Twilio webhook endpoint: `/webhooks/twilio/whatsapp`
- Parse Twilio JSON format → internal message schema
- Send responses via Twilio API

**REQ-002: Webhook Security**
- Validate `X-Twilio-Signature` header (HMAC-SHA256)
- Reject requests with invalid signatures
- Log all signature validation attempts

**REQ-003: Message Format Handling**
- Support text messages
- Support media messages (images, documents, audio)
- Handle Twilio status callbacks (delivered, read, failed)

**REQ-004: Environment Configuration**
- Add `TWILIO_ACCOUNT_SID`
- Add `TWILIO_AUTH_TOKEN`
- Add `TWILIO_WHATSAPP_NUMBER`
- Remove WAHA environment variables

#### Acceptance Criteria

**AC-001:** Twilio webhook endpoint receives messages
**AC-002:** Signature validation blocks invalid requests
**AC-003:** Messages correctly parsed and sent to LangGraph
**AC-004:** Responses sent via Twilio API successfully
**AC-005:** Media messages handled correctly

#### Technical Specifications

**Twilio Client Implementation:**
```python
# app/integrations/twilio_client.py

import os
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from typing import Optional

class TwilioWhatsAppClient:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        self.client = Client(self.account_sid, self.auth_token)
        self.validator = RequestValidator(self.auth_token)

    def validate_request(self, url: str, post_vars: dict, signature: str) -> bool:
        """Validate Twilio webhook signature"""
        return self.validator.validate(url, post_vars, signature)

    def send_message(
        self,
        to: str,
        body: str,
        media_url: Optional[str] = None
    ) -> dict:
        """Send WhatsApp message via Twilio"""
        message_params = {
            "from_": f"whatsapp:{self.whatsapp_number}",
            "to": to if to.startswith("whatsapp:") else f"whatsapp:{to}",
            "body": body
        }

        if media_url:
            message_params["media_url"] = [media_url]

        message = self.client.messages.create(**message_params)

        return {
            "sid": message.sid,
            "status": message.status,
            "to": message.to,
            "from": message.from_
        }

    def parse_incoming_message(self, request_data: dict) -> dict:
        """Parse Twilio webhook data to internal schema"""
        return {
            "from_number": request_data.get("From", "").replace("whatsapp:", ""),
            "to_number": request_data.get("To", "").replace("whatsapp:", ""),
            "message_text": request_data.get("Body", ""),
            "message_sid": request_data.get("MessageSid"),
            "timestamp": request_data.get("Timestamp"),
            "num_media": int(request_data.get("NumMedia", 0)),
            "media_urls": [
                request_data.get(f"MediaUrl{i}")
                for i in range(int(request_data.get("NumMedia", 0)))
            ] if int(request_data.get("NumMedia", 0)) > 0 else []
        }
```

**Webhook Endpoint:**
```python
# app/api/webhooks.py

from fastapi import APIRouter, Request, HTTPException, Header
from app.integrations.twilio_client import TwilioWhatsAppClient
from app.orchestration.graph_builder import process_message
import logging

router = APIRouter()
twilio_client = TwilioWhatsAppClient()
logger = logging.getLogger(__name__)

@router.post("/webhooks/twilio/whatsapp")
async def twilio_whatsapp_webhook(
    request: Request,
    x_twilio_signature: str = Header(None)
):
    """
    Twilio WhatsApp webhook endpoint
    Receives incoming WhatsApp messages from Twilio
    """
    # Get request data
    form_data = await request.form()
    post_vars = dict(form_data)

    # Validate Twilio signature
    url = str(request.url)
    if not twilio_client.validate_request(url, post_vars, x_twilio_signature):
        logger.warning(f"Invalid Twilio signature from {post_vars.get('From')}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse incoming message
    message_data = twilio_client.parse_incoming_message(post_vars)

    logger.info(f"Received WhatsApp message from {message_data['from_number']}")

    # Send to Chatwoot (async background task)
    # TODO: Implement Chatwoot forwarding

    # Trigger LangGraph orchestration
    response = await process_message(message_data)

    # Send response via Twilio
    if response.get("reply_text"):
        twilio_client.send_message(
            to=message_data["from_number"],
            body=response["reply_text"]
        )

    return {"status": "success"}
```

---

### 3.2 FEATURE: HubSpot Free CRM Integration

**Feature ID:** INT-002
**Priority:** P0 (Must-have)
**Complexity:** High
**Owner:** Backend Expert + Integration Expert

#### Requirements

**REQ-005: HubSpot Account Setup**
- Create HubSpot Free CRM account
- Create private app for API access
- Configure API scopes: crm.objects.contacts, crm.objects.deals, crm.objects.tasks, crm.objects.notes
- Generate API key

**REQ-006: Custom Properties**
- Create contact custom properties:
  - `car_preference` (text)
  - `budget_range` (text)
  - `trade_in_car_model` (text)
  - `urgency_level` (dropdown: low, medium, high)
  - `lead_source` (default: "WhatsApp")
- Create deal custom properties:
  - `appointment_date` (datetime)
  - `test_drive_completed` (checkbox)
  - `financing_needed` (checkbox)

**REQ-007: Sales Pipeline Configuration**
- Create pipeline: "Car Sales"
- Create stages:
  - Inquiry
  - Qualified
  - Appointment Scheduled
  - Test Drive Completed
  - Negotiation
  - Closed Won
  - Closed Lost

**REQ-008: API Client Implementation**
- Implement HubSpot client wrapper
- Methods: create_contact, update_contact, create_deal, update_deal, create_note, create_task
- Rate limiting: 100 requests/10 seconds
- Error handling + retry logic (exponential backoff)

#### Acceptance Criteria

**AC-006:** HubSpot account configured with custom properties
**AC-007:** API client successfully creates contacts
**AC-008:** API client successfully creates deals with correct pipeline/stage
**AC-009:** API client successfully creates notes and tasks
**AC-010:** Rate limiting prevents API quota exceeded errors

#### Technical Specifications

**HubSpot Client Implementation:**
```python
# app/integrations/hubspot_client.py

import os
import requests
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class HubSpotClient:
    def __init__(self):
        self.api_key = os.getenv("HUBSPOT_API_KEY")
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.rate_limit_delay = 0.1  # 100ms between requests (max 100/10s)
        self.last_request_time = 0

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retries: int = 3
    ) -> Dict:
        """Make HTTP request with rate limiting and retry logic"""
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)

        url = f"{self.base_url}{endpoint}"

        for attempt in range(retries):
            try:
                self.last_request_time = time.time()

                if method == "GET":
                    response = requests.get(url, headers=self.headers, params=params)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers, json=data)
                elif method == "PATCH":
                    response = requests.patch(url, headers=self.headers, json=data)
                elif method == "DELETE":
                    response = requests.delete(url, headers=self.headers)

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit exceeded
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"HubSpot rate limit hit, waiting {wait_time}s")
                    time.sleep(wait_time)
                elif e.response.status_code >= 500:  # Server error
                    if attempt < retries - 1:
                        logger.warning(f"HubSpot server error, retry {attempt + 1}/{retries}")
                        time.sleep(1)
                    else:
                        raise
                else:
                    raise

            except requests.exceptions.RequestException as e:
                logger.error(f"HubSpot request failed: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                else:
                    raise

        raise Exception("Max retries exceeded")

    def create_contact(
        self,
        firstname: str,
        lastname: str,
        phone: str,
        email: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> Dict:
        """Create HubSpot contact"""
        contact_properties = {
            "firstname": firstname,
            "lastname": lastname,
            "phone": phone,
        }

        if email:
            contact_properties["email"] = email

        if properties:
            contact_properties.update(properties)

        data = {"properties": contact_properties}

        response = self._make_request("POST", "/crm/v3/objects/contacts", data=data)

        logger.info(f"Created HubSpot contact: {response['id']}")
        return response

    def update_contact(self, contact_id: str, properties: Dict) -> Dict:
        """Update HubSpot contact properties"""
        data = {"properties": properties}
        response = self._make_request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", data=data)

        logger.info(f"Updated HubSpot contact: {contact_id}")
        return response

    def create_deal(
        self,
        dealname: str,
        pipeline: str,
        dealstage: str,
        amount: Optional[float] = None,
        contact_id: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> Dict:
        """Create HubSpot deal"""
        deal_properties = {
            "dealname": dealname,
            "pipeline": pipeline,
            "dealstage": dealstage
        }

        if amount:
            deal_properties["amount"] = str(amount)

        if properties:
            deal_properties.update(properties)

        data = {"properties": deal_properties}

        # Add contact association if provided
        if contact_id:
            data["associations"] = [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 3  # Contact to Deal
                        }
                    ]
                }
            ]

        response = self._make_request("POST", "/crm/v3/objects/deals", data=data)

        logger.info(f"Created HubSpot deal: {response['id']}")
        return response

    def update_deal(self, deal_id: str, properties: Dict) -> Dict:
        """Update HubSpot deal properties"""
        data = {"properties": properties}
        response = self._make_request("PATCH", f"/crm/v3/objects/deals/{deal_id}", data=data)

        logger.info(f"Updated HubSpot deal: {deal_id}")
        return response

    def create_note(
        self,
        content: str,
        object_id: str,
        object_type: str = "deal"  # "contact", "deal", "company"
    ) -> Dict:
        """Create HubSpot note associated with object"""
        note_properties = {
            "hs_note_body": content,
            "hs_timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Association type IDs:
        # Contact: 202, Deal: 214, Company: 190
        association_type_map = {
            "contact": 202,
            "deal": 214,
            "company": 190
        }

        data = {
            "properties": note_properties,
            "associations": [
                {
                    "to": {"id": object_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": association_type_map[object_type]
                        }
                    ]
                }
            ]
        }

        response = self._make_request("POST", "/crm/v3/objects/notes", data=data)

        logger.info(f"Created HubSpot note for {object_type} {object_id}")
        return response

    def create_task(
        self,
        subject: str,
        body: str,
        due_date: datetime,
        priority: str = "MEDIUM",  # LOW, MEDIUM, HIGH
        associated_deal_id: Optional[str] = None
    ) -> Dict:
        """Create HubSpot task"""
        task_properties = {
            "hs_task_subject": subject,
            "hs_task_body": body,
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": priority,
            "hs_timestamp": due_date.isoformat() + "Z"
        }

        data = {"properties": task_properties}

        # Add deal association if provided
        if associated_deal_id:
            data["associations"] = [
                {
                    "to": {"id": associated_deal_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 216  # Deal to Task
                        }
                    ]
                }
            ]

        response = self._make_request("POST", "/crm/v3/objects/tasks", data=data)

        logger.info(f"Created HubSpot task: {response['id']}")
        return response
```

---

### 3.3 FEATURE: Google Calendar Integration

**Feature ID:** INT-003
**Priority:** P0 (Must-have)
**Complexity:** Medium
**Owner:** Backend Expert + Integration Expert

#### Requirements

**REQ-009: Google Cloud Setup**
- Create Google Cloud Project
- Enable Google Calendar API
- Create service account with Calendar API access
- Download service account JSON key file

**REQ-010: Shared Calendar Configuration**
- Create shared calendar: "Seldenrijk Test Drives"
- Share with service account (Manager role)
- Share with sales team (View + Edit role)

**REQ-011: API Client Implementation**
- Implement Google Calendar client wrapper
- Methods: check_availability, create_event, update_event, delete_event, get_event
- Timezone handling: Europe/Amsterdam
- Conflict detection (double booking prevention)
- Email invite sending

#### Acceptance Criteria

**AC-011:** Service account can access shared calendar
**AC-012:** API client successfully checks availability
**AC-013:** API client successfully creates calendar events
**AC-014:** Email invites sent to customers
**AC-015:** Conflict detection prevents double bookings

#### Technical Specifications

**Google Calendar Client Implementation:**
```python
# app/integrations/google_calendar_client.py

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
import logging

logger = logging.getLogger(__name__)

class GoogleCalendarClient:
    def __init__(self):
        # Load service account credentials
        credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        credentials_dict = json.loads(credentials_json)

        self.credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.timezone = pytz.timezone("Europe/Amsterdam")

    def check_availability(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60
    ) -> List[Dict]:
        """
        Check calendar availability for given date range
        Returns list of available time slots
        """
        try:
            # Get existing events in range
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            existing_events = events_result.get('items', [])

            # Generate all possible slots (e.g., every hour from 10am-6pm)
            available_slots = []
            current = start_date

            while current < end_date:
                slot_end = current + timedelta(minutes=duration_minutes)

                # Check if slot conflicts with existing events
                is_available = True
                for event in existing_events:
                    event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                    event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))

                    # Check overlap
                    if (current < event_end and slot_end > event_start):
                        is_available = False
                        break

                if is_available:
                    available_slots.append({
                        "start": current,
                        "end": slot_end
                    })

                # Move to next slot (e.g., next hour)
                current += timedelta(hours=1)

            logger.info(f"Found {len(available_slots)} available slots")
            return available_slots

        except HttpError as error:
            logger.error(f"Calendar availability check failed: {error}")
            raise

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict:
        """
        Create calendar event with email invites
        """
        try:
            # Ensure times are timezone-aware
            if start_time.tzinfo is None:
                start_time = self.timezone.localize(start_time)
            if end_time.tzinfo is None:
                end_time = self.timezone.localize(end_time)

            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Amsterdam'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Amsterdam'
                },
                'attendees': [
                    {'email': email} for email in attendees
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},
                        {'method': 'popup', 'minutes': 30}
                    ]
                },
                'sendUpdates': 'all'  # Send email invites to attendees
            }

            if description:
                event['description'] = description

            if location:
                event['location'] = location

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            logger.info(f"Created calendar event: {created_event['id']}")
            return created_event

        except HttpError as error:
            logger.error(f"Calendar event creation failed: {error}")
            raise

    def update_event(self, event_id: str, updates: Dict) -> Dict:
        """Update existing calendar event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            # Apply updates
            event.update(updates)
            event['sendUpdates'] = 'all'  # Notify attendees of changes

            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Updated calendar event: {event_id}")
            return updated_event

        except HttpError as error:
            logger.error(f"Calendar event update failed: {error}")
            raise

    def delete_event(self, event_id: str) -> None:
        """Delete calendar event"""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
                sendUpdates='all'  # Notify attendees of cancellation
            ).execute()

            logger.info(f"Deleted calendar event: {event_id}")

        except HttpError as error:
            logger.error(f"Calendar event deletion failed: {error}")
            raise

    def get_event(self, event_id: str) -> Dict:
        """Get calendar event details"""
        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            return event

        except HttpError as error:
            logger.error(f"Get calendar event failed: {error}")
            raise
```

---

## 4. DATABASE DESIGN

### 4.1 New Tables

**Table: `calendar_events`**
```sql
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    lead_id INT REFERENCES leads(id),
    calendar_event_id VARCHAR(255) NOT NULL,  -- Google Calendar event ID
    event_type VARCHAR(50) NOT NULL,  -- 'test_drive', 'viewing', 'consultation'
    car_model VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    location TEXT,
    attendees JSONB,  -- Array of email addresses
    status VARCHAR(50) DEFAULT 'scheduled',  -- 'scheduled', 'completed', 'cancelled', 'no_show'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_calendar_events_lead_id ON calendar_events(lead_id);
CREATE INDEX idx_calendar_events_start_time ON calendar_events(start_time);
CREATE INDEX idx_calendar_events_status ON calendar_events(status);
```

**Table: `integrations_log`**
```sql
CREATE TABLE integrations_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_id VARCHAR(255),  -- WhatsApp message SID
    conversation_id INT,  -- Internal conversation ID
    hubspot_contact_id VARCHAR(255),
    hubspot_deal_id VARCHAR(255),
    calendar_event_id VARCHAR(255),
    chatwoot_conversation_id INT,
    action_type VARCHAR(100),  -- 'create_contact', 'create_deal', 'create_event', etc.
    status VARCHAR(50),  -- 'success', 'failed', 'partial'
    error_message TEXT,
    api_response JSONB,  -- Full API response for debugging
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_integrations_log_message_id ON integrations_log(message_id);
CREATE INDEX idx_integrations_log_timestamp ON integrations_log(timestamp);
CREATE INDEX idx_integrations_log_status ON integrations_log(status);
```

### 4.2 Updated Tables

**Table: `leads` (add HubSpot fields)**
```sql
ALTER TABLE leads ADD COLUMN hubspot_contact_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN hubspot_deal_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN last_hubspot_sync TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_leads_hubspot_contact_id ON leads(hubspot_contact_id);
CREATE INDEX idx_leads_hubspot_deal_id ON leads(hubspot_deal_id);
```

---

## 5. IMPLEMENTATION ROADMAP

### Week 1: Twilio Migration
- **Day 1-2**: Twilio setup, webhook endpoint, signature validation
- **Day 3**: Docker updates, environment configuration
- **Deliverable**: WAHA fully replaced, Twilio working end-to-end

### Week 2: HubSpot CRM Integration
- **Day 4-5**: HubSpot setup, API client, custom properties
- **Day 6-7**: Enhanced CRM Agent implementation
- **Deliverable**: HubSpot contact + deal creation working

### Week 3: Google Calendar Integration
- **Day 8-9**: Google Cloud setup, Calendar API client
- **Day 10-11**: CRM Agent calendar logic, appointment flow
- **Deliverable**: Automated appointment scheduling working

### Week 4: Testing & Documentation
- **Day 12-13**: End-to-end testing, load testing, security audit
- **Day 14**: Documentation updates, production deployment
- **Deliverable**: System fully tested and deployed

**Total Duration**: 4 weeks (26 working days)
**Estimated Effort**: 80-100 hours

---

## 6. TESTING STRATEGY

### 6.1 Unit Tests

**Twilio Client:**
- Test signature validation (valid/invalid signatures)
- Test message parsing (text, media messages)
- Test send_message (success, failures, retries)

**HubSpot Client:**
- Test create_contact, update_contact
- Test create_deal, update_deal
- Test create_note, create_task
- Test rate limiting (100 req/10s)
- Test retry logic (exponential backoff)

**Google Calendar Client:**
- Test check_availability (multiple scenarios)
- Test create_event (with attendees, location, reminders)
- Test update_event, delete_event
- Test timezone handling
- Test conflict detection

### 6.2 Integration Tests

**End-to-End Flows:**
1. **Car Inquiry → HubSpot Contact + Deal**
   - Send WhatsApp message: "I'm interested in BMW X5"
   - Verify HubSpot contact created
   - Verify HubSpot deal created with correct stage
   - Verify custom properties populated

2. **Appointment Request → Calendar Event + HubSpot Update**
   - Send WhatsApp message: "I'd like to schedule a test drive"
   - Verify Google Calendar event created
   - Verify email invite sent
   - Verify HubSpot deal updated to "Appointment Scheduled"
   - Verify HubSpot task created

3. **Trade-In Inquiry → HubSpot Property Update**
   - Send WhatsApp message: "I want to trade in my old car"
   - Verify HubSpot contact property `trade_in_car_model` updated

### 6.3 Load Testing

- Simulate 100 messages/minute
- Verify HubSpot rate limits respected (100 req/10s)
- Verify Google Calendar API limits respected
- Check for dropped messages or failed integrations

### 6.4 Security Testing

- Test Twilio signature validation with invalid signatures
- Test unauthorized access to webhook endpoint
- Verify API keys stored securely (environment variables)
- Test HTTPS for all API calls

---

## 7. DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Twilio account verified and WhatsApp number configured
- [ ] HubSpot Free CRM account created with custom properties
- [ ] Google Cloud Project created with Calendar API enabled
- [ ] Service account JSON key file downloaded
- [ ] Shared calendar "Seldenrijk Test Drives" created and shared
- [ ] All environment variables documented in `.env.example`
- [ ] Database migrations prepared and tested on staging

### Deployment

- [ ] Deploy to Railway staging environment
- [ ] Update Twilio webhook URL (staging URL)
- [ ] Run database migrations on staging
- [ ] Test end-to-end flows on staging
- [ ] Fix any issues found during staging testing
- [ ] Deploy to Railway production environment
- [ ] Update Twilio webhook URL (production URL)
- [ ] Run database migrations on production
- [ ] Configure environment variables in Railway production
- [ ] Monitor logs for 24 hours

### Post-Deployment

- [ ] Verify first real customer message processed correctly
- [ ] Check HubSpot data accuracy
- [ ] Check Google Calendar events created correctly
- [ ] Monitor error rates and API failures
- [ ] Train sales team on HubSpot pipeline usage
- [ ] Document any issues encountered and resolutions

---

## 8. SUCCESS METRICS

### Technical KPIs

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Uptime | 99.95% | TBD | 📊 TO MEASURE |
| Response Time | <2s | TBD | 📊 TO MEASURE |
| Message Delivery Rate | 100% | TBD | 📊 TO MEASURE |
| API Error Rate | <1% | TBD | 📊 TO MEASURE |

### Business KPIs

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Cost Savings | €900/year | €0 | 📊 PENDING |
| Lead Conversion Rate | +20-30% | TBD | 📊 TO MEASURE |
| Appointment Booking Time | 95% faster | TBD | 📊 TO MEASURE |
| Lead Data Capture | 100% | TBD | 📊 TO MEASURE |
| Sales Team Satisfaction | 4.5/5 stars | TBD | 📊 TO MEASURE |

---

## 9. COST ANALYSIS

### Current State (WAHA Only)

```
Monthly Costs:
- WAHA: €135/month
- Chatwoot: €0 (self-hosted)
- PostgreSQL (Supabase): €25/month
- Railway hosting: €20/month

Total: €180/month
```

### Future State (Twilio + HubSpot + Calendar)

```
Monthly Costs:
- Twilio WhatsApp: €60 base + (12,000 × €0.0042) = €110.40/month
- HubSpot Free CRM: €0/month
- Google Calendar API: €0/month
- Chatwoot: €0 (self-hosted)
- PostgreSQL (Supabase): €25/month
- Railway hosting: €20/month

Total: €155.40/month

Monthly Savings: €180 - €155.40 = €24.60/month
Annual Savings: €24.60 × 12 = €295.20/year
```

**ROI Timeline:**
- Implementation cost: 80-100 hours × €100/hour = €8,000-€10,000
- Annual savings: €295/year + increased revenue from better lead management
- Break-even: 3-4 months (with 20-30% conversion improvement)
- Year 1 ROI: 50-100% (factoring in increased sales)

---

## 10. RISK ASSESSMENT

### High-Risk Items

1. **Twilio WhatsApp Business Approval Delay**
   - **Risk**: WhatsApp Business approval can take 1-3 days
   - **Mitigation**: Apply early, use sandbox for testing
   - **Contingency**: Keep WAHA running until Twilio approved

2. **Google Calendar Shared Calendar Access**
   - **Risk**: Service account permissions misconfigured
   - **Mitigation**: Test calendar access thoroughly before production
   - **Contingency**: Manual calendar management if API fails

### Medium-Risk Items

3. **HubSpot API Rate Limits**
   - **Risk**: 100 requests/10 seconds might be exceeded with high volume
   - **Mitigation**: Implement rate limiting and queuing in client
   - **Contingency**: Batch API calls, use webhooks for real-time updates

4. **Data Migration from WAHA to Twilio**
   - **Risk**: Historical message format incompatibility
   - **Mitigation**: Keep WAHA data archived, only use Twilio for new messages
   - **Contingency**: Export WAHA data before shutdown

### Low-Risk Items

5. **Email Delivery for Calendar Invites**
   - **Risk**: Calendar invites might go to spam
   - **Mitigation**: Use verified email domain (sales@seldenrijk.nl)
   - **Contingency**: Send WhatsApp confirmation message as backup

---

## 11. APPROVAL & SIGN-OFF

**Project Owner:** Seldenrijk Auto + SDK AGENTS Framework Team
**Approval Date:** 2025-10-24
**Status:** ✅ READY FOR IMPLEMENTATION

**Approved By:**
- Solution Architecture Expert: ✅ Approved
- Backend Expert: ✅ Approved
- Integration Expert: ✅ Approved
- Database Expert: ✅ Approved
- DevOps Expert: ✅ Approved

**Next Steps:**
1. Begin Week 1: Twilio Migration
2. Daily progress updates
3. Weekly demos of completed features
4. Final deployment after Week 4 testing

---

## 12. APPENDICES

### Appendix A: Environment Variables

```bash
# Twilio WhatsApp Business API
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=+31850000000

# HubSpot Free CRM
HUBSPOT_API_KEY=pat-na1-...

# Google Calendar API
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
GOOGLE_CALENDAR_ID=primary  # or specific shared calendar ID

# Existing (keep)
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
CHATWOOT_URL=...
CHATWOOT_TOKEN=...
```

### Appendix B: API Rate Limits

| Service | Rate Limit | Mitigation |
|---------|------------|-----------|
| Twilio WhatsApp | 600 messages/min | Queueing system |
| HubSpot REST API | 100 requests/10s | Rate limiting + backoff |
| Google Calendar API | 500 queries/100s | Caching + batching |
| Chatwoot | No strict limit | N/A |

### Appendix C: Webhook URLs

```
Production:
- Twilio Webhook: https://seldenrijk-whatsapp.up.railway.app/webhooks/twilio/whatsapp

Staging:
- Twilio Webhook: https://seldenrijk-whatsapp-staging.up.railway.app/webhooks/twilio/whatsapp
```

---

**🎯 PRD Complete! Ready for Implementation.**

**Version:** 2.0.0
**Status:** ✅ VALIDATED
**Timeline:** 4 weeks (26 days)
**Effort:** 80-100 hours
**Savings:** €295/year + increased revenue from better lead management
