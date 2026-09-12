"""
Tests for model_router — tier resolution, per-task cap (A7), catalog integrity.
"""
import pytest

from backend.services import model_router as mr
from backend.services.model_router import (
    TASK_TIER_CAP,
    TASK_TIER_FLOOR,
    _effective_tier,
    get_model_for_task,
)


class TestEffectiveTier:
    """A7: explicit arg > per-task floor/cap > global tier. A cap only ever
    downgrades from the global tier; a floor (2026-09-12) only ever upgrades."""

    def test_explicit_tier_overrides_everything(self):
        # Explicit 'best' wins even for a capped task and a cheaper global.
        assert _effective_tier("news", "best", "free") == "best"

    def test_uncapped_task_uses_global(self):
        # "test" has neither a cap nor a floor -> tracks the global tier as-is.
        assert _effective_tier("test", None, "best") == "best"
        assert _effective_tier("test", None, "cheap") == "cheap"

    def test_cap_downgrades_from_higher_global(self):
        # news is capped at cheap; global best -> resolves to cheap.
        assert _effective_tier("news", None, "best") == "cheap"

    def test_cap_is_a_noop_when_global_equals_cap(self):
        assert _effective_tier("news", None, "cheap") == "cheap"

    def test_cap_never_upgrades(self):
        # Global 'free' is cheaper than the cap 'cheap' -> stay on free.
        assert _effective_tier("news", None, "free") == "free"

    def test_global_none_defaults_to_cheap(self):
        # "test" is unfloored/uncapped, so this still reflects the plain default.
        assert _effective_tier("test", None, None) == "cheap"

    def test_floor_upgrades_from_lower_global(self):
        # lesson is floored at best; global cheap -> resolves to best anyway.
        assert _effective_tier("lesson", None, "cheap") == "best"

    def test_floor_is_a_noop_when_global_equals_floor(self):
        assert _effective_tier("lesson", None, "best") == "best"

    def test_floor_never_downgrades(self):
        # Global 'best' is already >= the floor 'best' -> stays best (no-op,
        # not an error) even though "best" can't go any higher.
        assert _effective_tier("lesson", None, "best") == "best"

    def test_explicit_tier_beats_lesson_floor(self):
        # An explicit lower tier can still deliberately downgrade lesson.
        assert _effective_tier("lesson", "cheap", "cheap") == "cheap"


class TestGetModelForTaskWithCap:
    """End-to-end: the cap/floor actually changes the model the router returns."""

    @pytest.fixture
    def openrouter_best(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "best")

    @pytest.fixture
    def openrouter_cheap(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "cheap")

    def test_news_capped_to_cheap_under_global_best(self, openrouter_best):
        # best news would be gemini-2.5-pro; cap forces the cheap news model.
        assert get_model_for_task("news") == "google/gemini-2.5-flash"

    def test_lesson_stays_best_under_global_best(self, openrouter_best):
        assert get_model_for_task("lesson") == "anthropic/claude-sonnet-5"

    def test_explicit_best_beats_news_cap(self, openrouter_best):
        assert get_model_for_task("news", tier="best") == "google/gemini-2.5-pro"

    def test_lesson_floored_to_best_under_global_cheap(self, openrouter_cheap):
        # This is the whole point of the floor (2026-09-12): even on the
        # default "cheap" global tier, lesson generation resolves to Claude.
        assert get_model_for_task("lesson") == "anthropic/claude-sonnet-5"

    def test_other_tasks_unaffected_by_lesson_floor(self, openrouter_cheap):
        # The floor is scoped to "lesson" only — placement/conversation/test
        # must keep tracking the cheap global tier, not silently get bumped.
        assert get_model_for_task("placement") == "google/gemini-2.5-flash-lite"
        assert get_model_for_task("conversation") == "google/gemini-2.5-flash"
        assert get_model_for_task("test") == "deepseek/deepseek-v3.2"

    def test_lesson_floor_falls_back_sensibly_on_gemini_provider(self, monkeypatch):
        # Anthropic isn't reachable via the Gemini Direct API, so "where
        # possible" means: on this provider, the floor still selects the
        # provider's own best-tier lesson model instead of erroring.
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "gemini")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "cheap")
        assert get_model_for_task("lesson") == "gemini-2.5-pro"


class TestCapCatalogIntegrity:
    """Every capped/floored tier must be a real tier, and every resolved model
    must exist in the catalog for the used tasks (guards against a typo)."""

    def test_cap_tiers_are_valid(self):
        assert set(TASK_TIER_CAP.values()) <= {"free", "cheap", "best"}

    def test_floor_tiers_are_valid(self):
        assert set(TASK_TIER_FLOOR.values()) <= {"free", "cheap", "best"}

    def test_capped_tasks_resolve_to_catalog_models(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "best")
        for task in TASK_TIER_CAP:
            model = get_model_for_task(task)
            assert mr.validate_model(model), f"{task} -> {model} not in catalog"

    def test_floored_tasks_resolve_to_catalog_models(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "cheap")
        for task in TASK_TIER_FLOOR:
            model = get_model_for_task(task)
            assert mr.validate_model(model), f"{task} -> {model} not in catalog"
