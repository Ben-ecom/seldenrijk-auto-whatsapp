"""
Unit tests for database migrations.

Tests:
- SQL syntax validation
- Migration file structure
- Index definitions
"""
import os
import re
from pathlib import Path


class TestMigrations:
    """Test database migration files."""

    def test_migration_files_exist(self):
        """Test that all migration files exist."""
        migrations_dir = Path("migrations")

        expected_files = [
            "003_add_escalations_table.sql",
            "004_add_rag_cache_table.sql",
            "005_add_lead_scores_table.sql"
        ]

        for filename in expected_files:
            filepath = migrations_dir / filename
            assert filepath.exists(), f"Migration file {filename} not found"

    def test_escalations_table_structure(self):
        """Test escalations table has correct structure."""
        migrations_dir = Path("migrations")
        filepath = migrations_dir / "003_add_escalations_table.sql"

        content = filepath.read_text()

        # Check table creation
        assert "CREATE TABLE IF NOT EXISTS escalations" in content

        # Check required columns
        required_columns = [
            "id",
            "escalation_type",
            "urgency",
            "customer_phone",
            "conversation_id",
            "whatsapp_sent",
            "email_sent",
            "chatwoot_assigned"
        ]

        for column in required_columns:
            assert column in content, f"Column {column} not found in escalations table"

        # Check indexes
        assert "idx_escalations_customer_phone" in content
        assert "idx_escalations_status" in content

    def test_rag_cache_table_structure(self):
        """Test RAG cache table has correct structure."""
        migrations_dir = Path("migrations")
        filepath = migrations_dir / "004_add_rag_cache_table.sql"

        content = filepath.read_text()

        # Check table creation
        assert "CREATE TABLE IF NOT EXISTS rag_cache" in content

        # Check required columns
        required_columns = [
            "cache_key",
            "results",
            "expires_at",
            "created_at"
        ]

        for column in required_columns:
            assert column in content, f"Column {column} not found in rag_cache table"

        # Check JSONB type for results
        assert "JSONB" in content

        # Check indexes
        assert "idx_rag_cache_expires_at" in content

    def test_lead_scores_table_structure(self):
        """Test lead scores table has correct structure."""
        migrations_dir = Path("migrations")
        filepath = migrations_dir / "005_add_lead_scores_table.sql"

        content = filepath.read_text()

        # Check table creation
        assert "CREATE TABLE IF NOT EXISTS lead_scores" in content

        # Check required columns
        required_columns = [
            "id",
            "customer_phone",
            "lead_score",
            "lead_quality",
            "score_breakdown",
            "interest_level",
            "urgency",
            "scored_at"
        ]

        for column in required_columns:
            assert column in content, f"Column {column} not found in lead_scores table"

        # Check view creation
        assert "CREATE OR REPLACE VIEW latest_lead_scores" in content

        # Check indexes
        assert "idx_lead_scores_customer_phone" in content
        assert "idx_lead_scores_lead_quality" in content

    def test_migration_syntax_valid(self):
        """Test that migration files have valid SQL syntax."""
        migrations_dir = Path("migrations")

        migration_files = [
            "003_add_escalations_table.sql",
            "004_add_rag_cache_table.sql",
            "005_add_lead_scores_table.sql"
        ]

        for filename in migration_files:
            filepath = migrations_dir / filename
            content = filepath.read_text()

            # Basic SQL validation
            assert "CREATE TABLE" in content or "CREATE OR REPLACE" in content
            assert content.strip().endswith(";") or "CREATE OR REPLACE VIEW" in content

            # Check for common SQL errors
            assert "--" in content or "/*" in content, f"No comments in {filename}"
            assert ";" in content, f"No semicolons found in {filename}"

    def test_migration_headers_present(self):
        """Test that migrations have proper headers."""
        migrations_dir = Path("migrations")

        migration_files = [
            "003_add_escalations_table.sql",
            "004_add_rag_cache_table.sql",
            "005_add_lead_scores_table.sql"
        ]

        for filename in migration_files:
            filepath = migrations_dir / filename
            content = filepath.read_text()

            # Check for header comments
            assert "Migration:" in content or "Purpose:" in content
            assert "Date:" in content or "2025" in content


# Run tests
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
