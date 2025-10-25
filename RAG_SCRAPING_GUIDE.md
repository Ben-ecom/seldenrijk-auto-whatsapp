# 🚗 RAG Scraping Guide - Seldenrijk Auto

## Overview

This guide documents the scraping strategy for retrieving real-time car inventory from:
1. **Seldenrijk Website** (https://seldenrijk.nl/aanbod-occasions)
2. **Marktplaats Dealer Profile** (https://www.marktplaats.nl/u/seldenrijk-bv/10866554/)

## ⚠️ Critical Requirements

- **NO WRONG CAR INFO**: Always include link to original listing
- **Fast changing inventory**: 100+ cars/week sold
- **Dual-source scraping**: Check both Marktplaats + website
- **Caching strategy**: 10-minute cache to prevent excessive requests
- **Fallback handling**: Always have "car not found" response ready

---

## 🌐 Seldenrijk Website Structure

### Base URL
```
https://seldenrijk.nl/aanbod-occasions
```

### Car Listing Structure

**Visible Text Pattern:**
```
[Make] [Model]
[Specifications] | [Features separated by |]
[Year]
[Mileage] km
[Transmission Type]
[Fuel Type]
Kopen
€ [Price],-
Financial lease v.a.
€ [Monthly Price],- p./m.
```

**Example from screenshot:**
```
Toyota Yaris
1.5 Hybrid Comfort | Camera | Navigatie | Climate control | Cruise control | Bluetooth
2016
137.035 km
Automaat
Hybride
Kopen
€ 10.400,-
Financial lease v.a.
€ 188,- p./m.
```

### Extraction Strategy

**Step 1: Navigate to occasions page**
```python
playwright_navigate("https://seldenrijk.nl/aanbod-occasions")
```

**Step 2: Get visible text content**
```python
content = playwright_get_visible_text()
```

**Step 3: Parse car listings**
The listings appear as a structured list with this pattern:
- Make/Model on first line
- Features separated by "|" on second line
- Year (4-digit number)
- Mileage (number + " km")
- Transmission (Automaat/Handgeschakeld)
- Fuel type (Benzine/Diesel/Elektrisch/Hybride)
- Price ("€ X.XXX,-")

**Step 4: Build search URL (if needed)**
Website appears to use client-side filtering, so we may need to:
- Load full page
- Parse all listings
- Filter in Python based on criteria

### Filtering Options Available

From the visible filter panel:
- **Merk/model** (Make/Model) - dropdown with all brands
- **Prijs** (Price) - range from €2.500 to >€150.000
- **Kilometerstand** (Mileage) - range from 0 to >200.000 km
- **Bouwjaar** (Build year) - range from 2006 to 2024
- **Transmissie** (Transmission) - Automaat/Handgeschakeld
- **Brandstof** (Fuel) - Benzine/Diesel/Elektrisch/Hybride/LPG
- **Carrosserie** (Body type) - SUV/Sedan/Hatchback/etc.

### Data Structure to Extract

```python
{
    "source": "seldenrijk_website",
    "make": "Toyota",
    "model": "Yaris",
    "full_title": "Toyota Yaris 1.5 Hybrid Comfort",
    "specifications": "1.5 Hybrid Comfort | Camera | Navigatie | Climate control",
    "year": 2016,
    "mileage": 137035,
    "transmission": "Automaat",
    "fuel_type": "Hybride",
    "price": 10400,
    "monthly_lease": 188,
    "features": ["Camera", "Navigatie", "Climate control", "Cruise control", "Bluetooth"],
    "url": "https://seldenrijk.nl/aanbod-occasions"  # Individual car page if available
}
```

---

## 🔵 Marktplaats Structure

### Base URL
```
https://www.marktplaats.nl/u/seldenrijk-bv/10866554/
```

### Search URL Pattern
```
https://www.marktplaats.nl/u/seldenrijk-bv/10866554/?query=[search_term]
```

### Car Listing Structure

**Visible Text Pattern:**
```
[Make] [Model] [Specs] | [Features separated by |]
[Full description in lowercase]
[Year]
[Mileage] km
NAP gecontroleerd (optional)
Financiering mogelijk
Onderhoudsboekje (optional)
Alle milieu/emissie zones
€ [Price],-
[Date posted]
Dagtopper (optional)
Seldenrijk B.V.
Harderwijk
```

**Example from screenshot:**
```
Skoda Octavia 1.4 TSI iV PHEV Business Edition | Trekhaak |
Skoda octavia 1.4 Tsi iv phev business edition | trekhaak | stoel & stuurverwarming | head-up | adaptive cruise | memory | par
2021
164.070 km
Financiering mogelijk
Onderhoudsboekje
Alle milieu/emissie zones
€ 17.900,-
Vandaag
Dagtopper
Seldenrijk B.V.
Harderwijk
```

### Key Identifiers

**Dealer Confirmation:**
- Every listing shows: "Seldenrijk B.V." and "Harderwijk"
- This ensures we only scrape their inventory

**Quality Indicators:**
- "NAP gecontroleerd" - Mileage verified
- "Onderhoudsboekje" - Service book available
- "Dagtopper" - Featured listing
- "Financiering mogelijk" - Financing available

### Extraction Strategy

**Step 1: Navigate to dealer profile**
```python
playwright_navigate("https://www.marktplaats.nl/u/seldenrijk-bv/10866554/")
```

**Step 2: Search for specific car (optional)**
```python
# If searching for specific make/model
search_url = f"https://www.marktplaats.nl/u/seldenrijk-bv/10866554/?query={make}+{model}"
playwright_navigate(search_url)
```

**Step 3: Get visible text**
```python
content = playwright_get_visible_text()
```

**Step 4: Parse listings**
Pattern:
- First line: Make Model Specs
- Second line: Full lowercase description
- Year (4-digit number)
- Mileage (number + " km")
- Price ("€ X.XXX,-")
- Date ("Vandaag", "Gisteren", or specific date)

### Filtering Available

From the sidebar:
- **Prijs** (Price) - van/tot
- **Categorie** (Category) - Auto's with brand breakdown
- **Conditie** (Condition) - Gebruikt (424 listings)
- **Aangeboden sinds** (Posted since) - Vandaag/Gisteren/Een week/Altijd

### Data Structure to Extract

```python
{
    "source": "marktplaats",
    "make": "Skoda",
    "model": "Octavia",
    "full_title": "Skoda Octavia 1.4 TSI iV PHEV Business Edition | Trekhaak |",
    "description": "skoda octavia 1.4 tsi iv phev business edition | trekhaak | stoel & stuurverwarming...",
    "year": 2021,
    "mileage": 164070,
    "price": 17900,
    "nap_verified": True,
    "service_book": True,
    "financing_available": True,
    "featured": True,
    "date_posted": "Vandaag",
    "dealer": "Seldenrijk B.V.",
    "location": "Harderwijk",
    "url": "[link to individual listing]"  # Extract from HTML if available
}
```

---

## 🤖 RAG Agent Implementation

### Recommended Flow

```python
class RAGAgent(BaseAgent):
    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        # 1. Extract customer criteria
        extraction = state.get("extraction_output", {})
        make = extraction.get("car_preferences", {}).get("make")
        model = extraction.get("car_preferences", {}).get("model")
        fuel_type = extraction.get("car_preferences", {}).get("fuel_type")
        max_price = extraction.get("car_preferences", {}).get("max_price")
        preferred_color = extraction.get("car_preferences", {}).get("preferred_color")

        # 2. Check cache first (10-minute cache)
        cache_key = f"{make}_{model}_{fuel_type}_{max_price}"
        cached_results = self._get_from_cache(cache_key)
        if cached_results:
            return cached_results

        # 3. Scrape both sources in parallel
        marktplaats_results = self._search_marktplaats(make, model, fuel_type)
        website_results = self._search_website(make, model, fuel_type)

        # 4. Combine and filter results
        all_results = marktplaats_results + website_results
        filtered_results = self._filter_by_criteria(
            all_results,
            max_price=max_price,
            fuel_type=fuel_type,
            preferred_color=preferred_color
        )

        # 5. Rank results (website first, then Marktplaats)
        ranked_results = self._rank_results(filtered_results)

        # 6. Cache results
        self._cache_results(cache_key, ranked_results)

        # 7. Return top 3 matches
        return {
            "rag_results": ranked_results[:3],
            "total_found": len(all_results),
            "filtered_count": len(filtered_results)
        }
```

### Caching Strategy

```python
import time
from functools import lru_cache

# Cache results for 10 minutes (600 seconds)
@lru_cache(maxsize=100)
def search_with_cache(query_hash: str, timestamp_bucket: int):
    # timestamp_bucket = current_time // 600
    # This forces cache refresh every 10 minutes
    return _actual_search(query_hash)

def _get_cache_timestamp():
    return int(time.time()) // 600  # 10-minute buckets
```

### Error Handling

```python
# Scenario 1: No results found
if len(rag_results) == 0:
    return {
        "rag_results": [],
        "total_found": 0,
        "response_hint": "Helaas heb ik geen exacte match gevonden. Kan ik je helpen met alternatieven?"
    }

# Scenario 2: Scraping failed
try:
    results = self._search_marktplaats(make, model, fuel_type)
except Exception as e:
    logger.error(f"Marktplaats scraping failed: {e}")
    # Try website as fallback
    results = self._search_website(make, model, fuel_type)
```

---

## 🎯 Ranking Logic

### Priority Order:
1. **Source**: Website listings > Marktplaats listings (our inventory first)
2. **Exact match**: Exact make/model/fuel match > similar matches
3. **Price**: Closer to customer budget = higher score
4. **Recency**: Newer listings > older listings
5. **Mileage**: Lower mileage = higher score (if specified)
6. **Color**: Matches preferred color = bonus points

### Ranking Function:

```python
def _rank_results(self, results: List[Dict], criteria: dict) -> List[Dict]:
    for result in results:
        score = 0

        # Source priority (website first)
        if result["source"] == "seldenrijk_website":
            score += 100

        # Exact match bonus
        if result["make"].lower() == criteria.get("make", "").lower():
            score += 50
        if result["model"].lower() in criteria.get("model", "").lower():
            score += 50
        if result["fuel_type"].lower() == criteria.get("fuel_type", "").lower():
            score += 30

        # Price score (closer to max_price = better)
        max_price = criteria.get("max_price", float('inf'))
        if result["price"] <= max_price:
            price_diff = max_price - result["price"]
            score += min(20, (20 - (price_diff / 1000)))

        # Recency bonus (Marktplaats only)
        if result.get("date_posted") == "Vandaag":
            score += 10
        elif result.get("date_posted") == "Gisteren":
            score += 5

        # Mileage bonus (lower is better)
        max_mileage = criteria.get("max_mileage")
        if max_mileage and result["mileage"] < max_mileage:
            score += 10

        # Color match
        preferred_color = criteria.get("preferred_color", "").lower()
        if preferred_color and preferred_color in result.get("full_title", "").lower():
            score += 15

        result["relevance_score"] = score

    # Sort by score (highest first)
    return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
```

---

## 🚨 Error Prevention

### Always Include Links
```python
response = f"""
Perfect! We hebben een {car['make']} {car['model']} gevonden:

- Bouwjaar: {car['year']}
- Kilometerstand: {car['mileage']:,} km
- Brandstof: {car['fuel_type']}
- Prijs: €{car['price']:,}

**Bekijk de advertentie:** {car['url']}

Kloppen deze gegevens? Dan kan ik een afspraak inplannen!
"""
```

### Timestamp Info
```python
from datetime import datetime

footer = f"""
ℹ️ Prijsinformatie van {datetime.now().strftime('%d-%m-%Y %H:%M')}
Let op: Prijzen en beschikbaarheid kunnen wijzigen.
"""
```

### Car Not Available
```python
if not rag_results:
    alternative_response = """
Helaas heb ik geen exacte match gevonden voor een Golf 8 diesel onder €25.000.

Maar ik heb wel deze alternatieven:
- Golf 7 2.0 TDI - €22.900 - 2019
- Golf 8 1.5 TSI (benzine) - €24.500 - 2020

Wil je meer info over één van deze auto's?
"""
```

---

## 📊 Testing Strategy

### Test Cases

**Test 1: Exact Match**
```
Query: "Ik zoek een Golf 8 diesel, budget €25.000, zwart"
Expected: Find exact Golf 8 diesel, filter by price and color
```

**Test 2: No Match**
```
Query: "Ik zoek een Ferrari F40"
Expected: Return empty results, suggest alternatives
```

**Test 3: Partial Match**
```
Query: "Golf diesel onder 20k"
Expected: Return all Golf diesels under €20.000 (Golf 7, Golf 8, etc.)
```

**Test 4: Cache Hit**
```
Query 1: "Golf 8" at 10:00
Query 2: "Golf 8" at 10:05
Expected: Second query uses cached results (no scraping)
```

---

## 🛠️ Implementation Priority

### Phase 1: Marktplaats Scraper (Week 5)
✅ **Why first**: Public, easier to test, clear structure
- Implement `_search_marktplaats()` method
- Parse listings with Playwright
- Test with real queries
- Add to conversation agent

### Phase 2: Website Scraper (Week 6)
- Implement `_search_website()` method
- Combine with Marktplaats results
- Add ranking logic
- Test dual-source scraping

### Phase 3: Advanced Features (Week 7+)
- Image extraction
- Similar car suggestions
- Price comparison
- Availability check (is listing still active?)

---

## 📝 Next Steps

1. ✅ Create `app/agents/rag_agent.py`
2. ✅ Update extraction models (CarPreferences)
3. ✅ Update conversation agent prompt (automotive)
4. ✅ Update CRM agent (car attributes)
5. ✅ Test with: "Ik zoek een Golf 8 diesel, budget €25.000, zwart"

**Expected Result:**
```
Agent: "Perfect! Ik heb 2 Golf 8 diesel gevonden binnen je budget:

1. VW Golf 8 2.0 TDI - €24.950 - 45.000 km - Zwart
   Bekijk: https://marktplaats.nl/...

2. VW Golf 8 1.6 TDI - €23.500 - 62.000 km - Grijs
   Bekijk: https://seldenrijk.nl/...

Wil je meer details over één van deze auto's?"
```
