"""P1-3/P1-4 (docs/BACKLOG_UX_2026-08.md): a lesson exercise or grammar
explanation must never reach the user empty. Unit tests for the
server-side filter (_clean_exercises) plus an integration test for the
retry-then-fallback behavior in generate_daily_lesson.
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.lesson_generator.daily_lesson import (
    _clean_exercises,
    generate_daily_lesson,
)


def test_clean_exercises_drops_items_missing_prompt_or_answer():
    exercises = [{
        "type": "fill-in-the-blank",
        "instruction": "Fill in the blank",
        "items": [
            {"prompt": "Ich ___ Anna.", "answer": "heiße"},
            {"prompt": "", "answer": "heiße"},   # missing prompt
            {"prompt": "Du ___ nett.", "answer": ""},  # missing answer
        ],
    }]
    out = _clean_exercises(exercises)
    assert len(out) == 1
    assert len(out[0]["items"]) == 1
    assert out[0]["items"][0]["prompt"] == "Ich ___ Anna."


def test_clean_exercises_drops_block_with_no_good_items():
    exercises = [{
        "type": "translation",
        "instruction": "Translate",
        "items": [{"prompt": "", "answer": ""}],
    }]
    assert _clean_exercises(exercises) == []


def test_clean_exercises_drops_block_missing_instruction():
    exercises = [{
        "type": "translation",
        "instruction": "",
        "items": [{"prompt": "Hello", "answer": "Hallo"}],
    }]
    assert _clean_exercises(exercises) == []


def test_clean_exercises_keeps_matching_pairs_with_delimited_content():
    # Matching blocks cram N pairs into one item as "a / b" <-> "x | y" — that's
    # the model's only way to express multiple pairs, not malformed data.
    exercises = [{
        "type": "matching",
        "instruction": "Match the words",
        "items": [{"prompt": "der Hund / die Katze", "answer": "the dog | the cat"}],
    }]
    out = _clean_exercises(exercises)
    assert len(out) == 1
    assert out[0]["items"][0]["prompt"] == "der Hund / die Katze"


def test_clean_exercises_non_list_input_returns_empty():
    assert _clean_exercises(None) == []
    assert _clean_exercises("not a list") == []
    assert _clean_exercises({}) == []


def _lesson_payload(exercises, explanation):
    return {
        "warmup": {}, "vocabulary": [], "grammar": {"topic": "X", "explanation": explanation},
        "exercises": exercises, "cultural_note": {}, "speaking_practice": [],
        "writing_exercise": {}, "wrap_up": {}, "pretest": [],
    }


@pytest.mark.asyncio
async def test_generate_daily_lesson_retries_once_on_empty_exercises(db):
    incomplete = _lesson_payload(
        exercises=[{"type": "translation", "instruction": "Translate", "items": [{"prompt": "", "answer": ""}]}],
        explanation="A real explanation.",
    )
    complete = _lesson_payload(
        exercises=[{"type": "translation", "instruction": "Translate", "items": [{"prompt": "Hello", "answer": "Hallo"}]}],
        explanation="A real explanation.",
    )
    mock_generate = AsyncMock(side_effect=[incomplete, complete])
    with patch("backend.services.lesson_generator.daily_lesson.generate_json", mock_generate):
        result = await generate_daily_lesson(
            user_id=1, target_language="German", native_language="Polish",
            cefr_level="A1", recent_topics=None, day_number=1, db=db,
        )
    assert mock_generate.call_count == 2
    assert len(result["exercises"]) == 1
    assert result["exercises"][0]["items"][0]["answer"] == "Hallo"


@pytest.mark.asyncio
async def test_generate_daily_lesson_falls_back_to_labeled_explanation_if_still_empty(db):
    always_incomplete = _lesson_payload(exercises=[], explanation="")
    mock_generate = AsyncMock(return_value=always_incomplete)
    with patch("backend.services.lesson_generator.daily_lesson.generate_json", mock_generate):
        result = await generate_daily_lesson(
            user_id=1, target_language="German", native_language="Polish",
            cefr_level="A1", recent_topics=None, day_number=1, db=db,
        )
    # Retried once (2 attempts total), then filled in a labeled fallback
    # rather than shipping a blank explanation.
    assert mock_generate.call_count == 2
    assert result["grammar"]["explanation"].strip() != ""
    assert "X" in result["grammar"]["explanation"]  # references the topic it did get
