"""Offline practice: answer replay must be idempotent and time-aware."""
from datetime import datetime, timedelta, timezone

from backend.models.exercise import Exercise
from backend.models.sync_event import SyncEvent
from backend.services.exercise_service import create_exercises_from_lesson, grade_answer

LESSON = {
    "exercises": [{
        "type": "fill-in-the-blank",
        "instruction": "Uzupełnij",
        "skill_tag": "Perfekt with haben",
        "feedback": "haben + Partizip II",
        "items": [{"prompt": "Ich ___ Kaffee getrunken.", "answer": "habe"}],
    }]
}


def _seed(db, uid):
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    return db.query(Exercise).filter(Exercise.user_id == uid).first()


# ── Grading parity fixtures ──────────────────────────────────────────────────
# The same cases are asserted in frontend/src/utils/__tests__/offlineQueue.test.js
# so device-side grading cannot silently drift from the server.

def test_grading_rules_used_by_offline_clients():
    assert grade_answer("Ich sehe den Hund", "ich sehe den hund!") is True
    assert grade_answer("habe", "  HABE  ") is True
    assert grade_answer("schön", "schon") is False      # diacritics are significant
    assert grade_answer("żółw", "żółw") is True         # non-ASCII letters survive
    assert grade_answer("habe", "hast") is False
    assert grade_answer("", "anything") is False


# ── Idempotent replay ────────────────────────────────────────────────────────

def test_replaying_same_event_counts_once(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    payload = {
        "user_id": uid, "answer": "habe",
        "client_event_id": "evt-abc-123",
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }

    first = client.post(f"/api/exercises/{ex.id}/answer", json=payload)
    second = client.post(f"/api/exercises/{ex.id}/answer", json=payload)

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    # The review was applied exactly once
    assert second.json()["times_seen"] == 1
    db.expire_all()
    assert db.get(Exercise, ex.id).times_seen == 1
    assert db.query(SyncEvent).filter(SyncEvent.client_event_id == "evt-abc-123").count() == 1


def test_distinct_events_both_count(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    for eid in ("evt-1", "evt-2"):
        r = client.post(f"/api/exercises/{ex.id}/answer", json={
            "user_id": uid, "answer": "habe", "client_event_id": eid,
        })
        assert r.json()["duplicate"] is False
    db.expire_all()
    assert db.get(Exercise, ex.id).times_seen == 2


def test_answer_without_event_id_still_works(client, db, sample_user):
    """Online answers carry no event id and must behave exactly as before."""
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    r = client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "habe"})
    assert r.status_code == 200
    assert r.json()["duplicate"] is False
    assert db.query(SyncEvent).count() == 0


# ── Timestamps ───────────────────────────────────────────────────────────────

def test_offline_answer_schedules_from_when_it_happened(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)

    client.post(f"/api/exercises/{ex.id}/answer", json={
        "user_id": uid, "answer": "habe",
        "client_event_id": "evt-old", "answered_at": two_days_ago.isoformat(),
    })

    db.expire_all()
    updated = db.get(Exercise, ex.id)
    last = updated.last_review_date
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    # Scheduled from the moment of answering, not from the reconnect
    assert last < datetime.now(timezone.utc) - timedelta(days=1)


def test_future_client_clock_is_clamped(client, db, sample_user):
    """A device clock running ahead must not push reviews into the future."""
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    future = datetime.now(timezone.utc) + timedelta(days=30)

    client.post(f"/api/exercises/{ex.id}/answer", json={
        "user_id": uid, "answer": "habe",
        "client_event_id": "evt-future", "answered_at": future.isoformat(),
    })

    db.expire_all()
    last = db.get(Exercise, ex.id).last_review_date
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    assert last <= datetime.now(timezone.utc) + timedelta(minutes=1)


def test_malformed_timestamp_falls_back_to_now(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _seed(db, uid)
    r = client.post(f"/api/exercises/{ex.id}/answer", json={
        "user_id": uid, "answer": "habe",
        "client_event_id": "evt-bad-ts", "answered_at": "not-a-date",
    })
    assert r.status_code == 200
    assert r.json()["duplicate"] is False


# ── Offline pack ─────────────────────────────────────────────────────────────

def test_offline_pack_includes_answers(client, db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid)
    r = client.get(f"/api/exercises/{uid}/offline-pack")
    assert r.status_code == 200
    items = r.json()["exercises"]
    assert len(items) == 1
    # Unlike /practice, the pack deliberately ships answers so the device can grade
    assert items[0]["answer"] == "habe"
    assert items[0]["feedback"] == "haben + Partizip II"
    assert "next_review_date" in items[0]


def test_practice_still_withholds_answers(client, db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid)
    r = client.get(f"/api/exercises/{uid}/practice")
    assert "answer" not in r.json()["exercises"][0]


def test_offline_pack_user_not_found(client):
    assert client.get("/api/exercises/99999/offline-pack").status_code == 404


# ── Flashcards offline ───────────────────────────────────────────────────────
# Flashcards are self-rated, so there is nothing to grade on the device — only
# the review itself has to survive the round trip exactly once.

def _card(db, uid, word="Hund"):
    from backend.models.flashcard import Flashcard
    c = Flashcard(user_id=uid, word=word, translation="dog",
                  language="German", cefr_level="A1")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_flashcard_offline_pack_has_content_and_schedule(client, db, sample_user):
    uid = sample_user["user_id"]
    _card(db, uid)
    r = client.get(f"/api/flashcards/{uid}/offline-pack")
    assert r.status_code == 200
    cards = r.json()["flashcards"]
    assert len(cards) == 1
    assert cards[0]["word"] == "Hund" and cards[0]["translation"] == "dog"
    # audio_path lets the service worker pre-cache pronunciation
    assert "audio_path" in cards[0]
    assert "next_review_date" in cards[0]


def test_flashcard_offline_pack_user_not_found(client):
    assert client.get("/api/flashcards/99999/offline-pack").status_code == 404


def test_replaying_flashcard_review_counts_once(client, db, sample_user):
    from backend.models.flashcard import Flashcard
    uid = sample_user["user_id"]
    card = _card(db, uid)
    payload = {"rating": 3, "client_event_id": "fc-evt-1",
               "reviewed_at": datetime.now(timezone.utc).isoformat()}

    first = client.post(f"/api/flashcards/{card.id}/review", json=payload, params={"user_id": uid})
    second = client.post(f"/api/flashcards/{card.id}/review", json=payload, params={"user_id": uid})

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    db.expire_all()
    # One review applied, not two
    assert db.get(Flashcard, card.id).repetitions == 1
    assert db.query(SyncEvent).filter(SyncEvent.kind == "flashcard_review").count() == 1


def test_flashcard_review_without_event_id_unchanged(client, db, sample_user):
    """Online reviews carry no event id and must behave exactly as before."""
    uid = sample_user["user_id"]
    card = _card(db, uid)
    r = client.post(f"/api/flashcards/{card.id}/review", json={"rating": 3}, params={"user_id": uid})
    assert r.status_code == 200
    assert r.json()["duplicate"] is False
    assert db.query(SyncEvent).count() == 0


def test_flashcard_review_uses_offline_timestamp(client, db, sample_user):
    from backend.models.flashcard import Flashcard
    uid = sample_user["user_id"]
    card = _card(db, uid)
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)

    client.post(f"/api/flashcards/{card.id}/review",
                json={"rating": 3, "client_event_id": "fc-old",
                      "reviewed_at": two_days_ago.isoformat()},
                params={"user_id": uid})

    db.expire_all()
    last = db.get(Flashcard, card.id).last_review_date
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    assert last < datetime.now(timezone.utc) - timedelta(days=1)
