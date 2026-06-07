"""Backward-compatible re-export of lesson_generator sub-modules.

The implementation has been split into:
- backend.services.lesson_generator.placement
- backend.services.lesson_generator.study_plan
- backend.services.lesson_generator.daily_lesson
- backend.services.lesson_generator.tests
- backend.services.lesson_generator.conversation
- backend.services.lesson_generator.tips

This file re-exports all functions for backward compatibility.
"""

from backend.services.lesson_generator import *  # noqa: F401,F403
