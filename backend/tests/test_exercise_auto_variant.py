"""Auto-generate variants when a learner keeps failing one skill (no click).

The signal is the bank's aggregate accuracy for the skill; the spend is bounded
by skill_needs_auto_variant and only ever happens on a live wrong answer.
"""
from unittest.mock import AsyncMock, patch

from backend.models.exercise import Exercise
from backend.services.exercise_service import (
    AUTO_VARIANT_FRESH_TARGET,
    VARIANT_AFTER_TIMES_SEEN,
    create_exercises_from_lesson,
    skill_memorized_needs_variant,
    skill_needs_auto_variant,
)

SKILL = "Perfekt with haben"

LESSON = {
    "exercises": [
        {
            "type": "fill-in-the-blank",
            "instruction": "Uzupełnij",
            "skill_tag": SKILL,
            "feedback": "haben + Partizip II",
            "items": [
                {"prompt": "Ich ___ Kaffee getrunken.", "answer": "habe"},
                {"prompt": "Du ___ Brot gegessen.", "answer": "hast"},
            ],
        },
    ]
}

FAKE_VARIANTS = [
    {"prompt": "Wir ___ Pizza gegessen.", "answer": "haben", "skill_tag": SKILL,
     "exercise_type": "fill-in-the-blank", "instruction": "Uzupełnij", "feedback": "x"},
    {"prompt": "Ihr ___ Wein getrunken.", "answer": "habt", "skill_tag": SKILL,
     "exercise_type": "fill-in-the-blank", "instruction": "Uzupełnij", "feedback": "x"},
]


def _seed(db, uid, habe_seen, habe_correct, hast_seen, hast_correct):
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Food")
    db.commit()
    habe = db.query(Exercise).filter(Exercise.answer == "habe").first()
    hast = db.query(Exercise).filter(Exercise.answer == "hast").first()
    habe.times_seen, habe.times_correct = habe_seen, habe_correct
    hast.times_seen, hast.times_correct = hast_seen, hast_correct
    db.commit()
    return habe, hast


# ── unit: skill_needs_auto_variant ────────────────────────────────────────────

def test_no_skill_tag_never_triggers(db, sample_user):
    assert skill_needs_auto_variant(db, sample_user["user_id"], "German", None) is False


def test_below_min_attempts_does_not_trigger(db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid, habe_seen=1, habe_correct=0, hast_seen=0, hast_correct=0)
    # Only 1 attempt on the skill — not yet a "series"
    assert skill_needs_auto_variant(db, uid, "German", SKILL) is False


def test_good_accuracy_does_not_trigger(db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid, habe_seen=3, habe_correct=3, hast_seen=2, hast_correct=2)
    assert skill_needs_auto_variant(db, uid, "German", SKILL) is False


def test_low_accuracy_with_no_fresh_triggers(db, sample_user):
    uid = sample_user["user_id"]
    # 3 attempts, 0 correct, both items already seen → no fresh material waiting
    _seed(db, uid, habe_seen=2, habe_correct=0, hast_seen=1, hast_correct=0)
    assert skill_needs_auto_variant(db, uid, "German", SKILL) is True


def test_existing_fresh_variants_suppress_trigger(db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid, habe_seen=2, habe_correct=0, hast_seen=1, hast_correct=0)
    # Two unseen variants already await — the learner has material, so don't spend
    for i in range(AUTO_VARIANT_FRESH_TARGET):
        db.add(Exercise(user_id=uid, language="German", cefr_level="A2",
                        skill_tag=SKILL, prompt=f"fresh {i}", answer="x", times_seen=0))
    db.commit()
    assert skill_needs_auto_variant(db, uid, "German", SKILL) is False


# ── endpoint: answer triggers auto-generation ─────────────────────────────────

def test_wrong_answer_on_struggling_skill_auto_generates(client, db, sample_user):
    uid = sample_user["user_id"]
    habe, _ = _seed(db, uid, habe_seen=1, habe_correct=0, hast_seen=1, hast_correct=0)
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)):
        r = client.post(f"/api/exercises/{habe.id}/answer",
                        json={"user_id": uid, "answer": "wrong"})
    data = r.json()
    assert data["correct"] is False
    assert data["auto_generated"] == 2
    assert data["auto_generated_reason"] == "struggle"
    assert data["auto_generated_skill"] == SKILL
    assert len(data["auto_generated_exercises"]) == 2
    # Persisted in the bank for future sessions
    assert db.query(Exercise).filter(Exercise.prompt == "Wir ___ Pizza gegessen.").count() == 1


def test_correct_answer_below_mastery_does_not_generate(client, db, sample_user):
    """A correct answer on an item not yet over-familiar (times_seen < threshold)
    triggers neither path."""
    uid = sample_user["user_id"]
    habe, _ = _seed(db, uid, habe_seen=2, habe_correct=0, hast_seen=1, hast_correct=0)
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)) as mock_gen:
        r = client.post(f"/api/exercises/{habe.id}/answer",
                        json={"user_id": uid, "answer": "habe"})  # correct, seen→3 (<4)
    assert r.json()["correct"] is True
    assert "auto_generated" not in r.json()
    mock_gen.assert_not_called()


def test_good_skill_wrong_answer_does_not_generate(client, db, sample_user):
    uid = sample_user["user_id"]
    habe, _ = _seed(db, uid, habe_seen=3, habe_correct=3, hast_seen=2, hast_correct=2)
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)) as mock_gen:
        r = client.post(f"/api/exercises/{habe.id}/answer",
                        json={"user_id": uid, "answer": "wrong"})
    assert r.json()["correct"] is False
    assert "auto_generated" not in r.json()
    mock_gen.assert_not_called()


# ── mastery / memorization trigger ────────────────────────────────────────────

def test_memorized_needs_variant_unit(db, sample_user):
    uid = sample_user["user_id"]
    _seed(db, uid, habe_seen=VARIANT_AFTER_TIMES_SEEN, habe_correct=VARIANT_AFTER_TIMES_SEEN,
          hast_seen=1, hast_correct=1)
    # Item seen >= threshold, no fresh variants → memorization warrants a variant
    assert skill_memorized_needs_variant(
        db, uid, "German", SKILL, VARIANT_AFTER_TIMES_SEEN) is True
    # Below threshold → no
    assert skill_memorized_needs_variant(db, uid, "German", SKILL, 1) is False
    # No skill tag → no
    assert skill_memorized_needs_variant(db, uid, "German", None, 99) is False


def test_correct_answer_on_memorized_item_auto_generates(client, db, sample_user):
    """A correct answer that pushes an item to the memorization threshold spawns
    fresh same-skill variants (mastery trigger)."""
    uid = sample_user["user_id"]
    # Both items already well-known; habe one short of the threshold
    habe, _ = _seed(db, uid, habe_seen=VARIANT_AFTER_TIMES_SEEN - 1,
                    habe_correct=VARIANT_AFTER_TIMES_SEEN - 1, hast_seen=3, hast_correct=3)
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)):
        r = client.post(f"/api/exercises/{habe.id}/answer",
                        json={"user_id": uid, "answer": "habe"})  # correct → seen hits threshold
    data = r.json()
    assert data["correct"] is True
    assert data["auto_generated"] == 2
    assert data["auto_generated_reason"] == "mastery"
    assert db.query(Exercise).filter(Exercise.prompt == "Wir ___ Pizza gegessen.").count() == 1


def test_mastery_suppressed_when_fresh_variants_exist(client, db, sample_user):
    uid = sample_user["user_id"]
    habe, _ = _seed(db, uid, habe_seen=VARIANT_AFTER_TIMES_SEEN - 1,
                    habe_correct=VARIANT_AFTER_TIMES_SEEN - 1, hast_seen=3, hast_correct=3)
    # Fresh unseen variants already waiting → don't spend
    for i in range(AUTO_VARIANT_FRESH_TARGET):
        db.add(Exercise(user_id=uid, language="German", cefr_level="A2",
                        skill_tag=SKILL, prompt=f"fresh {i}", answer="x", times_seen=0))
    db.commit()
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)) as mock_gen:
        r = client.post(f"/api/exercises/{habe.id}/answer",
                        json={"user_id": uid, "answer": "habe"})
    assert r.json()["correct"] is True
    assert "auto_generated" not in r.json()
    mock_gen.assert_not_called()


def test_offline_replay_never_auto_generates(client, db, sample_user):
    """A replayed offline answer must not spend AI on reconnect."""
    uid = sample_user["user_id"]
    habe, _ = _seed(db, uid, habe_seen=1, habe_correct=0, hast_seen=1, hast_correct=0)
    with patch("backend.routers.exercises.generate_exercise_variants",
               AsyncMock(return_value=FAKE_VARIANTS)) as mock_gen:
        r = client.post(f"/api/exercises/{habe.id}/answer", json={
            "user_id": uid, "answer": "wrong",
            "client_event_id": "evt-replay-1",
            "answered_at": "2026-07-25T10:00:00Z",
        })
    assert r.json()["correct"] is False
    assert "auto_generated" not in r.json()
    mock_gen.assert_not_called()
