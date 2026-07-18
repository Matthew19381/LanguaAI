"""Lesson generator service — AI prompt logic for all lesson content.

Split into sub-modules by domain:
- placement: placement test generation and analysis
- study_plan: 30-day study plan generation
- daily_lesson: daily lesson content generation
- tests: test generation and error analysis
- conversation: conversation scenarios and analysis
- tips: daily tips and Q&A
"""

from backend.services.lesson_generator.conversation import (
    analyze_conversation,
    analyze_pasted_conversation,
    generate_conversation_scenario,
)
from backend.services.lesson_generator.daily_lesson import (
    generate_daily_lesson,
    generate_exercise_variants,
    generate_iplus1_content,
    lexical_coverage,
)
from backend.services.lesson_generator.placement import (
    analyze_placement_results,
    generate_placement_test,
)
from backend.services.lesson_generator.study_plan import (
    generate_study_plan,
)
from backend.services.lesson_generator.tests import (
    analyze_test_errors,
    generate_daily_test,
    generate_errors_test,
    generate_weekly_test,
)
from backend.services.lesson_generator.tips import (
    answer_language_question,
    generate_daily_tips,
)

__all__ = [
    "generate_placement_test",
    "analyze_placement_results",
    "generate_study_plan",
    "generate_daily_lesson",
    "generate_exercise_variants",
    "generate_iplus1_content",
    "lexical_coverage",
    "generate_daily_test",
    "analyze_test_errors",
    "generate_weekly_test",
    "generate_errors_test",
    "generate_conversation_scenario",
    "analyze_conversation",
    "analyze_pasted_conversation",
    "answer_language_question",
    "generate_daily_tips",
]
