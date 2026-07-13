"""
FSRS (Free Spaced Repetition Scheduler) Service.

Replaces the legacy SM-2 algorithm with FSRS v6, a modern spaced repetition
algorithm based on the DSR (Difficulty, Stability, Retrievability) model.

Uses the `fsrs` Python package (v6.x) which implements the FSRS-6 algorithm.

Rating scale (unified 1-4, same as Anki):
  1 = Again  (forgot completely)
  2 = Hard   (recalled with significant difficulty)
  3 = Good   (recalled with some effort)
  4 = Easy   (instant, effortless recall)

Both flashcards and topics use this same 1-4 scale for consistency.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fsrs import Card, Rating, Scheduler, State

# ── Module-level Scheduler instance ──────────────────────────────────────────
_scheduler = Scheduler()


# ── State mapping ────────────────────────────────────────────────────────────
_STATE_TO_NAME = {
    State.Learning: "Learning",
    State.Review: "Review",
    State.Relearning: "Relearning",
}

_NAME_TO_STATE = {
    "Learning": State.Learning,
    "Review": State.Review,
    "Relearning": State.Relearning,
}


@dataclass
class FSRSResult:
    """Result of an FSRS review calculation."""
    difficulty: float
    stability: float
    retrievability: float
    interval: int          # days until next review
    repetitions: int       # total number of reviews
    next_review_date: datetime
    state: str             # "Learning", "Review", "Relearning"
    lapses: int            # updated lapse count


def _card_to_json(card: Card) -> str:
    """Serialize a Card to JSON string."""
    data = {
        "card_id": getattr(card, 'card_id', 0) or 0,
        "state": card.state.value,
        "step": getattr(card, 'step', 0) or 0,
        "difficulty": card.difficulty if card.difficulty is not None else 5.0,
        "stability": card.stability if card.stability is not None else 0.1,
        "due": card.due.isoformat() if card.due else datetime.now(timezone.utc).isoformat(),
        "last_review": card.last_review.isoformat() if card.last_review else None,
    }
    return json.dumps(data)


def _card_from_state(
    difficulty: float,
    stability: float,
    state: str,
    last_review: datetime,
    reps: int,
) -> Card:
    """
    Reconstruct a Card from saved FSRS state.

    Uses Card.from_json to properly restore the card's internal state.
    """
    now = datetime.now(timezone.utc)
    state_enum = _NAME_TO_STATE.get(state, State.Learning)

    # Ensure last_review is timezone-aware (SQLite may store naive datetimes)
    if last_review and last_review.tzinfo is None:
        last_review = last_review.replace(tzinfo=timezone.utc)

    data = {
        "card_id": 0,
        "state": state_enum.value,
        "step": 0,
        "difficulty": difficulty if difficulty is not None else 5.0,
        "stability": stability if stability and stability > 0 else 0.1,
        "due": now.isoformat(),
        "last_review": last_review.isoformat() if last_review else now.isoformat(),
    }
    try:
        return Card.from_json(json.dumps(data))
    except Exception:
        return Card()


def apply_fsrs(
    rating: int,
    difficulty: float = 5.0,
    stability: float = 0.0,
    retrievability: Optional[float] = None,
    elapsed_days: int = 0,
    reps: int = 0,
    lapses: int = 0,
    current_state: str = "Learning",
    last_review_date: Optional[datetime] = None,
) -> FSRSResult:
    """
    Apply the FSRS algorithm to compute the next review schedule.

    Args:
        rating: User's quality rating (1-4)
          1 = Again (forgot)
          2 = Hard (recalled with difficulty)
          3 = Good (recalled with effort)
          4 = Easy (instant recall)
        difficulty: Current difficulty estimate (FSRS default ~5.0)
        stability: Current stability estimate (days)
        retrievability: Current retrievability (0-1), computed if None
        elapsed_days: Days since the last review
        reps: Total number of reviews so far
        lapses: Total number of times the card was forgotten
        current_state: Current state — "Learning", "Review", "Relearning"
        last_review_date: When the card was last reviewed

    Returns:
        FSRSResult with updated scheduling parameters
    """
    now = datetime.now(timezone.utc)

    # Map 1-4 rating to fsrs.Rating enum
    rating_map = {
        1: Rating.Again,
        2: Rating.Hard,
        3: Rating.Good,
        4: Rating.Easy,
    }
    fsrs_rating = rating_map.get(rating, Rating.Good)

    # Build or reconstruct the card
    if reps == 0:
        # Brand new card
        card = Card()
    else:
        # Reconstruct card from saved state
        card = _card_from_state(
            difficulty=difficulty,
            stability=stability,
            state=current_state,
            last_review=last_review_date or now - timedelta(days=elapsed_days),
            reps=reps,
        )

    # Run FSRS
    updated_card, _log = _scheduler.review_card(card, fsrs_rating, now)

    # Compute interval in days
    interval_days = max(1, (updated_card.due - now).days)

    # Get retrievability
    try:
        ret = _scheduler.get_card_retrievability(updated_card, now)
    except Exception:
        ret = 0.9 if rating >= 3 else 0.3

    # Determine new state
    new_state = _STATE_TO_NAME.get(updated_card.state, "Learning")

    # Update lapse count
    new_lapses = lapses + 1 if rating == 1 else lapses

    return FSRSResult(
        difficulty=round(updated_card.difficulty, 4) if updated_card.difficulty else difficulty,
        stability=round(updated_card.stability, 4) if updated_card.stability else stability,
        retrievability=round(ret, 4),
        interval=interval_days,
        repetitions=reps + 1,
        next_review_date=updated_card.due,
        state=new_state,
        lapses=new_lapses,
    )


def calculate_memory_strength_fsrs(
    difficulty: float,
    stability: float,
    retrievability: float,
    reps: int,
    lapses: int,
) -> float:
    """
    Calculate a 0.0-1.0 memory strength indicator based on FSRS state.

    This replaces the old SM-2 memory_strength calculation.
    Uses retrievability as the primary signal, adjusted by stability and difficulty.
    """
    if reps == 0:
        return 0.0

    # Retrievability is the primary signal (probability of recall)
    strength = retrievability

    # Bonus for high stability (long-term retention)
    stability_bonus = min(0.2, stability / 365.0 * 0.2)

    # Penalty for high difficulty
    difficulty_penalty = min(0.2, (difficulty / 10.0) * 0.2)

    # Penalty for many lapses relative to reps
    lapse_ratio = lapses / max(reps, 1)
    lapse_penalty = min(0.2, lapse_ratio * 0.4)

    strength = strength + stability_bonus - difficulty_penalty - lapse_penalty
    return round(min(1.0, max(0.0, strength)), 2)
