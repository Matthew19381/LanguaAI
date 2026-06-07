"""Conversation scenario generation and analysis."""
import logging
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


@with_model("conversation")
async def generate_conversation_scenario(
    topic: str,
    cefr_level: str,
    user_errors: list,
    language: str,
    native_language: str,
) -> dict:
    error_context = ""
    if user_errors:
        error_context = f"Help the student practice areas where they made errors: {user_errors[:3]}"

    prompt = f"""Create a conversation practice scenario for a {language} learner.

Student profile:
- CEFR level: {cefr_level}
- Native language: {native_language}
- Topic to practice: {topic}
{error_context}

Design an engaging, realistic conversation scenario appropriate for level {cefr_level}.

Return JSON:
{{
    "scenario": "Brief description of the situation",
    "ai_role": "Your role in this conversation (e.g., 'a shopkeeper in Berlin')",
    "user_role": "The student's role (e.g., 'a tourist buying souvenirs')",
    "suggested_phrases": [
        "Useful phrase 1 in {language}",
        "Useful phrase 2 in {language}",
        "Useful phrase 3 in {language}",
        "Useful phrase 4 in {language}",
        "Useful phrase 5 in {language}"
    ],
    "system_prompt": "You are playing the role of [AI role] in a {language} conversation practice. The student is at CEFR {cefr_level} level. Always respond in {language}. If the student makes an error, gently incorporate the correct form naturally in your response. Keep sentences appropriate for {cefr_level} level. Be encouraging and patient. If asked for help, provide it in {native_language}.",
    "opening_line": "The first line you'll say to start the conversation in {language}"
}}"""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating conversation scenario: {e}")
        return {
            "scenario": f"You are at a {language}-speaking café ordering food and drinks.",
            "ai_role": "A friendly café waiter/waitress",
            "user_role": "A customer visiting for the first time",
            "suggested_phrases": [
                "Ich möchte... (I would like...)",
                "Was empfehlen Sie? (What do you recommend?)",
                "Die Rechnung, bitte. (The bill, please.)",
                "Danke schön! (Thank you very much!)",
                "Entschuldigung... (Excuse me...)",
            ],
            "system_prompt": f"You are a friendly café waiter in a German café. The student is at CEFR {cefr_level} level. Respond only in German. Be patient and encouraging.",
            "opening_line": "Guten Tag! Was darf ich Ihnen bringen?",
        }


@with_model("conversation")
async def analyze_conversation(
    conversation_history: list,
    cefr_level: str,
    language: str,
    native_language: str,
) -> dict:
    prompt = f"""Analyze this {language} conversation practice session for a {native_language} speaker at CEFR {cefr_level}.

Conversation:
{conversation_history}

Produce a DETAILED analysis with SPECIFIC error categories. Use these category types:
- "grammar" — grammatical rule violations (wrong case, wrong tense, wrong conjugation)
- "vocabulary" — wrong word choice, false friends, missing vocabulary
- "word_order" — incorrect sentence structure / word placement
- "articles" — wrong article (der/die/das/ein/eine), gender errors
- "verb_conjugation" — wrong verb form, wrong auxiliary verb
- "prepositions" — wrong preposition usage
- "pronunciation_spelling" — spelling errors that suggest pronunciation issues
- "fluency" — overly simple/broken sentences for the level
- "register" — too formal/informal for the context

Severity rules:
- "critical" — errors that impede comprehension or break fundamental grammar rules (wrong verb form, wrong case, missing key word)
- "minor" — stylistic issues, slight awkwardness, or non-essential improvement suggestions

Return JSON:
{{
    "summary": "2-3 sentence overall assessment in {native_language}",
    "errors": [
        {{
            "type": "grammar|vocabulary|word_order|articles|verb_conjugation|prepositions|pronunciation_spelling|fluency|register",
            "severity": "critical|minor",
            "question": "the problematic phrase the student wrote",
            "correct_answer": "the corrected form",
            "explanation": "brief explanation in {native_language} why it's wrong and what rule applies"
        }}
    ],
    "category_advice": {{
        "grammar": "Specific advice on what grammar topics to study",
        "vocabulary": "Specific vocabulary areas to improve",
        "word_order": "Word order rules to practice"
    }},
    "recommendations": ["Specific actionable recommendation 1", "Specific recommendation 2", "Specific recommendation 3"],
    "score": 75,
    "strengths": ["What the student did well 1", "What the student did well 2"]
}}

Note: category_advice should only include categories where errors were found."""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error analyzing conversation: {e}")
        return {
            "summary": "Conversation analysis complete. Good effort in practicing!",
            "errors": [],
            "category_advice": {},
            "recommendations": [
                "Continue practicing daily conversations",
                "Focus on grammar accuracy",
                "Expand vocabulary in this topic area",
            ],
            "score": 70,
            "strengths": ["Attempted communication", "Used target language"],
        }


@with_model("conversation")
async def analyze_pasted_conversation(
    pasted_text: str,
    cefr_level: str,
    language: str,
    native_language: str,
) -> dict:
    prompt = f"""A {native_language} speaker learning {language} at CEFR {cefr_level} pasted this conversation/text for analysis.
Analyze their {language} usage for errors and provide detailed feedback.

Text to analyze:
{pasted_text}

Instructions:
- Only analyze the LEARNER's lines (not the AI/tutor responses)
- If it's unclear who wrote what, analyze all {language} text
- Be specific about error types

Use these error category types:
- "grammar", "vocabulary", "word_order", "articles", "verb_conjugation", "prepositions", "pronunciation_spelling", "fluency", "register"

Return JSON:
{{
    "summary": "2-3 sentence overall assessment in {native_language}",
    "errors": [
        {{
            "type": "grammar|vocabulary|word_order|articles|verb_conjugation|prepositions|pronunciation_spelling|fluency|register",
            "question": "the problematic phrase",
            "correct_answer": "the corrected form",
            "explanation": "brief explanation in {native_language}"
        }}
    ],
    "category_advice": {{
        "grammar": "what grammar to study"
    }},
    "recommendations": ["recommendation 1", "recommendation 2"],
    "score": 70,
    "strengths": ["strength 1"]
}}"""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error analyzing pasted conversation: {e}")
        return {
            "summary": "Analiza zakończona.",
            "errors": [],
            "category_advice": {},
            "recommendations": ["Ćwicz codziennie konwersacje"],
            "score": 0,
            "strengths": [],
        }
