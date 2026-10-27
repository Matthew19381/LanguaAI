"""Speech recognition measured on the learner's own voice (A6).

The learner reads 20 fixed German sentences. Each recording is kept with what
the browser's recogniser (Web Speech API, used by the exam, the conversation
and the fluency drill) heard; then every faster-whisper size asked for
(used by the pronunciation trainer) transcribes the same audio. Accuracy is the
word error rate (WER): (substituted + deleted + inserted words) / words of the
sentence, after lower-casing and removing punctuation.

Recordings stay in backend/asr_pomiar/ on the PC (git-ignored).
"""
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.config import REPO_ROOT

logger = logging.getLogger(__name__)

STORE = REPO_ROOT / "backend" / "asr_pomiar"
SESSION_RE = re.compile(r"[A-Za-z0-9-]{8,64}")
AUDIO_FORMATS = {"webm", "ogg", "wav", "mp4", "m4a", "mp3"}
DEFAULT_MODELS = ["tiny", "base", "small"]
ALLOWED_MODELS = {"tiny", "base", "small", "medium"}
# Recommendation rule (my assumption, not from a study): the smallest model
# whose WER is within 2 points of the best one and that needs at most 3 s per
# sentence on this PC, so the trainer still answers right away.
WER_MARGIN = 2.0
MAX_SECONDS = 3.0

# A2-B1 sentences from the exam's topics, with sounds that are hard for Polish
# speakers (ü, ö, ä, ich/ach, h, r, long vowels, compounds).
SENTENCES = [
    "Ich stehe jeden Morgen um halb sieben auf.",
    "Am Wochenende habe ich meine Großeltern besucht.",
    "Können wir uns am Freitag vor dem Kino treffen?",
    "Ich würde lieber mit dem Zug fahren, weil es billiger ist.",
    "Meine Schwester arbeitet seit drei Jahren in München.",
    "Das Wetter war schön, deshalb sind wir an den See gefahren.",
    "Ich muss noch Brötchen, Käse und Milch kaufen.",
    "Wie lange dauert die Fahrt von Hamburg nach Köln?",
    "Für mich ist Gesundheit wichtiger als Geld.",
    "Gestern Abend habe ich zu viel Kuchen gegessen.",
    "Ein Vorteil ist, dass man viel Zeit spart.",
    "Ein Nachteil ist, dass man oft allein arbeitet.",
    "In Polen feiern viele Familien Weihnachten am vierundzwanzigsten Dezember.",
    "Ich habe mich sehr über dein Geschenk gefreut.",
    "Wenn ich mehr Zeit hätte, würde ich öfter Sport machen.",
    "Die Wohnung ist klein, aber sie hat einen schönen Balkon.",
    "Entschuldigung, wo ist hier die nächste Apotheke?",
    "Wir könnten zusammen ein Geschenk für Anna kaufen.",
    "Vielen Dank für Ihre Aufmerksamkeit.",
    "Ich bin nicht sicher, ob das eine gute Idee ist.",
]


def normalize(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def word_errors(reference: str, hypothesis: str) -> tuple[int, int]:
    """(edit distance in words, number of reference words)."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1], len(ref)


def _session_dir(session_id: str) -> Path:
    if not SESSION_RE.fullmatch(session_id or ""):
        raise ValueError("bad session id")
    return STORE / session_id


def save_recording(session_id: str, index: int, audio: bytes, audio_format: str,
                   browser_text: str | None) -> None:
    if not 0 <= index < len(SENTENCES):
        raise ValueError("bad sentence index")
    if audio_format not in AUDIO_FORMATS:
        raise ValueError("bad audio format")
    folder = _session_dir(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{index:02d}.*"):
        old.unlink()  # a re-recorded sentence replaces the old take
    (folder / f"{index:02d}.{audio_format}").write_bytes(audio)
    meta_path = folder / "browser.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta[str(index)] = browser_text
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def recordings(session_id: str) -> dict[int, Path]:
    folder = _session_dir(session_id)
    out = {}
    for p in folder.glob("[0-9][0-9].*") if folder.exists() else []:
        out[int(p.stem)] = p
    return dict(sorted(out.items()))


def _summary(per_sentence: list[dict]) -> dict:
    scored = [s for s in per_sentence if s.get("text") is not None]
    errors = sum(s["errors"] for s in scored)
    words = sum(s["words"] for s in scored)
    seconds = [s["seconds"] for s in scored if s.get("seconds") is not None]
    return {"wer": round(100 * errors / words, 1) if words else None, "sentences": len(scored),
            "avg_seconds": round(sum(seconds) / len(seconds), 2) if seconds else None,
            "per_sentence": per_sentence}


def recommend(results: dict) -> str | None:
    whisper = {m: r for m, r in results.items() if m != "browser" and r.get("wer") is not None}
    if not whisper:
        return None
    best = min(r["wer"] for r in whisper.values())
    order = ["tiny", "base", "small", "medium"]
    for m in sorted(whisper, key=order.index):
        r = whisper[m]
        if r["wer"] <= best + WER_MARGIN and (r["avg_seconds"] or 0) <= MAX_SECONDS:
            return m
    return min(whisper, key=lambda m: whisper[m]["wer"])


def evaluate(session_id: str, models: list[str], transcribe, release=None) -> dict:
    """Score the browser and each Whisper size on the session's recordings.

    ``transcribe(audio_bytes, audio_format, language, model_size)`` is
    pronunciation_service.transcribe_audio (passed in so tests need no model).
    ``release(keep)`` frees the measured models other than the configured one.
    """
    recs = recordings(session_id)
    if not recs:
        raise ValueError("no recordings")
    folder = _session_dir(session_id)
    meta_path = folder / "browser.json"
    browser = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    results: dict[str, dict] = {}
    rows = []
    for i in recs:
        text = browser.get(str(i))
        e, w = word_errors(SENTENCES[i], text) if text is not None else (0, 0)
        rows.append({"index": i, "text": text, "errors": e, "words": w, "seconds": None})
    results["browser"] = _summary(rows)

    for size in models:
        if size not in ALLOWED_MODELS:
            continue
        rows = []
        try:
            # untimed first call: loading (and on the first run downloading) the
            # model must not count as the time per sentence
            first = next(iter(recs.values()))
            transcribe(first.read_bytes(), first.suffix[1:], "de", size)
            for i, path in recs.items():
                start = time.perf_counter()
                text = transcribe(path.read_bytes(), path.suffix[1:], "de", size)
                seconds = time.perf_counter() - start
                e, w = word_errors(SENTENCES[i], text)
                rows.append({"index": i, "text": text, "errors": e, "words": w, "seconds": round(seconds, 2)})
            results[size] = _summary(rows)
        except Exception as ex:  # model missing, download blocked, faster-whisper not installed
            logger.error(f"ASR measurement with whisper '{size}' failed: {ex}")
            results[size] = {"wer": None, "error": str(ex)[:300], "sentences": 0, "avg_seconds": None,
                             "per_sentence": []}
    if release:
        release()

    out = {"session_id": session_id, "measured_at": datetime.now(timezone.utc).isoformat(),
           "recordings": len(recs), "results": results, "recommended_whisper": recommend(results),
           "rule": f"najmniejszy model z WER do {WER_MARGIN} pkt od najlepszego i najwyżej {MAX_SECONDS} s na zdanie"}
    (folder / "wyniki.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def latest() -> dict | None:
    files = sorted(STORE.glob("*/wyniki.json"), key=lambda p: p.stat().st_mtime) if STORE.exists() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None
