"""
Integration tests for Supabase VectorStore operations.

Tests cover real database interactions:
- Vehicle upsert (insert/update)
- Semantic search with embeddings
- Vehicle retrieval by external_id
- Soft delete (mark unavailable)

NOTE: These tests require a running Supabase instance with pgvector.
"""
import pytest
from app.services.vector_store import VehicleVectorStore, get_vector_store


@pytest.mark.integration
@pytest.mark.asyncio
class TestVectorStoreIntegration:
    """Integration tests for VectorStore database operations."""

    @pytest.fixture
    async def vector_store(self):
        """Fixture to provide VectorStore instance."""
        return get_vector_store()

    @pytest.fixture
    async def test_vehicle_data(self):
        """Fixture with test vehicle data."""
        return {
            "external_id": "test_wire:12345",
            "brand": "Audi",
            "model": "Q5",
            "title": "Audi Q5 3.0 TDI quattro panoramadak leder",
            "price": 35000,
            "build_year": 2020,
            "mileage": 75000,
            "fuel": "diesel",
            "transmission": "automaat",
            "url": "https://seldenrijk.nl/test-vehicle",
            "image_url": "https://seldenrijk.nl/test-vehicle.jpg"
        }

    async def test_upsert_vehicle(self, vector_store, test_vehicle_data):
        """Test vehicle insert/update operation."""
        # Insert vehicle
        vehicle_id = await vector_store.upsert_vehicle(**test_vehicle_data)

        assert vehicle_id is not None
        assert isinstance(vehicle_id, int)

        # Verify vehicle was inserted
        vehicle = await vector_store.get_vehicle_by_external_id(
            test_vehicle_data["external_id"]
        )

        assert vehicle is not None
        assert vehicle["brand"] == "Audi"
        assert vehicle["model"] == "Q5"
        assert vehicle["price"] == 35000

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_upsert_updates_existing(self, vector_store, test_vehicle_data):
        """Test vehicle update (upsert with existing external_id)."""
        # Insert vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Update price
        test_vehicle_data["price"] = 32000
        vehicle_id = await vector_store.upsert_vehicle(**test_vehicle_data)

        # Verify price was updated
        vehicle = await vector_store.get_vehicle_by_external_id(
            test_vehicle_data["external_id"]
        )

        assert vehicle["price"] == 32000

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_search_vehicles_semantic(self, vector_store, test_vehicle_data):
        """Test semantic search with vector embeddings."""
        # Insert test vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Search for Audi diesel
        results = await vector_store.search_vehicles(
            query="Audi diesel automatic",
            max_price=40000,
            match_count=5
        )

        assert len(results) > 0

        # Verify our test vehicle is in results
        found = any(
            r["external_id"] == test_vehicle_data["external_id"]
            for r in results
        )
        assert found, "Test vehicle should be found in search results"

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_search_with_filters(self, vector_store, test_vehicle_data):
        """Test semantic search with price/fuel/mileage filters."""
        # Insert test vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Search with filters
        results = await vector_store.search_vehicles(
            query="Audi Q5",
            max_price=40000,
            fuel_type="diesel",
            max_mileage=100000,
            min_year=2018
        )

        assert len(results) > 0

        # All results should match filters
        for vehicle in results:
            assert vehicle["price"] <= 40000
            assert vehicle["fuel"] == "diesel"
            assert vehicle["mileage"] <= 100000
            assert vehicle["build_year"] >= 2018

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_get_vehicle_by_external_id(self, vector_store, test_vehicle_data):
        """Test retrieving vehicle by external_id."""
        # Insert vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Retrieve by external_id
        vehicle = await vector_store.get_vehicle_by_external_id(
            test_vehicle_data["external_id"]
        )

        assert vehicle is not None
        assert vehicle["brand"] == test_vehicle_data["brand"]
        assert vehicle["model"] == test_vehicle_data["model"]

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_get_vehicle_not_found(self, vector_store):
        """Test retrieving non-existent vehicle returns None."""
        vehicle = await vector_store.get_vehicle_by_external_id("nonexistent_id")

        assert vehicle is None

    async def test_mark_unavailable(self, vector_store, test_vehicle_data):
        """Test soft delete (mark vehicle unavailable)."""
        # Insert vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Mark unavailable
        success = await vector_store.mark_unavailable(test_vehicle_data["external_id"])

        assert success is True

        # Verify vehicle is marked unavailable
        vehicle = await vector_store.get_vehicle_by_external_id(
            test_vehicle_data["external_id"]
        )

        assert vehicle["available"] is False

    async def test_get_all_vehicles(self, vector_store, test_vehicle_data):
        """Test retrieving all vehicles."""
        # Insert vehicle
        await vector_store.upsert_vehicle(**test_vehicle_data)

        # Get all available vehicles
        vehicles = await vector_store.get_all_vehicles(available_only=True)

        assert len(vehicles) > 0
        assert all(v["available"] for v in vehicles)

        # Clean up
        await vector_store.mark_unavailable(test_vehicle_data["external_id"])

    async def test_search_empty_query(self, vector_store):
        """Test search with empty query returns results."""
        results = await vector_store.search_vehicles(
            query="",
            match_count=5
        )

        # Should still return some results (all vehicles)
        assert isinstance(results, list)

    async def test_search_no_matches(self, vector_store):
        """Test search with impossible filters returns empty list."""
        results = await vector_store.search_vehicles(
            query="Bugatti Veyron",
            max_price=1000,  # Impossibly low price
            match_count=5
        )

        assert len(results) == 0
