"""One attempt at a curriculum skill (21.10.2026).

The exercise bank keeps only running totals (times_seen, times_correct), so it
cannot tell three correct answers in one sitting from three on different days.
Mastery needs the second (successive relearning: Rawson, Dunlosky & Sciartelli
2013), and conversation errors need a place to land, so every answer to an
exercise with a skill id and every skill-tagged conversation error is logged here.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from backend.database import Base


class SkillAttempt(Base):
    __tablename__ = "skill_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String, nullable=False)
    skill_id = Column(String, nullable=False, index=True)   # catalog id, e.g. "G-DAT"
    source = Column(String, nullable=False)                 # exercise / conversation
    correct = Column(Boolean, nullable=False)
    # First answer of this item on that day; repeats in one sitting do not count for mastery
    first_try = Column(Boolean, nullable=False, default=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=True)
    detail = Column(Text, nullable=True)                    # JSON: {"wrong": ..., "correct": ...}
    occurred_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
