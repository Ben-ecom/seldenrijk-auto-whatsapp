# 🔷 SPARC Phase 2: Pseudocode Design
# World-Class Auto Sales Agent - All Agents

**Project**: Seldenrijk Auto WhatsApp AI Agent
**Phase**: Pseudocode (Logic Design)
**Date**: 2025-01-13

---

## 🎯 Overall System Flow

```
MAIN WORKFLOW:
1. WhatsApp Message Received
2. RouterAgent → Classify intent + detect escalation need
3. ExtractionAgent → Extract car preferences + urgency + trade-in info
4. ExpertiseAgent → Determine knowledge module needed + escalation check
5. IF needs_escalation:
   → EscalationRouter → Send WhatsApp/Email to humans
   → ConversationAgent → Generate graceful handoff message
   ELSE:
   → RAGAgent → Search inventory (if car_inquiry)
   → ConversationAgent → Generate expert response
6. CRMAgent → Tag conversation + score lead + update attributes
7. Send response to customer
```

---

## 📋 Agent 1: ExpertiseAgent (NEW)

**Purpose**: Determine which knowledge module to use and whether escalation is needed

### Pseudocode:

```python
class ExpertiseAgent(BaseAgent):
    """
    Expertise Agent - Knowledge base with 3 modules + escalation logic

    Modules:
    1. Technical Knowledge (car specs, features)
    2. Financial Knowledge (financing, trade-in, pricing)
    3. Service/Process Knowledge (test drives, delivery, guarantees)
    """

    def __init__(self):
        self.model = "claude-3-haiku"  # Fast model for classification
        self.knowledge_base = {
            "technical": TechnicalKnowledgeModule(),
            "financial": FinancialKnowledgeModule(),
            "service": ServiceKnowledgeModule()
        }

    def _execute(state: ConversationState) -> Dict:
        """
        Main execution logic:
        1. Analyze user message
        2. Determine which knowledge module(s) needed
        3. Check if escalation required
        4. Return knowledge + escalation decision
        """

        # Step 1: Classify query type
        classification = self._classify_query(state["content"])
        # Returns: {
        #   "primary_domain": "technical" | "financial" | "service",
        #   "requires_expert": True/False,
        #   "complexity_level": "simple" | "moderate" | "complex",
        #   "confidence": 0.0-1.0
        # }

        # Step 2: Check escalation triggers
        escalation_needed = self._check_escalation_triggers(
            state["content"],
            classification,
            state.get("conversation_history", [])
        )
        # Returns: {
        #   "escalate": True/False,
        #   "escalation_type": "technical_expert" | "finance_advisor" | "manager" | None,
        #   "urgency": "low" | "medium" | "high" | "critical",
        #   "reason": "complex_financing" | "complaint" | "custom_request" | None
        # }

        # Step 3: IF simple query, get knowledge from module
        IF NOT escalation_needed["escalate"]:
            knowledge = self._get_knowledge(
                domain=classification["primary_domain"],
                query=state["content"]
            )
            # Returns relevant knowledge snippets to help Conversation Agent
        ELSE:
            knowledge = None  # Will escalate instead

        # Step 4: Return decision
        RETURN {
            "classification": classification,
            "escalation_decision": escalation_needed,
            "knowledge": knowledge,
            "confidence": classification["confidence"]
        }

    def _classify_query(self, message: str) -> Dict:
        """
        Classify user query into knowledge domains

        Examples:
        - "Wat is het brandstofverbruik?" → technical
        - "Kan ik deze auto financieren?" → financial
        - "Hoe werkt een test-rit?" → service
        """

        # Use LLM to classify
        prompt = f"""
        Classify this automotive customer query:

        Message: "{message}"

        Determine:
        1. Primary domain: technical, financial, or service
        2. Complexity: simple (FAQ), moderate (requires expertise), complex (needs human)
        3. Confidence: 0.0-1.0

        Examples:
        - "Wat kost deze auto?" → financial, simple, 0.95
        - "Kan ik aflossingsvrij lenen met BKR?" → financial, complex, 0.90
        - "Heeft deze auto cruise control?" → technical, simple, 0.98
        """

        response = self.llm_call(prompt)
        RETURN parsed_classification

    def _check_escalation_triggers(
        self,
        message: str,
        classification: Dict,
        conversation_history: List
    ) -> Dict:
        """
        Check if message requires human escalation

        Escalation Triggers:
        1. Complex financing (BKR, custom plans, lease)
        2. Technical deep-dive (remapping, hidden damage)
        3. Legal questions (return policy, warranty claims)
        4. Complaints (negative sentiment)
        5. Custom requests (import car, specific search)
        """

        # Trigger 1: Complex Financing
        financing_keywords = [
            "bkr", "aflossingsvrij", "lease", "custom plan",
            "rente", "annuïteit", "restschuld", "negatieve BKR"
        ]
        IF any(keyword in message.lower() for keyword in financing_keywords):
            IF classification["complexity_level"] == "complex":
                RETURN {
                    "escalate": True,
                    "escalation_type": "finance_advisor",
                    "urgency": "medium",
                    "reason": "complex_financing"
                }

        # Trigger 2: Technical Expert Needed
        expert_keywords = [
            "remap", "chip tune", "verborgen schade", "complete onderhoudshistorie",
            "exacte specificaties", "technische details van motor"
        ]
        IF any(keyword in message.lower() for keyword in expert_keywords):
            RETURN {
                "escalate": True,
                "escalation_type": "technical_expert",
                "urgency": "low",
                "reason": "technical_deep_dive"
            }

        # Trigger 3: Legal/Policy Questions
        legal_keywords = [
            "retour", "annuleren", "terugbetaling", "garantieclaim",
            "juridisch", "aansprakelijk", "wet"
        ]
        IF any(keyword in message.lower() for keyword in legal_keywords):
            RETURN {
                "escalate": True,
                "escalation_type": "manager",
                "urgency": "high",
                "reason": "legal_question"
            }

        # Trigger 4: Complaint Detection
        complaint_indicators = [
            "teleurgesteld", "niet tevreden", "slechte service",
            "klacht", "probleem met", "advertentie klopt niet"
        ]
        IF any(indicator in message.lower() for indicator in complaint_indicators):
            RETURN {
                "escalate": True,
                "escalation_type": "manager",
                "urgency": "critical",
                "reason": "complaint"
            }

        # Trigger 5: Custom Requests
        custom_keywords = [
            "kunnen jullie zoeken", "importeren", "custom deal",
            "speciale wens", "op maat"
        ]
        IF any(keyword in message.lower() for keyword in custom_keywords):
            RETURN {
                "escalate": True,
                "escalation_type": "sales_manager",
                "urgency": "medium",
                "reason": "custom_request"
            }

        # Trigger 6: Repeated Confusion (conversation context)
        IF len(conversation_history) > 5:
            # Check if customer is asking same question repeatedly
            recent_messages = conversation_history[-5:]
            IF self._detect_repeated_confusion(recent_messages):
                RETURN {
                    "escalate": True,
                    "escalation_type": "manager",
                    "urgency": "medium",
                    "reason": "repeated_confusion"
                }

        # No escalation needed
        RETURN {
            "escalate": False,
            "escalation_type": None,
            "urgency": "low",
            "reason": None
        }

    def _get_knowledge(self, domain: str, query: str) -> Dict:
        """
        Retrieve relevant knowledge from domain module
        """

        IF domain == "technical":
            RETURN self.knowledge_base["technical"].query(query)
        ELIF domain == "financial":
            RETURN self.knowledge_base["financial"].query(query)
        ELIF domain == "service":
            RETURN self.knowledge_base["service"].query(query)
        ELSE:
            RETURN {"snippets": [], "confidence": 0.0}


# ============ KNOWLEDGE MODULES ============

class TechnicalKnowledgeModule:
    """
    Technical automotive knowledge
    """

    def __init__(self):
        self.knowledge_base = {
            "motor_types": {
                "TSI": "Turbocharged Stratified Injection - benzinemotor met turbo en directe inspuiting",
                "TDI": "Turbocharged Direct Injection - dieselmotor met turbo en directe inspuiting",
                "TFSI": "Turbo Fuel Stratified Injection - Audi's versie van TSI",
                "TDI BiTurbo": "Diesel met twee turbo's voor meer vermogen",
                "PHEV": "Plug-in Hybrid Electric Vehicle - hybride met oplaadbare batterij",
                "EV": "Electric Vehicle - volledig elektrisch"
            },
            "fuel_consumption": {
                "diesel": "Gemiddeld 5-7 liter per 100km, afhankelijk van model en rijstijl",
                "benzine": "Gemiddeld 6-9 liter per 100km, afhankelijk van model en rijstijl",
                "hybride": "Gemiddeld 4-6 liter per 100km, afhankelijk van elektrisch rijden",
                "elektrisch": "Gemiddeld 15-20 kWh per 100km, afhankelijk van model"
            },
            "safety_features": {
                "adaptive_cruise_control": "Automatisch afstand houden tot voorganger",
                "lane_assist": "Waarschuwing en correctie bij ongewild van baan gaan",
                "blind_spot": "Waarschuwing voor voertuigen in dode hoek",
                "emergency_brake": "Automatisch remmen bij dreigend ongeval"
            }
        }

    def query(self, question: str) -> Dict:
        """
        Query technical knowledge base
        """
        question_lower = question.lower()

        # Match keywords to knowledge
        relevant_snippets = []

        IF "tsi" in question_lower OR "tdi" in question_lower:
            relevant_snippets.append(self.knowledge_base["motor_types"])

        IF "verbruik" in question_lower OR "brandstof" in question_lower:
            relevant_snippets.append(self.knowledge_base["fuel_consumption"])

        IF "cruise control" in question_lower OR "safety" in question_lower:
            relevant_snippets.append(self.knowledge_base["safety_features"])

        RETURN {
            "snippets": relevant_snippets,
            "domain": "technical",
            "confidence": 0.85 IF relevant_snippets ELSE 0.0
        }


class FinancialKnowledgeModule:
    """
    Financial knowledge (financing, trade-in, pricing)
    """

    def __init__(self):
        self.knowledge_base = {
            "financing_options": [
                "Autolening met vaste rente (4.5% - 7.5%)",
                "Lease (private lease of financial lease)",
                "Betalen in termijnen (tot 60 maanden)",
                "Ballonfinanciering (lage maandlasten, restbedrag aan einde)"
            ],
            "trade_in_process": {
                "step1": "Gratis waardetaxatie van je huidige auto",
                "step2": "Inruilwaarde wordt afgetrokken van aankoopprijs",
                "step3": "Eventuele restschuld kan meegenomen worden in financiering",
                "time": "Taxatie duurt ongeveer 15-30 minuten"
            },
            "monthly_payment_estimates": {
                "15000_euro": "€250 - €300 per maand (60 maanden)",
                "25000_euro": "€400 - €500 per maand (60 maanden)",
                "35000_euro": "€550 - €700 per maand (60 maanden)"
            },
            "taxes": {
                "mrb": "Motorrijtuigenbelasting - afhankelijk van gewicht en brandstof",
                "bpm": "Belasting Personenauto's en Motorrijwielen - al betaald bij aankoop"
            }
        }

    def query(self, question: str) -> Dict:
        """
        Query financial knowledge base
        """
        question_lower = question.lower()

        relevant_snippets = []

        IF "financier" in question_lower OR "lening" in question_lower:
            relevant_snippets.append(self.knowledge_base["financing_options"])

        IF "inruil" in question_lower OR "trade" in question_lower:
            relevant_snippets.append(self.knowledge_base["trade_in_process"])

        IF "maandlasten" in question_lower OR "per maand" in question_lower:
            relevant_snippets.append(self.knowledge_base["monthly_payment_estimates"])

        RETURN {
            "snippets": relevant_snippets,
            "domain": "financial",
            "confidence": 0.90 IF relevant_snippets ELSE 0.0
        }


class ServiceKnowledgeModule:
    """
    Service & process knowledge
    """

    def __init__(self):
        self.knowledge_base = {
            "test_drive": {
                "duration": "30-45 minuten",
                "requirements": "Geldig rijbewijs meenemen",
                "booking": "Vandaag nog mogelijk, reserveer van tevoren",
                "location": "Seldenrijk Harderwijk, Parallelweg 30"
            },
            "warranty": {
                "dealer_warranty": "1 jaar dealer garantie standaard",
                "extended": "Uitgebreide garantie tot 3 jaar mogelijk",
                "coverage": "Alle mechanische en elektrische onderdelen"
            },
            "delivery": {
                "preparation_time": "3-5 werkdagen na aankoop",
                "includes": "APK, onderhoudsbeurt, schoonmaak, tankje vol",
                "home_delivery": "Mogelijk tegen meerprijs (€100-€200)"
            }
        }

    def query(self, question: str) -> Dict:
        """
        Query service knowledge base
        """
        question_lower = question.lower()

        relevant_snippets = []

        IF "proefrit" in question_lower OR "test" in question_lower:
            relevant_snippets.append(self.knowledge_base["test_drive"])

        IF "garantie" in question_lower OR "warranty" in question_lower:
            relevant_snippets.append(self.knowledge_base["warranty"])

        IF "levering" in question_lower OR "bezorgen" in question_lower:
            relevant_snippets.append(self.knowledge_base["delivery"])

        RETURN {
            "snippets": relevant_snippets,
            "domain": "service",
            "confidence": 0.88 IF relevant_snippets ELSE 0.0
        }
```

---

## 🚨 Agent 2: EscalationRouter (NEW)

**Purpose**: Route escalations to correct human via WhatsApp/Email

### Pseudocode:

```python
class EscalationRouter:
    """
    Escalation Router - Send notifications to humans

    Channels:
    1. WhatsApp (urgent, direct)
    2. Email (documentation, non-urgent)
    3. Chatwoot (assignment + internal notes)
    """

    def __init__(self):
        self.whatsapp_contacts = {
            "finance_advisor": "+31612345678",
            "technical_expert": "+31687654321",
            "sales_manager": "+31698765432",
            "manager": "+31611111111"
        }

        self.email_contacts = {
            "finance_advisor": "finance@seldenrijk.nl",
            "technical_expert": "techniek@seldenrijk.nl",
            "sales_manager": "sales@seldenrijk.nl",
            "manager": "manager@seldenrijk.nl"
        }

    def execute(
        self,
        escalation_type: str,
        urgency: str,
        customer_info: Dict,
        conversation_context: str,
        chatwoot_conversation_id: str
    ) -> Dict:
        """
        Main escalation routing logic

        Args:
            escalation_type: "finance_advisor", "technical_expert", "sales_manager", "manager"
            urgency: "low", "medium", "high", "critical"
            customer_info: {name, phone, budget, car_interest}
            conversation_context: Summary of conversation
            chatwoot_conversation_id: ID for linking

        Returns:
            {
                "whatsapp_sent": True/False,
                "email_sent": True/False,
                "chatwoot_assigned": True/False,
                "notification_id": "escalation_xxx"
            }
        """

        # Step 1: Determine channels based on urgency
        channels = self._determine_channels(urgency)
        # Returns: ["whatsapp", "email"] OR ["email"] OR ["whatsapp"]

        # Step 2: Prepare notification content
        notification = self._prepare_notification(
            escalation_type=escalation_type,
            urgency=urgency,
            customer_info=customer_info,
            conversation_context=conversation_context,
            chatwoot_url=f"https://chatwoot.yourdomain.com/app/accounts/1/conversations/{chatwoot_conversation_id}"
        )

        # Step 3: Send via channels
        results = {}

        IF "whatsapp" in channels:
            results["whatsapp_sent"] = self._send_whatsapp(
                recipient=self.whatsapp_contacts[escalation_type],
                message=notification["whatsapp_message"]
            )

        IF "email" in channels:
            results["email_sent"] = self._send_email(
                recipient=self.email_contacts[escalation_type],
                subject=notification["email_subject"],
                body=notification["email_body"],
                cc=notification["cc_emails"]
            )

        # Step 4: Assign in Chatwoot
        results["chatwoot_assigned"] = self._assign_chatwoot(
            conversation_id=chatwoot_conversation_id,
            assignee_type=escalation_type,
            internal_note=notification["internal_note"]
        )

        # Step 5: Log escalation
        escalation_id = self._log_escalation(
            escalation_type=escalation_type,
            urgency=urgency,
            customer_phone=customer_info["phone"],
            timestamp=datetime.now()
        )

        results["notification_id"] = escalation_id

        RETURN results

    def _determine_channels(self, urgency: str) -> List[str]:
        """
        Decide which channels to use based on urgency
        """

        IF urgency == "critical":
            RETURN ["whatsapp", "email"]  # Both channels
        ELIF urgency == "high":
            RETURN ["whatsapp", "email"]  # Both channels
        ELIF urgency == "medium":
            RETURN ["whatsapp"]  # Quick notification
        ELSE:  # low urgency
            RETURN ["email"]  # Documentation only

    def _prepare_notification(
        self,
        escalation_type: str,
        urgency: str,
        customer_info: Dict,
        conversation_context: str,
        chatwoot_url: str
    ) -> Dict:
        """
        Prepare notification messages for each channel
        """

        # WhatsApp message (short, urgent)
        whatsapp_message = f"""
🚨 ESCALATIE: {escalation_type.upper()}
Urgentie: {urgency.upper()}

Klant: {customer_info.get('name', 'Onbekend')}
Telefoon: {customer_info['phone']}
Interesse: {customer_info.get('car_interest', 'Onbekend')}

Context: {conversation_context[:200]}...

📱 Chatwoot: {chatwoot_url}

Actie vereist binnen {self._get_response_sla(urgency)}
        """.strip()

        # Email message (detailed, formal)
        email_subject = f"[{urgency.upper()}] Escalatie: {escalation_type} - {customer_info.get('name', 'Klant')}"

        email_body = f"""
Beste team,

Er is een escalatie van het WhatsApp AI Agent systeem:

=== KLANT INFORMATIE ===
Naam: {customer_info.get('name', 'Onbekend')}
Telefoon: {customer_info['phone']}
Budget: €{customer_info.get('budget', 'Onbekend')}
Interesse: {customer_info.get('car_interest', 'Algemeen')}

=== ESCALATIE DETAILS ===
Type: {escalation_type}
Urgentie: {urgency}
Reden: {customer_info.get('escalation_reason', 'Zie conversatie')}

=== CONVERSATIE CONTEXT ===
{conversation_context}

=== ACTIE VEREIST ===
Response tijd: {self._get_response_sla(urgency)}
Chatwoot conversatie: {chatwoot_url}

Groet,
WhatsApp AI Agent Systeem
        """.strip()

        # CC emails for high urgency
        cc_emails = []
        IF urgency in ["critical", "high"]:
            cc_emails.append("manager@seldenrijk.nl")

        # Internal note for Chatwoot
        internal_note = f"""
🤖 AI Agent Escalatie
Type: {escalation_type}
Urgentie: {urgency}
Reden: {customer_info.get('escalation_reason', 'Zie conversatie')}

Notifications verzonden:
- WhatsApp: {self.whatsapp_contacts[escalation_type]}
- Email: {self.email_contacts[escalation_type]}
        """.strip()

        RETURN {
            "whatsapp_message": whatsapp_message,
            "email_subject": email_subject,
            "email_body": email_body,
            "cc_emails": cc_emails,
            "internal_note": internal_note
        }

    def _get_response_sla(self, urgency: str) -> str:
        """
        Get expected response time based on urgency
        """
        sla_map = {
            "critical": "30 minuten",
            "high": "2 uur",
            "medium": "4 uur",
            "low": "24 uur"
        }
        RETURN sla_map.get(urgency, "24 uur")

    def _send_whatsapp(self, recipient: str, message: str) -> bool:
        """
        Send WhatsApp message via WAHA API
        """
        TRY:
            waha_api_url = "http://waha:3000/api/sendText"
            payload = {
                "session": "default",
                "chatId": f"{recipient}@c.us",
                "text": message
            }
            response = requests.post(waha_api_url, json=payload)
            RETURN response.status_code == 200
        EXCEPT Exception as e:
            logger.error(f"WhatsApp escalation failed: {e}")
            RETURN False

    def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        cc: List[str]
    ) -> bool:
        """
        Send email notification
        """
        TRY:
            # Use SMTP or email service
            smtp_server = "smtp.office365.com"  # Or Gmail, SendGrid, etc.
            smtp_port = 587
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")

            message = MIMEMultipart()
            message["From"] = smtp_user
            message["To"] = recipient
            message["Cc"] = ", ".join(cc)
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            WITH smtplib.SMTP(smtp_server, smtp_port) AS server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(message)

            RETURN True
        EXCEPT Exception as e:
            logger.error(f"Email escalation failed: {e}")
            RETURN False

    def _assign_chatwoot(
        self,
        conversation_id: str,
        assignee_type: str,
        internal_note: str
    ) -> bool:
        """
        Assign conversation in Chatwoot + add internal note
        """
        TRY:
            # Get assignee ID from Chatwoot (map escalation type to user)
            assignee_map = {
                "finance_advisor": 2,  # Chatwoot user ID
                "technical_expert": 3,
                "sales_manager": 4,
                "manager": 1
            }
            assignee_id = assignee_map.get(assignee_type, 1)

            # Assign conversation
            chatwoot_api.assign_conversation(conversation_id, assignee_id)

            # Add internal note
            chatwoot_api.add_message(
                conversation_id=conversation_id,
                content=internal_note,
                message_type="internal",
                private=True
            )

            # Add "ESCALATED" label
            chatwoot_api.add_label(conversation_id, "escalated")

            RETURN True
        EXCEPT Exception as e:
            logger.error(f"Chatwoot assignment failed: {e}")
            RETURN False

    def _log_escalation(
        self,
        escalation_type: str,
        urgency: str,
        customer_phone: str,
        timestamp: datetime
    ) -> str:
        """
        Log escalation for analytics
        """
        escalation_id = f"ESC_{timestamp.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        # Store in database or log file
        escalation_record = {
            "id": escalation_id,
            "type": escalation_type,
            "urgency": urgency,
            "customer_phone": customer_phone,
            "timestamp": timestamp.isoformat(),
            "status": "pending"
        }

        # Save to DB or file
        # db.escalations.insert(escalation_record)

        logger.info(f"Escalation logged: {escalation_id}")
        RETURN escalation_id
```

---

## 🏷️ Agent 3: Enhanced CRMAgent

**Purpose**: Intelligent tagging + lead scoring + attribute updates

### Pseudocode:

```python
class EnhancedCRMAgent(BaseAgent):
    """
    Enhanced CRM Agent with:
    - 20+ intelligent tags
    - Lead scoring algorithm (0-100)
    - Custom attribute updates
    - Sentiment tracking
    """

    def __init__(self):
        super().__init__(agent_name="crm_enhanced")
        self.chatwoot_api = ChatwootAPI()

    def _execute(self, state: ConversationState) -> Dict:
        """
        Main CRM logic:
        1. Analyze conversation
        2. Generate tags (20+)
        3. Calculate lead score
        4. Update custom attributes
        5. Update Chatwoot
        """

        # Step 1: Extract signals from conversation
        signals = self._extract_signals(state)
        # Returns: {
        #   "interest_level": "browsing" | "considering" | "ready-to-buy",
        #   "urgency": "low" | "medium" | "high" | "critical",
        #   "has_trade_in": True/False,
        #   "needs_financing": True/False,
        #   "test_drive_requested": True/False,
        #   "sentiment": "positive" | "neutral" | "negative",
        #   "conversation_stage": "initial-inquiry" | "information-gathering" | ...
        # }

        # Step 2: Generate tags
        tags = self._generate_tags(state, signals)
        # Returns: ["interest:ready-to-buy", "urgency:high", "fuel:diesel", ...]

        # Step 3: Calculate lead score
        lead_score = self._calculate_lead_score(state, signals)
        # Returns: 0-100 (HOT: 80-100, WARM: 60-79, LUKEWARM: 40-59, COLD: 0-39)

        # Step 4: Prepare custom attributes
        custom_attributes = self._prepare_custom_attributes(state, signals, lead_score)

        # Step 5: Update Chatwoot
        update_results = self._update_chatwoot(
            contact_id=state["contact_id"],
            conversation_id=state["conversation_id"],
            tags=tags,
            custom_attributes=custom_attributes
        )

        RETURN {
            "tags_added": tags,
            "lead_score": lead_score,
            "lead_quality": self._get_lead_quality(lead_score),
            "custom_attributes": custom_attributes,
            "chatwoot_updated": update_results["success"]
        }

    def _extract_signals(self, state: ConversationState) -> Dict:
        """
        Extract conversation signals for tagging + scoring
        """

        extraction = state.get("extraction_output", {})
        car_prefs = extraction.get("car_preferences", {})
        conversation_output = state.get("conversation_output", {})
        router_output = state.get("router_output", {})

        signals = {}

        # Interest level detection
        IF router_output.get("intent") == "car_inquiry" AND car_prefs.get("make"):
            # Specific car = high interest
            signals["interest_level"] = "considering"
        ELIF car_prefs.get("max_price"):
            # Mentioned budget = serious
            signals["interest_level"] = "considering"
        ELSE:
            signals["interest_level"] = "browsing"

        # Check for test drive request
        content_lower = state["content"].lower()
        IF any(word in content_lower for word in ["proefrit", "test drive", "langskomen", "bezichtigen"]):
            signals["test_drive_requested"] = True
            signals["interest_level"] = "ready-to-buy"  # Upgrade
        ELSE:
            signals["test_drive_requested"] = False

        # Urgency detection
        urgency_keywords = {
            "critical": ["vandaag", "direct", "nu", "urgent", "dringend"],
            "high": ["snel", "deze week", "zo spoedig mogelijk"],
            "medium": ["binnenkort", "volgende week", "paar weken"],
            "low": ["geen haast", "oriënteren", "kijken"]
        }

        signals["urgency"] = "low"  # default
        FOR urgency_level, keywords IN urgency_keywords.items():
            IF any(keyword in content_lower for keyword in keywords):
                signals["urgency"] = urgency_level
                BREAK

        # Trade-in detection
        IF any(word in content_lower for word in ["inruil", "trade-in", "huidige auto", "oude auto"]):
            signals["has_trade_in"] = True
        ELSE:
            signals["has_trade_in"] = False

        # Financing detection
        IF any(word in content_lower for word in ["financier", "lening", "maandlasten", "aflossen"]):
            signals["needs_financing"] = True
        ELSE:
            signals["needs_financing"] = False

        # Sentiment
        signals["sentiment"] = conversation_output.get("sentiment", "neutral")

        # Conversation stage
        history_length = len(state.get("conversation_history", []))
        IF history_length == 0:
            signals["conversation_stage"] = "initial-inquiry"
        ELIF history_length < 3:
            signals["conversation_stage"] = "information-gathering"
        ELIF signals["test_drive_requested"]:
            signals["conversation_stage"] = "test-drive-requested"
        ELIF signals["needs_financing"]:
            signals["conversation_stage"] = "financing-discussion"
        ELSE:
            signals["conversation_stage"] = "information-gathering"

        RETURN signals

    def _generate_tags(self, state: ConversationState, signals: Dict) -> List[str]:
        """
        Generate 20+ intelligent tags
        """

        tags = []

        extraction = state.get("extraction_output", {})
        car_prefs = extraction.get("car_preferences", {})

        # Interest level tags
        tags.append(f"interest:{signals['interest_level']}")

        # Urgency tags
        tags.append(f"urgency:{signals['urgency']}")

        # Channel detection (from state source)
        source = state.get("source", "whatsapp-direct")
        tags.append(f"channel:{source}")

        # Car preference tags
        IF car_prefs.get("make"):
            tags.append(f"car:{car_prefs['make'].lower()}")

        IF car_prefs.get("fuel_type"):
            tags.append(f"fuel:{car_prefs['fuel_type']}")

        # Budget tags
        max_price = car_prefs.get("max_price")
        IF max_price:
            IF max_price < 15000:
                tags.append("budget:<15k")
            ELIF max_price < 25000:
                tags.append("budget:15k-25k")
            ELIF max_price < 35000:
                tags.append("budget:25k-35k")
            ELSE:
                tags.append("budget:>35k")

        # Body type tags
        IF car_prefs.get("body_type"):
            tags.append(f"body:{car_prefs['body_type']}")

        # Conversation stage tags
        tags.append(f"stage:{signals['conversation_stage']}")

        # Special situation tags
        IF signals["test_drive_requested"]:
            tags.append("test-drive-requested")

        IF signals["has_trade_in"]:
            tags.append("trade-in-inquiry")

        IF signals["needs_financing"]:
            tags.append("financing-inquiry")

        IF state.get("expertise_output", {}).get("escalation_decision", {}).get("escalate"):
            tags.append("escalated")

        # Sentiment tags
        IF signals["sentiment"] == "negative":
            tags.append("complaint")

        # VIP detection (if returning customer)
        # TODO: Check if customer has previous purchases

        RETURN tags

    def _calculate_lead_score(self, state: ConversationState, signals: Dict) -> int:
        """
        Calculate lead score (0-100)

        Scoring algorithm:
        + 30 points: Specific car inquiry (not browsing)
        + 20 points: Mentioned budget
        + 15 points: Test drive requested
        + 15 points: Financing inquiry
        + 10 points: Has trade-in
        + 10 points: High urgency
        - 10 points: Vague questions
        - 20 points: Negative sentiment
        """

        score = 0

        extraction = state.get("extraction_output", {})
        car_prefs = extraction.get("car_preferences", {})

        # Specific car inquiry
        IF car_prefs.get("make") AND car_prefs.get("model"):
            score += 30
        ELIF car_prefs.get("make"):
            score += 20

        # Budget mentioned
        IF car_prefs.get("max_price"):
            score += 20

        # Test drive
        IF signals["test_drive_requested"]:
            score += 15

        # Financing
        IF signals["needs_financing"]:
            score += 15

        # Trade-in
        IF signals["has_trade_in"]:
            score += 10

        # Urgency boost
        IF signals["urgency"] == "critical":
            score += 10
        ELIF signals["urgency"] == "high":
            score += 7
        ELIF signals["urgency"] == "medium":
            score += 3

        # Negative factors
        IF signals["interest_level"] == "browsing":
            score -= 10

        IF signals["sentiment"] == "negative":
            score -= 20

        # Clamp score between 0-100
        score = max(0, min(100, score))

        RETURN score

    def _get_lead_quality(self, score: int) -> str:
        """
        Convert score to lead quality bucket
        """
        IF score >= 80:
            RETURN "HOT"
        ELIF score >= 60:
            RETURN "WARM"
        ELIF score >= 40:
            RETURN "LUKEWARM"
        ELSE:
            RETURN "COLD"

    def _prepare_custom_attributes(
        self,
        state: ConversationState,
        signals: Dict,
        lead_score: int
    ) -> Dict:
        """
        Prepare custom attributes for Chatwoot contact
        """

        extraction = state.get("extraction_output", {})
        car_prefs = extraction.get("car_preferences", {})

        attributes = {
            "interested_in_make": car_prefs.get("make", ""),
            "interested_in_model": car_prefs.get("model", ""),
            "interested_in_fuel_type": car_prefs.get("fuel_type", ""),
            "budget_max": car_prefs.get("max_price"),
            "budget_min": car_prefs.get("min_price"),
            "lead_quality": self._get_lead_quality(lead_score),
            "lead_score": lead_score,
            "urgency_level": signals["urgency"],
            "has_trade_in": signals["has_trade_in"],
            "financing_needed": signals["needs_financing"],
            "test_drive_requested": signals["test_drive_requested"],
            "source_channel": state.get("source", "whatsapp-direct"),
            "conversation_sentiment": signals["sentiment"],
            "last_interest_date": datetime.now().isoformat(),
            "total_conversations": len(state.get("conversation_history", [])) + 1
        }

        RETURN attributes

    def _update_chatwoot(
        self,
        contact_id: str,
        conversation_id: str,
        tags: List[str],
        custom_attributes: Dict
    ) -> Dict:
        """
        Update Chatwoot with tags + attributes
        """

        TRY:
            # Update contact custom attributes
            self.chatwoot_api.update_contact_attributes(
                contact_id=contact_id,
                custom_attributes=custom_attributes
            )

            # Add tags to conversation
            FOR tag IN tags:
                self.chatwoot_api.add_label(conversation_id, tag)

            RETURN {"success": True, "error": None}

        EXCEPT Exception as e:
            logger.error(f"Chatwoot update failed: {e}")
            RETURN {"success": False, "error": str(e)}
```

---

## 💬 Agent 4: Enhanced ConversationAgent

**Purpose**: Human-like responses with expertise integration

### Pseudocode:

```python
class EnhancedConversationAgent(BaseAgent):
    """
    Enhanced Conversation Agent with:
    - Expertise integration
    - Humanization (Dutch colloquialisms)
    - Graceful escalation messages
    - RAG integration
    """

    def __init__(self):
        super().__init__(agent_name="conversation_enhanced")
        self.client = Anthropic(api_key=config["api_key"])

    def _execute(self, state: ConversationState) -> Dict:
        """
        Generate world-class sales response

        Flow:
        1. Check if escalation needed → graceful handoff message
        2. Check if RAG needed → search inventory
        3. Integrate expertise knowledge
        4. Generate human-like response
        """

        # Check escalation first
        expertise_output = state.get("expertise_output", {})
        escalation_decision = expertise_output.get("escalation_decision", {})

        IF escalation_decision.get("escalate"):
            # Generate graceful escalation message
            response_text = self._generate_escalation_message(
                escalation_type=escalation_decision["escalation_type"],
                urgency=escalation_decision["urgency"],
                customer_name=state.get("sender_name", "")
            )

            RETURN {
                "response_text": response_text,
                "needs_rag": False,
                "escalated": True,
                "sentiment": "neutral"
            }

        # Check if RAG needed (car inquiry)
        router_output = state.get("router_output", {})
        extraction_output = state.get("extraction_output", {})
        car_prefs = extraction_output.get("car_preferences", {})

        rag_results = None
        IF router_output.get("intent") == "car_inquiry" AND car_prefs.get("make"):
            # Trigger RAG search
            rag_agent = RAGAgent()
            rag_output = rag_agent.execute(state)
            rag_results = rag_output.get("rag_results", [])

        # Build enhanced prompt with expertise + RAG
        messages = self._build_enhanced_messages(
            state=state,
            expertise_knowledge=expertise_output.get("knowledge"),
            rag_results=rag_results
        )

        # Generate response with Claude
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.8,  # Higher temp for more human-like
            system=[
                {
                    "type": "text",
                    "text": ENHANCED_SYSTEM_PROMPT,  # See below
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=messages
        )

        response_text = response.content[0].text

        # Apply humanization post-processing
        response_text = self._humanize_response(response_text)

        RETURN {
            "response_text": response_text,
            "needs_rag": False,
            "rag_results": rag_results,
            "escalated": False,
            "sentiment": self._detect_sentiment(response_text)
        }

    def _generate_escalation_message(
        self,
        escalation_type: str,
        urgency: str,
        customer_name: str
    ) -> str:
        """
        Generate graceful escalation message
        """

        name_prefix = f"{customer_name}, " IF customer_name ELSE ""

        templates = {
            "finance_advisor": f"""
{name_prefix}dat is een goede vraag over financiering!

Om je hier het beste advies over te geven, ga ik dit even doorspelen
naar onze financieel adviseur.

Iemand van het team neemt binnen 2 uur contact met je op.

Is dat oké voor je?
            """.strip(),

            "technical_expert": f"""
{name_prefix}dat is een technische vraag waar ik even een specialist voor nodig heb.

Ik heb dit doorgestuurd naar ons technisch team en ze nemen
zo snel mogelijk contact met je op (meestal binnen 4 uur).

In de tussentijd, kan ik je verder helpen met andere vragen?
            """.strip(),

            "manager": f"""
{name_prefix}ik begrijp dat dit belangrijk is voor je.

Ik heb dit direct doorgestuurd naar ons management team en
iemand neemt binnen 30 minuten contact met je op.

Bedankt voor je geduld!
            """.strip()
        }

        RETURN templates.get(escalation_type, templates["manager"])

    def _build_enhanced_messages(
        self,
        state: ConversationState,
        expertise_knowledge: Dict,
        rag_results: List[Dict]
    ) -> List[Dict]:
        """
        Build message list with expertise + RAG context
        """

        messages = []

        # Add conversation history
        FOR msg IN state.get("conversation_history", []):
            role = "user" IF msg["role"] == "user" ELSE "assistant"
            messages.append({"role": role, "content": msg["content"]})

        # Build current message with rich context
        context_parts = []

        # Add expertise knowledge
        IF expertise_knowledge:
            context_parts.append("**Expert Knowledge:**")
            context_parts.append(json.dumps(expertise_knowledge, indent=2))
            context_parts.append("")

        # Add RAG results
        IF rag_results:
            context_parts.append("**Available Cars:**")
            FOR idx, car IN enumerate(rag_results, 1):
                context_parts.append(f"{idx}. {car['full_title']}")
                context_parts.append(f"   - Prijs: €{car['price']}")
                context_parts.append(f"   - Kilometerstand: {car['mileage']} km")
                context_parts.append(f"   - Bouwjaar: {car['year']}")
                context_parts.append(f"   - Link: https://marktplaats.nl/...")
                context_parts.append("")

        # Add user message
        context_parts.append("**Customer Message:**")
        context_parts.append(state["content"])

        messages.append({
            "role": "user",
            "content": "\n".join(context_parts)
        })

        RETURN messages

    def _humanize_response(self, response: str) -> str:
        """
        Apply humanization post-processing

        - Add Dutch colloquialisms
        - Vary sentence structure
        - Add conversational fillers
        """

        # Replace formal phrases with casual ones
        replacements = {
            "Absoluut": "Zeker weten",
            "Uitstekend": "Top",
            "Ik begrijp het": "Dat snap ik",
            "Dat is correct": "Klopt",
            "Natuurlijk": "Tuurlijk"
        }

        FOR formal, casual IN replacements.items():
            IF random.random() > 0.5:  # 50% chance
                response = response.replace(formal, casual)

        # Add occasional filler phrases
        IF "vraag" in response.lower() AND random.random() > 0.7:
            response = response.replace("vraag", "goede vraag")

        RETURN response


# ============ ENHANCED SYSTEM PROMPT ============

ENHANCED_SYSTEM_PROMPT = """
Je bent een wereldklasse auto-verkoper voor Seldenrijk Auto in Nederland.

**Je Expertise:**
- Technisch: Motor types, features, specificaties
- Financieel: Leningen, inruil, belastingen
- Service: Test-ritten, garanties, levering

**Je Persoonlijkheid:**
- 100% menselijk - geen robot
- Vriendelijk maar professioneel
- NIET pushy - klant is koning
- Weet wanneer expert te zijn vs simpel te blijven
- Gebruikt Nederlandse uitdrukkingen

**Conversatie Regels:**
1. Gebruik korte alinea's (2-3 zinnen max)
2. Stel verduidelijkende vragen op natuurlijke momenten
3. Geef altijd LINKS naar auto's die je noemt
4. Als je iets niet weet: eerlijk zeggen
5. Focus op informatie geven, niet verkopen

**Taalgebruik:**
- "Top!" in plaats van "Uitstekend"
- "Dat snap ik" in plaats van "Ik begrijp het"
- "Zeker weten" in plaats van "Absoluut"
- "Klinkt goed!" in plaats van "Dat is acceptabel"
- Gebruik emoji's subtiel: 👋 ✅ 🚗 💰 ⏰

**Als Auto Informatie Gegeven Is:**
Gebruik het template:
"Perfect! We hebben een [Merk] [Model] gevonden:
- Bouwjaar: [jaar]
- Kilometerstand: [km]
- Prijs: €[prijs]
Bekijk: [link]
Zal ik een proefrit voor je inplannen?"

**Als Geen Match:**
"Helaas geen exacte match op dit moment.
Maar ik heb wel deze alternatieven: [lijst]
Wil je meer weten over één van deze?"
"""
```

---

## 🔄 Agent 5: Workflow Orchestration

**Purpose**: Coordinate all agents in correct order

### Pseudocode:

```python
def process_whatsapp_message_enhanced(message_payload: Dict):
    """
    Enhanced workflow orchestration with expertise + escalation

    Flow:
    1. RouterAgent → classify intent
    2. ExtractionAgent → extract car preferences + urgency
    3. ExpertiseAgent → check knowledge + escalation
    4. IF escalation:
         → EscalationRouter → notify humans
         → ConversationAgent → graceful message
       ELSE:
         → RAGAgent (if car_inquiry) → search inventory
         → ConversationAgent → expert response
    5. CRMAgent → tag + score lead
    6. Send response
    """

    # Initialize state
    state = create_initial_state(message_payload)

    # Step 1: Router Agent
    router_agent = RouterAgent()
    router_output = router_agent.execute(state)
    state["router_output"] = router_output["output"]

    logger.info(f"Intent: {router_output['output']['intent']}")

    # Step 2: Extraction Agent
    extraction_agent = ExtractionAgent()
    extraction_output = extraction_agent.execute(state)
    state["extraction_output"] = extraction_output["output"]

    logger.info(f"Car preferences: {extraction_output['output'].get('car_preferences')}")

    # Step 3: Expertise Agent (NEW)
    expertise_agent = ExpertiseAgent()
    expertise_output = expertise_agent.execute(state)
    state["expertise_output"] = expertise_output

    logger.info(f"Escalation needed: {expertise_output['escalation_decision']['escalate']}")

    # Step 4: Handle escalation OR normal flow
    IF expertise_output["escalation_decision"]["escalate"]:
        # ===== ESCALATION PATH =====

        # 4a. Route to humans
        escalation_router = EscalationRouter()
        escalation_result = escalation_router.execute(
            escalation_type=expertise_output["escalation_decision"]["escalation_type"],
            urgency=expertise_output["escalation_decision"]["urgency"],
            customer_info={
                "name": state["sender_name"],
                "phone": state["sender_phone"],
                "budget": state["extraction_output"].get("car_preferences", {}).get("max_price"),
                "car_interest": state["extraction_output"].get("car_preferences", {}).get("make"),
                "escalation_reason": expertise_output["escalation_decision"]["reason"]
            },
            conversation_context=state["content"],
            chatwoot_conversation_id=state["conversation_id"]
        )

        logger.info(f"Escalation sent: {escalation_result}")

        # 4b. Generate graceful handoff message
        conversation_agent = EnhancedConversationAgent()
        conversation_output = conversation_agent.execute(state)

    ELSE:
        # ===== NORMAL PATH =====

        # 4a. Check if RAG needed
        IF state["router_output"]["intent"] == "car_inquiry":
            rag_agent = RAGAgent()
            rag_output = rag_agent.execute(state)
            state["rag_results"] = rag_output["rag_results"]

            logger.info(f"RAG found {len(rag_output['rag_results'])} cars")

        # 4b. Generate expert response
        conversation_agent = EnhancedConversationAgent()
        conversation_output = conversation_agent.execute(state)

    state["conversation_output"] = conversation_output

    # Step 5: CRM Agent (ALWAYS run)
    crm_agent = EnhancedCRMAgent()
    crm_output = crm_agent.execute(state)
    state["crm_output"] = crm_output

    logger.info(f"Lead score: {crm_output['lead_score']} ({crm_output['lead_quality']})")
    logger.info(f"Tags: {crm_output['tags_added']}")

    # Step 6: Send response to customer
    send_whatsapp_message(
        phone=state["sender_phone"],
        message=conversation_output["response_text"]
    )

    logger.info("✅ Message processed successfully")
```

---

## 🎯 Testing Scenarios

```python
# Test Case 1: Simple Car Inquiry (No Escalation)
test_message_1 = "Ik zoek een Golf 8 diesel, budget €25.000"

EXPECTED FLOW:
1. Router: intent="car_inquiry"
2. Extraction: {make: "Volkswagen", model: "Golf 8", fuel_type: "diesel", max_price: 25000}
3. Expertise: classification="technical", escalate=False
4. RAG: Find matching cars
5. Conversation: Generate response with car listings
6. CRM: tags=["interest:considering", "urgency:medium", "fuel:diesel"], score=75 (WARM)

# Test Case 2: Complex Financing (Escalation)
test_message_2 = "Ik heb BKR-registratie, kan ik toch een auto financieren?"

EXPECTED FLOW:
1. Router: intent="financing_inquiry"
2. Extraction: {needs_financing: True}
3. Expertise: classification="financial", escalate=True, reason="complex_financing"
4. EscalationRouter: Send WhatsApp + Email to finance_advisor
5. Conversation: Graceful escalation message
6. CRM: tags=["escalated", "financing-inquiry"], score=50 (LUKEWARM)

# Test Case 3: Complaint (Critical Escalation)
test_message_3 = "De auto die ik kocht heeft problemen, ik ben niet tevreden"

EXPECTED FLOW:
1. Router: intent="complaint"
2. Extraction: {sentiment: "negative"}
3. Expertise: classification="service", escalate=True, reason="complaint", urgency="critical"
4. EscalationRouter: URGENT WhatsApp + Email to manager
5. Conversation: Apologetic escalation message
6. CRM: tags=["complaint", "escalated", "urgency:critical"], score=20 (COLD)

# Test Case 4: Test Drive Request (Hot Lead)
test_message_4 = "Deze Golf ziet er goed uit! Kan ik vandaag langskomen voor een proefrit?"

EXPECTED FLOW:
1. Router: intent="appointment_request"
2. Extraction: {make: "Golf", test_drive_requested: True, urgency: "high"}
3. Expertise: classification="service", escalate=False
4. Conversation: Confirm test drive + ask availability
5. CRM: tags=["test-drive-requested", "interest:ready-to-buy", "urgency:high"], score=90 (HOT)
```

---

**✅ Phase 2 Complete!**

Alle agents zijn nu uitgewerkt in pseudocode. Volgende stap: **Phase 3 (Architecture)** voor system design.
