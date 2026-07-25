"""Offline lesson completion — idempotent replay + streak-correct timing.

Same guarantees as the exercise/flashcard offline pattern, applied to the
one-shot "complete lesson" action (+25 XP, streak, achievements).
"""
import json
from datetime import datetime, timedelta, timezone

from backend.models.lesson import Lesson
from backend.models.sync_event import SyncEvent


def _create_lesson(db, user_id, day=1):
    lesson = Lesson(
        user_id=user_id,
        day_number=day,
        title="Test Lesson",
        topic="Test Topic",
        content=json.dumps({"vocabulary": []}),
        cefr_level="A1",
        language="German",
        is_completed=False,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def test_replay_is_idempotent(client, sample_user, db):
    """Replaying the same queued completion must not award XP twice."""
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)
    xp_before = client.get(f"/api/stats/{uid}").json()["user"]["total_xp"]

    payload = {
        "user_id": uid,
        "client_event_id": "evt-lesson-1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    r1 = client.post(f"/api/lessons/{lesson.id}/complete", json=payload)
    assert r1.status_code == 200
    assert r1.json()["xp_awarded"] == 25
    assert r1.json()["is_completed"] is True

    # Same client_event_id replayed (retry, reinstall, two tabs)
    r2 = client.post(f"/api/lessons/{lesson.id}/complete", json=payload)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True
    assert r2.json()["xp_awarded"] == 0

    xp_after = client.get(f"/api/stats/{uid}").json()["user"]["total_xp"]
    assert xp_after == xp_before + 25  # awarded exactly once


def test_completed_at_pins_to_device_day(client, sample_user, db):
    """A lesson finished offline yesterday must record yesterday, not today."""
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    client.post(f"/api/lessons/{lesson.id}/complete", json={
        "user_id": uid,
        "client_event_id": "evt-lesson-2",
        "completed_at": yesterday.isoformat(),
    })

    db.expire_all()
    stored = db.query(Lesson).filter(Lesson.id == lesson.id).first()
    assert stored.completed_at.date() == yesterday.date()


def test_future_timestamp_is_clamped(client, sample_user, db):
    """A device clock running ahead must not push completion into the future."""
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)
    future = datetime.now(timezone.utc) + timedelta(days=3)

    client.post(f"/api/lessons/{lesson.id}/complete", json={
        "user_id": uid,
        "client_event_id": "evt-lesson-3",
        "completed_at": future.isoformat(),
    })

    db.expire_all()
    stored = db.query(Lesson).filter(Lesson.id == lesson.id).first()
    # Compare naive vs aware safely by date; stored must be today, not +3 days
    assert stored.completed_at.date() <= datetime.now(timezone.utc).date()


def test_online_completion_without_event_records_no_ledger(client, sample_user, db):
    """Backward compat: an online complete with no client_event_id behaves
    exactly as before and writes no idempotency row."""
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)

    r = client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid})
    assert r.status_code == 200
    assert r.json()["xp_awarded"] == 25
    assert "duplicate" not in r.json()

    events = db.query(SyncEvent).filter(SyncEvent.kind == "lesson_complete").all()
    assert events == []


def test_replay_records_ledger_entry(client, sample_user, db):
    """A completion carrying a client_event_id leaves an idempotency marker."""
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)

    client.post(f"/api/lessons/{lesson.id}/complete", json={
        "user_id": uid,
        "client_event_id": "evt-lesson-4",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })

    ev = db.query(SyncEvent).filter(
        SyncEvent.client_event_id == "evt-lesson-4"
    ).first()
    assert ev is not None
    assert ev.kind == "lesson_complete"
    assert ev.target_id == lesson.id
