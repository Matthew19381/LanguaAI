"""SCI-3: unit tests for i+1 lexical-coverage validation (Nation 2006)."""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.lesson_generator import daily_lesson
from backend.services.lesson_generator.daily_lesson import (
    COVERAGE_TARGET,
    generate_iplus1_content,
    lexical_coverage,
)

# ── lexical_coverage ─────────────────────────────────────────────────────────

def test_coverage_all_known_is_one():
    assert lexical_coverage("Ich lerne heute viel", known_words=[]) == 1.0


def test_coverage_counts_marked_new_words():
    # 5 tokens, 1 marked new → 4/5 = 0.8
    assert lexical_coverage("Ich habe einen **Regenschirm** gekauft") == pytest.approx(0.8)


def test_known_word_marked_new_is_not_penalised():
    # 'Hund' is marked new but the learner already knows it → coverage 1.0
    cov = lexical_coverage("Der **Hund** rennt", known_words=["Hund"])
    assert cov == 1.0


def test_empty_text_is_zero():
    assert lexical_coverage("", known_words=["a"]) == 0.0


def test_typical_iplus1_text_meets_target():
    # ~120 known tokens + 4 new → well above 0.95
    text = " ".join(["wort"] * 116) + " **neu1** **neu2** **neu3** **neu4**"
    assert lexical_coverage(text) >= COVERAGE_TARGET


# ── generate_iplus1_content regeneration loop ────────────────────────────────

LOW = {"text": "a **x** **y** **z**", "new_words": ["x", "y", "z"]}   # 1/4 = 0.25
HIGH = {"text": "a b c d e f g h i **x**", "new_words": ["x"]}         # 9/10 = 0.9...


@pytest.mark.asyncio
async def test_regenerates_until_target_met():
    good = {"text": " ".join(["w"] * 20) + " **neu**", "new_words": ["neu"]}  # 20/21 ≈ 0.95
    mock = AsyncMock(side_effect=[LOW, good])
    with patch.object(daily_lesson, "generate_json", mock):
        result = await generate_iplus1_content(
            known_words=["w"], target_language="German",
            native_language="Polish", cefr_level="A2",
        )
    assert mock.call_count == 2                      # retried once
    assert result["lexical_coverage"] >= COVERAGE_TARGET
    assert result["coverage_attempts"] == 2


@pytest.mark.asyncio
async def test_returns_best_attempt_after_max_regenerations():
    mid = {"text": "a b c d **x**", "new_words": ["x"]}   # 4/5 = 0.8
    mock = AsyncMock(side_effect=[LOW, LOW, mid])
    with patch.object(daily_lesson, "generate_json", mock):
        result = await generate_iplus1_content(
            known_words=[], target_language="German",
            native_language="Polish", cefr_level="A2",
        )
    assert mock.call_count == 3                       # 1 initial + 2 regenerations
    assert result["lexical_coverage"] == pytest.approx(0.8)  # best of the three


@pytest.mark.asyncio
async def test_all_attempts_raise_returns_fallback():
    mock = AsyncMock(side_effect=Exception("api down"))
    with patch.object(daily_lesson, "generate_json", mock):
        result = await generate_iplus1_content(
            known_words=[], target_language="German",
            native_language="Polish", cefr_level="A2",
        )
    assert "text" in result and result["coverage_attempts"] == 0


# ── GET /api/lessons/iplus1/{user_id} ────────────────────────────────────────

def test_iplus1_endpoint_returns_coverage(client, sample_user):
    uid = sample_user["user_id"]
    fake = {"text": "Ich lerne **neu**", "new_words": ["neu"],
            "questions": [], "cefr_level": "A2", "lexical_coverage": 0.96,
            "coverage_attempts": 1}
    with patch("backend.routers.lessons.generate_iplus1_content",
               AsyncMock(return_value=fake)):
        r = client.get(f"/api/lessons/iplus1/{uid}", params={"topic": "food"})
    assert r.status_code == 200
    assert r.json()["lexical_coverage"] == 0.96


def test_iplus1_endpoint_user_not_found(client):
    r = client.get("/api/lessons/iplus1/99999")
    assert r.status_code == 404
