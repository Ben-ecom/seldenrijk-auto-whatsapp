"""
Migration Script: Redis → Supabase with OpenAI Embeddings

Transfers 427 vehicles from Redis to Supabase vehicle_inventory table.
Generates OpenAI embeddings for each vehicle for semantic search.

Usage:
    python -m app.scripts.migrate_redis_to_supabase

Requirements:
    - Redis running with seldenrijk:inventory:full key
    - Supabase credentials in environment
    - OpenAI API key for embeddings
"""
import asyncio
import json
from typing import List, Dict, Any
from app.integrations.chatwoot_sync import get_redis_client
from app.services.vector_store import get_vector_store
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


async def migrate_redis_to_supabase() -> Dict[str, Any]:
    """
    Migrate all vehicles from Redis to Supabase with embeddings.

    Returns:
        Migration statistics dict
    """
    logger.info("🚀 Starting Redis → Supabase migration")

    # Initialize services
    redis_client = get_redis_client()
    vector_store = get_vector_store()

    inventory_key = "seldenrijk:inventory:full"

    # Check if Redis inventory exists
    if not redis_client.exists(inventory_key):
        logger.error("❌ No inventory in Redis - scraper may not have run")
        return {
            "success": False,
            "error": "No inventory found in Redis",
            "migrated": 0,
            "failed": 0
        }

    # Load all vehicles from Redis
    inventory_json = redis_client.get(inventory_key)
    vehicles = json.loads(inventory_json)

    total_vehicles = len(vehicles)
    logger.info(f"✅ Loaded {total_vehicles} vehicles from Redis")

    # Migration counters
    migrated_count = 0
    failed_count = 0
    failed_vehicles = []

    # Migrate each vehicle with progress logging
    for idx, vehicle in enumerate(vehicles, 1):
        try:
            # Extract vehicle data
            external_id = vehicle.get("id")
            brand = vehicle.get("brand")
            model = vehicle.get("model")
            title = vehicle.get("title")
            price = vehicle.get("price", 0)
            build_year = vehicle.get("buildYear")
            mileage = vehicle.get("mileage")
            fuel = vehicle.get("fuel")
            transmission = vehicle.get("transmission")
            url = vehicle.get("url")
            image_url = vehicle.get("image")
            available = vehicle.get("available", True)

            # Validate required fields
            if not external_id or not brand or not model or not url:
                logger.warning(
                    f"⚠️ Skipping vehicle {idx}/{total_vehicles}: Missing required fields"
                )
                failed_count += 1
                failed_vehicles.append({
                    "index": idx,
                    "reason": "Missing required fields",
                    "data": vehicle
                })
                continue

            # Upsert vehicle with embedding generation
            vehicle_id = await vector_store.upsert_vehicle(
                external_id=external_id,
                brand=brand,
                model=model,
                title=title,
                price=price,
                build_year=build_year,
                mileage=mileage,
                fuel=fuel,
                transmission=transmission,
                url=url,
                image_url=image_url,
                available=available
            )

            migrated_count += 1

            # Log progress every 10 vehicles
            if idx % 10 == 0:
                logger.info(
                    f"📊 Progress: {idx}/{total_vehicles} vehicles processed "
                    f"({migrated_count} migrated, {failed_count} failed)"
                )

        except Exception as e:
            logger.error(
                f"❌ Failed to migrate vehicle {idx}/{total_vehicles}: {e}",
                exc_info=True
            )
            failed_count += 1
            failed_vehicles.append({
                "index": idx,
                "reason": str(e),
                "data": vehicle
            })

    # Final statistics
    logger.info("\n" + "="*60)
    logger.info("📊 MIGRATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Successfully migrated: {migrated_count}/{total_vehicles} vehicles")
    logger.info(f"❌ Failed: {failed_count}/{total_vehicles} vehicles")
    logger.info(f"📈 Success rate: {(migrated_count/total_vehicles*100):.1f}%")

    if failed_vehicles:
        logger.warning(f"\n⚠️ {len(failed_vehicles)} vehicles failed to migrate:")
        for failure in failed_vehicles[:5]:  # Show first 5 failures
            logger.warning(f"  - Vehicle {failure['index']}: {failure['reason']}")
        if len(failed_vehicles) > 5:
            logger.warning(f"  ... and {len(failed_vehicles) - 5} more")

    return {
        "success": True,
        "total_vehicles": total_vehicles,
        "migrated": migrated_count,
        "failed": failed_count,
        "success_rate": round(migrated_count / total_vehicles * 100, 1),
        "failed_vehicles": failed_vehicles
    }


def run_migration():
    """
    Synchronous wrapper for migration (for CLI execution).
    """
    result = asyncio.run(migrate_redis_to_supabase())

    if result["success"]:
        print(f"\n✅ Migration complete: {result['migrated']}/{result['total_vehicles']} vehicles")
    else:
        print(f"\n❌ Migration failed: {result.get('error')}")

    return result


if __name__ == "__main__":
    run_migration()
