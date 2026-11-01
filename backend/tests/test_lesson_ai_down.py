"""An AI outage must not save a made-up lesson (1.11.2026).

Before: when every attempt raised (no key, no credit, model down) generate_daily_lesson
returned a fixed placeholder ("Hallo", English instructions), which GET /today, POST /next
and the background preparation (0016) saved as the real lesson of that day.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import settings
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.services import lesson_prefetch
from backend.services.curriculum import build_curriculum_plan
from backend.services.lesson_generator.daily_lesson import LessonGenerationError, generate_daily_lesson
from backend.tests.conftest import TestingSessionLocal

DOWN = "backend.services.lesson_generator.daily_lesson.generate_json"


def _plan(db, uid):
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(1)), is_active=True))
    db.commit()


def _count(db, uid):
    db.expire_all()
    return db.query(Lesson).filter(Lesson.user_id == uid).count()


async def test_generator_raises_instead_of_placeholder(db):
    with patch(DOWN, AsyncMock(side_effect=RuntimeError("no key"))) as gen:
        with pytest.raises(LessonGenerationError):
            await generate_daily_lesson(user_id=1, target_language="German", native_language="Polish",
                                        cefr_level="A2", recent_topics=[], day_number=1, db=db)
    assert gen.await_count == 2  # the retry still happens


@pytest.mark.parametrize("call", ["today", "next"])
def test_pages_answer_503_and_save_nothing(client, sample_user, db, call):
    uid = sample_user["user_id"]
    _plan(db, uid)
    with patch(DOWN, AsyncMock(side_effect=RuntimeError("no credit"))):
        r = (client.get(f"/api/lessons/today/{uid}") if call == "today"
             else client.post(f"/api/lessons/next/{uid}"))
    assert r.status_code == 503
    assert "Nic nie zapisano" in r.json()["detail"]
    assert _count(db, uid) == 0


async def test_background_preparation_saves_nothing(sample_user, db, monkeypatch):
    uid = sample_user["user_id"]
    _plan(db, uid)
    monkeypatch.setattr(settings, "PREPARE_NEXT_LESSON", True)
    monkeypatch.setattr(lesson_prefetch, "SessionLocal", TestingSessionLocal)
    with patch(DOWN, AsyncMock(side_effect=RuntimeError("model down"))):
        assert await lesson_prefetch.prepare_next_lesson(uid) is None
    assert _count(db, uid) == 0
