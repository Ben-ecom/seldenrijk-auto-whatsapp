# Chatwoot API - Comprehensive Technical Reference

**Document Version:** 1.0
**Last Updated:** 2025-10-16
**API Base URL:** `https://app.chatwoot.com/`
**Official Documentation:** https://developers.chatwoot.com/api-reference/introduction

---

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limits & Best Practices](#rate-limits--best-practices)
3. [Tags Management API](#tags-management-api)
4. [Conversation Notes API](#conversation-notes-api)
5. [Custom Attributes API](#custom-attributes-api)
6. [Team Assignment & Escalation](#team-assignment--escalation)
7. [Webhooks & Events](#webhooks--events)
8. [Status & Priority Management](#status--priority-management)
9. [Common Response Codes](#common-response-codes)
10. [Code Examples](#code-examples)

---

## Authentication

### Authentication Methods

Chatwoot supports three types of authentication:

#### 1. Application APIs (User API Key)
- **Use Case:** General API access for managing conversations, contacts, etc.
- **Token Type:** User `access_token`
- **How to Obtain:** Profile Settings → Access Token (after logging into Chatwoot)
- **Header Name:** `api_access_token`
- **Available On:** Cloud and Self-hosted installations

#### 2. Client APIs
- **Use Case:** Building custom chat interfaces
- **Requires:**
  - `inbox_identifier` (from Settings → Configuration in API inboxes)
  - `contact_identifier` (returned when creating a contact)
- **Available On:** Cloud and Self-hosted installations

#### 3. Platform APIs
- **Use Case:** Administrative control for installations
- **Token Type:** Platform App `access_token`
- **How to Obtain:** Generated in Super Admin Console
- **Available On:** Self-hosted/Managed Hosting only
- **Limitation:** Can only access accounts, users, and objects created by the specific platform API key

### Authentication Header Format

```bash
-H "api_access_token: YOUR_API_TOKEN"
-H "Content-Type: application/json"
```

---

## Rate Limits & Best Practices

### Default Rate Limits

Chatwoot enforces the following rate limits using the `rack_attack` gem:

| Request Type | Limit | Time Window | Tracking Method |
|--------------|-------|-------------|-----------------|
| General API Requests | 60 requests | Per minute | By IP address |
| Signup Requests | 5 requests | Per 5 minutes | By IP address |
| Signin Requests (per IP) | 5 requests | Per 20 seconds | By IP address |
| Signin Requests (per email) | 20 requests | Per 5 minutes | By email |
| Reset Password | 5 requests | Per hour | By email |

### Configuration Environment Variables

```bash
ENABLE_RACK_ATTACK=true              # Enable/disable rate limiter
RACK_ATTACK_LIMIT=60                 # Requests per minute
ENABLE_RACK_ATTACK_WIDGET_API=true   # Control widget API rate limiting
```

### Best Practices

1. **Implement Exponential Backoff:** When receiving 429 responses, wait progressively longer between retries
2. **Batch Operations:** Group multiple operations where possible to reduce API calls
3. **Cache Responses:** Store frequently accessed data locally to minimize redundant requests
4. **Monitor Rate Limit Headers:** Check response headers for rate limit information
5. **Use Webhooks:** Instead of polling for updates, subscribe to webhook events
6. **Handle 429 Errors Gracefully:** Implement proper error handling with retry logic

### Rate Limit Error Response

```json
{
  "error": "Rate limit exceeded",
  "status": 429,
  "retry_after": 60
}
```

---

## Tags Management API

### Overview
Tags (also called Labels in Chatwoot) are used for categorizing and segmenting conversations and contacts. Tags enable lead qualification, workflow management, and reporting.

### 1. Add Labels to Conversation

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/labels`

**Important:** This API **overwrites** the existing list of labels. Always include all labels you want to keep.

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `conversation_id` (integer, path, required): Numeric ID of the conversation

**Request Body:**
```json
{
  "labels": ["support", "billing", "priority", "new-lead"]
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/labels \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "labels": ["support", "billing"]
  }'
```

**Success Response (200):**
```json
{
  "payload": ["support", "billing"]
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing API token
- `404 Not Found`: Conversation does not exist

---

### 2. List Conversation Labels

**Endpoint:** `GET /api/v1/accounts/{account_id}/conversations/{conversation_id}/labels`

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `conversation_id` (integer, path, required): Numeric ID of the conversation

**Example cURL:**
```bash
curl --request GET \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/labels \
  --header 'api_access_token: YOUR_TOKEN'
```

**Success Response (200):**
```json
["support", "billing", "priority"]
```

---

### 3. Add Labels to Contact

**Endpoint:** `POST /api/v1/accounts/{account_id}/contacts/{contact_id}/labels`

**Important:** This API **overwrites** the existing list of labels for the contact.

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `contact_id` (integer, path, required): ID of the contact

**Request Body:**
```json
{
  "labels": ["vip-customer", "enterprise", "onboarding"]
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/contacts/789/labels \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "labels": ["vip-customer", "enterprise"]
  }'
```

**Success Response (200):**
```json
{
  "payload": {
    "id": 789,
    "name": "John Doe",
    "labels": ["vip-customer", "enterprise"]
  }
}
```

---

### 4. Filter Conversations by Labels

**Endpoint:** `GET /api/v1/accounts/{account_id}/conversations`

**Query Parameters:**
- `labels[]` (array of strings): Filter by one or more labels
- `status` (string): Filter by status (open, resolved, pending, snoozed)

**Example cURL:**
```bash
curl --request GET \
  --url 'https://app.chatwoot.com/api/v1/accounts/123/conversations?labels[]=support&labels[]=priority&status=open' \
  --header 'api_access_token: YOUR_TOKEN'
```

---

### Best Practices for Tag-Based Lead Segmentation

1. **Use Consistent Naming:** Establish a standard naming convention (e.g., lowercase, hyphen-separated)
2. **Create a Tag Taxonomy:** Define categories like:
   - Lead Stage: `new-lead`, `qualified`, `nurturing`, `closed-won`, `closed-lost`
   - Priority: `urgent`, `high-priority`, `standard`
   - Department: `sales`, `support`, `billing`
   - Product Interest: `product-a`, `product-b`, `enterprise-plan`
3. **Automate Tagging:** Use automation rules to add tags based on message content or user behavior
4. **Avoid Over-Tagging:** Keep tags focused and relevant (5-7 tags max per conversation)
5. **Regular Cleanup:** Periodically review and consolidate unused or redundant tags

---

## Conversation Notes API

### Overview
Conversation notes (private messages) are internal comments visible only to agents. They are perfect for:
- Internal discussion about customer issues
- Handoff notes between agents
- Recording research or decision-making context
- Lead qualification notes

### 1. Create a Private Note

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages`

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `conversation_id` (integer, path, required): Numeric ID of the conversation

**Request Body:**
```json
{
  "content": "Customer mentioned interest in enterprise plan. Follow up next week.",
  "message_type": "outgoing",
  "private": true,
  "content_type": "text"
}
```

**Field Descriptions:**
- `content` (string, required): The note text
- `message_type` (enum, required): Use `"outgoing"` for agent messages
  - Options: `incoming`, `outgoing`
- `private` (boolean, required): Set to `true` for internal notes, `false` for customer-visible messages
- `content_type` (enum, optional): Defaults to `"text"`
  - Options: `text`, `input_email`, `cards`, `input_select`, `form`, `article`

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/messages \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "content": "Customer shows high intent. Pricing discussion scheduled for tomorrow.",
    "message_type": "outgoing",
    "private": true
  }'
```

**Success Response (200):**
```json
{
  "id": 12345,
  "content": "Customer shows high intent. Pricing discussion scheduled for tomorrow.",
  "message_type": "outgoing",
  "private": true,
  "created_at": 1697472000,
  "sender": {
    "id": 1,
    "name": "Agent Name",
    "email": "agent@example.com"
  }
}
```

---

### 2. Create a Public Message (Customer-Visible)

**Request Body:**
```json
{
  "content": "Thanks for contacting us! How can I help you today?",
  "message_type": "outgoing",
  "private": false
}
```

---

### 3. Retrieve Messages (Including Notes)

**Endpoint:** `GET /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages`

**Example cURL:**
```bash
curl --request GET \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/messages \
  --header 'api_access_token: YOUR_TOKEN'
```

**Success Response (200):**
```json
{
  "meta": {
    "mine_count": 5,
    "unassigned_count": 2
  },
  "payload": [
    {
      "id": 12345,
      "content": "Internal note content",
      "message_type": "outgoing",
      "private": true,
      "created_at": 1697472000,
      "sender": {
        "id": 1,
        "name": "Agent Name"
      }
    },
    {
      "id": 12346,
      "content": "Customer-visible message",
      "message_type": "outgoing",
      "private": false,
      "created_at": 1697472100,
      "sender": {
        "id": 1,
        "name": "Agent Name"
      }
    }
  ]
}
```

---

### Note Formatting and Metadata

#### Markdown Support
Chatwoot supports basic Markdown formatting in notes:
```json
{
  "content": "**Important:** Customer requires enterprise security features:\n- SSO integration\n- Custom domain\n- Dedicated support",
  "private": true,
  "message_type": "outgoing"
}
```

#### Mentioning Agents
Use `@` mentions to notify other agents:
```json
{
  "content": "@john Please follow up on the pricing discussion",
  "private": true,
  "message_type": "outgoing"
}
```

---

### Best Practices for Notes

1. **Use Templates:** Create standardized note formats for common scenarios
2. **Document Decisions:** Record why certain actions were taken
3. **Handoff Protocol:** Always add notes when reassigning conversations
4. **Lead Qualification:** Use structured notes format for lead scoring
5. **Time-Sensitive Info:** Include deadlines or follow-up dates in notes
6. **Privacy First:** Never include sensitive customer data (passwords, payment info) in notes

---

## Custom Attributes API

### Overview
Custom attributes allow you to store additional structured data on contacts and conversations beyond standard fields. They require definition before use.

### Attribute Types

| Type | Code | Description | Example Use Case |
|------|------|-------------|------------------|
| Text | 0 | Free-form text | Company name, job title |
| Number | 1 | Numeric values | Deal value, employee count |
| Currency | 2 | Monetary amounts | Contract value, MRR |
| Percent | 3 | Percentage values | Discount rate, completion |
| Link | 4 | URLs | LinkedIn profile, website |
| Date | 5 | Date values | Contract end date, next follow-up |
| List | 6 | Dropdown selection | Industry, plan tier |
| Checkbox | 7 | Boolean true/false | Newsletter opt-in, trial user |

---

### 1. Create Custom Attribute Definition

**Endpoint:** `POST /api/v1/accounts/{account_id}/custom_attribute_definitions`

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account

**Request Body:**
```json
{
  "attribute_display_name": "Lead Score",
  "attribute_display_type": 1,
  "attribute_description": "Numerical score for lead qualification (0-100)",
  "attribute_key": "lead_score",
  "attribute_model": 0,
  "regex_pattern": "^[0-9]{1,3}$",
  "regex_cue": "Please enter a number between 0 and 100"
}
```

**Field Descriptions:**
- `attribute_display_name` (string, required): Human-readable name shown in UI
- `attribute_display_type` (integer, required): Type code (see table above)
- `attribute_description` (string, optional): Help text for agents
- `attribute_key` (string, required): Unique identifier (use snake_case)
- `attribute_model` (integer, required):
  - `0` = Conversation attribute
  - `1` = Contact attribute
- `attribute_values` (array, optional): For list types, predefined options
- `regex_pattern` (string, optional): Validation pattern for text attributes
- `regex_cue` (string, optional): Error message for failed validation

**Example - List Type Attribute:**
```json
{
  "attribute_display_name": "Industry",
  "attribute_display_type": 6,
  "attribute_description": "Customer industry vertical",
  "attribute_key": "industry",
  "attribute_model": 1,
  "attribute_values": [
    "Technology",
    "Healthcare",
    "Finance",
    "Retail",
    "Manufacturing",
    "Other"
  ]
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/custom_attribute_definitions \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "attribute_display_name": "Deal Value",
    "attribute_display_type": 2,
    "attribute_key": "deal_value",
    "attribute_model": 0
  }'
```

**Success Response (200):**
```json
{
  "id": 42,
  "attribute_display_name": "Deal Value",
  "attribute_display_type": 2,
  "attribute_key": "deal_value",
  "attribute_model": 0,
  "created_at": "2025-10-16T10:30:00.000Z"
}
```

---

### 2. Update Conversation Custom Attributes

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/custom_attributes`

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `conversation_id` (integer, path, required): Numeric ID of the conversation

**Request Body:**
```json
{
  "custom_attributes": {
    "lead_score": 85,
    "deal_value": 50000,
    "industry": "Technology",
    "next_follow_up": "2025-10-20"
  }
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/custom_attributes \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "custom_attributes": {
      "lead_score": 85,
      "deal_value": 50000
    }
  }'
```

**Success Response (200):**
```json
{
  "custom_attributes": {
    "lead_score": 85,
    "deal_value": 50000,
    "industry": "Technology",
    "next_follow_up": "2025-10-20"
  }
}
```

---

### 3. Update Contact Custom Attributes

**Endpoint:** `PATCH /api/v1/accounts/{account_id}/contacts/{contact_id}`

**Request Body:**
```json
{
  "custom_attributes": {
    "company_size": "51-200",
    "linkedin_profile": "https://linkedin.com/in/johndoe",
    "newsletter_subscribed": true
  }
}
```

**Example cURL:**
```bash
curl --request PATCH \
  --url https://app.chatwoot.com/api/v1/accounts/123/contacts/789 \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "custom_attributes": {
      "company_size": "51-200",
      "newsletter_subscribed": true
    }
  }'
```

---

### 4. List Custom Attribute Definitions

**Endpoint:** `GET /api/v1/accounts/{account_id}/custom_attribute_definitions`

**Query Parameters:**
- `attribute_model` (integer, optional): Filter by model type (0 or 1)

**Example cURL:**
```bash
curl --request GET \
  --url 'https://app.chatwoot.com/api/v1/accounts/123/custom_attribute_definitions?attribute_model=0' \
  --header 'api_access_token: YOUR_TOKEN'
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "attribute_display_name": "Lead Score",
    "attribute_display_type": 1,
    "attribute_key": "lead_score",
    "attribute_model": 0
  },
  {
    "id": 2,
    "attribute_display_name": "Industry",
    "attribute_display_type": 6,
    "attribute_key": "industry",
    "attribute_model": 1,
    "attribute_values": ["Technology", "Healthcare", "Finance"]
  }
]
```

---

### 5. Delete Custom Attribute Definition

**Endpoint:** `DELETE /api/v1/accounts/{account_id}/custom_attribute_definitions/{id}`

**Example cURL:**
```bash
curl --request DELETE \
  --url https://app.chatwoot.com/api/v1/accounts/123/custom_attribute_definitions/42 \
  --header 'api_access_token: YOUR_TOKEN'
```

---

### Data Types and Validation

#### Text Attributes with Regex Validation
```json
{
  "attribute_display_name": "Phone Number",
  "attribute_display_type": 0,
  "attribute_key": "phone",
  "attribute_model": 1,
  "regex_pattern": "^\\+?[1-9]\\d{1,14}$",
  "regex_cue": "Please enter a valid international phone number"
}
```

#### Date Attributes
Store dates as ISO 8601 strings:
```json
{
  "custom_attributes": {
    "contract_end_date": "2026-12-31",
    "last_contact": "2025-10-16"
  }
}
```

#### Boolean (Checkbox) Attributes
```json
{
  "custom_attributes": {
    "is_enterprise": true,
    "newsletter_subscribed": false
  }
}
```

---

### Best Practices

1. **Plan Your Schema:** Define all attributes before implementation
2. **Use Descriptive Keys:** Use clear, self-documenting attribute keys
3. **Validation Rules:** Add regex patterns for text fields that need validation
4. **List vs Text:** Use list type for limited, predefined options
5. **Contact vs Conversation:** Store persistent data on contacts, temporary data on conversations
6. **Default Values:** Document expected defaults when attributes are missing
7. **Data Cleanup:** Periodically audit and remove unused custom attributes

---

## Team Assignment & Escalation

### Overview
Team assignment allows routing conversations to specific groups of agents. This is essential for:
- Department-based routing (Sales, Support, Technical)
- Skill-based assignment
- Escalation workflows
- Load balancing

---

### 1. Assign Conversation to Agent or Team

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/assignments`

**Parameters:**
- `account_id` (integer, path, required): Numeric ID of the account
- `conversation_id` (integer, path, required): Numeric ID of the conversation

**Request Body:**
```json
{
  "assignee_id": 5,
  "team_id": 2
}
```

**Field Descriptions:**
- `assignee_id` (integer, optional): ID of the agent to assign
- `team_id` (integer, optional): ID of the team to assign
- **Note:** If `assignee_id` is present, `team_id` is ignored

**Example cURL - Assign to Agent:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/assignments \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "assignee_id": 5
  }'
```

**Example cURL - Assign to Team:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/assignments \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "team_id": 2
  }'
```

**Success Response (200):**
```json
{
  "id": 5,
  "name": "John Smith",
  "email": "john@example.com",
  "account_id": 123,
  "role": "agent",
  "confirmed": true
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid API token
- `404 Not Found`: Conversation, agent, or team not found

---

### 2. Create Team

**Endpoint:** `POST /api/v1/accounts/{account_id}/teams`

**Request Body:**
```json
{
  "name": "Enterprise Sales Team",
  "description": "Handles enterprise and high-value customers",
  "allow_auto_assign": true
}
```

**Field Descriptions:**
- `name` (string, required): Team name
- `description` (string, optional): Team description
- `allow_auto_assign` (boolean, optional): Enable automatic agent assignment within team

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/teams \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "name": "Support Team",
    "allow_auto_assign": true
  }'
```

**Success Response (200):**
```json
{
  "id": 2,
  "name": "Support Team",
  "description": "",
  "allow_auto_assign": true,
  "account_id": 123
}
```

---

### 3. List All Teams

**Endpoint:** `GET /api/v1/accounts/{account_id}/teams`

**Example cURL:**
```bash
curl --request GET \
  --url https://app.chatwoot.com/api/v1/accounts/123/teams \
  --header 'api_access_token: YOUR_TOKEN'
```

**Success Response (200):**
```json
[
  {
    "id": 1,
    "name": "Sales Team",
    "allow_auto_assign": true
  },
  {
    "id": 2,
    "name": "Support Team",
    "allow_auto_assign": false
  }
]
```

---

### 4. Add Agent to Team

**Endpoint:** `POST /api/v1/accounts/{account_id}/teams/{team_id}/team_members`

**Request Body:**
```json
{
  "user_ids": [5, 7, 12]
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/teams/2/team_members \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "user_ids": [5, 7]
  }'
```

---

### 5. Create Conversation with Team Assignment

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations`

**Request Body:**
```json
{
  "source_id": "SOURCE_ID",
  "inbox_id": 1,
  "contact_id": 789,
  "team_id": 2,
  "status": "open"
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "source_id": "whatsapp_12345",
    "inbox_id": 1,
    "contact_id": 789,
    "team_id": 2
  }'
```

---

### Priority Settings

Set conversation priority to facilitate escalation workflows.

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_priority`

**Request Body:**
```json
{
  "priority": "urgent"
}
```

**Available Priority Levels:**
- `urgent` - Highest priority, immediate attention required
- `high` - High priority
- `medium` - Normal priority
- `low` - Low priority
- `none` - No priority set (default)

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/toggle_priority \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "priority": "urgent"
  }'
```

**Success Response (200):**
```json
{
  "id": 456,
  "priority": "urgent",
  "status": "open"
}
```

---

### Notification Mechanisms

When a conversation is assigned:
1. **Email Notification:** Agent receives email (if enabled in settings)
2. **In-App Notification:** Real-time notification in Chatwoot dashboard
3. **Webhook Event:** `conversation_updated` webhook is triggered

---

### Escalation Workflow Example

```javascript
// Step 1: Set priority to urgent
await fetch(`https://app.chatwoot.com/api/v1/accounts/123/conversations/456/toggle_priority`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'api_access_token': 'YOUR_TOKEN'
  },
  body: JSON.stringify({ priority: 'urgent' })
});

// Step 2: Add escalation tag
await fetch(`https://app.chatwoot.com/api/v1/accounts/123/conversations/456/labels`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'api_access_token': 'YOUR_TOKEN'
  },
  body: JSON.stringify({ labels: ['escalated', 'urgent', 'requires-manager'] })
});

// Step 3: Assign to senior team
await fetch(`https://app.chatwoot.com/api/v1/accounts/123/conversations/456/assignments`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'api_access_token': 'YOUR_TOKEN'
  },
  body: JSON.stringify({ team_id: 5 }) // Senior support team
});

// Step 4: Add internal note
await fetch(`https://app.chatwoot.com/api/v1/accounts/123/conversations/456/messages`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'api_access_token': 'YOUR_TOKEN'
  },
  body: JSON.stringify({
    content: 'ESCALATED: Customer is enterprise tier and threatening to churn. Requires immediate manager attention.',
    message_type: 'outgoing',
    private: true
  })
});
```

---

### Best Practices

1. **Auto-Assignment:** Enable `allow_auto_assign` for balanced workload distribution
2. **Round-Robin:** Chatwoot automatically distributes conversations when auto-assign is enabled
3. **Skill-Based Routing:** Create teams based on expertise (billing, technical, onboarding)
4. **Escalation Criteria:** Define clear rules for when to escalate (priority + tags + custom attributes)
5. **Team Size:** Keep teams between 5-15 members for optimal management
6. **Backup Assignment:** Always have backup agents in critical teams

---

## Webhooks & Events

### Overview
Webhooks allow real-time notifications when events occur in Chatwoot. Instead of polling the API, your application receives HTTP POST requests when specific events happen.

---

### Available Webhook Events

| Event Name | Description | When Triggered |
|------------|-------------|----------------|
| `conversation_created` | New conversation initiated | Contact starts new conversation |
| `conversation_status_changed` | Conversation status updated | Status changes (open, resolved, etc.) |
| `conversation_updated` | Any conversation field changed | Labels, priority, custom attributes, etc. |
| `message_created` | New message in conversation | Agent or contact sends message |
| `message_updated` | Message edited or deleted | Message content modified |
| `contact_created` | New contact created | First interaction from new user |
| `contact_updated` | Contact details modified | Name, email, custom attributes changed |
| `webwidget_triggered` | Widget opened by visitor | User initiates chat widget |

---

### 1. Create Webhook Subscription

**Endpoint:** `POST /api/v1/accounts/{account_id}/webhooks`

**Request Body:**
```json
{
  "url": "https://your-server.com/webhooks/chatwoot",
  "subscriptions": [
    "conversation_created",
    "conversation_status_changed",
    "message_created"
  ]
}
```

**Field Descriptions:**
- `url` (string, required): Your webhook endpoint URL (must be HTTPS in production)
- `subscriptions` (array, required): List of events to subscribe to

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/webhooks \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "url": "https://your-server.com/webhooks/chatwoot",
    "subscriptions": ["conversation_created", "message_created"]
  }'
```

**Success Response (200):**
```json
{
  "id": 42,
  "url": "https://your-server.com/webhooks/chatwoot",
  "subscriptions": [
    "conversation_created",
    "message_created"
  ],
  "account_id": 123
}
```

---

### 2. List All Webhooks

**Endpoint:** `GET /api/v1/accounts/{account_id}/webhooks`

**Example cURL:**
```bash
curl --request GET \
  --url https://app.chatwoot.com/api/v1/accounts/123/webhooks \
  --header 'api_access_token: YOUR_TOKEN'
```

**Success Response (200):**
```json
[
  {
    "id": 42,
    "url": "https://your-server.com/webhooks/chatwoot",
    "subscriptions": ["conversation_created", "message_created"],
    "account_id": 123
  }
]
```

---

### 3. Update Webhook

**Endpoint:** `PATCH /api/v1/accounts/{account_id}/webhooks/{webhook_id}`

**Request Body:**
```json
{
  "url": "https://new-server.com/webhooks/chatwoot",
  "subscriptions": [
    "conversation_created",
    "conversation_updated",
    "message_created",
    "contact_created"
  ]
}
```

**Example cURL:**
```bash
curl --request PATCH \
  --url https://app.chatwoot.com/api/v1/accounts/123/webhooks/42 \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "subscriptions": ["conversation_created", "contact_created"]
  }'
```

---

### 4. Delete Webhook

**Endpoint:** `DELETE /api/v1/accounts/{account_id}/webhooks/{webhook_id}`

**Example cURL:**
```bash
curl --request DELETE \
  --url https://app.chatwoot.com/api/v1/accounts/123/webhooks/42 \
  --header 'api_access_token: YOUR_TOKEN'
```

---

### Webhook Payload Structures

#### conversation_created Event

```json
{
  "event": "conversation_created",
  "id": 456,
  "account": {
    "id": 123,
    "name": "Acme Corp"
  },
  "additional_attributes": {},
  "custom_attributes": {},
  "inbox": {
    "id": 1,
    "name": "WhatsApp Inbox"
  },
  "messages": [],
  "meta": {
    "sender": {
      "id": 789,
      "name": "John Doe",
      "email": "john@example.com",
      "phone_number": "+1234567890"
    },
    "assignee": null
  },
  "status": "open",
  "priority": null,
  "labels": [],
  "created_at": 1697472000,
  "timestamp": "2025-10-16T10:30:00.000Z"
}
```

#### message_created Event

```json
{
  "event": "message_created",
  "id": 12345,
  "content": "Hello, I need help with my order",
  "account": {
    "id": 123,
    "name": "Acme Corp"
  },
  "conversation": {
    "id": 456,
    "inbox_id": 1,
    "status": "open",
    "labels": ["support"]
  },
  "sender": {
    "id": 789,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "message_type": "incoming",
  "content_type": "text",
  "content_attributes": {},
  "private": false,
  "created_at": 1697472100,
  "source_id": "whatsapp_msg_123"
}
```

#### conversation_status_changed Event

```json
{
  "event": "conversation_status_changed",
  "id": 456,
  "account": {
    "id": 123
  },
  "status": "resolved",
  "previous_status": "open",
  "changed_at": 1697472500,
  "changed_by": {
    "id": 5,
    "name": "Agent Name",
    "type": "user"
  }
}
```

#### conversation_updated Event

```json
{
  "event": "conversation_updated",
  "id": 456,
  "account": {
    "id": 123
  },
  "changes": {
    "labels": {
      "before": ["support"],
      "after": ["support", "urgent"]
    },
    "priority": {
      "before": null,
      "after": "high"
    },
    "custom_attributes": {
      "before": {},
      "after": {
        "lead_score": 85
      }
    }
  },
  "updated_at": 1697472600
}
```

#### contact_created Event

```json
{
  "event": "contact_created",
  "id": 789,
  "name": "John Doe",
  "email": "john@example.com",
  "phone_number": "+1234567890",
  "account": {
    "id": 123
  },
  "custom_attributes": {},
  "additional_attributes": {
    "source": "whatsapp"
  },
  "created_at": 1697471000
}
```

---

### Webhook Security

#### Verify Webhook Authenticity

Chatwoot doesn't currently send HMAC signatures, but you should:

1. **Use HTTPS:** Always use HTTPS endpoints for webhooks
2. **IP Whitelisting:** Restrict incoming requests to Chatwoot's IP addresses
3. **API Token Validation:** Include a secret parameter in your webhook URL
4. **Idempotency:** Handle duplicate webhook deliveries gracefully

**Example Secure URL:**
```
https://your-server.com/webhooks/chatwoot?secret=YOUR_SECRET_TOKEN_HERE
```

#### Webhook Endpoint Implementation (Node.js/Express)

```javascript
const express = require('express');
const app = express();

app.post('/webhooks/chatwoot', express.json(), async (req, res) => {
  // Validate secret token
  if (req.query.secret !== process.env.WEBHOOK_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const payload = req.body;
  const event = payload.event;

  console.log(`Received webhook event: ${event}`);

  try {
    switch (event) {
      case 'conversation_created':
        await handleNewConversation(payload);
        break;

      case 'message_created':
        await handleNewMessage(payload);
        break;

      case 'conversation_status_changed':
        await handleStatusChange(payload);
        break;

      default:
        console.log(`Unhandled event type: ${event}`);
    }

    // Always respond quickly (within 3 seconds)
    res.status(200).json({ received: true });

  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({ error: 'Processing failed' });
  }
});

async function handleNewConversation(payload) {
  console.log('New conversation:', payload.id);
  // Your business logic here
}

async function handleNewMessage(payload) {
  // Only process incoming messages (not agent replies)
  if (payload.message_type === 'incoming') {
    console.log('New customer message:', payload.content);
    // Auto-tagging, lead scoring, etc.
  }
}

async function handleStatusChange(payload) {
  if (payload.status === 'resolved') {
    console.log('Conversation resolved:', payload.id);
    // Send satisfaction survey, update CRM, etc.
  }
}

app.listen(3000, () => {
  console.log('Webhook server running on port 3000');
});
```

---

### Webhook Retry Logic

Chatwoot webhook delivery behavior:
- **Timeout:** 5 seconds for your endpoint to respond
- **Retries:** Limited retry attempts on failure
- **Success:** Any 2xx HTTP status code is considered successful

**Best Practices:**
1. **Respond Immediately:** Return 200 status, then process asynchronously
2. **Queue Processing:** Use a job queue for time-consuming tasks
3. **Idempotency Keys:** Track processed webhook IDs to avoid duplicate processing
4. **Error Logging:** Log all webhook payloads for debugging

---

### Webhook Testing

Use tools like ngrok for local development:

```bash
# Start ngrok tunnel
ngrok http 3000

# Your webhook URL
https://abc123.ngrok.io/webhooks/chatwoot
```

Test webhook manually with cURL:

```bash
curl --request POST \
  --url 'https://your-server.com/webhooks/chatwoot?secret=YOUR_SECRET' \
  --header 'Content-Type: application/json' \
  --data '{
    "event": "message_created",
    "id": 12345,
    "content": "Test message",
    "conversation": { "id": 456 }
  }'
```

---

## Status & Priority Management

### Conversation Status API

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_status`

**Available Statuses:**
- `open` - Active conversation
- `resolved` - Issue resolved, conversation closed
- `pending` - Waiting on customer response
- `snoozed` - Temporarily hidden until specified time

**Request Body:**
```json
{
  "status": "resolved"
}
```

**Snooze Until Specific Time:**
```json
{
  "status": "snoozed",
  "snoozed_until": 1729180800
}
```

**Important:** Snoozed conversations automatically reopen when the contact sends a new reply.

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/toggle_status \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "status": "resolved"
  }'
```

**Success Response (200):**
```json
{
  "payload": {
    "success": true,
    "current_status": "resolved",
    "conversation_id": 456
  }
}
```

---

### Conversation Priority API

**Endpoint:** `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_priority`

**Available Priority Levels:**
- `urgent` - Immediate attention required
- `high` - High priority
- `medium` - Normal priority
- `low` - Low priority
- `none` - No priority (default)

**Request Body:**
```json
{
  "priority": "urgent"
}
```

**Example cURL:**
```bash
curl --request POST \
  --url https://app.chatwoot.com/api/v1/accounts/123/conversations/456/toggle_priority \
  --header 'Content-Type: application/json' \
  --header 'api_access_token: YOUR_TOKEN' \
  --data '{
    "priority": "high"
  }'
```

---

## Common Response Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no response body |
| 400 | Bad Request | Invalid request parameters or body |
| 401 | Unauthorized | Missing or invalid API token |
| 403 | Forbidden | Authenticated but not authorized for this action |
| 404 | Not Found | Resource does not exist |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Code Examples

### Complete Lead Qualification Workflow

```javascript
const CHATWOOT_API_TOKEN = 'your_api_token';
const ACCOUNT_ID = 123;
const BASE_URL = 'https://app.chatwoot.com/api/v1';

async function qualifyLead(conversationId, leadData) {
  const headers = {
    'Content-Type': 'application/json',
    'api_access_token': CHATWOOT_API_TOKEN
  };

  try {
    // Step 1: Add qualification tags
    await fetch(`${BASE_URL}/accounts/${ACCOUNT_ID}/conversations/${conversationId}/labels`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        labels: ['qualified', 'hot-lead', 'enterprise-interest']
      })
    });

    // Step 2: Set custom attributes
    await fetch(`${BASE_URL}/accounts/${ACCOUNT_ID}/conversations/${conversationId}/custom_attributes`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        custom_attributes: {
          lead_score: leadData.score,
          deal_value: leadData.estimatedValue,
          industry: leadData.industry,
          company_size: leadData.companySize,
          next_follow_up: leadData.followUpDate
        }
      })
    });

    // Step 3: Set high priority
    await fetch(`${BASE_URL}/accounts/${ACCOUNT_ID}/conversations/${conversationId}/toggle_priority`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ priority: 'high' })
    });

    // Step 4: Assign to sales team
    await fetch(`${BASE_URL}/accounts/${ACCOUNT_ID}/conversations/${conversationId}/assignments`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ team_id: 2 }) // Sales team ID
    });

    // Step 5: Add internal qualification note
    await fetch(`${BASE_URL}/accounts/${ACCOUNT_ID}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        content: `**Lead Qualified**\n\nScore: ${leadData.score}/100\nEstimated Deal Value: $${leadData.estimatedValue}\nCompany: ${leadData.companyName} (${leadData.companySize} employees)\nIndustry: ${leadData.industry}\n\nNext Steps:\n- Schedule discovery call\n- Send pricing deck\n- Add to CRM`,
        message_type: 'outgoing',
        private: true
      })
    });

    console.log('Lead qualification completed successfully');
    return { success: true };

  } catch (error) {
    console.error('Lead qualification failed:', error);
    return { success: false, error: error.message };
  }
}

// Usage
qualifyLead(456, {
  score: 85,
  estimatedValue: 50000,
  industry: 'Technology',
  companyName: 'Acme Corp',
  companySize: '51-200',
  followUpDate: '2025-10-20'
});
```

---

### Webhook Event Handler with Auto-Tagging

```javascript
const express = require('express');
const app = express();

// Auto-tagging rules based on message content
const AUTO_TAG_RULES = [
  { keywords: ['price', 'pricing', 'cost', 'how much'], tags: ['pricing-inquiry'] },
  { keywords: ['bug', 'error', 'broken', 'not working'], tags: ['technical-issue'] },
  { keywords: ['cancel', 'refund', 'unsubscribe'], tags: ['churn-risk'] },
  { keywords: ['enterprise', 'team', 'bulk', 'organization'], tags: ['enterprise-lead'] },
  { keywords: ['demo', 'trial', 'get started'], tags: ['sales-qualified'] }
];

app.post('/webhooks/chatwoot', express.json(), async (req, res) => {
  const payload = req.body;

  if (payload.event === 'message_created' && payload.message_type === 'incoming') {
    await handleIncomingMessage(payload);
  }

  res.status(200).json({ received: true });
});

async function handleIncomingMessage(message) {
  const content = message.content.toLowerCase();
  const conversationId = message.conversation.id;

  // Find matching tags
  const matchedTags = [];
  for (const rule of AUTO_TAG_RULES) {
    if (rule.keywords.some(keyword => content.includes(keyword))) {
      matchedTags.push(...rule.tags);
    }
  }

  if (matchedTags.length > 0) {
    // Get existing labels
    const existingLabels = message.conversation.labels || [];
    const allLabels = [...new Set([...existingLabels, ...matchedTags])];

    // Update conversation labels
    await fetch(`https://app.chatwoot.com/api/v1/accounts/${message.account.id}/conversations/${conversationId}/labels`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api_access_token': process.env.CHATWOOT_API_TOKEN
      },
      body: JSON.stringify({ labels: allLabels })
    });

    console.log(`Auto-tagged conversation ${conversationId} with:`, matchedTags);
  }

  // Lead scoring based on keywords
  let leadScore = 0;
  if (content.includes('enterprise')) leadScore += 30;
  if (content.includes('budget')) leadScore += 20;
  if (content.includes('urgent')) leadScore += 15;
  if (content.includes('demo') || content.includes('trial')) leadScore += 25;

  if (leadScore > 0) {
    await fetch(`https://app.chatwoot.com/api/v1/accounts/${message.account.id}/conversations/${conversationId}/custom_attributes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api_access_token': process.env.CHATWOOT_API_TOKEN
      },
      body: JSON.stringify({
        custom_attributes: { lead_score: leadScore }
      })
    });
  }
}

app.listen(3000);
```

---

### Batch Update Conversations

```javascript
async function batchUpdateConversations(conversationIds, updates) {
  const results = [];

  for (const convId of conversationIds) {
    try {
      // Update labels
      if (updates.labels) {
        await updateLabels(convId, updates.labels);
      }

      // Update custom attributes
      if (updates.customAttributes) {
        await updateCustomAttributes(convId, updates.customAttributes);
      }

      // Update priority
      if (updates.priority) {
        await updatePriority(convId, updates.priority);
      }

      // Update status
      if (updates.status) {
        await updateStatus(convId, updates.status);
      }

      results.push({ conversationId: convId, success: true });
    } catch (error) {
      results.push({ conversationId: convId, success: false, error: error.message });
    }

    // Rate limiting: wait 100ms between requests
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  return results;
}

async function updateLabels(conversationId, labels) {
  const response = await fetch(
    `https://app.chatwoot.com/api/v1/accounts/${ACCOUNT_ID}/conversations/${conversationId}/labels`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api_access_token': CHATWOOT_API_TOKEN
      },
      body: JSON.stringify({ labels })
    }
  );
  return response.json();
}

// Usage
batchUpdateConversations(
  [123, 124, 125, 126],
  {
    labels: ['Q4-campaign', 'follow-up-needed'],
    customAttributes: { campaign_source: 'email-blast-oct' },
    priority: 'medium'
  }
);
```

---

### Error Handling Best Practices

```javascript
class ChatwootAPIClient {
  constructor(apiToken, accountId) {
    this.apiToken = apiToken;
    this.accountId = accountId;
    this.baseUrl = 'https://app.chatwoot.com/api/v1';
  }

  async makeRequest(endpoint, method = 'GET', body = null) {
    const url = `${this.baseUrl}/accounts/${this.accountId}${endpoint}`;
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'api_access_token': this.apiToken
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
        console.warn(`Rate limited. Retrying after ${retryAfter} seconds...`);
        await this.sleep(retryAfter * 1000);
        return this.makeRequest(endpoint, method, body); // Retry
      }

      // Handle errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          `Chatwoot API Error (${response.status}): ${errorData.message || response.statusText}`
        );
      }

      return await response.json();

    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Convenience methods
  async addLabels(conversationId, labels) {
    return this.makeRequest(
      `/conversations/${conversationId}/labels`,
      'POST',
      { labels }
    );
  }

  async createNote(conversationId, content) {
    return this.makeRequest(
      `/conversations/${conversationId}/messages`,
      'POST',
      {
        content,
        message_type: 'outgoing',
        private: true
      }
    );
  }

  async updateCustomAttributes(conversationId, attributes) {
    return this.makeRequest(
      `/conversations/${conversationId}/custom_attributes`,
      'POST',
      { custom_attributes: attributes }
    );
  }
}

// Usage
const client = new ChatwootAPIClient('your_token', 123);

try {
  await client.addLabels(456, ['priority', 'sales']);
  await client.createNote(456, 'Customer interested in enterprise plan');
  await client.updateCustomAttributes(456, { lead_score: 90 });
} catch (error) {
  console.error('Failed to update conversation:', error);
}
```

---

## Additional Resources

- **Official Documentation:** https://developers.chatwoot.com/
- **GitHub Repository:** https://github.com/chatwoot/chatwoot
- **Community Forum:** https://chatwoot.com/community
- **API Changelog:** Check GitHub releases for API updates
- **Support:** https://www.chatwoot.com/hc/

---

## Screenshots Reference

The following screenshots were captured during research and are available at:
- `/Users/benomarlaamiri/Downloads/chatwoot-api-homepage-2025-10-16T11-25-29-343Z.png`
- `/Users/benomarlaamiri/Downloads/chatwoot-api-reference-2025-10-16T11-26-02-015Z.png`
- `/Users/benomarlaamiri/Downloads/chatwoot-add-labels-api-2025-10-16T11-32-19-319Z.png`

---

**End of Technical Reference Document**
