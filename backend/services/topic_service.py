"""
Topic Service — topic extraction from lesson content, SM-2 spaced repetition,
and thematic organization of learning materials.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.topic import ItemType, Topic, TopicCategory, TopicItem
from backend.services.gemini_service import generate_json

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# TOPIC EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

async def extract_topics_from_lesson(content: dict, language: str, cefr_level: str) -> list[dict]:
    """
    Use AI to extract topics from lesson content.

    Returns list of dicts: [{"name": "Perfekt", "category": "grammar", "description": "..."}]
    """
    # Build a summary of the lesson for topic extraction
    summary_parts = []
    if isinstance(content, dict):
        if "grammar" in content:
            g = content["grammar"]
            if isinstance(g, dict):
                summary_parts.append(f"Grammar: {g.get('explanation', '')[:200]}")
            elif isinstance(g, str):
                summary_parts.append(f"Grammar: {g[:200]}")
        if "vocabulary" in content:
            v = content["vocabulary"]
            if isinstance(v, list):
                words = [w.get("word", "") if isinstance(w, dict) else str(w) for w in v[:10]]
                summary_parts.append(f"Vocabulary: {', '.join(words)}")
        if "dialogue" in content:
            summary_parts.append(f"Dialogue present: {str(content['dialogue'])[:150]}")
        if "reading" in content:
            summary_parts.append(f"Reading: {str(content['reading'])[:150]}")
        if "exercises" in content:
            summary_parts.append(f"Exercises: {len(content.get('exercises', []))} items")

    summary = "\n".join(summary_parts) if summary_parts else str(content)[:500]

    prompt = f"""Analyze this {language} lesson (CEFR {cefr_level}) and extract the main topics/themes.

Lesson summary:
{summary}

Respond with JSON array of topics. Each topic should have:
- "name": short topic name in {language} (e.g. "Perfekt", "Konjunktiv II", "Trennbare Verben")
- "category": one of: grammar, vocabulary, pronunciation, listening, reading, writing, speaking, culture, idioms, other
- "description": 1-sentence description in Polish explaining what this topic covers

Extract 1-5 topics. Be specific (not just "Grammar" but "Perfekt mit haben/sein").

Respond ONLY with valid JSON array."""

    try:
        result = await generate_json(prompt)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "topics" in result:
            return result["topics"]
        return []
    except Exception as e:
        logger.error(f"Topic extraction failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# TOPIC CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def get_or_create_topic(db: Session, user_id: int, language: str, name: str,
                        category: str = TopicCategory.GRAMMAR,
                        description: str = None,
                        cefr_level: str = None) -> Topic:
    """Get existing topic or create a new one."""
    topic = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.language == language,
        func.lower(Topic.name) == func.lower(name.strip())
    ).first()

    if topic:
        if description and not topic.description:
            topic.description = description
        if cefr_level and not topic.cefr_level:
            topic.cefr_level = cefr_level
        return topic

    topic = Topic(
        user_id=user_id,
        language=language,
        name=name.strip(),
        category=category,
        description=description,
        cefr_level=cefr_level,
    )
    db.add(topic)
    db.flush()
    return topic


def assign_item_to_topic(db: Session, topic_id: int, item_type: str,
                         item_id: int, title: str = None,
                         day_number: int = None, score: float = None) -> TopicItem:
    """Assign a lesson/test/exercise to a topic. Creates duplicate-safe."""
    # Check if already assigned
    existing = db.query(TopicItem).filter(
        TopicItem.topic_id == topic_id,
        TopicItem.item_type == item_type,
        TopicItem.item_id == item_id
    ).first()

    if existing:
        if score is not None:
            existing.score = score
        return existing

    item = TopicItem(
        topic_id=topic_id,
        item_type=item_type,
        item_id=item_id,
        title=title,
        day_number=day_number,
        score=score,
    )
    db.add(item)

    # Update topic total_items count
    topic = db.get(Topic, topic_id)
    if topic:
        topic.total_items = db.query(TopicItem).filter(
            TopicItem.topic_id == topic_id
        ).count() + 1
        topic.memory_strength = topic.calculate_memory_strength()

    return item


async def process_lesson_topics(db: Session, lesson, content: dict) -> list[Topic]:
    """
    Extract topics from a lesson and create Topic + TopicItem records.
    Called after lesson generation.
    """
    topics_data = await extract_topics_from_lesson(
        content, lesson.language, lesson.cefr_level
    )

    created_topics = []
    for td in topics_data:
        topic = get_or_create_topic(
            db=db,
            user_id=lesson.user_id,
            language=lesson.language,
            name=td.get("name", "Unnamed"),
            category=td.get("category", TopicCategory.GRAMMAR),
            description=td.get("description"),
            cefr_level=lesson.cefr_level,
        )
        assign_item_to_topic(
            db=db,
            topic_id=topic.id,
            item_type=ItemType.LESSON,
            item_id=lesson.id,
            title=lesson.title,
            day_number=lesson.day_number,
        )
        created_topics.append(topic)

    db.commit()
    for t in created_topics:
        db.refresh(t)

    return created_topics


async def process_test_topics(db: Session, test_result, test_content: dict,
                             language: str, cefr_level: str) -> list[Topic]:
    """Extract topics from test results and assign test to topics."""
    topics_data = await extract_topics_from_lesson(test_content, language, cefr_level)

    created_topics = []
    score = test_result.score if hasattr(test_result, 'score') else None

    for td in topics_data:
        topic = get_or_create_topic(
            db=db,
            user_id=test_result.user_id,
            language=language,
            name=td.get("name", "Unnamed"),
            category=td.get("category", TopicCategory.GRAMMAR),
            description=td.get("description"),
            cefr_level=cefr_level,
        )
        assign_item_to_topic(
            db=db,
            topic_id=topic.id,
            item_type=ItemType.TEST,
            item_id=test_result.id,
            title=f"Test: {td.get('name', 'Unknown')}",
            score=score,
        )
        created_topics.append(topic)

    db.commit()
    return created_topics


# ═══════════════════════════════════════════════════════════════════════════════
# SM-2 REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def review_topic(db: Session, topic_id: int, rating: int) -> Topic:
    """
    Review a topic with FSRS spaced repetition.

    Args:
        topic_id: Topic to review
        rating: 1-4 (1=Again, 2=Hard, 3=Good, 4=Easy)

    Returns:
        Updated Topic object
    """
    topic = db.get(Topic, topic_id)
    if not topic:
        raise ValueError(f"Topic {topic_id} not found")

    topic.apply_fsrs(rating)

    # Update avg_score (normalize 1-4 → 0-5 scale for backward compat)
    normalized_score = (rating - 1) / 3.0 * 5.0
    if topic.total_reviews > 0:
        topic.avg_score = round(
            ((topic.avg_score * (topic.total_reviews - 1)) + normalized_score) / topic.total_reviews, 2
        )

    db.commit()
    db.refresh(topic)
    return topic


def get_due_topics(db: Session, user_id: int, language: str = None, limit: int = 20) -> list[Topic]:
    """Get topics due for review, ordered by most overdue first."""
    query = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.total_items > 0,
        (Topic.next_review_date <= datetime.now(timezone.utc)) | (Topic.next_review_date == None),
    )
    if language:
        query = query.filter(Topic.language == language)

    due = query.order_by(Topic.next_review_date.asc()).limit(limit).all()
    return due


def get_topic_stats(db: Session, user_id: int, language: str = None) -> dict:
    """Get aggregate topic statistics for a user."""
    query = db.query(Topic).filter(Topic.user_id == user_id)
    if language:
        query = query.filter(Topic.language == language)

    topics = query.all()
    if not topics:
        return {
            "total_topics": 0,
            "due_now": 0,
            "avg_memory_strength": 0.0,
            "mastered": 0,  # memory_strength >= 0.8
            "learning": 0,  # 0.3-0.8
            "new": 0,       # < 0.3
        }

    strengths = [t.memory_strength for t in topics]
    due_count = sum(1 for t in topics if t.is_due())

    return {
        "total_topics": len(topics),
        "due_now": due_count,
        "avg_memory_strength": round(sum(strengths) / len(strengths), 2),
        "mastered": sum(1 for s in strengths if s >= 0.8),
        "learning": sum(1 for s in strengths if 0.3 <= s < 0.8),
        "new": sum(1 for s in strengths if s < 0.3),
    }


def get_category_tree(db: Session, user_id: int, language: str = None) -> dict:
    """
    Get topics organized by category for tree view.

    Returns: {category: [{topic_id, name, memory_strength, due, items_count, ...}]}
    """
    query = db.query(Topic).filter(Topic.user_id == user_id)
    if language:
        query = query.filter(Topic.language == language)

    topics = query.order_by(Topic.category, Topic.name).all()

    tree = {}
    for t in topics:
        cat = t.category or TopicCategory.OTHER
        if cat not in tree:
            tree[cat] = []
        tree[cat].append({
            "id": t.id,
            "name": t.name,
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
        })

    return tree


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS (for FastAPI BackgroundTasks)
# ═══════════════════════════════════════════════════════════════════════════════

async def process_lesson_topics_bg(user_id: int, language: str, cefr_level: str,
                                    lesson_id: int, day_number: int,
                                    lesson_title: str, content: dict) -> None:
    """
    Background task version of process_lesson_topics.
    Creates its own DB session — safe for FastAPI BackgroundTasks.
    """
    db = SessionLocal()
    try:
        # Reconstruct a minimal lesson-like object
        class _LessonProxy:
            pass
        proxy = _LessonProxy()
        proxy.user_id = user_id
        proxy.language = language
        proxy.cefr_level = cefr_level
        proxy.id = lesson_id
        proxy.day_number = day_number
        proxy.title = lesson_title

        topics_data = await extract_topics_from_lesson(content, language, cefr_level)

        for td in topics_data:
            topic = get_or_create_topic(
                db=db,
                user_id=user_id,
                language=language,
                name=td.get("name", "Unnamed"),
                category=td.get("category", TopicCategory.GRAMMAR),
                description=td.get("description"),
                cefr_level=cefr_level,
            )
            assign_item_to_topic(
                db=db,
                topic_id=topic.id,
                item_type=ItemType.LESSON,
                item_id=lesson_id,
                title=lesson_title,
                day_number=day_number,
            )

        db.commit()
        logger.info(f"Extracted {len(topics_data)} topics for lesson {lesson_id}")
    except Exception as e:
        logger.error(f"Background topic extraction failed for lesson {lesson_id}: {e}")
        db.rollback()
    finally:
        db.close()
