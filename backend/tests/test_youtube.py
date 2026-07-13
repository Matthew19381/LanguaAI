"""Tests for /api/youtube/* endpoint."""
import json
from datetime import datetime
from unittest.mock import patch

from backend.models.lesson import Lesson

MOCK_VIDEOS = [
    {
        "video_id": "abc123",
        "title": "Learn German A1",
        "channel": "German Channel",
        "description": "A1 German lesson",
        "thumbnail": "http://img.com/1.jpg",
        "published_at": "2026-05-01",
        "url": "https://www.youtube.com/watch?v=abc123",
    }
]

MOCK_QUERIES = {
    "queries": ["Learn German A1", "German for beginners"],
    "topic_queries": [0]
}


def test_youtube_search_with_query(client, sample_user):
    """YouTube search with explicit query."""
    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", "fake_key"
    ), patch(
        "backend.routers.youtube._search_youtube",
        return_value=MOCK_VIDEOS,
    ):
        uid = sample_user["user_id"]
        r = client.get(f"/api/youtube/search?user_id={uid}&query=German%20A1")
        assert r.status_code == 200
        data = r.json()
        assert "videos" in data
        assert len(data["videos"]) > 0


def test_youtube_search_no_query(client, sample_user, db):
    """YouTube search generates queries when no query provided."""
    uid = sample_user["user_id"]
    # Create a lesson for topic context
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Test Lesson",
        topic="Greetings",
        content=json.dumps({"vocabulary": []}),
        cefr_level="A1",
        language="German",
        is_completed=True,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()

    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", "fake_key"
    ), patch(
        "backend.routers.youtube._suggest_queries",
        return_value=(["query1", "query2"], [0])
    ), patch(
        "backend.routers.youtube._search_youtube",
        return_value=MOCK_VIDEOS,
    ):
        r = client.get(f"/api/youtube/search?user_id={uid}")
        assert r.status_code == 200
        data = r.json()
        assert "videos" in data
        assert data.get("suggested") is True


def test_youtube_user_not_found(client):
    """YouTube returns 404 for non-existent user."""
    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", "fake_key"
    ):
        r = client.get("/api/youtube/search?user_id=99999")
        assert r.status_code == 404


def test_youtube_no_api_key(client, sample_user):
    """YouTube returns 503 when API key is missing."""
    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", None
    ):
        uid = sample_user["user_id"]
        r = client.get(f"/api/youtube/search?user_id={uid}")
        assert r.status_code == 503


def test_youtube_video_structure(client, sample_user):
    """Each video has all required fields."""
    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", "fake_key"
    ), patch(
        "backend.routers.youtube._search_youtube",
        return_value=MOCK_VIDEOS,
    ):
        uid = sample_user["user_id"]
        r = client.get(f"/api/youtube/search?user_id={uid}&query=test")
        assert r.status_code == 200
        video = r.json()["videos"][0]
        assert "video_id" in video
        assert "title" in video
        assert "url" in video
        assert "thumbnail" in video


def test_youtube_include_polish(client, sample_user):
    """YouTube supports Polish query suggestions."""
    with patch(
        "backend.routers.youtube.settings.YOUTUBE_API_KEY", "fake_key"
    ), patch(
        "backend.routers.youtube._suggest_queries",
        return_value=(["query1", "query2"], [])
    ), patch(
        "backend.routers.youtube._search_youtube",
        return_value=MOCK_VIDEOS,
    ):
        uid = sample_user["user_id"]
        r = client.get(f"/api/youtube/search?user_id={uid}&include_polish=true")
        assert r.status_code == 200
