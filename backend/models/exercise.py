"""Exercise bank — every generated exercise is persisted as a reusable item.

Rationale (see docs/NEURO_FEATURES.md):
- Cost: exercises are already generated with each lesson; discarding them into a
  JSON blob means paying the AI again for equivalent practice.
- Pedagogy: persisting each exercise as an addressable item turns it into a
  spaced-retrieval unit (testing effect + spacing), and lets practice sets
  interleave items across topics (Rohrer & Taylor 2007).
- Transfer: items are keyed by ``skill_tag`` (the underlying grammar/lexical
  skill), not by surface text, so a skill can be re-practised through fresh
  variants instead of the identical sentence (Schmidt & Bjork 1992 — variability
  of practice). ``variant_of`` links a generated variant to its origin item.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String, nullable=False, index=True)
    cefr_level = Column(String, nullable=True)

    # ── Content ──
    exercise_type = Column(String, nullable=True)   # fill-in-the-blank / translation / ...
    instruction = Column(Text, nullable=True)
    prompt = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    feedback = Column(Text, nullable=True)

    # ── Classification ──
    skill_tag = Column(String, nullable=True, index=True)  # e.g. "Perfekt with haben"
    topic = Column(String, nullable=True, index=True)      # lesson topic
    source_lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    variant_of = Column(Integer, ForeignKey("exercises.id"), nullable=True)

    # ── Exposure counters (drive variant generation) ──
    times_seen = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)

    # ── FSRS scheduling (same fields/scheduler as flashcards) ──
    difficulty = Column(Float, default=5.0)
    stability = Column(Float, default=0.0)
    retrievability = Column(Float, default=0.0)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    fsrs_state = Column(String, default="Learning")
    next_review_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_review_date = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
