"""A10: the next lesson is prepared in the background, so the lesson page does not wait."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import settings
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.services import lesson_prefetch
from backend.services.curriculum import build_curriculum_plan
from backend.tests.conftest import TestingSessionLocal

CONTENT = {"title": "Dzień 2: Rodzina", "day_type": "nowy_material",
           "vocabulary": [{"word": "die Mutter", "translation": "matka"}],
           "grammar": {"topic": "Possessivartikel", "explanation": "mein, dein"},
           "exercises": []}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "PREPARE_NEXT_LESSON", True)
    monkeypatch.setattr(lesson_prefetch, "SessionLocal", TestingSessionLocal)
    gen = AsyncMock(return_value=json.loads(json.dumps(CONTENT)))
    monkeypatch.setattr(lesson_prefetch, "generate_daily_lesson", gen)
    monkeypatch.setattr(lesson_prefetch, "generate_full_lesson_audio", AsyncMock(return_value={}))
    monkeypatch.setattr(lesson_prefetch, "process_lesson_topics_bg", AsyncMock(return_value=None))
    return gen


def _plan(db, uid):
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(1)), is_active=True))
    db.commit()


def _lesson(db, uid, day=1, done=False, created=None):
    lesson = Lesson(user_id=uid, day_number=day, title=f"Dzień {day}", topic="x",
                    content=json.dumps({"day_type": "nowy_material"}), cefr_level="A2", language="German",
                    is_completed=done, completed_at=datetime.now(timezone.utc) if done else None,
                    created_at=created or datetime.now(timezone.utc))
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _lessons(db, uid):
    db.expire_all()
    return db.query(Lesson).filter(Lesson.user_id == uid).order_by(Lesson.day_number).all()


async def test_prepares_next_day_after_completed_lesson(sample_user, db, enabled):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, day=1, done=True)
    lesson_id = await lesson_prefetch.prepare_next_lesson(uid)
    rows = _lessons(db, uid)
    assert [(r.day_number, r.is_completed) for r in rows] == [(1, True), (2, False)]
    assert rows[1].id == lesson_id
    assert enabled.call_args.kwargs["day_number"] == 2
    lesson_prefetch.generate_full_lesson_audio.assert_awaited_once()


async def test_nothing_while_a_lesson_waits_or_when_off(sample_user, db, enabled, monkeypatch):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, day=1, done=True)
    _lesson(db, uid, day=2, done=False)
    assert await lesson_prefetch.prepare_next_lesson(uid) is None   # at most one lesson ahead
    monkeypatch.setattr(settings, "PREPARE_NEXT_LESSON", False)
    db.query(Lesson).filter(Lesson.day_number == 2).delete()
    db.commit()
    assert await lesson_prefetch.prepare_next_lesson(uid) is None
    enabled.assert_not_awaited()


async def test_no_plan_or_failed_generation_leaves_nothing(sample_user, db, enabled):
    uid = sample_user["user_id"]
    _lesson(db, uid, day=1, done=True)
    assert await lesson_prefetch.prepare_next_lesson(uid) is None    # no active plan
    _plan(db, uid)
    enabled.side_effect = RuntimeError("model down")
    assert await lesson_prefetch.prepare_next_lesson(uid) is None
    assert len(_lessons(db, uid)) == 1


def test_completing_a_lesson_prepares_the_next_one(client, sample_user, db, enabled):
    uid = sample_user["user_id"]
    _plan(db, uid)
    lesson = _lesson(db, uid, day=1)
    assert client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid}).status_code == 200
    assert [r.day_number for r in _lessons(db, uid)] == [1, 2]
    # the same day the lesson page still shows the lesson done today ...
    assert client.get(f"/api/lessons/today/{uid}").json()["day_number"] == 1
    # ... and the next day the prepared one, without generating
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    db.query(Lesson).filter(Lesson.user_id == uid).update({"created_at": yesterday})
    db.commit()
    with patch("backend.routers.lessons.generate_daily_lesson", AsyncMock()) as page_gen:
        r = client.get(f"/api/lessons/today/{uid}").json()
    assert r["day_number"] == 2 and not page_gen.await_count


def test_active_learners(sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    old = _lesson(db, uid, day=1, done=True)
    old.completed_at = datetime.utcnow() - timedelta(days=30)
    db.commit()
    assert lesson_prefetch.active_learners(db) == []
    _lesson(db, uid, day=2, done=True)
    assert lesson_prefetch.active_learners(db) == [uid]
