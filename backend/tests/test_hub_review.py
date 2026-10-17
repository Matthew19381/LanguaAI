"""System-Glowny stage C: the hub's review deck reads the schedule and writes reviews back."""
from datetime import datetime, timedelta, timezone

from backend.models.flashcard import Flashcard
from backend.services.fsrs_service import apply_fsrs


def _card(client, uid, word="Hund"):
    r = client.post(f"/api/flashcards/{uid}/add", json={"word": word, "translation": "pies"})
    assert r.status_code == 200
    return r.json()["id"]


def _state(**kw):
    due = datetime.now(timezone.utc) + timedelta(days=3)
    st = {"fsrs_state": "Review", "fsrs_step": None, "stability": 3.2, "difficulty": 5.1,
          "next_review_date": due.isoformat(), "repetitions": 2, "lapses": 0, "interval_days": 3}
    st.update(kw)
    return st


def test_list_exposes_last_review_and_step(client, sample_user):
    uid = sample_user["user_id"]
    _card(client, uid)
    card = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]
    assert "last_review_date" in card and card["last_review_date"] is None
    assert "fsrs_step" in card


def test_hub_review_stores_hub_schedule(client, sample_user, db):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    when = datetime.now(timezone.utc) - timedelta(hours=1)
    r = client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid}, json={
        "rating": 3, "client_event_id": "hub-review-1", "reviewed_at": when.isoformat(), "state": _state()})
    assert r.status_code == 200, r.text
    assert r.json()["duplicate"] is False
    f = db.get(Flashcard, cid)
    db.refresh(f)
    assert (f.fsrs_state, f.fsrs_step, f.stability, f.repetitions, f.interval_days) == ("Review", None, 3.2, 2, 3)
    assert abs(f.last_review_date.replace(tzinfo=timezone.utc) - when) < timedelta(seconds=1)
    # due 3 days ahead is kept (the SCI-1 cap is not applied over the hub's schedule)
    assert f.next_review_date.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) + timedelta(days=2)
    assert f.correct_recall_sessions == 1
    card = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]
    assert card["last_review_date"] is not None and card["repetitions"] == 2


def test_hub_review_is_idempotent(client, sample_user):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    body = {"rating": 3, "client_event_id": "hub-review-7", "state": _state()}
    assert client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid}, json=body).json()["duplicate"] is False
    assert client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid}, json=body).json()["duplicate"] is True


def test_hub_review_learning_step_and_validation(client, sample_user, db):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    r = client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid},
                    json={"rating": 3, "state": _state(fsrs_state="Learning", fsrs_step=1, repetitions=1)})
    assert r.status_code == 200
    f = db.get(Flashcard, cid)
    db.refresh(f)
    assert f.fsrs_state == "Learning" and f.fsrs_step == 1
    bad = client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid},
                      json={"rating": 3, "state": _state(fsrs_state="New")})
    assert bad.status_code == 422


def test_hub_review_other_user_and_missing_card(client, sample_user):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    body = {"rating": 3, "state": _state()}
    assert client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid + 1}, json=body).status_code == 403
    r = client.post("/api/flashcards/99999/hub-review", params={"user_id": uid}, json=body)
    assert r.status_code == 404 and r.json()["detail"] == "Flashcard not found"


def test_hub_review_rejected_when_newer_review_in_linguaai(client, sample_user, db):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    f = db.get(Flashcard, cid)
    f.last_review_date = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()
    older = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    r = client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid},
                    json={"rating": 3, "reviewed_at": older, "state": _state()})
    assert r.status_code == 409
    db.refresh(f)
    assert f.repetitions == 0  # untouched


def test_hub_review_needs_app_token_when_gate_is_on(client, sample_user):
    from backend.config import settings

    uid = sample_user["user_id"]
    cid = _card(client, uid)
    body = {"rating": 3, "state": _state()}
    url = f"/api/flashcards/{cid}/hub-review"
    original = settings.APP_ACCESS_TOKEN
    settings.APP_ACCESS_TOKEN = "test-access-token-1234567890"
    try:
        client.cookies.clear()
        assert client.post(url, params={"user_id": uid}, json=body).status_code == 401
        assert client.post(url, params={"user_id": uid}, json=body,
                           headers={"X-App-Token": "wrong-token"}).status_code == 401
        ok = client.post(url, params={"user_id": uid}, json=body,
                         headers={"X-App-Token": "test-access-token-1234567890"})
        assert ok.status_code == 200, ok.text
    finally:
        settings.APP_ACCESS_TOKEN = original


# ── LinguaAI's own /review after a hub review (fix 2026-10-18) ──

def test_offline_review_older_than_hub_review_is_rejected(client, sample_user, db):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    hub_at = datetime.now(timezone.utc) - timedelta(hours=1)
    assert client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid}, json={
        "rating": 3, "reviewed_at": hub_at.isoformat(), "state": _state()}).status_code == 200
    # The phone answered before the hub but synced only now
    r = client.post(f"/api/flashcards/{cid}/review", params={"user_id": uid}, json={
        "rating": 1, "client_event_id": "phone-1",
        "reviewed_at": (hub_at - timedelta(hours=2)).isoformat()})
    assert r.status_code == 409
    f = db.get(Flashcard, cid)
    db.refresh(f)
    assert (f.fsrs_state, f.stability, f.lapses, f.repetitions) == ("Review", 3.2, 0, 2)
    assert abs(f.last_review_date.replace(tzinfo=timezone.utc) - hub_at) < timedelta(seconds=1)


def test_review_after_hub_review_is_scheduled_from_reviewed_at(client, sample_user, db):
    uid = sample_user["user_id"]
    cid = _card(client, uid)
    hub_at = datetime.now(timezone.utc) - timedelta(days=5)
    assert client.post(f"/api/flashcards/{cid}/hub-review", params={"user_id": uid}, json={
        "rating": 3, "reviewed_at": hub_at.isoformat(), "state": _state()}).status_code == 200
    answered = hub_at + timedelta(days=3)
    r = client.post(f"/api/flashcards/{cid}/review", params={"user_id": uid}, json={
        "rating": 3, "client_event_id": "phone-2", "reviewed_at": answered.isoformat()})
    assert r.status_code == 200, r.text
    f = db.get(Flashcard, cid)
    db.refresh(f)
    assert abs(f.last_review_date.replace(tzinfo=timezone.utc) - answered) < timedelta(seconds=1)
    # Stability follows the 3 days between the reviews, not the 5 days until the sync
    expected = apply_fsrs(rating=3, difficulty=5.1, stability=3.2, reps=2, lapses=0,
                          current_state="Review", last_review_date=hub_at, reviewed_at=answered)
    as_if_now = apply_fsrs(rating=3, difficulty=5.1, stability=3.2, reps=2, lapses=0,
                           current_state="Review", last_review_date=hub_at)
    assert f.stability == expected.stability != as_if_now.stability
