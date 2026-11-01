"""Audit 01.11.2026: today's lesson, the streak, the daily test and the local day."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.exercise import Exercise
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.test_result import TestResult
from backend.models.user import User
from backend.services import lesson_prefetch, local_day
from backend.services.curriculum import build_curriculum_plan
from backend.services.plan_day import todays_lesson
from backend.services.streak_service import calculate_streak
from backend.services.test_generator import submit_test

CET = timezone(timedelta(hours=1))
NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def warsaw(monkeypatch):
    monkeypatch.setattr(local_day, "LOCAL_TZ", CET)


def _plan(db, uid):
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(1)), is_active=True))
    db.commit()


def _lesson(db, uid, day, done_at=None, created=None, content=None):
    lesson = Lesson(user_id=uid, day_number=day, title=f"Dzień {day}", topic="x",
                    content=json.dumps(content or {"day_type": "nowy_material"}), cefr_level="A2",
                    language="German", is_completed=done_at is not None, completed_at=done_at,
                    created_at=created or NOW)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _local_midnight_utc(days_ago=0):
    start, _ = local_day.utc_range(local_day.local_today() - timedelta(days=days_ago))
    return start


# ── streak ──

def test_completing_a_lesson_counts_it_in_the_streak(client, sample_user, db):
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid, 1)
    assert client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid}).status_code == 200
    db.expire_all()
    assert db.query(User).get(uid).streak_days == 1


def test_completion_does_not_spend_the_freezes_again(client, sample_user, db):
    uid = sample_user["user_id"]
    # done 3 and 1 days ago: one missed day, bridged by a freeze
    _lesson(db, uid, 1, done_at=NOW - timedelta(days=3))
    _lesson(db, uid, 2, done_at=NOW - timedelta(days=1))
    for day in (3, 4):
        lesson = _lesson(db, uid, day)
        client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid})
    db.expire_all()
    user = db.query(User).get(uid)
    assert user.streak_freezes == 2
    assert user.streak_days == 4  # 3 days ago, the frozen day, yesterday, today


def test_streak_counts_the_local_day(db, sample_user):
    uid = sample_user["user_id"]
    # 00:30 local time today = 23:30 UTC yesterday
    _lesson(db, uid, 1, done_at=_local_midnight_utc() + timedelta(minutes=30))
    assert calculate_streak(db, uid, 0) == (1, 0)


# ── today's lesson ──

def test_today_shows_the_lesson_done_today_not_the_prepared_one(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, 1, done_at=NOW, created=NOW - timedelta(days=1))
    _lesson(db, uid, 2)  # prepared right after lesson 1 (A10)
    r = client.get(f"/api/lessons/today/{uid}").json()
    assert r["day_number"] == 1 and r["is_completed"]


def test_lesson_done_after_local_midnight_is_todays(db, sample_user):
    uid = sample_user["user_id"]
    done = _lesson(db, uid, 1, done_at=_local_midnight_utc() + timedelta(minutes=10))
    _lesson(db, uid, 2)
    user = db.query(User).get(uid)
    assert todays_lesson(db, user).id == done.id


def test_next_returns_the_waiting_lesson_instead_of_skipping_it(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, 1, done_at=NOW)
    _lesson(db, uid, 2)
    with patch("backend.routers.lessons.generate_daily_lesson", AsyncMock()) as gen:
        r = client.post(f"/api/lessons/next/{uid}").json()
    assert r["day_number"] == 2 and not gen.await_count


def test_new_lesson_does_not_reuse_a_skipped_day_number(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, 1, done_at=NOW - timedelta(days=2))
    _lesson(db, uid, 3, done_at=NOW - timedelta(days=1))  # day 2 was skipped earlier
    content = {"title": "Dzień 4", "day_type": "nowy_material", "vocabulary": [], "exercises": [],
               "grammar": {"topic": "x", "explanation": "y"}}
    with patch("backend.routers.lessons.generate_daily_lesson", AsyncMock(return_value=content)), \
         patch("backend.routers.lessons.process_lesson_topics_bg", AsyncMock()), \
         patch("backend.routers.lessons.generate_full_lesson_audio", AsyncMock()):
        r = client.get(f"/api/lessons/today/{uid}").json()
    assert r["day_number"] == 4 and not r["is_completed"]


async def test_today_waits_for_the_background_preparation(sample_user, db):
    uid = sample_user["user_id"]
    lock = lesson_prefetch._locks.setdefault(uid, asyncio.Lock())
    await lock.acquire()

    async def finish():
        await asyncio.sleep(0.05)
        lock.release()

    task = asyncio.create_task(finish())
    assert await lesson_prefetch.wait_if_preparing(uid) is True
    await task
    assert await lesson_prefetch.wait_if_preparing(uid) is False


# ── regenerate today's lesson ──

def test_reset_removes_only_the_unfinished_lesson_and_keeps_reviewed_cards(client, sample_user, db):
    uid = sample_user["user_id"]
    done = _lesson(db, uid, 1, done_at=NOW)
    waiting = _lesson(db, uid, 2)
    common = dict(user_id=uid, language="German", cefr_level="A2")
    db.add_all([
        Flashcard(word="der Hund", translation="pies", lesson_id=done.id, **common),
        Flashcard(word="die Katze", translation="kot", lesson_id=waiting.id, **common),
        Flashcard(word="das Haus", translation="dom", lesson_id=waiting.id, repetitions=2,
                  last_review_date=NOW, **common),
        Exercise(prompt="p", answer="a", source_lesson_id=waiting.id, user_id=uid, language="German"),
        Exercise(prompt="p2", answer="a2", source_lesson_id=waiting.id, user_id=uid, language="German",
                 times_seen=1),
    ])
    db.commit()
    r = client.delete(f"/api/lessons/reset-today/{uid}")
    assert r.status_code == 200 and r.json()["deleted"] == 1
    db.expire_all()
    assert [l.id for l in db.query(Lesson).filter(Lesson.user_id == uid)] == [done.id]
    cards = {c.word: c.lesson_id for c in db.query(Flashcard).filter(Flashcard.user_id == uid)}
    assert cards == {"der Hund": done.id, "das Haus": None}
    exercises = {e.prompt: e.source_lesson_id for e in db.query(Exercise).filter(Exercise.user_id == uid)}
    assert exercises == {"p2": None}


def test_reset_refuses_a_finished_lesson(client, sample_user, db):
    uid = sample_user["user_id"]
    _lesson(db, uid, 1, done_at=NOW)
    assert client.delete(f"/api/lessons/reset-today/{uid}").status_code == 409
    db.expire_all()
    assert db.query(Lesson).filter(Lesson.user_id == uid).count() == 1


# ── tests ──

def test_daily_test_is_about_the_lesson_just_studied(client, sample_user, db):
    uid = sample_user["user_id"]
    studied = _lesson(db, uid, 1, done_at=NOW, created=NOW - timedelta(days=1),
                      content={"grammar": {"topic": "Dativ"}})
    _lesson(db, uid, 2, content={"grammar": {"topic": "Perfekt"}})
    with patch("backend.services.test_generator.generate_daily_test",
               AsyncMock(return_value={"questions": [{"id": 1}]})) as gen:
        r = client.get(f"/api/tests/daily/{uid}").json()
    assert r["lesson_id"] == studied.id
    assert gen.await_args.kwargs["lesson_content"]["grammar"]["topic"] == "Dativ"


def test_taken_daily_test_does_not_return_answers_as_questions(client, sample_user, db):
    uid = sample_user["user_id"]
    _lesson(db, uid, 1, done_at=NOW)
    db.add(TestResult(user_id=uid, test_type="daily", score=80, answers=json.dumps({"1": "A"}),
                      errors="[]", cefr_level="A2", language="German"))
    db.commit()
    r = client.get(f"/api/tests/daily/{uid}").json()
    assert r["already_taken"] and r["questions"] == []


async def test_double_submit_gives_one_result_and_xp_once(sample_user, db):
    uid = sample_user["user_id"]

    async def slow(**_kw):
        await asyncio.sleep(0.05)
        return {"score": 80, "errors": []}

    with patch("backend.services.test_generator.analyze_test_errors", side_effect=slow):
        a, b = await asyncio.gather(
            submit_test(uid, "daily", [{"id": 1}], {"1": "A"}, db),
            submit_test(uid, "daily", [{"id": 1}], {"1": "A"}, db),
        )
    db.expire_all()
    assert db.query(TestResult).filter(TestResult.user_id == uid).count() == 1
    assert sorted([a["xp_earned"], b["xp_earned"]]) == [0, 40]
    assert db.query(User).get(uid).total_xp == 40


async def test_errors_test_is_checked_even_after_the_daily_test(sample_user, db):
    uid = sample_user["user_id"]
    with patch("backend.services.test_generator.analyze_test_errors",
               AsyncMock(side_effect=[{"score": 80, "errors": []}, {"score": 50, "errors": []}])):
        await submit_test(uid, "daily", [{"id": 1}], {"1": "A"}, db)
        r = await submit_test(uid, "errors", [{"id": 1}], {"1": "B"}, db)
    assert r["score"] == 50 and not r.get("already_submitted")


def test_unknown_test_type_is_rejected(client, sample_user):
    r = client.post("/api/tests/submit", json={"user_id": sample_user["user_id"], "test_type": "x",
                                                "questions": [], "answers": {}})
    assert r.status_code == 422


def test_weekly_test_week_follows_the_plan_day(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, 15, done_at=NOW)  # day 15 = week 3
    with patch("backend.routers.tests.get_or_create_weekly_test",
               AsyncMock(return_value={"questions": []})) as gen:
        client.get(f"/api/tests/weekly/{uid}")
    assert gen.await_args.args[1] == 3


def test_concepts_read_the_grammar_of_daily_lessons(client, sample_user, db):
    uid = sample_user["user_id"]
    _lesson(db, uid, 1, done_at=NOW, content={"grammar": {"topic": "Dativ", "explanation": "dem, der"}})
    with patch("backend.routers.lessons._ai_generate_concepts",
               AsyncMock(return_value={"concepts": [{"name": "Dativ"}]})) as gen:
        r = client.get(f"/api/lessons/latest/{uid}/concepts").json()
    assert gen.await_count == 1 and r["concepts"]
