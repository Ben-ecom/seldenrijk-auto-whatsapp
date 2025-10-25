"""
Celery tasks package.
"""
# Import all task modules to register tasks with Celery
from app.tasks.sync_inventory import sync_seldenrijk_inventory, trigger_immediate_inventory_sync

__all__ = ["sync_seldenrijk_inventory", "trigger_immediate_inventory_sync"]
