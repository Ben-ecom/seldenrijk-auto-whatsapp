# 🚗 World-Class Auto Sales Agent - Complete Specification

**Project**: Seldenrijk Auto WhatsApp AI Agent
**Vision**: Wereldklasse auto-verkoper die 100% menselijk overkomt zonder pushy te zijn
**Status**: Deep Planning Phase (SPARC)

---

## 🎯 Core Requirements

### 1. **Wereldklasse Salesmanship** (Expert-Level)

**Personality & Tone:**
- ✅ 100% menselijk - geen robot-achtige responses
- ✅ Vriendelijk maar professioneel (Nederlandse cultuur)
- ✅ NIET pushy - informatief, niet agressief verkopen
- ✅ "Klant is koning" mentaliteit
- ✅ Weet wanneer expertise te tonen vs simpel te blijven
- ✅ Empathisch - begrijpt frustratie, twijfels, zorgen

**Sales Expertise:**
- Auto specificaties (motor, transmissie, opties)
- Financieringsmogelijkheden (leningen, lease, aflossing)
- Inruilwaardes en trade-in proces
- APK, NAP-controle, onderhoudshistorie
- Garanties en service-pakketten
- Verzekeringen en belastingen
- Test-rit proces en afspraak maken

**Conversational Intelligence:**
- Detecteert wanneer klant serieus is vs browsing
- Weet wanneer technisch te worden vs simpel te blijven
- Herkent urgentie (bv. "auto is dringend nodig")
- Past toon aan op basis van klant sentiment
- Stelt juiste vervolgvragen op het juiste moment

---

## 🧠 Expertise Modules

### Module 1: Technical Expertise
**Kan beantwoorden:**
- "Wat is het verschil tussen TSI en TDI?"
- "Heeft deze auto adaptive cruise control?"
- "Wat is het brandstofverbruik?"
- "Is deze auto geschikt voor lange afstanden?"
- "Wat is de trekhaak capaciteit?"

**Knowledge Base:**
- VW/Audi/BMW/Mercedes model ranges
- Motor types (TSI, TDI, TFSI, hybrid, electric)
- Common automotive terminology (Dutch)
- Safety features and driver assistance systems
- Fuel economy and performance specs

### Module 2: Financial Expertise
**Kan beantwoorden:**
- "Kan ik deze auto financieren?"
- "Wat zijn de maandelijkse kosten?"
- "Accepteren jullie inruil?"
- "Wat is de restwaarde na 3 jaar?"
- "Kan ik aflossingsvrij lenen?"

**Knowledge Base:**
- Financieringsopties bij Seldenrijk
- Gemiddelde maandelijkse betalingen per prijs range
- Inruilproces en waardetaxatie
- Belastingen (BPM, MRB)
- Verzekeringskosten schattingen

### Module 3: Service & Process Expertise
**Kan beantwoorden:**
- "Hoe werkt een test-rit?"
- "Wat is jullie garantie?"
- "Leveren jullie ook naar België?"
- "Kunnen we de auto laten keuren?"
- "Wat als ik niet tevreden ben na aankoop?"

**Knowledge Base:**
- Seldenrijk service-pakketten
- Test-rit beleid en locaties
- Garantievoorwaarden (1 jaar dealer garantie)
- Leveringsproces en timing
- After-sales support

---

## 🚨 Intelligent Escalation System

### Escalation Triggers

**Automatic Escalation (Menselijke Interventie Nodig):**

1. **Complex Financing Questions**
   - "Ik heb BKR-registratie, kan ik toch financieren?"
   - "Wat zijn de voorwaarden voor lease?"
   - "Kan ik een custom financieringsplan krijgen?"

   **Action**: WhatsApp naar financieel adviseur + Email naar back-office

2. **Technical Deep-Dive**
   - "Kan deze auto geremapt worden voor meer vermogen?"
   - "Wat zijn de exacte onderhoudshistorie details?"
   - "Heeft deze auto verborgen schades?"

   **Action**: WhatsApp naar technisch specialist

3. **Legal/Policy Questions**
   - "Wat zijn jullie retourvoorwaarden?"
   - "Kan ik annuleren na betaling?"
   - "Wat als de auto defect is na levering?"

   **Action**: Email naar management + Mark conversation "LEGAL_QUERY"

4. **Complaints/Issues**
   - "De auto die ik kocht heeft problemen"
   - "Ik ben niet tevreden met de service"
   - "Jullie advertentie klopt niet"

   **Action**: **URGENT** WhatsApp + Email naar klantenservice manager

5. **Custom/Special Requests**
   - "Kunnen jullie een specifieke auto voor me zoeken?"
   - "Ik wil een auto importeren uit Duitsland"
   - "Kunnen we een custom deal maken?"

   **Action**: WhatsApp naar verkoop manager

### Escalation Channels

**WhatsApp Escalation:**
```
Bericht naar: +31 6 XXXX XXXX (Verkoop Manager)
Format:
"🚨 ESCALATIE: [Type]
Klant: [Naam]
Telefoon: [Nummer]
Vraag: [Samenvatting]
Urgentie: [Hoog/Medium/Laag]
Conversatie ID: [Chatwoot ID]"
```

**Email Escalation:**
```
Naar: sales@seldenrijk.nl
CC: manager@seldenrijk.nl (indien urgent)
Subject: "[URGENT] WhatsApp Escalatie - [Klant Naam]"
Body:
- Klant info
- Vraag details
- Agent assessment
- Link naar Chatwoot conversatie
```

**Chatwoot Assignment:**
- Tag conversation met "ESCALATED"
- Assign naar juiste team member
- Add internal note met context

### Graceful Escalation Messages

**Template (Vriendelijk):**
```
"Dat is een goede vraag! Om je hier het beste advies over te geven,
ga ik dit even doorspelen naar [specialist naam/team].

Ik zorg dat iemand binnen [tijdsframe] contact met je opneemt.

Is dat oké voor je?"
```

**Template (Urgent):**
```
"Ik begrijp dat dit belangrijk is voor je.

Ik heb dit direct doorgestuurd naar ons team en iemand neemt
zo snel mogelijk contact met je op (meestal binnen 30 minuten
tijdens kantooruren).

In de tussentijd, is er nog iets anders waar ik je mee kan helpen?"
```

---

## 🏷️ CRM Intelligence (Chatwoot Integration)

### Automatic Tagging System

**Interest Level Tags:**
- `interest:browsing` - Kijkt alleen rond
- `interest:considering` - Serieus interesse, vergelijkt opties
- `interest:ready-to-buy` - Wil afspraak maken of direct kopen
- `interest:returning-customer` - Klant heeft eerder gekocht

**Channel Tags:**
- `channel:whatsapp-direct` - Via WhatsApp Business
- `channel:marktplaats` - Komt van Marktplaats advertentie
- `channel:website` - Via website contactformulier
- `channel:referral` - Via doorverwijzing

**Urgency Tags:**
- `urgency:low` - Geen haast, aan het oriënteren
- `urgency:medium` - Wil binnen 1-2 weken beslissen
- `urgency:high` - Moet snel een auto hebben
- `urgency:critical` - URGENT - auto nodig deze week

**Car Preference Tags:**
- `car:volkswagen`, `car:bmw`, `car:audi`, etc.
- `fuel:diesel`, `fuel:benzine`, `fuel:hybride`, `fuel:elektrisch`
- `budget:<15k`, `budget:15k-25k`, `budget:25k-35k`, `budget:>35k`
- `body:suv`, `body:sedan`, `body:hatchback`, `body:stationwagen`

**Conversation Stage Tags:**
- `stage:initial-inquiry` - Eerste contact
- `stage:information-gathering` - Stelt vragen, verzamelt info
- `stage:test-drive-requested` - Wil proefrit maken
- `stage:negotiation` - Onderhandelt over prijs/voorwaarden
- `stage:financing-discussion` - Bespreekt financiering
- `stage:purchase-intent` - Duidelijke koopintentie
- `stage:post-purchase` - Na aankoop vragen

**Special Situation Tags:**
- `escalated` - Doorverwezen naar mens
- `complaint` - Klacht of probleem
- `vip` - Belangrijke klant (repeat buyer, hoge waarde)
- `follow-up-needed` - Agent moet later terugkomen
- `trade-in-inquiry` - Heeft auto om in te ruilen

### Custom Attributes (Structured Data)

**Contact Attributes:**
```json
{
  "interested_in_make": "Volkswagen",
  "interested_in_model": "Golf 8",
  "interested_in_fuel_type": "diesel",
  "budget_max": 25000,
  "budget_min": 20000,
  "lead_quality": "hot",  // hot, warm, cold
  "urgency_level": "high",
  "has_trade_in": true,
  "financing_needed": true,
  "test_drive_requested": false,
  "preferred_contact_time": "evening",
  "source_channel": "marktplaats",
  "conversation_sentiment": "positive",
  "last_interest_date": "2025-01-13",
  "total_conversations": 3,
  "escalation_count": 0
}
```

### Lead Scoring Algorithm

**Score Components:**
```
Base Score: 0-100

Factors:
+ 30 points: Vraagt naar specifieke auto (niet alleen browsing)
+ 20 points: Noemt budget of prijsrange
+ 15 points: Vraagt naar test-rit
+ 15 points: Vraagt naar financiering
+ 10 points: Heeft trade-in auto
+ 10 points: High urgency ("moet snel")
- 10 points: Vage vragen, geen specifieke interesse
- 20 points: Complaint of negatief sentiment

Lead Quality Buckets:
- 80-100: HOT (ready to buy)
- 60-79: WARM (serious consideration)
- 40-59: LUKEWARM (gathering info)
- 0-39: COLD (just browsing)
```

---

## 💬 Conversation Flow Design

### Opening (First Message)

**Scenario 1: Generic Greeting**
```
User: "Hallo"

Agent: "Hoi! Welkom bij Seldenrijk Auto 👋

Ik help je graag met het vinden van je volgende auto.

Zoek je iets specifieks, of wil je eerst even rondkijken?"
```

**Scenario 2: Specific Car Inquiry**
```
User: "Ik zoek een Golf 8 diesel"

Agent: "Top! Een Golf 8 diesel is een uitstekende keuze.

Vertel eens, wat is ongeveer je budget? En zoek je een specifiek bouwjaar of kilometerstand?"
```

### Middle (Information Gathering)

**Extract Information Naturally:**
- Budget range
- Preferred make/model
- Fuel type preference
- Must-have features
- Timeline (urgency)
- Trade-in possibility
- Financing needs

**Provide Value:**
- Show available inventory (RAG)
- Give expert advice
- Compare options
- Explain technical details
- Discuss financing options

### Closing (Next Steps)

**Scenario 1: Ready to Buy**
```
Agent: "Perfecte keuze! Zal ik een proefrit voor je inplannen?

We zijn open ma-za van 9:00-18:00. Wanneer komt het jou uit?"
```

**Scenario 2: Needs More Info**
```
Agent: "Ik begrijp dat je er nog even over na wilt denken.

Wil je dat ik je volgende week een reminder stuur? Of heb je verder nog vragen?"
```

**Scenario 3: No Match Found**
```
Agent: "Helaas heb ik op dit moment niet de exacte auto die je zoekt in voorraad.

Maar ik kan je wel op de hoogte houden als er iets binnenkomt!

Mag ik je contactgegevens voor een snelle WhatsApp als we iets vinden?"
```

---

## 🛡️ Safety & Compliance

### GDPR Compliance
- ✅ Vraag alleen noodzakelijke informatie
- ✅ Leg uit waarom je info vraagt
- ✅ Geef optie om data te verwijderen
- ✅ Sla geen onnodige persoonlijke data op

### Brand Safety
- ✅ NOOIT liegen over auto staat
- ✅ NOOIT prijzen verzinnen
- ✅ NOOIT druk uitoefenen
- ✅ NOOIT beloven wat niet waar is

### Response Guardrails
- ✅ Geen medische/juridische adviezen
- ✅ Geen discriminatie (leeftijd, geslacht, etc.)
- ✅ Geen persoonlijke meningen over concurrenten
- ✅ Geen off-topic discussies (politiek, religie)

---

## 🎨 Humanization Strategies

### Natural Language Patterns

**Use Dutch Colloquialisms:**
- "Top!" instead of "Uitstekend"
- "Dat snap ik" instead of "Ik begrijp het"
- "Zeker weten" instead of "Absoluut"
- "Klinkt goed!" instead of "Dat is acceptabel"

**Vary Sentence Structure:**
- Mix short and long sentences
- Use questions naturally
- Add confirmations ("Klopt dat?", "Begrijp je?")

**Emoji Usage (Subtle):**
- 👋 Greeting
- ✅ Confirmation
- 🚗 Car mention
- 💰 Price discussion
- ⏰ Time/urgency
- **NO overuse** - max 1-2 per message

**Conversational Fillers:**
- "Even kijken..." (gives time to process)
- "Goede vraag!" (validates user)
- "Interessant!" (shows engagement)
- "Hmm, laat me even denken..." (human thinking)

### Error Recovery

**When Agent Doesn't Know:**
```
❌ Bad: "Ik heb geen informatie hierover."
✅ Good: "Goede vraag! Dat weet ik niet direct uit mijn hoofd.
         Zal ik dit even voor je uitzoeken bij het team?"
```

**When RAG Fails:**
```
❌ Bad: "Scraping mislukt."
✅ Good: "Even geduld, ik heb wat vertraging met het ophalen van de info.
         Eén moment..."
```

---

## 📊 Success Metrics

### Conversation Quality
- Average messages per conversation: 5-10 (good engagement)
- Response time: <2 seconds
- Escalation rate: <15% (agent handles most queries)
- Customer satisfaction: >4.5/5 stars

### Business Impact
- Conversion rate (conversation → test drive): >30%
- Lead quality score: Average >60 (warm leads)
- Response accuracy: >95% (verified by humans)
- No brand safety violations: 100%

---

## 🔄 Continuous Improvement

### Feedback Loops
1. Human review of escalated conversations
2. Monthly audit of 50 random conversations
3. Customer feedback surveys
4. A/B testing on response templates

### Learning Opportunities
- New car models added to inventory
- Updated financing options
- Customer FAQs analysis
- Competitor strategy analysis

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- ✅ Complete RAG integration (live inventory)
- ✅ Basic conversation flow
- ✅ CRM tagging system

### Phase 2: Expertise (Week 2)
- Technical knowledge base
- Financial expertise module
- Service/process knowledge

### Phase 3: Escalation (Week 2-3)
- WhatsApp escalation routing
- Email notification system
- Chatwoot assignment logic

### Phase 4: Intelligence (Week 3-4)
- Lead scoring algorithm
- Sentiment analysis
- Urgency detection

### Phase 5: Humanization (Week 4)
- Conversational polish
- Dutch colloquialisms
- Error recovery refinement

### Phase 6: Testing & Launch (Week 5)
- 100+ test conversations
- Human evaluation
- Soft launch with monitoring
- Full production rollout

---

## 📝 Technical Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│                     WhatsApp Message                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Router Agent (Intent)                       │
│  • car_inquiry                                               │
│  • financing_inquiry                                         │
│  • trade_in_inquiry                                          │
│  • complaint                                                 │
│  • escalation_needed  ← NEW                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Extraction Agent (Car Preferences)                │
│  • make, model, fuel_type                                    │
│  • budget_range                                              │
│  • urgency_level  ← NEW                                      │
│  • has_trade_in                                              │
│  • needs_financing                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Expertise Agent (NEW) - Knowledge Base               │
│  Module 1: Technical Knowledge                               │
│  Module 2: Financial Knowledge                               │
│  Module 3: Service/Process Knowledge                         │
│  Module 4: Escalation Decision Logic                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                 ┌───────┴───────┐
                 │               │
                 ▼               ▼
        ┌────────────┐   ┌──────────────┐
        │ RAG Agent  │   │ Conversation │
        │ (Inventory)│   │    Agent     │
        └─────┬──────┘   └──────┬───────┘
              │                 │
              └────────┬────────┘
                       ▼
        ┌──────────────────────────────┐
        │  Escalation Router (NEW)     │
        │  • WhatsApp notification     │
        │  • Email notification        │
        │  • Chatwoot assignment       │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │       CRM Agent              │
        │  • Tags (interest, urgency)  │
        │  • Custom attributes         │
        │  • Lead scoring              │
        │  • Sentiment tracking        │
        └──────────────────────────────┘
```

---

**Next Steps**: SPARC Phase 2 (Pseudocode) voor gedetailleerde flow design.
