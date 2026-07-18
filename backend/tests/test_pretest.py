"""SCI-2: unit tests for the pretest sanitizer (Kornell, Hays & Bjork 2009)."""
from backend.services.lesson_generator.daily_lesson import _sanitize_pretest

VOCAB = [{"word": "Hund", "translation": "dog"}, {"word": "Katze", "translation": "cat"}]


def test_valid_item_kept():
    pretest = [{
        "word": "Hund", "prompt": "Guess:",
        "options": ["dog", "cat", "house", "tree"], "answer": "dog",
    }]
    out = _sanitize_pretest(pretest, VOCAB)
    assert len(out) == 1
    assert out[0]["word"] == "Hund" and out[0]["answer"] == "dog"


def test_answer_not_in_options_dropped():
    pretest = [{"word": "Hund", "options": ["cat", "house"], "answer": "dog"}]
    assert _sanitize_pretest(pretest, VOCAB) == []


def test_word_not_in_vocabulary_dropped():
    pretest = [{"word": "Vogel", "options": ["bird", "dog"], "answer": "bird"}]
    assert _sanitize_pretest(pretest, VOCAB) == []


def test_too_few_options_dropped():
    pretest = [{"word": "Hund", "options": ["dog"], "answer": "dog"}]
    assert _sanitize_pretest(pretest, VOCAB) == []


def test_non_list_inputs_return_empty():
    assert _sanitize_pretest(None, VOCAB) == []
    assert _sanitize_pretest([{"word": "Hund", "options": ["dog", "cat"], "answer": "dog"}], None) == []


def test_capped_at_five_items():
    pretest = [
        {"word": "Hund", "options": ["dog", "cat"], "answer": "dog"}
        for _ in range(8)
    ]
    assert len(_sanitize_pretest(pretest, VOCAB)) == 5
