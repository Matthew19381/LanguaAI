"""INT-1: GET /api/v1/summary — ecosystem summary for System-Glowny."""
from datetime import datetime, timedelta, timezone

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult


def _seed_activity(db, user_id: int, day: datetime):
    """One completed lesson, one test, two flashcards (1 due, 1 reviewed) on `day`."""
    db.add(
        Lesson(
            user_id=user_id,
            day_number=1,
            title="Tag 1",
            topic="Begrüßungen",
            content="{}",
            cefr_level="A1",
            language="German",
            is_completed=True,
            completed_at=day,
        )
    )
    db.add(
        TestResult(
            user_id=user_id,
            test_type="daily",
            score=80.0,
            answers="[]",
            cefr_level="A1",
            language="German",
            created_at=day,
        )
    )
    db.add(
        Flashcard(
            user_id=user_id,
            word="Hallo",
            translation="Cześć",
            language="German",
            cefr_level="A1",
            last_review_date=day,
            next_review_date=day + timedelta(days=3),
        )
    )
    db.add(
        Flashcard(
            user_id=user_id,
            word="Danke",
            translation="Dziękuję",
            language="German",
            cefr_level="A1",
            next_review_date=day - timedelta(days=1),
            is_mastered=True,
        )
    )
    db.commit()


def test_summary_unknown_user_404(client):
    resp = client.get("/api/v1/summary", params={"user_id": 99999})
    assert resp.status_code == 404


def test_summary_bad_date_422(client, sample_user):
    resp = client.get(
        "/api/v1/summary",
        params={"user_id": sample_user["user_id"], "date": "19-07-2026"},
    )
    assert resp.status_code == 422


def test_summary_empty_day(client, sample_user):
    resp = client.get(
        "/api/v1/summary",
        params={"user_id": sample_user["user_id"], "date": "2026-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["module"] == "lingua-ai"
    assert body["user_id"] == str(sample_user["user_id"])
    assert body["date"] == "2026-01-01"
    assert body["summary"]["lessons_completed"] == 0
    assert body["events"] == []
    # Honest null until the Affect Engine exists — never a fabricated number
    assert body["wellbeing_contribution"] is None


def test_summary_aggregates_daily_activity(client, db, sample_user):
    uid = sample_user["user_id"]
    day = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    _seed_activity(db, uid, day)

    resp = client.get(
        "/api/v1/summary", params={"user_id": uid, "date": "2026-07-19"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    s = body["summary"]
    assert s["lessons_completed"] == 1
    assert s["tests_submitted"] == 1
    assert s["reviews_done"] == 1        # card reviewed that day
    assert s["due_reviews"] >= 1         # overdue card counts as due
    assert s["mastered_words"] == 1
    assert s["target_language"] == "German"

    types = sorted(e["event_type"] for e in body["events"])
    assert types == ["lesson_completed", "test_submitted"]
    for ev in body["events"]:
        assert ev["module"] == "lingua-ai"
        assert ev["user_id"] == str(uid)
    test_ev = next(e for e in body["events"] if e["event_type"] == "test_submitted")
    assert test_ev["score"] == 80.0


def test_summary_ignores_other_days(client, db, sample_user):
    uid = sample_user["user_id"]
    day = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
    _seed_activity(db, uid, day)

    resp = client.get(
        "/api/v1/summary", params={"user_id": uid, "date": "2026-07-20"}
    )
    body = resp.json()
    assert body["summary"]["lessons_completed"] == 0
    assert body["summary"]["tests_submitted"] == 0
    assert body["summary"]["reviews_done"] == 0
    assert body["events"] == []
    # mastered/due are state (not per-day) — still visible
    assert body["summary"]["mastered_words"] == 1
