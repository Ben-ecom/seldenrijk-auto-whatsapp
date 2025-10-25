"""
Health check endpoints for monitoring and load balancers.
Provides basic and detailed health status.

Railway-optimized health checks with comprehensive monitoring.
"""
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
import psutil
import os
from app.database.supabase_pool import get_supabase_client
from app.database.postgres_pool import PostgresPool
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

class BasicHealthResponse(BaseModel):
    """Basic health check response."""
    status: str
    timestamp: str
    environment: Optional[str] = None
    version: Optional[str] = None

class ComponentStatus(BaseModel):
    """Individual component health status."""
    status: str  # healthy | unhealthy | degraded
    message: str
    latency_ms: Optional[float] = None
    metadata: Optional[dict] = None

class DetailedHealthResponse(BaseModel):
    """Detailed health check response with component status."""
    status: str
    timestamp: str
    version: str
    environment: str
    uptime_seconds: Optional[float] = None
    components: Dict[str, ComponentStatus]
    system: Optional[dict] = None
    deployment: Optional[dict] = None

# Track application start time for uptime calculation
_app_start_time = datetime.utcnow()

@router.get("/", response_model=BasicHealthResponse)
@router.get("/health", response_model=BasicHealthResponse)
async def basic_health_check():
    """
    Basic health check endpoint.
    Returns 200 if service is running.

    Used by:
    - Railway health checks
    - Docker healthcheck
    - Load balancers
    - Uptime monitoring
    """
    return BasicHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("ENVIRONMENT", "production"),
        version=os.getenv("GIT_COMMIT_SHA", "5.1.0")[:7]  # Short commit hash
    )

@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with component status.
    Checks database, Redis, Celery, and system resources.

    Returns:
        DetailedHealthResponse: Comprehensive health status
    """
    components = {}
    overall_status = "healthy"

    # Calculate uptime
    uptime = (datetime.utcnow() - _app_start_time).total_seconds()

    # Check Supabase connection
    supabase_start = datetime.utcnow()
    try:
        supabase = get_supabase_client()
        # Simple query to verify connection
        result = supabase.table("consent_records").select("id", count="exact").limit(1).execute()
        supabase_latency = (datetime.utcnow() - supabase_start).total_seconds() * 1000

        components["supabase"] = ComponentStatus(
            status="healthy",
            message="Connected",
            latency_ms=round(supabase_latency, 2),
            metadata={"table": "consent_records"}
        )
    except Exception as e:
        components["supabase"] = ComponentStatus(
            status="unhealthy",
            message=str(e)[:100]  # Truncate long error messages
        )
        overall_status = "degraded"
        logger.warning(f"Supabase health check failed: {e}")

    # Check PostgreSQL connection (if configured)
    postgres_start = datetime.utcnow()
    try:
        engine = PostgresPool.get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")

        postgres_latency = (datetime.utcnow() - postgres_start).total_seconds() * 1000

        # Get pool stats
        pool = engine.pool
        components["postgres"] = ComponentStatus(
            status="healthy",
            message="Connected",
            latency_ms=round(postgres_latency, 2),
            metadata={
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        )
    except Exception as e:
        components["postgres"] = ComponentStatus(
            status="unhealthy",
            message=str(e)[:100]
        )
        overall_status = "degraded"
        logger.warning(f"PostgreSQL health check failed: {e}")

    # Check Redis connection (CRITICAL for LangGraph checkpointing)
    redis_start = datetime.utcnow()
    try:
        from redis import Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
        redis_client.ping()

        redis_latency = (datetime.utcnow() - redis_start).total_seconds() * 1000

        # Get Redis info
        info = redis_client.info()
        components["redis"] = ComponentStatus(
            status="healthy",
            message="Connected",
            latency_ms=round(redis_latency, 2),
            metadata={
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_seconds": info.get("uptime_in_seconds"),
            }
        )
    except Exception as e:
        components["redis"] = ComponentStatus(
            status="unhealthy",
            message=f"Redis connection failed: {str(e)[:100]}"
        )
        overall_status = "unhealthy"  # Critical component
        logger.error(f"Redis health check failed: {e}")

    # Check Celery workers (optional - mark as degraded if down)
    try:
        from app.celery_app import app as celery_app
        inspect = celery_app.control.inspect(timeout=3.0)

        # Check if workers are alive
        stats = inspect.stats()
        if stats:
            active_workers = len(stats)
            components["celery"] = ComponentStatus(
                status="healthy",
                message=f"{active_workers} worker(s) active",
                metadata={
                    "workers": list(stats.keys())[:5]  # Limit to 5 worker names
                }
            )
        else:
            components["celery"] = ComponentStatus(
                status="degraded",
                message="No workers available (async jobs will queue)"
            )
            # Don't mark overall as unhealthy - system can work without Celery
    except Exception as e:
        components["celery"] = ComponentStatus(
            status="degraded",
            message="Celery health check timeout or error"
        )
        logger.warning(f"Celery health check failed: {e}")

    # Check LangGraph configuration
    try:
        from app.config.langgraph_config import (
            ENABLE_CHECKPOINTING,
            CHECKPOINT_BACKEND,
            REDIS_URL as LANGGRAPH_REDIS_URL
        )

        langgraph_status = "healthy" if ENABLE_CHECKPOINTING else "degraded"
        langgraph_message = f"Checkpointing enabled ({CHECKPOINT_BACKEND})" if ENABLE_CHECKPOINTING else "Checkpointing disabled (no fault tolerance)"

        components["langgraph"] = ComponentStatus(
            status=langgraph_status,
            message=langgraph_message,
            metadata={
                "checkpointing": ENABLE_CHECKPOINTING,
                "backend": CHECKPOINT_BACKEND,
                "redis_configured": bool(LANGGRAPH_REDIS_URL)
            }
        )

        if not ENABLE_CHECKPOINTING:
            overall_status = "degraded"

    except Exception as e:
        components["langgraph"] = ComponentStatus(
            status="unknown",
            message=f"Configuration check failed: {str(e)[:100]}"
        )

    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        system = {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": round(disk.percent, 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
        }

        # Check if resources are critically low
        if memory.percent > 90:
            overall_status = "degraded"
            logger.warning(f"High memory usage: {memory.percent}%")
        if disk.percent > 90:
            overall_status = "degraded"
            logger.warning(f"High disk usage: {disk.percent}%")

    except Exception as e:
        system = {"error": str(e)}
        logger.warning(f"System metrics collection failed: {e}")

    # Railway deployment info (if available)
    deployment = {}
    railway_vars = [
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_GIT_COMMIT_SHA",
        "RAILWAY_GIT_BRANCH",
        "RAILWAY_PUBLIC_DOMAIN"
    ]

    for var in railway_vars:
        value = os.getenv(var)
        if value:
            # Shorten long values
            if var == "RAILWAY_GIT_COMMIT_SHA":
                value = value[:7]
            deployment[var.lower().replace("railway_", "")] = value

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=os.getenv("GIT_COMMIT_SHA", "5.1.0")[:7],
        environment=os.getenv("ENVIRONMENT", "production"),
        uptime_seconds=round(uptime, 2),
        components=components,
        system=system,
        deployment=deployment if deployment else None
    )

@router.get("/health/liveness")
async def liveness_check():
    """
    Railway/Kubernetes liveness probe endpoint.
    Returns 200 if process is alive (even if dependencies are down).

    Used by Railway to determine if container should be restarted.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round((datetime.utcnow() - _app_start_time).total_seconds(), 2)
    }

@router.get("/health/readiness")
async def readiness_check():
    """
    Railway/Kubernetes readiness probe endpoint.
    Returns 200 only if all CRITICAL dependencies are healthy.

    Used by Railway to determine if traffic should be routed to this instance.

    Critical dependencies:
    - Redis (required for LangGraph checkpointing)
    - Supabase (required for data persistence)
    """
    errors = []

    # Check Redis (CRITICAL - required for LangGraph)
    try:
        from redis import Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, socket_timeout=3, socket_connect_timeout=3)
        redis_client.ping()
    except Exception as e:
        errors.append(f"Redis: {str(e)[:100]}")
        logger.error(f"Readiness check failed - Redis: {e}")

    # Check Supabase (CRITICAL - required for data)
    try:
        supabase = get_supabase_client()
        supabase.table("consent_records").select("id").limit(1).execute()
    except Exception as e:
        errors.append(f"Supabase: {str(e)[:100]}")
        logger.error(f"Readiness check failed - Supabase: {e}")

    # If any critical dependency failed, return 503
    if errors:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "All critical dependencies healthy"
    }

@router.get("/health/startup")
async def startup_check():
    """
    Railway startup probe endpoint.
    Returns 200 when application is fully initialized.

    More lenient than readiness check - allows time for initialization.
    """
    try:
        # Check if basic services are responding
        from redis import Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, socket_timeout=10)
        redis_client.ping()

        return {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round((datetime.utcnow() - _app_start_time).total_seconds(), 2)
        }
    except Exception as e:
        logger.warning(f"Startup check not ready: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Application still starting up: {str(e)[:100]}"
        )

@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus exposition format.

    For Railway monitoring and alerting.
    """
    try:
        from app.monitoring.metrics import get_metrics
        metrics = get_metrics()
        return Response(content=metrics, media_type="text/plain; version=0.0.4; charset=utf-8")
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return Response(
            content=f"# Metrics collection error: {str(e)}\n",
            media_type="text/plain"
        )

@router.get("/health/railway")
async def railway_health_check():
    """
    Railway-specific health check endpoint.
    Optimized for Railway's health check system.

    Returns 200 with minimal latency.
    """
    return {
        "ok": True,
        "service": "whatsapp-recruitment-platform",
        "version": os.getenv("GIT_COMMIT_SHA", "5.1.0")[:7]
    }
