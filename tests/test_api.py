"""
===================================
File: tests/test_api.py
===================================

Tests for the FastAPI API endpoints.
Uses TestClient for synchronous endpoint testing and mocks for
external dependencies (Redis, Celery).
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    @patch("app.main.is_redis_healthy", return_value=True)
    @patch("app.main._check_celery_health")
    def test_health_all_healthy(self, mock_celery, mock_redis, client):
        """Health endpoint returns healthy when all services are up."""
        from app.schemas import ServiceHealth

        mock_celery.return_value = ServiceHealth(
            status="healthy", detail="1 worker(s) active."
        )
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["api"]["status"] == "healthy"
        assert data["redis"]["status"] == "healthy"
        assert data["celery"]["status"] == "healthy"

    @patch("app.main.is_redis_healthy", return_value=False)
    @patch("app.main._check_celery_health")
    def test_health_redis_unhealthy(self, mock_celery, mock_redis, client):
        """Health endpoint reports unhealthy Redis."""
        from app.schemas import ServiceHealth

        mock_celery.return_value = ServiceHealth(
            status="healthy", detail="1 worker(s) active."
        )
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["redis"]["status"] == "unhealthy"


class TestAnalyzeEndpoint:
    """Tests for POST /analyze."""

    @patch("app.main.get_cache", return_value=None)
    @patch("app.main.analyze_url")
    def test_analyze_submits_task(self, mock_task, mock_cache, client):
        """New URL submission creates a Celery task."""
        mock_async_result = MagicMock()
        mock_async_result.id = "test-task-id-123"
        mock_task.delay.return_value = mock_async_result

        response = client.post(
            "/analyze", json={"url": "https://example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id-123"
        assert data["cache_hit"] is False

    @patch("app.main.get_cache")
    def test_analyze_returns_cached(self, mock_cache, client):
        """Cached URL returns result with cache_hit=True."""
        mock_cache.return_value = {
            "url": "https://example.com",
            "title": "Example",
            "word_count": 100,
            "response_time_seconds": 0.5,
            "top_keywords": [],
            "analyzed_at": "2026-01-01T00:00:00",
        }
        response = client.post(
            "/analyze", json={"url": "https://example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is True
        assert data["result"]["title"] == "Example"

    def test_analyze_invalid_url(self, client):
        """Invalid URL returns 422 validation error."""
        response = client.post("/analyze", json={"url": "not-a-url"})
        assert response.status_code == 422


class TestStatusEndpoint:
    """Tests for GET /status/{task_id}."""

    @patch("app.main.AsyncResult")
    def test_status_pending(self, mock_async, client):
        """Returns PENDING status for a new task."""
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_async.return_value = mock_result

        response = client.get("/status/some-task-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"

    @patch("app.main.AsyncResult")
    def test_status_success(self, mock_async, client):
        """Returns SUCCESS status when task completes."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_async.return_value = mock_result

        response = client.get("/status/some-task-id")
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"


class TestResultEndpoint:
    """Tests for GET /result/{task_id}."""

    @patch("app.main.AsyncResult")
    def test_result_success(self, mock_async, client):
        """Returns full result when task has completed successfully."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.result = {
            "url": "https://example.com",
            "title": "Example Domain",
            "response_time_seconds": 0.42,
            "word_count": 50,
            "top_keywords": [{"word": "example", "count": 5}],
            "cache_hit": False,
            "analyzed_at": "2026-01-01T00:00:00",
        }
        mock_async.return_value = mock_result

        response = client.get("/result/some-task-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"]["title"] == "Example Domain"

    @patch("app.main.AsyncResult")
    def test_result_pending(self, mock_async, client):
        """Returns pending message when task not yet complete."""
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_async.return_value = mock_result

        response = client.get("/result/some-task-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["error"] is not None

    @patch("app.main.AsyncResult")
    def test_result_failure(self, mock_async, client):
        """Returns error message when task has failed."""
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_result.result = Exception("Something went wrong")
        mock_async.return_value = mock_result

        response = client.get("/result/some-task-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert "Something went wrong" in data["error"]
