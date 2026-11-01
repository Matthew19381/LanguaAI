"""Error items in the hub's review deck: the list the hub imports and the review it sends back."""
from datetime import datetime, timedelta, timezone

from backend.models.exercise import Exercise
from backend.models.skill_attempt import SkillAttempt


def _ex(db, uid, **kw):
    ex = Exercise(user_id=uid, language="German", prompt=kw.pop("prompt", "p"), answer="a", **kw)
    db.add(ex)
    db.commit()
    return ex


def _state(**kw):
    base = {"fsrs_state": "Review", "fsrs_step": None, "stability": 4.2, "difficulty": 5.1,
            "next_review_date": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "repetitions": 2, "lapses": 1, "interval_days": 4}
    return {**base, **kw}


def test_for_hub_lists_only_error_items(client, db, sample_user):
    uid = sample_user["user_id"]
    _ex(db, uid, prompt="z rozmowy", exercise_type="error_correction", skill_id="G-V2")
    _ex(db, uid, prompt="pomylone", first_attempt_incorrect=True, skill_tag="G-DAT")
    _ex(db, uid, prompt="zapomniane", lapses=1)
    _ex(db, uid, prompt="zawsze dobrze")
    _ex(db, uid, prompt="wyłączone", exercise_type="error_correction", is_active=False)
    body = client.get(f"/api/exercises/{uid}/for-hub").json()
    assert body["total"] == 3
    items = {e["prompt"]: e for e in body["exercises"]}
    assert set(items) == {"z rozmowy", "pomylone", "zapomniane"}
    assert items["pomylone"]["skill_id"] == "G-DAT"
    assert items["pomylone"]["skill_name"] == "Celownik (Dativ): rodzajniki, zaimki, czasowniki z celownikiem"
    assert items["z rozmowy"]["answer"] == "a"


def test_hub_review_stores_the_hub_schedule_and_counts_for_mastery(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _ex(db, uid, exercise_type="error_correction", skill_id="G-V2")
    body = {"rating": 3, "client_event_id": "hub-review-1",
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "state": _state()}
    r = client.post(f"/api/exercises/{ex.id}/hub-review", params={"user_id": uid}, json=body)
    assert r.status_code == 200 and r.json()["duplicate"] is False
    again = client.post(f"/api/exercises/{ex.id}/hub-review", params={"user_id": uid}, json=body)
    assert again.json()["duplicate"] is True
    db.expire_all()
    ex = db.get(Exercise, ex.id)
    assert ex.fsrs_state == "Review" and ex.stability == 4.2 and ex.repetitions == 2
    assert ex.times_seen == 1 and ex.times_correct == 1
    attempts = db.query(SkillAttempt).all()
    assert [(a.skill_id, a.correct, a.source) for a in attempts] == [("G-V2", True, "hub")]


def test_hub_review_rejects_older_review_wrong_user_and_bad_state(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = _ex(db, uid, exercise_type="error_correction",
             last_review_date=datetime.now(timezone.utc))
    old = {"client_event_id": "t-exe-58", "rating": 1, "reviewed_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
           "state": _state()}
    assert client.post(f"/api/exercises/{ex.id}/hub-review", params={"user_id": uid}, json=old).status_code == 409
    assert client.post(f"/api/exercises/{ex.id}/hub-review", params={"user_id": uid + 1},
                       json=old).status_code == 403
    bad = {"client_event_id": "t-exe-63", "rating": 3, "state": _state(fsrs_state="New")}
    assert client.post(f"/api/exercises/{ex.id}/hub-review", params={"user_id": uid}, json=bad).status_code == 422
    assert client.post("/api/exercises/999999/hub-review", params={"user_id": uid}, json=bad).json()["detail"] \
        == "Exercise not found"
