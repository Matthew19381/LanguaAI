"""Test generation and error analysis."""
import logging
import re

from backend.services.gemini_service import generate_json, with_model
from backend.services.lesson_generator.answers import MC_TYPES, grade_open_answers, normalize, shuffle_options

logger = logging.getLogger(__name__)


def lesson_grammar_text(lesson_content: dict) -> str:
    """The lesson's grammar point for the test prompt. Lessons keep it under "grammar"
    (topic, rule, explanation); a top-level "explanation" is the old shape. Until 01.11.2026
    only the old key was read, so tests of daily lessons got no grammar at all."""
    g = lesson_content.get("grammar")
    if isinstance(g, dict):
        parts = [g.get("topic"), g.get("rule"), g.get("explanation")]
        text = "\n".join(str(p).strip() for p in parts if isinstance(p, str) and p.strip())
        if text:
            return text[:600]
    return str(lesson_content.get("explanation") or "")[:600]


def lesson_sentences_sample(lesson_content: dict, limit: int = 4) -> str:
    """Target-language sentences of the lesson: dialogue lines when the lesson has a
    dialogue, otherwise the grammar examples and the recall text (daily lessons have no
    dialogue, so the "dialogue" questions used to rest on nothing)."""
    dialogue = lesson_content.get("dialogue")
    lines = dialogue.get("lines", []) if isinstance(dialogue, dict) else dialogue if isinstance(dialogue, list) else []
    out = [f"{l.get('speaker', '')}: {l.get('text', '')}" for l in lines[:limit]
           if isinstance(l, dict) and l.get("text")]
    if out:
        return "  ".join(out)
    g = lesson_content.get("grammar")
    examples = g.get("examples", []) if isinstance(g, dict) else []
    out = [e.get("sentence", "").strip() for e in examples if isinstance(e, dict) and (e.get("sentence") or "").strip()]
    out = out[:limit]
    of = lesson_content.get("output_forcing")
    if isinstance(of, dict) and (of.get("text") or "").strip():
        # always kept: with 5+ examples it was cut off by the limit (01.11.2026)
        out.append(of["text"].strip())
    return "  ".join(out)


@with_model("test")
async def generate_daily_test(
    lesson_content: dict,
    cefr_level: str,
    language: str,
    native_language: str,
) -> dict:
    vocab = lesson_content.get("vocabulary", [])
    topic = lesson_content.get("topic", "general")
    title = lesson_content.get("title", "Today's Lesson")
    grammar = lesson_grammar_text(lesson_content)
    dialogue_sample = lesson_sentences_sample(lesson_content)

    vocab_words = [f"{v.get('word','')} = {v.get('translation','')}" for v in vocab[:12]]

    prompt = f"""You are a strict {language} language examiner. Create a CHALLENGING 15-question test based on today's lesson.

Lesson: {title}
Topic: {topic}
CEFR Level: {cefr_level}
Native language (student): {native_language}

LESSON VOCABULARY (ALL must be tested):
{chr(10).join(vocab_words)}

GRAMMAR TOPIC:
{grammar}

LESSON SENTENCES (dialogue or examples):
{dialogue_sample}

REQUIREMENTS — create EXACTLY:
- 4 vocabulary questions: fill-in-the-blank (NO multiple choice). Each is one natural, everyday sentence
  a person would really say, about the lesson topic, where the context makes only ONE word fit the gap.
  The missing word is one word from LESSON VOCABULARY above (inflected if the sentence needs it).
  For a noun the article stays in the sentence before the gap ("Nach der Arbeit habe ich großen ___."
  is wrong because many words fit; "Ich esse ein Brot, weil ich ___ habe." with answer "Hunger" is right).
- 3 grammar questions: multiple choice, test the specific grammar rule from the lesson (include plausible wrong answers)
- 3 translation questions: {native_language}→{language}, student must write the full sentence (no options)
- 2 context questions: multiple choice based on the lesson sentences above
- 2 application questions: student writes a sentence using a grammar rule or vocabulary word from the lesson (no options)
- 1 bonus error-correction question: give a sentence with 1 error, student writes the corrected version

DIFFICULTY: High. Wrong options must be plausible. Fill-blank and translation questions have no options (student types).
CRITICAL: The answer must NEVER appear literally in the question text.
CRITICAL: For fill_blank type, use ___ (three underscores) exactly ONCE per question. Never two blanks.
CRITICAL: For multiple_choice type, the question stem must be a complete sentence or clear question — NOT a sentence with blanks. Put the blank only if absolutely needed, and then ONLY ONE blank. The options must be single words or short forms (e.g. "A. hat" not "A. hat...geschehen").
CRITICAL: For fill_blank type, the "hint" field is the {native_language} translation of the WHOLE sentence, so the
student knows what the sentence means (e.g. "Jem chleb, bo jestem głodny."); "correct" is only the missing word.

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "type": "fill_blank",
            "question": "Sentence with ___ to fill in.",
            "hint": "{native_language} translation of the whole sentence",
            "correct": "the missing word only",
            "points": 7
        }},
        {{
            "id": 2,
            "type": "multiple_choice",
            "question": "Question?",
            "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
            "correct": "A",
            "points": 6
        }}
    ]
}}

Points should total 100. Types: fill_blank, multiple_choice, translation, application, error_correction."""

    try:
        result = _with_shuffled_options(await generate_json(prompt))
        return clean_fill_blanks(result, vocab_words=[v.get("word", "") for v in vocab if isinstance(v, dict)])
    except Exception as e:
        logger.error(f"Error generating daily test: {e}")
        return {
            "questions": [
                {
                    "id": 1,
                    "type": "vocabulary",
                    "question": f"What is the {language} word for 'Hello'?",
                    "options": ["A. Auf Wiedersehen", "B. Danke", "C. Hallo", "D. Bitte"],
                    "correct": "C",
                    "points": 10,
                }
            ]
        }


_BLANK = re.compile(r"_{3,}")
_ARTICLES = ("der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer", "eines")
_DETERMINER = re.compile(
    r"^(der|die|das|den|dem|des|k?ein|k?eine[nmrs]?|(mein|dein|sein|ihr|unser|eur|euer|ihr)(e[nmrs]?)?"
    r"|dies(e[nmrs]?)?|jed(e[nmrs]?)|welch(e[nmrs]?)|im|am|zum|zur|vom|beim|ins)$")


def _plain(text: str) -> str:
    t = _BLANK.sub(" ", str(text or "")).lower().replace("ß", "ss")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _core(word: str) -> str:
    """A vocabulary word without its article ("das Büro" -> "büro")."""
    parts = _plain(word).split()
    if len(parts) > 1 and parts[0] in _ARTICLES:
        parts = parts[1:]
    return " ".join(parts)


_FOLD = str.maketrans("äöü", "aou")


def _from_vocabulary(answer: str, cores: list[str]) -> bool:
    """The answer is a lesson word, also inflected ("arbeite" for "arbeiten als",
    "Kollegen" for "der Kollege", "fährt" for "fahren"): the same stem. Irregular
    forms ("isst" for "essen") do not pass; such a question is dropped, not shown wrong."""
    a = _core(answer).translate(_FOLD)
    for c in cores:
        words = c.translate(_FOLD).split()
        if not words:
            continue
        if a == " ".join(words):
            return True
        head = words[0]
        if a.startswith(head[:max(4, len(head) - 2)]):
            return True
    return False


def clean_fill_blanks(result, vocab_words: list | None = None, avoid_questions: list | None = None):
    """Gap questions that make sense (3.11.2026, "Nach der Arbeit ist ... groß" with
    the hint "głód"): one gap, a hint, the answer not given away in the sentence, an
    article in the answer moved into the sentence, the answer a lesson word (daily
    test) and no copy of a question the student already had (errors test).
    Other question types are left as they are."""
    if not isinstance(result, dict) or not isinstance(result.get("questions"), list):
        return result
    cores = [_core(w) for w in (vocab_words or []) if w]
    avoid = {_plain(q) for q in (avoid_questions or []) if _plain(q)}
    kept = []
    for q in result["questions"]:
        if not isinstance(q, dict):
            continue
        if q.get("type") == "fill_blank":
            text = str(q.get("question") or "")
            key = "correct" if q.get("correct") else "correct_answer"
            answer = str(q.get(key) or "").strip()
            # the hint is the translation of the whole sentence, not one word
            if len(_BLANK.findall(text)) != 1 or not answer or len(str(q.get("hint") or "").split()) < 3:
                logger.info("Gap question dropped (gap/answer/hint): %s", text)
                continue
            words = answer.split()
            if len(words) == 2 and words[0].lower() in _ARTICLES:
                before = _BLANK.split(text)[0].split()
                if before and _DETERMINER.match(_plain(before[-1])):
                    answer = words[1]          # "Meine ___" + "die Firma" -> "Firma"
                else:
                    art = words[0].capitalize() if not before else words[0].lower()
                    text = _BLANK.sub(art + " ___", text, count=1)
                    answer = words[1]
                q["question"], q[key] = text, answer
            if re.search(r"\b" + re.escape(_plain(answer)) + r"\b", _plain(text)):
                logger.info("Gap question dropped (answer in the sentence): %s", text)
                continue
            if cores and not _from_vocabulary(answer, cores):
                logger.info("Gap question dropped (not a lesson word): %s -> %s", text, answer)
                continue
        if avoid and q.get("type") not in MC_TYPES and _plain(q.get("question")) in avoid:
            logger.info("Question dropped (copy of an old question): %s", q.get("question"))
            continue
        kept.append(q)
    for i, q in enumerate(kept, start=1):
        q["id"] = i
    result["questions"] = kept
    return result


def _with_shuffled_options(result):
    """The model's test with multiple-choice options in random order (answers.py)."""
    if isinstance(result, list):
        result = {"questions": result}
    if isinstance(result, dict):
        shuffle_options(result.get("questions") or [])
    return result


@with_model("test")
async def analyze_test_errors(
    questions: list,
    answers: dict,
    language: str,
    native_language: str,
) -> dict:
    results = []
    total_points = 0
    earned_points = 0

    def _answer(q):
        return answers.get(str(q["id"]), answers.get(q["id"], ""))

    def _expected(q):
        return q.get("correct") or q.get("correct_answer") or ""

    # Written answers that differ from the one sample answer are checked by the model
    # (answers.py); an unavailable model leaves the exact comparison
    to_check = [
        {"id": q["id"], "type": q.get("type", "unknown"), "question": q.get("question", ""),
         "expected": _expected(q), "answer": _answer(q)}
        for q in questions
        if q.get("type", "unknown") not in MC_TYPES and not q.get("options")
        and str(_answer(q)).strip()
        and normalize(_answer(q), q.get("type")) != normalize(_expected(q), q.get("type"))
    ]
    verdicts = await grade_open_answers(to_check, language, native_language)

    for q in questions:
        user_ans = _answer(q)
        q_type = q.get("type", "unknown")
        correct_ans = _expected(q)
        is_correct = normalize(user_ans, q_type) == normalize(correct_ans, q_type)
        if not is_correct and str(q["id"]) in verdicts:
            is_correct = verdicts[str(q["id"])]
        points = q.get("points", 10)
        total_points += points
        if is_correct:
            earned_points += points

        opts = q.get("options", [])
        opts_map = {}
        for opt in opts:
            letter = opt.split(".")[0].strip()
            opts_map[letter.upper()] = opt
        user_ans_display = opts_map.get(str(user_ans).upper(), user_ans)
        correct_ans_display = opts_map.get(str(correct_ans).upper(), correct_ans)

        results.append({
            "question_id": q["id"],
            "type": q.get("type", "unknown"),
            "question": q.get("question", ""),
            "user_answer": user_ans_display,
            "correct_answer": correct_ans_display,
            "is_correct": is_correct,
            "points": points,
        })

    score = (earned_points / total_points * 100) if total_points > 0 else 0
    wrong_answers = [r for r in results if not r["is_correct"]]

    prompt = f"""Analyze these {language} test errors and provide detailed feedback.

Test results:
- Score: {score:.1f}%
- Wrong answers: {wrong_answers}
- Native language of student: {native_language}

For each error, classify the type using one of these specific categories:
- "grammar" — general grammar mistake
- "verb_conjugation" — wrong verb form or tense
- "word_order" — incorrect sentence structure
- "articles" — wrong or missing article (der/die/das, a/an/the)
- "prepositions" — wrong preposition used
- "vocabulary" — wrong word choice or unknown word
- "spelling" — spelling or punctuation error
- "comprehension" — misunderstood the question meaning
- "pronunciation" — phonetic confusion (e.g. similar-sounding words)
- "case" — wrong grammatical case (Nominativ/Akkusativ/Dativ/Genitiv)

IMPORTANT: Write "explanation" and "practice" fields in {native_language}. Keep "question", "user_answer", "correct_answer" in the original language.

Return JSON:
{{
    "score": {score:.1f},
    "errors": [
        {{
            "type": "verb_conjugation",
            "question": "original question text",
            "user_answer": "what the student answered",
            "correct_answer": "the correct answer",
            "explanation": "clear explanation in {native_language} of why it was wrong and what rule applies",
            "practice": "a short practice sentence in {language} the student should try to translate"
        }}
    ],
    "performance_summary": "Overall encouraging feedback message in {native_language}"
}}"""

    try:
        result = await generate_json(prompt)
        result["score"] = score
        return result
    except Exception as e:
        logger.error(f"Error analyzing test errors: {e}")
        errors = []
        for r in wrong_answers:
            errors.append({
                "type": r["type"] if r["type"] != "unknown" else "grammar",
                "question": r["question"],
                "user_answer": r["user_answer"],
                "correct_answer": r["correct_answer"],
                "explanation": f"Poprawna odpowiedź to: {r['correct_answer']}",
                "practice": "Przypomnij sobie tę regułę i spróbuj ponownie.",
            })

        return {
            "score": score,
            "errors": errors,
            "performance_summary": f"Zdobyłeś {score:.1f}%. Przejrzyj błędy i poćwicz te zagadnienia.",
        }


@with_model("test")
async def generate_weekly_test(
    study_plan_data: dict,
    week_number: int,
    cefr_level: str,
    language: str,
    native_language: str,
) -> dict:
    weekly_goals = study_plan_data.get("weekly_goals", [])
    week_goal = {}
    for goal in weekly_goals:
        if goal.get("week") == week_number:
            week_goal = goal
            break

    if not week_goal and weekly_goals:
        week_goal = weekly_goals[(week_number - 1) % len(weekly_goals)]

    daily_topics = study_plan_data.get("daily_topics", [])
    week_topics = [t for t in daily_topics if (week_number - 1) * 7 < t.get("day", 0) <= week_number * 7]

    prompt = f"""Create a comprehensive 25-question weekly review test for Week {week_number} of {language} learning.

Student level: CEFR {cefr_level}
Native language: {native_language}
Week goal: {week_goal.get("goal", "General review")}
Topics covered this week: {week_topics}
Key grammar: {week_goal.get("key_grammar", "Various")}

Create 25 varied questions covering all topics from the week.
Include: 8 vocabulary, 7 grammar, 5 translation, 5 reading comprehension questions.

Return JSON:
{{
    "questions": [
        {{
            "id": 1,
            "type": "vocabulary|grammar|translation|comprehension",
            "question": "Question text",
            "options": ["A. option", "B. option", "C. option", "D. option"],
            "correct": "A",
            "points": 4
        }}
    ]
}}

Points should total 100."""

    try:
        return _with_shuffled_options(await generate_json(prompt))
    except Exception as e:
        logger.error(f"Error generating weekly test: {e}")
        return await generate_daily_test({}, cefr_level, language, native_language)


@with_model("test")
async def generate_errors_test(
    errors: list,
    cefr_level: str,
    language: str,
    native_language: str,
) -> dict:
    """Generate a test targeting the user's specific error patterns."""
    error_lines = []
    for e in errors[:15]:
        q = e.get("question", "")
        ua = e.get("user_answer", "")
        ca = e.get("correct_answer", "")
        t = e.get("type", "")
        if ca:
            error_lines.append(f"- [{t}] {q} | Uczeń napisał: '{ua}' | Poprawnie: '{ca}'")

    errors_str = "\n".join(error_lines) if error_lines else "Brak szczegółów błędów."

    prompt = f"""Create a 10-question remediation test in {language} targeting these specific errors:

{errors_str}

CEFR Level: {cefr_level}
Native language: {native_language}

Make each question directly target one of the error patterns above with a NEW sentence:
- NEVER copy or lightly reword a question listed above; practise the same rule or word in a different sentence
- Correct forms of words the student got wrong, in new contexts
- Fill-in-the-blank with the correct forms

Rules:
- Each fill_blank question has EXACTLY ONE ___ blank, one natural sentence where only one word fits
- Each fill_blank question has a "hint": the {native_language} translation of the whole sentence
- Do NOT include the answer in the question text
- Options A/B/C/D for multiple choice questions

Return JSON with MIXED question types — fill_blank has NO options, multiple_choice HAS options:
{{
    "questions": [
        {{
            "id": 1,
            "type": "fill_blank",
            "question": "New sentence with ___ to fill.",
            "hint": "{native_language} translation of the whole sentence",
            "correct": "the missing word only",
            "points": 10
        }},
        {{
            "id": 2,
            "type": "multiple_choice",
            "question": "Choose the correct form:",
            "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
            "correct": "B",
            "points": 10
        }}
    ]
}}

Use at least 5 fill_blank and at most 5 multiple_choice questions. Points total 100."""

    try:
        result = _with_shuffled_options(await generate_json(prompt))
        return clean_fill_blanks(result, avoid_questions=[e.get("question", "") for e in errors if isinstance(e, dict)])
    except Exception as e:
        logger.error(f"Error generating errors test: {e}")
        return await generate_daily_test({}, cefr_level, language, native_language)
