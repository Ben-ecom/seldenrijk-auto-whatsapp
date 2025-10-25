"""
Scheduled Inventory Sync Task.

Celery task that scrapes Seldenrijk vehicle inventory AND website content
using Playwright and caches results in Redis for fast agent queries.
"""
import json
import asyncio
from typing import Dict, Any
from datetime import timedelta
from celery import shared_task
from app.scrapers.seldenrijk_scraper import get_scraper
from app.scrapers.content_scraper import get_content_scraper
from app.integrations.chatwoot_sync import get_redis_client
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


@shared_task(name="sync_seldenrijk_inventory", bind=True, max_retries=3)
def sync_seldenrijk_inventory(self) -> Dict[str, Any]:
    """
    Sync Seldenrijk vehicle inventory AND website content to Redis cache.

    This task:
    1. Scrapes complete vehicle inventory using Playwright
    2. Scrapes website content (team, contact, financing, etc.)
    3. Stores all data in Redis with 2-hour TTL
    4. Creates brand/model indexes for fast filtering
    5. Logs sync status and counts

    Schedule: Every 2 hours via Celery Beat

    Returns:
        Dict with sync status and counts
    """
    try:
        logger.info("🚀 Starting scheduled Seldenrijk full sync (vehicles + content)")

        # Get scraper instances
        vehicle_scraper = get_scraper()
        content_scraper = get_content_scraper()

        # Scrape vehicles (run async function in event loop)
        logger.info("🚗 Scraping vehicle inventory...")
        vehicles = asyncio.run(vehicle_scraper.scrape_inventory())

        if not vehicles:
            logger.warning("⚠️ Vehicle scraping returned no vehicles")

        # Scrape website content
        logger.info("📄 Scraping website content...")
        content = asyncio.run(content_scraper.scrape_all_content())

        # Get Redis client
        redis_client = get_redis_client()

        # Store full inventory
        cache_key = "seldenrijk:inventory:full"
        redis_client.setex(
            cache_key,
            timedelta(hours=2),
            json.dumps(vehicles)
        )

        logger.info(
            "✅ Stored inventory in Redis cache",
            extra={
                "cache_key": cache_key,
                "vehicle_count": len(vehicles),
                "ttl_hours": 2
            }
        )

        # Create brand index for fast filtering
        _index_by_brand(redis_client, vehicles)

        # Create model index for fast filtering
        _index_by_model(redis_client, vehicles)

        # Store website content in Redis
        logger.info("💾 Storing website content in Redis...")

        # Store company info
        redis_client.setex(
            "seldenrijk:content:company_info",
            timedelta(hours=6),  # Longer TTL for static content
            json.dumps(content["company_info"])
        )

        # Store team members
        redis_client.setex(
            "seldenrijk:content:team_members",
            timedelta(hours=24),  # Even longer for team (rarely changes)
            json.dumps(content["team_members"])
        )

        # Store financing info
        redis_client.setex(
            "seldenrijk:content:financing",
            timedelta(hours=6),
            json.dumps(content["financing"])
        )

        # Store contact info
        redis_client.setex(
            "seldenrijk:content:contact",
            timedelta(hours=6),
            json.dumps(content["contact"])
        )

        logger.info(
            "✅ Stored website content in Redis",
            extra={
                "team_members": len(content["team_members"]),
                "financing_options": len(content["financing"].get("options", [])),
                "has_contact": bool(content["contact"])
            }
        )

        # Store metadata
        metadata = {
            "last_sync": vehicles[0]["scraped_at"] if vehicles else content["scraped_at"],
            "vehicle_count": len(vehicles),
            "brands": list(set(v["brand"] for v in vehicles)) if vehicles else [],
            "fuel_types": list(set(v["fuel"] for v in vehicles)) if vehicles else [],
            "team_member_count": len(content["team_members"]),
            "has_financing": content["financing"].get("available", False),
            "has_contact": bool(content["contact"])
        }

        redis_client.setex(
            "seldenrijk:inventory:metadata",
            timedelta(hours=2),
            json.dumps(metadata)
        )

        logger.info(
            f"✅ Full sync complete: {len(vehicles)} vehicles + {len(content['team_members'])} team members",
            extra={
                "vehicle_count": len(vehicles),
                "brands": len(metadata["brands"]),
                "team_members": len(content["team_members"])
            }
        )

        return {
            "status": "success",
            "vehicle_count": len(vehicles),
            "team_member_count": len(content["team_members"]),
            "brands": metadata["brands"],
            "message": f"Successfully synced {len(vehicles)} vehicles + website content"
        }

    except Exception as e:
        logger.error(
            f"❌ Inventory sync failed: {e}",
            exc_info=True,
            extra={"attempt": self.request.retries + 1}
        )

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


def _index_by_brand(redis_client, vehicles: list) -> None:
    """
    Create brand index for fast filtering.

    Creates Redis sets for each brand containing vehicle IDs.
    Allows O(1) brand lookup instead of full inventory scan.
    """
    try:
        # Clear existing brand indexes
        brand_keys = redis_client.keys("seldenrijk:inventory:brand:*")
        if brand_keys:
            redis_client.delete(*brand_keys)

        # Group vehicles by brand
        brand_groups = {}
        for vehicle in vehicles:
            brand = vehicle["brand"].lower()
            if brand not in brand_groups:
                brand_groups[brand] = []
            brand_groups[brand].append(vehicle)

        # Store each brand group
        for brand, brand_vehicles in brand_groups.items():
            brand_key = f"seldenrijk:inventory:brand:{brand}"
            redis_client.setex(
                brand_key,
                timedelta(hours=2),
                json.dumps(brand_vehicles)
            )

        logger.debug(
            f"✅ Indexed {len(brand_groups)} brands",
            extra={"brands": list(brand_groups.keys())}
        )

    except Exception as e:
        logger.warning(f"⚠️ Brand indexing failed: {e}")


def _index_by_model(redis_client, vehicles: list) -> None:
    """
    Create model index for fast filtering.

    Creates Redis sets for each model containing vehicle IDs.
    """
    try:
        # Clear existing model indexes
        model_keys = redis_client.keys("seldenrijk:inventory:model:*")
        if model_keys:
            redis_client.delete(*model_keys)

        # Group vehicles by model
        model_groups = {}
        for vehicle in vehicles:
            model = vehicle["model"].lower().replace(" ", "-")
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(vehicle)

        # Store each model group
        for model, model_vehicles in model_groups.items():
            model_key = f"seldenrijk:inventory:model:{model}"
            redis_client.setex(
                model_key,
                timedelta(hours=2),
                json.dumps(model_vehicles)
            )

        logger.debug(
            f"✅ Indexed {len(model_groups)} models",
            extra={"model_count": len(model_groups)}
        )

    except Exception as e:
        logger.warning(f"⚠️ Model indexing failed: {e}")


@shared_task(name="trigger_immediate_inventory_sync")
def trigger_immediate_inventory_sync() -> Dict[str, Any]:
    """
    Trigger immediate inventory sync (manual/on-demand).

    Use this when:
    - Cache is empty and agent needs data immediately
    - Testing scraper functionality
    - Manual refresh requested

    Returns:
        Dict with sync status
    """
    logger.info("⚡ Manual inventory sync triggered")
    return sync_seldenrijk_inventory()
