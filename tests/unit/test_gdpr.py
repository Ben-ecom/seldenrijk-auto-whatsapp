"""
Unit tests for GDPR compliance endpoints.

Tests cover consent management, data export, data deletion,
GDPR status checks, and background task processing.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import json
from datetime import datetime, timedelta

from app.main import app

client = TestClient(app)


class TestConsentManagement:
    """Test suite for consent recording and retrieval."""

    @patch("app.api.gdpr.get_supabase_client")
    def test_record_consent_success(self, mock_supabase):
        """Test successful consent recording."""
        # Mock Supabase response
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": "consent_123", "contact_id": "contact_456"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_456",
            "consent_type": "marketing",
            "granted": True,
            "ip_address": "192.168.1.1"
        }

        response = client.post("/gdpr/consent", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recorded"
        assert data["consent_id"] == "consent_123"
        assert data["contact_id"] == "contact_456"

    @patch("app.api.gdpr.get_supabase_client")
    def test_record_consent_without_ip(self, mock_supabase):
        """Test consent recording without IP address (optional field)."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": "consent_789", "contact_id": "contact_101"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_101",
            "consent_type": "analytics",
            "granted": False
        }

        response = client.post("/gdpr/consent", json=payload)

        assert response.status_code == 201
        assert response.json()["consent_id"] == "consent_789"

    @patch("app.api.gdpr.get_supabase_client")
    def test_record_consent_database_failure(self, mock_supabase):
        """Test consent recording handles database failures."""
        mock_client = Mock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_999",
            "consent_type": "communication",
            "granted": True
        }

        response = client.post("/gdpr/consent", json=payload)

        assert response.status_code == 500
        assert "Failed to record consent" in response.json()["detail"]

    def test_record_consent_invalid_payload(self):
        """Test consent recording rejects invalid payload."""
        payload = {
            "contact_id": "contact_123",
            # Missing required fields: consent_type, granted
        }

        response = client.post("/gdpr/consent", json=payload)

        assert response.status_code == 422  # Validation error


class TestConsentStatus:
    """Test suite for consent status retrieval."""

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_get_consent_status_success(self, mock_supabase, mock_check_delete):
        """Test successful consent status retrieval."""
        # Mock Supabase response with multiple consent records
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [
            {"consent_type": "marketing", "granted": True, "timestamp": "2025-01-15T10:00:00"},
            {"consent_type": "analytics", "granted": False, "timestamp": "2025-01-14T09:00:00"},
            {"consent_type": "marketing", "granted": False, "timestamp": "2025-01-10T08:00:00"},  # Older, should be ignored
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        # Mock deletion check
        mock_check_delete.return_value = True

        response = client.get("/gdpr/consent/contact_123")

        assert response.status_code == 200
        data = response.json()
        assert data["contact_id"] == "contact_123"
        assert data["consents"]["marketing"] is True  # Latest consent
        assert data["consents"]["analytics"] is False
        assert data["data_retention_days"] == 90
        assert data["can_be_deleted"] is True
        assert data["export_available"] is True

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_get_consent_status_no_consents(self, mock_supabase, mock_check_delete):
        """Test consent status with no consent records."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = []  # No consent records
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        mock_check_delete.return_value = True

        response = client.get("/gdpr/consent/contact_456")

        assert response.status_code == 200
        data = response.json()
        assert data["consents"] == {}
        assert data["can_be_deleted"] is True

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_get_consent_status_cannot_delete(self, mock_supabase, mock_check_delete):
        """Test consent status when contact cannot be deleted."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        # Mock deletion check - contact has active conversations
        mock_check_delete.return_value = False

        response = client.get("/gdpr/consent/contact_789")

        assert response.status_code == 200
        assert response.json()["can_be_deleted"] is False

    @patch("app.api.gdpr.get_supabase_client")
    def test_get_consent_status_database_failure(self, mock_supabase):
        """Test consent status handles database failures."""
        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = Exception("DB error")
        mock_supabase.return_value = mock_client

        response = client.get("/gdpr/consent/contact_error")

        assert response.status_code == 500
        assert "Failed to get consent status" in response.json()["detail"]


class TestDataExport:
    """Test suite for data export functionality."""

    @patch("app.api.gdpr.get_supabase_client")
    def test_export_personal_data_success(self, mock_supabase):
        """Test successful data export request."""
        mock_client = Mock()
        mock_result = Mock()
        export_id = "export_abc123"
        mock_result.data = [{"id": export_id}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_123",
            "email": "test@example.com",
            "include_conversations": True,
            "include_metadata": True
        }

        response = client.post("/gdpr/export", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["export_id"] == export_id
        assert data["estimated_time_minutes"] == 5
        assert "expires_at" in data

    @patch("app.api.gdpr.get_supabase_client")
    def test_export_minimal_data(self, mock_supabase):
        """Test data export with minimal options (no conversations/metadata)."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": "export_xyz"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_456",
            "email": "minimal@example.com",
            "include_conversations": False,
            "include_metadata": False
        }

        response = client.post("/gdpr/export", json=payload)

        assert response.status_code == 200
        assert response.json()["export_id"] == "export_xyz"

    @patch("app.api.gdpr.get_supabase_client")
    def test_export_database_failure(self, mock_supabase):
        """Test data export handles database failures."""
        mock_client = Mock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("Insert failed")
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_error",
            "email": "error@example.com"
        }

        response = client.post("/gdpr/export", json=payload)

        assert response.status_code == 500
        assert "Failed to create export job" in response.json()["detail"]

    def test_export_invalid_email(self):
        """Test data export rejects invalid email."""
        payload = {
            "contact_id": "contact_123",
            "email": "not-an-email"  # Invalid email
        }

        response = client.post("/gdpr/export", json=payload)

        assert response.status_code == 422  # Validation error


class TestExportStatus:
    """Test suite for export status checking."""

    @patch("app.api.gdpr.get_supabase_client")
    def test_get_export_status_completed(self, mock_supabase):
        """Test getting status of completed export."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = {
            "id": "export_123",
            "status": "completed",
            "created_at": "2025-01-15T10:00:00",
            "completed_at": "2025-01-15T10:05:00",
            "download_url": "https://storage.example.com/export_123.json",
            "expires_at": "2025-01-22T10:00:00"
        }
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        response = client.get("/gdpr/export/export_123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["download_url"] == "https://storage.example.com/export_123.json"
        assert "completed_at" in data

    @patch("app.api.gdpr.get_supabase_client")
    def test_get_export_status_processing(self, mock_supabase):
        """Test getting status of processing export."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = {
            "id": "export_456",
            "status": "processing",
            "created_at": "2025-01-15T11:00:00",
            "expires_at": "2025-01-22T11:00:00"
        }
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        response = client.get("/gdpr/export/export_456/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "download_url" not in data or data["download_url"] is None

    @patch("app.api.gdpr.get_supabase_client")
    def test_get_export_status_not_found(self, mock_supabase):
        """Test export status for non-existent export."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = None  # Export not found
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        response = client.get("/gdpr/export/export_nonexistent/status")

        assert response.status_code == 404
        assert "Export not found" in response.json()["detail"]

    @patch("app.api.gdpr.get_supabase_client")
    def test_get_export_status_database_failure(self, mock_supabase):
        """Test export status handles database failures."""
        mock_client = Mock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")
        mock_supabase.return_value = mock_client

        response = client.get("/gdpr/export/export_error/status")

        assert response.status_code == 500
        assert "Failed to get export status" in response.json()["detail"]


class TestDataDeletion:
    """Test suite for data deletion functionality."""

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_delete_contact_data_success(self, mock_supabase, mock_check_delete):
        """Test successful contact data deletion."""
        # Mock deletion eligibility check
        mock_check_delete.return_value = True

        # Mock Supabase response
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": "deletion_123"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_123",
            "confirmation": True,
            "reason": "User requested account closure"
        }

        response = client.request("DELETE", "/gdpr/contacts/contact_123", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["deletion_id"] == "deletion_123"
        assert data["contact_id"] == "contact_123"
        assert data["estimated_time_minutes"] == 2

    @patch("app.api.gdpr._check_can_delete")
    def test_delete_contact_no_confirmation(self, mock_check_delete):
        """Test deletion rejected without confirmation."""
        mock_check_delete.return_value = True

        payload = {
            "contact_id": "contact_123",
            "confirmation": False  # Not confirmed
        }

        response = client.request("DELETE", "/gdpr/contacts/contact_123", json=payload)

        assert response.status_code == 400
        assert "Confirmation required" in response.json()["detail"]

    @patch("app.api.gdpr._check_can_delete")
    def test_delete_contact_cannot_delete_active_conversations(self, mock_check_delete):
        """Test deletion rejected for contacts with active conversations."""
        # Contact has active conversations
        mock_check_delete.return_value = False

        payload = {
            "contact_id": "contact_active",
            "confirmation": True
        }

        response = client.request("DELETE", "/gdpr/contacts/contact_active", json=payload)

        assert response.status_code == 409
        assert "Contact cannot be deleted" in response.json()["detail"]
        assert "active conversations" in response.json()["detail"]

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_delete_contact_with_reason(self, mock_supabase, mock_check_delete):
        """Test deletion with optional reason provided."""
        mock_check_delete.return_value = True

        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": "deletion_456"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_456",
            "confirmation": True,
            "reason": "Privacy concerns"
        }

        response = client.request("DELETE", "/gdpr/contacts/contact_456", json=payload)

        assert response.status_code == 200
        assert response.json()["deletion_id"] == "deletion_456"

    @patch("app.api.gdpr._check_can_delete")
    @patch("app.api.gdpr.get_supabase_client")
    def test_delete_contact_database_failure(self, mock_supabase, mock_check_delete):
        """Test deletion handles database failures."""
        mock_check_delete.return_value = True

        mock_client = Mock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        mock_supabase.return_value = mock_client

        payload = {
            "contact_id": "contact_error",
            "confirmation": True
        }

        response = client.request("DELETE", "/gdpr/contacts/contact_error", json=payload)

        assert response.status_code == 500
        assert "Failed to create deletion job" in response.json()["detail"]


class TestBackgroundTasks:
    """Test suite for background task functions."""

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch("app.api.gdpr.get_supabase_client")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_generate_data_export_success(self, mock_supabase, mock_httpx):
        """Test successful data export generation."""
        from app.api.gdpr import _generate_data_export

        # Mock Supabase client
        mock_client = Mock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])

        # Mock storage chain: client.storage.from_("bucket").upload() and .create_signed_url()
        mock_storage_bucket = Mock()
        mock_storage_bucket.upload.return_value = None
        mock_storage_bucket.create_signed_url.return_value = {"signedURL": "https://storage.example.com/export.json"}
        mock_client.storage.from_.return_value = mock_storage_bucket

        mock_supabase.return_value = mock_client

        # Mock HTTP client for Chatwoot API
        mock_http = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"id": "contact_123", "name": "Test User"}
        mock_http.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_http

        # Execute background task
        await _generate_data_export(
            "export_123",
            "contact_123",
            "test@example.com",
            include_conversations=True,
            include_metadata=True
        )

        # Verify Supabase storage upload was called
        mock_client.storage.from_.assert_called()

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch("app.api.gdpr.get_supabase_client")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_generate_data_export_failure(self, mock_supabase, mock_httpx):
        """Test data export generation handles failures."""
        from app.api.gdpr import _generate_data_export

        # Mock Supabase client
        mock_client = Mock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client

        # Mock HTTP client failure
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get.side_effect = Exception("Chatwoot API error")
        mock_httpx.return_value = mock_http

        # Execute background task - should not raise exception
        await _generate_data_export(
            "export_fail",
            "contact_fail",
            "fail@example.com",
            include_conversations=False,
            include_metadata=False
        )

        # Verify status was updated to failed (called twice: processing, then failed)
        assert mock_client.table.return_value.update.return_value.eq.return_value.execute.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch("app.api.gdpr.get_supabase_client")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_execute_data_deletion_success(self, mock_supabase, mock_httpx):
        """Test successful data deletion execution."""
        from app.api.gdpr import _execute_data_deletion

        # Mock Supabase client
        mock_client = Mock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client

        # Mock HTTP client for Chatwoot API
        mock_http = AsyncMock()
        mock_response = AsyncMock()
        mock_http.__aenter__.return_value.patch.return_value = mock_response
        mock_httpx.return_value = mock_http

        # Execute background task
        await _execute_data_deletion("deletion_123", "contact_123")

        # Verify Chatwoot anonymization was called
        mock_http.__aenter__.return_value.patch.assert_called_once()

        # Verify consent records were deleted
        mock_client.table.return_value.delete.return_value.eq.assert_called()

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch("app.api.gdpr.get_supabase_client")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_execute_data_deletion_failure(self, mock_supabase, mock_httpx):
        """Test data deletion handles failures."""
        from app.api.gdpr import _execute_data_deletion

        # Mock Supabase client
        mock_client = Mock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_supabase.return_value = mock_client

        # Mock HTTP client failure
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.patch.side_effect = Exception("Chatwoot API error")
        mock_httpx.return_value = mock_http

        # Execute background task - should not raise exception
        await _execute_data_deletion("deletion_fail", "contact_fail")

        # Verify status was updated to failed
        assert mock_client.table.return_value.update.return_value.eq.return_value.execute.call_count >= 2


class TestDeletionEligibility:
    """Test suite for deletion eligibility checking."""

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_check_can_delete_no_active_conversations(self, mock_httpx):
        """Test contact can be deleted when no active conversations."""
        from app.api.gdpr import _check_can_delete

        # Mock HTTP client - no active conversations
        mock_http = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])  # No conversations - must be AsyncMock
        mock_http.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_http

        result = await _check_can_delete("contact_123")

        assert result is True

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_check_can_delete_with_active_conversations(self, mock_httpx):
        """Test contact cannot be deleted with active conversations."""
        from app.api.gdpr import _check_can_delete

        # Mock HTTP client - active conversations exist
        mock_http = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {"id": "conv_1", "status": "open"},
            {"id": "conv_2", "status": "open"}
        ]
        mock_http.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_http

        result = await _check_can_delete("contact_active")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.api.gdpr.httpx.AsyncClient")
    @patch.dict("os.environ", {
        "CHATWOOT_BASE_URL": "https://chatwoot.example.com",
        "CHATWOOT_API_TOKEN": "test_token",
        "CHATWOOT_ACCOUNT_ID": "1"
    })
    async def test_check_can_delete_api_failure(self, mock_httpx):
        """Test deletion check handles API failures."""
        from app.api.gdpr import _check_can_delete

        # Mock HTTP client failure
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get.side_effect = Exception("API timeout")
        mock_httpx.return_value = mock_http

        result = await _check_can_delete("contact_error")

        # Should return False on error (safe default)
        assert result is False
