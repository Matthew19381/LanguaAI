"""A7: automatic check of a generated German lesson, on the errors found by hand
in lessons 8, 12 and 13 (report of 21.10.2026)."""
from unittest.mock import AsyncMock, patch

import httpx

from backend.services import lesson_check as lc


def _lesson():
    return {
        "vocabulary": [
            {"word": "Käse (KĘ-ze)", "translation": "ser", "example_sentence": "Der Käse ist teuer.",
             "audio_cue": "KĘ-ze is not checked here (Pl.)"},
            {"word": "Brot", "translation": "chleb", "example_sentence": "Ich kaufe Brot."},
            {"word": "Hallo", "translation": "cześć"},
            {"word": "die Milch (Pl.)", "translation": "mleko"},
        ],
        "grammar": {"topic": "Präsens",
                    "explanation": "ich koste – ja kosztuje, du kostest – ty kosztuje",
                    "examples": [{"sentence": "Das Brot kostet zwei Euro.", "translation": "Chleb kosztuje dwa euro."}]},
        "interleaved_review": [{"topic": "Käse (KĘ-ze)"}],
        "skill_ids": ["G-PRAES"],
    }


def test_flatten_only_content_fields():
    flat = lc.flatten(_lesson())
    assert flat["vocabulary.0.word"] == "Käse (KĘ-ze)"
    assert flat["grammar.examples.0.sentence"] == "Das Brot kostet zwei Euro."
    assert not any(p.startswith(("interleaved_review", "skill_ids")) or p.endswith("audio_cue") for p in flat)


def test_polish_transcription_removed_but_not_other_brackets():
    lesson = _lesson()
    fixes = lc.strip_polish_transcriptions(lesson)
    assert lesson["vocabulary"][0]["word"] == "Käse"
    assert lesson["vocabulary"][3]["word"] == "die Milch (Pl.)"
    assert [f["path"] for f in fixes] == ["vocabulary.0.word"]
    for keep in ("der Tisch (-e)", "Tisch (der/die)", "kaufen (kupować)"):
        assert lc.POLISH_TRANSCRIPTION.sub("", keep) == keep
    assert lc.POLISH_TRANSCRIPTION.sub("", "Guten Morgen (GU-ten MOR-gen)") == "Guten Morgen"


def test_noun_without_article_flagged_not_interjections():
    issues = lc.nouns_without_article(_lesson())
    assert [i["path"] for i in issues] == ["vocabulary.1.word"]  # "Brot"; "Hallo" and "Käse (…)" not


def test_corrections_applied_only_when_text_is_in_the_field():
    lesson = _lesson()
    applied, rejected = lc.apply_corrections(lesson, [
        {"path": "grammar.explanation", "wrong": "ja kosztuje", "correct": "ja kosztuję", "reason": "1. os."},
        {"path": "vocabulary.1.word", "wrong": "Brot", "correct": "das Brot", "reason": "rodzajnik"},
        {"path": "grammar.explanation", "wrong": "nie ma tego", "correct": "x"},      # not in the field
        {"path": "skill_ids.0", "wrong": "G-PRAES", "correct": "x"},                 # not a content field
        {"path": "grammar.rule", "wrong": "a", "correct": "b"},                      # no such field
        "zepsute",
    ])
    assert lesson["grammar"]["explanation"].startswith("ich koste – ja kosztuję")
    assert lesson["vocabulary"][1]["word"] == "das Brot"
    assert lesson["skill_ids"] == ["G-PRAES"]
    assert len(applied) == 2 and len(rejected) == 3


async def test_check_lesson_records_quality(monkeypatch):
    lesson = _lesson()
    fake = AsyncMock(return_value={"corrections": [
        {"path": "grammar.explanation", "wrong": "ty kosztuje", "correct": "ty kosztujesz", "reason": "2. os."}]})
    monkeypatch.setattr(lc, "generate_json", fake)
    q = await lc.check_lesson(lesson)
    prompt = fake.call_args.args[0]
    assert "vocabulary.1.word: Brot: Rzeczownik bez rodzajnika" in prompt
    assert "Käse (KĘ-ze)" not in prompt  # removed before the review
    assert q["review"] == "ok" and not q["languagetool"]
    assert [c["correct"] for c in q["corrections"]] == ["Käse", "ty kosztujesz"]
    # still flagged for the learner: "Brot" and "Käse" (without the transcription it is a bare noun too)
    assert [i["path"] for i in q["open_issues"]] == ["vocabulary.0.word", "vocabulary.1.word"]


async def test_failed_review_keeps_lesson_and_says_so(monkeypatch):
    monkeypatch.setattr(lc, "generate_json", AsyncMock(side_effect=RuntimeError("no model")))
    lesson = _lesson()
    q = await lc.check_lesson(lesson)
    assert q["review"] == "failed" and lesson["vocabulary"][1]["word"] == "Brot"


async def test_languagetool_hints_and_failure():
    def handler(request):
        text = dict(httpx.QueryParams(request.content.decode()))["text"]
        if "Ich kaufe Brot" in text:
            return httpx.Response(200, json={"matches": [{"offset": 0, "length": 3, "message": "Test",
                                                          "replacements": [{"value": "Wir"}]}]})
        return httpx.Response(200, json={"matches": []})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        hints = await lc.languagetool_hints(_lesson(), "http://lt/v2", client)
    assert hints == ["vocabulary.1.example_sentence: „Ich” – Test (propozycja: Wir)"]

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        assert await lc.languagetool_hints(_lesson(), "http://lt/v2", client) == []
    assert await lc.languagetool_hints(_lesson(), "") == []


async def test_generated_german_lesson_is_checked(monkeypatch):
    """generate_daily_lesson runs the check for German and records it."""
    from backend.services.lesson_generator import daily_lesson as dl
    def lesson():
        return {"vocabulary": [{"word": "Käse (KĘ-ze)", "translation": "ser"}],
                "grammar": {"topic": "x", "explanation": "y"},
                "exercises": [{"type": "translation", "instruction": "x", "items": [{"prompt": "a", "answer": "b"}]}]}
    with patch.object(dl, "generate_json", AsyncMock(return_value=lesson())):
        out = await dl.generate_daily_lesson(user_id=1, target_language="German", native_language="Polish",
                                             cefr_level="A2", recent_topics=[], day_number=1, db=None)
    assert out["vocabulary"][0]["word"] == "Käse" and out["quality"]["review"] == "ok"
    with patch.object(dl, "generate_json", AsyncMock(return_value=lesson())):
        out = await dl.generate_daily_lesson(user_id=1, target_language="Spanish", native_language="Polish",
                                             cefr_level="A2", recent_topics=[], day_number=1, db=None)
    assert "quality" not in out


async def test_only_corrections_confirmed_by_both_runs(monkeypatch):
    """27.10, real lessons 12 and 13: one run wrote "proszimy" and fixed the
    spelling of "KLEIN-gelt" instead of removing it."""
    lesson = _lesson()
    lesson["grammar"]["explanation"] += " Prosimy o rachunek."
    lesson["speaking_practice"] = [{"sample_answer": "Ich habe kein Kleingeld (KLEIN-gelt)."}]
    good = {"path": "grammar.explanation", "wrong": "ty kosztuje", "correct": "ty kosztujesz", "reason": "2. os."}
    invented = {"path": "grammar.explanation", "wrong": "Prosimy", "correct": "Proszimy", "reason": "?"}
    transcription = {"path": "speaking_practice.0.sample_answer", "wrong": "KLEIN-gelt", "correct": "KLEIN-geld",
                     "reason": "pisownia"}
    runs = iter([{"corrections": [good, invented, transcription]},
                 {"corrections": [dict(good, reason="inne słowa"), transcription]}])
    monkeypatch.setattr(lc, "generate_json", AsyncMock(side_effect=lambda *a, **k: next(runs)))
    q = await lc.check_lesson(lesson)
    assert "ty kosztujesz" in lesson["grammar"]["explanation"]
    assert "Prosimy o rachunek" in lesson["grammar"]["explanation"]          # one run only: not applied
    assert "KLEIN-geld" not in lesson["speaking_practice"][0]["sample_answer"]  # transcription not "corrected"
    assert [c["correct"] for c in q["corrections"] if c["path"] == "grammar.explanation"] == ["ty kosztujesz"]
    assert q["unconfirmed"] == 1


def test_confirmed_corrections_handles_bad_answers():
    c = {"path": "a", "wrong": "x", "correct": "y"}
    assert lc.confirmed_corrections({"corrections": [c, "zle"]}, {"corrections": [c]}) == ([c], 0)
    assert lc.confirmed_corrections(None, {"corrections": [c]}) == ([], 1)
    assert lc.confirmed_corrections({"corrections": "nie lista"}, []) == ([], 0)


async def test_one_failed_run_applies_no_model_correction(monkeypatch):
    runs = iter([{"corrections": [{"path": "grammar.explanation", "wrong": "ty kosztuje", "correct": "ty kosztujesz"}]},
                 RuntimeError("timeout")])

    async def fake(*a, **k):
        r = next(runs)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(lc, "generate_json", fake)
    lesson = _lesson()
    q = await lc.check_lesson(lesson)
    assert q["review"] == "failed" and lesson["grammar"]["explanation"].endswith("ty kosztuje")
    assert lesson["vocabulary"][0]["word"] == "Käse"  # fixed rules still applied
