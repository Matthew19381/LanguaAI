"""Mock Goethe-Zertifikat B1 "Sprechen" exam (A5 of the "finished" criterion).

One row per attempt: the generated tasks, what the student said in each of
the three parts, and the score. The goal "Mówienie B1" counts as reached
after two consecutive attempts at or above the pass mark.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from backend.database import Base


class MockExam(Base):
    __tablename__ = "mock_exams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scored_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="teil1")  # teil1, teil2, teil3, scoring, scored
    tasks = Column(Text, nullable=False)                  # JSON: generated tasks of all 3 parts
    teil1_history = Column(Text, nullable=False, default="[]")  # JSON: planning dialogue
    teil2_topic = Column(Integer, nullable=True)          # index of the chosen topic (0 or 1)
    teil2_transcript = Column(Text, nullable=True)        # the presentation as spoken/typed
    teil3 = Column(Text, nullable=True)                   # JSON: partner's question, answer, feedback
    scores = Column(Text, nullable=True)                  # JSON: per part and criterion
    points = Column(Float, nullable=True)                 # points on the assessed criteria
    max_points = Column(Integer, nullable=True)           # 84: Aussprache (16) is not assessed
    percent = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
