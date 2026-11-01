"""Whisper runs in a thread (the server keeps answering) and an unreadable recording is a 400."""
import threading
from unittest.mock import patch

from backend.routers import pronunciation


def _post(client, uid):
    return client.post("/api/pronunciation/analyze",
                       data={"target_text": "Guten Tag", "user_id": str(uid)},
                       files={"audio": ("a.webm", b"\x1a\x45\xdf\xa3data", "audio/webm")})


def test_transcription_runs_off_the_event_loop(client, sample_user, monkeypatch):
    seen = {}

    def fake_transcribe(audio_bytes, audio_format, language):
        seen["thread"] = threading.current_thread().name
        return "Guten Tag"

    monkeypatch.setattr(pronunciation, "PRONUNCIATION_AVAILABLE", True)
    monkeypatch.setattr(pronunciation, "transcribe_audio", fake_transcribe)
    r = _post(client, sample_user["user_id"])
    assert r.status_code == 200
    assert seen["thread"] != threading.main_thread().name and "AnyIO" in seen["thread"]


def test_undecodable_recording_is_400(client, sample_user, monkeypatch):
    monkeypatch.setattr(pronunciation, "PRONUNCIATION_AVAILABLE", True)
    monkeypatch.setattr(pronunciation, "transcribe_audio",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("cannot decode")))
    assert _post(client, sample_user["user_id"]).status_code == 400
