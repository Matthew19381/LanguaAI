"""Fair multiple choice and checking of written answers (test with the real model, 2.11.2026)."""
import random
from unittest.mock import AsyncMock, patch

from backend.services.lesson_generator import answers
from backend.services.lesson_generator import placement as placement_gen
from backend.services.lesson_generator import tests as tests_gen


def _mc(i, right="richtig"):
    return {"id": i, "type": "multiple_choice", "question": f"Frage {i}",
            "options": [f"A. {right}", "B. falsch1", "C. falsch2", "D. falsch3"], "correct": "A", "points": 10}


def test_shuffle_moves_the_key_with_the_option():
    qs = [_mc(i, right=f"richtig{i}") for i in range(1, 41)]
    answers.shuffle_options(qs, random.Random(7))
    letters = [q["correct"] for q in qs]
    assert len(set(letters)) == 4 and letters.count("A") < 20
    for i, q in enumerate(qs, start=1):
        assert q["options"][ord(q["correct"]) - 65] == f"{q['correct']}. richtig{i}"
        assert [o[0] for o in q["options"]] == ["A", "B", "C", "D"]


def test_shuffle_leaves_other_shapes():
    gap = {"id": 1, "type": "fill_blank", "question": "Ich ___ müde.", "correct": "bin"}
    odd = {"id": 2, "type": "multiple_choice", "options": ["ja", "nein"], "correct": "ja"}
    answers.shuffle_options([gap, odd])
    assert gap == {"id": 1, "type": "fill_blank", "question": "Ich ___ müde.", "correct": "bin"}
    assert odd["options"] == ["ja", "nein"] and odd["correct"] == "ja"


async def test_placement_test_is_not_all_answer_a():
    model = {"questions": [dict(_mc(i), cefr_hint="A1") for i in range(1, 21)]}
    with patch.object(placement_gen, "generate_json", AsyncMock(return_value=model)):
        r = await placement_gen.generate_placement_test("German", "Polish")
    assert sum(q["correct"] == "A" for q in r["questions"]) < 20
    assert all(q["options"][ord(q["correct"]) - 65].endswith("richtig") for q in r["questions"])


async def test_daily_test_is_not_all_answer_a():
    model = {"questions": [_mc(i) for i in range(1, 21)]}
    with patch.object(tests_gen, "generate_json", AsyncMock(return_value=model)):
        r = await tests_gen.generate_daily_test({"vocabulary": []}, "A2", "German", "Polish")
    assert sum(q["correct"] == "A" for q in r["questions"]) < 20


QUESTIONS = [
    {"id": 1, "type": "translation", "question": "Przetłumacz: Nazywam się Marta i pochodzę z Polski.",
     "correct_answer": "Ich heiße Marta und ich komme aus Polen.", "points": 10},
    {"id": 2, "type": "application", "question": "Zacznij od 'Heute' i powiedz, że pracujesz w biurze.",
     "correct_answer": "Heute arbeite ich im Büro.", "points": 10},
    {"id": 3, "type": "fill_blank", "question": "Meine ___ hat ihren Sitz in München.",
     "correct_answer": "die Firma", "points": 10},
    _mc(4),
]
ANSWERS = {"1": "Ich heisse Marta und komme aus Polen", "2": "heute arbeite ich im buero.", "3": "Firma", "4": "B"}


async def test_correct_own_wording_counts():
    """Before: only the model's one sample sentence counted (0 % here)."""
    grade = AsyncMock(return_value={"verdicts": [{"id": 1, "correct": True}, {"id": 2, "correct": True},
                                                 {"id": 3, "correct": True}]})
    with patch.object(answers, "generate_json", grade), \
         patch.object(tests_gen, "generate_json", AsyncMock(return_value={"errors": []})):
        r = await tests_gen.analyze_test_errors(QUESTIONS, ANSWERS, "German", "Polish")
    assert r["score"] == 75.0
    sent = grade.call_args.args[0]
    assert "Frage 4" not in sent and "Firma" in sent      # multiple choice is never sent


async def test_wrong_written_answer_stays_wrong_and_model_down_keeps_exact_check():
    grade = AsyncMock(return_value={"verdicts": [{"id": 1, "correct": False}, {"id": 2, "correct": True},
                                                 {"id": 3, "correct": False}]})
    with patch.object(answers, "generate_json", grade), \
         patch.object(tests_gen, "generate_json", AsyncMock(return_value={"errors": []})):
        r = await tests_gen.analyze_test_errors(QUESTIONS, ANSWERS, "German", "Polish")
    assert r["score"] == 25.0
    with patch.object(answers, "generate_json", AsyncMock(side_effect=RuntimeError("down"))), \
         patch.object(tests_gen, "generate_json", AsyncMock(return_value={"errors": []})):
        r = await tests_gen.analyze_test_errors(QUESTIONS, ANSWERS, "German", "Polish")
    assert r["score"] == 0.0


async def test_ss_for_eszett_and_final_stop_need_no_model():
    q = [{"id": 1, "type": "translation", "question": "Nazywam się Anna.", "correct_answer": "Ich heiße Anna.",
          "points": 10}]
    grade = AsyncMock()
    with patch.object(answers, "generate_json", grade), \
         patch.object(tests_gen, "generate_json", AsyncMock(return_value={"errors": []})):
        r = await tests_gen.analyze_test_errors(q, {"1": "ich heisse anna"}, "German", "Polish")
    assert r["score"] == 100.0 and not grade.called
