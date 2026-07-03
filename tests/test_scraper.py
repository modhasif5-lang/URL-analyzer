"""
===================================
File: tests/test_scraper.py
===================================

Tests for the scraper module.
Tests text cleaning, word counting, keyword extraction, and title extraction.
"""

from bs4 import BeautifulSoup

from app.scraper import (
    clean_text,
    count_words,
    extract_keywords,
    extract_title,
)


class TestExtractTitle:
    """Tests for extract_title()."""

    def test_extracts_title_tag(self):
        """Extracts text from <title> tag."""
        html = "<html><head><title>Hello World</title></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title(soup) == "Hello World"

    def test_fallback_to_h1(self):
        """Falls back to <h1> when <title> is missing."""
        html = "<html><body><h1>Heading One</h1></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title(soup) == "Heading One"

    def test_no_title_or_h1(self):
        """Returns None when neither <title> nor <h1> exists."""
        html = "<html><body><p>Just a paragraph</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title(soup) is None


class TestCleanText:
    """Tests for clean_text()."""

    def test_removes_scripts(self):
        """Script tags are removed from output."""
        html = "<html><body><script>alert('x');</script><p>Hello</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = clean_text(soup)
        assert "alert" not in text
        assert "Hello" in text

    def test_removes_styles(self):
        """Style tags are removed from output."""
        html = "<html><head><style>body{color:red}</style></head><body><p>World</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = clean_text(soup)
        assert "color" not in text
        assert "World" in text

    def test_collapses_whitespace(self):
        """Multiple whitespace characters are collapsed."""
        html = "<html><body><p>Hello     World</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = clean_text(soup)
        assert "  " not in text


class TestCountWords:
    """Tests for count_words()."""

    def test_counts_words(self):
        """Correctly counts space-separated words."""
        assert count_words("hello world foo bar") == 4

    def test_empty_string(self):
        """Empty string returns zero."""
        assert count_words("") == 0

    def test_single_word(self):
        """Single word returns one."""
        assert count_words("hello") == 1


class TestExtractKeywords:
    """Tests for extract_keywords()."""

    def test_basic_keywords(self):
        """Extracts most frequent non-stopword keywords."""
        text = "python python python java java javascript"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) == 3
        assert keywords[0]["word"] == "python"
        assert keywords[0]["count"] == 3

    def test_filters_stopwords(self):
        """Stopwords are excluded from results."""
        text = "the the the and and or python"
        keywords = extract_keywords(text, top_n=5)
        words = [k["word"] for k in keywords]
        assert "the" not in words
        assert "and" not in words
        assert "python" in words

    def test_ignores_short_words(self):
        """Words shorter than 3 characters are excluded."""
        text = "I am a go to be python developer"
        keywords = extract_keywords(text, top_n=10)
        words = [k["word"] for k in keywords]
        # "I", "am", "a", "go", "to", "be" are all filtered (short or stopwords)
        assert "python" in words
        assert "developer" in words

    def test_top_n_limit(self):
        """Only returns top_n keywords even when more exist."""
        text = " ".join(f"word{i} " * (10 - i) for i in range(20))
        keywords = extract_keywords(text, top_n=5)
        assert len(keywords) == 5

    def test_empty_text(self):
        """Empty text returns empty list."""
        keywords = extract_keywords("", top_n=10)
        assert keywords == []
