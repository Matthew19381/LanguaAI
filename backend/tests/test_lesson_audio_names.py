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


async def test_failed_tts_leaves_no_empty_cached_file(tmp_path, monkeypatch):
    """edge-tts creates the file before audio arrives; a failure must not leave it as 'cached'."""
    import sys
    import types

    calls = []

    class FailingCommunicate:
        def __init__(self, text, voice):
            pass

        async def save(self, path):
            calls.append(path)
            open(path, "wb").close()              # what edge-tts does before it fails
            raise ConnectionError("offline")

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=FailingCommunicate))
    monkeypatch.setattr(audio_service, "AUDIO_DIR", str(tmp_path))
    monkeypatch.setattr(audio_service.asyncio, "sleep", AsyncMock())
    out = tmp_path / "tts_x.mp3"
    with pytest.raises(ConnectionError):
        await audio_service.generate_audio("Guten Tag", "German", str(out))
    assert len(calls) == 3 and list(tmp_path.iterdir()) == []
    assert audio_service.audio_ready(str(out)) is False
    out.write_bytes(b"")                           # a 0-byte file left by the old code
    assert audio_service.audio_ready(str(out)) is False
