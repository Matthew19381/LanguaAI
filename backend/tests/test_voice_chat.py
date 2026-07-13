"""Tests for /api/voice-chat/* endpoints."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models.lesson import Lesson


def test_voice_chat_prompt_basic(client, sample_user):
    """Voice chat prompt generation returns prompt."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/v1/voice-chat/prompt/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert "prompt" in data
    assert data["language"] == "German"
    assert "has_lesson_today" in data


def test_voice_chat_prompt_user_not_found(client):
    """Voice chat prompt returns 404 for non-existent user."""
    r = client.get("/api/v1/voice-chat/prompt/99999")
    assert r.status_code == 404


def test_voice_chat_prompt_with_lesson(client, sample_user, db):
    """Voice chat includes lesson info when available."""
    uid = sample_user["user_id"]
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Today's Lesson",
        topic="Greetings",
        content=json.dumps({
            "vocabulary": [{"word": "Hallo", "translation": "Hello"}],
            "key_grammar": "Present tense",
            "goal": "Learn greetings",
        }),
        cefr_level="A1",
        language="German",
        is_completed=True,
        completed_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()

    r = client.get(f"/api/v1/voice-chat/prompt/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert "prompt" in data
    # Prompt should contain lesson topic
    assert "Greetings" in data["prompt"] or "Hallo" in data["prompt"]


def test_voice_chat_voice_conversation(client):
    """Voice conversation endpoint returns audio response."""
    with patch(
        "backend.routers.voice_chat.generate_text",
        new_callable=AsyncMock,
        return_value="Hallo! Wie geht es dir?"
    ), patch(
        "backend.routers.voice_chat.audio_service"
    ) as mock_audio:
        mock_audio.generate_audio = MagicMock(return_value=b"fake audio")
        r = client.post("/api/v1/voice-chat/conversation/voice", json={
            "user_id": 1,
            "message": "Hello",
            "language": "German"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "text" in data


def test_voice_chat_text_conversation(client):
    """Text-only conversation returns AI response."""
    with patch(
        "backend.routers.voice_chat.generate_text",
        new_callable=AsyncMock,
        return_value="Hallo! Wie geht es dir?"
    ):
        r = client.post("/api/v1/voice-chat/conversation/text", json={
            "user_id": 1,
            "message": "Hello",
            "language": "German"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "text" in data


def test_voice_chat_missing_fields(client):
    """Voice chat returns 400 for missing fields."""
    r = client.post("/api/v1/voice-chat/conversation/voice", json={})
    assert r.status_code == 400
