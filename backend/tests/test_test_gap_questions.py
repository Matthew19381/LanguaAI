"""Gap questions of the daily test and the errors test (a learner's report 3.11.2026:
"Nach der Arbeit ist ... groß" with the hint "głód"; the errors test repeated the same
questions without hints)."""
from unittest.mock import AsyncMock, patch

from backend.services.lesson_generator import tests as tests_gen
from backend.services.lesson_generator.tests import clean_fill_blanks

VOCAB = ["die Firma", "das Büro", "wohnen", "der Hunger"]


def _gap(question, correct, hint="Tłumaczenie całego zdania tutaj."):
    return {"type": "fill_blank", "question": question, "hint": hint, "correct": correct, "points": 7}


def test_one_word_hint_or_two_gaps_or_no_lesson_word_is_dropped():
    r = clean_fill_blanks({"questions": [
        _gap("Nach der Arbeit ist ___ groß.", "der Hunger", hint="głód"),
        _gap("Ich ___ in ___.", "wohne"),
        _gap("Ich habe ___.", "einen Hund"),
        _gap("Ich ___ in Gdańsk.", "wohne", hint="Mieszkam w Gdańsku."),
    ]}, vocab_words=VOCAB)
    assert [q["question"] for q in r["questions"]] == ["Ich ___ in Gdańsk."]
    assert r["questions"][0]["id"] == 1


def test_article_goes_into_the_sentence_and_answer_is_the_word():
    r = clean_fill_blanks({"questions": [
        _gap("___ ist heute geschlossen.", "das Büro"),
        _gap("Meine ___ hat ihren Sitz in München.", "die Firma"),
    ]}, vocab_words=VOCAB)
    assert [(q["question"], q["correct"]) for q in r["questions"]] == [
        ("Das ___ ist heute geschlossen.", "Büro"), ("Meine ___ hat ihren Sitz in München.", "Firma")]


def test_answer_given_away_in_the_sentence_is_dropped():
    r = clean_fill_blanks({"questions": [_gap("Die Firma ist groß, ich mag die ___.", "Firma")]}, vocab_words=VOCAB)
    assert r["questions"] == []


def test_errors_test_drops_copies_of_old_questions_keeps_multiple_choice():
    old = ["Ich ___ in Gdańsk.", "Choose the correct form:"]
    r = clean_fill_blanks({"questions": [
        _gap("Ich ___ in Gdańsk!", "wohne"),
        _gap("Wir ___ seit zwei Jahren in Polen.", "wohnen"),
        {"type": "multiple_choice", "question": "Choose the correct form:", "options": ["A. a", "B. b"], "correct": "A"},
    ]}, avoid_questions=old)
    assert [q["question"] for q in r["questions"]] == ["Wir ___ seit zwei Jahren in Polen.", "Choose the correct form:"]


async def test_daily_test_prompt_and_cleaning():
    model = AsyncMock(return_value={"questions": [_gap("___ ist heute geschlossen.", "das Büro", hint="biuro"),
                                                  _gap("Mein ___ ist in der Stadtmitte.", "Büro")]})
    with patch.object(tests_gen, "generate_json", model):
        r = await tests_gen.generate_daily_test({"vocabulary": [{"word": w, "translation": "x"} for w in VOCAB]},
                                                "A2", "German", "Polish")
    prompt = model.call_args.args[0]
    assert "translation of the WHOLE sentence" in prompt and "only ONE word fit" in prompt
    assert [q["question"] for q in r["questions"]] == ["Mein ___ ist in der Stadtmitte."]


async def test_errors_test_asks_for_new_sentences_with_hints():
    errors = [{"type": "fill_blank", "question": "Ich ___ in Gdańsk.", "user_answer": "wohnen", "correct_answer": "wohne"}]
    model = AsyncMock(return_value={"questions": [_gap("Ich ___ in Gdańsk.", "wohne"),
                                                  _gap("Du ___ in Berlin, oder?", "wohnst"),
                                                  _gap("Er ___ in Wien.", "wohnt", hint="")]})
    with patch.object(tests_gen, "generate_json", model):
        r = await tests_gen.generate_errors_test(errors, "A2", "German", "Polish")
    prompt = model.call_args.args[0]
    assert "NEVER copy" in prompt and '"hint"' in prompt
    assert [q["question"] for q in r["questions"]] == ["Du ___ in Berlin, oder?"]
