import json
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_user_or_404
from backend.models.lesson import Lesson
from backend.config import settings
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)
router = APIRouter()

LANG_TO_RELEVANCE = {
    "German": "de",
    "English": "en",
    "Spanish": "es",
    "Russian": "ru",
    "Chinese": "zh-Hans",
}

CEFR_DESCRIPTIONS = {
    "A1": "bardzo wolna mowa, krótkie zdania, absolutny początkujący",
    "A2": "prosta mowa, codzienne tematy, elementarny poziom",
    "B1": "średnie tempo, codzienne rozmowy, poziom średnio-zaawansowany",
    "B2": "naturalne tempo mówców native, różne tematy",
    "C1": "zaawansowany, złożone tematy, autentyczne materiały",
    "C2": "biegły, dowolne autentyczne treści",
}


def _extract_lesson_context(lesson: Lesson) -> dict:
    """Pull topic, title, and top vocabulary words from a lesson."""
    topic = lesson.topic or ""
    title = lesson.title or ""
    vocab_words = []
    try:
        content = json.loads(lesson.content)
        vocab = content.get("vocabulary", [])
        vocab_words = [v.get("word", "") for v in vocab[:8] if v.get("word")]
    except (json.JSONDecodeError, TypeError):
        pass
    return {"topic": topic, "title": title, "vocab": vocab_words}


@with_model("news")
async def _suggest_queries(
    language: str,
    cefr_level: str,
    native_language: str,
    lesson_context: dict | None = None,
    include_polish: bool = False,
) -> list[str]:
    cefr_desc = CEFR_DESCRIPTIONS.get(cefr_level, "")

    if lesson_context:
        topic = lesson_context.get("topic", "")
        prompt = f"""You are helping a {native_language} speaker learn {language} at CEFR {cefr_level}.

Today's lesson topic: "{topic}"

Generate 6{'+2 Polish' if include_polish else ''} YouTube search queries:
1. First 3: EXACTLY about the topic "{topic}" in {language}
2. Next 3: General {language} learning content for {cefr_level} ({cefr_desc})
{'''3. Last 2: Polish-language videos explaining {language} (e.g., "niemiecka gramatyka po polsku")''' if include_polish else ''}

Important:
- Videos must be SPOKEN in {language} (not just subtitles)
- Queries can be in English or {language}
- A1/A2: slow speech, educational channels
- B1+: authentic content (vlogs, podcasts, news)

Return JSON: {{"queries": [...], "topic_queries": [0,1,2]}}"""
    else:
        prompt = f"""You are helping a {native_language} speaker learn {language} at CEFR {cefr_level} ({cefr_desc}).

Generate {8 if include_polish else 6} YouTube search queries for general {language} learning.
{'''Include 2 Polish queries about learning {language} (e.g., "polskie lekcje niemieckiego")''' if include_polish else ''}

Videos must be SPOKEN in {language}.

Return JSON: {{"queries": [...], "topic_queries": []}}"""

    try:
        result = await generate_json(prompt)
        return result.get("queries", []), result.get("topic_queries", [])
    except (httpx.RequestError, ValueError, KeyError):
        # Fallback queries if AI fails
        base = {
            "A1": [f"{language} for beginners slow", f"easy {language} A1", f"learn {language} basics"],
            "A2": [f"{language} A2 conversation", f"simple {language} practice"],
            "B1": [f"{language} B1 listening", f"{language} everyday conversation"],
            "B2": [f"{language} news slow", f"{language} podcast"],
            "C1": [f"{language} documentary", f"authentic {language}"],
            "C2": [f"{language} native content", f"{language} advanced discussion"],
        }.get(cefr_level, [f"learn {language}"])
        if include_polish:
            base += [f"learn {language} in Polish", f"{language} grammar explained in Polish"]
        return base, []


async def _search_youtube(query: str, language_code: str, max_results: int = 6) -> list[dict]:
    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(status_code=503, detail="Brak klucza YouTube API")

    params = {
        "key": settings.YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": language_code,
        "videoEmbeddable": "true",
        "safeSearch": "moderate",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://www.googleapis.com/youtube/v3/search", params=params)
        if resp.status_code != 200:
            logger.error(f"YouTube API error: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=502, detail="Błąd YouTube API")
        data = resp.json()

    videos = []
    for item in data.get("items", []):
        vid_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not vid_id:
            continue
        videos.append({
            "video_id": vid_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", "")[:200],
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "published_at": snippet.get("publishedAt", "")[:10],
            "url": f"https://www.youtube.com/watch?v={vid_id}",
        })
    return videos


@router.get("/api/youtube/search")
async def search_videos(
    user_id: int,
    query: str = Query(default=""),
    include_polish: bool = Query(default=False, alias="include_polish"),
    db: Session = Depends(get_db)
):
    user = get_user_or_404(db, user_id)

    language = user.target_language
    cefr_level = user.cefr_level
    native_language = user.native_language
    lang_code = LANG_TO_RELEVANCE.get(language, "en")

    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(status_code=503, detail="Brak klucza YouTube API")

    try:
        if query.strip():
            videos = await _search_youtube(f"{query} {language}", lang_code)
            return {
                "videos": videos,
                "query_used": query,
                "suggested": False,
            }

        # Get most recent lesson for topic context
        latest_lesson = (
            db.query(Lesson)
            .filter(Lesson.user_id == user_id, Lesson.language == language)
            .order_by(Lesson.created_at.desc())
            .first()
        )
        lesson_context = _extract_lesson_context(latest_lesson) if latest_lesson else None

        queries, topic_query_indices = await _suggest_queries(
            language, cefr_level, native_language, lesson_context, include_polish
        )
        if not queries:
            queries = [f"learn {language} {cefr_level}"]

        # Fetch topic-related videos first (higher priority), then general
        topic_videos = []
        general_videos = []
        seen_ids = set()

        topic_qs = [queries[i] for i in topic_query_indices if i < len(queries)]
        general_qs = [q for i, q in enumerate(queries) if i not in topic_query_indices]

        if topic_qs:
            results = await _search_youtube(topic_qs[0], lang_code, max_results=5)
            for v in results:
                if v["video_id"] not in seen_ids:
                    topic_videos.append({**v, "is_lesson_related": True})
                    seen_ids.add(v["video_id"])

        if general_qs:
            results = await _search_youtube(general_qs[0], lang_code, max_results=6)
            for v in results:
                if v["video_id"] not in seen_ids:
                    general_videos.append({**v, "is_lesson_related": False})
                    seen_ids.add(v["video_id"])

        # Fill up if not enough
        if len(topic_videos) + len(general_videos) < 4 and len(general_qs) > 1:
            extra = await _search_youtube(general_qs[1], lang_code, max_results=4)
            for v in extra:
                if v["video_id"] not in seen_ids:
                    general_videos.append({**v, "is_lesson_related": False})
                    seen_ids.add(v["video_id"])

        all_videos = topic_videos + general_videos

        return {
            "videos": all_videos,
            "query_used": topic_qs[0] if topic_qs else (general_qs[0] if general_qs else ""),
            "suggested_queries": queries,
            "topic_queries": topic_qs,
            "suggested": True,
            "cefr_level": cefr_level,
            "language": language,
            "lesson_topic": lesson_context.get("topic") if lesson_context else None,
            "lesson_title": lesson_context.get("title") if lesson_context else None,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("YouTube search error")
        raise HTTPException(status_code=500, detail="Failed to search YouTube videos")
