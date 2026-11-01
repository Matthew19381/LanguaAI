"""
Topic & TopicItem models — thematic organization of lessons/tests/exercises
with SM-2 spaced repetition per topic.

Topic = a grammar/vocabulary theme (e.g. "Perfekt", "Konjunktiv II")
TopicItem = a lesson, test, or exercise linked to a topic
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class TopicCategory(str, enum.Enum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    PRONUNCIATION = "pronunciation"
    LISTENING = "listening"
    READING = "reading"
    WRITING = "writing"
    SPEAKING = "speaking"
    CULTURE = "culture"
    IDIOMS = "idioms"
    OTHER = "other"


class ItemType(str, enum.Enum):
    LESSON = "lesson"
    EXERCISE = "exercise"
    TEST = "test"
    CONVERSATION = "conversation"
    NEWS = "news"
    PRONUNCIATION = "pronunciation"


GERMAN = ("german", "niemiecki", "de", "deutsch")


class Topic(Base):
    __tablename__ = "topics"

    KB_GROUP_PREFIX = "Bank wiedzy · "  # umbrella rows owned by services/knowledge.py

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String, nullable=False)          # e.g. "German"
    category = Column(String, default=TopicCategory.GRAMMAR)
    name = Column(String, nullable=False)              # e.g. "Perfekt"
    description = Column(Text, nullable=True)           # AI-generated summary
    cefr_level = Column(String, nullable=True)          # A1-C2

    # Hierarchy: null = main topic; set = subtopic under another topic.
    parent_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    # Bank wiedzy entry for a curriculum skill (services/knowledge.py); null for model-made topics
    skill_id = Column(String, nullable=True, index=True)

    # ── FSRS Spaced Repetition ──
    difficulty = Column(Float, default=5.0)             # FSRS difficulty (0-10, lower=easier)
    stability = Column(Float, default=0.0)              # FSRS stability (days)
    retrievability = Column(Float, default=0.0)         # FSRS retrievability (0-1)
    interval = Column(Integer, default=0)               # days until next review
    repetitions = Column(Integer, default=0)            # total review count
    lapses = Column(Integer, default=0)                 # times forgotten
    fsrs_state = Column(String, default="Learning")     # Learning/Review/Relearning
    fsrs_step = Column(Integer, nullable=True)          # learning step; null in Review or if saved before 2026-10-11
    next_review_date = Column(DateTime, nullable=True)  # when to review next
    last_review_date = Column(DateTime, nullable=True)  # last time reviewed
    memory_strength = Column(Float, default=0.0)        # 0.0-1.0 visual indicator

    # ── Stats ──
    total_items = Column(Integer, default=0)            # total lessons+tests+exercises
    total_reviews = Column(Integer, default=0)          # total times reviewed
    avg_score = Column(Float, default=0.0)              # average score across reviews

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure FSRS defaults for in-memory objects (Column default only applies on commit)
        if self.difficulty is None:
            self.difficulty = 5.0
        if self.stability is None:
            self.stability = 0.0
        if self.retrievability is None:
            self.retrievability = 0.0
        if self.interval is None:
            self.interval = 0
        if self.repetitions is None:
            self.repetitions = 0
        if self.lapses is None:
            self.lapses = 0
        if self.fsrs_state is None:
            self.fsrs_state = "Learning"
        if self.memory_strength is None:
            self.memory_strength = 0.0
        if self.total_items is None:
            self.total_items = 0
        if self.total_reviews is None:
            self.total_reviews = 0
        if self.avg_score is None:
            self.avg_score = 0.0

    # ── Relationships ──
    user = relationship("User", back_populates="topics")
    items = relationship("TopicItem", back_populates="topic", cascade="all, delete-orphan")
    # Self-referential hierarchy (main topic → subtopics)
    parent = relationship("Topic", remote_side=[id], back_populates="subtopics")
    subtopics = relationship("Topic", back_populates="parent")

    def calculate_memory_strength(self) -> float:
        """
        Calculate memory strength 0.0-1.0 based on FSRS state.
        Uses retrievability as the primary signal, adjusted by stability and difficulty.
        """
        from backend.services.fsrs_service import calculate_memory_strength_fsrs, current_retrievability
        # Recall probability today, not the ~1.0 stored at the last review (01.11.2026)
        retrievability = current_retrievability(self.stability, self.last_review_date)
        strength = calculate_memory_strength_fsrs(
            difficulty=self.difficulty,
            stability=self.stability,
            retrievability=retrievability,
            reps=self.repetitions,
            lapses=self.lapses,
        )
        state = self.fsrs_state or "Learning"
        if state == "Relearning":
            strength = min(strength, 0.4)  # just forgotten: a weak topic, never a strong one
        elif state != "Review":
            strength = min(strength, 0.6)  # still learning: not yet strong
        return strength

    def current_strength(self) -> float:
        """Memory strength today. A reviewed topic is recalculated from the forgetting
        curve (the stored memory_strength is the one at the last review and never falls);
        a topic without reviews keeps its stored value."""
        return topic_strength(self)

    def is_knowledge_row(self) -> bool:
        """An entry or umbrella row of the Bank wiedzy (services/knowledge.py)."""
        return bool(self.skill_id) or (self.name or "").startswith(self.KB_GROUP_PREFIX)

    def has_own_reviews(self) -> bool:
        """Whether the topic is reviewed as one card here. Not for Bank wiedzy rows,
        and not for any German topic (A8): German flashcards and exercises are
        scheduled by the hub's single deck (decision D1), so a second schedule of
        whole topics here would only compete with it."""
        if self.is_knowledge_row():
            return False
        return (self.language or "").lower() not in GERMAN

    def is_due(self) -> bool:
        """Check if topic is due for review (never for topics without own reviews)."""
        if not self.has_own_reviews():
            return False
        if self.next_review_date is None:
            return True  # never reviewed = due
        review_date = self.next_review_date
        if review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= review_date

    def days_until_review(self) -> int:
        """Days until next review (negative = overdue)."""
        if self.next_review_date is None:
            return 0
        review_date = self.next_review_date
        if review_date.tzinfo is None:
            review_date = review_date.replace(tzinfo=timezone.utc)
        delta = (review_date - datetime.now(timezone.utc)).days
        return delta

    def apply_fsrs(self, rating: int) -> None:
        """
        Apply FSRS algorithm after a review.

        Args:
            rating: 1-4 rating
              1 = Again (forgot completely)
              2 = Hard (recalled with significant difficulty)
              3 = Good (recalled with some effort)
              4 = Easy (instant, effortless recall)
        """
        from backend.services.fsrs_service import apply_fsrs

        result = apply_fsrs(
            rating=rating,
            difficulty=self.difficulty,
            stability=self.stability,
            retrievability=self.retrievability if self.retrievability > 0 else None,
            elapsed_days=0,
            reps=self.repetitions,
            lapses=self.lapses or 0,
            current_state=self.fsrs_state or "Learning",
            last_review_date=self.last_review_date,
            step=self.fsrs_step,
            next_review_date=self.next_review_date,
        )

        self.difficulty = result.difficulty
        self.stability = result.stability
        self.retrievability = result.retrievability
        self.interval = result.interval
        self.repetitions = result.repetitions
        self.lapses = result.lapses
        self.fsrs_state = result.state
        self.fsrs_step = result.step
        self.next_review_date = result.next_review_date
        self.last_review_date = datetime.now(timezone.utc)
        self.memory_strength = self.calculate_memory_strength()
        self.total_reviews += 1
        self.updated_at = datetime.now(timezone.utc)

    # Backward compatibility alias
    apply_sm2 = apply_fsrs


class TopicItem(Base):
    __tablename__ = "topic_items"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    item_type = Column(String, nullable=False)          # lesson, exercise, test, etc.
    item_id = Column(Integer, nullable=False)           # FK to lesson/test/etc. table
    title = Column(String, nullable=True)               # snapshot title
    day_number = Column(Integer, nullable=True)         # lesson day if applicable
    score = Column(Float, nullable=True)                # test/exercise score if applicable
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    topic = relationship("Topic", back_populates="items")


def topic_strength(topic) -> float:
    """Memory strength of a topic today (see Topic.current_strength)."""
    if getattr(topic, "last_review_date", None) is None:
        return getattr(topic, "memory_strength", None) or 0.0
    return topic.calculate_memory_strength()
