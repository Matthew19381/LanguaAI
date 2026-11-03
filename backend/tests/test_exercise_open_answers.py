"""Exercises with a slot or an own sentence (a learner's report 3.11.2026: "Ich wohne in
[Twoje miasto]" was the "correct" answer and "Ich wohne in Leipzig" counted as wrong)."""
from unittest.mock import AsyncMock, patch

from backend.models.exercise import Exercise
from backend.services import exercise_service
from backend.services.exercise_service import create_exercises_from_lesson, grade_answer, needs_model_check
from backend.services.lesson_generator import answers

LESSON = {"exercises": [
    {"type": "translation", "instruction": "Przetłumacz", "skill_tag": "G-V2", "feedback": "",
     "items": [{"prompt": "Mieszkam w ...", "answer": "Ich wohne in [Twoje miasto]."},
               {"prompt": "Nazywam się Anna i pochodzę z Polski.", "answer": "Ich heiße Anna und ich komme aus Polen."}]},
    {"type": "fill-in-the-blank", "instruction": "Uzupełnij", "skill_tag": "G-V2", "feedback": "",
     "items": [{"prompt": "Ich ___ müde.", "answer": "bin"}]},
]}


def test_slot_accepts_any_words_but_not_wrong_grammar():
    assert grade_answer("Ich wohne in [Twoje miasto].", "Ich wohne in Leipzig") is True
    assert grade_answer("Ich wohne in [Twoje miasto].", "Ich wohnen in Leipzig") is False
    assert grade_answer("Ich wohne in [Twoje miasto].", "Ich wohne in") is False
    assert grade_answer("Ich bin [liczba] Jahre alt.", "Ich bin 40 Jahre alt.") is True
    assert grade_answer("Ich bin [liczba] Jahre alt.", "Ich bin Jahre alt") is False
    assert grade_answer("Przykład: Ich heiße [imię].", "ich heisse Anna") is True
    assert grade_answer("der Hund / die Katze", "die Katze") is True


def test_only_open_answers_go_to_the_model():
    assert needs_model_check("translation", "Ich bin müde.") is True
    assert needs_model_check("sentence_creation", "Przykład: Der Mann ist jung.") is True
    assert needs_model_check("fill-in-the-blank", "bin") is False
    assert needs_model_check("fill-in-the-blank", "in [Stadt]") is True


def _ex(db, answer):
    return db.query(Exercise).filter(Exercise.answer == answer).first()


def test_endpoint_slot_answer_is_correct_without_model(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Wohnen")
    db.commit()
    ex = _ex(db, "Ich wohne in [Twoje miasto].")
    model = AsyncMock()
    with patch.object(answers, "generate_json", model):
        r = client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "Ich wohne in Leipzig"})
    assert r.json()["correct"] is True and not model.called


def test_endpoint_own_correct_wording_is_checked_by_model(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Wohnen")
    db.commit()
    ex = _ex(db, "Ich heiße Anna und ich komme aus Polen.")
    model = AsyncMock(return_value={"verdicts": [{"id": ex.id, "correct": True}]})
    with patch.object(answers, "generate_json", model):
        r = client.post(f"/api/exercises/{ex.id}/answer",
                        json={"user_id": uid, "answer": "Ich heiße Anna und komme aus Polen"})
    data = r.json()
    assert data["correct"] is True and data["graded_by_model"] is True and data["times_correct"] == 1
    assert "Nazywam się Anna" in model.call_args.args[0]


def test_endpoint_model_says_wrong_or_is_down_keeps_wrong(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Wohnen")
    db.commit()
    ex = _ex(db, "Ich heiße Anna und ich komme aus Polen.")
    with patch.object(answers, "generate_json", AsyncMock(return_value={"verdicts": [{"id": ex.id, "correct": False}]})):
        r = client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "Ich heißen Anna"})
    assert r.json()["correct"] is False
    with patch.object(answers, "generate_json", AsyncMock(side_effect=RuntimeError("down"))):
        r = client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "Ich heiße Anna, komme aus Polen"})
    assert r.json()["correct"] is False


def test_closed_and_replayed_answers_never_call_the_model(client, db, sample_user):
    uid = sample_user["user_id"]
    create_exercises_from_lesson(db, LESSON, uid, "German", "A2", 1, "Wohnen")
    db.commit()
    model = AsyncMock()
    with patch.object(answers, "generate_json", model):
        r = client.post(f"/api/exercises/{_ex(db, 'bin').id}/answer", json={"user_id": uid, "answer": "bist"})
        assert r.json()["correct"] is False
        ex = _ex(db, "Ich heiße Anna und ich komme aus Polen.")
        r = client.post(f"/api/exercises/{ex.id}/answer", json={
            "user_id": uid, "answer": "Ich heiße Anna und komme aus Polen", "client_event_id": "e-1",
            "answered_at": "2026-11-03T10:00:00+00:00"})
        assert r.status_code == 200
    assert not model.called
    assert exercise_service.OPEN_TYPES


def test_unspaced_slash_is_part_of_the_answer():
    assert grade_answer("der/die Kollege/-in", "der") is False
    assert grade_answer("der/die Kollege/-in", "der/die Kollege/-in") is True
    assert grade_answer("kaufe | kaufen", "kaufen") is True
