"""SCI-6: dictation activity — listen to a sentence and type what you hear.

Dictation couples listening/decoding with spelling and pushes attention to form
(Nation & Newton 2009, *Teaching ESL/EFL Listening and Speaking*). This module
holds the AI sentence generator and a pure word-level diff used to score the
learner's transcription.
"""
import difflib
import logging
import re

from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize_tokens(text: str) -> list[str]:
    """Lowercase, drop punctuation, split on whitespace."""
    return _PUNCT_RE.sub("", (text or "").lower()).split()


def diff_transcription(reference: str, hypothesis: str) -> dict:
    """Word-level diff between the reference sentence and the learner's typing.

    Returns per-word status (correct / wrong / missing / extra), plus accuracy as
    the share of reference words recalled in the right place.
    """
    ref = _normalize_tokens(reference)
    hyp = _normalize_tokens(hypothesis)
    matcher = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)

    words: list[dict] = []
    correct = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                words.append({"reference": ref[i1 + k], "typed": hyp[j1 + k], "status": "correct"})
                correct += 1
        elif tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                words.append({
                    "reference": ref[i1 + k] if i1 + k < i2 else None,
                    "typed": hyp[j1 + k] if j1 + k < j2 else None,
                    "status": "wrong",
                })
        elif tag == "delete":
            for k in range(i1, i2):
                words.append({"reference": ref[k], "typed": None, "status": "missing"})
        elif tag == "insert":
            for k in range(j1, j2):
                words.append({"reference": None, "typed": hyp[k], "status": "extra"})

    total = len(ref)
    accuracy = round(correct / total * 100, 1) if total else 0.0
    return {
        "accuracy": accuracy,
        "total_words": total,
        "correct_words": correct,
        "words": words,
    }


@with_model("lesson")
async def generate_dictation_sentences(
    target_language: str,
    cefr_level: str,
    count: int = 3,
) -> list[str]:
    """Generate short, self-contained dictation sentences at the learner's level."""
    count = max(1, min(count, 8))
    prompt = f"""Generate {count} short {target_language} sentences for a dictation exercise
at CEFR {cefr_level} level. Each sentence: 5-12 words, natural, self-contained, everyday
vocabulary and grammar appropriate for {cefr_level}. No numbering, no translations.

Return ONLY valid JSON:
{{"sentences": ["sentence 1", "sentence 2"]}}"""
    try:
        data = await generate_json(prompt)
        sentences = data.get("sentences") if isinstance(data, dict) else None
        clean = [s.strip() for s in sentences if isinstance(s, str) and s.strip()]
        if clean:
            return clean[:count]
    except Exception as e:
        logger.error(f"Error generating dictation sentences: {e}")

    # Fallback sentences (German A1-ish) so the activity always works offline
    return [
        "Ich trinke jeden Morgen einen Kaffee.",
        "Das Wetter ist heute sehr schön.",
        "Wir gehen am Wochenende ins Kino.",
    ][:count]
