"""Shared utility functions for backend routers."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models.user import User


def get_user_or_404(db: Session, user_id: int) -> User:
    """Fetch a user by ID or raise 404.

    Replaces the repetitive pattern:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
