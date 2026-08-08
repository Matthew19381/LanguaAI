"""SCI-14: unit tests for the grammar elaborative-interrogation sanitizer (Pressley et al. 1987)."""
from backend.services.lesson_generator.daily_lesson import _sanitize_grammar_elaboration


def test_valid_elaboration_kept():
    grammar = {
        "topic": "Verb position",
        "elaboration_prompt": "Why does the verb move here?",
        "elaboration_answer": "Because finite verbs take second position in main clauses.",
    }
    out = _sanitize_grammar_elaboration(grammar)
    assert out["elaboration_prompt"] == "Why does the verb move here?"
    assert out["elaboration_answer"].startswith("Because")
    assert out["topic"] == "Verb position"  # other grammar fields untouched


def test_missing_prompt_strips_both_fields():
    grammar = {"topic": "X", "elaboration_answer": "Some answer."}
    out = _sanitize_grammar_elaboration(grammar)
    assert "elaboration_prompt" not in out
    assert "elaboration_answer" not in out
    assert out["topic"] == "X"


def test_missing_answer_strips_both_fields():
    grammar = {"topic": "X", "elaboration_prompt": "Why?"}
    out = _sanitize_grammar_elaboration(grammar)
    assert "elaboration_prompt" not in out
    assert "elaboration_answer" not in out


def test_blank_strings_treated_as_missing():
    grammar = {"elaboration_prompt": "   ", "elaboration_answer": ""}
    out = _sanitize_grammar_elaboration(grammar)
    assert "elaboration_prompt" not in out
    assert "elaboration_answer" not in out


def test_fields_are_trimmed():
    grammar = {"elaboration_prompt": "  Why?  ", "elaboration_answer": "  Because.  "}
    out = _sanitize_grammar_elaboration(grammar)
    assert out["elaboration_prompt"] == "Why?"
    assert out["elaboration_answer"] == "Because."


def test_non_dict_grammar_returns_empty_dict():
    assert _sanitize_grammar_elaboration(None) == {}
    assert _sanitize_grammar_elaboration("not a dict") == {}


def test_grammar_without_elaboration_keys_unchanged():
    grammar = {"topic": "X", "rule": "Y"}
    out = _sanitize_grammar_elaboration(grammar)
    assert out == {"topic": "X", "rule": "Y"}
