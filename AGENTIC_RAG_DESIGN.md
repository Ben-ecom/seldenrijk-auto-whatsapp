# 🚗 Agentic RAG Design voor Seldenrijk Auto

## Probleem Omschrijving

**Uitdaging:**
- 100+ auto's per week verkocht
- Stock verandert constant (nieuwe auto's, verkochte auto's, prijswijzigingen)
- Verkoper heeft Marktplaats + eigen website
- KRITIEK: Agent moet JUISTE auto vinden (geen verkeerde info geven!)

**Use Case:**
```
Klant: "Ik zoek een Golf 8 diesel, budget €25.000, liefst in zwart"

Agent moet:
1. Zoeken op Marktplaats + Website naar matching auto's
2. Filteren op: merk (VW), model (Golf 8), brandstof (diesel), prijs (<€25k), kleur (zwart)
3. Exacte match vinden
4. Specs + prijs + link geven
5. Als niet beschikbaar: alternatief voorstellen
```

---

## 🏗️ Architectuur

### **Option 1: Playwright MCP + RAG (RECOMMENDED)**

**Waarom deze:**
- Je hebt al Playwright MCP tool beschikbaar!
- Kan real-time scrapen tijdens gesprek
- Geen database onderhoud
- Altijd actuele data

**Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│ 1. Klant vraagt: "Golf 8 diesel, zwart, €25k"              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Router Agent: intent = "car_inquiry"                     │
│    Extraction Agent: merk=VW, model=Golf 8, fuel=diesel     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Conversation Agent: needs_rag = true                     │
│    rag_query = "VW Golf 8 diesel zwart max €25000"         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. RAG Agent (NEW):                                         │
│    - Navigate to Marktplaats search                         │
│    - Search: "Volkswagen Golf 8 diesel"                     │
│    - Extract listings (titel, prijs, km, link)              │
│    - Filter: prijs <= €25k, kleur contains "zwart"         │
│    - Navigate to website search (same process)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. RAG Results:                                             │
│    [                                                         │
│      {                                                       │
│        "source": "marktplaats",                             │
│        "title": "VW Golf 8 2.0 TDI - Zwart Metallic",      │
│        "price": 24950,                                       │
│        "mileage": 45000,                                     │
│        "year": 2021,                                         │
│        "url": "https://marktplaats.nl/...",                 │
│        "dealer": "Seldenrijk Auto"                          │
│      },                                                      │
│      ...                                                     │
│    ]                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Conversation Agent generates response:                   │
│    "Perfect! We hebben een VW Golf 8 2.0 TDI in zwart:     │
│     - Bouwjaar: 2021                                        │
│     - Kilometerstand: 45.000 km                             │
│     - Prijs: €24.950                                        │
│     - Link: [Marktplaats advertentie]                      │
│                                                             │
│     Wil je langskomen voor een bezichtiging?"               │
└─────────────────────────────────────────────────────────────┘
```

### **Implementation Steps**

#### **Step 1: Create RAG Agent** (`app/agents/rag_agent.py`)

```python
"""
RAG Agent - Real-time inventory search using Playwright MCP.

Uses Playwright to:
- Search Marktplaats for dealer listings
- Search dealer website for inventory
- Extract structured car data
- Filter based on customer preferences
"""

class RAGAgent(BaseAgent):
    def __init__(self):
        # Initialize with Playwright MCP tool access
        pass

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        # 1. Extract search criteria from state
        extraction = state.get("extraction_output")
        rag_query = state.get("conversation_output", {}).get("rag_query")

        # 2. Search Marktplaats
        marktplaats_results = self._search_marktplaats(extraction)

        # 3. Search dealer website
        website_results = self._search_website(extraction)

        # 4. Combine and rank results
        all_results = marktplaats_results + website_results
        ranked_results = self._rank_results(all_results, extraction)

        # 5. Return top 3 matches
        return {
            "rag_results": ranked_results[:3],
            "total_found": len(all_results)
        }

    def _search_marktplaats(self, criteria: dict) -> List[Dict]:
        """Search Marktplaats using Playwright MCP."""
        # Build search URL
        make = criteria.get("make", "")
        model = criteria.get("model", "")
        search_url = f"https://www.marktplaats.nl/l/auto-s/#{make}+{model}"

        # Use Playwright to navigate and extract
        # (This will use the mcp__playwright__playwright_navigate tool)
        results = []

        # Extract listings from page
        # (Using mcp__playwright__playwright_get_visible_html)

        return results

    def _search_website(self, criteria: dict) -> List[Dict]:
        """Search dealer website using Playwright MCP."""
        # Similar to Marktplaats search
        pass

    def _rank_results(self, results: List[Dict], criteria: dict) -> List[Dict]:
        """Rank results by relevance to customer criteria."""
        # Score based on:
        # - Price match (closer to budget = higher score)
        # - Exact model match vs similar models
        # - Color match
        # - Mileage match
        # - Recency of listing
        pass
```

#### **Step 2: Update Conversation Agent**

```python
# In conversation_agent.py

def _execute(self, state: ConversationState) -> Dict[str, Any]:
    # ... existing code ...

    # If needs_rag, trigger RAG agent
    if conversation_output["needs_rag"]:
        rag_agent = RAGAgent()
        rag_results = rag_agent.execute(state)

        # Add RAG results to state
        conversation_output["rag_results"] = rag_results["rag_results"]

    return conversation_output
```

#### **Step 3: Update State Management**

```python
# In orchestration/state.py

class ConversationOutput(TypedDict):
    response_text: str
    needs_rag: bool
    rag_query: Optional[str]
    rag_results: Optional[List[Dict[str, Any]]]  # ✅ Already exists!
    follow_up_questions: List[str]
    conversation_complete: bool
    sentiment: Literal["positive", "neutral", "negative"]
```

#### **Step 4: Update Extraction Models**

```python
# In extraction_agent.py

class CarPreferences(BaseModel):
    """Extracted car preferences."""
    make: Optional[str] = Field(None, description="Car make (VW, BMW, Mercedes)")
    model: Optional[str] = Field(None, description="Car model (Golf, 3-serie)")
    fuel_type: Optional[str] = Field(None, description="Fuel type (diesel, benzine, hybride)")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    max_mileage: Optional[int] = Field(None, description="Maximum mileage in km")
    preferred_color: Optional[str] = Field(None, description="Preferred color")
    min_year: Optional[int] = Field(None, description="Minimum build year")
```

---

## 🚀 Implementation Priority

### **Phase 1: Marktplaats Scraper (Week 5 - HIGH PRIORITY)**

**Why first:**
- Marktplaats is public (no authentication needed)
- Clear URL structure
- Reliable HTML structure
- Can test immediately

**Tasks:**
1. ✅ Create `rag_agent.py`
2. ✅ Implement Marktplaats search with Playwright MCP
3. ✅ Parse listings (title, price, mileage, link)
4. ✅ Filter based on criteria
5. ✅ Integrate with conversation agent

**Expected Result:**
```
Klant: "Golf 8 diesel €25k"
Agent: "Ik heb 3 Golf 8 diesel gevonden op Marktplaats:

1. VW Golf 8 2.0 TDI - €24.950 - 45.000 km - Zwart
   Link: https://marktplaats.nl/...

2. VW Golf 8 1.6 TDI - €23.500 - 62.000 km - Grijs
   Link: https://marktplaats.nl/...

Wil je meer details over één van deze auto's?"
```

### **Phase 2: Website Scraper (Week 6)**

**After Marktplaats works:**
- Add dealer website scraping
- Combine results from both sources
- Rank: website listings first (your inventory), then Marktplaats

### **Phase 3: Advanced Features (Week 7+)**

- Image extraction (show car photos)
- Similar car suggestions
- Price comparison
- Availability check (is car still listed?)

---

## 🔧 Technical Details

### **Playwright MCP Tools Available**

Je hebt deze tools al beschikbaar:
```python
# Navigate to page
mcp__playwright__playwright_navigate(url, headless=True)

# Get page HTML
mcp__playwright__playwright_get_visible_html(selector=None)

# Get text content
mcp__playwright__playwright_get_visible_text()

# Click elements
mcp__playwright__playwright_click(selector)

# Fill forms (for search)
mcp__playwright__playwright_fill(selector, value)

# Screenshot (for debugging)
mcp__playwright__playwright_screenshot(name)

# Close browser
mcp__playwright__playwright_close()
```

### **Marktplaats URL Structure**

```python
# Search URL format
base_url = "https://www.marktplaats.nl/l/auto-s/"

# Example searches
vw_golf = "https://www.marktplaats.nl/l/auto-s/#q:volkswagen+golf"
diesel_only = "https://www.marktplaats.nl/l/auto-s/#q:volkswagen+golf+diesel"
price_filter = "https://www.marktplaats.nl/l/auto-s/#q:volkswagen+golf&priceFrom:20000&priceTo:25000"

# Extract dealer listings only
# Filter by dealer name in listing
```

### **Data Extraction Pattern**

```python
# 1. Navigate to search page
playwright_navigate(search_url)

# 2. Get HTML
html = playwright_get_visible_html()

# 3. Parse with BeautifulSoup or regex
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# 4. Extract listings
listings = soup.find_all('article', class_='listing-card')

for listing in listings:
    title = listing.find('h3').text
    price = listing.find('span', class_='price').text
    details = listing.find('div', class_='details').text
    link = listing.find('a')['href']

    # Parse details (mileage, year, fuel type)
    # Store in structured format
```

### **Caching Strategy**

```python
# Cache scraped results for 10 minutes
# If same search within 10 min, use cached results
# This prevents excessive scraping

import time
from functools import lru_cache

@lru_cache(maxsize=100)
def search_with_cache(query_hash: str, timestamp: int):
    # timestamp rounded to 10-minute intervals
    # Forces cache refresh every 10 minutes
    return _actual_search(query_hash)
```

---

## ⚠️ Belangrijk: Fout Preventie

### **Scenario 1: Auto niet meer beschikbaar**

```python
# Als scraping 0 results geeft:
if len(rag_results) == 0:
    response = "Helaas heb ik geen exacte match gevonden voor een Golf 8 diesel onder €25.000."
    response += "\n\nMaar ik heb wel deze alternatieven:"
    # Show similar cars (Golf 7, andere diesels, etc.)
```

### **Scenario 2: Verkeerde auto info**

```python
# ALTIJD include link naar originele advertentie
# Dan kan klant zelf verifiëren

response = f"""
Perfect! We hebben een VW Golf 8 2.0 TDI in zwart:
- Prijs: €24.950
- Kilometerstand: 45.000 km
- Bouwjaar: 2021

Bekijk de volledige advertentie: {listing_url}

Kloppen deze gegevens? Dan kan ik een afspraak inplannen!
"""
```

### **Scenario 3: Prijs veranderd**

```python
# Scrape timestamp toevoegen
response = f"""
Prijsinformatie van vandaag, {datetime.now().strftime('%d-%m-%Y %H:%M')}

Let op: Prijzen kunnen wijzigen. Bel ons voor de actuele prijs.
"""
```

---

## 📊 Success Metrics

### **Must Haves:**
- ✅ Vindt juiste auto binnen 5 seconden
- ✅ Geen verkeerde auto info (99% accuraat)
- ✅ Altijd link naar originele advertentie
- ✅ Duidelijk als auto niet beschikbaar

### **Nice to Haves:**
- ⭐ Alternatieve voorstellen als exacte match niet bestaat
- ⭐ Foto's tonen (via Playwright screenshot)
- ⭐ Prijs vergelijking met vergelijkbare auto's
- ⭐ "Net binnen" tag voor nieuwe listings

---

## 🎯 Next Steps

**RECOMMEND:**
1. ✅ Start with Marktplaats scraping (Phase 1)
2. ✅ Use existing Playwright MCP tools
3. ✅ Test with real queries from customers
4. ✅ Add website scraping after Marktplaats works
5. ⚠️ Keep system prompts focused on info-giving, not pushing

**Timeline:**
- Week 5: Marktplaats RAG working
- Week 6: Website scraping added
- Week 7: Advanced features + refinement
