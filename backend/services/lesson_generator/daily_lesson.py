"""
Daily lesson content generation.
"""
import logging
from sqlalchemy.orm import Session
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


@with_model("lesson")
async def generate_daily_lesson(
    user_id: int,
    target_language: str,
    native_language: str,
    cefr_level: str,
    recent_topics: list[str],
    day_number: int,
    db: Session,
) -> dict:
    """Generate a full daily lesson with all sections."""
    # Import here to avoid circular dependencies

    # Generate core lesson
    prompt = f"""
    You are an expert language teacher creating a daily lesson for a {native_language} speaker learning {target_language} at {cefr_level} level.
    The student has recently studied: {', '.join(recent_topics) if recent_topics else 'none yet'}.
    This is day {day_number} of their personalized study plan.

    Create a comprehensive lesson with the following sections:
    1. Warm-up (2-3 min): Quick review of previous day's material
    2. Vocabulary introduction (10-15 min): 10-15 new words with translations, example sentences, and audio cues
    3. Grammar explanation (10-15 min): One key grammar point with clear examples
    4. Practice exercises (15-20 min): Mix of filling gaps, translation, and sentence creation
    5. Cultural note (2-3 min): Interesting cultural fact related to the language
    6. Speaking practice (5-10 min): Prompts for pronunciation and fluency
    7. Writing exercise (5-10 min): Short writing prompt with guidance
    8. Wrap-up (2-3 min): Summary and preview of next day

    Make sure the content is engaging, culturally appropriate, and follows CEFR {cefr_level} guidelines.
    Include approximate timings for each section.

    Return ONLY valid JSON:
    {{
        "warmup": {{
            "activity": "description of warm-up activity",
            "duration_minutes": 3,
            "content": "specific content for the warm-up"
        }},
        "vocabulary": [{{
            "word": "target language word",
            "translation": "native language translation",
            "example_sentence": "sentence in target language",
            "audio_cue": "description of when to play audio"
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

        # Add interleaved review and output forcing sections (will be filled by other functions)
        lesson["interleaved_review"] = []
        lesson["output_forcing"] = {
            "instruction": "Przeczytaj 5 zdań poniżej, zakryj je i spróbuj odtworzyć z pamięci. To trudne ćwiczenie na pamięć długotrwałą.",
            "text": "Hallo, ich heiße Max und ich komme aus Polen. In meiner Freizeit lerne ich Deutsch und treffe meine Freunde. Die Universität ist groß und ich studiere dort seit zwei Jahren. Meine Familie wohnt in Warschau i wir besuchen uns oft am Wochenende. Deutsch zu lernen macht viel Spaß und ich habe schon viele neue Freunde gefunden."
        }

        return lesson
    except Exception as e:
        logger.error(f"Error generating daily lesson: {e}")
        # Fallback lesson
        return {
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
                "text": "Hallo, ich heiße Max und ich komme aus Polen. In meiner Freizeit lerne ich Deutsch und treffe meine Freunde. Die Universität ist groß und ich studiere dort seit zwei Jahren. Meine Familie wohnt in Warschau i wir besuchen uns często am Weekend. Deutsch zu lernen macht viel Spaß und ich habe schon viele neue Freunde gefunden."
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
    """Generate i+1 content: 90% known vocabulary, 10% new words.
    Based on Predictive Coding / Comprehensible Input (Krashen + Friston).
    """
    known_vocab = ", ".join(known_words[:50]) if known_words else "basic greetings, numbers, basic verbs"

    prompt = f"""Generate a {target_language} text for a {native_language} speaker at {cefr_level}.
Topic: {topic}

STRICT RULES:
- 90% of words MUST be from this KNOWN vocabulary: {known_vocab}
- Only 10% new words (3-5 max), clearly marked with ** around them
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

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating i+1 content: {e}")
        return {
            "text": f"Hallo! Ich lerne {target_language}. Das ist gut.",
            "new_words": ["lernen", "gut"],
            "questions": [{"question": "Was lernt die Person?", "answer": "Deutsch"}],
            "cefr_level": cefr_level
        }