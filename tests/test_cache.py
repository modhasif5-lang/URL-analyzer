"""
===================================
File: tests/test_cache.py
===================================

Tests for the Redis cache module.
Uses mocked Redis client to avoid external dependencies.
"""

from unittest.mock import MagicMock, patch

from app.cache import delete_cache, get_cache, is_redis_healthy, save_cache


class TestGetCache:
    """Tests for get_cache()."""

    @patch("app.cache._get_redis_client")
    def test_cache_hit(self, mock_client_factory):
        """Returns parsed JSON on cache hit."""
        mock_client = MagicMock()
        mock_client.get.return_value = '{"title": "Test", "word_count": 42}'
        mock_client_factory.return_value = mock_client

        result = get_cache("url:abc123")
        assert result is not None
        assert result["title"] == "Test"
        assert result["word_count"] == 42

    @patch("app.cache._get_redis_client")
    def test_cache_miss(self, mock_client_factory):
        """Returns None on cache miss."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_client_factory.return_value = mock_client

        result = get_cache("url:nonexistent")
        assert result is None

    @patch("app.cache._get_redis_client")
    def test_cache_redis_error(self, mock_client_factory):
        """Returns None when Redis raises an error."""
        import redis

        mock_client = MagicMock()
        mock_client.get.side_effect = redis.RedisError("Connection refused")
        mock_client_factory.return_value = mock_client

        result = get_cache("url:abc123")
        assert result is None


class TestSaveCache:
    """Tests for save_cache()."""

    @patch("app.cache._get_redis_client")
    def test_save_success(self, mock_client_factory):
        """Returns True on successful save."""
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = save_cache("url:abc123", {"title": "Test"}, ttl=60)
        assert result is True
        mock_client.setex.assert_called_once()

    @patch("app.cache._get_redis_client")
    def test_save_redis_error(self, mock_client_factory):
        """Returns False when Redis raises an error."""
        import redis

        mock_client = MagicMock()
        mock_client.setex.side_effect = redis.RedisError("Connection refused")
        mock_client_factory.return_value = mock_client

        result = save_cache("url:abc123", {"title": "Test"})
        assert result is False


class TestDeleteCache:
    """Tests for delete_cache()."""

    @patch("app.cache._get_redis_client")
    def test_delete_success(self, mock_client_factory):
        """Returns True on successful delete."""
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = delete_cache("url:abc123")
        assert result is True
        mock_client.delete.assert_called_once_with("url:abc123")


class TestRedisHealth:
    """Tests for is_redis_healthy()."""

    @patch("app.cache._get_redis_client")
    def test_healthy(self, mock_client_factory):
        """Returns True when Redis responds to ping."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client_factory.return_value = mock_client

        assert is_redis_healthy() is True

    @patch("app.cache._get_redis_client")
    def test_unhealthy(self, mock_client_factory):
        """Returns False when Redis is unreachable."""
        import redis

        mock_client = MagicMock()
        mock_client.ping.side_effect = redis.RedisError("Unreachable")
        mock_client_factory.return_value = mock_client

        assert is_redis_healthy() is False
