"""Lesson recordings are named by the spoken text too (01.11.2026): a lesson that gets the
id of a deleted one, or a corrected lesson text, must not reuse an old recording."""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import audio_service


@pytest.fixture
def audio_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_service, "AUDIO_DIR", str(tmp_path))
    spoken = []

    async def fake_generate(text, language, output_path):
        spoken.append((text, language))
        open(output_path, "wb").write(b"mp3")
        return output_path

    monkeypatch.setattr(audio_service, "generate_audio", fake_generate)
    return spoken


async def test_same_id_new_text_gets_a_new_recording(audio_dir):
    old = {"output_forcing": {"text": "Ich wohne in Berlin."}}
    new = {"output_forcing": {"text": "Ich gehe in die Stadt."}}
    a = await audio_service.generate_full_lesson_audio(old, "German", 1)
    b = await audio_service.generate_full_lesson_audio(new, "German", 1)   # same lesson id
    assert a["output_forcing"] != b["output_forcing"]
    assert [t for t, _ in audio_dir] == ["Ich wohne in Berlin.", "Ich gehe in die Stadt."]
    again = await audio_service.generate_full_lesson_audio(new, "German", 1)
    assert again == b and len(audio_dir) == 2                               # still cached


async def test_package_reads_grammar_in_learners_voice_and_lesson_sentences(audio_dir):
    lesson = {"grammar": {"explanation": "Po „weil” czasownik idzie na koniec.",
                          "examples": [{"sentence": "Ich bleibe zu Hause, weil es regnet."}]},
              "vocabulary": [{"word": "der Regen", "translation": "deszcz"}],
              "output_forcing": {"text": "Es regnet heute."}}
    files = await audio_service.generate_lesson_package_audio(lesson, "German", 5, native_language="Polish")
    assert set(files) == {"grammar", "vocabulary", "dialogue"}
    assert ("Po „weil” czasownik idzie na koniec.", "Polish") in audio_dir
    assert ("Ich bleibe zu Hause, weil es regnet.  Es regnet heute.", "German") in audio_dir
