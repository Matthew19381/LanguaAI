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
from backend.services.gemini_service import generate_json, with_model

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# TOPIC EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@with_model("lesson")
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
- "name": short, SPECIFIC topic name in {language} (e.g. "Perfekt mit haben", "Konjunktiv II", "Trennbare Verben" — not just "Grammar" or "Verbs")
- "category": one of: grammar, vocabulary, pronunciation, listening, reading, writing, speaking, culture, idioms, other
- "description": 1-sentence description in Polish explaining what this topic covers
- "parent_topic": OPTIONAL — the name (in Polish) of the broader umbrella topic this one
  belongs under, if there is an obvious one, e.g. "Perfekt mit haben" -> parent_topic
  "Czasy przeszłe" (Past tenses), "Konjunktiv II" -> parent_topic "Tryb warunkowy"
  (Conditional mood). Omit or leave empty when the topic IS already the broad umbrella
  (don't invent a parent just to have one — most topics won't need this field).

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


def get_or_create_topic_with_parent(db: Session, user_id: int, language: str, name: str,
                                     category: str = TopicCategory.GRAMMAR,
                                     description: str = None,
                                     cefr_level: str = None,
                                     parent_topic_name: str = None) -> Topic:
    """Like get_or_create_topic, but also resolves an optional umbrella/parent
    topic (P2-4, docs/BACKLOG_UX_2026-08.md — Bank wiedzy hierarchy). The parent
    is itself just a plain topic (get_or_create_topic, no parent of its own) —
    this keeps the hierarchy at the two levels the AI prompt asks for (broad
    umbrella -> specific topic) without needing special-case modeling.

    parent_id is only ever set once: if a topic already has one (from an
    earlier lesson), a later lesson proposing a different parent does NOT
    overwrite it — the AI's parent suggestion isn't perfectly consistent
    lesson to lesson, and flip-flopping a topic's place in the tree on every
    regeneration would be worse than leaving it where a human would expect.
    """
    parent_name = (parent_topic_name or "").strip()
    parent_id = None
    if parent_name and parent_name.lower() != name.strip().lower():
        parent = get_or_create_topic(db, user_id, language, parent_name, category=category, cefr_level=cefr_level)
        db.flush()
        parent_id = parent.id

    topic = get_or_create_topic(db, user_id, language, name, category=category,
                                 description=description, cefr_level=cefr_level)
    if parent_id and not topic.parent_id and topic.id != parent_id:
        topic.parent_id = parent_id
    return topic


def get_hierarchy_tree(db: Session, user_id: int, language: str = None) -> list[dict]:
    """Build the Topic.parent_id hierarchy for the 'Bank wiedzy' tree view
    (P2-4). Root nodes are topics with no resolved parent (either parent_id is
    NULL, or it points at a topic that no longer exists/belongs to this user);
    everything else nests under its parent, recursively (the AI prompt asks
    for two levels, but nothing here assumes that depth).

    mastery_percent per node is round(Topic.memory_strength * 100) — the same
    FSRS-derived value already shown everywhere else in this app (list view,
    category tree, topic detail), not a new metric invented for this view.
    group_mastery_percent on a node WITH subtopics is a plain, unweighted
    average of the node's own mastery (if it has directly-assigned items) and
    its subtopics' mastery — an aggregate for orientation, not a research
    metric; see docs/NEURO_FEATURES.md for the evidence-level note this
    project's standard requires before shipping anything mastery-adjacent.
    """
    query = db.query(Topic).filter(Topic.user_id == user_id)
    if language:
        query = query.filter(Topic.language == language)
    topics = query.all()

    by_id = {t.id: t for t in topics}
    children_of: dict[int, list[Topic]] = {}
    roots = []
    for t in topics:
        if t.parent_id and t.parent_id in by_id and t.parent_id != t.id:
            children_of.setdefault(t.parent_id, []).append(t)
        else:
            roots.append(t)

    def build(t: Topic) -> dict:
        kids = sorted(children_of.get(t.id, []), key=lambda x: x.name.lower())
        subtopics = [build(k) for k in kids]
        node = {
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "cefr_level": t.cefr_level,
            "mastery_percent": round(t.memory_strength * 100),
            "is_due": t.is_due(),
            "days_until_review": t.days_until_review(),
            "items_count": t.total_items,
            "has_own_items": t.total_items > 0,
            "subtopics": subtopics,
        }
        if subtopics:
            values = [s.get("group_mastery_percent", s["mastery_percent"]) for s in subtopics]
            if node["has_own_items"]:
                values.append(node["mastery_percent"])
            node["group_mastery_percent"] = round(sum(values) / len(values)) if values else 0
        return node

    return sorted([build(r) for r in roots], key=lambda n: n["name"].lower())


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
        topic = get_or_create_topic_with_parent(
            db=db,
            user_id=lesson.user_id,
            language=lesson.language,
            name=td.get("name", "Unnamed"),
            category=td.get("category", TopicCategory.GRAMMAR),
            description=td.get("description"),
            cefr_level=lesson.cefr_level,
            parent_topic_name=td.get("parent_topic"),
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
        topic = get_or_create_topic_with_parent(
            db=db,
            user_id=test_result.user_id,
            language=language,
            name=td.get("name", "Unnamed"),
            category=td.get("category", TopicCategory.GRAMMAR),
            description=td.get("description"),
            cefr_level=cefr_level,
            parent_topic_name=td.get("parent_topic"),
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
            topic = get_or_create_topic_with_parent(
                db=db,
                user_id=user_id,
                language=language,
                name=td.get("name", "Unnamed"),
                category=td.get("category", TopicCategory.GRAMMAR),
                description=td.get("description"),
                cefr_level=cefr_level,
                parent_topic_name=td.get("parent_topic"),
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
