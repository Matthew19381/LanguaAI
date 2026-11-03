"""Bank wiedzy (a learner's report 3.11.2026: nothing to review, no average, no stats)."""
from datetime import datetime, timedelta, timezone

from backend.models.exercise import Exercise
from backend.services.mastery import record_attempt


def _attempts(db, uid, skill, results):
    t0 = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    for i, ok in enumerate(results):
        record_attempt(db, user_id=uid, language="German", skill_id=skill, source="exercise",
                       correct=ok, occurred_at=t0 + timedelta(hours=i))
    db.commit()


def test_list_and_stats_count_accuracy_without_a_language_parameter(client, db, sample_user):
    """The page sent no language, so every skill showed 0 % and the average was 0."""
    uid = sample_user["user_id"]
    client.get(f"/api/topics/{uid}")                    # creates the entries
    _attempts(db, uid, "G-V2", [True] * 9 + [False])    # 90 %
    rows = {t["skill_id"]: t for t in client.get(f"/api/topics/{uid}").json()["topics"] if t["skill_id"]}
    assert rows["G-V2"]["memory_strength"] == 0.9
    assert rows["G-V2"]["mastery"] == {"status": "w_nauce", "accuracy": 0.9, "attempts": 10}
    stats = client.get(f"/api/topics/{uid}/stats").json()
    assert stats["avg_memory_strength"] > 0 and stats["mastered"] >= 1   # 0.9 counts as mastered (>= 0.8)


def test_due_lists_skills_with_due_exercises_or_weak_first_tries(client, db, sample_user):
    uid = sample_user["user_id"]
    client.get(f"/api/topics/{uid}")
    _attempts(db, uid, "G-AKK", [False, False, True, False, False, True])   # weak
    db.add(Exercise(user_id=uid, language="German", prompt="Ich ___ müde.", answer="bin", skill_id="G-V2",
                    exercise_type="fill-in-the-blank", times_seen=1,
                    next_review_date=datetime.now(timezone.utc) - timedelta(hours=1)))
    db.add(Exercise(user_id=uid, language="German", prompt="Er ___ müde.", answer="ist", skill_id="G-MODAL",
                    exercise_type="fill-in-the-blank", times_seen=0))           # never practised: not due
    db.commit()
    due = client.get(f"/api/topics/{uid}/due").json()["topics"]
    by_skill = {t["skill_id"]: t for t in due if t.get("skill_id")}
    assert set(by_skill) == {"G-V2", "G-AKK"}
    assert by_skill["G-V2"]["review_reason"] == "ćwiczenia do powtórki: 1"
    assert "słaba" in by_skill["G-AKK"]["review_reason"]
    listed = {t["skill_id"]: t for t in client.get(f"/api/topics/{uid}").json()["topics"] if t["skill_id"]}
    assert listed["G-V2"]["is_due"] is True and listed["G-MODAL"]["is_due"] is False
    assert client.get(f"/api/topics/{uid}/stats").json()["due_now"] >= 2


def test_practice_one_skill(client, db, sample_user):
    uid = sample_user["user_id"]
    for i, skill in enumerate(["G-V2", "G-V2", "G-AKK"]):
        db.add(Exercise(user_id=uid, language="German", prompt=f"P{i}", answer="a", skill_id=skill,
                        exercise_type="fill-in-the-blank"))
    db.commit()
    r = client.get(f"/api/exercises/{uid}/practice", params={"skill": "G-V2"}).json()
    assert [e["prompt"] for e in r["exercises"]] == ["P0", "P1"] and r["skill_id"] == "G-V2"
