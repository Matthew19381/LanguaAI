"""Daily lesson content generation."""
import logging
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


@with_model("lesson")
async def generate_daily_lesson(
    day_number: int,
    study_plan_data: dict,
    user_errors: list,
    cefr_level: str,
    language: str,
    native_language: str,
    recent_topics: list = None,
    user_vocabulary: list = None,
    weak_topics: list = None,
    strong_topics: list = None,
) -> dict:
    daily_topics = study_plan_data.get("daily_topics", [])
    today_topic = {}
    for topic in daily_topics:
        if topic.get("day") == day_number:
            today_topic = topic
            break

    if not today_topic and daily_topics:
        today_topic = daily_topics[(day_number - 1) % len(daily_topics)]

    grammar_topic = today_topic.get("grammar_topic", "Basic grammar")
    vocab_theme = today_topic.get("vocabulary_theme", "Everyday vocabulary")
    conversation_topic = today_topic.get("conversation_topic", "Daily conversation")

    error_section = ""
    if user_errors:
        error_section = f"\nRecent errors to address: {user_errors[:3]}"

    interleaving_section = ""
    if recent_topics:
        interleaving_section = f"\nRecent topics from the last 7 days (for interleaved review): {recent_topics[:5]}"

    vocab_section = ""
    if user_vocabulary:
        vocab_list = ", ".join(user_vocabulary[:30])
        vocab_section = f"\nStudent's known vocabulary (use these words in examples, dialogues, and exercises where appropriate): {vocab_list}"

    weak_section = ""
    if weak_topics:
        weak_list = ", ".join(weak_topics[:5])
        weak_section = f"\nWeak topics needing extra practice (include targeted exercises): {weak_list}"

    strong_section = ""
    if strong_topics:
        strong_list = ", ".join(strong_topics[:3])
        strong_section = f"\nStrong topics the student has mastered (can be referenced as known material): {strong_list}"

    prompt = f"""Create a comprehensive language lesson for Day {day_number}.

Student profile:
- Learning: {language}
- Native language: {native_language}
- CEFR level: {cefr_level}
- Grammar topic: {grammar_topic}
- Vocabulary theme: {vocab_theme}
- Conversation topic: {conversation_topic}
{error_section}
{interleaving_section}
{vocab_section}
{weak_section}
{strong_section}

Generate a complete lesson with rich content. Return JSON:
{{
    "title": "Dzień {day_number}: {grammar_topic}",
    "topic": "{vocab_theme}",
    "explanation": "Detailed grammar explanation in {native_language} with {language} examples...",
    "vocabulary": [
        {{
            "word": "{language} word",
            "translation": "{native_language} translation",
            "example": "Example sentence in {language}",
            "example_translation": "Translation of example in {native_language}"
        }}
    ],
    "dialogue": {{
        "context": "Scenario description",
        "lines": [
            {{
                "speaker": "A",
                "text": "{language} sentence",
                "translation": "{native_language} translation"
            }},
            {{
                "speaker": "B",
                "text": "{language} response",
                "translation": "{native_language} translation"
            }}
        ]
    }},
    "exercises": [
        {{
            "type": "fill_blank",
            "instruction": "Fill in the blank",
            "content": "Sentence with ___",
            "answer": "correct answer"
        }},
        {{
            "type": "multiple_choice",
            "instruction": "Choose the correct form",
            "content": "Question text",
            "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
            "answer": "A"
        }},
        {{
            "type": "translation",
            "instruction": "Translate to {language}",
            "content": "Sentence in {native_language}",
            "answer": "Translation in {language}"
        }},
        {{
            "type": "matching",
            "instruction": "Match words with their translations",
            "pairs": [
                {{"left": "word1", "right": "translation1"}},
                {{"left": "word2", "right": "translation2"}}
            ],
            "answer": "1-A, 2-B"
        }},
        {{
            "type": "error_correction",
            "instruction": "Find and correct the error",
            "content": "Sentence with ONE error in {language}",
            "answer": "Corrected sentence",
            "explanation": "What was wrong (in {native_language})"
        }}
    ],
    "production_task": {{
        "instruction": "Write 2-3 sentences in {language} using today's vocabulary and grammar. AI will evaluate your answer. Keep it simple and focused on today's topic.",
        "example": "Example answer in {language}"
    }},
    "error_review": [],
    "comprehensible_input": {{
        "text": "A 100-150 word passage in {language} at {cefr_level} level using 95% known words and 3-5 new words in context",
        "new_words": ["new_word_1", "new_word_2"],
        "comprehension_questions": [
            {{"question": "Question about the text in {native_language}", "answer": "Answer"}}
        ]
    }},
    "interleaved_review": [],
    "output_forcing": {{
        "instruction": "Przeczytaj 5 zdań poniżej, zakryj je i spróbuj odtworzyć z pamięci. To trudne ćwiczenie na pamięć długotrwałą.",
        "text": "EXACTLY 5 LONG sentences in {language} (each 15-25 words, total 75-100 words) using today's grammar + vocabulary. Each sentence should be complex enough to challenge memory.",
        "translation": "Polish translation of all 5 sentences above"
    }}
}}

Include at least 10 vocabulary words, a 6-line dialogue, and 5 exercises.

ENFORCE VARIETY: The 5 exercises MUST be of DIFFERENT types. Use a mix of:
- fill_blank (NO options, student types the answer)
- multiple_choice (A/B/C/D options)
- translation (native_language → target_language, student types full sentence)
- error_correction (find and fix the error in a sentence)
- application (write 1-2 sentences using today's grammar + vocabulary)
- word_order (scrambled words, student orders correctly)
DO NOT generate 2 exercises of the same type. Each of the 5 must be unique.
{f'Also add 2-3 interleaved review questions from recent topics: {recent_topics[:3]}. Format: [{{"topic": "...", "question": "...", "answer": "..."}}]' if recent_topics else 'Leave interleaved_review as empty array.'}
If there are errors to address, add them to the error_review array with format:
{{"error": "original mistake", "correction": "correct form", "explanation": "why it's wrong (write explanation in {native_language})", "practice": "practice exercise in {language}"}}"""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating daily lesson: {e}")
        return {
            "title": f"Dzień {day_number}: {grammar_topic}",
            "topic": vocab_theme,
            "explanation": f"Today we will study {grammar_topic} in {language}. This is an important foundation for your {cefr_level} level studies.",
            "vocabulary": [
                {"word": "Hallo", "translation": "Cześć", "example": "Hallo, wie geht es dir?", "example_translation": "Cześć, jak się masz?"},
                {"word": "Danke", "translation": "Dziękuję", "example": "Danke schön!", "example_translation": "Dziękuję bardzo!"},
                {"word": "Bitte", "translation": "Proszę", "example": "Bitte sehr.", "example_translation": "Proszę bardzo."},
            ],
            "dialogue": {
                "context": "Two people meeting for the first time",
                "lines": [
                    {"speaker": "A", "text": "Hallo! Wie heißt du?", "translation": "Cześć! Jak masz na imię?"},
                    {"speaker": "B", "text": "Ich heiße Anna. Und du?", "translation": "Mam na imię Anna. A ty?"},
                    {"speaker": "A", "text": "Ich bin Max. Freut mich!", "translation": "Jestem Max. Miło mi!"},
                ],
            },
            "exercises": [
                {"type": "fill_blank", "instruction": "Fill in the blank", "content": "___ heiße Maria.", "answer": "Ich"},
                {"type": "multiple_choice", "instruction": "Choose the correct greeting",
                 "content": "How do you say 'Good morning' in German?",
                 "options": ["A. Gute Nacht", "B. Guten Morgen", "C. Auf Wiedersehen", "D. Danke"],
                 "answer": "B"},
                {"type": "translation", "instruction": "Translate to German",
                 "content": "My name is Anna.", "answer": "Ich heiße Anna."},
                {"type": "matching", "instruction": "Match words with translations",
                 "pairs": [{"left": "Hallo", "right": "Cześć"}, {"left": "Danke", "right": "Dziękuję"}],
                 "answer": "1-A, 2-B"},
                {"type": "error_correction", "instruction": "Find and correct the error",
                 "content": "Ich heiße Anna und lerne Deutsch.",
                 "answer": "Ich heiße Anna und lerne Deutsch.",
                 "explanation": "'lerne' should be 'lerne' - separable verb with 'lernen'"},
            ],
            "production_task": {
                "instruction": "Write 3 sentences introducing yourself in German",
                "example": "Ich heiße Max. Ich komme aus Polen. Ich lerne Deutsch.",
            },
            "error_review": [],
            "comprehensible_input": {
                "text": "Hallo! Ich heiße Max. Ich komme aus Polen. Ich lerne Deutsch. Das ist schön. Ich mag Deutsch sehr.",
                "new_words": ["schön", "mag"],
                "comprehension_questions": [
                    {"question": "Skąd pochodzi Max?", "answer": "Z Polski"},
                ],
            },
            "interleaved_review": [],
            "output_forcing": {
                "instruction": "Przeczytaj 5 zdań poniżej, zakryj je i spróbuj odtworzyć z pamięci. To trudne ćwiczenie na pamięć długotrwałą.",
                "text": "Hallo, ich heiße Max und ich komme aus Polen. In meiner Freizeit lerne ich Deutsch und treffe meine Freunde. Die Universität ist groß und ich studiere dort seit zwei Jahren. Meine Familie wohnt in Warschau und wir besuchen uns oft am Wochenende. Deutsch zu lernen macht viel Spaß und ich habe schon viele neue Freunde gefunden.",
            },
        }
