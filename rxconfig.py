"""
Reflex Dashboard Configuratie
"""

import reflex as rx


config = rx.Config(
    app_name="dashboard",  # Reflex app in dashboard/dashboard.py
    # Database (optioneel voor Reflex state)
    # db_url="sqlite:///reflex.db",

    # Environment
    env=rx.Env.DEV,

    # Frontend config
    frontend_port=3002,  # Port 3000 is in gebruik

    # Backend config
    backend_port=8001,  # Niet 8000 (FastAPI draait daar)

    # API URL
    api_url="http://localhost:8001",

    # Deployment
    deploy_url="https://yourdomain.com",
)
