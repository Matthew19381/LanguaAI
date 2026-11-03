"""The next lesson must actually be shaped by the learner's history:
recent mistakes, weak topics, known vocabulary, and recent topics (interleaving).

Existing lesson tests mock generate_daily_lesson wholesale, so they never check
that this context reaches the prompt. These capture the real prompt and assert
the connection.
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.lesson_generator.daily_lesson import (
    generate_daily_lesson,
)

MINIMAL_LESSON = {
    "vocabulary": [{"word": "haben", "translation": "mieć"}],
    "grammar": {"topic": "x", "explanation": "y"},
    "exercises": [],
}


async def _generate_capturing_prompt(**overrides):
    """Run generate_daily_lesson with generate_json mocked to capture the prompt."""
    captured = {}

    async def fake_generate_json(prompt, *a, **k):
        captured["prompt"] = prompt
        return dict(MINIMAL_LESSON)

    kwargs = dict(
        user_id=1, target_language="German", native_language="Polish",
        cefr_level="A1", recent_topics=["Greetings", "Food"], day_number=3, db=None,
        user_errors=[{"question": "Du ___ Brot gegessen.", "user_answer": "habe",
                      "correct_answer": "hast"}],
        weak_topics=["Perfekt with haben"],
        strong_topics=["Numbers"],
        user_vocabulary=["Hallo", "danke"],
    )
    kwargs.update(overrides)
    with patch("backend.services.lesson_generator.daily_lesson.generate_json",
               new=AsyncMock(side_effect=fake_generate_json)):
        result = await generate_daily_lesson(**kwargs)
    return captured.get("prompt", ""), result


@pytest.mark.asyncio
async def test_recent_mistakes_reach_the_prompt():
    prompt, _ = await _generate_capturing_prompt()
    # The learner's previous error (word + correct form) is fed into the lesson
    assert "Recent mistakes" in prompt
    assert "hast" in prompt  # the correct form of the missed answer


@pytest.mark.asyncio
async def test_weak_and_recent_topics_reach_the_prompt():
    prompt, _ = await _generate_capturing_prompt()
    assert "Perfekt with haben" in prompt      # weak topic → extra reinforcement
    assert "Greetings" in prompt and "Food" in prompt  # recent topics
    assert "Numbers" in prompt                 # strong topic (interleave harder)
    assert "Hallo" in prompt                   # known vocabulary (i+1)


@pytest.mark.asyncio
async def test_generated_lesson_stores_no_answerless_recall_prompts():
    """3.11.2026: the questions are built when the lesson is read (lesson_payload)."""
    _, result = await _generate_capturing_prompt()
    assert result["interleaved_review"] == []


@pytest.mark.asyncio
async def test_no_history_still_generates_without_injecting_context():
    prompt, result = await _generate_capturing_prompt(
        recent_topics=[], user_errors=None, weak_topics=None,
        strong_topics=None, user_vocabulary=None,
    )
    # A brand-new learner: no mistakes section, empty interleaving — but a lesson
    assert "Recent mistakes" not in prompt
    assert result["interleaved_review"] == []
    assert "vocabulary" in result
