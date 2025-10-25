"""
Celery application configuration for async task processing.
Handles message processing, scheduled tasks, and background jobs.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Initialize Celery app
celery_app = Celery(
    "whatsapp_recruitment",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit (warning)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    worker_disable_rate_limits=False,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "visibility_timeout": 3600,
    },

    # Retry settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Task routing
    task_routes={
        "app.tasks.process_message.*": {"queue": "messages"},
        "app.tasks.gdpr.*": {"queue": "gdpr"},
        "app.tasks.crm.*": {"queue": "crm"},
    },

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Clean up old task results every hour
        "cleanup-task-results": {
            "task": "app.tasks.maintenance.cleanup_task_results",
            "schedule": crontab(minute=0),  # Every hour at :00
        },
        # GDPR data retention enforcement (daily at 2 AM)
        "gdpr-data-retention": {
            "task": "app.tasks.gdpr.enforce_data_retention",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
        },
        # Health check metrics (every 5 minutes)
        "health-check-metrics": {
            "task": "app.tasks.monitoring.collect_health_metrics",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        # Seldenrijk inventory sync (every 2 hours)
        "sync-seldenrijk-inventory": {
            "task": "sync_seldenrijk_inventory",
            "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours at :00
        },
    },
)

# Auto-discover tasks from all app modules
celery_app.autodiscover_tasks([
    "app.tasks.process_message",
    "app.tasks.gdpr",
    "app.tasks.crm",
    "app.tasks.maintenance",
    "app.tasks.monitoring",
    "app.tasks.sync_inventory",
])

# Task error handler
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "worker": self.request.hostname}
