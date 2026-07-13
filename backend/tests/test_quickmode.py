"""Tests for /api/quickmode/* endpoint."""
import json
from datetime import datetime

from backend.models.lesson import Lesson
from backend.models.test_result import TestResult


def test_quickmode_basic(client, sample_user):
    """Quickmode returns activities for a user with no lesson yet."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == uid
    assert "activities" in data
    assert len(data["activities"]) > 0
    assert data["total_estimated_minutes"] > 0
    # First activity should be "lesson" since no lesson exists
    assert data["activities"][0]["id"] == "lesson"
    assert data["activities"][0]["completed"] is False


def test_quickmode_with_uncompleted_lesson(client, sample_user, db):
    """Quickmode shows lesson as priority 1 when lesson exists but not completed."""
    uid = sample_user["user_id"]
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Today's Lesson",
        topic="Greetings",
        cefr_level="A1",
        language="German",
        content=json.dumps({"vocabulary": []}),
        is_completed=False,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()

    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    lesson_activity = next(a for a in data["activities"] if a["id"] == "lesson")
    assert lesson_activity["completed"] is False
    assert lesson_activity["priority"] == 1


def test_quickmode_with_completed_lesson_and_no_test(client, sample_user, db):
    """Quickmode shows test as priority 1 when lesson completed but no test taken today."""
    uid = sample_user["user_id"]
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Today's Lesson",
        topic="Greetings",
        cefr_level="A1",
        language="German",
        content=json.dumps({"vocabulary": []}),
        is_completed=True,
        created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()

    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    test_activity = next(a for a in data["activities"] if a["id"] == "test")
    assert test_activity["completed"] is False
    assert test_activity["priority"] == 1


def test_quickmode_with_completed_lesson_and_test(client, sample_user, db):
    """Quickmode shows test as completed when test was taken today."""
    uid = sample_user["user_id"]
    lesson = Lesson(
        user_id=uid,
        day_number=1,
        title="Today's Lesson",
        topic="Greetings",
        cefr_level="A1",
        language="German",
        content=json.dumps({"vocabulary": []}),
        is_completed=True,
        created_at=datetime.now(),
    )
    db.add(lesson)
    # Add a test result from today
    test_result = TestResult(
        user_id=uid,
        test_type="daily",
        score=80.0,
        answers=json.dumps({}),
        errors=json.dumps([]),
        cefr_level="A1",
        language="German",
        created_at=datetime.now(),
    )
    db.add(test_result)
    db.commit()

    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    test_activity = next(a for a in data["activities"] if a["id"] == "test")
    assert test_activity["completed"] is True
    assert test_activity["priority"] == 3


def test_quickmode_user_not_found(client):
    """Quickmode returns 404 for non-existent user."""
    r = client.get("/api/quickmode/99999")
    assert r.status_code == 404


def test_quickmode_activities_structure(client, sample_user):
    """Each activity has all required fields."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    for activity in data["activities"]:
        assert "id" in activity
        assert "title" in activity
        assert "description" in activity
        assert "estimated_minutes" in activity
        assert "priority" in activity
        assert "route" in activity
        assert "icon" in activity
        assert "completed" in activity


def test_quickmode_total_time_under_15min(client, sample_user):
    """Total estimated time for uncompleted activities should be around 15 min."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["timer_minutes"] == 15
    assert data["total_estimated_minutes"] <= 20  # Some buffer
