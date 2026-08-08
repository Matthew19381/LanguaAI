"""Tests for /api/lessons/* endpoints."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

MOCK_LESSON_CONTENT = {
    "vocabulary": [{"word": "Hund", "translation": "dog", "example": "Der Hund läuft."}],
    "grammar_explanation": "Basic grammar",
    "exercises": [],
    "dialogue": [],
    "comprehensible_input": {},
    "interleaved_review": {},
    "output_forcing": {},
}

MOCK_LESSON_DATA = {
    "title": "Introduction to German",
    "topic": "Greetings",
    "content": MOCK_LESSON_CONTENT,
}


def _create_lesson(db, user_id, day=1, completed=False):
    """Helper to directly insert a lesson into the test DB."""
    from backend.models.lesson import Lesson
    # Use datetime.now() (local time) so the created_at >= today_start filter
    # in the router (which also uses local date.today()) works correctly.
    now = datetime.now()
    lesson = Lesson(
        user_id=user_id,
        day_number=day,
        title="Test Lesson",
        topic="Test Topic",
        content=json.dumps(MOCK_LESSON_CONTENT),
        cefr_level="A1",
        language="German",
        is_completed=completed,
        created_at=now,
        completed_at=now if completed else None,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ---------------------------------------------------------------------------
# GET /api/lessons/list/{user_id}
# ---------------------------------------------------------------------------

def test_list_lessons_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/lessons/list/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["lessons"] == []
    assert data["total"] == 0
    assert data["completed"] == 0


def test_list_lessons_with_data(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_lesson(db, uid, day=1, completed=True)
    _create_lesson(db, uid, day=2, completed=False)

    r = client.get(f"/api/lessons/list/{uid}")
    data = r.json()
    assert data["total"] == 2
    assert data["completed"] == 1


# ---------------------------------------------------------------------------
# GET /api/lessons/{lesson_id}
# ---------------------------------------------------------------------------

def test_get_lesson_not_found(client):
    r = client.get("/api/lessons/99999?user_id=1")
    assert r.status_code == 404


def test_get_lesson_found(client, sample_user, db):
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)

    r = client.get(f"/api/lessons/{lesson.id}?user_id={uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["lesson_id"] == lesson.id
    assert data["day_number"] == 1
    assert data["is_completed"] is False


# ---------------------------------------------------------------------------
# POST /api/lessons/{lesson_id}/complete
# ---------------------------------------------------------------------------

def test_complete_lesson(client, sample_user, db):
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)

    r = client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["xp_awarded"] == 25
    assert data["is_completed"] is True


def test_complete_lesson_awards_xp(client, sample_user, db):
    uid = sample_user["user_id"]
    lesson = _create_lesson(db, uid)

    client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid})

    # Verify XP was added
    stats = client.get(f"/api/stats/{uid}").json()
    assert stats["user"]["total_xp"] >= 25


def test_complete_lesson_not_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post("/api/lessons/99999/complete", json={"user_id": uid})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/lessons/today/{user_id}  (AI call mocked)
# ---------------------------------------------------------------------------

def test_today_lesson_generated(client, sample_user, db):
    uid = sample_user["user_id"]

    # User needs an active study plan
    from backend.models.study_plan import StudyPlan
    plan = StudyPlan(
        user_id=uid,
        language="German",
        cefr_level="A1",
        plan_data=json.dumps({"weeks": []}),
        is_active=True,
    )
    db.add(plan)
    db.commit()

    with patch("backend.routers.lessons.generate_daily_lesson",
               new=AsyncMock(return_value=MOCK_LESSON_DATA)):
        r = client.get(f"/api/lessons/today/{uid}")

    assert r.status_code == 200
    data = r.json()
    assert "lesson_id" in data
    assert data["title"] == "Introduction to German"


def test_today_lesson_returns_existing(client, sample_user, db):
    """When a lesson for today already exists, the router returns it (not AI-generated content)."""
    uid = sample_user["user_id"]
    _create_lesson(db, uid, day=1)

    # Add a study plan so the "no plan" 404 path is not hit if the lesson is missed
    from backend.models.study_plan import StudyPlan
    plan = StudyPlan(
        user_id=uid, language="German", cefr_level="A1",
        plan_data=json.dumps({"weeks": []}), is_active=True,
    )
    db.add(plan)
    db.commit()

    # AI mock returns a DIFFERENT title — if the existing lesson is returned, title
    # will be "Test Lesson"; if AI is called instead, it will be "AI Generated".
    ai_response = {**MOCK_LESSON_DATA, "title": "AI Generated"}
    with patch("backend.routers.lessons.generate_daily_lesson",
               new=AsyncMock(return_value=ai_response)):
        r = client.get(f"/api/lessons/today/{uid}")

    assert r.status_code == 200
    # "Test Lesson" means the cached lesson was served; "AI Generated" means it wasn't found
    assert r.json()["title"] == "Test Lesson"


async def test_today_lesson_concurrent_requests_both_succeed(sample_user, db):
    """Regression test: two simultaneous requests for the same not-yet-generated
    lesson must BOTH succeed with the SAME lesson, not 500.

    Found live (2026-08-09): the loser of the race hit the UNIQUE constraint on
    (user_id, language, day_number), correctly entered the `except IntegrityError`
    recovery block, but that block looked up the winner's row by
    `date(created_at) == today` instead of by the exact constraint key
    (day_number) — that lookup could miss the just-committed row, falling
    through to `raise` and surfacing as an unhandled 500 to the client.
    """
    import asyncio
    from unittest.mock import AsyncMock, patch

    from fastapi import BackgroundTasks

    from backend.models.study_plan import StudyPlan
    from backend.routers.lessons import get_today_lesson
    from backend.tests.conftest import TestingSessionLocal

    uid = sample_user["user_id"]
    db.add(StudyPlan(
        user_id=uid, language="German", cefr_level="A1",
        plan_data=json.dumps({"weeks": []}), is_active=True,
    ))
    db.commit()

    # A mock that returns instantly wouldn't reliably interleave the two
    # coroutines (asyncio only switches tasks at an actual await point) — a
    # tiny sleep forces both calls past the "does today's lesson exist yet?"
    # check before either one commits its insert, reproducing the race.
    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.05)
        return MOCK_LESSON_DATA

    async def call():
        session = TestingSessionLocal()
        try:
            with patch("backend.routers.lessons.generate_daily_lesson",
                       new=AsyncMock(side_effect=slow_generate)):
                return await get_today_lesson(
                    user_id=uid, background_tasks=BackgroundTasks(), db=session
                )
        finally:
            session.close()

    results = await asyncio.gather(call(), call())
    lesson_ids = {r["lesson_id"] for r in results}
    assert len(lesson_ids) == 1, f"expected both requests to agree on one lesson, got {results}"
