# 🎭 Demo Scenarios voor Potentiële Klanten

**Complete scripts voor het demonstreren van de WhatsApp Recruitment Platform**

---

## 📋 Voorbereiding Checklist

**Voor elke demo:**
- [ ] Docker services draaien: `./start-demo.sh`
- [ ] ngrok tunnel actief: `ngrok http 8000`
- [ ] Chatwoot dashboard open: http://localhost:3001
- [ ] Reflex metrics dashboard open: http://localhost:3002
- [ ] WhatsApp op je telefoon klaar
- [ ] Second screen voor dashboards (optioneel maar impressive)

---

## 🎯 Scenario 1: Job Search & Auto-Extraction

**Doel:** Laat zien hoe AI automatisch vacature voorkeuren extraheert en matcht

**Wat je laat zien:**
- Multi-agent orchestration (Router → Extraction → Conversation → CRM)
- Structured data extraction van ongestructureerde WhatsApp berichten
- Auto-tagging en lead scoring in Chatwoot
- Context-behoud over meerdere berichten

### Script

**Opening (30 seconden):**
> "Laat ik jullie laten zien hoe onze AI-powered recruitment assistent werkt. Ik ga nu een WhatsApp bericht sturen alsof ik een kandidaat ben die op zoek is naar een baan."

**Actie 1: Stuur WhatsApp bericht**
```
Hi! Ik ben op zoek naar een senior software engineer functie in Amsterdam of Rotterdam.
Ik heb 5 jaar ervaring met Python en React. Mijn salaris verwachting is €60k-€80k per jaar.
Ik kan binnen 1 maand starten.
```

**Live Commentary tijdens processing (~5 seconden):**
> "Kijk naar dit dashboard - je ziet nu in real-time dat ons systeem 4 AI agents parallel runt..."

**Actie 2: Show Chatwoot dashboard (scroll door processing)**
Point out:
- "Hier zie je de Router Agent die het bericht classificeert als 'job search'"
- "De Extraction Agent haalt gestructureerde data eruit"
- "Conversation Agent genereert een gepersonaliseerd antwoord"
- "CRM Agent update automatisch het contact profile"

**Actie 3: Show WhatsApp response (na ~8 seconden)**
Expected AI response:
```
Hallo! Bedankt voor je bericht. Ik zie dat je op zoek bent naar een senior software engineer functie.
Op basis van je profiel heb ik enkele interessante posities in Amsterdam en Rotterdam gevonden die
binnen je salaris range vallen.

Heb je een voorkeur voor remote werken of wil je liever volledig op kantoor?
```

**Actie 4: Show Chatwoot contact profile**
Point out auto-extracted data:
- **Custom Attributes:**
  - job_preferences_titles: ["Senior Software Engineer"]
  - job_preferences_locations: ["Amsterdam", "Rotterdam"]
  - salary_min: 60000
  - salary_max: 80000
  - skills: ["Python", "React"]
  - years_experience: 5
  - availability: "1 month"

- **Auto-Tags:**
  - job-seeker ✅
  - active ✅
  - normal (priority) ✅

- **Lead Quality Score:** Warm 🔥

**Closing (15 seconden):**
> "En dat is allemaal gebeurd in minder dan 10 seconden, volledig automatisch. Geen handmatig data entry, geen copy-paste. De recruiter ziet direct alle relevante informatie en kan meteen matches maken."

**Follow-up vraag van klant verwacht:**
*"Maar wat als de kandidaat niet alle info geeft?"*

**Antwoord + demo:**
> "Precies daarom heeft onze Conversation Agent intelligente follow-up vragen. Kijk maar..."

**Stuur follow-up bericht:**
```
Ik heb een voorkeur voor remote werken
```

**Show hoe AI context behoudt:**
- Remembers previous job preferences
- Adds remote preference to profile
- Suggests matching remote positions

---

## 🚨 Scenario 2: Complaint Escalation (High Priority)

**Doel:** Laat zien hoe AI urgente situaties herkent en direct escaleert

**Wat je laat zien:**
- Intent classification voor complaints
- Auto-escalation naar human agent
- Priority tagging
- Skip van extraction (snelheid)

### Script

**Opening (20 seconden):**
> "Natuurlijk wil je niet dat een AI verkeerde beslissingen maakt bij klachten. Daarom hebben we een intelligent escalation systeem. Kijk maar..."

**Actie 1: Stuur complaint**
```
Dit is echt onacceptabel! Ik wacht al 3 weken op feedback over mijn sollicitatie
en niemand reageert op mijn emails!
```

**Actie 2: Show real-time routing (in logs)**
```bash
docker-compose logs -f celery-worker | grep -E "Router|Escalation"
```

Point out in logs:
```
🔀 Router node executing
✅ Router classification complete: intent=complaint, escalate=True
⚡ ESCALATION: Routing to human agent
❌ SKIPPING: Extraction (high priority path)
❌ SKIPPING: Conversation (human required)
✅ CRM update: Priority tag added, conversation assigned
```

**Actie 3: Show Chatwoot dashboard**
Point out:
- Conversation instantly assigned to team member
- **Priority tag:** urgent 🚨
- **Labels:** complaint, escalated
- **Status:** open (awaiting human response)
- **No AI response sent** (waiting for human)

**Actie 4: Show team notification**
- Email/Slack notification sent to team
- SLA timer started (response within 1 hour)

**Closing (15 seconden):**
> "Dus binnen 3 seconden is deze klacht geëscaleerd, toegewezen, en heeft het team een notificatie. De kandidaat krijgt GEEN AI antwoord maar wacht op een mens. Zo voorkom je escalatie van frustratie."

---

## 💬 Scenario 3: Multi-Turn Conversation (Context Awareness)

**Doel:** Laat zien hoe AI context behoudt over meerdere berichten

**Wat je laat zien:**
- Conversation history tracking
- Context-aware responses
- Progressive data gathering
- Natural conversation flow

### Script

**Opening (15 seconden):**
> "Een veel voorkomende vraag: kan de AI context onthouden? Laat me een natuurlijk gesprek demonstreren..."

**Actie 1: Start conversation**
```
Welke soorten banen hebben jullie?
```

**Expected AI response:**
```
We hebben vacatures in verschillende sectoren:
- Software Development (Frontend, Backend, Full-Stack)
- Data Science & Analytics
- DevOps & Cloud Engineering
- Product Management

In welke richting ben je geïnteresseerd?
```

**Actie 2: Follow-up (geen context herhalen)**
```
Software development klinkt interessant. Wat is het salaris?
```

**Expected AI response:**
```
Onze software development posities variëren van €40k voor junior developers
tot €90k+ voor senior/lead posities.

Heb je al ervaring in dit vak, en in welke regio zoek je?
```

**Point out in Chatwoot:**
- **Conversation history** maintained
- AI "remembers" user asked about software development
- No need to repeat context

**Actie 3: Verify context in profile**
```
Ik heb 3 jaar ervaring met Python
```

**Show Chatwoot profile update:**
- skill: Python ✅
- years_experience: 3 ✅
- job_preference: Software Development ✅

**Actie 4: Progressive refinement**
```
En ik zoek iets in Utrecht
```

**Show profile:**
- location: Utrecht ✅

**Closing (10 seconden):**
> "Zie je? In 4 berichten hebben we een compleet kandidaat profiel opgebouwd, zonder dat de kandidaat een formulier hoefde in te vullen. Alles natuurlijk via chat."

---

## 📊 Scenario 4: Metrics & ROI Dashboard

**Doel:** Laat zien hoe platform ROI meet en optimaliseert

**Wat je laat zien:**
- Real-time metrics dashboard
- Token usage tracking
- Cost per conversation
- Response time optimization

### Script

**Opening (15 seconden):**
> "Natuurlijk willen jullie weten: wat kost dit en hoe kunnen we optimaliseren? Daarom hebben we een live metrics dashboard..."

**Actie 1: Open Reflex Dashboard**
```
http://localhost:3002
```

**Show metrics:**
- **Today's Stats:**
  - Messages processed: 45
  - Avg response time: 8.2s
  - Total tokens used: 125,420
  - Total cost: $0.42

- **Per Agent:**
  - Router (GPT-4o-mini): $0.001 per call
  - Extraction (Pydantic AI): $0.0002 per call
  - Conversation (Claude 3.5): $0.008 per call (with caching!)
  - CRM (GPT-4o-mini): $0.0001 per call

**Point out prompt caching:**
> "Let op dit getal: normaal zou elke Claude call €0.08 kosten. Door prompt caching reduceren we dit met 90% naar €0.008. Dat is een besparing van €3,600 per jaar bij 50,000 berichten."

**Actie 2: Show cost breakdown chart**
```
Cost per conversation: €0.01
- 70% Conversation Agent (Claude 3.5)
- 15% Router Agent
- 10% Extraction Agent
- 5% CRM Agent
```

**Actie 3: Show optimization opportunities**
Point out in dashboard:
- **Cache hit rate:** 89% 🎯 (excellent)
- **Avg extraction confidence:** 0.85 ✅
- **Escalation rate:** 5% ✅ (low is good)

**Closing (20 seconden):**
> "Bij 10,000 kandidaten per maand zijn je kosten ongeveer €100-150 voor AI. Traditioneel zou je 2-3 recruiters FTE nodig hebben (€120k+). Dat is een ROI van meer dan 800%."

---

## 🔒 Scenario 5: Security & Compliance (GDPR)

**Doel:** Address privacy concerns van enterprise clients

**Wat je laat zien:**
- HMAC-SHA256 webhook security
- GDPR-compliant data handling
- Explicit consent tracking
- Data retention policies

### Script

**Opening (15 seconden):**
> "Natuurlijk is privacy cruciaal, vooral in recruitment. Laat me jullie laten zien hoe we GDPR-compliant werken..."

**Actie 1: Show webhook security**
```bash
# Show webhook verification code
cat app/security/webhook_auth.py | grep -A 10 "def verify_chatwoot_signature"
```

Point out:
- HMAC-SHA256 signature verification
- Constant-time comparison (anti timing attacks)
- Rate limiting (100 req/min)

**Actie 2: Show extraction agent code**
```python
# Show GDPR-compliant extraction
# Only extract EXPLICITLY stated information
# No inferencing of sensitive data
```

**Actie 3: Demonstrate consent tracking**

Send message:
```
Ik geef toestemming om mijn gegevens op te slaan voor vacature matching
```

Show profile:
- **consent_given:** True ✅
- **consent_timestamp:** 2025-10-10 14:30:22
- **consent_type:** vacancy_matching

**Actie 4: Show data retention (Self-hosted)**
```
Chatwoot (http://localhost:3001) → Settings → Data Retention
- Messages: 90 days (configurable)
- Personal data: Deleted on request
- Audit logs: 1 year
- Self-hosted: Volledige controle over data lokaal
```

**Closing (15 seconden):**
> "Alle kandidaat data is encrypted at rest, we loggen alle toegang, en kandidaten kunnen op elk moment hun data opvragen of laten verwijderen via een automated process."

---

## ⚡ Bonus Scenario: RAG (Future Feature - Week 5-6)

**Doel:** Tease toekomstige features

**Wat je uitlegt (zonder demo):**
> "In de volgende release (over 2-3 weken) voegen we RAG toe - Retrieval Augmented Generation. Hiermee kan de AI ook je eigen vacature database doorzoeken en specifieke job postings matchen op basis van de kandidaat requirements."

**Show architecture diagram:**
```
Candidate: "I'm looking for a Python job in Amsterdam"
    ↓
Router: job_search intent
    ↓
Extraction: skills=[Python], location=[Amsterdam]
    ↓
RAG: Search vector DB voor matching vacancies
    ↓
Conversation: "I found 3 positions matching your profile:
              1. Senior Python Dev @ Company X - €70k
              2. Python Data Engineer @ Company Y - €65k
              3. ..."
```

---

## 📝 Demo Prep Checklist

**1 dag voor demo:**
- [ ] Verify alle API keys valid zijn
- [ ] Test volledige flow met test berichten
- [ ] Check Chatwoot inbox clean is
- [ ] Prepare demo WhatsApp nummer

**1 uur voor demo:**
- [ ] Start Docker: `./start-demo.sh`
- [ ] Wait for Chatwoot: Check http://localhost:3001 bereikbaar is
- [ ] Verify Chatwoot API token in .env configured
- [ ] Start ngrok: `ngrok http 8000`
- [ ] Update 360Dialog webhook URL naar ngrok URL
- [ ] Open Chatwoot dashboard: http://localhost:3001
- [ ] Open metrics dashboard: http://localhost:3002
- [ ] Test met 1 bericht dat alles werkt

**Tijdens demo:**
- [ ] Record screen (optioneel)
- [ ] Have backup plan als internet fail
- [ ] Note welke scenarios klant interessant vind
- [ ] Track vragen voor follow-up

**Na demo:**
- [ ] Export metrics report
- [ ] Screenshot van auto-extracted profiles
- [ ] Send follow-up email met:
  - Demo recording link
  - Metrics summary
  - ROI calculation
  - Next steps

---

## 🎤 Demo Tips

**Do's:**
- Explain wat er gebeurt tijdens AI processing (5-8 seconden)
- Show both WhatsApp EN Chatwoot side-by-side
- Point out time savings ("Dit zou normaal 5 minuten manual work zijn")
- Use real-world examples relevant voor klant's industry
- Let klant self-test door zelf berichten te sturen

**Don'ts:**
- Ga niet te technisch (tenzij CTO in de room)
- Laat geen errors zien (have fallback plan)
- Claim geen 100% accuracy (wees eerlijk over edge cases)
- Rush niet door scenarios - laat AI response uittypen

**Common Questions & Answers:**

**Q: "Wat als AI verkeerd antwoord geeft?"**
A: "Elke AI response heeft een confidence score. Bij <60% confidence escaleert systeem automatic naar human. Plus, we loggen alles voor continuous improvement."

**Q: "Kunnen we de AI customizen voor onze industry?"**
A: "Absoluut. Het systeem prompt kan volledig aangepast worden naar jullie tone-of-voice, vacature types, en specifieke requirements. Dat doen we tijdens onboarding."

**Q: "Wat als we 10,000 berichten per dag krijgen?"**
A: "Systeem schaalt horizontal. Op Railway deployen we per client een dedicated instance die auto-scales van 1-4 containers. We hebben geteste load tests tot 500 concurrent berichten."

**Q: "Hoe snel kunnen we live?"**
A: "Onboarding duurt 2-3 weken:
   - Week 1: Chatwoot + WhatsApp setup, data import
   - Week 2: AI customization, testing
   - Week 3: Training, pilot met klein team
   - Week 4: Full rollout"

---

**Succes met je demo! 🎉**

*Pro tip: Record je eerste demo, watch it back, en improve voor volgende keer. Je zult zien dat je steeds beter wordt in highlighting de juiste features.*
