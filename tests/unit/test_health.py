"""
Unit tests for health check endpoints.

Tests cover basic health, detailed health with component status checks,
liveness/readiness/startup probes, Railway-specific health checks, and metrics.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, MagicMock
import os
from datetime import datetime

from app.main import app

client = TestClient(app)


class TestBasicHealthCheck:
    """Test suite for basic health check endpoints."""

    def test_basic_health_check_root(self):
        """Test basic health check at root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "environment" in data
        assert "version" in data

    def test_basic_health_check_health_endpoint(self):
        """Test basic health check at /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "environment" in data
        assert "version" in data

    @patch.dict(os.environ, {"ENVIRONMENT": "development", "GIT_COMMIT_SHA": "abc123def456"})
    def test_basic_health_check_with_env_vars(self):
        """Test basic health check includes environment variables."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["environment"] == "development"
        assert data["version"] == "abc123d"  # First 7 characters

    @patch.dict(os.environ, {}, clear=True)
    def test_basic_health_check_defaults_when_no_env_vars(self):
        """Test basic health check uses defaults when environment variables missing."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["environment"] == "production"  # Default
        assert data["version"] == "5.1.0"  # Default version


class TestDetailedHealthCheck:
    """Test suite for detailed health check with component status."""

    @patch("app.api.health.get_supabase_client")
    @patch("app.api.health.PostgresPool.get_engine")
    @patch("redis.Redis.from_url")
    @patch("app.api.health.psutil.cpu_percent")
    @patch("app.api.health.psutil.virtual_memory")
    @patch("app.api.health.psutil.disk_usage")
    def test_detailed_health_all_healthy(
        self,
        mock_disk,
        mock_memory,
        mock_cpu,
        mock_redis,
        mock_postgres,
        mock_supabase
    ):
        """Test detailed health check when all components are healthy."""
        # Mock Supabase
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        # Mock PostgreSQL
        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.execute.return_value = None
        mock_engine.connect.return_value = mock_conn

        # Mock pool stats
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_postgres.return_value = mock_engine

        # Mock Redis
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {
            "connected_clients": 5,
            "used_memory_human": "1.5M",
            "uptime_in_seconds": 3600
        }
        mock_redis.return_value = mock_redis_client

        # Mock system resources
        mock_cpu.return_value = 45.2
        mock_memory.return_value = Mock(percent=60.5, available=2*1024**3)
        mock_disk.return_value = Mock(percent=50.0, free=100*1024**3)

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert data["components"]["supabase"]["status"] == "healthy"
        assert data["components"]["postgres"]["status"] == "healthy"
        assert data["components"]["redis"]["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "system" in data
        assert data["system"]["cpu_percent"] == 45.2

    @patch("app.api.health.get_supabase_client")
    @patch("app.api.health.PostgresPool.get_engine")
    @patch("redis.Redis.from_url")
    def test_detailed_health_supabase_unhealthy(
        self,
        mock_redis,
        mock_postgres,
        mock_supabase
    ):
        """Test detailed health check when Supabase is unhealthy."""
        # Mock Supabase failure
        mock_supabase.side_effect = Exception("Connection timeout")

        # Mock healthy PostgreSQL and Redis
        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_postgres.return_value = mock_engine

        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {}
        mock_redis.return_value = mock_redis_client

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"  # Overall status degraded
        assert data["components"]["supabase"]["status"] == "unhealthy"
        assert "Connection timeout" in data["components"]["supabase"]["message"]

    @patch("app.api.health.get_supabase_client")
    @patch("app.api.health.PostgresPool.get_engine")
    @patch("redis.Redis.from_url")
    def test_detailed_health_redis_unhealthy(
        self,
        mock_redis,
        mock_postgres,
        mock_supabase
    ):
        """Test detailed health check when Redis is unhealthy (critical)."""
        # Mock healthy Supabase
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        # Mock healthy PostgreSQL
        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_postgres.return_value = mock_engine

        # Mock Redis failure (CRITICAL)
        mock_redis.side_effect = Exception("Redis connection refused")

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"  # Redis is critical
        assert data["components"]["redis"]["status"] == "unhealthy"
        assert "Redis connection failed" in data["components"]["redis"]["message"]

    @patch("app.api.health.get_supabase_client")
    @patch("app.api.health.PostgresPool.get_engine")
    @patch("redis.Redis.from_url")
    @patch("app.api.health.psutil.virtual_memory")
    @patch("app.api.health.psutil.disk_usage")
    def test_detailed_health_high_memory_usage(
        self,
        mock_disk,
        mock_memory,
        mock_redis,
        mock_postgres,
        mock_supabase
    ):
        """Test detailed health check marks system as degraded when memory high."""
        # Mock healthy components
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_postgres.return_value = mock_engine

        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {}
        mock_redis.return_value = mock_redis_client

        # Mock high memory usage (>90%)
        mock_memory.return_value = Mock(percent=95.0, available=100*1024**2)
        mock_disk.return_value = Mock(percent=50.0, free=100*1024**3)

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"  # High memory causes degraded
        assert data["system"]["memory_percent"] == 95.0


class TestLivenessCheck:
    """Test suite for liveness probe endpoint."""

    def test_liveness_check_always_returns_alive(self):
        """Test liveness check always returns alive (even if dependencies down)."""
        response = client.get("/health/liveness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestReadinessCheck:
    """Test suite for readiness probe endpoint."""

    @patch("app.api.health.get_supabase_client")
    @patch("redis.Redis.from_url")
    def test_readiness_check_all_critical_deps_healthy(
        self,
        mock_redis,
        mock_supabase
    ):
        """Test readiness check passes when all critical dependencies healthy."""
        # Mock healthy Redis
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client

        # Mock healthy Supabase
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        response = client.get("/health/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
        assert "message" in data

    @patch("app.api.health.get_supabase_client")
    @patch("redis.Redis.from_url")
    def test_readiness_check_redis_fails(
        self,
        mock_redis,
        mock_supabase
    ):
        """Test readiness check returns 503 when Redis fails (critical)."""
        # Mock Redis failure
        mock_redis.side_effect = Exception("Connection refused")

        # Mock healthy Supabase
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        response = client.get("/health/readiness")

        assert response.status_code == 503
        assert "errors" in response.json()["detail"]
        assert any("Redis" in error for error in response.json()["detail"]["errors"])

    @patch("app.api.health.get_supabase_client")
    @patch("redis.Redis.from_url")
    def test_readiness_check_supabase_fails(
        self,
        mock_redis,
        mock_supabase
    ):
        """Test readiness check returns 503 when Supabase fails (critical)."""
        # Mock healthy Redis
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client

        # Mock Supabase failure
        mock_supabase.side_effect = Exception("Database connection error")

        response = client.get("/health/readiness")

        assert response.status_code == 503
        assert "errors" in response.json()["detail"]
        assert any("Supabase" in error for error in response.json()["detail"]["errors"])

    @patch("app.api.health.get_supabase_client")
    @patch("redis.Redis.from_url")
    def test_readiness_check_both_critical_deps_fail(
        self,
        mock_redis,
        mock_supabase
    ):
        """Test readiness check returns both errors when both critical deps fail."""
        # Mock Redis failure
        mock_redis.side_effect = Exception("Redis down")

        # Mock Supabase failure
        mock_supabase.side_effect = Exception("Supabase down")

        response = client.get("/health/readiness")

        assert response.status_code == 503
        errors = response.json()["detail"]["errors"]
        assert len(errors) == 2
        assert any("Redis" in error for error in errors)
        assert any("Supabase" in error for error in errors)


class TestStartupCheck:
    """Test suite for startup probe endpoint."""

    @patch("redis.Redis.from_url")
    def test_startup_check_redis_responding(self, mock_redis):
        """Test startup check passes when Redis is responding."""
        # Mock healthy Redis
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client

        response = client.get("/health/startup")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "timestamp" in data
        assert "uptime_seconds" in data

    @patch("redis.Redis.from_url")
    def test_startup_check_redis_not_ready(self, mock_redis):
        """Test startup check returns 503 when Redis not ready."""
        # Mock Redis failure
        mock_redis.side_effect = Exception("Connection timeout during startup")

        response = client.get("/health/startup")

        assert response.status_code == 503
        assert "Application still starting up" in response.json()["detail"]


class TestRailwayHealthCheck:
    """Test suite for Railway-specific health check."""

    def test_railway_health_check_minimal_response(self):
        """Test Railway health check returns minimal response for speed."""
        response = client.get("/health/railway")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["service"] == "whatsapp-recruitment-platform"
        assert "version" in data

    @patch.dict(os.environ, {"GIT_COMMIT_SHA": "abcdef123456"})
    def test_railway_health_check_with_commit_sha(self):
        """Test Railway health check includes commit SHA."""
        response = client.get("/health/railway")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "abcdef1"  # First 7 characters


class TestMetricsEndpoint:
    """Test suite for Prometheus metrics endpoint."""

    @patch("app.monitoring.metrics.get_metrics")
    def test_metrics_endpoint_success(self, mock_get_metrics):
        """Test metrics endpoint returns Prometheus format."""
        mock_get_metrics.return_value = "# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 123\n"

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        assert "test_metric" in response.text

    @patch("app.monitoring.metrics.get_metrics")
    def test_metrics_endpoint_error_handling(self, mock_get_metrics):
        """Test metrics endpoint handles errors gracefully."""
        mock_get_metrics.side_effect = Exception("Metrics collection failed")

        response = client.get("/metrics")

        assert response.status_code == 200  # Still returns 200
        assert "Metrics collection error" in response.text


class TestDeploymentInfo:
    """Test suite for Railway deployment information in detailed health."""

    @patch("app.api.health.get_supabase_client")
    @patch("app.api.health.PostgresPool.get_engine")
    @patch("redis.Redis.from_url")
    @patch.dict(os.environ, {
        "RAILWAY_ENVIRONMENT": "production",
        "RAILWAY_PROJECT_ID": "proj-123",
        "RAILWAY_SERVICE_ID": "svc-456",
        "RAILWAY_GIT_COMMIT_SHA": "abcdef123456789",
        "RAILWAY_GIT_BRANCH": "main",
        "RAILWAY_PUBLIC_DOMAIN": "api.example.com"
    })
    def test_detailed_health_includes_railway_deployment_info(
        self,
        mock_redis,
        mock_postgres,
        mock_supabase
    ):
        """Test detailed health includes Railway deployment information."""
        # Mock healthy components
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client

        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_engine.connect.return_value = mock_conn
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        mock_postgres.return_value = mock_engine

        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.info.return_value = {}
        mock_redis.return_value = mock_redis_client

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "deployment" in data
        assert data["deployment"]["environment"] == "production"
        assert data["deployment"]["git_commit_sha"] == "abcdef1"  # Shortened
        assert data["deployment"]["git_branch"] == "main"
