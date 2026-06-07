"""Study plan generation."""
import logging
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


@with_model("lesson")
async def generate_study_plan(user_data: dict, language: str, native_language: str) -> dict:
    cefr_level = user_data.get("cefr_level", "A1")
    name = user_data.get("name", "Student")

    prompt = f"""Create a comprehensive 30-day language study plan for {name}, a {native_language} speaker learning {language} at CEFR level {cefr_level}.

Write all text fields (grammar_topic, vocabulary_theme, conversation_topic, cultural_note, goal, key_grammar, overall_goal) in {native_language}.

The plan should:
- Build progressively from their current level ({cefr_level})
- Cover grammar, vocabulary, conversation, and culture
- Be realistic and engaging

Return JSON with this exact structure:
{{
    "language": "{language}",
    "cefr_level": "{cefr_level}",
    "daily_topics": [
        {{
            "day": 1,
            "grammar_topic": "Present tense conjugation",
            "vocabulary_theme": "Greetings and introductions",
            "conversation_topic": "Meeting someone new",
            "cultural_note": "Formal vs informal greetings in {language}-speaking countries"
        }}
    ],
    "weekly_goals": [
        {{
            "week": 1,
            "goal": "Master basic greetings and introduce yourself",
            "key_grammar": "Basic sentence structure",
            "vocabulary_count": 50
        }}
    ],
    "overall_goal": "Reach {cefr_level} proficiency and begin transitioning to the next level"
}}

Generate all 30 days and 4 weekly goals."""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating study plan: {e}")
        days = []
        grammar_topics = [
            "Basic sentence structure", "Present tense", "Articles and nouns",
            "Adjectives", "Numbers and counting", "Past tense", "Future tense",
            "Modal verbs", "Prepositions", "Questions and negation",
        ]
        vocab_themes = [
            "Greetings", "Family", "Colors and shapes", "Food and drinks",
            "Days and months", "Weather", "Travel", "Work and professions",
            "Health", "Hobbies",
        ]
        for day in range(1, 31):
            days.append({
                "day": day,
                "grammar_topic": grammar_topics[(day - 1) % len(grammar_topics)],
                "vocabulary_theme": vocab_themes[(day - 1) % len(vocab_themes)],
                "conversation_topic": f"Everyday conversation {day}",
                "cultural_note": f"Cultural aspect of {language}-speaking countries",
            })

        return {
            "language": language,
            "cefr_level": cefr_level,
            "daily_topics": days,
            "weekly_goals": [
                {"week": 1, "goal": "Basic communication", "key_grammar": "Present tense", "vocabulary_count": 50},
                {"week": 2, "goal": "Expand vocabulary", "key_grammar": "Past tense", "vocabulary_count": 100},
                {"week": 3, "goal": "Complex sentences", "key_grammar": "Modal verbs", "vocabulary_count": 150},
                {"week": 4, "goal": "Fluent conversations", "key_grammar": "Advanced structures", "vocabulary_count": 200},
            ],
            "overall_goal": f"Build foundation in {language}",
        }
