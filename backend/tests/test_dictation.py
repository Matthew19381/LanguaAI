"""SCI-6: unit + endpoint tests for the dictation activity (Nation & Newton 2009)."""
from unittest.mock import AsyncMock, patch

from backend.services.dictation_service import diff_transcription

# ── diff_transcription ───────────────────────────────────────────────────────

def test_perfect_transcription():
    out = diff_transcription("Ich trinke Kaffee", "ich trinke kaffee")
    assert out["accuracy"] == 100.0
    assert all(w["status"] == "correct" for w in out["words"])


def test_punctuation_and_case_ignored():
    out = diff_transcription("Das Wetter ist schön!", "das wetter ist schön")
    assert out["accuracy"] == 100.0


def test_wrong_word_detected():
    out = diff_transcription("Ich trinke Kaffee", "Ich trinke Tee")
    assert out["correct_words"] == 2
    assert out["total_words"] == 3
    statuses = {w["status"] for w in out["words"]}
    assert "wrong" in statuses


def test_missing_word_detected():
    out = diff_transcription("Wir gehen ins Kino", "Wir gehen Kino")
    assert any(w["status"] == "missing" and w["reference"] == "ins" for w in out["words"])


def test_extra_word_detected():
    out = diff_transcription("Wir gehen Kino", "Wir gehen ins Kino")
    assert any(w["status"] == "extra" and w["typed"] == "ins" for w in out["words"])


def test_empty_reference_is_zero_accuracy():
    assert diff_transcription("", "anything")["accuracy"] == 0.0


# ── GET /api/quickmode/dictation/{user_id} ───────────────────────────────────

def test_dictation_endpoint_returns_items(client, sample_user):
    uid = sample_user["user_id"]
    with patch("backend.routers.quickmode.generate_dictation_sentences",
               AsyncMock(return_value=["Ich lerne Deutsch.", "Das ist gut."])), \
         patch("backend.routers.quickmode.generate_audio", AsyncMock(return_value="ok")), \
         patch("backend.routers.quickmode.os.path.exists", return_value=False):
        r = client.get(f"/api/quickmode/dictation/{uid}", params={"count": 2})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert items[0]["sentence"] == "Ich lerne Deutsch."
    assert items[0]["audio_path"].startswith("/audio/")


def test_dictation_endpoint_degrades_without_audio(client, sample_user):
    uid = sample_user["user_id"]
    with patch("backend.routers.quickmode.generate_dictation_sentences",
               AsyncMock(return_value=["Ein Satz."])), \
         patch("backend.routers.quickmode.generate_audio",
               AsyncMock(side_effect=Exception("tts down"))), \
         patch("backend.routers.quickmode.os.path.exists", return_value=False):
        r = client.get(f"/api/quickmode/dictation/{uid}")
    assert r.status_code == 200
    assert r.json()["items"][0]["audio_path"] is None


def test_dictation_endpoint_user_not_found(client):
    r = client.get("/api/quickmode/dictation/99999")
    assert r.status_code == 404


# ── POST /api/quickmode/dictation/check ──────────────────────────────────────

def test_check_endpoint(client):
    r = client.post("/api/quickmode/dictation/check",
                    json={"reference": "Ich trinke Kaffee", "typed": "Ich trinke Tee"})
    assert r.status_code == 200
    assert r.json()["total_words"] == 3
    assert r.json()["correct_words"] == 2
