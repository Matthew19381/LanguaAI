"""The next lesson must actually be shaped by the learner's history:
recent mistakes, weak topics, known vocabulary, and recent topics (interleaving).

Existing lesson tests mock generate_daily_lesson wholesale, so they never check
that this context reaches the prompt. These capture the real prompt and assert
the connection.
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.lesson_generator.daily_lesson import (
    _build_interleaved_review,
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
async def test_interleaved_review_built_from_recent_topics():
    _, result = await _generate_capturing_prompt()
    review = result["interleaved_review"]
    topics = [item["topic"] for item in review]
    assert "Greetings" in topics and "Food" in topics


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


def test_interleaved_review_caps_at_three_topics():
    review = _build_interleaved_review(["a", "b", "c", "d", "e"])
    assert len(review) == 3
    assert all(item["type"] == "recall" for item in review)


# ── router path: individual exercise mistakes must NOT drive lesson generation ──
# Fine-grained remediation lives in the exercise bank (variants on failure /
# memorization), not in the lesson prompt. Lessons stay adaptive via recent
# topics (interleaving) and test-level weaknesses only.

def test_next_lesson_does_not_feed_exercise_errors_but_keeps_interleaving(client, db, sample_user):
    import json as _json

    from backend.models.lesson import Lesson
    from backend.models.study_plan import StudyPlan

    uid = sample_user["user_id"]
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A1",
                     plan_data=_json.dumps({"weeks": []}), is_active=True))
    prev_content = {
        "vocabulary": [],
        "user_exercise_errors": [
            {"question": "Du ___ Brot gegessen.", "user_answer": "habe",
             "correct_answer": "hast", "exercise_type": "fill-in-the-blank"}
        ],
    }
    db.add(Lesson(user_id=uid, day_number=1, title="Prev", topic="Perfekt",
                  content=_json.dumps(prev_content), cefr_level="A1",
                  language="German", is_completed=True))
    db.commit()

    captured = {}

    async def fake_gen(**kwargs):
        captured.update(kwargs)
        return {"title": "Next", "topic": "T", "vocabulary": [], "exercises": []}

    with patch("backend.routers.lessons.generate_daily_lesson",
               new=AsyncMock(side_effect=fake_gen)):
        r = client.post(f"/api/lessons/next/{uid}")

    assert r.status_code == 200
    # The in-lesson exercise mistake is NOT fed into lesson generation
    errors_blob = _json.dumps(captured.get("user_errors", []), ensure_ascii=False)
    assert "hast" not in errors_blob
    # But interleaving on the previous topic still happens
    assert "Perfekt" in (captured.get("recent_topics") or [])


def test_today_lesson_does_not_feed_exercise_errors(client, db, sample_user):
    """The daily lesson ignores individual in-lesson slips too — only recent
    topics and test errors shape it."""
    import json as _json
    from datetime import datetime, timedelta

    from backend.models.lesson import Lesson
    from backend.models.study_plan import StudyPlan

    uid = sample_user["user_id"]
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A1",
                     plan_data=_json.dumps({"weeks": []}), is_active=True))
    yesterday = datetime.now() - timedelta(days=1)
    db.add(Lesson(
        user_id=uid, day_number=1, title="Prev", topic="Akkusativ",
        content=_json.dumps({"vocabulary": [], "user_exercise_errors": [
            {"question": "Ich sehe ___ Mann.", "user_answer": "der",
             "correct_answer": "den"}]}),
        cefr_level="A1", language="German", is_completed=True,
        created_at=yesterday, completed_at=yesterday,
    ))
    db.commit()

    captured = {}

    async def fake_gen(**kwargs):
        captured.update(kwargs)
        return {"title": "Today", "topic": "T", "vocabulary": [], "exercises": []}

    with patch("backend.routers.lessons.generate_daily_lesson",
               new=AsyncMock(side_effect=fake_gen)):
        r = client.get(f"/api/lessons/today/{uid}")

    assert r.status_code == 200
    errors_blob = _json.dumps(captured.get("user_errors", []), ensure_ascii=False)
    assert "den" not in errors_blob  # in-lesson slip is NOT fed into generation
    assert "Akkusativ" in (captured.get("recent_topics") or [])  # interleaving stays
