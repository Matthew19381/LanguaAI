"""Placement test generation and analysis."""
import logging
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


@with_model("placement")
async def generate_placement_test(language: str, native_language: str) -> dict:
    prompt = f"""You are a strict certified {language} language examiner. Create a 20-question DIAGNOSTIC placement test for a native {native_language} speaker learning {language}.

GOAL: Correctly distinguish between A1, A2, B1, B2, C1, C2 speakers. Most native {native_language} speakers with NO prior {language} knowledge MUST score at A1 level.

CRITICAL RULES:
1. Questions must test KNOWLEDGE that requires actual study — not guessable by logic, cognates, or similarity to {native_language} or English
2. A1 questions should be IMPOSSIBLE to guess for someone with zero {language} knowledge — use grammar forms, not vocabulary recognition
3. Do NOT use internationally recognizable words (hotel, taxi, radio, internet, restaurant) as correct answers — these are guessable
4. Grammar questions must require knowledge of specific {language} grammatical rules (cases, conjugations, word order)
5. B1 questions should require at least 6+ months of dedicated study
6. fill_blank questions MUST have EXACTLY ONE blank (___) in the sentence
7. translation questions: do NOT include the {language} translation anywhere in the question or options framing
8. Distractor options must be plausible but clearly wrong to anyone who knows the rule
9. For word_order: all options must use the SAME words, only order differs
10. For correct_sentence: exactly 3 of 4 options must have a clear grammatical error

QUESTION DISTRIBUTION (20 questions — do NOT deviate):
- Q1-4: A1 — verb conjugation in present tense (sein/haben/regular verbs), gender of common nouns (der/die/das), basic SVO word order, simple negation (nicht/kein)
- Q5-8: A2 — accusative/dative case endings for articles (den/dem), separable verbs in main clause, Perfekt with haben/sein, common prepositions with cases
- Q9-13: B1 — Konjunktiv II (würde/wäre), subordinate clause word order (weil/dass/ob — verb at end), two-way prepositions (Wechselpräpositionen Dativ vs Akkusativ), Genitiv case, relative clauses
- Q14-17: B2 — Passiv (werden+Partizip II), indirect speech (Konjunktiv I), complex relative clauses with correct case, nominalized verbs, N-Deklination
- Q18-19: C1 — extended adjective phrases, stylistic register, advanced modal particles (doch/ja/halt/schon nuances)
- Q20: C2 — subtle grammatical error detection in formal text, pragmatic implicature

QUESTION TYPES (must vary — use ALL types):
- fill_blank: A {language} sentence with ONE blank. Options are {language} grammatical forms (e.g. "dem/den/des/der" or "bin/ist/sind/seid")
- correct_sentence: 4 {language} sentences, only ONE grammatically correct, other 3 have clear errors
- word_order: Scrambled {language} words — pick the correctly ordered sentence (all options same words)
- translation: A {native_language} phrase — pick the correct {language} translation from 4 options
- comprehension: A 2-3 sentence {language} text, question in {native_language} about the content

MANDATORY LANGUAGE RULE:
- {language} content (sentences, options for grammar questions) MUST stay in {language}
- ONLY question framing is in {native_language}
- Answer options for comprehension questions may be in {native_language}

GOOD EXAMPLE (fill_blank for A1 — verb conjugation):
{{"question": "Uzupełnij zdanie: Ich ___ aus Polen.", "options": ["A. kommen", "B. komme", "C. kommt", "D. kommst"], "correct": "B", "points": 1, "cefr_hint": "A1"}}

GOOD EXAMPLE (fill_blank for A2 — Akkusativ):
{{"question": "Uzupełnij zdanie (biernik): Ich sehe ___ Mann auf der Straße.", "options": ["A. der", "B. den", "C. dem", "D. ein"], "correct": "B", "points": 1, "cefr_hint": "A2"}}

GOOD EXAMPLE (word_order for B1):
{{"question": "Ułóż słowa w poprawnej kolejności: weil / ich / müde / bin / heute", "options": ["A. weil ich heute müde bin", "B. weil bin ich heute müde", "C. weil ich bin heute müde", "D. weil heute ich müde bin"], "correct": "A", "points": 2, "cefr_hint": "B1"}}

GOOD EXAMPLE (correct_sentence for B2):
{{"question": "Które zdanie jest gramatycznie poprawne (strona bierna)?", "options": ["A. Das Buch wurde von ihm gelesen.", "B. Das Buch ist von ihm gelesen worden.", "C. Das Buch wird von ihm gelesen gewesen.", "D. Das Buch hat von ihm gelesen werden."], "correct": "A", "points": 3, "cefr_hint": "B2"}}

GOOD EXAMPLE (comprehension for A2):
{{"question": "Anna kupiła wczoraj chleb i mleko. Poszła do sklepu rano, bo był pusty. Pytanie: Kiedy Anna poszła do sklepu?", "options": ["A. Wieczorem", "B. W południe", "C. Rano", "D. Wczoraj wieczorem"], "correct": "C", "points": 1, "cefr_hint": "A2"}}

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "type": "fill_blank",
            "question": "Question framing in {native_language} with {language} sentence",
            "options": ["A. option", "B. option", "C. option", "D. option"],
            "correct": "B",
            "points": 1,
            "cefr_hint": "A1"
        }}
    ]
}}"""

    try:
        result = await generate_json(prompt)
        if isinstance(result, list):
            result = {"questions": result}
        return result
    except Exception as e:
        logger.error(f"Error generating placement test: {e}")
        return {
            "questions": [
                {
                    "id": 1,
                    "type": "vocabulary",
                    "question": f"What does the {language} word for 'hello' translate to?",
                    "options": ["A. Goodbye", "B. Hello", "C. Thank you", "D. Please"],
                    "correct": "B",
                    "points": 1,
                    "cefr_hint": "A1",
                }
            ]
        }


@with_model("placement")
async def analyze_placement_results(questions: list, answers: dict, language: str, native_language: str = "Polish") -> dict:
    questions_summary = []
    for q in questions:
        user_ans = answers.get(str(q["id"]), answers.get(q["id"], ""))
        questions_summary.append({
            "id": q["id"],
            "type": q.get("type", "unknown"),
            "correct": q["correct"],
            "user_answer": user_ans,
            "cefr_hint": q.get("cefr_hint", "A1"),
            "is_correct": str(user_ans).upper() == str(q["correct"]).upper(),
        })

    correct_count = sum(1 for q in questions_summary if q["is_correct"])
    total = len(questions)
    score = (correct_count / total * 100) if total > 0 else 0

    prompt = f"""Analyze placement test results for a {native_language} speaker learning {language}.

Test summary:
- Total questions: {total}
- Correct answers: {correct_count}
- Score: {score:.1f}%
- Question breakdown (with CEFR hints): {questions_summary}

CEFR LEVEL DETERMINATION RULES — BE STRICT AND CONSERVATIVE:
- Assign A1 if student gets fewer than 60% of A1 questions correct OR overall score < 25%
- Assign A2 if student gets 60%+ of A1 questions AND fewer than 50% of B1 questions correct
- Assign B1 ONLY if student scores 70%+ on A1+A2 questions AND gets 50%+ of B1 questions
- Assign B2 ONLY if student masters B1 with 80%+ and scores 60%+ on B2 questions
- Assign C1 only if student scores 70%+ on C1 questions
- Assign C2 only for near-perfect scores (90%+) on advanced questions

IMPORTANT: A student who gets 30-50% overall is almost always A2, NOT B1. Do not over-estimate.
CRITICAL: Most native {native_language} speakers with NO prior {language} knowledge MUST get A1.
A student with overall score 30-50% is A2 at most, NEVER B1.
When in doubt, assign the LOWER level — it is better to start too easy than too hard.
Most native {native_language} speakers with minimal {language} exposure score A1-A2.

Write ALL text fields (strong_areas, weak_areas, recommendations) in {native_language}.

Return JSON:
{{
    "cefr_level": "A2",
    "score": {score:.1f},
    "strong_areas": ["obszary mocne w {native_language}"],
    "weak_areas": ["obszary słabe w {native_language}"],
    "recommendations": "Rekomendacje w {native_language}..."
}}"""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error analyzing placement results: {e}")
        if score < 20:
            level = "A1"
        elif score < 40:
            level = "A1"
        elif score < 55:
            level = "A2"
        elif score < 70:
            level = "B1"
        elif score < 85:
            level = "B2"
        elif score < 95:
            level = "C1"
        else:
            level = "C2"

        return {
            "cefr_level": level,
            "score": score,
            "strong_areas": ["general knowledge"],
            "weak_areas": ["needs assessment"],
            "recommendations": f"Na podstawie wyniku {score:.1f}% Twój poziom to {level}. Kontynuuj regularną naukę.",
        }
