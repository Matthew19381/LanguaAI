"""Tests for /api/news/* endpoint."""
from unittest.mock import AsyncMock, patch

MOCK_ARTICLES = [
    {
        "title": "Proste wiadomości",
        "original_title": "Simple News",
        "summary": "To jest uproszczone podsumowanie artykułu dla poziomu A1.",
        "original_text": "This is the original English text.",
        "vocabulary": [
            {"word": "prosty", "translation": "simple", "cefr": "A1"},
            {"word": "wiadomość", "translation": "news", "cefr": "A1"},
        ],
        "comprehension_questions": [
            {
                "question": "O czym jest ten tekst?",
                "options": ["O sporcie", "O wiadomościach", "O pogodzie"],
                "correct": "O wiadomościach",
            }
        ],
        "source": "Test Source",
        "link": "http://example.com/article1",
        "published": "2026-05-07",
    }
]


def test_news_basic(client, sample_user):
    """News endpoint returns articles for the user."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.news.get_news_for_user",
        new=AsyncMock(return_value=MOCK_ARTICLES),
    ):
        r = client.get(f"/api/news/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["language"] == "German"
    assert data["cefr_level"] == "A1"
    assert len(data["articles"]) == 1
    assert data["cached"] is False


def test_news_user_not_found(client):
    """News returns 404 for non-existent user."""
    r = client.get("/api/news/99999")
    assert r.status_code == 404


def test_news_returns_cached(client, sample_user):
    """News returns cached result on second call."""
    uid = sample_user["user_id"]

    import backend.routers.news as news_module

    # Clear cache before test
    news_module._news_cache.clear()

    cache_key = (uid, "German")
    fixed_time = 1000.0

    with patch(
        "backend.services.news_service.get_news_for_user",
        new=AsyncMock(return_value=MOCK_ARTICLES),
    ), patch(
        "time.time",
        return_value=fixed_time,
    ):
        # First call - not cached
        r1 = client.get(f"/api/news/{uid}")
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["cached"] is False

        # Verify cache was set
        assert cache_key in news_module._news_cache

        # Second call - should be cached (within 6 hour TTL)
        r2 = client.get(f"/api/news/{uid}")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["cached"] is True


def test_news_with_limit(client, sample_user):
    """News respects the limit parameter."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.news.get_news_for_user",
        new=AsyncMock(return_value=MOCK_ARTICLES),
    ):
        r = client.get(f"/api/news/{uid}?limit=1")
        assert r.status_code == 200


def test_news_article_structure(client, sample_user):
    """Each article has all required fields."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.news.get_news_for_user",
        new=AsyncMock(return_value=MOCK_ARTICLES),
    ):
        r = client.get(f"/api/news/{uid}")
        assert r.status_code == 200
        data = r.json()
        article = data["articles"][0]
        assert "title" in article
        assert "summary" in article
        assert "vocabulary" in article
        assert "comprehension_questions" in article
        assert "source" in article


def test_news_ai_service_error(client, sample_user):
    """News returns 500 when service fails."""
    uid = sample_user["user_id"]
    import backend.routers.news as news_router
    # Clear cache to prevent returning cached data from previous tests
    news_router._news_cache.clear()

    mock_service = AsyncMock(side_effect=Exception("AI service error"))
    news_router.get_news_for_user = mock_service
    try:
        r = client.get(f"/api/news/{uid}")
        assert r.status_code == 500
    finally:
        import backend.services.news_service as news_svc
        news_router.get_news_for_user = news_svc.get_news_for_user
