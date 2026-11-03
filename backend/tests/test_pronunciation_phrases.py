"""Pronunciation sentences (a learner's report 3.11.2026: only 3 sentences, generating
new ones did not work)."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.routers import pronunciation

CONTENT = {
    "vocabulary": [{"word": "heißen", "translation": "nazywać się", "example_sentence": "Ich heiße Anna.",
                    "example_translation": "Nazywam się Anna."},
                   {"word": "wohnen", "translation": "mieszkać", "example_sentence": "Ich wohne in Berlin."}],
    "grammar": {"examples": [{"sentence": "Heute arbeite ich im Büro.", "translation": "Dziś pracuję w biurze. (V2)"}]},
    "output_forcing": {"text": "Ich komme aus Polen. Seit drei Jahren wohne ich hier."},
}


def _lesson(db, uid):
    db.add(Lesson(user_id=uid, day_number=1, title="L", topic="T", content=json.dumps(CONTENT), cefr_level="A2",
                  language="German", created_at=datetime(2026, 9, 1)))   # older than 7 days: still used
    db.add(Flashcard(user_id=uid, word="die Firma", translation="firma", language="German", cefr_level="A2",
                     example_sentence="Meine Firma ist klein.", example_translation="Moja firma jest mała."))
    db.add(Flashcard(user_id=uid, word="heißen", translation="nazywać się", language="German", cefr_level="A2",
                     example_sentence="Ich heiße Anna."))      # repeat of the lesson sentence
    db.commit()


def test_phrases_from_all_lesson_parts_and_flashcards(client, db, sample_user):
    uid = sample_user["user_id"]
    _lesson(db, uid)
    data = client.get(f"/api/pronunciation/phrases/{uid}").json()
    texts = [p["text"] for p in data["phrases"]]
    assert texts == ["Ich heiße Anna.", "Ich wohne in Berlin.", "Heute arbeite ich im Büro.", "Ich komme aus Polen.",
                     "Seit drei Jahren wohne ich hier.", "Meine Firma ist klein."]
    assert data["phrases"][0]["translation"] == "Nazywam się Anna."
    assert data["phrases"][2]["translation"] == "Dziś pracuję w biurze."


def test_generate_returns_checked_sentences(client, sample_user):
    uid = sample_user["user_id"]
    model = AsyncMock(return_value={"phrases": [
        {"text": "Über die Brücke fahren wir morgen früh.", "translation": "Jutro rano jedziemy przez most."},
        {"text": "Oto zdania do ćwiczenia:", "translation": ""},        # Polish line, dropped
        {"text": "Hallo", "translation": "cześć"},                      # too short, dropped
    ]})
    with patch.object(pronunciation, "generate_json", model):
        r = client.post(f"/api/pronunciation/generate/{uid}")
    assert r.status_code == 200
    assert [p["text"] for p in r.json()["phrases"]] == ["Über die Brücke fahren wir morgen früh."]


def test_generate_reports_failure_instead_of_nothing(client, sample_user):
    uid = sample_user["user_id"]
    with patch.object(pronunciation, "generate_json", AsyncMock(side_effect=RuntimeError("no credit"))):
        r = client.post(f"/api/pronunciation/generate/{uid}")
    assert r.status_code == 503 and "Nie udało się" in r.json()["detail"]
    with patch.object(pronunciation, "generate_json", AsyncMock(return_value={"text": "x"})):
        r = client.post(f"/api/pronunciation/generate/{uid}")
    assert r.status_code == 502
