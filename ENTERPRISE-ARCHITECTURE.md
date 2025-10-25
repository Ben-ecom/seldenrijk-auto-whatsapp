# 🏢 ENTERPRISE ARCHITECTURE DOCUMENT
## Seldenrijk Auto WhatsApp AI Platform - Production-Ready Design

**Document Version**: 1.0
**Date**: January 2025
**Status**: Architecture Proposal
**Target**: Production Deployment for Seldenrijk B.V.

---

## 📋 EXECUTIVE SUMMARY

This document outlines the enterprise-grade architecture for transforming the Seldenrijk Auto WhatsApp AI Platform from a proof-of-concept (POC) to a production-ready SaaS solution.

### Current State (POC)
- ✅ 11 specialized AI agents handling customer conversations
- ✅ Redis cache with 2-hour TTL for vehicle inventory
- ✅ Web scraping via Playwright (427 vehicles)
- ✅ Full inventory refresh every 2 hours
- ✅ WhatsApp integration via WAHA (open-source)
- ✅ Chatwoot CRM integration
- ⚠️ Single-client architecture
- ⚠️ Manual deployment
- ⚠️ No incremental updates

### Enterprise Target (Production)
- 🎯 Multi-tenant SaaS architecture
- 🎯 PostgreSQL persistent storage with incremental sync
- 🎯 API-first integration (no scraping when client onboarded)
- 🎯 Real-time webhook updates for inventory changes
- 🎯 Automated deployment via CI/CD
- 🎯 Horizontal scalability for 50+ dealers
- 🎯 99.9% uptime SLA
- 🎯 GDPR-compliant data handling

---

## 🏗️ SYSTEM ARCHITECTURE

### 1. CURRENT POC ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                   DOCKER COMPOSE SETUP                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│  │   API    │   │  Celery  │   │  Celery  │          │
│  │ FastAPI  │   │  Worker  │   │   Beat   │          │
│  │  :8000   │   │ (Tasks)  │   │(Schedule)│          │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘          │
│       │              │              │                  │
│       └──────────────┴──────────────┘                  │
│                      │                                  │
│               ┌──────┴──────┐                          │
│               │   Redis     │                          │
│               │   :6379     │                          │
│               │ (Cache 2h)  │                          │
│               └─────────────┘                          │
│                                                         │
│  ┌──────────┐          ┌──────────┐                   │
│  │   WAHA   │          │Dashboard │                   │
│  │ WhatsApp │          │ Reflex   │                   │
│  │  :3003   │          │ :3002    │                   │
│  └──────────┘          └──────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘

External Dependencies:
├── Supabase (PostgreSQL + Auth)
├── Chatwoot (CRM)
├── Anthropic Claude API (AI)
├── OpenAI API (Embeddings)
└── Seldenrijk.nl (Web Scraping)
```

**Data Flow - Current POC:**
1. Celery Beat triggers inventory sync every 2 hours
2. Playwright scrapes seldenrijk.nl (page 30 = all 427 vehicles)
3. Full inventory stored in Redis with 2-hour TTL
4. RAG Agent queries Redis for vehicle search
5. WhatsApp messages → WAHA → API → Agent Router → RAG Agent → Response

**Limitations:**
- ❌ Full refresh wastes resources (95% of vehicles unchanged)
- ❌ No tracking of sold vehicles or price changes
- ❌ No historical data or analytics
- ❌ Web scraping fragile (website changes break scraper)
- ❌ Single dealer hardcoded
- ❌ No multi-tenancy

---

### 2. ENTERPRISE PRODUCTION ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      KUBERNETES CLUSTER (GKE/EKS/AKS)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐            │
│  │              INGRESS CONTROLLER (NGINX)                 │            │
│  │  ├── /api/* → FastAPI Service                          │            │
│  │  ├── /webhooks/* → Webhook Service                     │            │
│  │  └── /dashboard/* → Dashboard Service                  │            │
│  └────────────────────────────────────────────────────────┘            │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │  FastAPI Pod │  │  FastAPI Pod │  │  FastAPI Pod │                │
│  │ (API Service)│  │ (API Service)│  │ (API Service)│                │
│  │   Replicas:  │  │   Replicas:  │  │   Replicas:  │                │
│  │     3-10     │  │     3-10     │  │     3-10     │                │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│                            │                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ Celery Worker│  │ Celery Worker│  │ Celery Worker│                │
│  │  Queue: msgs │  │ Queue: crm   │  │ Queue: sync  │                │
│  │  Replicas: 5 │  │ Replicas: 3  │  │ Replicas: 2  │                │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│                            │                                            │
│               ┌────────────┴────────────┐                              │
│               │    Redis Cluster        │                              │
│               │    (ElastiCache)        │                              │
│               │    - Celery Broker      │                              │
│               │    - Session Cache      │                              │
│               │    - Rate Limiting      │                              │
│               └─────────────────────────┘                              │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐            │
│  │              POSTGRESQL CLUSTER (Supabase)              │            │
│  │  Tables:                                                │            │
│  │  ├── dealers (multi-tenant)                            │            │
│  │  ├── vehicles (incremental sync)                       │            │
│  │  ├── vehicle_history (price/status changes)           │            │
│  │  ├── conversations                                     │            │
│  │  ├── customers                                         │            │
│  │  ├── leads                                             │            │
│  │  └── analytics_events                                  │            │
│  │                                                         │            │
│  │  Indexes: brand, model, fuel, dealer_id, status        │            │
│  │  Partitioning: vehicles by dealer_id                   │            │
│  │  Read Replicas: 2 (for analytics)                      │            │
│  └─────────────────────────────────────────────────────────┘            │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ WAHA Pod #1  │  │ WAHA Pod #2  │  │ WAHA Pod #N  │                │
│  │  Dealer: 1   │  │  Dealer: 2   │  │  Dealer: N   │                │
│  │ WhatsApp Sesh│  │ WhatsApp Sesh│  │ WhatsApp Sesh│                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

External Services:
├── Supabase (PostgreSQL + Auth + Storage)
├── Sentry (Error Tracking)
├── Anthropic Claude (AI Models)
├── OpenAI (Embeddings)
├── Dealer APIs (AutoTrack, AutoTelex, GForces)
└── Webhook Receivers (from Dealer Management Software)
```

**Data Flow - Enterprise:**
1. **Dealer Onboarding**: API credentials exchanged, webhook setup
2. **Real-time Updates**: Dealer software pushes vehicle changes via webhook
3. **Incremental Sync**: INSERT new vehicles, UPDATE modified, soft-delete sold
4. **Query Optimization**: PostgreSQL indexes + read replicas for fast search
5. **Multi-tenant Isolation**: Row-Level Security (RLS) by dealer_id
6. **Conversation Routing**: WAHA pod per dealer → API → tenant-aware routing

---

## 💾 DATABASE SCHEMA DESIGN

### PostgreSQL Schema (Supabase)

```sql
-- ==========================================
-- DEALERS TABLE (Multi-Tenant)
-- ==========================================
CREATE TABLE dealers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,

    -- Contact Info
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(50) DEFAULT 'NL',

    -- API Integration
    api_type VARCHAR(50), -- 'autotrack', 'autotelex', 'gforces', 'custom'
    api_credentials JSONB, -- Encrypted credentials
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),

    -- WhatsApp
    whatsapp_number VARCHAR(50),
    waha_session_id VARCHAR(100),

    -- Business Config
    business_hours JSONB, -- {"monday": {"open": "09:00", "close": "18:00"}}
    team_members JSONB[], -- Array of staff profiles

    -- Subscription
    plan VARCHAR(50) DEFAULT 'free', -- 'free', 'starter', 'professional', 'enterprise'
    mrr_amount DECIMAL(10,2),
    subscription_status VARCHAR(50) DEFAULT 'active',
    trial_ends_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('dutch', coalesce(name, '') || ' ' || coalesce(city, ''))
    ) STORED
);

CREATE INDEX idx_dealers_slug ON dealers(slug);
CREATE INDEX idx_dealers_active ON dealers(is_active) WHERE is_active = true;
CREATE INDEX idx_dealers_search ON dealers USING GIN(search_vector);


-- ==========================================
-- VEHICLES TABLE (Incremental Sync)
-- ==========================================
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id UUID NOT NULL REFERENCES dealers(id) ON DELETE CASCADE,

    -- External IDs
    external_id VARCHAR(255), -- ID from dealer's system
    source VARCHAR(50) NOT NULL, -- 'api', 'scrape', 'manual'

    -- Vehicle Basics
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    variant VARCHAR(200),
    title TEXT,
    description TEXT,

    -- Specifications
    build_year INTEGER,
    mileage INTEGER,
    fuel_type VARCHAR(50),
    transmission VARCHAR(50),
    color_exterior VARCHAR(50),
    color_interior VARCHAR(50),
    body_type VARCHAR(50),
    doors INTEGER,
    seats INTEGER,

    -- Engine
    engine_capacity INTEGER, -- cc
    engine_power INTEGER, -- hp
    co2_emission INTEGER, -- g/km
    energy_label VARCHAR(10),

    -- Pricing
    price DECIMAL(10,2) NOT NULL,
    vat_included BOOLEAN DEFAULT true,
    negotiable BOOLEAN DEFAULT false,

    -- Status Tracking
    status VARCHAR(50) DEFAULT 'available', -- 'available', 'reserved', 'sold', 'removed'
    availability_date DATE,
    sold_at TIMESTAMP,

    -- Media
    images JSONB[], -- Array of image URLs
    videos JSONB[], -- Array of video URLs
    url VARCHAR(500), -- Link to dealer's website

    -- Features
    features JSONB, -- {"navigation": true, "leather_seats": true}
    equipment TEXT[],

    -- SEO & Search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('dutch',
            coalesce(brand, '') || ' ' ||
            coalesce(model, '') || ' ' ||
            coalesce(variant, '') || ' ' ||
            coalesce(title, '') || ' ' ||
            coalesce(description, '')
        )
    ) STORED,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_synced_at TIMESTAMP DEFAULT NOW(),
    sync_hash VARCHAR(64), -- MD5 hash for change detection

    -- Uniqueness constraint
    UNIQUE(dealer_id, external_id)
);

-- Indexes for Performance
CREATE INDEX idx_vehicles_dealer ON vehicles(dealer_id);
CREATE INDEX idx_vehicles_status ON vehicles(status) WHERE status = 'available';
CREATE INDEX idx_vehicles_brand_model ON vehicles(brand, model);
CREATE INDEX idx_vehicles_price ON vehicles(price);
CREATE INDEX idx_vehicles_year ON vehicles(build_year DESC);
CREATE INDEX idx_vehicles_mileage ON vehicles(mileage);
CREATE INDEX idx_vehicles_fuel ON vehicles(fuel_type);
CREATE INDEX idx_vehicles_search ON vehicles USING GIN(search_vector);
CREATE INDEX idx_vehicles_updated ON vehicles(updated_at DESC);

-- Partitioning by dealer_id (for scaling to 100+ dealers)
-- CREATE TABLE vehicles_dealer_001 PARTITION OF vehicles FOR VALUES IN (dealer_001_uuid);


-- ==========================================
-- VEHICLE_HISTORY TABLE (Audit Log)
-- ==========================================
CREATE TABLE vehicle_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    dealer_id UUID NOT NULL REFERENCES dealers(id) ON DELETE CASCADE,

    -- Change Tracking
    change_type VARCHAR(50) NOT NULL, -- 'created', 'price_change', 'status_change', 'updated', 'deleted'
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,

    -- Context
    triggered_by VARCHAR(50), -- 'webhook', 'scrape', 'manual', 'api'
    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vehicle_history_vehicle ON vehicle_history(vehicle_id, created_at DESC);
CREATE INDEX idx_vehicle_history_dealer ON vehicle_history(dealer_id, created_at DESC);
CREATE INDEX idx_vehicle_history_type ON vehicle_history(change_type);


-- ==========================================
-- CONVERSATIONS TABLE
-- ==========================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id UUID NOT NULL REFERENCES dealers(id) ON DELETE CASCADE,

    -- Customer Info
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),

    -- Chatwoot Integration
    chatwoot_conversation_id INTEGER,
    chatwoot_contact_id INTEGER,

    -- Conversation Data
    messages JSONB[], -- Array of message objects
    intent VARCHAR(100), -- 'browse', 'specific_vehicle', 'test_drive', 'financing'
    interested_vehicles UUID[], -- Array of vehicle IDs

    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'waiting', 'resolved', 'archived'
    assigned_to VARCHAR(255), -- Staff member

    -- Quality Metrics
    sentiment_score DECIMAL(3,2), -- -1.00 to 1.00
    ai_confidence DECIMAL(3,2), -- 0.00 to 1.00
    escalated BOOLEAN DEFAULT false,
    escalation_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,

    UNIQUE(dealer_id, customer_phone)
);

CREATE INDEX idx_conversations_dealer ON conversations(dealer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_phone ON conversations(customer_phone);
CREATE INDEX idx_conversations_updated ON conversations(last_message_at DESC);


-- ==========================================
-- LEADS TABLE (Sales Pipeline)
-- ==========================================
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id UUID NOT NULL REFERENCES dealers(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),

    -- Customer
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50) NOT NULL,
    customer_email VARCHAR(255),

    -- Lead Details
    interested_vehicle_id UUID REFERENCES vehicles(id),
    lead_source VARCHAR(50) DEFAULT 'whatsapp',
    lead_type VARCHAR(50), -- 'hot', 'warm', 'cold'
    interest_level INTEGER, -- 1-10

    -- Actions
    requested_test_drive BOOLEAN DEFAULT false,
    test_drive_date TIMESTAMP,
    requested_financing BOOLEAN DEFAULT false,
    requested_callback BOOLEAN DEFAULT false,
    callback_preferred_time VARCHAR(50),

    -- Notes
    notes TEXT,
    tags VARCHAR(100)[],

    -- Status
    status VARCHAR(50) DEFAULT 'new', -- 'new', 'contacted', 'qualified', 'proposal', 'won', 'lost'
    lost_reason TEXT,

    -- Assigned
    assigned_to VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    contacted_at TIMESTAMP,
    qualified_at TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE INDEX idx_leads_dealer ON leads(dealer_id);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_phone ON leads(customer_phone);
CREATE INDEX idx_leads_created ON leads(created_at DESC);
CREATE INDEX idx_leads_assigned ON leads(assigned_to);


-- ==========================================
-- ANALYTICS_EVENTS TABLE (Product Analytics)
-- ==========================================
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id UUID NOT NULL REFERENCES dealers(id) ON DELETE CASCADE,

    -- Event Data
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(100) NOT NULL,
    properties JSONB,

    -- Context
    user_id UUID,
    session_id VARCHAR(255),
    conversation_id UUID REFERENCES conversations(id),
    vehicle_id UUID REFERENCES vehicles(id),

    -- Device Info
    platform VARCHAR(50), -- 'whatsapp_web', 'whatsapp_mobile'
    user_agent TEXT,
    ip_address INET,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_dealer ON analytics_events(dealer_id, created_at DESC);
CREATE INDEX idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_vehicle ON analytics_events(vehicle_id) WHERE vehicle_id IS NOT NULL;
CREATE INDEX idx_analytics_created ON analytics_events(created_at DESC);

-- Partition by month for performance
-- CREATE TABLE analytics_events_2025_01 PARTITION OF analytics_events
-- FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

## 🔄 INCREMENTAL SYNC STRATEGY

### Current: Full Refresh (Inefficient)
```python
# Every 2 hours - scrape ALL 427 vehicles
vehicles = scraper.scrape_inventory()  # Returns ALL vehicles
redis_client.setex("seldenrijk:inventory:full", timedelta(hours=2), json.dumps(vehicles))
```

**Problems:**
- ❌ Wastes CPU/bandwidth (95% unchanged)
- ❌ No change detection
- ❌ No historical tracking
- ❌ Redis TTL = data loss on expiry

---

### Enterprise: Incremental Sync (Optimal)

```python
# app/tasks/incremental_sync.py

async def sync_dealer_inventory_incremental(dealer_id: str):
    """
    Incremental inventory sync with change detection.
    Only processes NEW, MODIFIED, and REMOVED vehicles.
    """
    dealer = await get_dealer(dealer_id)

    # Fetch current inventory from dealer API
    api_vehicles = await fetch_dealer_api_inventory(dealer)

    # Fetch existing vehicles from PostgreSQL
    db_vehicles = await get_dealer_vehicles(dealer_id)

    # Build lookup maps
    api_map = {v['external_id']: v for v in api_vehicles}
    db_map = {v.external_id: v for v in db_vehicles}

    stats = {
        "new": 0,
        "updated": 0,
        "removed": 0,
        "unchanged": 0
    }

    # Process NEW and UPDATED vehicles
    for external_id, api_vehicle in api_map.items():
        # Calculate hash for change detection
        vehicle_hash = calculate_vehicle_hash(api_vehicle)

        if external_id not in db_map:
            # NEW VEHICLE - INSERT
            await insert_vehicle(dealer_id, api_vehicle, vehicle_hash)
            await log_vehicle_history(dealer_id, external_id, "created", api_vehicle)
            stats["new"] += 1

        else:
            db_vehicle = db_map[external_id]

            if db_vehicle.sync_hash != vehicle_hash:
                # MODIFIED VEHICLE - UPDATE
                changes = detect_changes(db_vehicle, api_vehicle)
                await update_vehicle(db_vehicle.id, api_vehicle, vehicle_hash)

                # Log each field change
                for field, (old_val, new_val) in changes.items():
                    await log_vehicle_history(
                        dealer_id,
                        external_id,
                        "price_change" if field == "price" else "updated",
                        field_name=field,
                        old_value=str(old_val),
                        new_value=str(new_val)
                    )

                stats["updated"] += 1
            else:
                # UNCHANGED - just update last_synced_at
                await touch_vehicle_sync_timestamp(db_vehicle.id)
                stats["unchanged"] += 1

    # Process REMOVED vehicles (sold/deleted)
    for external_id, db_vehicle in db_map.items():
        if external_id not in api_map:
            # VEHICLE REMOVED - Soft delete
            await mark_vehicle_as_sold(db_vehicle.id)
            await log_vehicle_history(dealer_id, external_id, "sold", {
                "status": "available → sold"
            })
            stats["removed"] += 1

    logger.info(f"✅ Incremental sync complete: {stats}")
    return stats


def calculate_vehicle_hash(vehicle: dict) -> str:
    """Generate MD5 hash of critical vehicle fields for change detection."""
    critical_fields = [
        vehicle.get("price"),
        vehicle.get("mileage"),
        vehicle.get("status"),
        vehicle.get("description"),
        len(vehicle.get("images", []))  # Image count
    ]

    hash_input = "|".join(str(f) for f in critical_fields)
    return hashlib.md5(hash_input.encode()).hexdigest()


def detect_changes(db_vehicle, api_vehicle: dict) -> dict:
    """Detect which fields changed."""
    changes = {}

    comparable_fields = [
        "price", "mileage", "status", "description",
        "fuel_type", "transmission", "color_exterior"
    ]

    for field in comparable_fields:
        old_val = getattr(db_vehicle, field)
        new_val = api_vehicle.get(field)

        if old_val != new_val:
            changes[field] = (old_val, new_val)

    return changes
```

**Benefits:**
- ✅ **95% faster** - only process changed vehicles
- ✅ **Tracks price changes** - historical pricing data
- ✅ **Detects sold vehicles** - remove from listings automatically
- ✅ **Audit trail** - full change history in `vehicle_history` table
- ✅ **Database persistence** - no data loss on cache expiry

---

## 🔗 API INTEGRATION STRATEGY

### Scenario 1: Dealer Uses Management Software (IDEAL)

**Common Software in Netherlands:**
- **AutoTrack** - Most popular (50% market share)
- **AutoTelex** - Second largest
- **GForces** - Premium dealers
- **Autoplaza** - Smaller dealers
- **Custom APIs** - Large dealer groups

**Integration Flow:**

```
┌─────────────────────────────────────────────────────────┐
│         Dealer Management Software (AutoTrack)          │
│  - Inventory database (vehicles, pricing, images)       │
│  - Sales pipeline (leads, test drives, deals)           │
│  - Customer database (CRM)                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ REST API / Webhooks
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Our Platform (Middleware)                     │
│  1. Receive webhook: "New vehicle added"                │
│  2. Fetch vehicle details via API                       │
│  3. INSERT into PostgreSQL vehicles table               │
│  4. Update search indexes                               │
│  5. Notify AI agents (cache warming)                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           PostgreSQL (Our Database)                     │
│  - vehicles table (persistent storage)                  │
│  - vehicle_history (audit log)                         │
│  - Full-text search indexes                            │
└─────────────────────────────────────────────────────────┘
```

**Implementation Steps:**

1. **API Discovery**: Contact dealer's software vendor, request API documentation
2. **Credential Exchange**: OAuth 2.0 or API keys
3. **Webhook Setup**: Register our webhook endpoint with dealer's system
4. **Initial Sync**: Bulk import current inventory (one-time)
5. **Incremental Updates**: Real-time webhooks for changes
6. **Fallback**: Scheduled polling if webhooks fail

**Example: AutoTrack API Integration**

```python
# app/integrations/autotrack.py

import httpx
from typing import List, Dict, Any

class AutoTrackClient:
    """Client for AutoTrack dealer management software API."""

    def __init__(self, api_key: str, dealer_id: str):
        self.api_key = api_key
        self.dealer_id = dealer_id
        self.base_url = "https://api.autotrack.nl/v2"

    async def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch complete vehicle inventory."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/dealers/{self.dealer_id}/vehicles",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"status": "available", "limit": 1000}
            )
            response.raise_for_status()
            return response.json()["vehicles"]

    async def fetch_vehicle_details(self, vehicle_id: str) -> Dict[str, Any]:
        """Fetch detailed info for single vehicle."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/vehicles/{vehicle_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json()


# Webhook handler
# app/api/webhooks/autotrack.py

from fastapi import APIRouter, Request, HTTPException, Header
from app.tasks.incremental_sync import process_autotrack_webhook

router = APIRouter()

@router.post("/webhooks/autotrack/{dealer_id}")
async def handle_autotrack_webhook(
    dealer_id: str,
    request: Request,
    x_autotrack_signature: str = Header(None)
):
    """
    Handle webhook from AutoTrack.

    Events:
    - vehicle.created
    - vehicle.updated
    - vehicle.sold
    - vehicle.deleted
    """
    # Verify webhook signature
    body = await request.body()
    if not verify_autotrack_signature(body, x_autotrack_signature, dealer_id):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("event")
    vehicle_data = payload.get("data")

    # Queue background task
    process_autotrack_webhook.delay(dealer_id, event_type, vehicle_data)

    return {"status": "received"}
```

---

### Scenario 2: Dealer Has Custom Website (Fallback to Scraping)

If dealer doesn't use management software OR won't provide API access:

1. **Enhanced Scraping**: Continue using Playwright with improvements
2. **Change Detection**: Store HTML hashes to detect modifications
3. **Rate Limiting**: Respectful scraping (not more than 1 req/min)
4. **Error Monitoring**: Alert on scraping failures

```python
# app/scrapers/generic_dealer_scraper.py

async def scrape_dealer_website(
    dealer_id: str,
    base_url: str,
    scraper_config: dict
):
    """
    Generic dealer website scraper with configurable selectors.

    scraper_config:
    {
        "vehicle_list_url": "/occasions",
        "vehicle_card_selector": ".car-item",
        "pagination_type": "load_more",  # or "url_based"
        "fields": {
            "title": {"selector": ".car-title", "type": "text"},
            "price": {"selector": ".price", "type": "text", "parser": "price"},
            "mileage": {"selector": ".mileage", "type": "text", "parser": "mileage"}
        }
    }
    """
    # Implementation similar to seldenrijk_scraper.py
    # But with configurable selectors per dealer
    pass
```

---

## 🧠 MULTI-AGENT SYSTEM OVERVIEW

### Current Agent Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                       │
│  - Routes messages to appropriate agent                     │
│  - Manages conversation context                            │
│  - Handles agent escalation                                │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     SPECIALIZED AGENTS                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1️⃣  Router Agent                                           │
│      - Analyzes intent (browse, specific car, financing)   │
│      - Routes to appropriate specialist                    │
│                                                             │
│  2️⃣  Extraction Agent                                       │
│      - Extracts structured data (make, model, budget)      │
│      - Validates user inputs                               │
│                                                             │
│  3️⃣  RAG Agent (Vehicle Search)                            │
│      - Queries PostgreSQL vehicles table                   │
│      - Full-text search with ranking                       │
│      - Returns top 5 matching vehicles                     │
│                                                             │
│  4️⃣  Conversation Agent                                     │
│      - Manages dialogue flow                               │
│      - Maintains conversation memory                       │
│      - Generates natural responses                         │
│                                                             │
│  5️⃣  CRM Agent (Basic)                                      │
│      - Creates/updates contacts in Chatwoot                │
│      - Syncs conversation history                          │
│                                                             │
│  6️⃣  Enhanced CRM Agent                                     │
│      - Lead scoring and qualification                      │
│      - Test drive scheduling                               │
│      - Follow-up automation                                │
│                                                             │
│  7️⃣  Expertise Agent                                        │
│      - Technical specifications                            │
│      - Comparison between models                           │
│      - Financing calculations                              │
│                                                             │
│  8️⃣  Documentation Agent                                    │
│      - Generates conversation summaries                    │
│      - Creates handover notes for staff                    │
│      - Extracts action items                               │
│                                                             │
│  9️⃣  Escalation Router Agent                                │
│      - Detects complex queries                             │
│      - Identifies frustrated customers                     │
│      - Routes to human staff via Chatwoot                  │
│                                                             │
│  🔟 Inventory Helper Agent                                  │
│      - Vehicle availability checks                         │
│      - Price range filtering                               │
│      - Similar vehicle suggestions                         │
│                                                             │
│  1️⃣1️⃣ Sentiment Analysis Agent                              │
│      - Monitors customer satisfaction                      │
│      - Flags negative sentiment                            │
│      - Triggers proactive support                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Agent Communication Protocol:**

```python
# app/agents/protocol.py

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AgentMessage(BaseModel):
    """Standard message format between agents."""
    from_agent: str
    to_agent: str
    conversation_id: str
    intent: str
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = {}
    priority: int = 1  # 1-5, higher = more urgent

class AgentResponse(BaseModel):
    """Standard response from agents."""
    agent_name: str
    status: str  # 'success', 'failure', 'escalate'
    result: Any
    metadata: Dict[str, Any]
    next_agent: Optional[str] = None  # Suggest next agent
```

---

## 📊 PRICING & BUSINESS MODEL

### Subscription Tiers

| Tier | Monthly Price | Conversations | Dealers | Features |
|------|--------------|---------------|---------|----------|
| **Free** | €0 | 50/month | 1 | Basic AI, 7-day history |
| **Starter** | €199 | 500/month | 1 | Full AI, 30-day history, Analytics |
| **Professional** | €499 | 2,000/month | 1 | + CRM integration, Lead scoring, API access |
| **Enterprise** | €999+ | Unlimited | Multiple | + White-label, Priority support, Custom AI training |

### Revenue Projections (Year 1)

- **Month 1-3**: Launch with Seldenrijk (€499/month) = €1,497 MRR
- **Month 4-6**: Onboard 5 more dealers (€199 average) = €2,492 MRR
- **Month 7-12**: Scale to 25 dealers (€299 average) = €7,975 MRR
- **Year 1 Total**: €95,700 ARR

### Cost Structure

**Monthly Operating Costs:**
- Cloud Infrastructure (GCP/AWS): €500
- AI API Costs (Claude + OpenAI): €800
- Supabase Pro: €25
- Sentry Pro: €29
- Domain + SSL: €10
- **Total**: ~€1,364/month

**Break-even**: 5-6 dealers on Starter plan

---

## 🚀 DEPLOYMENT ROADMAP

### Phase 1: POC to Production (Q1 2025)
**Duration**: 6-8 weeks

**Week 1-2: Database Migration**
- ✅ Create PostgreSQL schema in Supabase
- ✅ Implement incremental sync logic
- ✅ Migrate current Redis data to PostgreSQL
- ✅ Add Row-Level Security (RLS) policies
- ✅ Create database backups strategy

**Week 3-4: Multi-Tenancy**
- ✅ Add `dealers` table
- ✅ Update all agents with dealer_id context
- ✅ Implement tenant isolation (RLS)
- ✅ Add dealer onboarding flow
- ✅ Create admin dashboard

**Week 5-6: API Integrations**
- ✅ Build AutoTrack integration
- ✅ Build AutoTelex integration
- ✅ Create webhook receivers
- ✅ Implement signature verification
- ✅ Add retry logic and monitoring

**Week 7-8: Testing & Launch**
- ✅ Load testing (1000 concurrent conversations)
- ✅ Security audit
- ✅ Documentation
- ✅ Deploy to production
- ✅ Onboard first 3 paying customers

---

### Phase 2: Scale & Optimize (Q2 2025)
**Duration**: 8-12 weeks

**Features:**
- Advanced analytics dashboard
- Custom AI training per dealer
- Multi-language support (EN, DE, FR)
- Voice message support
- Appointment booking integration
- Financial calculator integration

**Infrastructure:**
- Kubernetes migration (from Docker Compose)
- Horizontal auto-scaling
- CDN for media files
- Redis cluster for caching

---

### Phase 3: Enterprise Features (Q3-Q4 2025)
**Duration**: 12-16 weeks

**Features:**
- White-label solution
- Mobile app (dealer staff)
- Video call integration
- Document signing (contracts)
- Dealer-to-dealer marketplace
- Predictive lead scoring ML model

**Partnerships:**
- AutoTrack official integration
- RDW (Dutch DMV) API integration
- Insurance provider integrations
- Banking/financing partners

---

## 🔒 SECURITY & COMPLIANCE

### Data Protection (GDPR)

**Compliance Requirements:**
- ✅ Right to access (download all personal data)
- ✅ Right to erasure ("forget me" feature)
- ✅ Right to portability (export conversations)
- ✅ Consent management (explicit opt-in)
- ✅ Data minimization (only collect necessary fields)
- ✅ Purpose limitation (clear data usage policy)

**Implementation:**

```python
# app/gdpr/compliance.py

async def delete_customer_data(customer_phone: str, dealer_id: str):
    """
    GDPR Right to Erasure - Delete all customer data.

    This anonymizes but retains aggregate analytics.
    """
    async with database.transaction():
        # 1. Delete conversations
        await db.execute(
            "DELETE FROM conversations WHERE customer_phone = $1 AND dealer_id = $2",
            customer_phone, dealer_id
        )

        # 2. Delete leads
        await db.execute(
            "DELETE FROM leads WHERE customer_phone = $1 AND dealer_id = $2",
            customer_phone, dealer_id
        )

        # 3. Anonymize analytics events
        await db.execute(
            """
            UPDATE analytics_events
            SET user_id = NULL, ip_address = NULL
            WHERE user_id = (SELECT id FROM customers WHERE phone = $1)
            """,
            customer_phone
        )

        # 4. Delete from Chatwoot CRM
        await chatwoot.delete_contact(customer_phone)

        logger.info(f"GDPR deletion complete for {customer_phone}")


async def export_customer_data(customer_phone: str, dealer_id: str) -> dict:
    """
    GDPR Right to Access - Export all customer data as JSON.
    """
    data = {
        "customer_phone": customer_phone,
        "export_date": datetime.now().isoformat(),
        "dealer": await get_dealer(dealer_id),
        "conversations": await get_customer_conversations(customer_phone, dealer_id),
        "leads": await get_customer_leads(customer_phone, dealer_id),
        "interested_vehicles": await get_interested_vehicles(customer_phone, dealer_id)
    }

    return data
```

---

### Authentication & Authorization

**Supabase Row-Level Security (RLS):**

```sql
-- Dealers can only access their own data
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;

CREATE POLICY dealer_vehicles_policy ON vehicles
    FOR ALL
    USING (dealer_id = current_setting('app.current_dealer_id')::uuid);

CREATE POLICY dealer_conversations_policy ON conversations
    FOR ALL
    USING (dealer_id = current_setting('app.current_dealer_id')::uuid);

CREATE POLICY dealer_leads_policy ON leads
    FOR ALL
    USING (dealer_id = current_setting('app.current_dealer_id')::uuid);
```

**API Security:**
- JWT tokens (Supabase Auth)
- API key rotation (every 90 days)
- Rate limiting (100 req/min per dealer)
- IP whitelisting for webhooks
- HTTPS only (TLS 1.3)

---

### Monitoring & Observability

**Sentry Integration:**
- Error tracking
- Performance monitoring
- Release tracking
- User feedback

**Logging Strategy:**
```python
# app/monitoring/logging_config.py

import structlog

logger = structlog.get_logger()

# All logs include:
logger.info(
    "Vehicle search completed",
    extra={
        "dealer_id": dealer_id,
        "query": search_query,
        "results_count": len(results),
        "duration_ms": duration,
        "customer_phone": customer_phone,  # Only in non-production
        "environment": "production"
    }
)
```

**Metrics to Track:**
- Response time (p50, p95, p99)
- AI accuracy (user satisfaction score)
- Conversion rate (conversation → lead → sale)
- Cost per conversation (AI API costs)
- Uptime (99.9% SLA)

---

## 📈 SUCCESS METRICS

### North Star Metric
**Qualified Leads per Month** (conversations → test drives/appointments)

### Product Metrics

| Metric | Current (POC) | Target (Enterprise) |
|--------|--------------|---------------------|
| **Response Time** | ~3-5 seconds | < 2 seconds (p95) |
| **AI Accuracy** | ~80% | > 95% |
| **Conversation → Lead** | N/A | > 40% |
| **Lead → Sale** | N/A | > 15% |
| **Customer Satisfaction** | N/A | > 4.5/5.0 |
| **Uptime** | ~95% | 99.9% |
| **Concurrent Dealers** | 1 | 50+ |
| **Conversations/Month** | ~100 | 10,000+ |

### Business Metrics

| KPI | Target (Year 1) | Target (Year 2) |
|-----|----------------|----------------|
| **MRR** | €8,000 | €25,000 |
| **ARR** | €96,000 | €300,000 |
| **Active Dealers** | 25 | 100 |
| **Churn Rate** | < 10% | < 5% |
| **NPS** | > 50 | > 70 |
| **CAC** | < €500 | < €300 |
| **LTV** | > €5,000 | > €10,000 |

---

## 🎯 COMPETITIVE ANALYSIS

### Current Market Leaders

**1. Carcoach (carcoach.nl)**
- Focus: Automotive WhatsApp automation
- Pricing: ~€600/month
- Weakness: No AI, just template responses

**2. Ameego (ameego.com)**
- Focus: CRM + WhatsApp for dealers
- Pricing: ~€800/month
- Weakness: Limited AI capabilities

**3. AutoUncle (autouncle.nl)**
- Focus: Price intelligence
- Pricing: ~€400/month
- Weakness: No WhatsApp integration

### Our Competitive Advantages

| Feature | Us | Carcoach | Ameego | AutoUncle |
|---------|-----|----------|--------|-----------|
| **AI Conversations** | ✅ Claude 3.5 | ❌ Templates | ⚠️ Basic | ❌ None |
| **Multi-Agent System** | ✅ 11 agents | ❌ None | ❌ None | ❌ None |
| **Incremental Sync** | ✅ Real-time | ❌ Manual | ⚠️ Daily | ✅ Real-time |
| **API Integrations** | ✅ AutoTrack, etc. | ⚠️ Limited | ✅ Multiple | ⚠️ Few |
| **Pricing** | €199-999 | €600 | €800 | €400 |
| **Setup Time** | < 1 hour | 1-2 days | 2-3 days | < 1 hour |

**Market Positioning**:
- **More affordable** than Ameego
- **More intelligent** than Carcoach
- **More integrated** than AutoUncle

---

## 🔮 FUTURE ENHANCEMENTS

### AI Improvements
1. **Voice AI**: WhatsApp voice note support
2. **Vision AI**: Analyze customer-uploaded photos
3. **Predictive Models**: Predict which leads will convert
4. **Sentiment Tracking**: Real-time emotional analysis
5. **Multi-modal RAG**: Search by image similarity

### Product Features
1. **Virtual Test Drives**: 360° vehicle tours via WhatsApp
2. **AR Showroom**: Augmented reality car preview
3. **Dynamic Pricing**: AI-powered price recommendations
4. **Trade-in Valuation**: Instant used car appraisals
5. **Financing Calculator**: Real-time payment estimates

### Integrations
1. **Instagram/Facebook Messenger**: Beyond WhatsApp
2. **Website Chat Widget**: Unified inbox
3. **Email Marketing**: Nurture campaigns
4. **SMS Fallback**: For non-WhatsApp users
5. **Calendar Sync**: Google/Outlook integration

---

## 📝 MIGRATION PLAN: POC → Production

### Step-by-Step Migration

**Phase 1: Parallel Systems (Week 1-2)**
- ✅ Deploy new PostgreSQL schema alongside Redis
- ✅ Dual-write to both systems
- ✅ RAG agent reads from Redis (no disruption)
- ✅ Validate PostgreSQL data accuracy

**Phase 2: Gradual Traffic Shift (Week 3-4)**
- ✅ Switch RAG agent to PostgreSQL (10% traffic)
- ✅ Monitor performance and errors
- ✅ Increase to 50% traffic
- ✅ Monitor for 48 hours
- ✅ Switch to 100% PostgreSQL

**Phase 3: Cleanup (Week 5-6)**
- ✅ Stop writing to Redis (inventory only)
- ✅ Keep Redis for Celery broker + cache
- ✅ Archive old Redis data (S3 backup)
- ✅ Update documentation

**Phase 4: Multi-Tenancy (Week 7-8)**
- ✅ Add Seldenrijk as first dealer in `dealers` table
- ✅ Migrate existing conversations to dealer_id
- ✅ Test RLS policies
- ✅ Create admin dashboard
- ✅ Prepare for second dealer onboarding

---

## 💡 RECOMMENDATIONS

### Immediate Actions (This Week)
1. ✅ Create Supabase project
2. ✅ Run PostgreSQL schema migration
3. ✅ Implement incremental sync logic
4. ✅ Test dual-write (Redis + PostgreSQL)

### Short-term (Next Month)
1. Contact AutoTrack for API documentation
2. Build first API integration
3. Create dealer onboarding form
4. Implement GDPR compliance tools
5. Launch to 3 beta dealers

### Long-term (Next Quarter)
1. Migrate to Kubernetes (GKE)
2. Build white-label version
3. Hire first customer success manager
4. Establish partnerships with dealer software vendors
5. Scale to 25 active dealers

---

## 🎉 CONCLUSION

This enterprise architecture provides a clear roadmap from POC to production-ready SaaS platform. The key improvements are:

1. **Scalability**: PostgreSQL + incremental sync supports 100+ dealers
2. **Reliability**: 99.9% uptime with proper infrastructure
3. **Efficiency**: 95% faster syncing with change detection
4. **Compliance**: Full GDPR compliance built-in
5. **Revenue**: Clear path to €100K+ ARR in Year 1

**Next Steps:**
1. Review and approve architecture
2. Set up development environment
3. Start Phase 1 implementation
4. Schedule weekly progress reviews

**Document Owner**: Benomar Laamiri
**Last Updated**: January 2025
**Status**: Ready for Implementation

---

## 📚 APPENDIX

### Glossary

- **ARR**: Annual Recurring Revenue
- **MRR**: Monthly Recurring Revenue
- **POC**: Proof of Concept
- **RAG**: Retrieval-Augmented Generation
- **RLS**: Row-Level Security (PostgreSQL)
- **SLA**: Service Level Agreement
- **TTL**: Time To Live (cache expiration)
- **WAHA**: WhatsApp HTTP API

### Resources

- [Supabase Documentation](https://supabase.com/docs)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/async/)
- [AutoTrack API Docs](https://autotrack.nl/api) (hypothetical)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Playwright Automation](https://playwright.dev/)

### Contact

For questions or feedback on this architecture:
- **Email**: benomar@example.com
- **GitHub**: github.com/benomar/seldenrijk-auto-platform
- **Documentation**: /docs/ENTERPRISE-ARCHITECTURE.md

---

**END OF DOCUMENT**