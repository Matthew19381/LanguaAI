"""SCI-1: unit tests for the successive-relearning criterion (Rawson & Dunlosky 2011)."""
from datetime import datetime, timedelta, timezone

from backend.services.flashcard_service import (
    MASTERY_SESSIONS_REQUIRED,
    advance_relearning_criterion,
)

DAY1 = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
DAY2 = DAY1 + timedelta(days=1)
DAY3 = DAY1 + timedelta(days=2)


def test_correct_recall_counts_once_per_day():
    # Two correct recalls on the SAME day count as one session.
    sessions, mastered, last = advance_relearning_criterion(3, 0, None, DAY1)
    assert sessions == 1 and not mastered
    sessions, mastered, last = advance_relearning_criterion(
        3, sessions, last, DAY1 + timedelta(hours=2)
    )
    assert sessions == 1  # same calendar day → no extra credit


def test_mastery_after_three_distinct_days():
    sessions, mastered, last = advance_relearning_criterion(3, 0, None, DAY1)
    assert (sessions, mastered) == (1, False)
    sessions, mastered, last = advance_relearning_criterion(3, sessions, last, DAY2)
    assert (sessions, mastered) == (2, False)
    sessions, mastered, last = advance_relearning_criterion(3, sessions, last, DAY3)
    assert sessions == MASTERY_SESSIONS_REQUIRED
    assert mastered is True


def test_lapse_resets_progress():
    sessions, mastered, last = advance_relearning_criterion(3, 2, DAY1, DAY2)
    assert sessions == 3 and mastered  # would reach criterion...
    # ...but an 'Again' the next day wipes the progress
    sessions, mastered, last = advance_relearning_criterion(1, sessions, last, DAY3)
    assert sessions == 0 and mastered is False


def test_hard_rating_is_neutral():
    # rating 2 (Hard) neither advances nor resets the criterion
    sessions, mastered, last = advance_relearning_criterion(2, 2, DAY1, DAY2)
    assert sessions == 2 and not mastered
    assert last == DAY1  # last_recall_date unchanged on a Hard review


# ── Integration: review endpoint exposes mastery progress ────────────────────

def _add(client, uid, word="Vogel", translation="bird"):
    return client.post(f"/api/flashcards/{uid}/add", json={"word": word, "translation": translation}).json()["id"]


def test_review_reports_mastery_progress(client, sample_user):
    uid = sample_user["user_id"]
    card_id = _add(client, uid)
    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 3}, params={"user_id": uid})
    data = r.json()
    assert data["correct_recall_sessions"] == 1
    assert data["is_mastered"] is False


def test_unmastered_interval_is_capped(client, sample_user):
    """An Easy review on a fresh card would schedule far out; SCI-1 caps it."""
    from backend.services.flashcard_service import MASTERY_REVIEW_CAP_DAYS
    uid = sample_user["user_id"]
    card_id = _add(client, uid, "Blume", "flower")
    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 4}, params={"user_id": uid})
    data = r.json()
    # Not yet mastered → interval never exceeds the relearning cap
    assert data["is_mastered"] is False
    assert data["new_interval"] <= MASTERY_REVIEW_CAP_DAYS


def test_flashcard_list_exposes_mastered_count(client, sample_user):
    uid = sample_user["user_id"]
    _add(client, uid, "Baum", "tree")
    r = client.get(f"/api/flashcards/{uid}")
    data = r.json()
    assert "mastered_count" in data
    assert data["flashcards"][0]["is_mastered"] is False
