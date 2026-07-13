"""Tests for /api/audio/* endpoint."""
from unittest.mock import AsyncMock, patch


def test_tts_basic(client, sample_user):
    """TTS generates audio and returns URL."""
    uid = sample_user["user_id"]  # Just to ensure user exists
    with patch(
        "backend.services.audio_service.generate_audio",
        return_value=None,  # File created successfully
    ), patch(
        "os.path.exists", return_value=True
    ):
        r = client.post("/api/audio/tts", json={
            "text": "Hello, how are you?",
            "language": "German"
        })
        assert r.status_code == 200
        data = r.json()
        assert "url" in data
        assert "tts_" in data["url"]


def test_tts_empty_text(client, sample_user):
    """TTS returns 400 for empty text."""
    r = client.post("/api/audio/tts", json={
        "text": "",
        "language": "German"
    })
    assert r.status_code == 400


def test_tts_missing_text(client):
    """TTS returns 422 for missing text."""
    r = client.post("/api/audio/tts", json={"language": "German"})
    assert r.status_code == 422


def test_tts_cached(client, sample_user):
    """TTS returns cached URL on second request."""
    with patch(
        "backend.services.audio_service.generate_audio",
        return_value=None,
    ), patch(
        "os.path.exists", return_value=True
    ):
        # First call
        r1 = client.post("/api/audio/tts", json={
            "text": "Hello",
            "language": "German"
        })
        assert r1.status_code == 200
        url1 = r1.json()["url"]

        # Second call with same text should return same URL (cached)
        r2 = client.post("/api/audio/tts", json={
            "text": "Hello",
            "language": "German"
        })
        assert r2.status_code == 200
        assert r2.json()["url"] == url1


def test_tts_service_error(client):
    """TTS returns 500 when service unavailable."""
    with patch(
        "backend.routers.audio.generate_audio",
        new_callable=AsyncMock,
        side_effect=Exception("Service error")
    ), patch("os.path.exists", return_value=False):
        r = client.post("/api/audio/tts", json={
            "text": "Hello",
            "language": "German"
        })
        assert r.status_code == 500


def test_tts_different_languages(client):
    """TTS works for different languages."""
    for lang in ["German", "English", "Spanish"]:
        with patch(
            "backend.services.audio_service.generate_audio",
            return_value=None,
        ), patch(
            "os.path.exists", return_value=True
        ):
            r = client.post("/api/audio/tts", json={
                "text": "Hello",
                "language": lang
            })
            assert r.status_code == 200
            assert "url" in r.json()
