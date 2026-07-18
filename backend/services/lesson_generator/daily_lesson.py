"""Daily lesson content generation."""
import json
import logging
import re

from sqlalchemy.orm import Session

from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)

# ── SCI-3: lexical-coverage validation for i+1 comprehensible input ──────────
# Nation (2006); Hu & Nation (2000): learners need 95-98% known-word coverage to
# comprehend a text. We operationalize coverage from the text's own **new-word**
# markers (the "+1"): everything not marked new is assumed known.
COVERAGE_TARGET = 0.95
COVERAGE_MAX_REGENERATIONS = 2  # 1 initial attempt + up to 2 regenerations
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_NEW_WORD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def lexical_coverage(text: str, known_words: list[str] | None = None) -> float:
    """Estimate the fraction of word tokens in an i+1 text that are already known.

    New words are the tokens the text explicitly wraps in ``**...**``; a marked
    word that already appears in ``known_words`` is not counted as new (the model
    over-marked it). Returns coverage in [0, 1]; 0.0 for empty text.
    """
    if not text:
        return 0.0
    total = len(_TOKEN_RE.findall(text))
    if total == 0:
        return 0.0
    known = {w.strip().lower() for w in (known_words or []) if w and w.strip()}
    new_tokens = 0
    for phrase in _NEW_WORD_RE.findall(text):
        for tok in _TOKEN_RE.findall(phrase):
            if tok.lower() not in known:
                new_tokens += 1
    return max(0.0, (total - new_tokens) / total)


@with_model("lesson")
async def generate_daily_lesson(
    user_id: int,
    target_language: str,
    native_language: str,
    cefr_level: str,
    recent_topics: list[str],
    day_number: int,
    db: Session,
    study_plan_data: dict = None,
    user_errors: list = None,
    user_vocabulary: list[str] = None,
    weak_topics: list[str] = None,
    strong_topics: list[str] = None,
) -> dict:
    """Generate a full daily lesson with all sections."""
    # Import here to avoid circular dependencies

    # ── RAG context: personalize the lesson from the user's data ──
    rag_context = ""
    if user_vocabulary:
        rag_context += f"\n- Known vocabulary (use for i+1 / reinforcement): {', '.join(user_vocabulary[:30])}"
    if weak_topics:
        rag_context += f"\n- Weak topics (spend extra time reinforcing): {', '.join(weak_topics)}"
    if strong_topics:
        rag_context += f"\n- Strong topics (can interleave at higher difficulty): {', '.join(strong_topics)}"
    if user_errors:
        rag_context += f"\n- Recent mistakes to address gently: {json.dumps(user_errors[:5], ensure_ascii=False)}"
    if study_plan_data:
        plan_str = study_plan_data.get("focus") or study_plan_data.get("summary") or ""
        if plan_str:
            rag_context += f"\n- Study plan guidance: {plan_str}"

    # Generate core lesson
    prompt = f"""
    You are an expert language teacher creating a daily lesson for a {native_language} speaker learning {target_language} at {cefr_level} level.
    The student has recently studied: {', '.join(recent_topics) if recent_topics else 'none yet'}.
    This is day {day_number} of their personalized study plan.
{rag_context}

    Create a comprehensive lesson with the following sections:
    0. Pretest (2-3 min): BEFORE teaching anything, ask the student to GUESS the meaning of 3-5 of the
       new words from the Vocabulary section below. Wrong guesses are expected and helpful — this is a
       pretesting exercise (Kornell, Hays & Bjork 2009), not a graded quiz. Each item: the target word,
       a short guessing instruction in {native_language}, four plausible {native_language} options
       (exactly one correct), and the correct answer. The words MUST be a subset of the Vocabulary words.
    1. Warm-up (2-3 min): Quick review of previous day's material
    2. Vocabulary introduction (10-15 min): 10-15 new words with translations, example sentences, audio cues,
       and a short semantic "category" label per word (e.g. "colours", "food", "motion verbs") so related
       words can be spaced apart during review to reduce interference (Tinkham 1993).
    3. Grammar explanation (10-15 min): One key grammar point with clear examples
    4. Practice exercises (15-20 min): Mix of filling gaps, translation, and sentence creation.
       Tag each exercise block with the underlying skill it practises ("skill_tag"), so the same skill
       can later be re-practised through fresh variants rather than the identical sentence.
    5. Cultural note (2-3 min): Interesting cultural fact related to the language
    6. Speaking practice (5-10 min): Prompts for pronunciation and fluency
    7. Writing exercise (5-10 min): Short writing prompt with guidance
    8. Wrap-up (2-3 min): Summary and preview of next day
    9. Output forcing (retrieval practice): Exactly 5 connected sentences in {target_language} at {cefr_level} level,
       built mainly from THIS lesson's vocabulary and grammar. The student will read them, cover them,
       and recall them from memory. Write the instruction in {native_language}.

    Make sure the content is engaging, culturally appropriate, and follows CEFR {cefr_level} guidelines.
    Include approximate timings for each section.

    Return ONLY valid JSON:
    {{
        "pretest": [{{
            "word": "target language word (must also appear in vocabulary)",
            "prompt": "guessing instruction in {native_language}",
            "options": ["{native_language} option 1", "option 2", "option 3", "option 4"],
            "answer": "the correct {native_language} option"
        }}],
        "warmup": {{
            "activity": "description of warm-up activity",
            "duration_minutes": 3,
            "content": "specific content for the warm-up"
        }},
        "vocabulary": [{{
            "word": "target language word",
            "translation": "native language translation",
            "example_sentence": "sentence in target language",
            "audio_cue": "description of when to play audio",
            "category": "short semantic group label, e.g. colours / food / motion verbs"
        }}],
        "grammar": {{
            "topic": "grammar topic name",
            "explanation": "clear explanation in native language",
            "examples": [{{
                "sentence": "example sentence in target language",
                "translation": "translation in native language"
            }}],
            "rule": "concise rule summary"
        }},
        "exercises": [{{
            "type": "fill-in-the-blank|translation|sentence_creation|matching",
            "instruction": "what the student should do",
            "skill_tag": "the underlying skill being practised, e.g. 'Perfekt with haben' or 'accusative articles'",
            "items": [{{
                "prompt": "prompt or question",
                "answer": "correct answer"
            }}],
            "feedback": "explanation of correct answer"
        }}],
        "cultural_note": {{
            "title": "cultural topic title",
            "content": "interesting cultural information",
            "relevance": "how this relates to language learning"
        }},
        "speaking_practice": [{{
            "prompt": "what the student should say",
            "focus": "pronunciation|fluency|intonation",
            "sample_answer": "sample correct response"
        }}],
        "writing_exercise": {{
            "prompt": "writing prompt",
            "guidelines": "brief guidelines for the writing task",
            "sample_response": "sample good response"
        }},
        "wrap_up": {{
            "summary": "summary of what was learned",
            "preview": "preview of tomorrow's topic",
            "motivational_message": "encouraging message to continue learning"
        }},
        "output_forcing": {{
            "instruction": "instruction in {native_language}: read the 5 sentences, cover them, recall them from memory",
            "text": "5 connected sentences in {target_language} using this lesson's vocabulary",
            "translation": "translation of the 5 sentences into {native_language}"
        }}
    }}
    """

    try:
        lesson = await generate_json(prompt)
        # Ensure all expected fields are present
        required_sections = [
            "warmup", "vocabulary", "grammar", "exercises", "cultural_note",
            "speaking_practice", "writing_exercise", "wrap_up"
        ]
        for section in required_sections:
            if section not in lesson:
                lesson[section] = {} if section not in ["vocabulary", "exercises", "speaking_practice"] else []

        lesson["interleaved_review"] = _build_interleaved_review(recent_topics)

        # Output forcing must come from the model (lesson-specific, in the target
        # language). If missing or malformed, drop the section entirely — the
        # frontend renders it conditionally, so omission is safe.
        of = lesson.get("output_forcing")
        if not (isinstance(of, dict) and of.get("text") and of.get("instruction")):
            lesson.pop("output_forcing", None)

        # SCI-2: keep only well-formed pretest items (word + options + answer)
        # whose target word is actually taught in this lesson's vocabulary.
        lesson["pretest"] = _sanitize_pretest(lesson.get("pretest"), lesson.get("vocabulary"))

        return lesson
    except Exception as e:
        logger.error(f"Error generating daily lesson: {e}")
        # Fallback lesson
        return {
            "pretest": [{
                "word": "Hallo",
                "prompt": "Zgadnij, co znaczy to słowo (błędna odpowiedź jest OK):",
                "options": ["Hello", "Goodbye", "Please", "Thank you"],
                "answer": "Hello"
            }],
            "warmup": {
                "activity": "Review yesterday's vocabulary",
                "duration_minutes": 3,
                "content": "Go over the 5 words from yesterday's lesson"
            },
            "vocabulary": [{
                "word": "Hallo",
                "translation": "Hello",
                "example_sentence": "Hallo! Wie heißen Sie?",
                "audio_cue": "After greeting"
            }],
            "grammar": {
                "topic": "Basic sentence structure",
                "explanation": "Simple sentences follow Subject-Verb-Object order",
                "examples": [{
                    "sentence": "Ich heiße Anna.",
                    "translation": "My name is Anna."
                }],
                "rule": "Subject comes first, then verb, then object"
            },
            "exercises": [{
                "type": "translation",
                "instruction": "Translate to German",
                "items": [{
                    "prompt": "Hello",
                    "answer": "Hallo"
                }],
                "feedback": "Hallo is the correct greeting"
            }],
            "cultural_note": {
                "title": "German-speaking countries",
                "content": "German is spoken in Germany, Austria, Switzerland, Liechtenstein, and parts of Belgium and Italy.",
                "relevance": "Understanding where the language is spoken helps with motivation"
            },
            "speaking_practice": [{
                "prompt": "Say your name in German",
                "focus": "pronunciation",
                "sample_answer": "Ich heißen [Your Name]"
            }],
            "writing_exercise": {
                "prompt": "Write a simple sentence introducing yourself",
                "guidelines": "Use the structure: Ich heiße [name]. Ich komme aus [country].",
                "sample_response": "Ich heiße Max. Ich komme aus Polen."
            },
            "wrap_up": {
                "summary": "Learned basic greetings and self-introduction",
                "preview": "Tomorrow: numbers 1-10 and basic questions",
                "motivational_message": "Great job starting your language journey!"
            },
            "interleaved_review": [],
            "output_forcing": {
                "instruction": "Przeczytaj 5 zdań poniżej, zakryj je i spróbuj odtworzyć z pamięci. To trudne ćwiczenie na pamięć długotrwałą.",
                "text": "Hallo, ich heiße Max und ich komme aus Polen. In meiner Freizeit lerne ich Deutsch und treffe meine Freunde. Die Universität ist groß und ich studiere dort seit zwei Jahren. Meine Familie wohnt in Warschau und wir besuchen uns oft am Wochenende. Deutsch zu lernen macht viel Spaß und ich habe schon viele neue Freunde gefunden."
            }
        }


@with_model("lesson")
async def generate_iplus1_content(
    known_words: list,
    target_language: str,
    native_language: str,
    cefr_level: str,
    topic: str = "daily life",
) -> dict:
    """Generate comprehensible-input text: >=95% known vocabulary, 3-5 new words.

    Lexical-coverage research shows learners need 95-98% known words in a text
    for adequate comprehension (Hu & Nation 2000; Nation 2006; Schmitt et al.
    2011). 3-5 new words in a 100-150-word text lands at ~96-97% coverage.
    """
    known_vocab = ", ".join(known_words[:50]) if known_words else "basic greetings, numbers, basic verbs"

    base_prompt = f"""Generate a {target_language} text for a {native_language} speaker at {cefr_level}.
Topic: {topic}

STRICT RULES:
- At least 95% of the words MUST come from this KNOWN vocabulary (plus their inflected forms and {cefr_level}-level function words): {known_vocab}
- Introduce exactly 3-5 new words (no more), clearly marked with ** around them
- Use ONLY grammar appropriate for {cefr_level}
- Length: 100-150 words
- Comprehension questions in {native_language}

Return JSON:
{{
    "text": "...",
    "new_words": ["w1", "w2"],
    "questions": [{{"question": "...", "answer": "..."}}],
    "cefr_level": "{cefr_level}"
}}"""

    # SCI-3: generate, measure lexical coverage, and regenerate (with a stricter
    # nudge) if the text introduces too many new words. Keep the best attempt.
    best = None
    for attempt in range(1 + COVERAGE_MAX_REGENERATIONS):
        prompt = base_prompt
        if attempt > 0:
            prompt += (
                f"\n\nYour previous text had too many unfamiliar words "
                f"(below {int(COVERAGE_TARGET * 100)}% known-word coverage). "
                f"Rewrite it using MORE of the known vocabulary and NO MORE than "
                f"3-5 new words total."
            )
        try:
            result = await generate_json(prompt)
        except Exception as e:
            logger.error(f"Error generating i+1 content (attempt {attempt + 1}): {e}")
            continue

        coverage = lexical_coverage(result.get("text", ""), known_words)
        result["lexical_coverage"] = round(coverage, 3)
        result["coverage_attempts"] = attempt + 1
        if best is None or coverage > best.get("lexical_coverage", 0):
            best = result
        if coverage >= COVERAGE_TARGET:
            return result

    if best is not None:
        logger.warning(
            "i+1 coverage stayed below target (%.2f) after %d attempts",
            best.get("lexical_coverage", 0), best.get("coverage_attempts", 0),
        )
        return best

    # Total failure (every attempt raised) → safe fallback
    return {
        "text": f"Hallo! Ich lerne {target_language}. Das ist gut.",
        "new_words": ["lernen", "gut"],
        "questions": [{"question": "Was lernt die Person?", "answer": "Deutsch"}],
        "cefr_level": cefr_level,
        "lexical_coverage": 1.0,
        "coverage_attempts": 0,
    }


@with_model("lesson")
async def generate_exercise_variants(
    skill_tags: list[str],
    target_language: str,
    native_language: str,
    cefr_level: str,
    per_skill: int = 2,
    avoid_prompts: list[str] | None = None,
) -> list[dict]:
    """Generate fresh exercise variants for skills the learner keeps getting wrong.

    Variability of practice (Schmidt & Bjork 1992): re-practising a skill through
    *new* surface forms generalizes better than repeating the identical item.
    """
    if not skill_tags:
        return []
    avoid = "\n".join(f"- {p}" for p in (avoid_prompts or [])[:15])
    avoid_block = f"\n\nDo NOT reuse these existing prompts:\n{avoid}" if avoid else ""

    prompt = f"""Create practice exercises for a {native_language} speaker learning {target_language} at CEFR {cefr_level}.

Generate {per_skill} NEW exercises for EACH of these skills: {', '.join(skill_tags)}

Each exercise must practise the same underlying skill but with DIFFERENT vocabulary and
sentence content than typical textbook examples. Keep prompts short and unambiguous with
exactly one correct answer.{avoid_block}

Return ONLY valid JSON:
{{"exercises": [{{
    "skill_tag": "one of the skills listed above, copied exactly",
    "type": "fill-in-the-blank|translation|sentence_creation",
    "instruction": "what the student should do, in {native_language}",
    "prompt": "the question",
    "answer": "the single correct answer",
    "feedback": "one-sentence explanation in {native_language}"
}}]}}"""

    try:
        data = await generate_json(prompt)
        raw = data.get("exercises") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return []
        allowed = {s.strip().lower() for s in skill_tags}
        clean = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            p = (item.get("prompt") or "").strip()
            a = (item.get("answer") or "").strip()
            tag = (item.get("skill_tag") or "").strip()
            if not p or not a or tag.lower() not in allowed:
                continue
            clean.append({
                "prompt": p, "answer": a, "skill_tag": tag,
                "exercise_type": item.get("type"),
                "instruction": item.get("instruction"),
                "feedback": item.get("feedback"),
            })
        return clean
    except Exception as e:
        logger.error(f"Error generating exercise variants: {e}")
        return []


def _sanitize_pretest(pretest, vocabulary) -> list:
    """Validate SCI-2 pretest items (Kornell, Hays & Bjork 2009).

    Keeps only items that have a target word, exactly-one-correct multiple
    choice (>=2 options incl. the answer), and whose word is actually taught in
    this lesson's vocabulary. Returns [] on anything malformed — the frontend
    renders the section conditionally, so an empty list simply hides it.
    """
    if not isinstance(pretest, list) or not isinstance(vocabulary, list):
        return []
    vocab_words = {
        (v.get("word") or "").strip().lower()
        for v in vocabulary if isinstance(v, dict)
    }
    clean = []
    for item in pretest:
        if not isinstance(item, dict):
            continue
        word = (item.get("word") or "").strip()
        answer = (item.get("answer") or "").strip()
        options = item.get("options")
        if not (word and answer and isinstance(options, list) and len(options) >= 2):
            continue
        if answer not in options:
            continue
        if vocab_words and word.lower() not in vocab_words:
            continue
        clean.append({"word": word, "prompt": item.get("prompt", ""),
                      "options": options, "answer": answer})
    return clean[:5]


def _build_interleaved_review(recent_topics: list[str] | None) -> list:
    """Build a 'Mixed Review' section from the user's recent lesson topics.

    Combines two well-documented effects: retrieval practice / testing effect
    (Roediger & Karpicke 2006) and interleaving of prior topics with new
    material (Rohrer & Taylor 2007; Kornell & Bjork 2008). Returns 2-3
    lightweight recall prompts.
    """
    if not recent_topics:
        return []
    prompts = []
    for topic in recent_topics[:3]:
        prompts.append({
            "topic": topic,
            "prompt": f"Przypomnij sobie 3 słowa lub zwroty z tematu: {topic}",
            "type": "recall",
        })
    return prompts