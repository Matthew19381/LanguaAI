"""Export / import a user's full learning profile as a JSON file.

Purpose: a single-user app should never force the learner through onboarding
again after a database reset. The profile (account + lessons + flashcards with
FSRS state) serializes to `backups/user_profile.json` and can be re-imported
into a fresh database with the SAME user id, so localStorage keeps working.

CLI:
    python -m backend.services.profile_backup --export <user_id>
    python -m backend.services.profile_backup --import backups/user_profile.json
"""
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PATH = PROJECT_ROOT / "backups" / "user_profile.json"

PROFILE_VERSION = 1


def _dt(value):
    return value.isoformat() if isinstance(value, datetime) else None


def export_profile(db, user_id: int) -> dict:
    """Serialize user + lessons + flashcards (incl. FSRS state) to a dict."""
    from backend.models.flashcard import Flashcard
    from backend.models.lesson import Lesson
    from backend.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.user_id == user_id)
        .order_by(Lesson.day_number)
        .all()
    )
    flashcards = (
        db.query(Flashcard)
        .filter(Flashcard.user_id == user_id)
        .order_by(Flashcard.id)
        .all()
    )

    return {
        "version": PROFILE_VERSION,
        "exported_at": datetime.now().isoformat(),
        "user": {
            "id": user.id,
            "name": user.name,
            "native_language": user.native_language,
            "target_language": user.target_language,
            "cefr_level": user.cefr_level,
            "streak_days": user.streak_days,
            "streak_freezes": user.streak_freezes,
            "total_xp": user.total_xp,
            "created_at": _dt(user.created_at),
            "language_profiles": user.language_profiles,
            "sleep_data": user.sleep_data,
        },
        "lessons": [
            {
                "day_number": l.day_number,
                "title": l.title,
                "topic": l.topic,
                "content": l.content,
                "cefr_level": l.cefr_level,
                "language": l.language,
                "is_completed": l.is_completed,
                "created_at": _dt(l.created_at),
                "completed_at": _dt(l.completed_at),
            }
            for l in lessons
        ],
        "flashcards": [
            {
                "word": f.word,
                "translation": f.translation,
                "example_sentence": f.example_sentence,
                "language": f.language,
                "cefr_level": f.cefr_level,
                "gender": f.gender,
                "isImportant": f.isImportant,
                "difficulty": f.difficulty,
                "stability": f.stability,
                "retrievability": f.retrievability,
                "interval_days": f.interval_days,
                "repetitions": f.repetitions,
                "lapses": f.lapses,
                "fsrs_state": f.fsrs_state,
                "next_review_date": _dt(f.next_review_date),
                "last_review_date": _dt(f.last_review_date),
                "correct_recall_sessions": f.correct_recall_sessions,
                "last_recall_date": _dt(f.last_recall_date),
                "is_mastered": f.is_mastered,
                "created_at": _dt(f.created_at),
                "is_active": f.is_active,
            }
            for f in flashcards
        ],
    }


def save_profile(db, user_id: int, path: Path = DEFAULT_PATH) -> Path:
    data = export_profile(db, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Profile exported to %s", path)
    return path


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def import_profile(db, path: Path) -> int:
    """Restore a profile into the DB. Returns the user id (kept from the file).

    Idempotent: if the user id already exists, the import is skipped.
    """
    from backend.models.flashcard import Flashcard
    from backend.models.lesson import Lesson
    from backend.models.user import User

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != PROFILE_VERSION:
        raise ValueError(f"Unsupported profile version: {data.get('version')}")

    u = data["user"]
    existing = db.query(User).filter(User.id == u["id"]).first()
    if existing:
        logger.info("User %s already exists — import skipped", u["id"])
        return existing.id

    user = User(
        id=u["id"],
        name=u["name"],
        native_language=u["native_language"],
        target_language=u["target_language"],
        cefr_level=u["cefr_level"],
        streak_days=u.get("streak_days", 0),
        streak_freezes=u.get("streak_freezes", 2),
        total_xp=u.get("total_xp", 0),
        created_at=_parse_dt(u.get("created_at")) or datetime.now(),
        language_profiles=u.get("language_profiles", "{}"),
        sleep_data=u.get("sleep_data", "{}"),
    )
    db.add(user)

    # Restore day_number -> new lesson id mapping so flashcards keep their link
    day_to_lesson_id: dict = {}
    for l in data.get("lessons", []):
        lesson = Lesson(
            user_id=user.id,
            day_number=l["day_number"],
            title=l["title"],
            topic=l["topic"],
            content=l["content"],
            cefr_level=l["cefr_level"],
            language=l["language"],
            is_completed=l.get("is_completed", False),
            created_at=_parse_dt(l.get("created_at")) or datetime.now(),
            completed_at=_parse_dt(l.get("completed_at")),
        )
        db.add(lesson)
        db.flush()
        day_to_lesson_id[l["day_number"]] = lesson.id

    for f in data.get("flashcards", []):
        db.add(
            Flashcard(
                user_id=user.id,
                word=f["word"],
                translation=f["translation"],
                example_sentence=f.get("example_sentence"),
                language=f["language"],
                cefr_level=f["cefr_level"],
                gender=f.get("gender"),
                isImportant=f.get("isImportant", False),
                difficulty=f.get("difficulty", 5.0),
                stability=f.get("stability", 0.0),
                retrievability=f.get("retrievability", 0.0),
                interval_days=f.get("interval_days", 1),
                repetitions=f.get("repetitions", 0),
                lapses=f.get("lapses", 0),
                fsrs_state=f.get("fsrs_state", "Learning"),
                next_review_date=_parse_dt(f.get("next_review_date")) or datetime.now(),
                last_review_date=_parse_dt(f.get("last_review_date")),
                correct_recall_sessions=f.get("correct_recall_sessions", 0),
                last_recall_date=_parse_dt(f.get("last_recall_date")),
                is_mastered=f.get("is_mastered", False),
                created_at=_parse_dt(f.get("created_at")) or datetime.now(),
                is_active=f.get("is_active", True),
            )
        )

    db.commit()
    logger.info(
        "Profile imported: user %s, %d lessons, %d flashcards",
        user.id, len(data.get("lessons", [])), len(data.get("flashcards", [])),
    )
    return user.id


def main():
    parser = argparse.ArgumentParser(description="Export/import user learning profile")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", type=int, metavar="USER_ID", help="Export profile for user id")
    group.add_argument("--import", dest="import_path", metavar="PATH", help="Import profile from JSON file")
    parser.add_argument("--out", type=str, default=str(DEFAULT_PATH), help="Output path for export")
    args = parser.parse_args()

    # Import all models so every relationship on User resolves (standalone CLI
    # has no FastAPI lifespan to do it for us).
    import backend.models  # noqa: F401
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        if args.export is not None:
            path = save_profile(db, args.export, Path(args.out))
            print(f"Exported to {path}")
        else:
            uid = import_profile(db, Path(args.import_path))
            print(f"Imported user id {uid}")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
