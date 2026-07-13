from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint('user_id', 'language', 'day_number', name='uq_user_lang_day'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    content = Column(Text, nullable=False)  # JSON text - full lesson content
    cefr_level = Column(String, nullable=False)
    language = Column(String, nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    # Neuro: session type for sleep-aware scheduling
    session_type = Column(String, default="day")  # "evening" | "morning" | "day"
    sleep_quality = Column(Integer, nullable=True)  # 1-5, user-reported

    user = relationship("User", back_populates="lessons")
