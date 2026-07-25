"""
Tests for model_router — tier resolution, per-task cap (A7), catalog integrity.
"""
import pytest

from backend.services import model_router as mr
from backend.services.model_router import (
    TASK_TIER_CAP,
    _effective_tier,
    get_model_for_task,
)


class TestEffectiveTier:
    """A7: explicit arg > per-task cap > global tier, cap only ever downgrades."""

    def test_explicit_tier_overrides_everything(self):
        # Explicit 'best' wins even for a capped task and a cheaper global.
        assert _effective_tier("news", "best", "free") == "best"

    def test_uncapped_task_uses_global(self):
        assert _effective_tier("lesson", None, "best") == "best"
        assert _effective_tier("lesson", None, "cheap") == "cheap"

    def test_cap_downgrades_from_higher_global(self):
        # news is capped at cheap; global best -> resolves to cheap.
        assert _effective_tier("news", None, "best") == "cheap"

    def test_cap_is_a_noop_when_global_equals_cap(self):
        assert _effective_tier("news", None, "cheap") == "cheap"

    def test_cap_never_upgrades(self):
        # Global 'free' is cheaper than the cap 'cheap' -> stay on free.
        assert _effective_tier("news", None, "free") == "free"

    def test_global_none_defaults_to_cheap(self):
        assert _effective_tier("lesson", None, None) == "cheap"


class TestGetModelForTaskWithCap:
    """End-to-end: the cap actually changes the model the router returns."""

    @pytest.fixture
    def openrouter_best(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "best")

    def test_news_capped_to_cheap_under_global_best(self, openrouter_best):
        # best news would be gemini-2.5-pro; cap forces the cheap news model.
        assert get_model_for_task("news") == "google/gemini-2.5-flash"

    def test_lesson_stays_best_under_global_best(self, openrouter_best):
        assert get_model_for_task("lesson") == "anthropic/claude-sonnet-4.6"

    def test_explicit_best_beats_news_cap(self, openrouter_best):
        assert get_model_for_task("news", tier="best") == "google/gemini-2.5-pro"


class TestCapCatalogIntegrity:
    """Every capped tier must be a real tier, and every resolved model must
    exist in the catalog for the used tasks (guards against a typo in the cap)."""

    def test_cap_tiers_are_valid(self):
        assert set(TASK_TIER_CAP.values()) <= {"free", "cheap", "best"}

    def test_capped_tasks_resolve_to_catalog_models(self, monkeypatch):
        monkeypatch.setattr(mr.settings, "AI_PROVIDER", "openrouter")
        monkeypatch.setattr(mr.settings, "AI_MODEL_TIER", "best")
        for task in TASK_TIER_CAP:
            model = get_model_for_task(task)
            assert mr.validate_model(model), f"{task} -> {model} not in catalog"
