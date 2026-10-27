"""Automatic check of a generated German lesson (A7 of the "finished" criterion).

Errors found by hand in earlier lessons (report of 21.10.2026): nouns in the
vocabulary without their article (lesson 8), a wrong Polish translation of a
conjugation table ("ich koste - ja kosztuje"), pronunciation spelt in Polish
letters ("Käse (KĘ-ze)") and an explanation using the wrong pronoun (12, 13).

Three layers, all recorded in ``lesson["quality"]`` so the page can say what
was checked and what is still open:
1. fixed rules: pronunciation in Polish letters is removed; a single
   capitalised vocabulary word without der/die/das is flagged;
2. LanguageTool (optional, LANGUAGETOOL_URL): its matches on the German text
   are passed to the reviewer as hints, because the tool also flags correct
   learner-level sentences;
3. two independent reviewer calls of the model that return exact replacements;
   only a replacement both calls return identically, whose wrong text really
   occurs in the named field, is applied. One call alone wrote new errors on
   real lessons (27.10: "prosimy" -> "proszimy"; a Polish-letter pronunciation
   "KLEIN-gelt" corrected instead of removed) and its answer differs between
   runs, so a single unconfirmed replacement is not trusted.
The reviewer is a language model, not a teacher: it lowers the error rate, it
does not guarantee a correct lesson.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from backend.services.gemini_service import generate_json

logger = logging.getLogger(__name__)

GERMAN = ("german", "deutsch", "niemiecki", "de")
MAX_CORRECTIONS = 20

# Fields whose text is lesson content. Keys outside it (audio cues, tags,
# plan metadata, interleaved review built from old topics) are not checked.
CHECK_KEYS = {
    "pretest", "word", "prompt", "options", "answer",
    "warmup", "content", "activity",
    "vocabulary", "translation", "example_sentence", "example_translation", "mnemonic",
    "grammar", "explanation", "examples", "sentence", "rule", "elaboration_prompt", "elaboration_answer",
    "exercises", "instruction", "items", "feedback",
    "cultural_note", "title",
    "speaking_practice", "sample_answer",
    "writing_exercise", "guidelines", "sample_response",
    "wrap_up", "summary", "preview",
    "output_forcing", "text",
    "dialogue", "lines", "context",
    "comprehensible_input", "questions", "question",
}
# Strings that are German (sent to LanguageTool)
GERMAN_KEYS = {"word", "example_sentence", "sentence", "sample_answer", "sample_response", "text"}

# "(KĘ-ze)", "(GU-ten MOR-gen)": an upper-case syllable joined by hyphens.
# "(Pl.)", "(-e)", "(der/die)" do not match.
_LETTER = "A-Za-zÄÖÜäöüßąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
POLISH_TRANSCRIPTION = re.compile(
    rf"\s*\((?=[^)]*[A-ZĄĆĘŁŃÓŚŹŻ]{{2}})[{_LETTER}]+(?:[- ][{_LETTER}]+)*-[{_LETTER}]+(?:[- ][{_LETTER}]+)*\)"
)
# Pronunciation written as syllables: "KLEIN-geld", "HOJ-te" (an upper-case
# syllable joined by a hyphen). A replacement that keeps such a spelling only
# corrects the transcription instead of removing it.
TRANSCRIPTION_TOKEN = re.compile(rf"\b[A-ZÄÖÜĄĆĘŁŃÓŚŹŻ]{{2,}}-[{_LETTER}]+")
SINGLE_CAPITALISED = re.compile(r"[A-ZÄÖÜ][a-zäöüß]+")
# Capitalised single words that are not nouns, or are used without an article
NOT_A_NOUN = {"Hallo", "Danke", "Bitte", "Tschüss", "Ja", "Nein", "Entschuldigung", "Prost",
              "Servus", "Moin", "Achtung", "Willkommen", "Herzlich"}


def is_german(language: str | None) -> bool:
    return (language or "").lower() in GERMAN


def flatten(lesson: dict) -> dict[str, str]:
    """{"vocabulary.2.word": "Käse", ...} for every checked string field."""
    out: dict[str, str] = {}

    def walk(node, path: str, key_ok: bool):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in CHECK_KEYS:
                    walk(v, f"{path}.{k}" if path else k, True)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}.{i}", key_ok)
        elif isinstance(node, str) and key_ok and node.strip():
            out[path] = node

    walk(lesson, "", False)
    return out


def _set(lesson: dict, path: str, value: str) -> None:
    node = lesson
    parts = path.split(".")
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def strip_polish_transcriptions(lesson: dict) -> list[dict]:
    """Remove pronunciation written in Polish letters; the lesson has audio for that."""
    fixes = []
    for path, text in flatten(lesson).items():
        new = POLISH_TRANSCRIPTION.sub("", text)
        if new != text:
            _set(lesson, path, new)
            fixes.append({"path": path, "wrong": text, "correct": new,
                          "reason": "Wymowa zapisana polskimi literami (usunięta, wymowę daje nagranie)."})
    return fixes


def nouns_without_article(lesson: dict) -> list[dict]:
    issues = []
    for i, item in enumerate(lesson.get("vocabulary") or []):
        word = (item.get("word") or "").strip() if isinstance(item, dict) else ""
        if SINGLE_CAPITALISED.fullmatch(word) and word not in NOT_A_NOUN:
            issues.append({"path": f"vocabulary.{i}.word", "text": word,
                           "issue": "Rzeczownik bez rodzajnika (der/die/das)?"})
    return issues


async def languagetool_hints(lesson: dict, url: str, client: httpx.AsyncClient | None = None) -> list[str]:
    """LanguageTool matches on the German strings, as short hints; [] when off or failing."""
    if not url:
        return []
    german = [(p, t) for p, t in flatten(lesson).items() if p.split(".")[-1] in GERMAN_KEYS]
    hints = []
    owns = client is None
    client = client or httpx.AsyncClient(timeout=10.0)
    try:
        for path, text in german[:60]:
            r = await client.post(url.rstrip("/") + "/check", data={"text": text, "language": "de-DE"})
            r.raise_for_status()
            for m in r.json().get("matches", [])[:3]:
                bad = text[m.get("offset", 0): m.get("offset", 0) + m.get("length", 0)]
                repl = ", ".join(x.get("value", "") for x in (m.get("replacements") or [])[:3])
                hints.append(f"{path}: „{bad}” – {m.get('message', '')}" + (f" (propozycja: {repl})" if repl else ""))
    except Exception as e:  # the check is optional; a lesson is never lost because of it
        logger.warning(f"LanguageTool check skipped: {e}")
    finally:
        if owns:
            await client.aclose()
    return hints


def review_prompt(fields: dict[str, str], flags: list[dict], hints: list[str], native_language: str) -> str:
    flag_lines = "\n".join(f"- {f['path']}: {f['text']}: {f['issue']}" for f in flags) or "- none"
    hint_lines = "\n".join(f"- {h}" for h in hints[:40]) or "- none"
    return f"""You are an experienced teacher of German for {native_language} speakers proofreading a lesson
(level A2-B1) before a learner sees it. Find REAL errors only, do not restyle correct text:
- wrong German: grammar, spelling, wrong article or gender, verb form, word order, case;
- a wrong {native_language} translation of German (also of single conjugated forms, e.g. a table
  "ich koste - ja kosztuję": every person needs its own correct {native_language} form);
- a grammar explanation or rule that is false or uses the wrong word (e.g. "er" where "sie" is meant);
- a vocabulary noun without its article: correct it to "der/die/das Noun";
- pronunciation written in {native_language} letters: remove it (never correct its spelling).
Do not touch correct {native_language} text: change it only when the translation or explanation is
wrong, and keep its spelling exactly as it is everywhere else.

Fields (path: text):
{json.dumps(fields, ensure_ascii=False, indent=0)[:24000]}

Checks that flagged something (may be right or wrong):
{flag_lines}
LanguageTool hints (often false alarms on simple learner sentences):
{hint_lines}

Return JSON {{"corrections": [{{"path": "field path from the list", "wrong": "exact text copied from that field",
"correct": "replacement", "reason": "one short sentence in {native_language}"}}]}}. "wrong" must be
copied exactly and be as short as possible while unique in the field. Empty list if there are no errors.
At most {MAX_CORRECTIONS} corrections."""


def apply_corrections(lesson: dict, corrections) -> tuple[list[dict], list[dict]]:
    """Apply replacements whose wrong text is found in the named field; return (applied, rejected)."""
    applied, rejected = [], []
    if not isinstance(corrections, list):
        return applied, rejected
    for c in corrections[:MAX_CORRECTIONS]:
        if not isinstance(c, dict):
            continue
        path, wrong, correct = c.get("path"), c.get("wrong"), c.get("correct")
        fields = flatten(lesson)
        if not (isinstance(path, str) and isinstance(wrong, str) and isinstance(correct, str)) \
                or path not in fields or not wrong or wrong == correct or wrong not in fields[path] \
                or (TRANSCRIPTION_TOKEN.search(wrong) and TRANSCRIPTION_TOKEN.search(correct)):
            rejected.append(c)
            continue
        _set(lesson, path, fields[path].replace(wrong, correct, 1))
        applied.append({"path": path, "wrong": wrong, "correct": correct, "reason": str(c.get("reason") or "")})
    return applied, rejected


def _key(c) -> tuple | None:
    if not isinstance(c, dict):
        return None
    vals = [c.get(k) for k in ("path", "wrong", "correct")]
    return tuple(v.strip() for v in vals) if all(isinstance(v, str) for v in vals) else None


def confirmed_corrections(first, second) -> tuple[list[dict], int]:
    """Corrections of the first run that the second run returned identically; and how many were not."""
    def items(raw):
        found = (raw or {}).get("corrections") if isinstance(raw, dict) else None
        return found if isinstance(found, list) else []
    second_keys = {_key(c) for c in items(second)} - {None}
    agreed, seen = [], set()
    for c in items(first):
        k = _key(c)
        if k in second_keys and k not in seen:
            seen.add(k)
            agreed.append(c)
    unconfirmed = len({_key(c) for c in items(first) + items(second)} - {None} - seen)
    return agreed, unconfirmed


async def check_lesson(lesson: dict, native_language: str = "Polish", languagetool_url: str = "") -> dict:
    """Run all checks on a German lesson in place and record them in lesson["quality"].

    Called inside generate_daily_lesson, so the review uses the lesson's model.
    """
    fixes = strip_polish_transcriptions(lesson)
    flags = nouns_without_article(lesson)
    hints = await languagetool_hints(lesson, languagetool_url)
    review = "ok"
    applied: list[dict] = []
    unconfirmed = 0
    prompt = review_prompt(flatten(lesson), flags, hints, native_language)
    try:
        first, second = await asyncio.gather(generate_json(prompt), generate_json(prompt))
        agreed, unconfirmed = confirmed_corrections(first, second)
        applied, rejected = apply_corrections(lesson, agreed)
        if rejected or unconfirmed:
            logger.info("Lesson review: %d corrections rejected, %d not confirmed by the second run",
                        len(rejected), unconfirmed)
    except Exception as e:
        logger.error(f"Lesson review failed, lesson kept unchecked by the model: {e}")
        review = "failed"
    open_issues = nouns_without_article(lesson)  # what the reviewer did not fix
    lesson["quality"] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "review": review,
        "languagetool": bool(languagetool_url),
        "corrections": fixes + applied,
        "unconfirmed": unconfirmed,
        "open_issues": open_issues,
    }
    return lesson["quality"]
