"""
Unit tests for hash-based embedding generation.

Tests cover the critical hash-based embedding implementation that uses
SHA-256 + NumPy RandomState to generate deterministic 1536-dimensional vectors.
This approach is intentional per PRD - NO OpenAI dependency, only Anthropic Claude.
"""
import pytest
import numpy as np
from app.services.vector_store import VehicleVectorStore


class TestHashBasedEmbeddings:
    """
    Test suite for hash-based deterministic embeddings.

    Critical tests to ensure:
    1. Embeddings are deterministic (same text → same vector)
    2. Embeddings are 1536 dimensions
    3. Embeddings are normalized (unit length for cosine similarity)
    4. Different text produces different embeddings
    """

    @pytest.mark.asyncio
    async def test_embedding_dimension(self):
        """Test embedding vector is exactly 1536 dimensions."""
        store = VehicleVectorStore()

        text = "Audi Q5 3.0 TDI quattro diesel automaat"
        embedding = await store.generate_embedding(text)

        assert len(embedding) == 1536, f"Expected 1536 dimensions, got {len(embedding)}"

    @pytest.mark.asyncio
    async def test_embedding_deterministic(self):
        """Test same text produces identical embeddings (deterministic)."""
        store = VehicleVectorStore()

        text = "Volkswagen Golf 8 2.0 TDI benzine"

        # Generate embedding twice
        embedding1 = await store.generate_embedding(text)
        embedding2 = await store.generate_embedding(text)

        # Should be identical
        assert embedding1 == embedding2, "Embeddings for same text should be deterministic"

        # Verify numpy arrays are equal
        np.testing.assert_array_almost_equal(
            np.array(embedding1),
            np.array(embedding2),
            decimal=10,
            err_msg="Embeddings should be deterministic"
        )

    @pytest.mark.asyncio
    async def test_embedding_normalized(self):
        """Test embedding is normalized to unit length (for cosine similarity)."""
        store = VehicleVectorStore()

        text = "Mercedes-Benz E-Class diesel"
        embedding = await store.generate_embedding(text)

        # Calculate vector norm (should be 1.0)
        norm = np.linalg.norm(embedding)

        assert abs(norm - 1.0) < 1e-6, f"Expected norm ≈ 1.0, got {norm}"

    @pytest.mark.asyncio
    async def test_different_text_different_embeddings(self):
        """Test different text produces different embeddings."""
        store = VehicleVectorStore()

        text1 = "Audi Q5 diesel"
        text2 = "BMW X5 benzine"

        embedding1 = await store.generate_embedding(text1)
        embedding2 = await store.generate_embedding(text2)

        # Should NOT be identical
        assert embedding1 != embedding2, "Different text should produce different embeddings"

        # Calculate cosine similarity (should be < 1.0)
        cosine_sim = np.dot(embedding1, embedding2)
        assert cosine_sim < 0.99, f"Different text should have cosine similarity < 0.99, got {cosine_sim}"

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        """Test embeddings are case-insensitive (normalized to lowercase)."""
        store = VehicleVectorStore()

        text_lower = "audi q5 diesel"
        text_upper = "AUDI Q5 DIESEL"
        text_mixed = "Audi Q5 Diesel"

        embedding_lower = await store.generate_embedding(text_lower)
        embedding_upper = await store.generate_embedding(text_upper)
        embedding_mixed = await store.generate_embedding(text_mixed)

        # All should be identical
        assert embedding_lower == embedding_upper == embedding_mixed, \
            "Case-insensitive: same text (different case) should produce same embedding"

    @pytest.mark.asyncio
    async def test_whitespace_normalized(self):
        """Test embeddings normalize whitespace (strip leading/trailing)."""
        store = VehicleVectorStore()

        text_normal = "BMW X3"
        text_extra_spaces = "  BMW X3  "

        embedding_normal = await store.generate_embedding(text_normal)
        embedding_spaces = await store.generate_embedding(text_extra_spaces)

        assert embedding_normal == embedding_spaces, \
            "Whitespace normalization: stripped text should produce same embedding"

    @pytest.mark.asyncio
    async def test_empty_string_embedding(self):
        """Test embedding generation handles empty string."""
        store = VehicleVectorStore()

        # Empty string should still generate 1536-dim vector
        embedding = await store.generate_embedding("")

        assert len(embedding) == 1536
        assert abs(np.linalg.norm(embedding) - 1.0) < 1e-6, "Empty string embedding should be normalized"

    @pytest.mark.asyncio
    async def test_hash_consistency_across_instances(self):
        """Test embeddings are consistent across different VectorStore instances."""
        text = "Toyota Corolla Hybrid"

        # Create two separate instances
        store1 = VehicleVectorStore()
        store2 = VehicleVectorStore()

        embedding1 = await store1.generate_embedding(text)
        embedding2 = await store2.generate_embedding(text)

        assert embedding1 == embedding2, \
            "Embeddings should be consistent across VectorStore instances"

    @pytest.mark.asyncio
    async def test_unicode_text_embedding(self):
        """Test embedding generation handles Unicode text correctly."""
        store = VehicleVectorStore()

        text_unicode = "Renault Mégane E-Tech"
        embedding = await store.generate_embedding(text_unicode)

        assert len(embedding) == 1536
        assert abs(np.linalg.norm(embedding) - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_long_text_embedding(self):
        """Test embedding generation handles long text."""
        store = VehicleVectorStore()

        # Very long vehicle description
        text_long = " ".join([
            "Volkswagen Golf 8 2.0 TDI R-Line",
            "panoramadak leder navigatie",
            "climate control xenon LED",
            "parkeersensoren camera adaptive cruise control"
        ] * 10)  # Repeat 10 times

        embedding = await store.generate_embedding(text_long)

        assert len(embedding) == 1536
        assert abs(np.linalg.norm(embedding) - 1.0) < 1e-6


class TestVehicleDescriptionGeneration:
    """Test rich vehicle description generation for embeddings."""

    def test_generate_vehicle_description_full(self):
        """Test description generation with all fields present."""
        store = VehicleVectorStore()

        vehicle = {
            "brand": "Audi",
            "model": "Q5",
            "fuel": "diesel",
            "transmission": "automaat",
            "title": "Audi Q5 3.0 TDI quattro panoramadak leder navigatie"
        }

        description = store._generate_vehicle_description(vehicle)

        assert "Audi" in description
        assert "Q5" in description
        assert "diesel" in description
        assert "automaat" in description
        # Should extract features from title (max 5)
        assert "panoramadak" in description or "leder" in description

    def test_generate_vehicle_description_minimal(self):
        """Test description generation with minimal fields."""
        store = VehicleVectorStore()

        vehicle = {
            "brand": "BMW",
            "model": "X3"
        }

        description = store._generate_vehicle_description(vehicle)

        assert "BMW" in description
        assert "X3" in description

    def test_generate_vehicle_description_features_extracted(self):
        """Test features are correctly extracted from title."""
        store = VehicleVectorStore()

        vehicle = {
            "brand": "Mercedes-Benz",
            "model": "E-Class",
            "fuel": "diesel",
            "transmission": "automaat",
            "title": "Mercedes-Benz E-Class 220d AMG Line panoramadak leder navigatie camera"
        }

        description = store._generate_vehicle_description(vehicle)

        # Should NOT duplicate brand/model/fuel/transmission
        parts = description.split()
        assert parts.count("Mercedes-Benz") == 1
        assert parts.count("diesel") == 1

        # Should include features (max 5 beyond brand/model/fuel/transmission)
        feature_count = sum(1 for p in ["panoramadak", "leder", "navigatie", "camera"] if p in description)
        assert feature_count > 0, "Should extract at least some features from title"
