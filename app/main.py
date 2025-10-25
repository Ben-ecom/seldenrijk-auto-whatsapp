"""
FastAPI Main Application
Seldenrijk Auto WhatsApp - Automotive AI Agent System
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.monitoring.sentry_config import init_sentry
from app.monitoring.logging_config import configure_logging, get_logger
from app.database.supabase_pool import SupabasePool
from app.database.postgres_pool import PostgresPool

# Import routers
from app.api.webhooks import router as webhooks_router
from app.api.health import router as health_router
from app.api.gdpr import router as gdpr_router

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting WhatsApp Recruitment Platform v5.1")

    # Initialize monitoring
    init_sentry()
    configure_logging()

    # Initialize database pools
    SupabasePool.get_client()
    PostgresPool.get_engine()

    logger.info("✅ All systems initialized")

    yield

    # Shutdown
    logger.info("🛑 Shutting down application")

    # Close database connections
    SupabasePool.close()
    PostgresPool.close()

    logger.info("✅ Graceful shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Seldenrijk Auto WhatsApp",
    version="1.0.0",
    description="Automotive AI Agent System with LangGraph orchestration",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# Add slowapi rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id

        from app.monitoring.logging_config import add_request_id
        add_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        from app.monitoring.logging_config import clear_request_context
        clear_request_context()

        return response

app.add_middleware(RequestIDMiddleware)

# Register routers
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(gdpr_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {
        "name": "Seldenrijk Auto WhatsApp",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs" if os.getenv("ENVIRONMENT") != "production" else None
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False,
        log_level="info"
    )
