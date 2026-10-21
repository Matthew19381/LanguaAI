"""Replace a learner's active study plan with the A2→B1 curriculum plan (21.10.2026).

    py -3.11 scripts/plan_z_programu.py --db COPY.db --user 1 --language German
    py -3.11 scripts/plan_z_programu.py --db COPY.db --user 1 --language German --apply

Without --apply it only prints what it would do (nothing is written). With --apply it
deactivates the active plans of that user and language and inserts the curriculum plan
in one transaction. Old plans stay in the table (is_active = 0), lessons are not touched.

The plan's first day is the highest existing lesson number + 1, because lessons are
unique per (user, language, day_number): unfinished lessons that already exist are served
before the new plan starts, and the script lists them. Always run it on a copy first and
keep a backup of the real database.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.curriculum import CURRICULUM_ID, build_curriculum_plan  # noqa: E402


def _console_safe() -> None:
    """A Windows console (cp1250) cannot print every character of the data
    ("→" in tags and topic names): print "?" for those instead of crashing."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    _console_safe()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", type=int, required=True)
    ap.add_argument("--language", default="German")
    ap.add_argument("--cefr", default=None, help="default: the user's cefr_level")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    con = sqlite3.connect(args.db)
    try:
        row = con.execute("SELECT cefr_level FROM users WHERE id = ?", (args.user,)).fetchone()
        if not row:
            print(f"Brak użytkownika {args.user}.")
            return 2
        cefr = args.cefr or row[0] or "A2"
        last_day = con.execute(
            "SELECT COALESCE(MAX(day_number), 0) FROM lessons WHERE user_id = ? AND language = ?",
            (args.user, args.language),
        ).fetchone()[0]
        unfinished = con.execute(
            "SELECT day_number, title, topic FROM lessons WHERE user_id = ? AND language = ? "
            "AND is_completed = 0 ORDER BY day_number", (args.user, args.language),
        ).fetchall()
        active = con.execute(
            "SELECT id, cefr_level, created_at FROM study_plans WHERE user_id = ? AND language = ? "
            "AND is_active = 1", (args.user, args.language),
        ).fetchall()
        plan = build_curriculum_plan(start_day=last_day + 1, cefr_level=cefr)
        days = plan["daily_topics"]

        print(f"Użytkownik {args.user}, {args.language}, poziom {cefr}")
        print(f"Aktywne plany do wyłączenia: {[a[0] for a in active] or 'brak'}")
        print(f"Nowy plan: {CURRICULUM_ID}, dni {days[0]['day']}–{days[-1]['day']} ({len(days)} lekcji)")
        print(f"Pierwszy dzień: {days[0]['module_id']} — {days[0]['grammar_topic']} / {days[0]['vocabulary_theme']}")
        if unfinished:
            print(f"Nieukończone lekcje ze starego planu ({len(unfinished)}), podawane przed nowym planem:")
            for d, title, topic in unfinished:
                print(f"  dzień {d}: {title} ({topic})")

        if not args.apply:
            print("Tryb próbny: nic nie zapisano. Dodaj --apply, żeby zapisać.")
            return 0
        now = datetime.now(timezone.utc).isoformat(sep=" ")
        with con:
            con.execute(
                "UPDATE study_plans SET is_active = 0, updated_at = ? WHERE user_id = ? AND language = ? "
                "AND is_active = 1", (now, args.user, args.language),
            )
            con.execute(
                "INSERT INTO study_plans (user_id, language, cefr_level, plan_data, created_at, updated_at, "
                "is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (args.user, args.language, cefr, json.dumps(plan, ensure_ascii=False), now, now),
            )
        print("ZAPISANE.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
