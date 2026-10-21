"""Merge repeated Bank wiedzy topics into one (21.10.2026).

    py -3.11 scripts/scal_tematy.py --db COPY.db --user 1
    py -3.11 scripts/scal_tematy.py --db COPY.db --user 1 --apply

Lessons before the curriculum made topics with the model, so one grammar point
got several topics (on 17.10.2026: 9 for the present tense, 2 for word order,
2 for personal pronouns). The script first creates the knowledge-base entries
(services/knowledge.py, the same as opening the page), then lists:

- old topics that repeat a skill entry: their lessons go to the entry;
- old topics with the same or nearly the same name: their lessons go to the one
  that stays;
- empty old umbrella topics (no lessons, no subtopics left).

Lesson links are moved, never lost; a lesson already on the kept topic is not
linked twice. Topics with own reviews are left alone. Without --apply nothing
is written (the work is rolled back). Run it on a copy first, then on the real
database with LinguaAI stopped and after a backup.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.db).resolve()
    if not path.is_file():
        print(f"Nie ma pliku {path}.")
        return 2
    con = sqlite3.connect(path)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(topics)")}
    finally:
        con.close()
    if "skill_id" not in cols:
        print("Brak kolumny topics.skill_id: najpierw migracja (start LinguaAI po instalacji).")
        return 3

    os.environ["DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import backend.models  # noqa: F401  (registers every table)
    from backend.services.knowledge import merge_duplicates, sync_knowledge_base

    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine, autoflush=False)()
    try:
        sync_knowledge_base(db, args.user, args.language, commit=False)
        plan = merge_duplicates(db, args.user, args.language)
        for d in plan:
            target = f"-> {d['into_id']} {d['into_name']}" if d["into_id"] else "-> usunięty"
            print(f"{d['id']:5d}  {d['name']}  [{d['reason']}, lekcji: {d['items']}]  {target}")
        print(f"Do usunięcia: {len(plan)} tematów. Powiązań z lekcjami do przeniesienia: "
              f"{sum(d['items'] for d in plan if d['into_id'])} (lekcja już podpięta pod wpis nie będzie podpięta drugi raz).")
        if not args.apply:
            db.rollback()
            print("Tryb próbny: nic nie zapisano. Dodaj --apply, żeby zapisać.")
            return 0
        db.commit()
        print("ZAPISANE.")
        return 0
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
