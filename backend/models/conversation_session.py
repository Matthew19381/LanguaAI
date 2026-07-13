"""
Conversation Session model — persistent storage for AI conversation sessions.

Replaces the in-memory dict in routers/conversation.py so sessions survive
server restarts and work correctly with multiple workers.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String, primary_key=True)  # UUID string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String, nullable=False)
    native_language = Column(String, nullable=False)
    cefr_level = Column(String, nullable=False)
    scenario = Column(Text, nullable=False)       # JSON blob of the scenario dict
    system_prompt = Column(Text, nullable=False)
    history = Column(Text, nullable=False)         # JSON blob of message list
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
