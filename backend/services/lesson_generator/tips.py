"""Daily tips and language Q&A."""
import logging

from backend.services.gemini_service import generate_json, generate_text, with_model

logger = logging.getLogger(__name__)


@with_model("lesson")
async def answer_language_question(
    question: str,
    cefr_level: str,
    language: str,
    native_language: str,
) -> str:
    prompt = f"""You are an expert {language} language tutor. A student (CEFR level {cefr_level}, native {native_language} speaker) asks:

"{question}"

Provide a clear, helpful explanation appropriate for their level.
Use examples in {language} with {native_language} translations.
Keep the explanation concise but thorough."""

    try:
        return await generate_text(prompt)
    except Exception as e:
        logger.error(f"Error answering language question: {e}")
        return "I apologize, but I couldn't generate an answer right now. Please try again later."


@with_model("lesson")
async def generate_daily_tips(
    cefr_level: str,
    language: str,
    native_language: str,
    recent_topics: list[str] | None = None,
    weak_topics: list[str] | None = None,
) -> dict:
    # Ground the tips in what the learner is actually studying, so they feel
    # personal instead of generic. At least half the tips should reference these.
    context = ""
    if recent_topics:
        context += f"\nThe learner is CURRENTLY studying these topics: {', '.join(recent_topics[:8])}."
    if weak_topics:
        context += f"\nThey are WEAKEST at (low mastery): {', '.join(weak_topics[:6])}."
    if context:
        context += (
            f"\nAt least 2 of the 4 tips MUST directly target these current/weak"
            f" topics — name the topic and give a concrete {language} example from it."
        )

    prompt = f"""Generate 4 helpful daily language learning tips for a {native_language} speaker learning {language} at CEFR level {cefr_level}.
{context}

CRITICAL: You MUST write the "title" and "content" fields ENTIRELY in {native_language}. Do NOT use English in these fields. The "source" field can be in English.

Tips should cover different aspects: grammar, vocabulary, culture, and memory techniques.
Each tip must cite a real scientific source (researcher name, year, study/theory name).

Return JSON:
{{
    "tips": [
        {{
            "title": "Tytuł wskazówki po {native_language}",
            "content": "Szczegółowa treść wskazówki w języku {native_language} z przykładami w języku {language}",
            "type": "grammar|vocabulary|culture|memory_tip",
            "source": "Krashen (1982) - Input Hypothesis"
        }}
    ]
}}

Make tips practical, specific, and actionable. Include {language} examples where relevant.
Use real citations: e.g. Ebbinghaus (1885), Krashen (1982), Nation (2001), Baddeley (1986), Swain (1985)."""

    try:
        return await generate_json(prompt)
    except Exception as e:
        logger.error(f"Error generating daily tips: {e}")
        return {
            "tips": [
                {
                    "title": "Ćwicz codziennie",
                    "content": f"Systematyczność to klucz do nauki {language}. Nawet 15 minut dziennie jest lepsze niż 2 godziny raz w tygodniu.",
                    "type": "memory_tip",
                    "source": "Ebbinghaus (1885) - Spacing Effect",
                },
                {
                    "title": "Ucz się w kontekście",
                    "content": f"Nie zapamiętuj pojedynczych słów — ucz się słów {language} w zdaniach, by lepiej je zapamiętać.",
                    "type": "vocabulary",
                    "source": "Nation (2001) - Learning Vocabulary in Another Language",
                },
                {
                    "title": "Słuchaj native speakerów",
                    "content": f"Oglądaj filmy lub słuchaj muzyki po {language}, by przyzwyczaić ucho do języka.",
                    "type": "culture",
                    "source": "Krashen (1982) - Input Hypothesis",
                },
                {
                    "title": "Podstawy gramatyczne",
                    "content": f"Opanuj podstawową budowę zdań w {language} zanim przejdziesz do bardziej złożonych form.",
                    "type": "grammar",
                    "source": "Baddeley (1986) - Working Memory Model",
                },
            ]
        }
