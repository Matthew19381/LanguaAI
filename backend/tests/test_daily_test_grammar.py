"""The daily test is built from the lesson's own grammar and sentences (01.11.2026)."""
from unittest.mock import AsyncMock, patch

from backend.services.lesson_generator import tests as gen_tests

LESSON = {
    "title": "Dzień 9: Nach dem Weg fragen", "topic": "Wechselpräpositionen",
    "vocabulary": [{"word": "die Kreuzung", "translation": "skrzyżowanie"}],
    "grammar": {"topic": "Wechselpräpositionen", "rule": "Wo? Dativ, wohin? Akkusativ",
                "explanation": "Przyimki zmienne łączą się z celownikiem albo biernikiem.",
                "examples": [{"sentence": "Das Buch liegt auf dem Tisch.", "translation": "x"}]},
    "output_forcing": {"text": "Ich gehe in die Stadt."},
}


async def _prompt(content):
    gen = AsyncMock(return_value={"questions": []})
    with patch.object(gen_tests, "generate_json", gen):
        await gen_tests.generate_daily_test(content, "A2", "German", "Polish")
    return gen.call_args.args[0]


async def test_prompt_carries_the_lessons_grammar_and_sentences():
    prompt = await _prompt(LESSON)
    assert "Wo? Dativ, wohin? Akkusativ" in prompt
    assert "Przyimki zmienne" in prompt
    assert "Das Buch liegt auf dem Tisch." in prompt and "Ich gehe in die Stadt." in prompt


def test_old_shapes_still_work():
    assert gen_tests.lesson_grammar_text({"explanation": "alt"}) == "alt"
    dialogue = {"dialogue": {"lines": [{"speaker": "A", "text": "Hallo!"}]}}
    assert gen_tests.lesson_sentences_sample(dialogue) == "A: Hallo!"
    assert gen_tests.lesson_grammar_text({}) == "" and gen_tests.lesson_sentences_sample({}) == ""
