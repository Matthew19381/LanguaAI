"""Audit 01.11.2026: lesson check and ASR measurement (proofs of review A, 3-7)."""
import unicodedata

from backend.services.asr_benchmark import SENTENCES, german_number, word_errors
from backend.services.lesson_check import POLISH_TRANSCRIPTION, apply_corrections, nouns_without_article


def test_correction_of_a_text_that_occurs_twice_is_rejected():
    lesson = {"grammar": {"explanation": "er kostet - on kosztuje; ich koste - ja kosztuje"}}
    applied, rejected = apply_corrections(
        lesson, [{"path": "grammar.explanation", "wrong": "kosztuje", "correct": "kosztuję"}])
    assert not applied and rejected
    assert lesson["grammar"]["explanation"].count("kosztuje") == 2


def test_abbreviations_in_brackets_stay_and_transcriptions_go():
    for keep in ("wiadomość (SMS-y)", "kraj (EU-Land)"):
        assert POLISH_TRANSCRIPTION.sub("", keep) == keep
    assert POLISH_TRANSCRIPTION.sub("", "Käse (KĘ-ze)") == "Käse"
    assert POLISH_TRANSCRIPTION.sub("", "Guten Morgen (GU-ten MOR-gen)") == "Guten Morgen"


def test_place_names_are_not_nouns_missing_an_article():
    lesson = {"vocabulary": [{"word": "Deutschland"}, {"word": "Krakau"}, {"word": "Tisch"}]}
    assert [i["text"] for i in nouns_without_article(lesson)] == ["Tisch"]


def test_wer_ignores_unicode_form_and_digits():
    nfd = unicodedata.normalize("NFD", "Meine Schwester arbeitet seit drei Jahren in München.")
    assert word_errors(SENTENCES[4], nfd)[0] == 0
    assert word_errors(SENTENCES[12], "In Polen feiern viele Familien Weihnachten am 24. Dezember.")[0] == 0
    assert word_errors("Wir treffen uns um halb sieben.", "wir treffen uns um halb 7")[0] == 0
    assert german_number(2026) == "zweitausendsechsundzwanzig"


def test_test_prompt_keeps_the_recall_text_with_many_examples():
    from backend.services.lesson_generator.tests import lesson_sentences_sample
    lesson = {"grammar": {"examples": [{"sentence": f"Satz {i}."} for i in range(6)]},
              "output_forcing": {"text": "Erzähl von deinem Tag."}}
    assert "Erzähl von deinem Tag." in lesson_sentences_sample(lesson)
