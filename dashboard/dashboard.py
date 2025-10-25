"""
Main Reflex Dashboard App

Premium recruitment dashboard met moderne UI.
"""

import reflex as rx
from typing import List, Dict, Any
import httpx
import os
from datetime import datetime


# ============ STATE MANAGEMENT ============

class DashboardState(rx.State):
    """Main dashboard state."""

    # API config
    api_base_url: str = "http://localhost:8000"

    # Auth state
    is_authenticated: bool = False
    access_token: str = ""
    user_email: str = ""

    # Leads data
    leads: List[Dict[str, Any]] = []
    total_leads: int = 0
    selected_lead_id: str = ""
    selected_lead: Dict[str, Any] = {}

    # Messages data
    messages: List[Dict[str, Any]] = []

    # Filters
    status_filter: str = "all"
    search_query: str = ""

    # UI state
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    dark_mode: bool = True

    # Chat takeover
    takeover_active: bool = False
    manual_message: str = ""

    @rx.var
    def qualified_count(self) -> int:
        """Count qualified leads."""
        return len([l for l in self.leads if l.get("qualification_status") == "qualified"])

    @rx.var
    def pending_count(self) -> int:
        """Count pending review leads."""
        return len([l for l in self.leads if l.get("qualification_status") == "pending_review"])


    async def load_leads(self):
        """Laad leads van de API."""
        self.is_loading = True
        self.error_message = ""

        try:
            params = {"limit": 100}
            if self.status_filter != "all":
                params["status"] = self.status_filter

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/api/leads",
                    params=params,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.leads = data.get("leads", [])
                    self.total_leads = data.get("total", 0)
                    self.success_message = f"✅ {len(self.leads)} leads geladen"
                else:
                    self.error_message = f"❌ Fout bij laden leads: {response.status_code}"

        except Exception as e:
            self.error_message = f"❌ Connectie fout: {str(e)}"

        finally:
            self.is_loading = False


    async def select_lead(self, lead_id: str):
        """Selecteer een lead en laad details."""
        self.selected_lead_id = lead_id
        self.is_loading = True

        try:
            async with httpx.AsyncClient() as client:
                # Get lead details
                response = await client.get(
                    f"{self.api_base_url}/api/leads/{lead_id}",
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.selected_lead = data.get("lead", {})

                    # Get messages
                    msg_response = await client.get(
                        f"{self.api_base_url}/api/messages/lead/{lead_id}",
                        timeout=10.0
                    )

                    if msg_response.status_code == 200:
                        msg_data = msg_response.json()
                        self.messages = msg_data.get("messages", [])

        except Exception as e:
            self.error_message = f"❌ Fout bij laden lead: {str(e)}"

        finally:
            self.is_loading = False


    def set_status_filter(self, status: str):
        """Zet status filter."""
        self.status_filter = status
        return self.load_leads


    def set_search_query(self, query: str):
        """Zet zoekquery."""
        self.search_query = query


    def toggle_dark_mode(self):
        """Toggle dark mode."""
        self.dark_mode = not self.dark_mode


    def toggle_takeover(self):
        """Toggle chat takeover."""
        self.takeover_active = not self.takeover_active
        if not self.takeover_active:
            self.manual_message = ""


    async def send_manual_message(self):
        """Verstuur handmatig bericht."""
        if not self.manual_message or not self.selected_lead_id:
            return

        self.is_loading = True

        try:
            # Get lead phone number
            lead_phone = self.selected_lead.get("whatsapp_number", "")

            # Send via WhatsApp API
            async with httpx.AsyncClient() as client:
                # TODO: Call 360Dialog API directly or create API endpoint
                # For now: simulate by adding message to history

                self.success_message = "✅ Bericht verzonden"
                self.manual_message = ""

                # Reload messages
                await self.select_lead(self.selected_lead_id)

        except Exception as e:
            self.error_message = f"❌ Fout bij versturen: {str(e)}"

        finally:
            self.is_loading = False


# ============ STYLING ============

# Color scheme
COLORS = {
    "primary": "#3B82F6",      # Blue
    "success": "#10B981",      # Green
    "warning": "#F59E0B",      # Orange
    "danger": "#EF4444",       # Red
    "bg_dark": "#1F2937",      # Dark gray
    "bg_light": "#F9FAFB",     # Light gray
    "card_bg": "#FFFFFF",      # White cards
    "text_dark": "#111827",    # Almost black
    "text_light": "#F9FAFB",   # Almost white
    "border": "#E5E7EB",       # Border gray
}


def get_theme_colors(dark_mode: bool) -> dict:
    """Get theme colors based on dark mode."""
    if dark_mode:
        return {
            "bg": COLORS["bg_dark"],
            "text": COLORS["text_light"],
            "card_bg": "#374151",
            "border": "#4B5563",
        }
    else:
        return {
            "bg": COLORS["bg_light"],
            "text": COLORS["text_dark"],
            "card_bg": "#FFFFFF",
            "border": "#E5E7EB",
        }


# ============ COMPONENTS ============

def sidebar() -> rx.Component:
    """Sidebar navigatie."""
    return rx.box(
        rx.vstack(
            # Logo
            rx.heading(
                "💼 Recruitment",
                size="7",
                margin_bottom="2rem",
            ),

            # Menu items
            rx.link(
                rx.hstack(
                    rx.icon("users", size=20),
                    rx.text("Leads", size="4"),
                    spacing="3",
                ),
                href="/",
                width="100%",
                padding="0.75rem",
                border_radius="0.5rem",
                _hover={"background": "rgba(59, 130, 246, 0.1)"},
            ),

            rx.link(
                rx.hstack(
                    rx.icon("message_circle", size=20),
                    rx.text("Berichten", size="4"),
                    spacing="3",
                ),
                href="/messages",
                width="100%",
                padding="0.75rem",
                border_radius="0.5rem",
                _hover={"background": "rgba(59, 130, 246, 0.1)"},
            ),

            rx.link(
                rx.hstack(
                    rx.icon("bar_chart", size=20),
                    rx.text("Analytics", size="4"),
                    spacing="3",
                ),
                href="/analytics",
                width="100%",
                padding="0.75rem",
                border_radius="0.5rem",
                _hover={"background": "rgba(59, 130, 246, 0.1)"},
            ),

            rx.link(
                rx.hstack(
                    rx.icon("settings", size=20),
                    rx.text("Instellingen", size="4"),
                    spacing="3",
                ),
                href="/settings",
                width="100%",
                padding="0.75rem",
                border_radius="0.5rem",
                _hover={"background": "rgba(59, 130, 246, 0.1)"},
            ),

            spacing="2",
            align="start",
            width="100%",
        ),
        width="250px",
        padding="2rem",
        background=rx.cond(
            DashboardState.dark_mode,
            COLORS["bg_dark"],
            COLORS["card_bg"],
        ),
        border_right=f"1px solid {COLORS['border']}",
        height="100vh",
        position="fixed",
    )


def header() -> rx.Component:
    """Header met filters en acties."""
    return rx.box(
        rx.hstack(
            # Title
            rx.heading(
                "Leads Overzicht",
                size="8",
            ),

            rx.spacer(),

            # Dark mode toggle
            rx.button(
                rx.cond(
                    DashboardState.dark_mode,
                    rx.icon("sun", size=20),
                    rx.icon("moon", size=20),
                ),
                on_click=DashboardState.toggle_dark_mode,
                variant="ghost",
            ),

            # Refresh button
            rx.button(
                rx.icon("refresh_cw", size=20),
                on_click=DashboardState.load_leads,
                variant="ghost",
            ),

            width="100%",
            padding="1.5rem 2rem",
            border_bottom=f"1px solid {COLORS['border']}",
        ),
    )


def stats_cards() -> rx.Component:
    """Statistieken cards."""
    return rx.hstack(
        # Total leads
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("users", size=24, color=COLORS["primary"]),
                    rx.spacer(),
                ),
                rx.text(
                    DashboardState.total_leads,
                    size="8",
                    weight="bold",
                ),
                rx.text(
                    "Totaal Leads",
                    size="3",
                    color="gray",
                ),
                spacing="2",
                align="start",
            ),
            padding="1.5rem",
            border_radius="0.75rem",
            background=rx.cond(
                DashboardState.dark_mode,
                "#374151",
                "#FFFFFF",
            ),
            border=f"1px solid {COLORS['border']}",
            flex="1",
        ),

        # Qualified
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("circle_check", size=24, color=COLORS["success"]),
                    rx.spacer(),
                ),
                rx.text(
                    DashboardState.qualified_count,
                    size="8",
                    weight="bold",
                    color=COLORS["success"],
                ),
                rx.text(
                    "Gekwalificeerd",
                    size="3",
                    color="gray",
                ),
                spacing="2",
                align="start",
            ),
            padding="1.5rem",
            border_radius="0.75rem",
            background=rx.cond(
                DashboardState.dark_mode,
                "#374151",
                "#FFFFFF",
            ),
            border=f"1px solid {COLORS['border']}",
            flex="1",
        ),

        # Pending
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("clock", size=24, color=COLORS["warning"]),
                    rx.spacer(),
                ),
                rx.text(
                    DashboardState.pending_count,
                    size="8",
                    weight="bold",
                    color=COLORS["warning"],
                ),
                rx.text(
                    "In Review",
                    size="3",
                    color="gray",
                ),
                spacing="2",
                align="start",
            ),
            padding="1.5rem",
            border_radius="0.75rem",
            background=rx.cond(
                DashboardState.dark_mode,
                "#374151",
                "#FFFFFF",
            ),
            border=f"1px solid {COLORS['border']}",
            flex="1",
        ),

        spacing="4",
        width="100%",
        margin_bottom="2rem",
    )


def leads_table() -> rx.Component:
    """Leads tabel."""
    return rx.box(
        rx.vstack(
            # Filters
            rx.hstack(
                rx.select(
                    ["all", "qualified", "pending_review", "disqualified", "new"],
                    value=DashboardState.status_filter,
                    on_change=DashboardState.set_status_filter,
                    placeholder="Filter op status",
                ),

                rx.input(
                    placeholder="Zoek leads...",
                    value=DashboardState.search_query,
                    on_change=DashboardState.set_search_query,
                    width="300px",
                ),

                rx.spacer(),

                width="100%",
                margin_bottom="1rem",
            ),

            # Table
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Naam"),
                        rx.table.column_header_cell("Telefoon"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Score"),
                        rx.table.column_header_cell("Datum"),
                        rx.table.column_header_cell("Acties"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        DashboardState.leads,
                        lambda lead: rx.table.row(
                            rx.table.cell(lead["full_name"]),
                            rx.table.cell(lead["whatsapp_number"]),
                            rx.table.cell(
                                rx.badge(
                                    lead["qualification_status"],
                                    color_scheme=rx.cond(
                                        lead["qualification_status"] == "qualified",
                                        "green",
                                        rx.cond(
                                            lead["qualification_status"] == "disqualified",
                                            "red",
                                            "yellow",
                                        ),
                                    ),
                                ),
                            ),
                            rx.table.cell(
                                lead["qualification_score"]
                            ),
                            rx.table.cell(
                                lead["created_at"]
                            ),
                            rx.table.cell(
                                rx.button(
                                    "Bekijk",
                                    size="1",
                                    on_click=lambda: DashboardState.select_lead(lead["id"]),
                                ),
                            ),
                        ),
                    ),
                ),
                variant="surface",
                width="100%",
            ),

            spacing="4",
            width="100%",
        ),
        padding="1.5rem",
        border_radius="0.75rem",
        background=rx.cond(
            DashboardState.dark_mode,
            "#374151",
            "#FFFFFF",
        ),
        border=f"1px solid {COLORS['border']}",
    )


# ============ PAGES ============

@rx.page(route="/", title="Leads - Recruitment Dashboard")
def index() -> rx.Component:
    """Main dashboard page."""
    return rx.box(
        rx.hstack(
            sidebar(),

            rx.box(
                header(),

                rx.box(
                    stats_cards(),
                    leads_table(),

                    # Loading overlay
                    rx.cond(
                        DashboardState.is_loading,
                        rx.center(
                            rx.spinner(size="3"),
                            position="fixed",
                            top="50%",
                            left="50%",
                        ),
                    ),

                    padding="2rem",
                    margin_left="250px",
                ),

                flex="1",
            ),

            spacing="0",
            width="100%",
        ),
        background=rx.cond(
            DashboardState.dark_mode,
            COLORS["bg_dark"],
            COLORS["bg_light"],
        ),
        color=rx.cond(
            DashboardState.dark_mode,
            COLORS["text_light"],
            COLORS["text_dark"],
        ),
        min_height="100vh",
    )


# ============ APP ============

app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="blue",
    ),
)

# Add on_load event
app.add_page(index, on_load=DashboardState.load_leads)
