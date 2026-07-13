"""Tests for /api/pronunciation/* endpoints."""
import json
from datetime import datetime
from io import BytesIO
from unittest.mock import patch

from backend.models.lesson import Lesson

MOCK_TRANSCRIPT = "Hallo, wie geht es dir?"
MOCK_SCORE = {
    "transcribed": "Hallo, wie geht es dir?",
    "target": "Hallo, wie geht es dir?",
    "score": 95.0,
    "word_scores": [
        {"word": "Hallo", "accuracy": 98.0},
        {"word": "wie", "accuracy": 92.0},
    ],
    "incorrect_words": [],
}


def test_analyze_basic(client, sample_user):
    """Pronunciation analysis returns score."""
    uid = sample_user["user_id"]
    with patch("backend.routers.pronunciation.PRONUNCIATION_AVAILABLE", True), \
         patch("backend.routers.pronunciation.transcribe_audio", return_value=MOCK_TRANSCRIPT), \
         patch("backend.routers.pronunciation.score_pronunciation", return_value=MOCK_SCORE):
        r = client.post(
            "/api/pronunciation/analyze",
            data={"target_text": "Hallo, wie geht es dir?", "user_id": str(uid)},
            files={"audio": ("test.webm", BytesIO(b"fake audio data"), "audio/webm")}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "score" in data


def test_analyze_no_user(client):
    """Pronunciation returns 404 for non-existent user."""
    with patch("backend.routers.pronunciation.PRONUNCIATION_AVAILABLE", True), \
         patch("backend.routers.pronunciation.transcribe_audio", return_value="test"), \
         patch("backend.routers.pronunciation.score_pronunciation", return_value=MOCK_SCORE):
        r = client.post(
            "/api/pronunciation/analyze",
            data={"target_text": "test", "user_id": "99999"},
            files={"audio": ("test.webm", BytesIO(b"fake"), "audio/webm")}
        )
        assert r.status_code == 404


def test_analyze_empty_audio(client, sample_user):
    """Pronunciation returns 400 for empty audio."""
    uid = sample_user["user_id"]
    r = client.post(
        "/api/pronunciation/analyze",
        data={"target_text": "test", "user_id": str(uid)},
        files={"audio": ("empty.webm", BytesIO(b""), "audio/webm")}
    )
    assert r.status_code == 400


def test_analyze_service_unavailable(client, sample_user):
    """Pronunciation returns 503 when not available."""
    with patch("backend.routers.pronunciation.PRONUNCIATION_AVAILABLE", False):
        r = client.post(
            "/api/pronunciation/analyze",
            data={"target_text": "test", "user_id": str(sample_user["user_id"])},
            files={"audio": ("test.webm", BytesIO(b"fake"), "audio/webm")}
        )
        assert r.status_code == 503


def test_get_phrases_no_lessons(client, sample_user):
    """Phrases returns defaults when no lessons exist."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/pronunciation/phrases/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert "phrases" in data
    assert len(data["phrases"]) >= 1
    assert data["language"] == "German"


def test_get_phrases_with_lessons(client, sample_user, db):
    """Phrases returns lesson vocabulary."""
    uid = sample_user["user_id"]
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Test Lesson",
        topic="Greetings",
        content=json.dumps({
            "vocabulary": [
                {"word": "Hallo", "translation": "Hello", "example": "Hallo, wie geht es dir?"}
            ]
        }),
        cefr_level="A1",
        language="German",
        is_completed=True,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()

    r = client.get(f"/api/pronunciation/phrases/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["phrases"]) > 0
    assert any("Hallo" in p.get("text", "") for p in data["phrases"])
