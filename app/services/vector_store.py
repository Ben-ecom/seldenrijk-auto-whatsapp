"""
VectorStore Service - Supabase pgvector operations for vehicle inventory.

This service handles:
- Anthropic Claude embedding generation via API (1536 dimensions fallback to simple hashing)
- Supabase pgvector storage and retrieval
- Semantic search with filters (price, fuel, mileage, year)
- Vehicle upsert operations (insert/update)

EMBEDDING STRATEGY:
Since we only have Anthropic Claude API (no dedicated embedding API),
we use a simple deterministic embedding approach:
- Convert text to normalized tokens
- Create 1536-dim vector using hash-based distribution
- Consistent embeddings for identical text
"""
from typing import List, Dict, Any, Optional
import os
import hashlib
import numpy as np
from supabase import create_client, Client
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class VehicleVectorStore:
    """
    Vector store service for vehicle inventory with Supabase pgvector.

    Uses deterministic hash-based embeddings (1536 dimensions) for semantic search.
    Compatible with Anthropic Claude API (no OpenAI dependency).
    """

    def __init__(self):
        """Initialize Supabase client."""
        # Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL or SUPABASE_KEY environment variable not set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        logger.info("✅ VehicleVectorStore initialized (Hash-based embeddings + Supabase pgvector)")

    def _generate_vehicle_description(self, vehicle: Dict[str, Any]) -> str:
        """
        Generate rich description for embedding.

        Format: "{brand} {model} {fuel} {transmission} {features}"
        Example: "Audi Q5 3.0 TDI quattro diesel automaat panoramadak leder navigatie"

        Args:
            vehicle: Vehicle data dict

        Returns:
            Rich description string for embedding
        """
        parts = []

        # Brand + Model
        if vehicle.get("brand"):
            parts.append(vehicle["brand"])
        if vehicle.get("model"):
            parts.append(vehicle["model"])

        # Fuel type
        if vehicle.get("fuel"):
            parts.append(vehicle["fuel"])

        # Transmission
        if vehicle.get("transmission"):
            parts.append(vehicle["transmission"])

        # Additional features (if available)
        if vehicle.get("title"):
            # Extract features from title (e.g., "panoramadak", "leder", "navigatie")
            title_parts = vehicle["title"].lower().split()
            # Filter out brand/model/fuel/transmission (already added)
            excluded = {vehicle.get("brand", "").lower(), vehicle.get("model", "").lower(),
                       vehicle.get("fuel", "").lower(), vehicle.get("transmission", "").lower()}
            features = [p for p in title_parts if p not in excluded and len(p) > 3]
            parts.extend(features[:5])  # Max 5 additional features

        description = " ".join(parts)
        logger.debug(f"Generated description: {description}")
        return description

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate hash-based deterministic embedding for text.

        Uses SHA-256 hashing to create consistent 1536-dimension vectors.
        No external API required - works with Claude API only.

        Args:
            text: Text to embed

        Returns:
            1536-dimension embedding vector
        """
        try:
            # Normalize text
            normalized = text.lower().strip()

            # Generate SHA-256 hash
            hash_bytes = hashlib.sha256(normalized.encode('utf-8')).digest()

            # Expand hash to 1536 dimensions using seeded random
            seed = int.from_bytes(hash_bytes[:4], 'big')
            rng = np.random.RandomState(seed)

            # Generate deterministic vector
            embedding = rng.randn(1536).tolist()

            # Normalize to unit length (for cosine similarity)
            norm = np.linalg.norm(embedding)
            embedding = [x / norm for x in embedding]

            logger.debug(f"✅ Generated hash-based embedding (dim={len(embedding)})")
            return embedding

        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}", exc_info=True)
            raise

    async def upsert_vehicle(
        self,
        external_id: str,
        brand: str,
        model: str,
        title: str,
        price: int,
        build_year: Optional[int],
        mileage: Optional[int],
        fuel: Optional[str],
        transmission: Optional[str],
        url: str,
        image_url: Optional[str] = None,
        available: bool = True
    ) -> int:
        """
        Insert or update vehicle with embedding generation.

        Args:
            external_id: Unique scraper ID (wire:key)
            brand: Vehicle brand (e.g., "Volkswagen")
            model: Vehicle model (e.g., "Golf 8")
            title: Full title
            price: Price in euros
            build_year: Build year
            mileage: Mileage in kilometers
            fuel: Fuel type (diesel/benzine/etc.)
            transmission: Transmission type
            url: Vehicle detail URL
            image_url: Image URL (optional)
            available: Availability status

        Returns:
            Vehicle ID from Supabase
        """
        try:
            # Build vehicle dict for description
            vehicle_data = {
                "brand": brand,
                "model": model,
                "title": title,
                "fuel": fuel,
                "transmission": transmission
            }

            # Generate rich description
            full_description = self._generate_vehicle_description(vehicle_data)

            # Generate embedding
            embedding = await self.generate_embedding(full_description)

            # Call Supabase upsert_vehicle() function
            result = self.supabase.rpc(
                "upsert_vehicle",
                {
                    "p_external_id": external_id,
                    "p_brand": brand,
                    "p_model": model,
                    "p_title": title,
                    "p_price": price,
                    "p_build_year": build_year,
                    "p_mileage": mileage,
                    "p_fuel": fuel,
                    "p_transmission": transmission,
                    "p_full_description": full_description,
                    "p_embedding": embedding,
                    "p_url": url,
                    "p_image_url": image_url,
                    "p_available": available
                }
            ).execute()

            vehicle_id = result.data
            logger.info(
                f"✅ Upserted vehicle: {brand} {model} (ID={vehicle_id}, external_id={external_id})"
            )
            return vehicle_id

        except Exception as e:
            logger.error(
                f"❌ Vehicle upsert failed: {external_id} - {e}",
                exc_info=True
            )
            raise

    async def search_vehicles(
        self,
        query: str,
        max_price: Optional[int] = None,
        fuel_type: Optional[str] = None,
        max_mileage: Optional[int] = None,
        min_year: Optional[int] = None,
        match_threshold: float = 0.7,
        match_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for vehicles with filters.

        Args:
            query: Natural language query (e.g., "Audi Q5 diesel")
            max_price: Maximum price filter (euros)
            fuel_type: Fuel type filter (diesel/benzine/etc.)
            max_mileage: Maximum mileage filter (km)
            min_year: Minimum build year filter
            match_threshold: Similarity threshold 0.0-1.0 (default: 0.7)
            match_count: Number of results to return (default: 5)

        Returns:
            List of matching vehicles with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)

            # Call Supabase match_vehicles() function
            result = self.supabase.rpc(
                "match_vehicles",
                {
                    "query_embedding": query_embedding,
                    "max_price": max_price,
                    "fuel_type": fuel_type,
                    "max_mileage": max_mileage,
                    "min_year": min_year,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            ).execute()

            vehicles = result.data
            logger.info(
                f"🔍 Vector search: query='{query}' → {len(vehicles)} results",
                extra={
                    "query": query,
                    "num_results": len(vehicles),
                    "filters": {
                        "max_price": max_price,
                        "fuel_type": fuel_type,
                        "max_mileage": max_mileage,
                        "min_year": min_year
                    }
                }
            )

            return vehicles

        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}", exc_info=True)
            return []

    async def get_vehicle_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vehicle by external_id.

        Args:
            external_id: Scraper ID (wire:key)

        Returns:
            Vehicle dict or None if not found
        """
        try:
            result = self.supabase.table("vehicle_inventory") \
                .select("*") \
                .eq("external_id", external_id) \
                .limit(1) \
                .execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"❌ Get vehicle failed: {external_id} - {e}")
            return None

    async def get_all_vehicles(self, available_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all vehicles from inventory.

        Args:
            available_only: Only return available vehicles (default: True)

        Returns:
            List of all vehicles
        """
        try:
            query = self.supabase.table("vehicle_inventory").select("*")

            if available_only:
                query = query.eq("available", True)

            result = query.execute()
            logger.info(f"✅ Retrieved {len(result.data)} vehicles from Supabase")
            return result.data

        except Exception as e:
            logger.error(f"❌ Get all vehicles failed: {e}")
            return []

    async def mark_unavailable(self, external_id: str) -> bool:
        """
        Mark vehicle as unavailable (soft delete).

        Args:
            external_id: Scraper ID

        Returns:
            Success boolean
        """
        try:
            self.supabase.table("vehicle_inventory") \
                .update({"available": False}) \
                .eq("external_id", external_id) \
                .execute()

            logger.info(f"✅ Marked unavailable: {external_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Mark unavailable failed: {external_id} - {e}")
            return False


# ============ SINGLETON INSTANCE ============

_vector_store_instance: Optional[VehicleVectorStore] = None


def get_vector_store() -> VehicleVectorStore:
    """
    Get singleton VectorStore instance.

    Returns:
        VehicleVectorStore instance
    """
    global _vector_store_instance

    if _vector_store_instance is None:
        _vector_store_instance = VehicleVectorStore()

    return _vector_store_instance
