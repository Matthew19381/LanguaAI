"""The study plan must shape the daily lesson.

Before this fix the lesson prompt read only ``focus``/``summary`` from the plan,
keys the plan generator never writes, so no planned topic ever reached a lesson
and every lesson was stored with the topic "General" (17.10.2026: 7 of 7).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.routers.flashcards import public_lesson_topic
from backend.services.lesson_generator.daily_lesson import (
    generate_daily_lesson,
    lesson_topic,
    plan_entry_for_day,
)

# Shape of the stored plan (study_plans.plan_data, as generate_study_plan returns it)
PLAN = {
    "language": "German",
    "cefr_level": "A2",
    "daily_topics": [
        {"day": 1, "grammar_topic": "sein und haben", "vocabulary_theme": "Powitania",
         "conversation_topic": "Poznawanie nowej osoby", "cultural_note": "-"},
        {"day": 3, "grammar_topic": "Szyk zdania oznajmującego",
         "vocabulary_theme": "Kolory i przymiotniki",
         "conversation_topic": "Opisywanie przedmiotów", "cultural_note": "-"},
    ],
    "weekly_goals": [],
    "overall_goal": "B1",
}


async def _generate(day_number=3, plan=PLAN, grammar_topic="Wortstellung"):
    captured = {}

    async def fake_generate_json(prompt, *a, **k):
        captured["prompt"] = prompt
        return {
            "vocabulary": [{"word": "rot", "translation": "czerwony"}],
            "grammar": {"topic": grammar_topic, "explanation": "Czasownik na 2. miejscu."},
            "exercises": [{"type": "translation", "instruction": "x",
                           "items": [{"prompt": "a", "answer": "b"}]}],
        }

    with patch("backend.services.lesson_generator.daily_lesson.generate_json",
               new=AsyncMock(side_effect=fake_generate_json)):
        lesson = await generate_daily_lesson(
            user_id=1, target_language="German", native_language="Polish",
            cefr_level="A2", recent_topics=[], day_number=day_number, db=None,
            study_plan_data=plan,
        )
    return captured["prompt"], lesson


def test_plan_entry_for_day_finds_the_day_and_nothing_past_the_plan():
    assert plan_entry_for_day(PLAN, 3)["grammar_topic"] == "Szyk zdania oznajmującego"
    assert plan_entry_for_day(PLAN, 2) is None
    assert plan_entry_for_day(PLAN, 31) is None
    assert plan_entry_for_day(None, 1) is None
    assert plan_entry_for_day({"daily_topics": "zepsute"}, 1) is None


@pytest.mark.asyncio
async def test_todays_plan_reaches_the_prompt():
    prompt, _ = await _generate(day_number=3)
    assert "TODAY'S STUDY PLAN" in prompt
    assert "Szyk zdania oznajmującego" in prompt
    assert "Kolory i przymiotniki" in prompt
    assert "Opisywanie przedmiotów" in prompt


@pytest.mark.asyncio
async def test_lesson_takes_topic_and_title_from_the_plan():
    _, lesson = await _generate(day_number=3)
    assert lesson["topic"] == "Szyk zdania oznajmującego"
    assert lesson["title"] == "Dzień 3: Kolory i przymiotniki"


@pytest.mark.asyncio
async def test_day_without_plan_entry_uses_the_taught_grammar_topic():
    prompt, lesson = await _generate(day_number=2)
    assert "TODAY'S STUDY PLAN" not in prompt
    assert lesson["topic"] == "Wortstellung"
    assert "title" not in lesson  # persisted as "Dzień N" by create_and_persist_lesson


@pytest.mark.asyncio
async def test_old_focus_key_still_works_without_daily_topics():
    prompt, _ = await _generate(plan={"focus": "Perfekt"}, day_number=1)
    assert "Study plan guidance: Perfekt" in prompt


def test_lesson_topic_falls_back_to_general_only_without_any_grammar():
    assert lesson_topic({"grammar": {}}, None) == "General"
    assert lesson_topic({"grammar": "zepsute"}, None) == "General"
    assert lesson_topic({"grammar": {"topic": " Dativ "}}, None) == "Dativ"


def test_public_lesson_topic_hides_the_general_placeholder():
    assert public_lesson_topic("General") is None
    assert public_lesson_topic(" General ") is None
    assert public_lesson_topic(None) is None
    assert public_lesson_topic("Perfekt") == "Perfekt"


def test_flashcard_list_sends_none_for_general_cards(client, sample_user, db):
    from backend.models.flashcard import Flashcard

    uid = sample_user["user_id"]
    for word in ("Brot", "Zug"):
        r = client.post(f"/api/flashcards/{uid}/add", json={"word": word, "translation": "x"})
        assert r.status_code == 200
    db.query(Flashcard).filter(Flashcard.word == "Brot").update({"lesson_topic": "General"})
    db.query(Flashcard).filter(Flashcard.word == "Zug").update({"lesson_topic": "Reisen"})
    db.commit()

    cards = {c["word"]: c for c in client.get(f"/api/flashcards/{uid}").json()["flashcards"]}
    assert cards["Brot"]["lesson_topic"] is None
    assert cards["Zug"]["lesson_topic"] == "Reisen"


def test_unreviewed_topics_are_not_sent_as_weak():
    from backend.services import lesson_service

    topics = [
        SimpleNamespace(name="Nie powtarzany", memory_strength=0.0, total_reviews=0),
        SimpleNamespace(name="Słaby", memory_strength=0.3, total_reviews=2),
        SimpleNamespace(name="Mocny", memory_strength=0.9, total_reviews=5),
    ]

    class FakeQuery:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def all(self):
            return self.rows

    class FakeDB:
        def query(self, model, *a):
            return FakeQuery(topics if model is lesson_service.Topic else [])

    user = SimpleNamespace(id=1, target_language="German")
    with patch.object(lesson_service, "get_recent_errors", return_value=[]):
        ctx = lesson_service.gather_lesson_context(FakeDB(), user)
    assert ctx["weak_topics"] == ["Słaby"]
    assert ctx["strong_topics"] == ["Mocny"]
