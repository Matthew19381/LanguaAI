"""
Topics Router — thematic organization with FSRS spaced repetition.

GET  /api/topics/{user_id}              — list all topics (flat, with filters)
GET  /api/topics/{user_id}/tree         — topics grouped by category
GET  /api/topics/{user_id}/due          — topics due for review
GET  /api/topics/{user_id}/stats        — aggregate statistics
GET  /api/topics/detail/{topic_id}      — single topic with items
POST /api/topics/{topic_id}/review      — submit FSRS review (rating 1-4)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.topic import Topic, TopicItem
from backend.models.user import User
from backend.services import topic_service
from backend.services.exercise_service import skills_to_review
from backend.services.knowledge import entry_details, entry_strength, sync_knowledge_base
from backend.services.mastery import skill_mastery

router = APIRouter()


# ── Request/Response schemas ─────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    rating: int  # 1-4 FSRS rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    user_id: int


class ReviewResponse(BaseModel):
    topic_id: int
    name: str
    memory_strength: float
    interval: int
    repetitions: int
    next_review: str
    is_due: bool


# ── Routes ───────────────────────────────────────────────────────────────────

def _language(db: Session, user_id: int, language: Optional[str]) -> Optional[str]:
    """The learner's target language when the page sends none. Until 3.11.2026 the
    Bank wiedzy page sent none, so no skill got its accuracy (all at 0 %, no stats)."""
    if language:
        return language
    user = db.get(User, user_id)
    return user.target_language if user else None


def _review_reason(info: dict | None) -> str | None:
    if not info:
        return None
    parts = []
    if info.get("due_exercises"):
        parts.append(f"ćwiczenia do powtórki: {info['due_exercises']}")
    if info.get("weak"):
        parts.append("słaba trafność pierwszych prób")
    return ", ".join(parts) or None


def _sync(db: Session, user_id: int) -> None:
    """Bank wiedzy entries exist and are current before any list is shown."""
    user = db.get(User, user_id)
    if user:
        sync_knowledge_base(db, user_id, user.target_language)


@router.get("/{user_id}")
async def list_topics(
    user_id: int,
    language: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query("name", pattern="^(name|strength|due|items)$"),
    db: Session = Depends(get_db),
):
    """List all topics for a user with optional filters."""
    _sync(db, user_id)
    query = db.query(Topic).filter(Topic.user_id == user_id)

    if language:
        query = query.filter(Topic.language == language)
    if category:
        query = query.filter(Topic.category == category)

    topics = query.all()
    # accuracy of skill entries in the learner's language, also when the page sends
    # no language (the list itself stays unfiltered then)
    mlang = _language(db, user_id, language)
    mastery = skill_mastery(db, user_id, mlang) if mlang else {}
    to_review = skills_to_review(db, user_id, mlang) if mlang else {}

    # Update memory strength for all
    result = []
    for t in topics:
        m = mastery.get(t.skill_id) if t.skill_id else None
        reason = _review_reason(to_review.get(t.skill_id)) if t.skill_id else None
        t.memory_strength = (entry_strength(mastery.get(t.skill_id)) if t.skill_id
                             else t.calculate_memory_strength())
        result.append({
            "id": t.id,
            "skill_id": t.skill_id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "cefr_level": t.cefr_level,
            "memory_strength": t.memory_strength,
            "difficulty": t.difficulty,
            "stability": t.stability,
            "retrievability": t.retrievability,
            "fsrs_state": t.fsrs_state,
            "is_due": bool(reason) if t.skill_id else t.is_due(),
            "review_reason": reason,
            "mastery": {k: m[k] for k in ("status", "accuracy", "attempts")} if m else None,
            "days_until_review": t.days_until_review(),
            "items_count": t.total_items,
            "repetitions": t.repetitions,
            "lapses": t.lapses,
            "interval": t.interval,
            "next_review": t.next_review_date.isoformat() if t.next_review_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    # Sort
    if sort == "strength":
        result.sort(key=lambda x: x["memory_strength"], reverse=True)
    elif sort == "due":
        result.sort(key=lambda x: x["days_until_review"])
    elif sort == "items":
        result.sort(key=lambda x: x["items_count"], reverse=True)
    else:
        result.sort(key=lambda x: x["name"].lower())

    return {"topics": result, "count": len(result)}


@router.get("/{user_id}/tree")
async def topic_tree(
    user_id: int,
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get topics organized by category (tree view)."""
    _sync(db, user_id)
    tree = topic_service.get_category_tree(db, user_id, language)
    return {"tree": tree}


@router.get("/{user_id}/hierarchy")
async def topic_hierarchy(
    user_id: int,
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """P2-4 (docs/BACKLOG_UX_2026-08.md): topic->subtopic tree via Topic.parent_id,
    distinct from /tree above (which groups by the fixed category enum)."""
    _sync(db, user_id)
    nodes = topic_service.get_hierarchy_tree(db, user_id, language)
    return {"topics": nodes}


@router.get("/{user_id}/due")
async def due_topics(
    user_id: int,
    language: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get topics due for review, then Bank wiedzy skills to go back to (3.11.2026)."""
    topics = topic_service.get_due_topics(db, user_id, language, limit)
    skills = _skills_due(db, user_id, _language(db, user_id, language))
    return {
        "topics": skills + [{
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "memory_strength": t.memory_strength,
            "difficulty": t.difficulty,
            "stability": t.stability,
            "fsrs_state": t.fsrs_state,
            "days_until_review": t.days_until_review(),
            "items_count": t.total_items,
            "next_review": t.next_review_date.isoformat() if t.next_review_date else None,
        } for t in topics],
        "count": len(topics) + len(skills),
    }


def _skills_due(db: Session, user_id: int, language: Optional[str]) -> list[dict]:
    if not language:
        return []
    to_review = skills_to_review(db, user_id, language)
    if not to_review:
        return []
    mastery = skill_mastery(db, user_id, language)
    rows = db.query(Topic).filter(Topic.user_id == user_id, Topic.language == language,
                                  Topic.skill_id.in_(list(to_review))).all()
    out = [{
        "id": t.id, "skill_id": t.skill_id, "name": t.name, "category": t.category,
        "memory_strength": entry_strength(mastery.get(t.skill_id)),
        "difficulty": t.difficulty, "stability": t.stability, "fsrs_state": t.fsrs_state,
        "days_until_review": 0, "items_count": t.total_items, "next_review": None,
        "review_reason": _review_reason(to_review[t.skill_id]),
        "due_exercises": to_review[t.skill_id]["due_exercises"],
    } for t in rows]
    out.sort(key=lambda x: (-x["due_exercises"], x["memory_strength"]))
    return out


@router.get("/{user_id}/stats")
async def topic_stats(
    user_id: int,
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregate topic statistics."""
    language = _language(db, user_id, language)
    stats = topic_service.get_topic_stats(db, user_id, language)
    if stats.get("total_topics"):
        stats["due_now"] = stats.get("due_now", 0) + len(_skills_due(db, user_id, language))
    return stats


@router.get("/detail/{topic_id}")
async def topic_detail(
    topic_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get single topic with all its items (lessons, tests, exercises)."""
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Verify ownership
    if topic.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this topic")

    knowledge = entry_details(db, topic)
    topic.memory_strength = (entry_strength(knowledge["mastery"]) if knowledge
                             else topic.calculate_memory_strength())

    items = db.query(TopicItem).filter(
        TopicItem.topic_id == topic_id
    ).order_by(TopicItem.created_at.desc()).all()

    return {
        "topic": {
            "id": topic.id,
            "name": topic.name,
            "category": topic.category,
            "description": topic.description,
            "cefr_level": topic.cefr_level,
            "memory_strength": topic.memory_strength,
            "difficulty": topic.difficulty,
            "stability": topic.stability,
            "retrievability": topic.retrievability,
            "fsrs_state": topic.fsrs_state,
            "interval": topic.interval,
            "repetitions": topic.repetitions,
            "lapses": topic.lapses,
            "is_due": topic.is_due(),
            "has_own_reviews": topic.has_own_reviews(),
            "days_until_review": topic.days_until_review(),
            "next_review": topic.next_review_date.isoformat() if topic.next_review_date else None,
            "last_review": topic.last_review_date.isoformat() if topic.last_review_date else None,
            "total_items": topic.total_items,
            "total_reviews": topic.total_reviews,
            "avg_score": topic.avg_score,
        },
        "knowledge": knowledge,
        "items": [{
            "id": item.id,
            "type": item.item_type,
            "item_id": item.item_id,
            "title": item.title,
            "day_number": item.day_number,
            "score": item.score,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        } for item in items],
    }


@router.post("/{topic_id}/review")
async def review_topic(
    topic_id: int,
    review: ReviewRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a review for a topic (FSRS spaced repetition).

    Rating scale:
    1 = Again (forgot completely)
    2 = Hard (recalled with significant difficulty)
    3 = Good (recalled with some effort)
    4 = Easy (instant, effortless recall)
    """
    if review.rating < 1 or review.rating > 4:
        raise HTTPException(status_code=400, detail="Rating must be 1-4")

    # Verify ownership
    topic_check = db.get(Topic, topic_id)
    if not topic_check:
        raise HTTPException(status_code=404, detail="Topic not found")
    if review.user_id and topic_check.user_id != review.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to review this topic")
    if not topic_check.has_own_reviews():
        raise HTTPException(status_code=409, detail="Ten temat nie ma własnych powtórek: "
                                                    "jego fiszki i ćwiczenia są w Powtórkach w hubie")

    try:
        topic = topic_service.review_topic(db, topic_id, review.rating)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "topic_id": topic.id,
        "name": topic.name,
        "memory_strength": topic.memory_strength,
        "difficulty": topic.difficulty,
        "stability": topic.stability,
        "retrievability": topic.retrievability,
        "fsrs_state": topic.fsrs_state,
        "interval": topic.interval,
        "repetitions": topic.repetitions,
        "lapses": topic.lapses,
        "next_review": topic.next_review_date.isoformat() if topic.next_review_date else None,
        "is_due": topic.is_due(),
    }
