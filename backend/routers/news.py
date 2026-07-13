import logging
import time
import httpx
from collections import OrderedDict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_user_or_404
from backend.services.news_service import get_news_for_user

logger = logging.getLogger(__name__)
router = APIRouter()

# LRU cache: key = (user_id, language) -> {"timestamp": float, "data": list}
_news_cache: OrderedDict = OrderedDict()
_CACHE_MAX_SIZE = 100  # max cached entries
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours


def _cache_prune():
    """Remove expired entries and enforce max size."""
    now = time.time()
    expired = [k for k, v in _news_cache.items() if now - v["timestamp"] > CACHE_TTL_SECONDS]
    for k in expired:
        del _news_cache[k]
    while len(_news_cache) > _CACHE_MAX_SIZE:
        _news_cache.popitem(last=False)


@router.get("/api/news/{user_id}")
async def get_news(user_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Fetch and simplify news articles for the user's target language and CEFR level."""
    user = get_user_or_404(db, user_id)

    _cache_prune()
    cache_key = (user_id, user.target_language)
    now = time.time()
    cached = _news_cache.get(cache_key)
    if cached and (now - cached["timestamp"]) < CACHE_TTL_SECONDS:
        logger.info(f"Returning cached news for user {user_id} / {user.target_language}")
        return {
            "success": True,
            "language": user.target_language,
            "cefr_level": user.cefr_level,
            "articles": cached["data"],
            "cached": True,
        }

    try:
        articles = await get_news_for_user(
            language=user.target_language,
            cefr_level=user.cefr_level,
            native_language=user.native_language,
            limit=min(limit, 8),
        )
        _news_cache[cache_key] = {"timestamp": now, "data": articles}
        return {
            "success": True,
            "language": user.target_language,
            "cefr_level": user.cefr_level,
            "articles": articles,
            "cached": False,
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error fetching news: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception(f"Unexpected error fetching news for user {user_id}")
        raise HTTPException(status_code=500, detail="Failed to fetch news")
