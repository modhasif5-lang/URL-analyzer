"""
===================================
File: tests/test_tasks.py
===================================

Tests for Celery tasks.
Uses mocked scraper and cache to test task orchestration logic.
"""

from unittest.mock import patch

from app.tasks import analyze_url


class TestAnalyzeUrlTask:
    """Tests for the analyze_url Celery task."""

    @patch("app.tasks.save_cache", return_value=True)
    @patch("app.tasks.analyze_page")
    def test_successful_analysis(self, mock_analyze, mock_save):
        """Task returns analysis result and saves to cache."""
        mock_analyze.return_value = {
            "title": "Example Domain",
            "response_time_seconds": 0.35,
            "word_count": 120,
            "top_keywords": [{"word": "example", "count": 5}],
        }

        result = analyze_url("https://example.com")

        assert result["title"] == "Example Domain"
        assert result["url"] == "https://example.com"
        assert result["cache_hit"] is False
        assert "analyzed_at" in result
        mock_save.assert_called_once()

    @patch("app.tasks.save_cache", return_value=True)
    @patch("app.tasks.analyze_page")
    def test_result_contains_metadata(self, mock_analyze, mock_save):
        """Task enriches result with url, cache_hit, and analyzed_at."""
        mock_analyze.return_value = {
            "title": "Test Page",
            "response_time_seconds": 0.1,
            "word_count": 10,
            "top_keywords": [],
        }

        result = analyze_url("https://test.com")

        assert result["url"] == "https://test.com"
        assert result["cache_hit"] is False
        assert result["analyzed_at"] is not None

    @patch("app.tasks.save_cache", return_value=True)
    @patch("app.tasks.analyze_page")
    def test_cache_is_saved(self, mock_analyze, mock_save):
        """Task stores results in Redis cache."""
        mock_analyze.return_value = {
            "title": "Cached Page",
            "response_time_seconds": 0.2,
            "word_count": 50,
            "top_keywords": [],
        }

        analyze_url("https://cached.com")

        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert "url:cached" not in call_args[0][0]  # key is a hash, not raw URL
        assert call_args[0][1]["title"] == "Cached Page"
