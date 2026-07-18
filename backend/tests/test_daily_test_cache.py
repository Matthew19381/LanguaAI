"""Daily test generation must be paid for once, not on every page open."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.lesson import Lesson

GENERATED = {"questions": [{"question": "Was heißt 'Hallo'?", "answer": "Hello"}]}


def _lesson(db, uid):
    lesson = Lesson(
        user_id=uid, day_number=1, title="Today's Lesson", topic="Greetings",
        content=json.dumps({"vocabulary": []}), cefr_level="A1", language="German",
        is_completed=False, created_at=datetime.now(),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def test_daily_test_generated_once_and_reused(client, db, sample_user):
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid)

    gen = AsyncMock(return_value=GENERATED)
    with patch("backend.services.test_generator.generate_daily_test", gen):
        first = client.get(f"/api/tests/daily/{uid}")
        second = client.get(f"/api/tests/daily/{uid}")

    assert first.status_code == 200 and second.status_code == 200
    # The AI generator ran once for two opens of the test page
    assert gen.call_count == 1
    assert first.json()["from_cache"] is False
    assert second.json()["from_cache"] is True
    assert second.json()["questions"] == GENERATED["questions"]

    # And the questions were persisted into the lesson blob
    db.refresh(lesson)
    assert json.loads(lesson.content)["daily_test"]["questions"] == GENERATED["questions"]


@pytest.mark.asyncio
async def test_cache_failure_does_not_break_the_request(db, sample_user):
    """If persisting the cache fails, the learner must still get their test."""
    from backend.services.test_generator import get_or_create_daily_test

    uid = sample_user["user_id"]

    class BadLesson:
        """A lesson whose content cannot be read/written."""
        id = 999

        @property
        def content(self):
            raise ValueError("boom")

    gen = AsyncMock(return_value=GENERATED)
    with patch("backend.services.test_generator.generate_daily_test", gen):
        result = await get_or_create_daily_test(uid, {"vocabulary": []}, db, lesson=BadLesson())

    assert result["questions"] == GENERATED["questions"]
    assert result["from_cache"] is False
