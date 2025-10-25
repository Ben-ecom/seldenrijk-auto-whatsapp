"""
Escalation Router - Routes escalations to human staff via WhatsApp/Email/Chatwoot.

Handles:
- WhatsApp notifications to staff
- Email notifications via SMTP
- Chatwoot conversation assignment
- Escalation logging to database
"""
import os
import random
import smtplib
import requests
from typing import Dict, Any, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.monitoring.logging_config import get_logger
from app.integrations.chatwoot_api import ChatwootAPI

logger = get_logger(__name__)


class EscalationRouter:
    """Routes escalations to appropriate human staff members."""

    def __init__(self):
        # WhatsApp contact numbers (from env vars)
        self.whatsapp_contacts = {
            "finance_advisor": os.getenv("ESCALATION_WHATSAPP_FINANCE", "+31612345678"),
            "technical_expert": os.getenv("ESCALATION_WHATSAPP_TECHNICAL", "+31687654321"),
            "sales_manager": os.getenv("ESCALATION_WHATSAPP_SALES", "+31698765432"),
            "manager": os.getenv("ESCALATION_WHATSAPP_MANAGER", "+31611111111")
        }

        # Email contacts
        self.email_contacts = {
            "finance_advisor": os.getenv("ESCALATION_EMAIL_FINANCE", "finance@seldenrijk.nl"),
            "technical_expert": os.getenv("ESCALATION_EMAIL_TECHNICAL", "techniek@seldenrijk.nl"),
            "sales_manager": os.getenv("ESCALATION_EMAIL_SALES", "sales@seldenrijk.nl"),
            "manager": os.getenv("ESCALATION_EMAIL_MANAGER", "manager@seldenrijk.nl")
        }

        # SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.office365.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

        self.chatwoot_api = ChatwootAPI()

        logger.info("✅ EscalationRouter initialized")

    def execute(
        self,
        escalation_type: str,
        urgency: str,
        customer_info: Dict,
        conversation_context: str,
        chatwoot_conversation_id: str
    ) -> Dict[str, Any]:
        """
        Route escalation to appropriate channels.

        Args:
            escalation_type: finance_advisor, technical_expert, sales_manager, manager
            urgency: low, medium, high, critical
            customer_info: {name, phone, budget, car_interest, escalation_reason}
            conversation_context: Summary of conversation
            chatwoot_conversation_id: Chatwoot conversation ID

        Returns:
            {
                "whatsapp_sent": bool,
                "email_sent": bool,
                "chatwoot_assigned": bool,
                "notification_id": str
            }
        """
        logger.info(f"🚨 Escalating to {escalation_type} (urgency: {urgency})")

        # Determine channels based on urgency
        channels = self._determine_channels(urgency)

        # Prepare notifications
        notification = self._prepare_notification(
            escalation_type=escalation_type,
            urgency=urgency,
            customer_info=customer_info,
            conversation_context=conversation_context,
            chatwoot_url=f"https://chatwoot.yourdomain.com/app/accounts/1/conversations/{chatwoot_conversation_id}"
        )

        # Send notifications
        results = {}

        if "whatsapp" in channels:
            results["whatsapp_sent"] = self._send_whatsapp(
                recipient=self.whatsapp_contacts[escalation_type],
                message=notification["whatsapp_message"]
            )
        else:
            results["whatsapp_sent"] = False

        if "email" in channels:
            results["email_sent"] = self._send_email(
                recipient=self.email_contacts[escalation_type],
                subject=notification["email_subject"],
                body=notification["email_body"],
                cc=notification["cc_emails"]
            )
        else:
            results["email_sent"] = False

        # Assign in Chatwoot
        results["chatwoot_assigned"] = self._assign_chatwoot(
            conversation_id=chatwoot_conversation_id,
            assignee_type=escalation_type,
            internal_note=notification["internal_note"]
        )

        # Log escalation
        escalation_id = self._log_escalation(
            escalation_type=escalation_type,
            urgency=urgency,
            customer_phone=customer_info["phone"],
            conversation_id=chatwoot_conversation_id
        )

        results["notification_id"] = escalation_id

        logger.info(f"✅ Escalation {escalation_id} sent: WhatsApp={results['whatsapp_sent']}, Email={results['email_sent']}")

        return results

    def _determine_channels(self, urgency: str) -> List[str]:
        """Determine notification channels based on urgency."""
        if urgency in ["critical", "high"]:
            return ["whatsapp", "email"]
        elif urgency == "medium":
            return ["whatsapp"]
        else:  # low
            return ["email"]

    def _prepare_notification(
        self,
        escalation_type: str,
        urgency: str,
        customer_info: Dict,
        conversation_context: str,
        chatwoot_url: str
    ) -> Dict[str, str]:
        """Prepare notification messages."""
        # WhatsApp message (short)
        whatsapp_message = f"""🚨 ESCALATIE: {escalation_type.upper()}
Urgentie: {urgency.upper()}

Klant: {customer_info.get('name', 'Onbekend')}
Telefoon: {customer_info['phone']}
Interesse: {customer_info.get('car_interest', 'Onbekend')}

Context: {conversation_context[:200]}...

📱 Chatwoot: {chatwoot_url}

Actie vereist binnen {self._get_response_sla(urgency)}""".strip()

        # Email message (detailed)
        email_subject = f"[{urgency.upper()}] Escalatie: {escalation_type} - {customer_info.get('name', 'Klant')}"

        email_body = f"""Beste team,

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
WhatsApp AI Agent Systeem""".strip()

        # CC emails for high urgency
        cc_emails = []
        if urgency in ["critical", "high"]:
            cc_emails.append("manager@seldenrijk.nl")

        # Internal note
        internal_note = f"""🤖 AI Agent Escalatie
Type: {escalation_type}
Urgentie: {urgency}
Reden: {customer_info.get('escalation_reason', 'Zie conversatie')}

Notifications verzonden:
- WhatsApp: {self.whatsapp_contacts[escalation_type]}
- Email: {self.email_contacts[escalation_type]}""".strip()

        return {
            "whatsapp_message": whatsapp_message,
            "email_subject": email_subject,
            "email_body": email_body,
            "cc_emails": cc_emails,
            "internal_note": internal_note
        }

    def _get_response_sla(self, urgency: str) -> str:
        """Get expected response time."""
        sla_map = {
            "critical": "30 minuten",
            "high": "2 uur",
            "medium": "4 uur",
            "low": "24 uur"
        }
        return sla_map.get(urgency, "24 uur")

    def _send_whatsapp(self, recipient: str, message: str) -> bool:
        """Send WhatsApp message via WAHA API."""
        try:
            waha_url = os.getenv("WAHA_URL", "http://waha:3000/api/sendText")
            payload = {
                "session": "default",
                "chatId": f"{recipient}@c.us",
                "text": message
            }
            response = requests.post(waha_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"WhatsApp escalation failed: {e}")
            return False

    def _send_email(self, recipient: str, subject: str, body: str, cc: List[str]) -> bool:
        """Send email notification."""
        try:
            if not self.smtp_user or not self.smtp_password:
                logger.warning("SMTP not configured, skipping email")
                return False

            message = MIMEMultipart()
            message["From"] = self.smtp_user
            message["To"] = recipient
            message["Cc"] = ", ".join(cc)
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)

            return True
        except Exception as e:
            logger.error(f"Email escalation failed: {e}")
            return False

    def _assign_chatwoot(self, conversation_id: str, assignee_type: str, internal_note: str) -> bool:
        """Assign conversation in Chatwoot."""
        try:
            # Map escalation type to Chatwoot user ID (configure these!)
            assignee_map = {
                "finance_advisor": int(os.getenv("CHATWOOT_USER_FINANCE", "2")),
                "technical_expert": int(os.getenv("CHATWOOT_USER_TECH", "3")),
                "sales_manager": int(os.getenv("CHATWOOT_USER_SALES", "4")),
                "manager": int(os.getenv("CHATWOOT_USER_MANAGER", "1"))
            }
            assignee_id = assignee_map.get(assignee_type, 1)

            # Assign conversation
            self.chatwoot_api.assign_conversation(conversation_id, assignee_id)

            # Add internal note
            self.chatwoot_api.send_message(
                conversation_id=conversation_id,
                content=internal_note,
                message_type="outgoing",
                private=True
            )

            # Add escalated label
            self.chatwoot_api.add_label(conversation_id, "escalated")

            return True
        except Exception as e:
            logger.error(f"Chatwoot assignment failed: {e}")
            return False

    def _log_escalation(self, escalation_type: str, urgency: str, customer_phone: str, conversation_id: str) -> str:
        """Log escalation (could be DB or file)."""
        escalation_id = f"ESC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        # TODO: Insert into escalations table
        logger.info(f"📝 Escalation logged: {escalation_id}")

        return escalation_id
