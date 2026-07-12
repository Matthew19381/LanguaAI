import logging
import os
import tempfile
import difflib
import threading

logger = logging.getLogger(__name__)

# Model is downloaded once on first use (~75MB for "tiny")
_whisper_model = None
_whisper_lock = threading.Lock()
WHISPER_MODEL_SIZE = "tiny"

LANGUAGE_CODES = {
    "German": "de",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Polish": "pl",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
}


def _get_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    with _whisper_lock:
        # Double-check after acquiring lock
        if _whisper_model is not None:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}'...")
            _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded.")
        except ImportError:
            logger.error("faster-whisper is not installed. Run: pip install faster-whisper==1.0.3")
            raise
    return _whisper_model


def transcribe_audio(audio_bytes: bytes, audio_format: str = "webm", language: str = "de") -> str:
    """Transcribe audio bytes using faster-whisper. Returns transcribed text."""
    model = _get_model()

    # Write to temp file (delete=True auto-removes on close, but we need the path for Whisper)
    suffix = f".{audio_format}"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(audio_bytes)
        tmp.close()
        segments, info = model.transcribe(tmp.name, beam_size=5, language=language)
        text = " ".join(seg.text.strip() for seg in segments)
        logger.info(f"Transcribed ({info.language}): {text!r}")
        return text.strip()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def score_pronunciation(transcribed: str, target: str) -> dict:
    """Compare transcribed text to target text and return a score 0-100."""
    if not target:
        return {"score": 0, "transcribed": transcribed, "target": target, "feedback": "No target text provided."}

    # Normalize both strings for comparison
    trans_norm = _normalize(transcribed)
    target_norm = _normalize(target)

    if not trans_norm:
        return {
            "score": 0,
            "transcribed": transcribed,
            "target": target,
            "feedback": "No speech detected. Please speak clearly and try again.",
            "word_scores": [],
        }

    # Character-level similarity
    char_ratio = difflib.SequenceMatcher(None, trans_norm, target_norm).ratio()

    # Word-level analysis
    trans_words = trans_norm.split()
    target_words = target_norm.split()
    word_scores = _compare_words(trans_words, target_words)

    word_accuracy = sum(1 for w in word_scores if w["correct"]) / max(len(target_words), 1)

    # Final score: weighted average
    score = round((char_ratio * 0.5 + word_accuracy * 0.5) * 100)
    score = max(0, min(100, score))

    feedback = _generate_feedback(score, word_scores, target_words)

    return {
        "score": score,
        "transcribed": transcribed,
        "target": target,
        "char_similarity": round(char_ratio * 100, 1),
        "word_accuracy": round(word_accuracy * 100, 1),
        "word_scores": word_scores,
        "feedback": feedback,
    }


def _normalize(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _compare_words(trans_words: list, target_words: list) -> list:
    matcher = difflib.SequenceMatcher(None, target_words, trans_words)
    target_covered = {}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        for idx in range(i1, i2):
            word = target_words[idx]
            if tag == "equal":
                target_covered[idx] = {"word": word, "correct": True, "said": word}
            elif tag == "replace" and (j2 - j1) > 0:
                said = trans_words[j1] if j1 < len(trans_words) else ""
                target_covered[idx] = {"word": word, "correct": False, "said": said}
            else:
                target_covered[idx] = {"word": word, "correct": False, "said": ""}

    # Fill in any missing
    for idx, word in enumerate(target_words):
        if idx not in target_covered:
            target_covered[idx] = {"word": word, "correct": False, "said": ""}

    return [target_covered[i] for i in sorted(target_covered.keys())]


def _generate_feedback(score: int, word_scores: list, target_words: list) -> str:
    missed = [w["word"] for w in word_scores if not w["correct"]]

    if score >= 90:
        return "Excellent pronunciation! Very close to perfect."
    elif score >= 75:
        missed_str = ", ".join(missed[:3]) if missed else ""
        return f"Good pronunciation! {'Pay attention to: ' + missed_str if missed_str else ''}"
    elif score >= 50:
        missed_str = ", ".join(missed[:3]) if missed else ""
        return f"Decent attempt. Words to practice: {missed_str}. Try speaking more slowly and clearly."
    else:
        return "Keep practicing! Try to speak clearly, one word at a time. Listen to the audio and repeat."
