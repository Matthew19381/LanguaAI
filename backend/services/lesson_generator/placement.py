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
        questions = result.get("questions", [])
        # Validate: ensure we have 20 questions with proper structure
        if len(questions) < 20:
            logger.warning(f"AI returned only {len(questions)} questions, expected 20. Padding with fallback questions.")
            questions = _ensure_20_questions(questions, language, native_language)
        # Ensure sequential IDs
        for i, q in enumerate(questions):
            q["id"] = i + 1
        return {"questions": questions}
    except Exception as e:
        logger.error(f"Error generating placement test: {e}")
        return {"questions": _generate_fallback_questions(language, native_language)}


def _ensure_20_questions(existing: list, language: str, native_language: str) -> list:
    """Pad existing questions up to 20 with fallback questions if AI returned too few."""
    fallback = _generate_fallback_questions(language, native_language)
    # Add fallback questions until we have 20
    i = 0
    while len(existing) < 20 and i < len(fallback):
        existing.append(fallback[i])
        i += 1
    # If still not enough, duplicate last fallback with modified IDs
    while len(existing) < 20:
        q = dict(fallback[len(existing) % len(fallback)])
        q["id"] = len(existing) + 1
        existing.append(q)
    return existing[:20]


def _generate_fallback_questions(language: str, native_language: str) -> list:
    """Generate a full 20-question fallback placement test."""
    lang_lower = language.lower()
    if lang_lower == "german":
        return [
            {"id": 1, "type": "fill_blank", "question": "Uzupełnij: Ich ___ aus Polen.", "options": ["A. kommen", "B. komme", "C. kommt", "D. kommst"], "correct": "B", "points": 1, "cefr_hint": "A1"},
            {"id": 2, "type": "fill_blank", "question": "Uzupełnij: Das ___ ein Buch.", "options": ["A. ist", "B. sind", "C. bin", "D. seid"], "correct": "A", "points": 1, "cefr_hint": "A1"},
            {"id": 3, "type": "fill_blank", "question": "Uzupełnij: Er ___ Deutsch.", "options": ["A. spreche", "B. sprichst", "C. spricht", "D. sprechen"], "correct": "C", "points": 1, "cefr_hint": "A1"},
            {"id": 4, "type": "fill_blank", "question": "Rodzajnik: ___ Mann (mianownik)", "options": ["A. der", "B. die", "C. das", "D. den"], "correct": "A", "points": 1, "cefr_hint": "A1"},
            {"id": 5, "type": "fill_blank", "question": "Uzupełnij (biernik): Ich sehe ___ Hund.", "options": ["A. der", "B. den", "C. dem", "D. die"], "correct": "B", "points": 1, "cefr_hint": "A2"},
            {"id": 6, "type": "fill_blank", "question": "Uzupełnij (celownik): Ich gebe ___ Kind ein Geschenk.", "options": ["A. der", "B. die", "C. dem", "D. das"], "correct": "C", "points": 1, "cefr_hint": "A2"},
            {"id": 7, "type": "fill_blank", "question": "Czas Perfekt: Ich ___ nach Hause ___.", "options": ["A. habe / gegangen", "B. bin / gegangen", "C. habe / gehen", "D. bin / gehen"], "correct": "B", "points": 1, "cefr_hint": "A2"},
            {"id": 8, "type": "fill_blank", "question": "Przyimek: Er geht ___ Schule.", "options": ["A. nach", "B. zu", "C. in", "D. an"], "correct": "B", "points": 1, "cefr_hint": "A2"},
            {"id": 9, "type": "word_order", "question": "Ułóż zdanie: weil / ich / müde / bin", "options": ["A. weil ich müde bin", "B. weil bin ich müde", "C. weil ich bin müde", "D. weil müde ich bin"], "correct": "A", "points": 2, "cefr_hint": "B1"},
            {"id": 10, "type": "fill_blank", "question": "Konjunktiv II: Ich ___ gern mehr Zeit.", "options": ["A. hätte", "B. habe", "C. hatte", "D. hat"], "correct": "A", "points": 2, "cefr_hint": "B1"},
            {"id": 11, "type": "fill_blank", "question": "Zwrotny czasownik: Er ___ sich die Hände.", "options": ["A. wäscht", "B. wascht", "C. waschen", "D. wäschen"], "correct": "A", "points": 2, "cefr_hint": "B1"},
            {"id": 12, "type": "fill_blank", "question": "Przyimek dwupadkowy: Er sitzt ___ Stuhl. (Dativ)", "options": ["A. auf den", "B. auf dem", "C. auf das", "D. auf die"], "correct": "B", "points": 2, "cefr_hint": "B1"},
            {"id": 13, "type": "fill_blank", "question": "Dopełniacz: Die Farbe ___ Hauses (neutrum)", "options": ["A. des", "B. der", "C. dem", "D. die"], "correct": "A", "points": 2, "cefr_hint": "B1"},
            {"id": 14, "type": "correct_sentence", "question": "Które zdanie jest poprawne (strona bierna)?", "options": ["A. Das Buch wurde gelesen.", "B. Das Buch ist gelesen worden.", "C. Das Buch hat gelesen werden.", "D. Das Buch wird gelesen gewesen."], "correct": "A", "points": 3, "cefr_hint": "B2"},
            {"id": 15, "type": "fill_blank", "question": "Tryb łączący (Konj.II): Er sagte, er ___ krank.", "options": ["A. ist", "B. sei", "C. wäre", "D. war"], "correct": "B", "points": 3, "cefr_hint": "B2"},
            {"id": 16, "type": "fill_blank", "question": "Rozszerzone wyprzedzenie: Die ___ Blumen sind schön.", "options": ["A. rot", "B. roten", "C. roter", "D. rotes"], "correct": "B", "points": 3, "cefr_hint": "B2"},
            {"id": 17, "type": "fill_blank", "question": "Rzeczownik odsłownik: Das ___ ist wichtig.", "options": ["A. Lesen", "B. lesen", "C. gelesen", "D. lesend"], "correct": "A", "points": 3, "cefr_hint": "B2"},
            {"id": 18, "type": "fill_blank", "question": "Partykuła modalna: Das ist ___ wahr.", "options": ["A. doch", "B. ja", "C. wohl", "D. schon"], "correct": "C", "points": 4, "cefr_hint": "C1"},
            {"id": 19, "type": "comprehension", "question": "Trotz der Schwierigkeiten hat er seine Ziele erreicht. Co oznacza 'trotz'?", "options": ["A. Dzięki", "B. Pomimo", "C. Z powodu", "D. Przed"], "correct": "B", "points": 4, "cefr_hint": "C1"},
            {"id": 20, "type": "correct_sentence", "question": "Które zdanie zawiera subtelny błąd?", "options": ["A. Kaum dass er ankam, rief er an.", "B. Er aß, nachdem er gekocht hatte.", "C. Je mehr er lernte, desto besser wurde er.", "D. Er behauptete, er habe es nicht gewusst."], "correct": "A", "points": 5, "cefr_hint": "C2"},
        ]
    elif lang_lower == "english":
        return [
            {"id": 1, "type": "fill_blank", "question": "She ___ to school every day.", "options": ["A. go", "B. goes", "C. going", "D. gone"], "correct": "B", "points": 1, "cefr_hint": "A1"},
            {"id": 2, "type": "fill_blank", "question": "I ___ a student.", "options": ["A. am", "B. is", "C. are", "D. be"], "correct": "A", "points": 1, "cefr_hint": "A1"},
            {"id": 3, "type": "fill_blank", "question": "There ___ three cats in the garden.", "options": ["A. is", "B. are", "C. was", "D. has"], "correct": "B", "points": 1, "cefr_hint": "A1"},
            {"id": 4, "type": "fill_blank", "question": "He ___ like coffee.", "options": ["A. don't", "B. doesn't", "C. isn't", "D. hasn't"], "correct": "B", "points": 1, "cefr_hint": "A1"},
            {"id": 5, "type": "fill_blank", "question": "I have ___ finished my homework.", "options": ["A. yet", "B. already", "C. still", "D. since"], "correct": "B", "points": 1, "cefr_hint": "A2"},
            {"id": 6, "type": "fill_blank", "question": "She is taller ___ her brother.", "options": ["A. that", "B. than", "C. then", "D. as"], "correct": "B", "points": 1, "cefr_hint": "A2"},
            {"id": 7, "type": "fill_blank", "question": "If I ___ rich, I would travel the world.", "options": ["A. am", "B. was", "C. were", "D. be"], "correct": "C", "points": 1, "cefr_hint": "A2"},
            {"id": 8, "type": "fill_blank", "question": "He has ___ to Paris three times.", "options": ["A. been", "B. gone", "C. went", "D. go"], "correct": "A", "points": 1, "cefr_hint": "A2"},
            {"id": 9, "type": "fill_blank", "question": "The book ___ by Shakespeare is famous.", "options": ["A. wrote", "B. written", "C. writing", "D. was written"], "correct": "B", "points": 2, "cefr_hint": "B1"},
            {"id": 10, "type": "fill_blank", "question": "I wish I ___ harder for the exam.", "options": ["A. study", "B. studied", "C. had studied", "D. would study"], "correct": "C", "points": 2, "cefr_hint": "B1"},
            {"id": 11, "type": "fill_blank", "question": "She made me ___ the whole story.", "options": ["A. repeat", "B. to repeat", "C. repeating", "D. repeated"], "correct": "A", "points": 2, "cefr_hint": "B1"},
            {"id": 12, "type": "fill_blank", "question": "___ it was raining, we went out.", "options": ["A. Despite", "B. Although", "C. However", "D. Because"], "correct": "B", "points": 2, "cefr_hint": "B1"},
            {"id": 13, "type": "fill_blank", "question": "The report must ___ by Friday.", "options": ["A. finish", "B. be finished", "C. finished", "D. finishing"], "correct": "B", "points": 2, "cefr_hint": "B1"},
            {"id": 14, "type": "fill_blank", "question": "Not until midnight ___ the results.", "options": ["A. we received", "B. did we receive", "C. we did receive", "D. received we"], "correct": "B", "points": 3, "cefr_hint": "B2"},
            {"id": 15, "type": "fill_blank", "question": "The proposal is worthy ___ consideration.", "options": ["A. of", "B. for", "C. to", "D. with"], "correct": "A", "points": 3, "cefr_hint": "B2"},
            {"id": 16, "type": "fill_blank", "question": "He denied ___ the money.", "options": ["A. take", "B. to take", "C. taking", "D. having taken"], "correct": "D", "points": 3, "cefr_hint": "B2"},
            {"id": 17, "type": "fill_blank", "question": "___ the circumstances, we did well.", "options": ["A. Given", "B. Giving", "C. Having given", "D. To give"], "correct": "A", "points": 3, "cefr_hint": "B2"},
            {"id": 18, "type": "fill_blank", "question": "The ___ of evidence was overwhelming.", "options": ["A. weigh", "B. weight", "C. weighted", "D. weighing"], "correct": "B", "points": 4, "cefr_hint": "C1"},
            {"id": 19, "type": "fill_blank", "question": "She spoke so ___ that everyone was captivated.", "options": ["A. eloquent", "B. eloquently", "C. eloquence", "D. elocution"], "correct": "B", "points": 4, "cefr_hint": "C1"},
            {"id": 20, "type": "correct_sentence", "question": "Which sentence contains a subtle error?", "options": ["A. I look forward to hearing from you.", "B. He insisted that she stay.", "C. Between you and I, this is wrong.", "D. The data shows a clear trend."], "correct": "C", "points": 5, "cefr_hint": "C2"},
        ]
    else:
        # Generic fallback for any language
        return [
            {"id": i+1, "type": "fill_blank", "question": f"Question {i+1} in {language}", "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"], "correct": "A", "points": 1, "cefr_hint": "A1" if i < 4 else "A2" if i < 8 else "B1" if i < 13 else "B2" if i < 17 else "C1" if i < 19 else "C2"}
            for i in range(20)
        ]


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
