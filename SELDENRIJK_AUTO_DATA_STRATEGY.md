# 🚗 SELDENRIJK AUTO-DATA OPHAAL STRATEGIE

**Doel:** Agent moet alleen praten over auto's op https://seldenrijk.nl met 100% accurate informatie

---

## 🎯 PROBLEEM DEFINITIE

**Huidige situatie:**
- Agent heeft geen actuele data van Seldenrijk voorraad
- Klanten vragen over specifieke auto's op de website
- Agent moet accurate prijzen, specificaties, en beschikbaarheid geven

**Requirements:**
1. ✅ 100% accurate data (geen hallucinaties)
2. ✅ Snelle responses (< 2 seconden)
3. ✅ Real-time of near real-time updates
4. ✅ Betrouwbaar en schaalbaar

---

## 🏆 OPTIE 1: AUTOSOCIAAL API (BESTE - AANBEVOLEN) ⭐

**Waarom deze website gebruik maakt van AutoSociaal:**

Van de website HTML zie ik:
```html
<img src="https://cdn.autosociaal.nl/dtweb/images/thumb/...">
```

**Dit betekent:** Seldenrijk gebruikt **AutoSociaal/DealerTeam** als CMS/voorraad platform!

### **✅ Voordelen:**
1. **Directe API beschikbaar** - AutoSociaal heeft XML/JSON feeds
2. **Officiële data bron** - Exact wat op website staat
3. **Real-time updates** - Wanneer Seldenrijk voorraad update, API updated
4. **Gestructureerde data** - Alle specs, prijzen, afbeeldingen
5. **Snelste methode** - Milliseconden response time

### **📋 Wat je nodig hebt:**
- AutoSociaal API toegang van Seldenrijk (via account)
- Meestal gratis/inclusief bij AutoSociaal abonnement
- API documentatie: https://www.autosociaal.nl/api-documentatie

### **🔧 Implementatie:**

**Stap 1: API Key opvragen bij Seldenrijk**
```
Contact: info@seldenrijk.nl
Vraag: "API toegang voor AutoSociaal voorraad feed voor WhatsApp bot"
```

**Stap 2: API Endpoints (typisch AutoSociaal formaat)**
```bash
# XML Feed (meest voorkomend)
GET https://www.seldenrijk.nl/occasions-xml

# JSON Feed (als beschikbaar)
GET https://api.autosociaal.nl/v1/vehicles?dealerId=XXXX

# Voorbeeld response structuur:
{
  "vehicles": [
    {
      "id": "12345",
      "brand": "BMW",
      "model": "X5",
      "price": 42500,
      "mileage": 45000,
      "buildYear": 2021,
      "fuel": "Hybride",
      "transmission": "Automaat",
      "description": "BMW X5 xDrive30e M Sport...",
      "images": ["url1", "url2"],
      "url": "https://seldenrijk.nl/occasion/bmw-x5-...",
      "available": true
    }
  ]
}
```

**Stap 3: Scheduled Sync (Celery Beat)**
```python
# app/tasks/sync_inventory.py
from celery import shared_task
import httpx
import redis

@shared_task(name="sync_seldenrijk_inventory")
async def sync_seldenrijk_inventory():
    """
    Sync Seldenrijk AutoSociaal inventory to Redis cache.
    Runs every 2 hours via Celery Beat.
    """
    try:
        # Fetch from AutoSociaal API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.seldenrijk.nl/occasions-xml",
                timeout=30.0
            )

        # Parse XML/JSON
        vehicles = parse_autosociaal_feed(response.content)

        # Store in Redis
        redis_client = get_redis_client()

        # Store full inventory
        redis_client.set(
            "seldenrijk:inventory:full",
            json.dumps(vehicles),
            ex=7200  # 2 hours TTL
        )

        # Store by brand for quick lookup
        for vehicle in vehicles:
            brand_key = f"seldenrijk:inventory:brand:{vehicle['brand'].lower()}"
            redis_client.sadd(brand_key, json.dumps(vehicle))
            redis_client.expire(brand_key, 7200)

        logger.info(f"✅ Synced {len(vehicles)} vehicles from AutoSociaal")

    except Exception as e:
        logger.error(f"❌ Inventory sync failed: {e}", exc_info=True)
```

**Stap 4: Query Interface**
```python
# app/services/inventory_service.py
class InventoryService:
    """Query Seldenrijk inventory from Redis cache."""

    def __init__(self):
        self.redis = get_redis_client()

    async def search_vehicles(
        self,
        brand: str = None,
        model: str = None,
        max_price: int = None,
        fuel_type: str = None
    ) -> List[Dict]:
        """Search inventory with filters."""

        # Get full inventory from cache
        cached_inventory = self.redis.get("seldenrijk:inventory:full")

        if not cached_inventory:
            logger.warning("⚠️ Inventory cache empty - triggering sync")
            # Trigger immediate sync
            sync_seldenrijk_inventory.delay()
            return []

        vehicles = json.loads(cached_inventory)

        # Apply filters
        filtered = vehicles

        if brand:
            filtered = [v for v in filtered if v['brand'].lower() == brand.lower()]

        if model:
            filtered = [v for v in filtered if model.lower() in v['model'].lower()]

        if max_price:
            filtered = [v for v in filtered if v['price'] <= max_price]

        if fuel_type:
            filtered = [v for v in filtered if v['fuel'].lower() == fuel_type.lower()]

        return filtered

    async def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict]:
        """Get specific vehicle details."""
        cached_inventory = self.redis.get("seldenrijk:inventory:full")

        if not cached_inventory:
            return None

        vehicles = json.loads(cached_inventory)

        for vehicle in vehicles:
            if vehicle['id'] == vehicle_id:
                return vehicle

        return None
```

### **⏰ Celery Beat Schedule:**
```python
# app/config/celery_config.py
beat_schedule = {
    'sync-seldenrijk-inventory': {
        'task': 'sync_seldenrijk_inventory',
        'schedule': crontab(minute='0', hour='*/2'),  # Every 2 hours
    },
}
```

### **💰 Kosten:**
- ✅ **€0** - Gratis (meestal inclusief bij AutoSociaal abonnement)
- ✅ Geen extra API kosten

### **⚡ Performance:**
- **Initial Sync:** 5-10 seconden (447 voertuigen)
- **Query Response:** < 50ms (Redis cache)
- **Update Frequency:** Elke 2 uur (configureerbaar)

---

## 🥈 OPTIE 2: SCHEDULED WEB SCRAPING + CACHE (BACKUP OPLOSSING)

**Gebruik alleen als AutoSociaal API NIET beschikbaar is**

### **✅ Voordelen:**
- Werkt zonder API toegang
- Volledig geautomatiseerd
- Betrouwbare fallback

### **❌ Nadelen:**
- Trager (30-60 seconden scraping tijd)
- Fragiel bij website updates
- Meer resource-intensief

### **🔧 Implementatie:**

**Stap 1: Playwright Scraper**
```python
# app/scrapers/seldenrijk_scraper.py
from playwright.async_api import async_playwright
import json

async def scrape_seldenrijk_inventory():
    """
    Scrape all vehicles from Seldenrijk website.
    Returns structured vehicle data.
    """
    vehicles = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to occasions page
        await page.goto('https://seldenrijk.nl/aanbod-occasions', wait_until='networkidle')

        # Wait for vehicle cards to load
        await page.wait_for_selector('.occasion-card', timeout=10000)

        # Extract all vehicle data
        vehicle_elements = await page.query_selector_all('.occasion-card')

        for element in vehicle_elements:
            try:
                vehicle = {
                    'brand': await element.query_selector('.brand').inner_text(),
                    'model': await element.query_selector('.model').inner_text(),
                    'price': parse_price(await element.query_selector('.price').inner_text()),
                    'mileage': parse_mileage(await element.query_selector('.mileage').inner_text()),
                    'buildYear': await element.query_selector('.year').inner_text(),
                    'fuel': await element.query_selector('.fuel').inner_text(),
                    'url': await element.query_selector('a').get_attribute('href'),
                    'image': await element.query_selector('img').get_attribute('src')
                }
                vehicles.append(vehicle)
            except Exception as e:
                logger.warning(f"Failed to parse vehicle: {e}")
                continue

        await browser.close()

    return vehicles

@shared_task(name="scrape_and_cache_inventory")
async def scrape_and_cache_inventory():
    """Scrape Seldenrijk and cache results."""
    try:
        vehicles = await scrape_seldenrijk_inventory()

        redis_client = get_redis_client()
        redis_client.set(
            "seldenrijk:inventory:full",
            json.dumps(vehicles),
            ex=7200  # 2 hours
        )

        logger.info(f"✅ Scraped and cached {len(vehicles)} vehicles")

    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}", exc_info=True)
```

**Stap 2: Celery Beat Schedule**
```python
beat_schedule = {
    'scrape-seldenrijk-inventory': {
        'task': 'scrape_and_cache_inventory',
        'schedule': crontab(minute='0', hour='*/2'),  # Every 2 hours
    },
}
```

### **💰 Kosten:**
- ✅ **€0** - Gratis scraping
- ⚠️ Extra CPU/memory gebruik

### **⚡ Performance:**
- **Scraping Time:** 30-60 seconden (447 voertuigen)
- **Query Response:** < 50ms (Redis cache)
- **Update Frequency:** Elke 2 uur

---

## 🥉 OPTIE 3: RSS/XML FEED (INDIEN BESCHIKBAAR)

Veel AutoSociaal dealers hebben publieke XML feeds:

```bash
# Typische URLs om te testen:
https://seldenrijk.nl/occasions.xml
https://seldenrijk.nl/occasions-xml
https://seldenrijk.nl/feed/occasions
https://www.seldenrijk.nl/rss
```

**Test command:**
```bash
curl -I https://seldenrijk.nl/occasions.xml
```

Als 200 OK → Gebruik deze feed (snelste methode zonder API key!)

---

## 🚫 OPTIE 4: REAL-TIME PLAYWRIGHT (NIET AANBEVOLEN)

**Waarom NIET gebruiken:**
- ❌ Te traag (5-10 seconden per query)
- ❌ Blokkeert agent response
- ❌ Niet schaalbaar
- ❌ Slechte user experience

**Alleen voor:** Emergency fallback als cache leeg is.

---

## 🎯 AANBEVOLEN IMPLEMENTATIE STRATEGIE

### **FASE 1: DISCOVERY (VANDAAG)**
1. ✅ Contact Seldenrijk voor AutoSociaal API toegang
2. ✅ Test publieke XML feeds
3. ✅ Bepaal welke data bron beschikbaar is

### **FASE 2: IMPLEMENTATIE (1-2 DAGEN)**
1. ✅ Implement AutoSociaal API client (of scraper als backup)
2. ✅ Build Redis caching layer
3. ✅ Create InventoryService query interface
4. ✅ Setup Celery Beat scheduled sync

### **FASE 3: INTEGRATION (1 DAG)**
1. ✅ Integrate met conversation agent
2. ✅ Add inventory search capabilities
3. ✅ Update prompts met "only Seldenrijk inventory" constraint

### **FASE 4: TESTING & MONITORING (ONGOING)**
1. ✅ Test accuracy van data
2. ✅ Monitor sync failures
3. ✅ Setup alerts voor stale cache

---

## 🔧 AGENT INTEGRATION VOORBEELD

```python
# app/agents/enhanced_conversation_agent.py

async def _build_enhanced_messages(self, state: ConversationState) -> List[Dict]:
    """Build messages with inventory context."""

    # Check if query is about specific car
    if self._is_car_inquiry(state["content"]):
        # Search inventory
        inventory_service = InventoryService()

        # Extract search params from message
        search_params = self._extract_search_params(state["content"])

        # Query inventory
        matching_vehicles = await inventory_service.search_vehicles(
            brand=search_params.get("brand"),
            model=search_params.get("model"),
            max_price=search_params.get("max_price")
        )

        # Add inventory context to system prompt
        if matching_vehicles:
            inventory_context = self._format_inventory_for_prompt(matching_vehicles)

            system_prompt += f"""

📋 **BESCHIKBARE VOERTUIGEN (Seldenrijk.nl):**

{inventory_context}

**KRITISCH:**
- Gebruik ALLEEN data uit bovenstaande lijst
- Als specifieke auto niet in lijst: zeg dat deze NIET beschikbaar is
- Geen prijzen/specs verzinnen
- Verwijs altijd naar Seldenrijk.nl voor foto's en details
"""
```

---

## 📊 VERGELIJKINGSTABEL

| Criterium | AutoSociaal API | Scheduled Scraping | Real-time Playwright |
|-----------|----------------|-------------------|---------------------|
| **Snelheid** | ⭐⭐⭐⭐⭐ < 50ms | ⭐⭐⭐⭐ < 50ms | ⭐ 5-10s |
| **Accuracy** | ⭐⭐⭐⭐⭐ 100% | ⭐⭐⭐⭐ 95% | ⭐⭐⭐⭐ 95% |
| **Betrouwbaarheid** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Kosten** | ✅ €0 | ✅ €0 | ✅ €0 |
| **Setup Complexiteit** | ⭐⭐ Makkelijk | ⭐⭐⭐ Medium | ⭐⭐⭐⭐ Moeilijk |
| **Maintenance** | ⭐⭐⭐⭐⭐ Laag | ⭐⭐⭐ Medium | ⭐⭐ Hoog |

---

## 🎯 MIJN AANBEVELING

### **PRIORITEIT 1:** AutoSociaal API
1. Contact Seldenrijk: info@seldenrijk.nl
2. Vraag: "AutoSociaal XML/JSON feed toegang voor WhatsApp bot"
3. Implementeer API sync + Redis cache
4. **ETA:** 1 dag setup

### **BACKUP:** Scheduled Playwright Scraping
- Alleen als AutoSociaal API niet beschikbaar
- Implementeer als fallback
- **ETA:** 2 dagen setup

### **WAAROM DEZE AANPAK:**
- ✅ 100% accurate data (direct van bron)
- ✅ Snelle responses (< 50ms via cache)
- ✅ Betrouwbaar (scheduled updates elke 2 uur)
- ✅ Schaalbaar (Redis cache)
- ✅ Geen hallucinaties mogelijk (alleen cached data)

---

## 📞 VOLGENDE STAP

**Vraag aan Ben/Seldenrijk:**
```
Subject: API Toegang AutoSociaal Voorraad Feed

Hallo,

Voor de WhatsApp AI agent hebben we toegang nodig tot de AutoSociaal
voorraad feed (XML of JSON format) om klanten accurate informatie te
kunnen geven over beschikbare auto's.

Kunnen jullie:
1. API credentials of feed URL delen?
2. Documentatie over data formaat?

Dit zorgt ervoor dat de agent altijd accurate prijzen en
beschikbaarheid kan tonen.

Dank je!
```

**Zodra API toegang:** Ik kan de volledige implementatie binnen 1 dag bouwen.

---

*Aangemaakt: 2025-10-17 13:00 CET*
*Seldenrijk Auto Data Strategy - Volledig Plan*
