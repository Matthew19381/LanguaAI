"""
Topics Router — thematic organization with FSRS spaced repetition.

GET  /api/topics/{user_id}              — list all topics (flat, with filters)
GET  /api/topics/{user_id}/tree         — topics grouped by category
GET  /api/topics/{user_id}/due          — topics due for review
GET  /api/topics/{user_id}/stats        — aggregate statistics
GET  /api/topics/detail/{topic_id}      — single topic with items
POST /api/topics/{topic_id}/review      — submit FSRS review (rating 1-4)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.models.topic import Topic, TopicItem
from backend.services import topic_service

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

@router.get("/{user_id}")
async def list_topics(
    user_id: int,
    language: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query("name", regex="^(name|strength|due|items)$"),
    db: Session = Depends(get_db),
):
    """List all topics for a user with optional filters."""
    query = db.query(Topic).filter(Topic.user_id == user_id)

    if language:
        query = query.filter(Topic.language == language)
    if category:
        query = query.filter(Topic.category == category)

    topics = query.all()

    # Update memory strength for all
    result = []
    for t in topics:
        t.memory_strength = t.calculate_memory_strength()
        result.append({
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "cefr_level": t.cefr_level,
            "memory_strength": t.memory_strength,
            "difficulty": t.difficulty,
            "stability": t.stability,
            "retrievability": t.retrievability,
            "fsrs_state": t.fsrs_state,
            "is_due": t.is_due(),
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
    tree = topic_service.get_category_tree(db, user_id, language)
    return {"tree": tree}


@router.get("/{user_id}/due")
async def due_topics(
    user_id: int,
    language: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get topics due for review."""
    topics = topic_service.get_due_topics(db, user_id, language, limit)
    return {
        "topics": [{
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
        "count": len(topics),
    }


@router.get("/{user_id}/stats")
async def topic_stats(
    user_id: int,
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregate topic statistics."""
    stats = topic_service.get_topic_stats(db, user_id, language)
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

    topic.memory_strength = topic.calculate_memory_strength()

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
            "days_until_review": topic.days_until_review(),
            "next_review": topic.next_review_date.isoformat() if topic.next_review_date else None,
            "last_review": topic.last_review_date.isoformat() if topic.last_review_date else None,
            "total_items": topic.total_items,
            "total_reviews": topic.total_reviews,
            "avg_score": topic.avg_score,
        },
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
