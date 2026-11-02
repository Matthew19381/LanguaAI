"""Fair multiple choice and fair checking of written answers (02.11.2026).

Found in the test with the real model (2.11.2026):
- the model puts the right option first: 13 of 20 placement questions and 4 of 5
  daily-test questions had answer A, so answering "A" everywhere scored 65 % in the placement test;
- written answers (translation, sentence, correction, gap) were compared letter by
  letter with the model's one sample answer, so "Ich heiße Marta und komme aus Polen"
  or any other correct sentence of one's own counted as wrong.
"""
import logging
import random
import re

from backend.services.gemini_service import generate_json, json_object

logger = logging.getLogger(__name__)

_OPTION = re.compile(r"^\s*([A-Da-d])\s*[.)]\s*(.*)$", re.S)
MC_TYPES = ("multiple_choice", "mc")


def _key(q: dict) -> str:
    return "correct" if q.get("correct") else "correct_answer"


def shuffle_options(questions: list, rng: random.Random | None = None) -> list:
    """Put each question's options "A. …" – "D. …" in random order and move the key
    with them. Questions in another shape are left as they are."""
    rng = rng or random.Random()
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        opts = q.get("options") or []
        key = _key(q)
        correct = str(q.get(key) or "").strip().upper()
        parsed = [_OPTION.match(str(o)) for o in opts]
        if len(opts) < 2 or not all(parsed) or len(correct) != 1:
            continue
        letters = [m.group(1).upper() for m in parsed]
        if letters != [chr(65 + i) for i in range(len(opts))] or correct not in letters:
            continue
        texts = [m.group(2).strip() for m in parsed]
        right = texts[letters.index(correct)]
        rng.shuffle(texts)
        q["options"] = [f"{chr(65 + i)}. {t}" for i, t in enumerate(texts)]
        q[key] = chr(65 + texts.index(right))
    return questions


def normalize(ans, q_type: str) -> str:
    s = str(ans or "").strip()
    if q_type in MC_TYPES:
        return s.upper()
    s = s.lower().replace("ß", "ss")
    s = re.sub(r"[.!?;:,]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


async def grade_open_answers(items: list, language: str, native_language: str) -> dict:
    """{question id: True/False} for written answers that did not match the sample
    answer. Empty when the model is unavailable (the letter-by-letter result stays)."""
    if not items:
        return {}
    listing = [{"id": i["id"], "type": i["type"], "task": i["question"], "sample_answer": i["expected"],
                "student_answer": i["answer"]} for i in items]
    prompt = f"""You check a {native_language} learner's written {language} answers in a test.
The sample answer is ONE possible correct answer, not the only one.

Mark an answer correct when it does what the task asks and is correct {language}:
- any other correct wording, word order or synonym that fits the task is correct;
- "ss" for "ß", a missing final full stop and a different but correct optional word are correct;
- for a gap (fill_blank) the answer must make the whole sentence correct, read it with the gap filled;
- wrong grammar, wrong spelling of the practised form, a missing required word or an answer in
  {native_language} instead of {language} is wrong;
- an empty answer is wrong.

Answers: {listing}

Return ONLY valid JSON:
{{"verdicts": [{{"id": 1, "correct": true}}]}}"""
    try:
        data = json_object(await generate_json(prompt))
        out = {}
        for v in data.get("verdicts") or []:
            if isinstance(v, dict) and isinstance(v.get("correct"), bool):
                out[str(v.get("id"))] = v["correct"]
        return out
    except Exception as e:  # checking falls back to the exact comparison
        logger.warning("Open answers not checked by the model: %s", e)
        return {}
