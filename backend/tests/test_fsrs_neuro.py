"""Unit tests for the neuro-FSRS scheduler (backend/services/fsrs_neuro.py)."""
from backend.services.fsrs_neuro import (
    NeuroCardState,
    NeuroFSRSParams,
    calculate_sleep_modulator,
    neuro_fsrs_next_interval,
    neuro_fsrs_params_from_user,
)


def _base_card(**overrides):
    base = dict(
        difficulty=5.0,
        stability=2.0,
        retrievability=0.9,
        interval_days=4,
        repetitions=2,
        sleep_quality=3,
        session_type="day",
    )
    base.update(overrides)
    return NeuroCardState(**base)


def test_sleep_modulator_returns_float_for_all_session_types():
    # Morning branch previously returned None (latent crash bug)
    for st in ("morning", "day", "evening"):
        val = calculate_sleep_modulator(4, st)
        assert isinstance(val, float)
        assert val > 0


def test_morning_high_sleep_boosts_more_than_evening():
    morning = calculate_sleep_modulator(5, "morning")
    evening = calculate_sleep_modulator(5, "evening")
    assert morning > evening


def test_neuro_fsrs_returns_valid_state():
    card = _base_card()
    out = neuro_fsrs_next_interval(card, rating=3, similar_count=1, current_hour=12)
    assert isinstance(out, NeuroCardState)
    assert out.interval_days >= 1
    assert out.state in ("Learning", "Review", "Relearning")
    assert 0.0 <= out.interference_penalty <= 0.3


def test_easy_rating_increases_interval_over_again():
    card = _base_card(stability=3.0, interval_days=3, repetitions=2)
    again = neuro_fsrs_next_interval(card, rating=1, current_hour=12)
    easy = neuro_fsrs_next_interval(card, rating=4, current_hour=12)
    assert easy.interval_days >= again.interval_days


def test_interference_penalty_grows_with_similar_cards():
    card = _base_card()
    low = neuro_fsrs_next_interval(card, rating=3, similar_count=1, current_hour=12)
    high = neuro_fsrs_next_interval(card, rating=3, similar_count=6, current_hour=12)
    assert high.interference_penalty >= low.interference_penalty


def test_params_from_user_default_when_no_weights():
    class DummyUser:
        neuro_weights = None

    params = neuro_fsrs_params_from_user(DummyUser())
    assert isinstance(params, NeuroFSRSParams)
    assert params.sleep_modulator_weight == 0.15


def test_params_from_user_reads_custom_weights():
    class DummyUser:
        neuro_weights = '{"sleep_modulator_weight": 0.3, "time_of_day_weight": 0.2, "interleaving_bonus_weight": 0.1, "interference_penalty_weight": 0.2}'

    params = neuro_fsrs_params_from_user(DummyUser())
    assert params.sleep_modulator_weight == 0.3
    assert params.interference_penalty_weight == 0.2


def test_params_from_user_falls_back_on_bad_json():
    class DummyUser:
        neuro_weights = "not-json"

    params = neuro_fsrs_params_from_user(DummyUser())
    assert params.sleep_modulator_weight == 0.15
