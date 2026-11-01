"""Audit 01.11.2026: flashcards, exercises and the hub (time zones, stale answers, limits)."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.exercise import Exercise
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.skill_attempt import SkillAttempt
from backend.models.topic import Topic, topic_strength
from backend.services import local_day
from backend.services.flashcard_service import advance_relearning_criterion
from backend.services.fsrs_service import apply_fsrs
from backend.services.mastery import skill_mastery
from backend.services.sync_service import parse_occurred_at

CET = timezone(timedelta(hours=1))


@pytest.fixture(autouse=True)
def warsaw(monkeypatch):
    monkeypatch.setattr(local_day, "LOCAL_TZ", CET)


def test_client_time_with_offset_is_stored_as_utc(client, sample_user, db):
    assert parse_occurred_at("2026-11-01T10:00:00+01:00") == datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
    uid = sample_user["user_id"]
    card = Flashcard(user_id=uid, word="das Brot", translation="chleb", language="German", cefr_level="A2")
    db.add(card)
    db.commit()
    answered = (datetime.now(timezone.utc) - timedelta(hours=2)).astimezone(CET)
    r = client.post(f"/api/flashcards/{card.id}/review", params={"user_id": uid},
                    json={"rating": 3, "client_event_id": "e-1", "reviewed_at": answered.isoformat()})
    assert r.status_code == 200
    db.refresh(card)
    assert abs((card.last_review_date - answered.astimezone(timezone.utc).replace(tzinfo=None)).total_seconds()) < 1


def test_offline_answer_older_than_the_last_review_is_rejected(client, sample_user, db):
    uid = sample_user["user_id"]
    ex = Exercise(user_id=uid, language="German", prompt="Ich ___ müde.", answer="bin",
                  last_review_date=datetime.now(timezone.utc) - timedelta(minutes=5), fsrs_state="Review",
                  interval_days=9, next_review_date=datetime.now(timezone.utc) + timedelta(days=9))
    db.add(ex)
    db.commit()
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    r = client.post(f"/api/exercises/{ex.id}/answer",
                    json={"user_id": uid, "answer": "bist", "client_event_id": "old-1", "answered_at": old})
    assert r.status_code == 409
    db.refresh(ex)
    assert ex.fsrs_state == "Review" and ex.interval_days == 9


def test_hub_review_needs_a_client_event_id(client, sample_user, db):
    uid = sample_user["user_id"]
    card = Flashcard(user_id=uid, word="das Haus", translation="dom", language="German", cefr_level="A2")
    db.add(card)
    db.commit()
    state = {"fsrs_state": "Review", "stability": 3, "difficulty": 5, "repetitions": 1, "lapses": 0,
             "interval_days": 3}
    r = client.post(f"/api/flashcards/{card.id}/hub-review", params={"user_id": uid},
                    json={"rating": 3, "state": state})
    assert r.status_code == 422


def test_correct_recall_counts_once_per_local_day():
    # 00:50 and 01:10 CET on the same Polish day (23:50 and 00:10 UTC: two UTC days)
    first = datetime(2026, 10, 31, 23, 50, tzinfo=timezone.utc)
    second = datetime(2026, 11, 1, 0, 10, tzinfo=timezone.utc)
    sessions, _, last = advance_relearning_criterion(rating=3, correct_recall_sessions=0,
                                                     last_recall_date=None, now=first)
    sessions, _, _ = advance_relearning_criterion(rating=3, correct_recall_sessions=sessions,
                                                  last_recall_date=last, now=second)
    assert sessions == 1


def test_skill_mastery_counts_local_days(db, sample_user):
    uid = sample_user["user_id"]
    # 3 UTC days but 2 Polish days: 31.10 23:30 UTC is already 1.11 00:30 CET
    moments = [datetime(2026, 10, 31, 23, 30), datetime(2026, 11, 1, 12, 0), datetime(2026, 11, 2, 12, 0)]
    for i in range(6):
        db.add(SkillAttempt(user_id=uid, language="German", skill_id="G-DAT", source="exercise",
                            correct=True, first_try=True, occurred_at=moments[i % 3] + timedelta(seconds=i)))
    db.commit()
    assert skill_mastery(db, uid, "German")["G-DAT"]["status"] == "w_nauce"


def test_again_while_learning_is_no_lapse():
    r = apply_fsrs(rating=1, difficulty=5, stability=0, retrievability=None, elapsed_days=0, reps=0,
                   lapses=0, current_state="Learning", last_review_date=None)
    assert r.lapses == 0


def test_topic_strength_falls_with_time_and_a_forgotten_topic_is_not_strong():
    now = datetime.now(timezone.utc)
    fresh = Topic(name="t", language="English", difficulty=5, stability=2, repetitions=3, lapses=0,
                  fsrs_state="Review", last_review_date=now, memory_strength=0.95)
    old = Topic(name="t", language="English", difficulty=5, stability=2, repetitions=3, lapses=0,
                fsrs_state="Review", last_review_date=now - timedelta(days=30), memory_strength=0.95)
    forgotten = Topic(name="t", language="English", difficulty=5, stability=0.4, repetitions=3, lapses=1,
                      fsrs_state="Relearning", last_review_date=now, memory_strength=0.95)
    assert topic_strength(old) < topic_strength(fresh)
    assert topic_strength(old) < 0.7  # no longer "strong" (stored 0.95 said it was)
    assert topic_strength(forgotten) < 0.7
    assert topic_strength(SimpleNamespace(memory_strength=0.3)) == 0.3  # never reviewed: stored value


def test_ai_card_without_translation_is_not_saved(client, sample_user, db):
    uid = sample_user["user_id"]
    with patch("backend.routers.flashcards._ai_generate_flashcard", AsyncMock(side_effect=Exception("down"))), \
         patch("backend.routers.flashcards.generate_json", AsyncMock(return_value={"valid": True})):
        r = client.post(f"/api/flashcards/{uid}/add-ai", json={"word": "Brot"})
    assert r.status_code == 503
    assert db.query(Flashcard).filter(Flashcard.user_id == uid).count() == 0


def test_batch_add_keeps_the_gender(client, sample_user, db):
    uid = sample_user["user_id"]
    r = client.post("/api/flashcards/batch-add", json={"user_id": uid, "flashcards": [
        {"word": "Tisch", "translation": "stół", "gender": "der"}]})
    assert r.status_code == 200
    assert db.query(Flashcard).filter(Flashcard.user_id == uid).one().gender == "der"


def test_images_are_behind_the_access_gate(client):
    from backend.config import settings
    original = settings.APP_ACCESS_TOKEN
    settings.APP_ACCESS_TOKEN = "test-access-token-1234567890"
    try:
        client.cookies.clear()
        assert client.get("/images/x.png").status_code == 401
    finally:
        settings.APP_ACCESS_TOKEN = original


def test_flashcard_pages_are_stable_and_mastered_counts_all(client, sample_user, db):
    uid = sample_user["user_id"]
    same = datetime(2026, 10, 1, 12, 0)
    db.add_all([Flashcard(user_id=uid, word=f"w{i}", translation="t", language="German", cefr_level="A2",
                          created_at=same, is_mastered=(i == 0)) for i in range(6)])
    db.commit()
    pages = [client.get(f"/api/flashcards/{uid}", params={"limit": 2, "offset": o}).json() for o in (0, 2, 4)]
    words = [f["word"] for p in pages for f in p["flashcards"]]
    assert sorted(words) == sorted(f"w{i}" for i in range(6))
    assert all(p["mastered_count"] == 1 for p in pages)


def test_dictation_sentences_starting_alike_get_their_own_audio(client, sample_user, tmp_path):
    uid = sample_user["user_id"]
    a = "Ich gehe heute Abend mit meinem Bruder ins Kino."
    b = "Ich gehe heute Abend mit meinem Bruder essen."

    async def tts(text, language, path):
        with open(path, "wb") as f:
            f.write(text.encode())

    gen = AsyncMock(side_effect=tts)
    with patch("backend.routers.quickmode.generate_audio", gen), \
         patch("backend.routers.quickmode.AUDIO_DIR", str(tmp_path)):
        for sentence in (a, b):  # two sessions, each with one sentence
            with patch("backend.routers.quickmode.generate_dictation_sentences",
                       AsyncMock(return_value=[sentence])):
                client.get(f"/api/quickmode/dictation/{uid}", params={"count": 1})
    assert [c.args[0] for c in gen.await_args_list] == [a, b]


def test_interleaving_takes_topics_of_the_learners_language(db, sample_user):
    from backend.models.user import User
    from backend.services.lesson_service import gather_lesson_context
    uid = sample_user["user_id"]
    db.add_all([
        Lesson(user_id=uid, day_number=1, title="t", topic="Dativ", content="{}", cefr_level="A2", language="German"),
        Lesson(user_id=uid, day_number=1, title="t", topic="Present Perfect", content="{}", cefr_level="A2",
               language="English"),
    ])
    db.commit()
    ctx = gather_lesson_context(db, db.query(User).get(uid))
    assert ctx["recent_topics"] == ["Dativ"]
