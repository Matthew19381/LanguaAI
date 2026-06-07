"""Flashcard-related helper functions extracted from routers."""
from sqlalchemy.orm import Session
from backend.models.flashcard import Flashcard


def create_flashcards_from_vocab(
    db: Session,
    vocabulary: list,
    user_id: int,
    target_language: str,
    cefr_level: str,
    lesson_id: int,
    day_number: int,
    topic: str,
) -> None:
    """Batch-create flashcards from vocabulary list, skipping duplicates."""
    vocab_words = [v.get("word", "") for v in vocabulary if v.get("word") and v.get("translation")]
    if vocab_words:
        existing = db.query(Flashcard.word).filter(
            Flashcard.user_id == user_id,
            Flashcard.language == target_language,
            Flashcard.word.in_(vocab_words),
        ).all()
        existing_words = {row[0] for row in existing}
    else:
        existing_words = set()

    for item in vocabulary:
        word = item.get("word", "")
        translation = item.get("translation", "")
        if word and translation and word not in existing_words:
            db.add(Flashcard(
                user_id=user_id,
                word=word,
                translation=translation,
                example_sentence=item.get("example", ""),
                language=target_language,
                cefr_level=cefr_level,
                lesson_id=lesson_id,
                lesson_day=day_number,
                lesson_topic=topic,
            ))
