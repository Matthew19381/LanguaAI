"""Tests for endpoints the frontend called but that never existed (2026-07-23 audit).

BUG-3: POST /api/flashcards/generate-from-errors — previews from test errors.
BUG-4: POST /api/flashcards/batch-add — persist previewed flashcards.

Note: POST /api/stats/{id}/xp (BUG-2) is intentionally NOT re-added — it was
removed in commit d339b59 as an XP injection backdoor; test_stats.py guards
its absence. The dead addXP() calls were removed from the frontend instead.
"""
import json

from backend.models.flashcard import Flashcard
from backend.models.test_result import TestResult


# ── BUG-4: batch add flashcards ──────────────────────────────────────────

def test_batch_add_creates_flashcards(client, sample_user, db):
    uid = sample_user["user_id"]
    payload = {
        "user_id": uid,
        "flashcards": [
            {"word": "der Hund", "translation": "pies", "example": "Der Hund läuft."},
            {"word": "die Katze", "translation": "kot"},
        ],
    }
    r = client.post("/api/flashcards/batch-add", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2
    assert body["skipped"] == 0

    cards = db.query(Flashcard).filter(Flashcard.user_id == uid).all()
    assert {c.word for c in cards} == {"der Hund", "die Katze"}
    assert all(c.language == "German" for c in cards)


def test_batch_add_skips_duplicates(client, sample_user):
    uid = sample_user["user_id"]
    payload = {
        "user_id": uid,
        "flashcards": [{"word": "Hallo", "translation": "cześć"}],
    }
    r1 = client.post("/api/flashcards/batch-add", json=payload)
    assert r1.json()["created"] == 1
    r2 = client.post("/api/flashcards/batch-add", json=payload)
    assert r2.json()["created"] == 0
    assert r2.json()["skipped"] == 1


def test_batch_add_ignores_empty_rows(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post("/api/flashcards/batch-add", json={
        "user_id": uid,
        "flashcards": [{"word": "", "translation": "x"}, {"word": "y", "translation": ""}],
    })
    assert r.status_code == 200
    assert r.json()["created"] == 0


def test_batch_add_unknown_user_404(client):
    r = client.post("/api/flashcards/batch-add", json={
        "user_id": 999999, "flashcards": [{"word": "a", "translation": "b"}],
    })
    assert r.status_code == 404


# ── BUG-3: generate from errors ──────────────────────────────────────────

def _seed_errors(db, user_id: int):
    db.add(TestResult(
        user_id=user_id,
        test_type="daily",
        score=60.0,
        answers="[]",
        errors=json.dumps([
            {"type": "vocabulary", "user_answer": "Hund geht", "correct_answer": "der Hund läuft"},
            {"type": "grammar", "user_answer": "ich habe gegangen", "correct_answer": "ich bin gegangen"},
        ]),
        cefr_level="A1",
        language="German",
    ))
    db.commit()


def test_generate_from_errors_no_errors_returns_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post("/api/flashcards/generate-from-errors", json={"user_id": uid, "count": 5})
    assert r.status_code == 200
    assert r.json()["flashcards"] == []


def test_generate_from_errors_with_errors_calls_ai(client, sample_user, db, monkeypatch):
    uid = sample_user["user_id"]
    _seed_errors(db, uid)

    async def fake_ai(prompt):
        assert "der Hund läuft" in prompt  # correct forms reach the prompt
        return {"flashcards": [
            {"word": "laufen", "translation": "biec", "example": "Der Hund läuft schnell."},
        ]}

    import backend.routers.flashcards as fc_router
    monkeypatch.setattr(fc_router, "_ai_generate_flashcard", fake_ai)

    r = client.post("/api/flashcards/generate-from-errors", json={"user_id": uid, "count": 5})
    assert r.status_code == 200
    cards = r.json()["flashcards"]
    assert len(cards) == 1
    assert cards[0]["word"] == "laufen"


def test_generate_from_errors_ai_failure_returns_empty(client, sample_user, db, monkeypatch):
    uid = sample_user["user_id"]
    _seed_errors(db, uid)

    async def boom(prompt):
        raise RuntimeError("AI down")

    import backend.routers.flashcards as fc_router
    monkeypatch.setattr(fc_router, "_ai_generate_flashcard", boom)

    r = client.post("/api/flashcards/generate-from-errors", json={"user_id": uid, "count": 5})
    assert r.status_code == 200
    assert r.json()["flashcards"] == []
