"""
Standalone Discord notifier — runs via Windows Task Scheduler.
Does NOT require FastAPI to be running. Reads SQLite directly.

Usage: python backend/notifier.py  (run from LinguaAI/ directory)
Setup: run backend/setup_scheduler.bat once to register scheduled tasks.
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure LinguaAI/ is in the path so backend.* imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load env from backend/.env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "LinguaAI.db"
STATE_FILE = Path(__file__).parent / "notifier_state.json"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

STATIC_TIPS = [
    {"tip": "Spaced repetition increases retention by 200%", "source": "Ebbinghaus (1885)"},
    {"tip": "Reading comprehensible input (i+1) is the core of language acquisition", "source": "Krashen (1982)"},
    {"tip": "Output practice forces you to notice gaps in your knowledge", "source": "Swain (1985)"},
    {"tip": "Learning words in context triples retention vs word lists", "source": "Nation (2001)"},
    {"tip": "Sleep consolidates newly learned vocabulary into long-term memory", "source": "Stickgold (2005)"},
    {"tip": "Interleaved practice outperforms blocked practice for retention", "source": "Kornell & Bjork (2008)"},
    {"tip": "Regular short sessions beat infrequent long sessions", "source": "Cepeda et al. (2006)"},
]


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def send_discord(embeds: list):
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping notification")
        return
    try:
        resp = httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": embeds}, timeout=10)
        resp.raise_for_status()
        logger.info(f"Discord notification sent (status {resp.status_code})")
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")


def get_tip_of_day() -> dict:
    day_of_year = date.today().timetuple().tm_yday
    return STATIC_TIPS[day_of_year % len(STATIC_TIPS)]


def run():
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return

    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    db = Session()

    state = load_state()
    today_str = date.today().isoformat()
    now_hour = datetime.now().hour

    notify_lesson_hour = int(os.getenv("NOTIFY_LESSON_HOUR", "8"))
    notify_review_hour = int(os.getenv("NOTIFY_REVIEW_HOUR", "18"))

    # Determine which type of notification to send
    is_morning = abs(now_hour - notify_lesson_hour) <= 1
    is_evening = abs(now_hour - notify_review_hour) <= 1
    is_tip_day = date.today().weekday() in (0, 2)  # Monday=0, Wednesday=2

    try:
        users = db.query(User).all()

        for user in users:
            user_state = state.get(str(user.id), {})

            # Check if we already notified this user today for this slot
            morning_key = f"{today_str}_morning"
            evening_key = f"{today_str}_evening"

            embeds = []

            if is_morning and not user_state.get(morning_key):
                # Check if today's lesson is done
                today_start = datetime.combine(date.today(), datetime.min.time())
                today_lesson = db.query(Lesson).filter(
                    Lesson.user_id == user.id,
                    Lesson.created_at >= today_start,
                    Lesson.is_completed == True
                ).first()

                # Calculate streak
                completed_lessons = db.query(Lesson).filter(
                    Lesson.user_id == user.id,
                    Lesson.is_completed == True
                ).all()
                streak = 0
                if completed_lessons:
                    lesson_dates = sorted(set(
                        l.completed_at.date() for l in completed_lessons if l.completed_at
                    ))
                    if lesson_dates:
                        streak = 1
                        for i in range(len(lesson_dates) - 1, 0, -1):
                            if (lesson_dates[i] - lesson_dates[i-1]).days == 1:
                                streak += 1
                            else:
                                break

                streak_text = f"Seria: {streak} dni 🔥" if streak > 0 else "Zacznij swoją serię dzisiaj!"
                description = f"Czas na lekcję {user.target_language}! | {streak_text}"

                if not today_lesson:
                    fields = [{"name": "🎓 Dzisiejsza lekcja", "value": description, "inline": False}]

                    if is_tip_day:
                        tip = get_tip_of_day()
                        fields.append({
                            "name": "💡 Tip dnia",
                            "value": f"{tip['tip']}\n*— {tip['source']}*",
                            "inline": False
                        })

                    embeds.append({
                        "title": f"🌅 Poranny reminder — {user.name}",
                        "color": 0x5865F2,
                        "fields": fields,
                        "footer": {"text": f"LinguaAI · {user.target_language} · {user.cefr_level}"}
                    })

                user_state[morning_key] = True

            if is_evening and not user_state.get(evening_key):
                # Check due flashcards
                now = datetime.now(timezone.utc)
                due_cards = db.query(Flashcard).filter(
                    Flashcard.user_id == user.id,
                    Flashcard.is_active == True,
                    Flashcard.next_review_date <= now
                ).count()

                if due_cards > 0:
                    # Check if yesterday's lesson was done (streak at risk)
                    yesterday = date.today() - timedelta(days=1)
                    yesterday_start = datetime.combine(yesterday, datetime.min.time())
                    yesterday_end = datetime.combine(date.today(), datetime.min.time())
                    yesterday_lesson = db.query(Lesson).filter(
                        Lesson.user_id == user.id,
                        Lesson.created_at >= yesterday_start,
                        Lesson.created_at < yesterday_end,
                        Lesson.is_completed == True
                    ).first()

                    fields = [{
                        "name": "📚 Fiszki do powtórki",
                        "value": f"{due_cards} fiszek czeka na powtórkę!",
                        "inline": False
                    }]

                    if not yesterday_lesson:
                        fields.append({
                            "name": "⚠️ Seria zagrożona!",
                            "value": "Nie było lekcji wczoraj. Zrób dzisiejszą lekcję, aby utrzymać serię!",
                            "inline": False
                        })

                    embeds.append({
                        "title": f"🌆 Wieczorny reminder — {user.name}",
                        "color": 0xF97316,
                        "fields": fields,
                        "footer": {"text": f"LinguaAI · {user.target_language} · {user.cefr_level}"}
                    })

                user_state[evening_key] = True

            if embeds:
                send_discord(embeds)

            state[str(user.id)] = user_state

        save_state(state)
        logger.info("Notifier run complete")

    finally:
        db.close()


if __name__ == "__main__":
    run()
