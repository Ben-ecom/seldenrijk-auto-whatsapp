"""
API Module: FastAPI Backend

This module provides the REST API for the WhatsApp Recruitment Platform.

Features:
- WhatsApp webhook receiver (360Dialog)
- Lead management (CRUD)
- Message history
- Authentication (Supabase Auth + JWT)
- Rate limiting
- CORS

Architecture:
    Webhook → Orchestration → Agent 1 + Agent 2 → Database → WhatsApp Reply

Endpoints:
    POST /webhook/whatsapp      - Receive WhatsApp messages
    GET  /api/leads             - List leads
    GET  /api/leads/{id}        - Get lead details
    POST /api/leads             - Create lead
    GET  /api/messages          - List messages
    POST /api/auth/login        - Login
"""

__all__ = ["main"]
