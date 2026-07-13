"""Pydantic schemas for placement router."""
from typing import Optional

from pydantic import BaseModel


class StartPlacementRequest(BaseModel):
    user_id: Optional[int] = None
    language: Optional[str] = None
    native_language: Optional[str] = None


class SubmitPlacementRequest(BaseModel):
    user_id: Optional[int] = None
    questions: Optional[list] = None
    answers: dict
    language: Optional[str] = None
    native_language: Optional[str] = None


class CreateUserRequest(BaseModel):
    name: str
    native_language: Optional[str] = None
    target_language: Optional[str] = None


class UpdateLanguageRequest(BaseModel):
    target_language: str
