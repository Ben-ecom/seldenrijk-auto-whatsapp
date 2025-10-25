"""
FastAPI Main Application

This is the main entry point for the WhatsApp Recruitment Platform API.
It handles:
- WhatsApp webhook receiver (360Dialog)
- Lead management endpoints
- Message history
- Authentication
- CORS and rate limiting
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routes import webhook, leads, messages, auth
from .middleware.rate_limiting import RateLimitMiddleware


# ============ LIFESPAN CONTEXT (startup/shutdown) ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context for startup and shutdown events.
    """
    # Startup
    print("🚀 Starting WhatsApp Recruitment Platform API...")
    print(f"📦 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"🔑 Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
    print(f"📞 WhatsApp Number: {os.getenv('THREESIXTY_DIALOG_PHONE_NUMBER', 'NOT SET')}")

    # TODO: Initialize background tasks (Celery workers)
    # TODO: Verify database connection
    # TODO: Check API keys are set

    yield

    # Shutdown
    print("🛑 Shutting down API...")


# ============ APP INITIALIZATION ============

app = FastAPI(
    title="WhatsApp Recruitment Platform API",
    description="""
    AI-powered recruitment platform with 2-agent system:
    - Agent 1 (Pydantic AI): Structured qualification extraction
    - Agent 2 (Claude SDK): Conversational WhatsApp agent with agentic RAG

    Features:
    - WhatsApp Business API integration (360Dialog)
    - Semantic job search (PGVector + OpenAI embeddings)
    - Calendar integration (Calendly)
    - Human escalation
    - Real-time qualification scoring
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ============ MIDDLEWARE ============

# CORS (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (prevent abuse)
app.add_middleware(RateLimitMiddleware)


# ============ EXCEPTION HANDLERS ============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


# ============ ROUTES ============

# Health check
@app.get("/")
async def root():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "WhatsApp Recruitment Platform",
        "version": "1.0.0",
        "agents": {
            "agent_1": "Pydantic AI (GPT-4o-mini) - Extraction",
            "agent_2": "Claude SDK (Claude 3.5 Sonnet) - Conversation"
        }
    }


@app.get("/health")
async def health():
    """
    Detailed health check with service dependencies.
    """
    # TODO: Check Supabase connection
    # TODO: Check OpenAI API
    # TODO: Check Anthropic API
    # TODO: Check 360Dialog API

    return {
        "status": "healthy",
        "checks": {
            "database": "ok",  # TODO: actual check
            "openai": "ok",    # TODO: actual check
            "anthropic": "ok", # TODO: actual check
            "whatsapp": "ok"   # TODO: actual check
        }
    }


# Include routers
app.include_router(webhook.router, prefix="/webhook", tags=["WhatsApp"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])


# ============ DEV SERVER ============

if __name__ == "__main__":
    """
    Run development server.

    Usage:
        python -m api.main
    """
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=True,
        log_level="info"
    )
