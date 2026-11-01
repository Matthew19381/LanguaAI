"""Start learning from zero: remove the learner's progress, keep the flashcards (01.11.2026).

    py -3.11 scripts/start_od_zera.py --db COPY.db --user 1
    py -3.11 scripts/start_od_zera.py --db COPY.db --user 1 --apply

Removed for that user and language: lessons, daily/weekly/placement test results, error
exercises and their attempts (mastery of the curriculum skills), conversation sessions,
mock exams, topics with their lesson links, achievements; XP and the streak go to 0.
The active plan is replaced by the curriculum plan from day 1 (old plans stay inactive).

Kept: the flashcards with their whole review history (only their link to a removed
lesson is cleared), the account, its login link, its level and the hub settings. The
hub drops the removed exercises from Powtórki at its next sync (cards of items that
no longer exist become inactive); flashcards stay in the deck. Bank wiedzy topics come
back by themselves when the Topics page is opened. Take the placement test afterwards
from the same device: it sets the level and builds the plan again from day 1.

Without --apply nothing is written. Run it with LinguaAI stopped and after a backup.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.curriculum import build_curriculum_plan  # noqa: E402

# (label, table, filter on user_id [and language]) in delete order
REMOVED = [
    ("próby umiejętności (opanowanie)", "skill_attempts", "user_id = ? AND language = ?"),
    ("ćwiczenia i błędy (karty cw-* w hubie)", "exercises", "user_id = ? AND language = ?"),
    ("wyniki testów (dzienne, tygodniowe, plasujący)", "test_results", "user_id = ? AND language = ?"),
    ("rozmowy z AI", "conversation_sessions", "user_id = ? AND language = ?"),
    ("próbne egzaminy", "mock_exams", "user_id = ?"),
    ("osiągnięcia", "achievements", "user_id = ?"),
]
TOPICS = "user_id = ? AND language = ?"
TOPIC_ITEMS = f"topic_id IN (SELECT id FROM topics WHERE {TOPICS})"
LESSONS = "user_id = ? AND language = ?"


def _console_safe() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(errors="replace")


def _params(where: str, user: int, language: str) -> tuple:
    return (user, language) if where.count("?") == 2 else (user,)


def _count(con, table: str, where: str, user: int, language: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", _params(where, user, language)).fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    _console_safe()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", type=int, required=True)
    ap.add_argument("--language", default="German")
    ap.add_argument("--cefr", default=None, help="level of the new plan; default: the user's level")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    user, lang = args.user, args.language

    con = sqlite3.connect(args.db)
    try:
        row = con.execute("SELECT name, cefr_level, total_xp, streak_days FROM users WHERE id = ?",
                          (user,)).fetchone()
        if not row:
            print(f"Brak użytkownika {user}.")
            return 2
        name, cefr, xp, streak = row
        cefr = args.cefr or cefr or "A2"
        lessons = _count(con, "lessons", LESSONS, user, lang)
        done = con.execute(f"SELECT COUNT(*) FROM lessons WHERE {LESSONS} AND is_completed = 1",
                           (user, lang)).fetchone()[0]
        cards = con.execute("SELECT COUNT(*), SUM(is_active = 1), SUM(lesson_id IS NOT NULL) FROM flashcards "
                            "WHERE user_id = ? AND language = ?", (user, lang)).fetchone()
        pending = con.execute("SELECT COUNT(*) FROM hub_outbox WHERE done_at IS NULL").fetchone()[0]

        print(f"Użytkownik {user} ({name}), język {lang}.")
        print("Do usunięcia:")
        print(f"  lekcje: {lessons} (ukończone {done})")
        for label, table, where in REMOVED:
            print(f"  {label}: {_count(con, table, where, user, lang)}")
        print(f"  tematy: {_count(con, 'topics', TOPICS, user, lang)} "
              f"(powiązania z lekcjami: {_count(con, 'topic_items', TOPIC_ITEMS, user, lang)}; "
              "wpisy Banku wiedzy wrócą same)")
        print(f"  XP: {xp} → 0, seria: {streak} → 0")
        print(f"Plan: aktywny plan zastąpi plan z programu od dnia 1 (poziom {cefr}).")
        print(f"Zostaje: fiszki {cards[0]} (aktywne {cards[1] or 0}) z całą historią powtórek; "
              f"powiązanie z lekcją wyczyszczone w {cards[2] or 0}.")
        if pending:
            print(f"Uwaga: {pending} zdarzeń czeka na wysłanie do huba (zostają bez zmian).")
        if not args.apply:
            print("Tryb próbny: nic nie zapisano. Dodaj --apply, żeby zapisać.")
            return 0

        plan = build_curriculum_plan(start_day=1, cefr_level=cefr)
        now = datetime.now(timezone.utc).isoformat(sep=" ")
        with con:
            con.execute(f"UPDATE flashcards SET lesson_id = NULL WHERE user_id = ? AND language = ? "
                        f"AND lesson_id IN (SELECT id FROM lessons WHERE {LESSONS})", (user, lang, user, lang))
            con.execute("UPDATE exercises SET variant_of = NULL WHERE user_id = ? AND language = ?", (user, lang))
            for _label, table, where in REMOVED:
                con.execute(f"DELETE FROM {table} WHERE {where}", _params(where, user, lang))
            con.execute(f"DELETE FROM topic_items WHERE {TOPIC_ITEMS}", (user, lang))
            con.execute(f"UPDATE topics SET parent_id = NULL WHERE {TOPICS}", (user, lang))
            con.execute(f"DELETE FROM topics WHERE {TOPICS}", (user, lang))
            con.execute(f"DELETE FROM lessons WHERE {LESSONS}", (user, lang))
            con.execute("UPDATE users SET total_xp = 0, streak_days = 0 WHERE id = ?", (user,))
            con.execute("UPDATE study_plans SET is_active = 0 WHERE user_id = ? AND language = ? AND is_active = 1",
                        (user, lang))
            con.execute("INSERT INTO study_plans (user_id, language, cefr_level, plan_data, created_at, updated_at, "
                        "is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                        (user, lang, cefr, json.dumps(plan, ensure_ascii=False), now, now))
        left = _count(con, "lessons", LESSONS, user, lang)
        kept = con.execute("SELECT COUNT(*) FROM flashcards WHERE user_id = ? AND language = ?",
                           (user, lang)).fetchone()[0]
        print(f"ZAPISANE. Lekcji: {left}, fiszek: {kept}. Następna lekcja: dzień 1.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
