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


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String, nullable=False)          # e.g. "German"
    category = Column(String, default=TopicCategory.GRAMMAR)
    name = Column(String, nullable=False)              # e.g. "Perfekt"
    description = Column(Text, nullable=True)           # AI-generated summary
    cefr_level = Column(String, nullable=True)          # A1-C2

    # ── FSRS Spaced Repetition ──
    difficulty = Column(Float, default=5.0)             # FSRS difficulty (0-10, lower=easier)
    stability = Column(Float, default=0.0)              # FSRS stability (days)
    retrievability = Column(Float, default=0.0)         # FSRS retrievability (0-1)
    interval = Column(Integer, default=0)               # days until next review
    repetitions = Column(Integer, default=0)            # total review count
    lapses = Column(Integer, default=0)                 # times forgotten
    fsrs_state = Column(String, default="Learning")     # Learning/Review/Relearning
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

    def calculate_memory_strength(self) -> float:
        """
        Calculate memory strength 0.0-1.0 based on FSRS state.
        Uses retrievability as the primary signal, adjusted by stability and difficulty.
        """
        from backend.services.fsrs_service import calculate_memory_strength_fsrs
        return calculate_memory_strength_fsrs(
            difficulty=self.difficulty,
            stability=self.stability,
            retrievability=self.retrievability,
            reps=self.repetitions,
            lapses=self.lapses,
        )

    def is_due(self) -> bool:
        """Check if topic is due for review."""
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
        )

        self.difficulty = result.difficulty
        self.stability = result.stability
        self.retrievability = result.retrievability
        self.interval = result.interval
        self.repetitions = result.repetitions
        self.fsrs_state = result.state
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
