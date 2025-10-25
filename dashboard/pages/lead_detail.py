"""
Lead Detail Pagina

Toont:
- Lead informatie
- Qualification details
- Chat geschiedenis
- Live chat takeover
"""

import reflex as rx
from typing import Dict, Any


def lead_info_card(lead: Dict[str, Any]) -> rx.Component:
    """Lead informatie card."""
    return rx.box(
        rx.vstack(
            rx.heading("Lead Informatie", size="6", margin_bottom="1rem"),

            rx.vstack(
                rx.hstack(
                    rx.text("Naam:", weight="bold"),
                    rx.text(lead.get("full_name", "-")),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Telefoon:", weight="bold"),
                    rx.text(lead.get("whatsapp_number", "-")),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Status:", weight="bold"),
                    rx.badge(
                        lead.get("qualification_status", "new"),
                        color_scheme="green" if lead.get("qualification_status") == "qualified" else "yellow",
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Score:", weight="bold"),
                    rx.text(f"{int((lead.get('qualification_score', 0) or 0) * 100)}%"),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Aangemaakt:", weight="bold"),
                    rx.text(lead.get("created_at", "-")[:19] if lead.get("created_at") else "-"),
                    width="100%",
                ),

                spacing="3",
                align="start",
                width="100%",
            ),

            spacing="4",
            align="start",
            width="100%",
        ),
        padding="1.5rem",
        border_radius="0.75rem",
        background="#374151",
        border="1px solid #4B5563",
    )


def qualification_card(qualification: Dict[str, Any]) -> rx.Component:
    """Qualification details card."""
    if not qualification:
        return rx.box(
            rx.text("Nog geen qualification data beschikbaar", color="gray"),
            padding="1.5rem",
        )

    return rx.box(
        rx.vstack(
            rx.heading("Qualification Details", size="6", margin_bottom="1rem"),

            # Scores
            rx.vstack(
                rx.hstack(
                    rx.text("Technical Score:", weight="bold"),
                    rx.text(f"{qualification.get('technical_score', 0)}/40"),
                    rx.progress(
                        value=qualification.get("technical_score", 0),
                        max_value=40,
                        width="100px",
                    ),
                    width="100%",
                ),

                rx.hstack(
                    rx.text("Soft Skills Score:", weight="bold"),
                    rx.text(f"{qualification.get('soft_skills_score', 0)}/40"),
                    rx.progress(
                        value=qualification.get("soft_skills_score", 0),
                        max_value=40,
                        width="100px",
                    ),
                    width="100%",
                ),

                rx.hstack(
                    rx.text("Experience Score:", weight="bold"),
                    rx.text(f"{qualification.get('experience_score', 0)}/20"),
                    rx.progress(
                        value=qualification.get("experience_score", 0),
                        max_value=20,
                        width="100px",
                    ),
                    width="100%",
                ),

                rx.divider(),

                rx.hstack(
                    rx.text("Overall Score:", weight="bold", size="5"),
                    rx.text(
                        f"{qualification.get('overall_score', 0)}/100",
                        size="5",
                        weight="bold",
                        color="green" if qualification.get("overall_score", 0) >= 70 else "orange",
                    ),
                    width="100%",
                ),

                spacing="3",
                align="start",
                width="100%",
            ),

            # Skills
            rx.cond(
                qualification.get("skills"),
                rx.vstack(
                    rx.text("Skills:", weight="bold"),
                    rx.wrap(
                        rx.foreach(
                            qualification.get("skills", []),
                            lambda skill: rx.badge(skill, color_scheme="blue"),
                        ),
                        spacing="2",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
            ),

            # Missing info
            rx.cond(
                qualification.get("missing_info"),
                rx.vstack(
                    rx.text("Missing Info:", weight="bold", color="orange"),
                    rx.wrap(
                        rx.foreach(
                            qualification.get("missing_info", []),
                            lambda info: rx.badge(info, color_scheme="orange"),
                        ),
                        spacing="2",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
            ),

            spacing="4",
            align="start",
            width="100%",
        ),
        padding="1.5rem",
        border_radius="0.75rem",
        background="#374151",
        border="1px solid #4B5563",
    )


def chat_message(message: Dict[str, Any]) -> rx.Component:
    """Single chat message."""
    is_inbound = message.get("direction") == "inbound"

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.avatar(
                    fallback="👤" if is_inbound else "🤖",
                    size="2",
                ),
                rx.vstack(
                    rx.text(
                        "Kandidaat" if is_inbound else message.get("agent_name", "Agent"),
                        size="2",
                        weight="bold",
                    ),
                    rx.text(
                        message.get("created_at", "")[:19] if message.get("created_at") else "",
                        size="1",
                        color="gray",
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
            ),

            rx.box(
                rx.text(message.get("content", "")),
                padding="0.75rem",
                border_radius="0.5rem",
                background="#4B5563" if is_inbound else "#3B82F6",
                max_width="80%",
            ),

            spacing="2",
            align="start" if is_inbound else "end",
            width="100%",
        ),
        width="100%",
        margin_bottom="1rem",
    )


def chat_viewer(messages: list) -> rx.Component:
    """Chat geschiedenis viewer."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Chat Geschiedenis", size="6"),
                rx.spacer(),
                rx.badge(f"{len(messages)} berichten", color_scheme="blue"),
                width="100%",
                margin_bottom="1rem",
            ),

            # Messages
            rx.box(
                rx.foreach(
                    messages,
                    chat_message,
                ),
                height="500px",
                overflow_y="auto",
                width="100%",
                padding="1rem",
            ),

            # Manual message input (chat takeover)
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text("💬 Live Chat Takeover", weight="bold"),
                        rx.switch(
                            # on_change=DashboardState.toggle_takeover,
                            # checked=DashboardState.takeover_active,
                        ),
                        width="100%",
                    ),

                    # rx.cond(
                    #     DashboardState.takeover_active,
                        rx.hstack(
                            rx.input(
                                placeholder="Type je bericht...",
                                # value=DashboardState.manual_message,
                                # on_change=DashboardState.set_manual_message,
                                flex="1",
                            ),
                            rx.button(
                                "Verstuur",
                                # on_click=DashboardState.send_manual_message,
                            ),
                            width="100%",
                        ),
                    # ),

                    spacing="3",
                    width="100%",
                ),
                padding="1rem",
                border_top="1px solid #4B5563",
            ),

            spacing="0",
            width="100%",
        ),
        padding="1.5rem",
        border_radius="0.75rem",
        background="#374151",
        border="1px solid #4B5563",
        height="700px",
    )
