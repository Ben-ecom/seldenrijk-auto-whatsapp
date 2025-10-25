"""
Maintenance and cleanup tasks for Celery.
Handles periodic cleanup of old data, task results, and logs.
"""
from celery import Task
from datetime import datetime, timedelta
from app.celery_app import celery_app
from app.monitoring.logging_config import get_logger
from app.database.supabase_pool import get_supabase_client

logger = get_logger(__name__)

@celery_app.task(name="app.tasks.maintenance.cleanup_task_results")
def cleanup_task_results():
    """
    Clean up old Celery task results from Redis.
    Runs every hour.
    """
    try:
        # Get all task keys from Redis
        from celery.result import AsyncResult
        from app.celery_app import celery_app as app

        # Cleanup tasks older than 1 hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        # This is handled by Celery's result_expires setting
        # Just log that cleanup ran
        logger.info("Task results cleanup completed")

        return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error("Task results cleanup failed", extra={"error": str(e)}, exc_info=True)
        raise

@celery_app.task(name="app.tasks.maintenance.cleanup_expired_exports")
def cleanup_expired_exports():
    """
    Clean up expired GDPR data exports.
    Runs daily at 3 AM.
    """
    supabase = get_supabase_client()

    try:
        # Find expired exports
        cutoff_time = datetime.utcnow().isoformat()

        result = supabase.table("gdpr_exports")\
            .select("*")\
            .lt("expires_at", cutoff_time)\
            .eq("status", "completed")\
            .execute()

        expired_exports = result.data

        if not expired_exports:
            logger.info("No expired exports to clean up")
            return {"status": "completed", "deleted_count": 0}

        # Delete files from storage and update records
        deleted_count = 0

        for export in expired_exports:
            try:
                # Delete file from storage
                if export.get("file_name"):
                    supabase.storage.from_("gdpr-exports").remove([export["file_name"]])

                # Update record status
                supabase.table("gdpr_exports")\
                    .update({"status": "expired", "download_url": None})\
                    .eq("id", export["id"])\
                    .execute()

                deleted_count += 1

            except Exception as e:
                logger.error(
                    "Failed to delete export file",
                    extra={"export_id": export["id"], "error": str(e)}
                )

        logger.info(
            "Expired exports cleanup completed",
            extra={"deleted_count": deleted_count}
        )

        return {"status": "completed", "deleted_count": deleted_count}

    except Exception as e:
        logger.error("Expired exports cleanup failed", extra={"error": str(e)}, exc_info=True)
        raise

@celery_app.task(name="app.tasks.maintenance.archive_old_conversations")
def archive_old_conversations():
    """
    Archive conversations older than retention policy.
    Runs weekly.
    """
    supabase = get_supabase_client()

    try:
        # Get retention policy for conversations
        policy_result = supabase.table("data_retention_policies")\
            .select("retention_days")\
            .eq("data_type", "conversations")\
            .single()\
            .execute()

        retention_days = policy_result.data["retention_days"]
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        logger.info(
            "Archiving conversations",
            extra={"cutoff_date": cutoff_date.isoformat(), "retention_days": retention_days}
        )

        # TODO: Implement conversation archiving logic
        # This depends on Chatwoot API capabilities

        return {
            "status": "completed",
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": retention_days,
        }

    except Exception as e:
        logger.error("Conversation archiving failed", extra={"error": str(e)}, exc_info=True)
        raise
