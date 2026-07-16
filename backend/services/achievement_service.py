import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.achievement import Achievement

logger = logging.getLogger(__name__)

# Achievement definitions: type -> (title, description, icon)
ACHIEVEMENT_DEFS = {
    # ── Lessons ──
    "first_lesson": ("Pierwszy krok", "Ukończyłeś swoją pierwszą lekcję", "🎯"),
    "lessons_5": ("Dobry początek", "Ukończono 5 lekcji", "📚"),
    "lessons_10": ("Wytrwały uczeń", "Ukończono 10 lekcji", "🏅"),
    "lessons_25": ("Konsekwentny", "Ukończono 25 lekcji", "🎖️"),
    "lessons_50": ("Pół setki", "Ukończono 50 lekcji", "🏆"),
    "lessons_100": ("Setka lekcji", "Ukończono 100 lekcji", "💯"),
    # ── Streaks ──
    "streak_3": ("W rytmie", "3-dniowa seria nauki", "🔥"),
    "streak_7": ("Tygodniowy wojownik", "7-dniowa seria nauki", "⚡"),
    "streak_14": ("Dwutygodniowy mistrz", "14-dniowa seria nauki", "💪"),
    "streak_30": ("Miesięczny mistrz", "30-dniowa seria nauki", "👑"),
    "streak_60": ("Dwumiesięczna legenda", "60-dniowa seria nauki", "🌋"),
    "streak_100": ("Sto dni pod rząd", "100-dniowa seria nauki", "☀️"),
    # ── Tests ──
    "first_test": ("Pierwszy test", "Ukończono pierwszy test", "📝"),
    "first_test_perfect": ("Idealny wynik", "100% na teście", "⭐"),
    "tests_10": ("Mistrz testów", "Ukończono 10 testów", "🎓"),
    "tests_25": ("Ekspert testów", "Ukończono 25 testów", "📊"),
    "tests_50": ("Arcywrog testów", "Ukończono 50 testów", "🏅"),
    # ── XP ──
    "xp_100": ("Zbieracz XP", "Zdobyto 100 XP", "✨"),
    "xp_500": ("Łowca XP", "Zdobyto 500 XP", "💫"),
    "xp_1000": ("Legenda XP", "Zdobyto 1000 XP", "🌟"),
    "xp_2500": ("Mistrz XP", "Zdobyto 2500 XP", "💎"),
    "xp_5000": ("Tytan XP", "Zdobyto 5000 XP", "🔮"),
    # ── Levels ──
    "level_5": ("Poziom 5", "Osiągnięto poziom 5", "🚀"),
    "level_10": ("Poziom 10", "Osiągnięto poziom 10", "🎊"),
    "level_25": ("Poziom 25", "W połowie drogi do mistrzostwa", "🏹"),
    "level_50": ("Poziom 50", "Osiągnięto maksymalny poziom!", "🌍"),
    # ── Flashcards ──
    "flashcards_10": ("Pierwsze fiszki", "Dodano 10 fiszek", "🃏"),
    "flashcards_50": ("Kolekcjoner", "Dodano 50 fiszek", "📇"),
    "flashcards_100": ("Wielka kolekcja", "Dodano 100 fiszek", "🗂️"),
    "flashcards_review_50": ("Powtórki", "Przeglądnięto 50 fiszek", "🔄"),
    "flashcards_review_200": ("Mistrz powtórek", "Przeglądnięto 200 fiszek", "🧠"),
    # ── Conversation ──
    "first_conversation": ("Pierwsza rozmowa", "Ukończono pierwszą rozmowę z AI", "💬"),
    "conversations_5": ("Mówca", "Ukończono 5 rozmów", "🗣️"),
    "conversations_20": ("Ekspert konwersacji", "Ukończono 20 rozmów", "🎙️"),
    # ── Pronunciation ──
    "first_pronunciation": ("Pierwsza wymowa", "Przeanalizowano pierwszą wymowę", "🎤"),
    "pronunciation_5": ("Ćwiczący wymowę", "5 analiz wymowy", "🔊"),
    "pronunciation_20": ("Mistrz wymowy", "20 analiz wymowy", "🎵"),
    "pronunciation_perfect": ("Perfekcyjna wymowa", "100% w analizie wymowy", "🏅"),
    # ── Topics ──
    "first_topic": ("Pierwszy temat", "Utworzono pierwszy temat", "📌"),
    "topics_5": ("Kolekcjonertematów", "Utworzono 5 tematów", "📋"),
    "topics_review_10": ("Powtórki z tematów", "10 przeglądów tematów", "📖"),
    # ── Neuro-FSRS ──
    "sleep_tracker": ("Strażnik snu", "Zanotowano jakość snu 3 razy", "🌙"),
    "neuro_tuned": ("Architekt pamięci", "Dostosowano wagi neuro-FSRS", "🧬"),
    # ── News ──
    "first_news": ("Pierwszy artykuł", "Przeczytano pierwszy artykuł", "📰"),
    "news_10": ("Czytelnik", "Przeczytano 10 artykułów", "🗞️"),
    "news_vocab_20": ("Słownikowy erudyta", "Dodano 20 słów z newsów do fiszek", "📝"),
    # ── Videos ──
    "videos_5": ("Kinoman", "Oglądano 5 filmów", "🎬"),
    "videos_20": ("Bibliofil filmowa", "Oglądano 20 filmów", "📺"),
    # ── Error Review ──
    "first_error_review": ("Pierwsza analiza błędów", "Przeanalizowano pierwsze błędy", "🔍"),
    "errors_reviewed_50": ("Analityczyk", "Przeanalizowano 50 błędów", "🧐"),
    # ── Multi-language ──
    "second_language": ("Dwujęzyczny", "Rozpoczęto naukę drugiego języka", "🌐"),
    "third_language": ("Poliglota", "Rozpoczęto naukę trzeciego języka", "🌍"),
}


def calculate_level_from_xp(xp: int) -> dict:
    """Calculate level (1-50) from XP using a quadratic curve."""
    # Level n requires (n-1)^2 * 20 total XP
    # Level 1: 0, Level 2: 20, Level 5: 320, Level 10: 1620, Level 25: 11520, Level 50: 48020
    level = 1
    for n in range(1, 51):
        required = (n - 1) ** 2 * 20
        if xp >= required:
            level = n
        else:
            break

    current_xp_req = (level - 1) ** 2 * 20
    next_xp_req = level ** 2 * 20 if level < 50 else current_xp_req + 1000

    if level < 50:
        progress = ((xp - current_xp_req) / (next_xp_req - current_xp_req)) * 100
    else:
        progress = 100.0

    return {
        "level": level,
        "level_name": _get_level_name(level),
        "xp": xp,
        "current_level_xp": current_xp_req,
        "next_level_xp": next_xp_req,
        "progress_percent": min(100.0, max(0.0, progress)),
        "max_level": 50,
    }


def _get_level_name(level: int) -> str:
    if level <= 5:
        return "Początkujący"
    elif level <= 10:
        return "Elementarny"
    elif level <= 15:
        return "Przedśredniozaawansowany"
    elif level <= 20:
        return "Średniozaawansowany"
    elif level <= 25:
        return "Wyższy średniozaawansowany"
    elif level <= 30:
        return "Zaawansowany"
    elif level <= 35:
        return "Biegły"
    elif level <= 40:
        return "Ekspert"
    elif level <= 45:
        return "Mistrz"
    else:
        return "Wielki Mistrz"


def check_and_award_achievements(user, db: Session) -> list:
    """Check which achievements the user has earned and award new ones. Returns list of newly awarded achievements."""
    from backend.models.flashcard import Flashcard
    from backend.models.lesson import Lesson
    from backend.models.test_result import TestResult
    from backend.models.topic import Topic

    # Fetch data needed for checks (global across all languages — intentional)
    completed_lessons = db.query(Lesson).filter(
        Lesson.user_id == user.id,
        Lesson.is_completed == True
    ).count()

    test_results = db.query(TestResult).filter(
        TestResult.user_id == user.id
    ).all()

    total_tests = len(test_results)
    perfect_tests = sum(1 for t in test_results if t.score >= 99.5)
    xp = user.total_xp
    streak = user.streak_days or 0
    level_info = calculate_level_from_xp(xp)
    current_level = level_info["level"]

    # Flashcard stats
    total_flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user.id
    ).count()
    from sqlalchemy import func as _func
    total_reviews = db.query(Flashcard).filter(
        Flashcard.user_id == user.id,
        Flashcard.repetitions > 0
    ).with_entities(_func.sum(Flashcard.repetitions)).scalar() or 0

    # Topic stats
    total_topics = db.query(Topic).filter(Topic.user_id == user.id).count()
    topic_reviews = db.query(Topic).filter(
        Topic.user_id == user.id,
        Topic.total_reviews > 0
    ).with_entities(_func.sum(Topic.total_reviews)).scalar() or 0

    # Conversation count (from conversation sessions)
    try:
        from backend.models.conversation_session import ConversationSession
        total_conversations = db.query(ConversationSession).filter(
            ConversationSession.user_id == user.id
        ).count()
    except Exception:
        total_conversations = 0

    # Pronunciation count
    try:
        from backend.models.pronunciation import PronunciationAttempt
        total_pronunciation = db.query(PronunciationAttempt).filter(
            PronunciationAttempt.user_id == user.id
        ).count()
        perfect_pronunciation = db.query(PronunciationAttempt).filter(
            PronunciationAttempt.user_id == user.id,
            PronunciationAttempt.score >= 95
        ).count()
    except Exception:
        total_pronunciation = 0
        perfect_pronunciation = 0

    # News read count (tracked via XP log or cached — approximate from achievements)
    # We use a simple counter stored in user stats or just check flashcards from news
    news_flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user.id,
        Flashcard.example_sentence.like('From article:%')
    ).count()

    # Error review count
    try:
        from backend.models.error_log import ErrorLog
        errors_reviewed = db.query(ErrorLog).filter(
            ErrorLog.user_id == user.id
        ).count()
    except Exception:
        errors_reviewed = 0

    # Language profiles count (from JSON field on User)
    import json as _json
    try:
        profiles = _json.loads(user.language_profiles or '{}')
        language_count = len([k for k, v in profiles.items() if v])
    except Exception:
        language_count = 1

    # Already unlocked
    existing = {a.achievement_type for a in db.query(Achievement).filter(
        Achievement.user_id == user.id
    ).all()}

    candidates = []

    def maybe_award(ach_type: str):
        if ach_type not in existing and ach_type in ACHIEVEMENT_DEFS:
            candidates.append(ach_type)

    # ── Lesson-based ──
    if completed_lessons >= 1: maybe_award("first_lesson")
    if completed_lessons >= 5: maybe_award("lessons_5")
    if completed_lessons >= 10: maybe_award("lessons_10")
    if completed_lessons >= 25: maybe_award("lessons_25")
    if completed_lessons >= 50: maybe_award("lessons_50")
    if completed_lessons >= 100: maybe_award("lessons_100")

    # ── Streak-based ──
    if streak >= 3: maybe_award("streak_3")
    if streak >= 7: maybe_award("streak_7")
    if streak >= 14: maybe_award("streak_14")
    if streak >= 30: maybe_award("streak_30")
    if streak >= 60: maybe_award("streak_60")
    if streak >= 100: maybe_award("streak_100")

    # ── Test-based ──
    if total_tests >= 1: maybe_award("first_test")
    if perfect_tests >= 1: maybe_award("first_test_perfect")
    if total_tests >= 10: maybe_award("tests_10")
    if total_tests >= 25: maybe_award("tests_25")
    if total_tests >= 50: maybe_award("tests_50")

    # ── XP-based ──
    if xp >= 100: maybe_award("xp_100")
    if xp >= 500: maybe_award("xp_500")
    if xp >= 1000: maybe_award("xp_1000")
    if xp >= 2500: maybe_award("xp_2500")
    if xp >= 5000: maybe_award("xp_5000")

    # ── Level-based ──
    if current_level >= 5: maybe_award("level_5")
    if current_level >= 10: maybe_award("level_10")
    if current_level >= 25: maybe_award("level_25")
    if current_level >= 50: maybe_award("level_50")

    # ── Flashcard-based ──
    if total_flashcards >= 10: maybe_award("flashcards_10")
    if total_flashcards >= 50: maybe_award("flashcards_50")
    if total_flashcards >= 100: maybe_award("flashcards_100")
    if total_reviews >= 50: maybe_award("flashcards_review_50")
    if total_reviews >= 200: maybe_award("flashcards_review_200")

    # ── Conversation-based ──
    if total_conversations >= 1: maybe_award("first_conversation")
    if total_conversations >= 5: maybe_award("conversations_5")
    if total_conversations >= 20: maybe_award("conversations_20")

    # ── Pronunciation-based ──
    if total_pronunciation >= 1: maybe_award("first_pronunciation")
    if total_pronunciation >= 5: maybe_award("pronunciation_5")
    if total_pronunciation >= 20: maybe_award("pronunciation_20")
    if perfect_pronunciation >= 1: maybe_award("pronunciation_perfect")

    # ── Topic-based ──
    if total_topics >= 1: maybe_award("first_topic")
    if total_topics >= 5: maybe_award("topics_5")
    if topic_reviews >= 10: maybe_award("topics_review_10")

    # ── News-based (tracked via flashcards created from articles) ──
    if news_flashcards >= 1: maybe_award("first_news")
    if news_flashcards >= 10: maybe_award("news_10")
    if news_flashcards >= 20: maybe_award("news_vocab_20")
    # Note: "first_news" triggers on first article-based flashcard as a proxy for reading news

    # ── Error-review-based ──
    if errors_reviewed >= 1: maybe_award("first_error_review")
    if errors_reviewed >= 50: maybe_award("errors_reviewed_50")

    # ── Multi-language ──
    if language_count >= 2: maybe_award("second_language")
    if language_count >= 3: maybe_award("third_language")

    # Award new achievements
    newly_awarded = []
    for ach_type in candidates:
        ach = Achievement(
            user_id=user.id,
            achievement_type=ach_type,
            unlocked_at=datetime.now(timezone.utc),
            notified=False
        )
        db.add(ach)
        title, description, icon = ACHIEVEMENT_DEFS[ach_type]
        newly_awarded.append({
            "type": ach_type,
            "title": title,
            "description": description,
            "icon": icon,
        })

    if newly_awarded:
        try:
            db.commit()
        except Exception:  # intentional: any DB error during concurrent achievement award
            db.rollback()
            # Another concurrent request may have awarded the same achievements
            # Re-query to return only truly new ones
            re_existing = {a.achievement_type for a in db.query(Achievement).filter(
                Achievement.user_id == user.id
            ).all()}
            return [a for a in newly_awarded if a["type"] not in re_existing]

    return newly_awarded


def get_all_achievements_for_user(user_id: int, db: Session) -> dict:
    """Return all achievements (earned + locked) for display."""
    earned_records = db.query(Achievement).filter(
        Achievement.user_id == user_id
    ).all()
    earned_types = {a.achievement_type: a for a in earned_records}

    all_achievements = []
    for ach_type, (title, description, icon) in ACHIEVEMENT_DEFS.items():
        record = earned_types.get(ach_type)
        all_achievements.append({
            "type": ach_type,
            "title": title,
            "description": description,
            "icon": icon,
            "earned": record is not None,
            "unlocked_at": record.unlocked_at.isoformat() if record else None,
        })

    return {
        "total": len(ACHIEVEMENT_DEFS),
        "earned": len(earned_types),
        "achievements": all_achievements,
    }


def get_unnotified_achievements(user_id: int, db: Session) -> list:
    """Return achievements that haven't been shown as toast yet, then mark them notified."""
    unnotified = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.notified == False
    ).all()

    result = []
    for a in unnotified:
        if a.achievement_type in ACHIEVEMENT_DEFS:
            title, description, icon = ACHIEVEMENT_DEFS[a.achievement_type]
            result.append({
                "type": a.achievement_type,
                "title": title,
                "description": description,
                "icon": icon,
                "unlocked_at": a.unlocked_at.isoformat(),
            })
        a.notified = True

    if result:
        db.commit()

    return result
