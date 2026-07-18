"""SCI-4: unit tests for semantic spacing of related new words (Tinkham 1993)."""
from datetime import datetime, timezone

from backend.models.flashcard import Flashcard
from backend.services.flashcard_service import (
    SEMANTIC_STAGGER_MAX_DAYS,
    assign_cluster_offsets,
    create_flashcards_from_vocab,
)

# ── assign_cluster_offsets ───────────────────────────────────────────────────

def test_same_category_is_spread():
    offsets = assign_cluster_offsets(["colours", "colours", "colours"])
    assert offsets == [0, 1, 2]


def test_distinct_categories_all_start_at_zero():
    offsets = assign_cluster_offsets(["food", "motion", "weather"])
    assert offsets == [0, 0, 0]


def test_blank_category_gets_zero():
    offsets = assign_cluster_offsets(["", None, "colours", "colours"])
    assert offsets == [0, 0, 0, 1]


def test_offset_is_capped():
    cats = ["x"] * (SEMANTIC_STAGGER_MAX_DAYS + 4)
    offsets = assign_cluster_offsets(cats)
    assert max(offsets) == SEMANTIC_STAGGER_MAX_DAYS


def test_category_matching_is_case_insensitive():
    assert assign_cluster_offsets(["Food", "food", "FOOD"]) == [0, 1, 2]


# ── create_flashcards_from_vocab staggering ──────────────────────────────────

def test_related_words_get_staggered_review_dates(db, sample_user):
    uid = sample_user["user_id"]
    vocab = [
        {"word": "rot", "translation": "red", "category": "colours"},
        {"word": "blau", "translation": "blue", "category": "colours"},
        {"word": "grün", "translation": "green", "category": "colours"},
        {"word": "Hund", "translation": "dog", "category": "animals"},
    ]
    create_flashcards_from_vocab(db, vocab, uid, "German", "A1", 1, 1, "Basics")
    db.commit()

    cards = {c.word: c for c in db.query(Flashcard).filter(Flashcard.user_id == uid).all()}
    now = datetime.now(timezone.utc)

    def days_out(card):
        due = card.next_review_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return round((due - now).total_seconds() / 86400)

    # Three colours spread over separate days; the animal starts immediately.
    colour_offsets = sorted(days_out(cards[w]) for w in ("rot", "blau", "grün"))
    assert colour_offsets == [0, 1, 2]
    assert days_out(cards["Hund"]) == 0


def test_duplicate_words_in_batch_created_once(db, sample_user):
    uid = sample_user["user_id"]
    vocab = [
        {"word": "Tisch", "translation": "table", "category": "furniture"},
        {"word": "Tisch", "translation": "table again", "category": "furniture"},
    ]
    create_flashcards_from_vocab(db, vocab, uid, "German", "A1", 1, 1, "Home")
    db.commit()
    count = db.query(Flashcard).filter(Flashcard.user_id == uid, Flashcard.word == "Tisch").count()
    assert count == 1
