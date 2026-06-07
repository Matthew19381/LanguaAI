import json
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from backend.schemas.placement import (
    StartPlacementRequest,
    SubmitPlacementRequest,
    CreateUserRequest,
    UpdateLanguageRequest,
)
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User
from backend.utils import get_user_or_404
from backend.models.test_result import TestResult
from backend.models.study_plan import StudyPlan
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.services.lesson_generator import (
    generate_placement_test,
    analyze_placement_results,
    generate_study_plan
)
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Map friendly (Polish) language names to canonical English names
LANGUAGE_MAP = {
    "Niemiecki": "German",
    "Angielski": "English",
    "Hiszpański": "Spanish",
    "Rosyjski": "Russian",
    "Chiński": "Chinese",
    "Francuski": "French",
    "Włoski": "Italian",
    "Polski": "Polish",
    "German": "German",
    "English": "English",
    "Spanish": "Spanish",
    "Russian": "Russian",
    "Chinese": "Chinese",
    "French": "French",
    "Italian": "Italian",
}

@router.post("/api/placement/start")
async def start_placement(
    request: StartPlacementRequest,
    db: Session = Depends(get_db)
):
    language = request.language or settings.TARGET_LANGUAGE
    native_language = request.native_language or settings.NATIVE_LANGUAGE

    # Map Polish/other language names to canonical English
    language = LANGUAGE_MAP.get(language, language)
    native_language = LANGUAGE_MAP.get(native_language, native_language) if native_language else native_language

    try:
        test_data = await generate_placement_test(language, native_language)
        return {
            "success": True,
            "language": language,
            "native_language": native_language,
            "questions": test_data.get("questions", []),
            "total_questions": len(test_data.get("questions", []))
        }
    except ValueError as e:
        logger.error(f"Validation error in placement test: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.RequestError as e:
        logger.error(f"AI service error in placement test: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.exception("Unexpected error in placement test")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/placement/submit")
async def submit_placement(
    request: SubmitPlacementRequest,
    db: Session = Depends(get_db)
):
    language = request.language or settings.TARGET_LANGUAGE
    native_language = request.native_language or settings.NATIVE_LANGUAGE

    # Map Polish/other language names to canonical English
    language = LANGUAGE_MAP.get(language, language)
    native_language = LANGUAGE_MAP.get(native_language, native_language) if native_language else native_language

    try:
        # Analyze results
        analysis = await analyze_placement_results(
            questions=request.questions or [],
            answers=request.answers,
            language=language,
            native_language=native_language
        )

        cefr_level = analysis.get("cefr_level", "A1")
        score = analysis.get("score", 0)

        user = None
        study_plan_data = None

        if request.user_id:
            user = db.query(User).filter(User.id == request.user_id).first()
            if user:
                import json as _json
                # Update user's CEFR level and save to language_profiles
                user.cefr_level = cefr_level
                try:
                    profiles = _json.loads(user.language_profiles or "{}")
                except (json.JSONDecodeError, TypeError):
                    profiles = {}
                profiles[language] = cefr_level
                user.language_profiles = _json.dumps(profiles)
                db.commit()

                # Save test result
                test_result = TestResult(
                    user_id=user.id,
                    test_type="placement",
                    score=score,
                    answers=json.dumps(request.answers),
                    errors=json.dumps(analysis.get("weak_areas", [])),
                    cefr_level=cefr_level,
                    language=language
                )
                db.add(test_result)

                # Generate study plan
                user_data = {
                    "name": user.name,
                    "cefr_level": cefr_level,
                    "native_language": native_language,
                    "target_language": language
                }
                study_plan_data = await generate_study_plan(user_data, language, native_language)

                # Deactivate old study plans
                db.query(StudyPlan).filter(
                    StudyPlan.user_id == user.id,
                    StudyPlan.is_active == True
                ).update({"is_active": False})

                # Save new study plan
                new_plan = StudyPlan(
                    user_id=user.id,
                    language=language,
                    cefr_level=cefr_level,
                    plan_data=json.dumps(study_plan_data),
                    is_active=True
                )
                db.add(new_plan)
                db.commit()

        return {
            "success": True,
            "cefr_level": cefr_level,
            "score": score,
            "strong_areas": analysis.get("strong_areas", []),
            "weak_areas": analysis.get("weak_areas", []),
            "recommendations": analysis.get("recommendations", ""),
            "study_plan": study_plan_data
        }
    except ValueError as e:
        logger.error(f"Validation error in placement submit: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.RequestError as e:
        logger.error(f"AI service error in placement submit: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.exception("Unexpected error in placement submit")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/placement/create-user")
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    try:
        native_language = request.native_language or settings.NATIVE_LANGUAGE
        target_language = request.target_language or settings.TARGET_LANGUAGE

        # MapPolish/other language names to canonical English for internal storage
        canonical_target = LANGUAGE_MAP.get(target_language, target_language)

        user = User(
            name=request.name,
            native_language=native_language,
            target_language=canonical_target,
            cefr_level="A1",
            streak_days=0,
            total_xp=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "user_id": user.id,
            "name": user.name,
            "native_language": user.native_language,
            "target_language": user.target_language,
            "cefr_level": user.cefr_level
        }
    except ValueError as e:
        logger.error(f"Validation error creating user: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error creating user")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/placement/user/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    return {
        "user_id": user.id,
        "name": user.name,
        "native_language": user.native_language,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
        "streak_days": user.streak_days,
        "total_xp": user.total_xp,
        "created_at": user.created_at.isoformat()
    }


SUPPORTED_LANGUAGES = ["German", "English", "Spanish", "Russian", "Chinese"]


@router.patch("/api/placement/{user_id}/language")
async def update_user_language(
    user_id: int,
    request: UpdateLanguageRequest,
    db: Session = Depends(get_db)
):
    import json as _json
    user = get_user_or_404(db, user_id)

    new_lang = request.target_language
    if new_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language. Supported: {SUPPORTED_LANGUAGES}")

    # Load existing language profiles
    try:
        profiles = _json.loads(user.language_profiles or "{}")
    except (ValueError, TypeError):
        profiles = {}

    # Track before any modifications whether this is a genuinely new language
    was_new = new_lang not in profiles

    # Save current language's CEFR level before switching
    if user.target_language:
        profiles[user.target_language] = user.cefr_level

    # Restore CEFR for the new language (default A1 if never studied)
    new_cefr = profiles.get(new_lang, "A1")

    # Save profiles back
    profiles[new_lang] = new_cefr
    user.language_profiles = _json.dumps(profiles)
    user.target_language = new_lang
    user.cefr_level = new_cefr

    # Deactivate study plans for other languages, keep new language's plan active
    all_plans = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).all()
    for plan in all_plans:
        plan.is_active = (plan.language == new_lang)

    db.commit()

    return {
        "success": True,
        "user_id": user_id,
        "target_language": new_lang,
        "cefr_level": new_cefr,
        "language_profiles": profiles,
        "needs_placement": was_new
    }


@router.get("/api/placement/{user_id}/languages")
async def get_language_profiles(user_id: int, db: Session = Depends(get_db)):
    """Return all language progress profiles for the user."""
    import json as _json
    user = get_user_or_404(db, user_id)

    try:
        profiles = _json.loads(user.language_profiles or "{}")
    except (ValueError, TypeError):
        profiles = {}

    # N+1 fix: single GROUP BY query instead of one query per language
    from sqlalchemy import func as sa_func
    lesson_counts = dict(
        db.query(Lesson.language, sa_func.count(Lesson.id))
        .filter(
            Lesson.user_id == user_id,
            Lesson.language.in_(SUPPORTED_LANGUAGES),
            Lesson.is_completed == True,
        )
        .group_by(Lesson.language)
        .all()
    )

    result = []
    for lang in SUPPORTED_LANGUAGES:
        result.append({
            "language": lang,
            "cefr_level": profiles.get(lang),
            "is_active": user.target_language == lang,
            "lessons_completed": lesson_counts.get(lang, 0),
            "started": lang in profiles or user.target_language == lang,
        })

    return {"languages": result, "current": user.target_language}
