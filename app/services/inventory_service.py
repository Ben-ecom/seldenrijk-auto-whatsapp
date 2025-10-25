"""
Inventory Query Service.

Provides fast vehicle search and filtering from Redis cache.
Used by conversation agent to answer customer inquiries about available cars.
"""
import json
from typing import List, Dict, Optional, Any
from app.integrations.chatwoot_sync import get_redis_client
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class InventoryService:
    """
    Query Seldenrijk vehicle inventory from Redis cache.

    Features:
    - Fast Redis-based queries (< 50ms)
    - Multiple filter options (brand, model, price, fuel)
    - Graceful fallback when cache empty
    - Detailed logging for debugging
    """

    def __init__(self):
        """Initialize inventory service."""
        self.redis = get_redis_client()
        self.cache_key = "seldenrijk:inventory:full"

    async def search_vehicles(
        self,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
        fuel_type: Optional[str] = None,
        max_mileage: Optional[int] = None,
        min_year: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search inventory with multiple filters.

        Args:
            brand: Filter by brand (e.g., "BMW", "Mercedes")
            model: Filter by model (e.g., "X5", "C-Class")
            max_price: Maximum price in euros
            min_price: Minimum price in euros
            fuel_type: Filter by fuel type (e.g., "Hybride", "Diesel", "Benzine")
            max_mileage: Maximum mileage in kilometers
            min_year: Minimum build year
            limit: Maximum number of results to return

        Returns:
            List of matching vehicles (empty list if cache empty)

        Examples:
            # Find BMW X5 models
            vehicles = await service.search_vehicles(brand="BMW", model="X5")

            # Find hybrid cars under €50,000
            vehicles = await service.search_vehicles(fuel_type="Hybride", max_price=50000)

            # Find recent BMWs with low mileage
            vehicles = await service.search_vehicles(
                brand="BMW",
                min_year=2020,
                max_mileage=30000
            )
        """
        try:
            # Try brand-specific index first (faster)
            if brand and not any([model, max_price, min_price, fuel_type, max_mileage, min_year]):
                vehicles = await self._get_by_brand(brand)
            else:
                # Get full inventory from cache
                vehicles = await self._get_full_inventory()

            if not vehicles:
                logger.warning(
                    "⚠️ Inventory cache empty",
                    extra={"cache_key": self.cache_key}
                )
                return []

            # Apply filters
            filtered = vehicles

            if brand:
                filtered = [
                    v for v in filtered
                    if v.get("brand", "").lower() == brand.lower()
                ]

            if model:
                filtered = [
                    v for v in filtered
                    if model.lower() in v.get("model", "").lower()
                ]

            if max_price:
                filtered = [
                    v for v in filtered
                    if v.get("price", 0) <= max_price
                ]

            if min_price:
                filtered = [
                    v for v in filtered
                    if v.get("price", 0) >= min_price
                ]

            if fuel_type:
                filtered = [
                    v for v in filtered
                    if v.get("fuel", "").lower() == fuel_type.lower()
                ]

            if max_mileage:
                filtered = [
                    v for v in filtered
                    if v.get("mileage", 0) <= max_mileage
                ]

            if min_year:
                filtered = [
                    v for v in filtered
                    if v.get("buildYear", 0) >= min_year
                ]

            # Apply limit
            if limit:
                filtered = filtered[:limit]

            logger.info(
                f"🔍 Inventory search: {len(filtered)} matches",
                extra={
                    "filters": {
                        "brand": brand,
                        "model": model,
                        "max_price": max_price,
                        "min_price": min_price,
                        "fuel_type": fuel_type,
                        "max_mileage": max_mileage,
                        "min_year": min_year,
                        "limit": limit
                    },
                    "result_count": len(filtered)
                }
            )

            return filtered

        except Exception as e:
            logger.error(f"❌ Inventory search failed: {e}", exc_info=True)
            return []

    async def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific vehicle by ID.

        Args:
            vehicle_id: Vehicle identifier (from URL slug)

        Returns:
            Vehicle dictionary or None if not found

        Example:
            vehicle = await service.get_vehicle_by_id("bmw-x5-xdrive30e-12345")
        """
        try:
            vehicles = await self._get_full_inventory()

            if not vehicles:
                return None

            for vehicle in vehicles:
                if vehicle.get("id") == vehicle_id:
                    logger.info(
                        f"✅ Found vehicle by ID: {vehicle_id}",
                        extra={"vehicle_id": vehicle_id}
                    )
                    return vehicle

            logger.warning(
                f"⚠️ Vehicle not found: {vehicle_id}",
                extra={"vehicle_id": vehicle_id}
            )
            return None

        except Exception as e:
            logger.error(f"❌ Get vehicle by ID failed: {e}", exc_info=True)
            return None

    async def get_available_brands(self) -> List[str]:
        """
        Get list of all brands in current inventory.

        Returns:
            List of brand names (sorted alphabetically)

        Example:
            brands = await service.get_available_brands()
            # Returns: ["Audi", "BMW", "Mercedes-Benz", "Volvo", ...]
        """
        try:
            metadata = self.redis.get("seldenrijk:inventory:metadata")

            if metadata:
                data = json.loads(metadata)
                brands = sorted(data.get("brands", []))
                logger.debug(f"✅ Found {len(brands)} brands in metadata")
                return brands

            # Fallback: extract from full inventory
            vehicles = await self._get_full_inventory()
            brands = sorted(list(set(v["brand"] for v in vehicles if v.get("brand"))))

            logger.debug(f"✅ Extracted {len(brands)} brands from inventory")
            return brands

        except Exception as e:
            logger.error(f"❌ Get available brands failed: {e}", exc_info=True)
            return []

    async def get_inventory_stats(self) -> Dict[str, Any]:
        """
        Get inventory statistics and metadata.

        Returns:
            Dict with inventory stats (vehicle count, brands, fuel types, etc.)

        Example:
            stats = await service.get_inventory_stats()
            # Returns: {
            #     "vehicle_count": 447,
            #     "brands": ["BMW", "Mercedes-Benz", ...],
            #     "fuel_types": ["Benzine", "Diesel", "Hybride"],
            #     "last_sync": "2025-10-17T13:30:00"
            # }
        """
        try:
            metadata = self.redis.get("seldenrijk:inventory:metadata")

            if metadata:
                stats = json.loads(metadata)
                logger.debug("✅ Retrieved inventory stats from metadata")
                return stats

            # Fallback: calculate from full inventory
            vehicles = await self._get_full_inventory()

            if not vehicles:
                return {
                    "vehicle_count": 0,
                    "brands": [],
                    "fuel_types": [],
                    "last_sync": None,
                    "cache_status": "empty"
                }

            stats = {
                "vehicle_count": len(vehicles),
                "brands": sorted(list(set(v["brand"] for v in vehicles))),
                "fuel_types": sorted(list(set(v["fuel"] for v in vehicles))),
                "last_sync": vehicles[0].get("scraped_at") if vehicles else None,
                "cache_status": "active"
            }

            logger.debug("✅ Calculated inventory stats from full cache")
            return stats

        except Exception as e:
            logger.error(f"❌ Get inventory stats failed: {e}", exc_info=True)
            return {
                "vehicle_count": 0,
                "brands": [],
                "fuel_types": [],
                "last_sync": None,
                "cache_status": "error"
            }

    async def is_cache_healthy(self) -> bool:
        """
        Check if inventory cache is healthy and populated.

        Returns:
            True if cache contains data, False otherwise

        Example:
            if not await service.is_cache_healthy():
                # Trigger immediate sync
                await trigger_immediate_inventory_sync()
        """
        try:
            cached_inventory = self.redis.get(self.cache_key)
            healthy = cached_inventory is not None and len(cached_inventory) > 0

            logger.debug(
                f"✅ Cache health check: {'healthy' if healthy else 'empty'}",
                extra={"cache_key": self.cache_key, "healthy": healthy}
            )

            return healthy

        except Exception as e:
            logger.error(f"❌ Cache health check failed: {e}", exc_info=True)
            return False

    async def _get_full_inventory(self) -> List[Dict[str, Any]]:
        """
        Get full inventory from Redis cache.

        Returns:
            List of all vehicles or empty list if cache empty
        """
        try:
            cached_inventory = self.redis.get(self.cache_key)

            if not cached_inventory:
                logger.warning("⚠️ Full inventory cache empty")
                return []

            vehicles = json.loads(cached_inventory)
            logger.debug(f"✅ Loaded {len(vehicles)} vehicles from cache")
            return vehicles

        except Exception as e:
            logger.error(f"❌ Failed to load full inventory: {e}", exc_info=True)
            return []

    async def _get_by_brand(self, brand: str) -> List[Dict[str, Any]]:
        """
        Get vehicles by brand from brand-specific index.

        Faster than filtering full inventory when only brand filter needed.

        Args:
            brand: Brand name

        Returns:
            List of vehicles for specified brand
        """
        try:
            brand_key = f"seldenrijk:inventory:brand:{brand.lower()}"
            cached_brand = self.redis.get(brand_key)

            if not cached_brand:
                logger.debug(f"⚠️ Brand index not found: {brand}")
                # Fallback to full inventory
                return await self._get_full_inventory()

            vehicles = json.loads(cached_brand)
            logger.debug(f"✅ Loaded {len(vehicles)} vehicles from brand index: {brand}")
            return vehicles

        except Exception as e:
            logger.warning(f"⚠️ Brand index lookup failed: {e}")
            # Fallback to full inventory
            return await self._get_full_inventory()


# Singleton instance
_inventory_service = None


def get_inventory_service() -> InventoryService:
    """Get singleton inventory service instance."""
    global _inventory_service
    if _inventory_service is None:
        _inventory_service = InventoryService()
    return _inventory_service
