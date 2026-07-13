from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.news_service import fetch_articles, get_news_for_user, simplify_article


class MockEntry:
    """Simple mock that behaves like a feedparser entry."""
    def __init__(self, title, summary, link):
        self._title = title
        self._summary = summary
        self._link = link

    def get(self, key, default=None):
        d = {
            "title": self._title,
            "summary": self._summary,
            "link": self._link,
        }
        if key == "description":
            return self._summary
        return d.get(key, default)


class TestFetchArticles:
    def test_fetch_articles_success(self):
        entry1 = MockEntry("Test Article 1", "This is a test article about German.", "http://example.com/1")
        entry2 = MockEntry("Test Article 2", "Another test article.", "http://example.com/2")

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]
        mock_feed.feed = MagicMock(links=[{"rel": "alternate", "href": "http://rss.source.com"}])
        mock_feed.bozo = False

        with patch("backend.services.news_service.feedparser.parse", return_value=mock_feed):
            result = fetch_articles("German", limit=2)

            assert len(result) == 2
            assert result[0]["title"] == "Test Article 1"
            assert result[0]["link"] == "http://example.com/1"
            assert "summary" in result[0]

    def test_fetch_articles_respects_limit(self):
        entries = [
            MockEntry(f"Article {i}", "Test", f"http://example.com/{i}")
            for i in range(10)
        ]

        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_feed.feed = MagicMock(links=[])
        mock_feed.bozo = False

        with patch("backend.services.news_service.feedparser.parse", return_value=mock_feed):
            result = fetch_articles("German", limit=3)
            assert len(result) == 3

    def test_fetch_articles_skips_empty_title(self):
        entry1 = MockEntry("", "Has content", "http://example.com/1")
        entry2 = MockEntry("Real Article", "Has content", "http://example.com/2")

        # Create separate mocks for each feed URL
        mock_feed_with_entries = MagicMock()
        mock_feed_with_entries.entries = [entry1, entry2]
        mock_feed_with_entries.feed = MagicMock(links=[])
        mock_feed_with_entries.bozo = False

        mock_feed_empty = MagicMock()
        mock_feed_empty.entries = []
        mock_feed_empty.feed = MagicMock(links=[])
        mock_feed_empty.bozo = False

        # Return feeds with entries first, then empty feeds
        with patch("backend.services.news_service.feedparser.parse", side_effect=[mock_feed_with_entries] + [mock_feed_empty] * 5):
            result = fetch_articles("German", limit=5)
            # entry1 (empty title) skipped, entry2 added once
            assert len(result) == 1
            assert result[0]["title"] == "Real Article"

    def test_fetch_articles_bozo_feed(self):
        """Test handling of malformed RSS feed."""
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Bad feed")

        with patch("backend.services.news_service.feedparser.parse", return_value=mock_feed):
            result = fetch_articles("German", limit=5)
            assert result == []

    def test_fetch_articles_feed_exception(self):
        with patch("backend.services.news_service.feedparser.parse", side_effect=Exception("Network error")):
            result = fetch_articles("German", limit=5)
            assert result == []

    def test_fetch_articles_missing_summary(self):
        entry = MockEntry("Test", "", "http://example.com/1")

        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_feed.feed = MagicMock(links=[])
        mock_feed.bozo = False

        with patch("backend.services.news_service.feedparser.parse", return_value=mock_feed):
            result = fetch_articles("German", limit=1)
            assert len(result) == 0  # Empty summary should be skipped


class TestSimplifyArticle:
    @pytest.mark.asyncio
    async def test_simplify_success(self):
        article = {
            "title": "Complex Article",
            "summary": "A very complex German text.",
            "link": "http://example.com/1"
        }
        simplified = {
            "title": "Simple Article",
            "simplified_text": "A simple German text for A1 level.",
            "vocabulary": [{"word": "Text", "translation": "Tekst"}],
            "comprehension_questions": [{"question": "What?", "answer": "Something"}]
        }

        with patch("backend.services.news_service.generate_json", AsyncMock(return_value=simplified)):
            result = await simplify_article(article, "A1", "Polish", "German")
            assert result["title"] == "Simple Article"
            assert "simplified_text" in result

    @pytest.mark.asyncio
    async def test_simplify_error_fallback(self):
        article = {
            "title": "Test Article",
            "summary": "Some text.",
            "link": "http://example.com/1"
        }

        with patch("backend.services.news_service.generate_json", AsyncMock(side_effect=Exception("API Error"))):
            result = await simplify_article(article, "B1", "Polish", "German")
            assert result["title"] == "Test Article"
            assert result["simplified_text"] == "Some text."

    @pytest.mark.asyncio
    async def test_simplify_preserves_original_link(self):
        article = {
            "title": "Test",
            "summary": "Text.",
            "link": "http://example.com/test"
        }

        simplified = {
            "title": "Simplified",
            "simplified_text": "Simple text.",
            "vocabulary": [],
            "comprehension_questions": []
        }

        with patch("backend.services.news_service.generate_json", AsyncMock(return_value=simplified)):
            result = await simplify_article(article, "A1", "Polish", "German")
            assert result["original_link"] == "http://example.com/test"


class TestGetNewsForUser:
    @pytest.mark.asyncio
    async def test_get_news_success(self):
        mock_articles = [
            {"title": "Article 1", "summary": "Summary 1", "link": "http://example.com/1"}
        ]

        with patch("backend.services.news_service.fetch_articles", return_value=mock_articles):
            with patch("backend.services.news_service.simplify_article", AsyncMock(return_value={
                "title": "Simplified 1",
                "simplified_text": "Simple text.",
                "vocabulary": [],
                "comprehension_questions": []
            })):
                result = await get_news_for_user("German", "A1", "Polish", limit=1)
                assert len(result) == 1
                assert "simplified_text" in result[0]

    @pytest.mark.asyncio
    async def test_get_news_empty_feed(self):
        with patch("backend.services.news_service.fetch_articles", return_value=[]):
            result = await get_news_for_user("German", "A1", "Polish", limit=1)
            assert isinstance(result, list)
