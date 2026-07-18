"""SCI-5: unit + endpoint tests for data-driven best-study-time (May & Hasher 1998)."""
from datetime import datetime

from backend.models.test_result import TestResult
from backend.services.analytics_service import (
    MIN_SAMPLES,
    analyze_best_study_time,
    bucket_for_hour,
)

# ── bucket_for_hour ──────────────────────────────────────────────────────────

def test_bucket_boundaries():
    assert bucket_for_hour(5) == "morning"
    assert bucket_for_hour(11) == "morning"
    assert bucket_for_hour(12) == "afternoon"
    assert bucket_for_hour(17) == "evening"
    assert bucket_for_hour(22) == "night"
    assert bucket_for_hour(3) == "night"


# ── analyze_best_study_time ──────────────────────────────────────────────────

def test_insufficient_data_gives_no_recommendation():
    out = analyze_best_study_time([(9, 80.0), (10, 90.0)])
    assert out["enough_data"] is False
    assert out["best_bucket"] is None


def test_picks_highest_scoring_bucket():
    # 4 strong morning tests, 4 weak evening tests → morning wins
    samples = [(9, 95.0)] * 4 + [(19, 40.0)] * 4
    out = analyze_best_study_time(samples)
    assert out["enough_data"] is True
    assert out["best_bucket"] == "morning"
    assert out["buckets"]["morning"]["avg_score"] == 95.0


def test_bucket_below_min_per_bucket_cannot_win():
    # One lone perfect night score, but not enough of them to be trusted;
    # the well-sampled afternoon bucket should be chosen instead.
    samples = [(14, 70.0)] * 7 + [(23, 100.0)]
    out = analyze_best_study_time(samples)
    assert out["samples"] == 8
    assert out["best_bucket"] == "afternoon"


def test_min_samples_threshold_value():
    samples = [(9, 80.0)] * (MIN_SAMPLES - 1)
    assert analyze_best_study_time(samples)["enough_data"] is False


# ── GET /api/stats/{user_id}/best-study-time ─────────────────────────────────

def _add_test_result(db, uid, hour, score, seq):
    # seq keeps created_at unique (UNIQUE user_id+test_type+language+created_at)
    db.add(TestResult(
        user_id=uid, test_type="daily", score=score, answers="[]",
        language="German", cefr_level="A1",
        created_at=datetime(2026, 7, 1, hour, seq % 60),
    ))


def test_endpoint_insufficient_data(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/stats/{uid}/best-study-time")
    assert r.status_code == 200
    assert r.json()["enough_data"] is False


def test_endpoint_recommends_bucket(client, sample_user, db):
    uid = sample_user["user_id"]
    seq = 0
    for _ in range(5):
        _add_test_result(db, uid, hour=9, score=92.0, seq=seq)
        seq += 1
    for _ in range(4):
        _add_test_result(db, uid, hour=20, score=55.0, seq=seq)
        seq += 1
    db.commit()

    r = client.get(f"/api/stats/{uid}/best-study-time")
    assert r.status_code == 200
    data = r.json()
    assert data["enough_data"] is True
    assert data["best_bucket"] == "morning"


def test_endpoint_user_not_found(client):
    r = client.get("/api/stats/99999/best-study-time")
    assert r.status_code == 404
