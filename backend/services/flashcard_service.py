"""Flashcard-related helper functions extracted from routers."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.flashcard import Flashcard

# ── SCI-4: semantic spacing of related new words (Tinkham 1993) ──────────────
# Semantically related words learned together interfere with each other. When a
# batch of new cards contains several words of the same category, spread their
# first review across separate days instead of queueing them all at once.
SEMANTIC_STAGGER_MAX_DAYS = 3


def assign_cluster_offsets(categories: list[str]) -> list[int]:
    """Return a first-review day offset for each new card given its semantic
    category. Cards sharing a category are spread 0, 1, 2, … days apart (capped
    at SEMANTIC_STAGGER_MAX_DAYS); blank/unknown categories get offset 0.

    Tinkham (1993); Nakata & Suzuki (2019): spacing semantically related items
    reduces cross-item interference during initial learning.
    """
    seen: dict[str, int] = {}
    offsets: list[int] = []
    for cat in categories:
        key = (cat or "").strip().lower()
        if not key:
            offsets.append(0)
            continue
        n = seen.get(key, 0)
        offsets.append(min(n, SEMANTIC_STAGGER_MAX_DAYS))
        seen[key] = n + 1
    return offsets


# ── SCI-1: Successive relearning (Rawson & Dunlosky 2011) ────────────────────
# A card is "mastered" only after this many correct recalls on distinct days.
MASTERY_SESSIONS_REQUIRED = 3
# Until mastered, FSRS review intervals are capped to this many days so the
# card returns for another relearning session soon (relearn-to-criterion).
MASTERY_REVIEW_CAP_DAYS = 2


def advance_relearning_criterion(
    rating: int,
    correct_recall_sessions: int,
    last_recall_date: Optional[datetime],
    now: datetime,
) -> tuple[int, bool, Optional[datetime]]:
    """Advance a card's successive-relearning progress after a review.

    Rawson & Dunlosky (2011): relearning a item to a correct-recall criterion
    across *separate* sessions yields large, durable retention gains. A correct
    recall (rating >= 3) counts once per calendar day; a lapse (rating == 1)
    resets progress; a "Hard" recall (rating == 2) is neutral.

    Returns (correct_recall_sessions, is_mastered, last_recall_date).
    """
    sessions = correct_recall_sessions or 0
    new_last = last_recall_date
    if rating == 1:
        sessions = 0
    elif rating >= 3:
        if last_recall_date is None or last_recall_date.date() < now.date():
            sessions += 1
        new_last = now
    return sessions, sessions >= MASTERY_SESSIONS_REQUIRED, new_last


def create_flashcards_from_vocab(
    db: Session,
    vocabulary: list,
    user_id: int,
    target_language: str,
    cefr_level: str,
    lesson_id: int,
    day_number: int,
    topic: str,
) -> None:
    """Batch-create flashcards from vocabulary list, skipping duplicates."""
    vocab_words = [v.get("word", "") for v in vocabulary if v.get("word") and v.get("translation")]
    if vocab_words:
        existing = db.query(Flashcard.word).filter(
            Flashcard.user_id == user_id,
            Flashcard.language == target_language,
            Flashcard.word.in_(vocab_words),
        ).all()
        existing_words = {row[0] for row in existing}
    else:
        existing_words = set()

    # Collect the cards to create (dedup against DB and within this batch)
    to_create = []
    seen_batch = set()
    for item in vocabulary:
        word = item.get("word", "")
        translation = item.get("translation", "")
        if word and translation and word not in existing_words and word not in seen_batch:
            to_create.append(item)
            seen_batch.add(word)

    # SCI-4: stagger first-review dates so same-category words don't all land
    # in the queue together.
    offsets = assign_cluster_offsets([it.get("category", "") for it in to_create])
    now = datetime.now(timezone.utc)
    for item, offset in zip(to_create, offsets, strict=True):
        db.add(Flashcard(
            user_id=user_id,
            word=item.get("word", ""),
            translation=item.get("translation", ""),
            example_sentence=item.get("example", "") or item.get("example_sentence", ""),
            language=target_language,
            cefr_level=cefr_level,
            lesson_id=lesson_id,
            lesson_day=day_number,
            lesson_topic=topic,
            next_review_date=now + timedelta(days=offset),
        ))
