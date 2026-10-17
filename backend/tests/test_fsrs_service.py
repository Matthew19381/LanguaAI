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


# ── Offline answers are scheduled from when they were given (fix 2026-10-18) ──
# FSRS predicts recall from the time elapsed since the last review, so a review
# replayed from a phone that was offline must use the moment of the answer.

def _review_card(last, reviewed_at, rating=GOOD):
    return apply_fsrs(
        rating=rating, difficulty=5.0, stability=4.0, reps=3, lapses=0,
        current_state="Review", last_review_date=last, step=None,
        next_review_date=last + timedelta(days=4), reviewed_at=reviewed_at,
    )


def test_offline_review_is_scheduled_from_reviewed_at():
    answered = datetime.now(timezone.utc) - timedelta(days=6)
    offline = _review_card(answered - timedelta(days=4), answered)
    # The same answer given today after the same 4-day gap
    online = _review_card(datetime.now(timezone.utc) - timedelta(days=4), None)
    assert offline.stability == online.stability
    # The due date counts from the answer (interval fuzzing makes the exact day random)
    gap = offline.next_review_date - answered
    assert timedelta(days=offline.interval) <= gap < timedelta(days=offline.interval + 1)


def test_offline_review_elapsed_time_changes_stability():
    """Before the fix the 6 days spent offline were counted as extra elapsed time."""
    answered = datetime.now(timezone.utc) - timedelta(days=6)
    last = answered - timedelta(days=1)
    on_time = _review_card(last, answered)
    as_if_received_now = _review_card(last, None)
    assert on_time.stability != as_if_received_now.stability


def test_reviewed_at_before_last_review_is_clamped():
    last = datetime.now(timezone.utc) - timedelta(days=1)
    result = _review_card(last, last - timedelta(days=3))
    assert result.next_review_date > last


def test_naive_reviewed_at_is_treated_as_utc():
    answered = datetime.now(timezone.utc) - timedelta(days=2)
    aware = _review_card(answered - timedelta(days=4), answered)
    naive = _review_card((answered - timedelta(days=4)).replace(tzinfo=None), answered.replace(tzinfo=None))
    assert aware.stability == naive.stability
    gap = naive.next_review_date - answered
    assert timedelta(days=naive.interval) <= gap < timedelta(days=naive.interval + 1)


def test_exercise_offline_answer_uses_answer_time():
    answered = datetime.now(timezone.utc) - timedelta(days=5)
    ex = Exercise(user_id=1, language="German", prompt="p", answer="a",
                  difficulty=5.0, stability=4.0, retrievability=0.9,
                  repetitions=3, lapses=0, fsrs_state="Review",
                  last_review_date=answered - timedelta(days=4),
                  next_review_date=answered)
    review_exercise(None, ex, GOOD, now=answered)
    assert ex.last_review_date == answered
    gap = ex.next_review_date - answered
    assert timedelta(days=ex.interval_days) <= gap < timedelta(days=ex.interval_days + 1)


def test_exercise_out_of_order_answer_keeps_last_review():
    last = datetime.now(timezone.utc) - timedelta(hours=1)
    ex = Exercise(user_id=1, language="German", prompt="p", answer="a",
                  difficulty=5.0, stability=4.0, retrievability=0.9,
                  repetitions=3, lapses=0, fsrs_state="Review",
                  last_review_date=last, next_review_date=last + timedelta(days=4))
    review_exercise(None, ex, GOOD, now=last - timedelta(days=2))
    assert ex.last_review_date == last


def test_topic_again_counts_lapse():
    topic = Topic(user_id=1, name="Dativ", language="German",
                  difficulty=5.0, stability=0.0, retrievability=0.0,
                  repetitions=0, lapses=0, fsrs_state="Learning",
                  memory_strength=0.0, total_reviews=0)
    topic.apply_fsrs(GOOD)
    topic.apply_fsrs(GOOD)
    assert topic.lapses == 0
    topic.apply_fsrs(AGAIN)
    assert topic.lapses == 1
    topic.apply_fsrs(AGAIN)
    assert topic.lapses == 2
