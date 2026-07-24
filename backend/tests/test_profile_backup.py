"""Profile backup: export → JSON file → import into a fresh DB keeps everything."""
import json

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.user import User
from backend.services.profile_backup import export_profile, import_profile, save_profile


def _seed_user_with_progress(db, user_id=42):
    user = User(
        id=user_id, name="Backup Test", native_language="Polish",
        target_language="German", cefr_level="A2", total_xp=123, streak_days=4,
    )
    db.add(user)
    db.add(Lesson(
        user_id=user_id, day_number=1, title="Tag 1", topic="Begrüßungen",
        content=json.dumps({"vocabulary": [{"word": "Hallo"}]}),
        cefr_level="A2", language="German", is_completed=True,
    ))
    db.add(Flashcard(
        user_id=user_id, word="laufen", translation="biec", language="German",
        cefr_level="A2", difficulty=4.2, stability=6.5, repetitions=5,
        fsrs_state="Review", is_mastered=True, correct_recall_sessions=3,
    ))
    db.commit()
    return user_id


def test_export_contains_user_lessons_flashcards(db):
    uid = _seed_user_with_progress(db)
    data = export_profile(db, uid)

    assert data["user"]["id"] == uid
    assert data["user"]["total_xp"] == 123
    assert data["user"]["cefr_level"] == "A2"
    assert len(data["lessons"]) == 1
    assert data["lessons"][0]["topic"] == "Begrüßungen"
    assert len(data["flashcards"]) == 1
    fc = data["flashcards"][0]
    assert fc["word"] == "laufen"
    assert fc["fsrs_state"] == "Review"
    assert fc["is_mastered"] is True
    assert fc["stability"] == 6.5


def test_save_profile_writes_json_file(db, tmp_path):
    uid = _seed_user_with_progress(db)
    path = save_profile(db, uid, tmp_path / "profile.json")

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["user"]["name"] == "Backup Test"
    assert data["version"] == 1


def test_import_restores_into_fresh_db(db, tmp_path):
    uid = _seed_user_with_progress(db)
    path = save_profile(db, uid, tmp_path / "profile.json")

    # Simulate DB reset: wipe the rows
    db.query(Flashcard).filter(Flashcard.user_id == uid).delete()
    db.query(Lesson).filter(Lesson.user_id == uid).delete()
    db.query(User).filter(User.id == uid).delete()
    db.commit()
    assert db.query(User).filter(User.id == uid).first() is None

    restored_id = import_profile(db, path)
    assert restored_id == uid  # SAME id — localStorage keeps working

    user = db.query(User).filter(User.id == uid).first()
    assert user.total_xp == 123
    lessons = db.query(Lesson).filter(Lesson.user_id == uid).all()
    assert len(lessons) == 1 and lessons[0].is_completed is True
    cards = db.query(Flashcard).filter(Flashcard.user_id == uid).all()
    assert len(cards) == 1
    assert cards[0].fsrs_state == "Review"
    assert cards[0].is_mastered is True
    assert cards[0].repetitions == 5


def test_import_is_idempotent(db, tmp_path):
    uid = _seed_user_with_progress(db)
    path = save_profile(db, uid, tmp_path / "profile.json")

    # User still exists → import must not duplicate or fail
    result = import_profile(db, path)
    assert result == uid
    assert db.query(Flashcard).filter(Flashcard.user_id == uid).count() == 1
