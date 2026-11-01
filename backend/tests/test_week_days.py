"""A8: days with a finished lesson this week (goal 5 of 7) instead of a streak."""
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.models.lesson import Lesson
from backend.services import local_day, streak_service
from backend.services.streak_service import WEEK_GOAL_DAYS, week_days


@pytest.fixture
def warsaw(monkeypatch):
    # Warsaw after 25.10.2026 is CET (UTC+1); a fixed zone works on Windows too,
    # where time.tzset() does not exist
    monkeypatch.setattr(local_day, "LOCAL_TZ", timezone(timedelta(hours=1)))


def _lesson(db, uid, n, completed_at):
    db.add(Lesson(user_id=uid, day_number=n, title="t", topic="t", content="{}", cefr_level="A2",
                  language="German", is_completed=completed_at is not None, completed_at=completed_at))


def test_counts_local_days_of_this_week(client, sample_user, db, warsaw):
    uid = sample_user["user_id"]
    _lesson(db, uid, 1, datetime(2026, 10, 25, 22, 0))   # Sun 23:00 CET: last week
    _lesson(db, uid, 2, datetime(2026, 10, 25, 23, 30))  # Mon 00:30 CET (stored UTC): this week
    _lesson(db, uid, 3, datetime(2026, 10, 27, 18, 0))   # Tuesday
    _lesson(db, uid, 6, datetime(2026, 10, 27, 19, 0))   # same Tuesday, counted once
    _lesson(db, uid, 4, datetime(2026, 10, 28, 9, 0))    # Wednesday
    _lesson(db, uid, 5, None)                            # not finished
    db.commit()
    out = week_days(db, uid, today=date(2026, 10, 28))
    assert out == {"week_start": "2026-10-26", "days": 3, "goal": WEEK_GOAL_DAYS,
                   "dates": ["2026-10-26", "2026-10-27", "2026-10-28"]}


def test_missed_day_does_not_reset(client, sample_user, db, warsaw):
    uid = sample_user["user_id"]
    for n, day in enumerate((26, 27, 29, 30), start=1):  # Wednesday skipped
        _lesson(db, uid, n, datetime(2026, 10, day, 10, 0))
    db.commit()
    assert week_days(db, uid, today=date(2026, 10, 30))["days"] == 4


def test_stats_report_week_days(client, sample_user):
    r = client.get(f"/api/stats/{sample_user['user_id']}")
    assert r.status_code == 200
    week = r.json()["user"]["week_days"]
    assert week["days"] == 0 and week["goal"] == 5
