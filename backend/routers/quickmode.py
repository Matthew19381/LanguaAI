import logging
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_user_or_404
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/quickmode/{user_id}")
async def get_quickmode_plan(user_id: int, db: Session = Depends(get_db)):
    """Return a prioritized 15-minute daily activity list."""
    user = get_user_or_404(db, user_id)

    activities = []

    # Check today's lesson (per language)
    from sqlalchemy import func
    today_date = date.today()
    today_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
        func.date(Lesson.created_at) == today_date
    ).first()

    if today_lesson and not today_lesson.is_completed:
        activities.append({
            "id": "lesson",
            "title": "Dzisiejsza lekcja",
            "description": today_lesson.title,
            "estimated_minutes": 8,
            "priority": 1,
            "route": "/lesson",
            "icon": "BookOpen",
            "completed": False,
        })
    elif today_lesson and today_lesson.is_completed:
        # Check if test done today
        today_test = db.query(TestResult).filter(
            TestResult.user_id == user_id,
            func.date(TestResult.created_at) == today_date
        ).first()
        if not today_test:
            activities.append({
                "id": "test",
                "title": "Dzienny test",
                "description": "Sprawdź wiedzę z dzisiejszej lekcji",
                "estimated_minutes": 5,
                "priority": 1,
                "route": "/test",
                "icon": "FlaskConical",
                "completed": False,
            })
        else:
            activities.append({
                "id": "test",
                "title": "Dzienny test",
                "description": "Już ukończono dziś",
                "estimated_minutes": 5,
                "priority": 3,
                "route": "/test",
                "icon": "FlaskConical",
                "completed": True,
            })
    else:
        activities.append({
            "id": "lesson",
            "title": "Dzisiejsza lekcja",
            "description": "Zacznij dzienną lekcję",
            "estimated_minutes": 8,
            "priority": 1,
            "route": "/lesson",
            "icon": "BookOpen",
            "completed": False,
        })

    # Pronunciation practice
    activities.append({
        "id": "pronunciation",
        "title": "Ćwiczenie wymowy",
        "description": "Ćwicz wymowę i sprawdź poprawność",
        "estimated_minutes": 3,
        "priority": 3,
        "route": "/pronunciation",
        "icon": "Mic",
        "completed": False,
    })

    # News reading
    activities.append({
        "id": "news",
        "title": "Newsy w języku docelowym",
        "description": f"Czytaj uproszczone wiadomości po {user.target_language}",
        "estimated_minutes": 4,
        "priority": 4,
        "route": "/news",
        "icon": "Newspaper",
        "completed": False,
    })

    # Sort by priority
    activities.sort(key=lambda x: x["priority"])

    total_minutes = sum(a["estimated_minutes"] for a in activities if not a["completed"])

    return {
        "user_id": user_id,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
        "total_estimated_minutes": total_minutes,
        "activities": activities,
        "timer_minutes": 15,
    }
