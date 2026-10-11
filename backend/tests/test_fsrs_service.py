"""FSRS learning steps must survive between reviews (fix 2026-10-11).

Before the fix every Learning card was rebuilt at step 0, so with the default
steps (1 min, 10 min) a "Good" answer moved it to step 1, the next "Good"
moved it to step 1 again, and the card never reached Review.
"""
from datetime import datetime, timedelta, timezone

from backend.models.exercise import Exercise
from backend.models.topic import Topic
from backend.services.exercise_service import review_exercise
from backend.services.fsrs_service import apply_fsrs, infer_step

GOOD, AGAIN, HARD = 3, 1, 2


def _review(prev, rating, step_saved=True):
    """One review fed with the state the app saves after the previous one."""
    return apply_fsrs(
        rating=rating,
        difficulty=prev.difficulty,
        stability=prev.stability,
        reps=prev.repetitions,
        lapses=prev.lapses,
        current_state=prev.state,
        last_review_date=datetime.now(timezone.utc),
        step=prev.step if step_saved else None,
        next_review_date=prev.next_review_date,
    )


def test_new_card_good_good_graduates_to_review():
    first = apply_fsrs(GOOD)
    assert first.state == "Learning"
    assert first.step == 1
    second = _review(first, GOOD)
    assert second.state == "Review"
    assert second.step is None
    assert second.interval >= 1
    assert second.next_review_date - datetime.now(timezone.utc) >= timedelta(hours=23)


def test_repeated_good_never_stays_in_learning():
    result = apply_fsrs(GOOD)
    states = []
    for _ in range(5):
        result = _review(result, GOOD)
        states.append(result.state)
    assert set(states) == {"Review"}
    assert result.interval > 1


def test_again_returns_to_first_step():
    first = apply_fsrs(GOOD)
    again = _review(first, AGAIN)
    assert again.state == "Learning"
    assert again.step == 0


def test_hard_keeps_step():
    first = apply_fsrs(GOOD)
    hard = _review(first, HARD)
    assert hard.state == "Learning"
    assert hard.step == 1


def test_review_lapse_relearns_then_graduates():
    result = _review(apply_fsrs(GOOD), GOOD)
    assert result.state == "Review"
    lapse = _review(result, AGAIN)
    assert lapse.state == "Relearning"
    assert lapse.step == 0
    back = _review(lapse, GOOD)
    assert back.state == "Review"


def test_legacy_card_without_step_infers_it_from_due_gap():
    # Saved before fsrs_step existed: one Good, due 10 min after the review
    first = apply_fsrs(GOOD)
    second = _review(first, GOOD, step_saved=False)
    assert second.state == "Review"


def test_infer_step_from_gap():
    t = datetime(2026, 10, 1, 12, 0)
    assert infer_step("Learning", t, t + timedelta(minutes=10)) == 1
    assert infer_step("Learning", t, t + timedelta(minutes=1)) == 0
    assert infer_step("Relearning", t, t + timedelta(minutes=10)) == 0
    # naive and aware datetimes mixed (SQLite returns naive)
    assert infer_step("Learning", t, (t + timedelta(minutes=10)).replace(tzinfo=timezone.utc)) == 1


def test_infer_step_without_dates_or_with_day_gap_is_zero():
    t = datetime(2026, 10, 1, 12, 0)
    assert infer_step("Learning", None, None) == 0
    assert infer_step("Learning", t, None) == 0
    assert infer_step("Learning", t, t + timedelta(days=2)) == 0
    assert infer_step("Learning", t, t - timedelta(minutes=5)) == 0


def test_exercise_review_saves_step_and_graduates():
    ex = Exercise(user_id=1, language="German", prompt="p", answer="a",
                  difficulty=5.0, stability=0.0, retrievability=0.0,
                  repetitions=0, lapses=0, fsrs_state="Learning")
    review_exercise(None, ex, GOOD)
    assert (ex.fsrs_state, ex.fsrs_step) == ("Learning", 1)
    review_exercise(None, ex, GOOD)
    assert (ex.fsrs_state, ex.fsrs_step) == ("Review", None)


def test_topic_review_saves_step_and_graduates():
    topic = Topic(user_id=1, name="Akkusativ", language="German",
                  difficulty=5.0, stability=0.0, retrievability=0.0,
                  repetitions=0, lapses=0, fsrs_state="Learning",
                  memory_strength=0.0, total_reviews=0)
    topic.apply_fsrs(GOOD)
    assert (topic.fsrs_state, topic.fsrs_step) == ("Learning", 1)
    topic.apply_fsrs(GOOD)
    assert (topic.fsrs_state, topic.fsrs_step) == ("Review", None)
