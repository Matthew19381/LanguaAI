import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# edge-tts voice mapping per language
LANGUAGE_VOICES = {
    "German": "de-DE-KatjaNeural",
    "English": "en-US-JennyNeural",
    "French": "fr-FR-DeniseNeural",
    "Spanish": "es-ES-ElviraNeural",
    "Italian": "it-IT-ElsaNeural",
    "Portuguese": "pt-BR-FranciscaNeural",
    "Dutch": "nl-NL-ColetteNeural",
    "Polish": "pl-PL-ZofiaNeural",
    "Russian": "ru-RU-SvetlanaNeural",
    "Japanese": "ja-JP-NanamiNeural",
    "Chinese": "zh-CN-XiaoxiaoNeural",
    "Korean": "ko-KR-SunHiNeural",
}

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio")


def ensure_audio_dir():
    os.makedirs(AUDIO_DIR, exist_ok=True)


async def generate_audio(text: str, language: str, output_path: str) -> str:
    """Generate audio for the given text using edge-tts. Retries up to 3 times on transient errors."""
    import edge_tts
    ensure_audio_dir()
    voice = LANGUAGE_VOICES.get(language, "de-DE-KatjaNeural")
    last_exc = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await asyncio.wait_for(communicate.save(output_path), timeout=15.0)
            logger.info(f"Audio generated: {output_path}")
            return output_path
        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"edge-tts timed out after 15s (attempt {attempt + 1})")
            logger.warning(f"Audio attempt {attempt + 1}/3 timed out")
        except Exception as e:
            last_exc = e
            logger.warning(f"Audio attempt {attempt + 1}/3 failed: {e}")
        if attempt < 2:
            await asyncio.sleep(0.5 * (2 ** attempt))
    logger.error(f"Error generating audio after 3 attempts: {last_exc}")
    raise last_exc


async def generate_vocabulary_audio(vocabulary: list, language: str, lesson_id: int) -> list:
    """Generate audio for vocabulary words in a lesson."""
    ensure_audio_dir()
    audio_files = []

    for i, vocab_item in enumerate(vocabulary):
        word = vocab_item.get("word", "")
        if not word:
            continue

        filename = f"lesson_{lesson_id}_vocab_{i}_{word[:20].replace(' ', '_')}.mp3"
        output_path = os.path.join(AUDIO_DIR, filename)

        if os.path.exists(output_path):
            audio_files.append({"word": word, "audio_path": f"/audio/{filename}"})
            continue

        try:
            await generate_audio(word, language, output_path)
            audio_files.append({"word": word, "audio_path": f"/audio/{filename}"})
        except Exception as e:
            logger.warning(f"Could not generate audio for word '{word}': {e}")
            audio_files.append({"word": word, "audio_path": None})

    return audio_files


async def generate_dialogue_audio(dialogue_lines: list, language: str, lesson_id: int) -> list:
    """Generate audio for dialogue lines."""
    ensure_audio_dir()
    audio_files = []

    for i, line in enumerate(dialogue_lines):
        text = line.get("text", "")
        speaker = line.get("speaker", "A")
        if not text:
            continue

        filename = f"lesson_{lesson_id}_dialogue_{i}.mp3"
        output_path = os.path.join(AUDIO_DIR, filename)

        if os.path.exists(output_path):
            audio_files.append({"speaker": speaker, "text": text, "audio_path": f"/audio/{filename}"})
            continue

        try:
            await generate_audio(text, language, output_path)
            audio_files.append({"speaker": speaker, "text": text, "audio_path": f"/audio/{filename}"})
        except Exception as e:
            logger.warning(f"Could not generate dialogue audio: {e}")
            audio_files.append({"speaker": speaker, "text": text, "audio_path": None})

    return audio_files


async def generate_flashcard_audio(word: str, language: str, flashcard_id: int) -> str:
    """Generate audio for a single flashcard word."""
    ensure_audio_dir()
    filename = f"flashcard_{flashcard_id}_{word[:20].replace(' ', '_')}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)

    if os.path.exists(output_path):
        return f"/audio/{filename}"

    try:
        await generate_audio(word, language, output_path)
        return f"/audio/{filename}"
    except Exception as e:
        logger.error(f"Error generating flashcard audio: {e}")
        return None


async def generate_full_lesson_audio(lesson_content: dict, language: str, lesson_id: int) -> dict:
    """Generate audio for all lesson sections: vocabulary, dialogue, reading text, output forcing."""
    ensure_audio_dir()
    result = {}

    # Vocabulary words
    vocabulary = lesson_content.get("vocabulary", [])
    if vocabulary:
        try:
            vocab_audio = await generate_vocabulary_audio(vocabulary, language, lesson_id)
            result["vocabulary"] = vocab_audio
        except Exception as e:
            logger.warning(f"Vocab audio failed: {e}")

    # Dialogue lines
    dialogue = lesson_content.get("dialogue", [])
    if dialogue:
        try:
            dialogue_audio = await generate_dialogue_audio(dialogue, language, lesson_id)
            result["dialogue"] = dialogue_audio
        except Exception as e:
            logger.warning(f"Dialogue audio failed: {e}")

    # Reading practice (comprehensible_input)
    ci = lesson_content.get("comprehensible_input", {})
    ci_text = ci.get("text", "") if isinstance(ci, dict) else ""
    if ci_text:
        try:
            filename = f"lesson_{lesson_id}_reading.mp3"
            output_path = os.path.join(AUDIO_DIR, filename)
            if not os.path.exists(output_path):
                await generate_audio(ci_text[:500], language, output_path)
            result["reading"] = f"/audio/{filename}"
        except Exception as e:
            logger.warning(f"Reading audio failed: {e}")

    # Output forcing text
    of = lesson_content.get("output_forcing", {})
    of_text = of.get("text", "") or of.get("sentence", "") if isinstance(of, dict) else ""
    if of_text:
        try:
            filename = f"lesson_{lesson_id}_output_forcing.mp3"
            output_path = os.path.join(AUDIO_DIR, filename)
            if not os.path.exists(output_path):
                await generate_audio(of_text[:300], language, output_path)
            result["output_forcing"] = f"/audio/{filename}"
        except Exception as e:
            logger.warning(f"Output forcing audio failed: {e}")

    return result


async def generate_lesson_package_audio(lesson_content: dict, language: str, lesson_id: int) -> dict:
    """Generate 3 combined audio files for download: Grammar, Vocabulary, Dialog.

    Returns dict with local file paths:
      {"grammar": path, "vocabulary": path, "dialogue": path}
    """
    ensure_audio_dir()
    result = {}

    # 1. Grammar — full explanation text
    explanation = lesson_content.get("explanation", "")
    if explanation:
        filename = f"lesson_{lesson_id}_pkg_gramatyka.mp3"
        output_path = os.path.join(AUDIO_DIR, filename)
        try:
            if not os.path.exists(output_path):
                await generate_audio(explanation[:1500], language, output_path)
            result["grammar"] = output_path
        except Exception as e:
            logger.warning(f"Grammar package audio failed: {e}")

    # 2. Vocabulary — all words + translations read aloud
    vocabulary = lesson_content.get("vocabulary", [])
    if vocabulary:
        parts = []
        for item in vocabulary:
            word = item.get("word", "")
            translation = item.get("translation", "")
            if word:
                parts.append(f"{word}. {translation}." if translation else f"{word}.")
        vocab_text = "  ".join(parts)
        if vocab_text:
            filename = f"lesson_{lesson_id}_pkg_slownictwo.mp3"
            output_path = os.path.join(AUDIO_DIR, filename)
            try:
                if not os.path.exists(output_path):
                    await generate_audio(vocab_text[:1500], language, output_path)
                result["vocabulary"] = output_path
            except Exception as e:
                logger.warning(f"Vocabulary package audio failed: {e}")

    # 3. Dialogue — all lines concatenated
    dialogue = lesson_content.get("dialogue", {})
    lines = dialogue.get("lines", []) if isinstance(dialogue, dict) else dialogue if isinstance(dialogue, list) else []
    if lines:
        parts = []
        for line in lines:
            text = line.get("text", "")
            if text:
                parts.append(text)
        dialogue_text = "  ".join(parts)
        if dialogue_text:
            filename = f"lesson_{lesson_id}_pkg_dialog.mp3"
            output_path = os.path.join(AUDIO_DIR, filename)
            try:
                if not os.path.exists(output_path):
                    await generate_audio(dialogue_text[:1500], language, output_path)
                result["dialogue"] = output_path
            except Exception as e:
                logger.warning(f"Dialogue package audio failed: {e}")

    return result
