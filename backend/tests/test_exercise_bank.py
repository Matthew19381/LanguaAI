"""Exercise bank: persistence, mixing, FSRS scheduling and variant generation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from backend.models.exercise import Exercise
from backend.services.exercise_service import (
    VARIANT_AFTER_TIMES_SEEN,
    create_exercises_from_lesson,
    find_weak_skills,
    flatten_lesson_exercises,
    grade_answer,
)

LESSON = {
    "exercises": [
        {
            "type": "fill-in-the-blank",
            "instruction": "Uzupełnij",
            "skill_tag": "Perfekt with haben",
            "feedback": "haben + Partizip II",
            "items": [
                {"prompt": "Ich ___ Kaffee getrunken.", "answer": "habe"},
                {"prompt": "Du ___ Brot gegessen.", "answer": "hast"},
            ],
        },
        {
            "type": "translation",
            "instruction": "Przetłumacz",
            "skill_tag": "accusative articles",
            "items": [{"prompt": "I see the dog", "answer": "Ich sehe den Hund"}],
        },
    ]
}


# ── flattening ───────────────────────────────────────────────────────────────

def test_flatten_produces_one_item_per_question():
    items = flatten_lesson_exercises(LESSON)
    assert len(items) == 3
    assert items[0]["skill_tag"] == "Perfekt with haben"
    assert items[2]["exercise_type"] == "translation"


def test_flatten_skips_incomplete_items():
    bad = {"exercises": [{"type": "x", "items": [{"prompt": "", "answer": "a"},
                                                 {"prompt": "p", "answer": ""}]}]}
    assert flatten_lesson_exercises(bad) == []


def test_flatten_handles_missing_or_malformed_section():
    assert flatten_lesson_exercises({}) == []
    assert flatten_lesson_exercises({"exercises": "nope"}) == []


# ── persistence ──────────────────────────────────────────────────────────────

def test_exercises_persisted_from_lesson(db, sample_user):
    uid = sample_user["user_id"]
    added = create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    assert added == 3
    rows = db.query(Exercise).filter(Exercise.user_id == uid).all()
    assert len(rows) == 3
    assert {r.skill_tag for r in rows} == {"Perfekt with haben", "accusative articles"}
    assert all(r.topic == "Food" for r in rows)


def test_regenerating_same_lesson_does_not_duplicate(db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    added_again = create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 2, "Food")
    db.commit()
    assert added_again == 0
    assert db.query(Exercise).filter(Exercise.user_id == uid).count() == 3


# ── grading ──────────────────────────────────────────────────────────────────

def test_grading_is_lenient_about_case_and_punctuation():
    assert grade_answer("Ich sehe den Hund", "ich sehe den hund!") is True
    assert grade_answer("habe", "hast") is False
    assert grade_answer("", "anything") is False


# ── weak skills ──────────────────────────────────────────────────────────────

def test_weak_skills_ignores_unpractised_items(db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    # Nothing practised yet → no skill can be called weak
    assert find_weak_skills(db, uid, "German") == []


def test_weak_skills_reports_low_accuracy(db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    for ex in db.query(Exercise).filter(Exercise.skill_tag == "Perfekt with haben").all():
        ex.times_seen, ex.times_correct = 4, 1      # 25% accuracy
    for ex in db.query(Exercise).filter(Exercise.skill_tag == "accusative articles").all():
        ex.times_seen, ex.times_correct = 4, 4      # 100% accuracy
    db.commit()
    weak = find_weak_skills(db, uid, "German")
    assert weak == ["Perfekt with haben"]


# ── practice set endpoint ────────────────────────────────────────────────────

def test_practice_set_returns_due_items(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    r = client.get(f"/api/exercises/{uid}/practice", params={"size": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["due_count"] == 3
    # The answer must not leak into the practice payload
    assert "answer" not in data["exercises"][0]


def test_practice_set_interleaves_other_topics(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    # Push everything into the future so nothing is "due" — only interleaving can fill the set
    future = datetime.now(timezone.utc) + timedelta(days=10)
    for ex in db.query(Exercise).filter(Exercise.user_id == uid).all():
        ex.next_review_date = future
    db.commit()

    r = client.get(f"/api/exercises/{uid}/practice", params={"size": 5, "topic": "Food"})
    data = r.json()
    assert data["due_count"] == 0
    # All bank items belong to topic "Food", which is excluded → nothing to interleave
    assert data["interleaved_count"] == 0

    # An item from a different topic becomes available for interleaving
    db.add(Exercise(user_id=uid, language="German", prompt="Other topic q",
                    answer="a", topic="Travel", next_review_date=future))
    db.commit()
    r2 = client.get(f"/api/exercises/{uid}/practice", params={"size": 5, "topic": "Food"})
    assert r2.json()["interleaved_count"] == 1


def test_practice_set_user_not_found(client):
    assert client.get("/api/exercises/99999/practice").status_code == 404


# ── answering ────────────────────────────────────────────────────────────────

def test_answer_correct_schedules_and_counts(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    ex = db.query(Exercise).filter(Exercise.answer == "habe").first()

    r = client.post(f"/api/exercises/{ex.id}/answer",
                    json={"user_id": uid, "answer": "Habe"})
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is True
    assert data["times_seen"] == 1 and data["times_correct"] == 1
    assert data["interval_days"] >= 1
    assert data["expected_answer"] == "habe"


def test_answer_wrong_does_not_count_as_correct(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    ex = db.query(Exercise).filter(Exercise.answer == "habe").first()
    r = client.post(f"/api/exercises/{ex.id}/answer",
                    json={"user_id": uid, "answer": "hast"})
    data = r.json()
    assert data["correct"] is False
    assert data["times_seen"] == 1 and data["times_correct"] == 0


def test_answer_flags_variant_after_repeated_exposure(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    ex = db.query(Exercise).filter(Exercise.answer == "habe").first()
    ex.times_seen = VARIANT_AFTER_TIMES_SEEN - 1
    db.commit()
    r = client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "habe"})
    assert r.json()["needs_variant"] is True


def test_answer_wrong_user_forbidden(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    ex = db.query(Exercise).first()
    r = client.post(f"/api/exercises/{ex.id}/answer",
                    json={"user_id": uid + 999, "answer": "x"})
    assert r.status_code == 403


# ── variant generation ───────────────────────────────────────────────────────

def test_generate_variants_adds_to_bank(client, db, sample_user):
    uid = sample_user["user_id"]
    fake = [{"prompt": "Wir ___ Pizza gegessen.", "answer": "haben",
             "skill_tag": "Perfekt with haben", "exercise_type": "fill-in-the-blank",
             "instruction": "Uzupełnij", "feedback": "haben + Partizip II"}]
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=fake)):
        r = client.post(f"/api/exercises/{uid}/generate-variants",
                        json={"skills": ["Perfekt with haben"], "per_skill": 1})
    assert r.status_code == 200
    assert r.json()["added"] == 1
    assert db.query(Exercise).filter(Exercise.user_id == uid).count() == 1


def test_generate_variants_without_weak_skills_is_noop(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post(f"/api/exercises/{uid}/generate-variants", json={})
    assert r.status_code == 200
    assert r.json()["added"] == 0


# ── stats ────────────────────────────────────────────────────────────────────

def test_exercise_stats(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    r = client.get(f"/api/exercises/{uid}/stats")
    data = r.json()
    assert data["total"] == 3 and data["due"] == 3 and data["practised"] == 0
