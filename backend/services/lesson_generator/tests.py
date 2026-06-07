"""Test generation and error analysis."""
import logging
import re
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


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
    grammar = lesson_content.get("explanation", "")[:600]
    dialogue = lesson_content.get("dialogue", {})
    dialogue_lines = dialogue.get("lines", [])[:4] if isinstance(dialogue, dict) else []
    dialogue_sample = "  ".join(f"{l.get('speaker','')}: {l.get('text','')}" for l in dialogue_lines)

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

DIALOGUE EXCERPT:
{dialogue_sample}

REQUIREMENTS — create EXACTLY:
- 4 vocabulary questions: fill-in-the-blank sentences requiring the exact word from the lesson (NO multiple choice)
- 3 grammar questions: multiple choice, test the specific grammar rule from the lesson (include plausible wrong answers)
- 3 translation questions: {native_language}→{language}, student must write the full sentence (no options)
- 2 dialogue questions: multiple choice based on the dialogue context
- 2 application questions: student writes a sentence using a grammar rule or vocabulary word from the lesson (no options)
- 1 bonus error-correction question: give a sentence with 1 error, student writes the corrected version

DIFFICULTY: High. Wrong options must be plausible. Fill-blank and translation questions have no options (student types).
CRITICAL: The answer must NEVER appear literally in the question text.
CRITICAL: For fill_blank type, use ___ (three underscores) exactly ONCE per question. Never two blanks.
CRITICAL: For multiple_choice type, the question stem must be a complete sentence or clear question — NOT a sentence with blanks. Put the blank only if absolutely needed, and then ONLY ONE blank. The options must be single words or short forms (e.g. "A. hat" not "A. hat...geschehen").
CRITICAL: For fill_blank type, add a "hint" field with a short {native_language} hint for the missing word (e.g. the translation or grammar hint like "czas przeszły 'sein'").

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "type": "fill_blank",
            "question": "Sentence with ___ to fill in.",
            "hint": "Short {native_language} hint for the missing word",
            "correct": "exact word",
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
        return await generate_json(prompt)
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

    def _normalize_answer(ans: str, q_type: str) -> str:
        s = str(ans).strip()
        if q_type in ("multiple_choice", "mc"):
            return s.upper()
        s = s.lower()
        s = re.sub(r'[.!?;:]+$', '', s)
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    for q in questions:
        user_ans = answers.get(str(q["id"]), answers.get(q["id"], ""))
        q_type = q.get("type", "unknown")
        is_correct = _normalize_answer(user_ans, q_type) == _normalize_answer(q["correct"], q_type)
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
        correct_ans_display = opts_map.get(str(q["correct"]).upper(), q["correct"])

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
        return await generate_json(prompt)
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

Make each question directly target one of the error patterns above. Focus on:
- Correct forms of words the student got wrong
- Similar constructions to what was answered incorrectly
- Fill-in-the-blank with the correct forms

Rules:
- Each fill_blank question has EXACTLY ONE ___ blank
- Do NOT include the answer in the question text
- Options A/B/C/D for multiple choice questions

Return JSON with MIXED question types — fill_blank has NO options, multiple_choice HAS options:
{{
    "questions": [
        {{
            "id": 1,
            "type": "fill_blank",
            "question": "Sentence with ___ to fill.",
            "correct": "exact word",
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
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating errors test: {e}")
        return await generate_daily_test({}, cefr_level, language, native_language)
