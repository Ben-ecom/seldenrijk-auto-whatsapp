# Chatwoot API Reference

Complete API reference for Chatwoot integration with focus on contacts, conversations, and messages.

## Authentication

All API requests require authentication via API access token:

```http
Headers:
  api_access_token: YOUR_API_TOKEN
  Content-Type: application/json
```

## Base URL Structure

```
{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/...
```

## Contacts API

### Get Contact by Phone Number

Search for existing contact by phone number (identifier):

```http
GET /api/v1/accounts/{account_id}/contacts/search?q={phone_number}
```

**Response:**
```json
{
  "payload": [
    {
      "id": 123,
      "name": "John Doe",
      "phone_number": "+31612345678",
      "email": null,
      "identifier": "31612345678@c.us",
      "custom_attributes": {},
      "contact_inboxes": [
        {
          "inbox_id": 1,
          "source_id": "31612345678@c.us"
        }
      ]
    }
  ]
}
```

### Create Contact

```http
POST /api/v1/accounts/{account_id}/contacts
```

**Payload:**
```json
{
  "name": "John Doe",
  "phone_number": "+31612345678",
  "identifier": "31612345678@c.us",
  "inbox_id": 1
}
```

**Response:**
```json
{
  "id": 123,
  "name": "John Doe",
  "phone_number": "+31612345678",
  "identifier": "31612345678@c.us"
}
```

### Update Contact

```http
PUT /api/v1/accounts/{account_id}/contacts/{contact_id}
```

**Payload:**
```json
{
  "name": "Updated Name",
  "custom_attributes": {
    "lead_score": 75,
    "last_interaction": "2025-01-15T10:30:00Z"
  }
}
```

## Conversations API

### Get Conversation

```http
GET /api/v1/accounts/{account_id}/conversations/{conversation_id}
```

**Response:**
```json
{
  "id": 456,
  "status": "open",
  "inbox_id": 1,
  "contact_id": 123,
  "messages": [...],
  "meta": {
    "sender": {
      "id": 123,
      "name": "John Doe",
      "phone_number": "+31612345678"
    }
  }
}
```

### Create Conversation

```http
POST /api/v1/accounts/{account_id}/conversations
```

**Payload:**
```json
{
  "source_id": "31612345678@c.us",
  "inbox_id": 1,
  "contact_id": 123,
  "status": "open"
}
```

**Response:**
```json
{
  "id": 456,
  "status": "open",
  "inbox_id": 1,
  "contact_id": 123
}
```

### List Conversations

```http
GET /api/v1/accounts/{account_id}/conversations?inbox_id={inbox_id}&status={status}
```

**Query Parameters:**
- `inbox_id`: Filter by inbox (optional)
- `status`: open, resolved, pending (optional)
- `assignee_type`: mine, unassigned, all (optional)
- `page`: Page number (default: 1)

### Update Conversation Status

```http
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_status
```

**Payload:**
```json
{
  "status": "resolved"
}
```

### Assign Conversation

```http
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/assignments
```

**Payload:**
```json
{
  "assignee_id": 5
}
```

## Messages API

### Get Messages

```http
GET /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
```

**Response:**
```json
[
  {
    "id": 789,
    "content": "Hello, I'm looking for a car",
    "message_type": "incoming",
    "created_at": "2025-01-15T10:30:00Z",
    "sender": {
      "id": 123,
      "name": "John Doe"
    }
  }
]
```

### Send Message

```http
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
```

**Payload:**
```json
{
  "content": "Thank you for your message!",
  "message_type": "outgoing",
  "private": false
}
```

**Message Types:**
- `incoming`: From customer
- `outgoing`: To customer (visible)
- `activity`: System message

**Private Notes:**
```json
{
  "content": "Internal note for team",
  "message_type": "outgoing",
  "private": true
}
```

## Labels API

### Add Label to Conversation

```http
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/labels
```

**Payload:**
```json
{
  "labels": ["hot-lead", "test-drive"]
}
```

**Note:** Labels must exist in Chatwoot before adding. Returns 404 if label doesn't exist.

### Remove Label

```http
DELETE /api/v1/accounts/{account_id}/conversations/{conversation_id}/labels/{label_id}
```

## Inboxes API

### Get Inbox Details

```http
GET /api/v1/accounts/{account_id}/inboxes/{inbox_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "WhatsApp",
  "channel_type": "Channel::Api",
  "webhook_url": "https://your-domain.com/webhooks/waha"
}
```

### List Inboxes

```http
GET /api/v1/accounts/{account_id}/inboxes
```

## Contact Inboxes API

### Create Contact Inbox (Link Contact to Inbox)

```http
POST /api/v1/accounts/{account_id}/contact_inboxes
```

**Payload:**
```json
{
  "inbox_id": 1,
  "contact_id": 123,
  "source_id": "31612345678@c.us"
}
```

**Response:**
```json
{
  "id": 10,
  "contact_id": 123,
  "inbox_id": 1,
  "source_id": "31612345678@c.us"
}
```

## Webhooks

### Message Created Event

Chatwoot sends webhook when new message is created:

```json
{
  "event": "message_created",
  "message_type": "incoming",
  "id": 789,
  "content": "Customer message",
  "conversation": {
    "id": 456,
    "inbox_id": 1
  },
  "sender": {
    "id": 123,
    "name": "John Doe",
    "phone_number": "+31612345678"
  },
  "account": {
    "id": 2
  }
}
```

### Conversation Status Changed

```json
{
  "event": "conversation_status_changed",
  "conversation": {
    "id": 456,
    "status": "resolved"
  }
}
```

## Common Patterns

### Check if Contact Exists

```python
# Search by phone number
response = requests.get(
    f"{base_url}/api/v1/accounts/{account_id}/contacts/search",
    params={"q": phone_number},
    headers={"api_access_token": api_token}
)

contacts = response.json()["payload"]
if contacts:
    contact_id = contacts[0]["id"]
else:
    # Create new contact
    ...
```

### Get or Create Conversation

```python
# 1. Search for existing conversation
response = requests.get(
    f"{base_url}/api/v1/accounts/{account_id}/conversations",
    params={
        "inbox_id": inbox_id,
        "status": "open"
    },
    headers={"api_access_token": api_token}
)

# Filter by contact_id
conversations = [c for c in response.json()["data"]["payload"]
                 if c["meta"]["sender"]["id"] == contact_id]

if conversations:
    conversation_id = conversations[0]["id"]
else:
    # Create new conversation
    response = requests.post(
        f"{base_url}/api/v1/accounts/{account_id}/conversations",
        json={
            "source_id": source_id,
            "inbox_id": inbox_id,
            "contact_id": contact_id
        },
        headers={"api_access_token": api_token}
    )
    conversation_id = response.json()["id"]
```

### Send Message and Add Labels

```python
# 1. Send message
requests.post(
    f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages",
    json={
        "content": "Your message here",
        "message_type": "outgoing"
    },
    headers={"api_access_token": api_token}
)

# 2. Add labels (if they exist)
requests.post(
    f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/labels",
    json={"labels": ["hot-lead"]},
    headers={"api_access_token": api_token}
)
```

## Error Handling

### Common Error Responses

**404 Not Found:**
```json
{
  "error": "Resource not found"
}
```

**422 Unprocessable Entity:**
```json
{
  "message": "Validation failed",
  "errors": {
    "phone_number": ["has already been taken"]
  }
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error"
}
```

### Best Practices

1. **Always check if resource exists before creating**
2. **Handle 404 errors gracefully** (e.g., labels that don't exist)
3. **Use identifiers for uniqueness** (e.g., phone number as identifier)
4. **Link contacts to inboxes** via contact_inboxes API
5. **Set proper message_type** (incoming vs outgoing)

## Rate Limits

- **100 requests per minute** per API token
- Use exponential backoff for retries
- Cache conversation/contact lookups

## Testing

### Test Contact Creation

```bash
curl -X POST "http://localhost:3001/api/v1/accounts/1/contacts" \
  -H "api_access_token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "phone_number": "+31612345678",
    "identifier": "31612345678@c.us",
    "inbox_id": 1
  }'
```

### Test Message Sending

```bash
curl -X POST "http://localhost:3001/api/v1/accounts/1/conversations/456/messages" \
  -H "api_access_token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test message",
    "message_type": "outgoing"
  }'
```

## Source

Documentation compiled from:
- https://www.chatwoot.com/developers/api
- https://www.chatwoot.com/docs/product/channels/api/send-messages
- Chatwoot GitHub repository examples
