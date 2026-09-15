"""Regression tests for lesson sections reported broken (2026-09-15):
concept flashcards never created, mixed review unusable, recall too long."""
import json
from unittest.mock import AsyncMock, patch

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.user import User


def _user(db):
    user = User(name="Lesson Fixes", native_language="Polish", target_language="German", cefr_level="A2")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _lesson(db, user, day, content, title=None):
    lesson = Lesson(
        user_id=user.id, day_number=day, title=title or f"Dzień {day}", topic="General",
        content=json.dumps(content), language="German", cefr_level="A2",
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def test_concept_flashcards_read_grammar_from_the_grammar_dict(client, db):
    # Lessons store grammar as content["grammar"]["explanation"]; the endpoint
    # used to look only at top-level keys and always answered "no grammar".
    user = _user(db)
    lesson = _lesson(db, user, 1, {
        "grammar": {
            "topic": "Präsens",
            "explanation": "Regelmäßige Verben: ich kaufe, du kaufst, er kauft.",
            "rule": "Stamm + -e, -st, -t",
            "examples": [{"sentence": "Ich kaufe Brot.", "translation": "Kupuję chleb."}],
        },
    })
    ai = AsyncMock(return_value={"concepts": [
        {"front": "Końcówki Präsens", "back": "-e, -st, -t", "example": "Ich kaufe."},
        {"front": "Temat czasownika", "back": "bezokolicznik bez -en", "example": "kauf-en"},
    ]})
    with patch("backend.routers.lessons._ai_generate_concepts", new=ai):
        r = client.post(f"/api/lessons/{lesson.id}/concept-flashcards", params={"user_id": user.id})

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["created"] == 2
    prompt = ai.await_args.args[0]
    assert "ich kaufe, du kaufst" in prompt and "Stamm + -e" in prompt and "Ich kaufe Brot." in prompt
    fronts = {f.word for f in db.query(Flashcard).filter(Flashcard.user_id == user.id)}
    assert {"Końcówki Präsens", "Temat czasownika"} <= fronts


def test_mixed_review_is_built_from_previous_lessons_vocabulary(client, db):
    user = _user(db)
    _lesson(db, user, 1, {
        "grammar": {"topic": "Einkaufen"},
        "vocabulary": [
            {"word": "kochen", "translation": "gotować"},
            {"word": "das Brot", "translation": "chleb"},
        ],
    })
    # The stored placeholder (topic "General", no answer) is what old lessons contain.
    current = _lesson(db, user, 2, {
        "interleaved_review": [{"topic": "General", "prompt": "Przypomnij sobie 3 słowa", "type": "recall"}],
    })

    r = client.get(f"/api/lessons/{current.id}", params={"user_id": user.id})
    assert r.status_code == 200
    review = r.json()["content"]["interleaved_review"]
    assert {item["answer"] for item in review} == {"kochen", "das Brot"}
    assert all(item["question"].startswith("Jak po niemiecku:") for item in review)
    assert all(item["topic"] == "Einkaufen" for item in review)
    # Stable between reloads (seeded by lesson id).
    again = client.get(f"/api/lessons/{current.id}", params={"user_id": user.id}).json()
    assert again["content"]["interleaved_review"] == review


def test_first_lesson_keeps_its_stored_review_when_there_is_no_history(client, db):
    user = _user(db)
    lesson = _lesson(db, user, 1, {"interleaved_review": []})
    r = client.get(f"/api/lessons/{lesson.id}", params={"user_id": user.id})
    assert r.json()["content"]["interleaved_review"] == []


def test_recall_prompt_asks_for_at_most_three_sentences():
    import inspect

    from backend.services.lesson_generator import daily_lesson

    source = inspect.getsource(daily_lesson)
    assert "Exactly 5 connected sentences" not in source
    assert "2-3 short connected sentences" in source
