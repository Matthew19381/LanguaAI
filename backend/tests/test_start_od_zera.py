"""scripts/start_od_zera.py: the learner's progress goes, the flashcards stay (01.11.2026)."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.models.achievement import Achievement
from backend.models.conversation_session import ConversationSession
from backend.models.exercise import Exercise
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.mock_exam import MockExam
from backend.models.skill_attempt import SkillAttempt
from backend.models.study_plan import StudyPlan
from backend.models.test_result import TestResult
from backend.models.topic import Topic, TopicItem
from backend.models.user import User
from backend.services.curriculum import build_curriculum_plan
from backend.tests.conftest import test_engine

_spec = importlib.util.spec_from_file_location(
    "start_od_zera", Path(__file__).resolve().parents[2] / "scripts" / "start_od_zera.py")
reset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reset)

DB = test_engine.url.database
NOW = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)


def _progress(db, uid):
    """Days 1-4 done on the curriculum plan, with everything a learner leaves behind."""
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(start_day=1)), is_active=True))
    lessons = []
    for day in range(1, 5):
        lesson = Lesson(user_id=uid, day_number=day, title=f"Dzień {day}", topic="x",
                        content=json.dumps({"day": day}), cefr_level="A2", language="German",
                        is_completed=True, completed_at=NOW, created_at=NOW)
        db.add(lesson)
        lessons.append(lesson)
    db.flush()
    db.add(Flashcard(user_id=uid, word="die Kreuzung", translation="skrzyżowanie", language="German",
                     cefr_level="A2", lesson_id=lessons[0].id, lesson_day=1, repetitions=5,
                     stability=12.0, fsrs_state="Review", last_review_date=NOW))
    ex = Exercise(user_id=uid, language="German", prompt="Ich ___ nach Hause.", answer="gehe",
                  first_attempt_incorrect=True, source_lesson_id=lessons[1].id, skill_id="G-V2")
    db.add(ex)
    db.flush()
    db.add(Exercise(user_id=uid, language="German", prompt="p", answer="a", variant_of=ex.id))
    db.add(SkillAttempt(user_id=uid, language="German", skill_id="G-V2", source="exercise",
                        correct=False, exercise_id=ex.id))
    db.add(TestResult(user_id=uid, test_type="placement", score=55, answers="{}", cefr_level="A2",
                      language="German"))
    db.add(ConversationSession(id=f"conv-{uid}", user_id=uid, language="German", native_language="Polish",
                               cefr_level="A2", scenario="{}", system_prompt="s", history="[]"))
    db.add(MockExam(user_id=uid, tasks="{}", status="scored", percent=48.0))
    db.add(Achievement(user_id=uid, achievement_type="first_lesson"))
    topic = Topic(user_id=uid, language="German", name="Präsens", category="grammar")
    db.add(topic)
    db.flush()
    db.add(TopicItem(topic_id=topic.id, item_type="lesson", item_id=lessons[0].id, day_number=1))
    user = db.get(User, uid)
    user.total_xp, user.streak_days = 420, 4
    db.commit()


def _count(db, model, uid):
    db.expire_all()
    return db.query(model).filter(model.user_id == uid).count()


def test_dry_run_changes_nothing(sample_user, db, capsys):
    uid = sample_user["user_id"]
    _progress(db, uid)
    assert reset.main(["--db", DB, "--user", str(uid)]) == 0
    out = capsys.readouterr().out
    assert "lekcje: 4 (ukończone 4)" in out and "Tryb próbny" in out
    assert _count(db, Lesson, uid) == 4 and _count(db, Exercise, uid) == 2


def test_apply_removes_progress_keeps_flashcards_and_next_lesson_is_day_1(client, sample_user, db):
    uid = sample_user["user_id"]
    _progress(db, uid)
    other = client.post("/api/placement/create-user", json={"name": "Inny", "target_language": "German"}).json()
    _progress(db, other["user_id"])

    assert reset.main(["--db", DB, "--user", str(uid), "--apply"]) == 0

    for model in (Lesson, Exercise, SkillAttempt, TestResult, ConversationSession, MockExam, Achievement, Topic):
        assert _count(db, model, uid) == 0, model.__name__
    assert _count(db, Lesson, other["user_id"]) == 4                   # another account is untouched
    card = db.query(Flashcard).filter(Flashcard.user_id == uid).one()
    assert (card.repetitions, card.stability, card.fsrs_state, card.lesson_id) == (5, 12.0, "Review", None)
    user = db.get(User, uid)
    assert (user.total_xp, user.streak_days) == (0, 0)
    plans = db.query(StudyPlan).filter(StudyPlan.user_id == uid).all()
    active = [p for p in plans if p.is_active]
    assert len(plans) == 2 and len(active) == 1
    assert json.loads(active[0].plan_data)["start_day"] == 1

    assert client.get(f"/api/exercises/{uid}/for-hub").json()["exercises"] == []   # hub drops cw-* cards
    cards = client.get(f"/api/flashcards/{uid}", params={"active_only": "false"}).json()["flashcards"]
    assert [c["word"] for c in cards] == ["die Kreuzung"]                      # hub keeps this card
    generated = {"title": "Dzień 1", "vocabulary": [], "grammar": {"topic": "V2", "explanation": "x"},
                 "exercises": []}
    with patch("backend.routers.lessons.generate_daily_lesson", AsyncMock(return_value=generated)) as gen:
        r = client.get(f"/api/lessons/today/{uid}")
    assert r.status_code == 200 and r.json()["day_number"] == 1
    assert gen.call_args.kwargs["day_number"] == 1


def test_unknown_user(sample_user):
    assert reset.main(["--db", DB, "--user", "999999"]) == 2
