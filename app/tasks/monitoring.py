"""
Monitoring and health check tasks.
Collects system metrics and performs health checks.
"""
from celery import Task
from datetime import datetime
from app.celery_app import celery_app
from app.monitoring.logging_config import get_logger
from app.monitoring.metrics import (
    db_connection_pool_size,
    db_connection_pool_available,
    celery_tasks_queued,
)
from app.database.postgres_pool import PostgresPool
import psutil
import os

logger = get_logger(__name__)

@celery_app.task(name="app.tasks.monitoring.collect_health_metrics")
def collect_health_metrics():
    """
    Collect system health metrics.
    Runs every 5 minutes.
    """
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {},
            "database": {},
            "celery": {},
        }

        # System metrics
        metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # Database metrics
        try:
            engine = PostgresPool.get_engine()
            pool = engine.pool

            db_connection_pool_size.set(pool.size())
            db_connection_pool_available.set(pool.size() - pool.checkedin())

            metrics["database"] = {
                "pool_size": pool.size(),
                "pool_available": pool.size() - pool.checkedin(),
                "pool_checked_in": pool.checkedin(),
                "pool_checked_out": pool.checkedout(),
                "pool_overflow": pool.overflow(),
            }
        except Exception as e:
            logger.error("Failed to collect database metrics", extra={"error": str(e)})
            metrics["database"]["error"] = str(e)

        # Celery metrics
        try:
            from celery import current_app
            inspect = current_app.control.inspect()

            # Get active tasks
            active_tasks = inspect.active()
            if active_tasks:
                total_active = sum(len(tasks) for tasks in active_tasks.values())
                metrics["celery"]["active_tasks"] = total_active

            # Get reserved tasks
            reserved_tasks = inspect.reserved()
            if reserved_tasks:
                total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
                metrics["celery"]["reserved_tasks"] = total_reserved

            # Get scheduled tasks
            scheduled_tasks = inspect.scheduled()
            if scheduled_tasks:
                total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
                metrics["celery"]["scheduled_tasks"] = total_scheduled

        except Exception as e:
            logger.error("Failed to collect Celery metrics", extra={"error": str(e)})
            metrics["celery"]["error"] = str(e)

        logger.info("Health metrics collected", extra=metrics)

        return metrics

    except Exception as e:
        logger.error("Health metrics collection failed", extra={"error": str(e)}, exc_info=True)
        raise
