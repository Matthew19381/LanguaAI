"""Give old exercises a curriculum skill id from their free-text skill tag (21.10.2026).

    py -3.11 scripts/mapuj_umiejetnosci.py --db COPY.db --user 1
    py -3.11 scripts/mapuj_umiejetnosci.py --db COPY.db --user 1 --apply

Lessons before the curriculum tagged exercises with names the model made up
(33 different tags for about 10 skills on 17.10.2026). Mastery is summed per
skill id, so this script fills ``exercises.skill_id`` (added by the migration
c6e1a2b3d406) for tags that clearly name one skill. Tags that only name
vocabulary or mix several things stay without an id: a wrong id would put wrong
data into mastery. ``skill_tag`` itself is not changed.

Without --apply it only prints the table (tag, id, number of exercises). Only
rows with an empty ``skill_id`` are touched. Run it on a copy first.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.curriculum import find_skill_id  # noqa: E402

# Checked in this order: the first match wins. Word order first, because
# "zdania z V2 i rodzajnikami" is about word order.
RULES: list[tuple[str, re.Pattern]] = [
    ("G-V2", re.compile(r"\bv2\b|verb-second|word order|szyk|zda[nń] oznajmuj|zda[nń] twierdz", re.I)),
    ("G-PRAES", re.compile(r"pr[äa]sens|koniugac|conjugation|odmian\w* czasown|ko[nń]c[oó]wki osobowe|'sein'|\bsein\b", re.I)),
    ("G-ARTIKEL", re.compile(r"rodzajnik|article|nominativ", re.I)),
]
# A tag that also names vocabulary or adjectives mixes skills: an error there may
# be a word, not the grammar point, so it gets no id.
MIXED = re.compile(r"s[łl]ownict|vocabular|przymiotnik|adjecti", re.I)


def guess_skill_id(tag: str | None) -> str | None:
    """Catalog id written in the tag, else the first rule that matches, else None."""
    if not tag:
        return None
    found = find_skill_id(tag)
    if found:
        return found
    if MIXED.search(tag):
        return None
    for skill_id, pattern in RULES:
        if pattern.search(tag):
            return skill_id
    return None


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
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    con = sqlite3.connect(args.db)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(exercises)")}
        if "skill_id" not in cols:
            print("Brak kolumny exercises.skill_id: najpierw migracja (start LinguaAI po instalacji).")
            return 3
        rows = con.execute(
            "SELECT skill_tag, COUNT(*) FROM exercises WHERE user_id = ? AND skill_id IS NULL "
            "AND skill_tag IS NOT NULL GROUP BY skill_tag ORDER BY COUNT(*) DESC, skill_tag",
            (args.user,),
        ).fetchall()
        mapped = [(tag, guess_skill_id(tag), n) for tag, n in rows]
        for tag, skill_id, n in mapped:
            print(f"{n:4d}  {skill_id or '(bez id)':10s}  {tag}")
        with_id = [(t, s, n) for t, s, n in mapped if s]
        print(f"Tagów: {len(mapped)}, z id: {len(with_id)} ({sum(n for *_, n in with_id)} ćwiczeń), "
              f"bez id: {len(mapped) - len(with_id)}")

        if not args.apply:
            print("Tryb próbny: nic nie zapisano. Dodaj --apply, żeby zapisać.")
            return 0
        with con:
            for tag, skill_id, _ in with_id:
                con.execute(
                    "UPDATE exercises SET skill_id = ? WHERE user_id = ? AND skill_tag = ? "
                    "AND skill_id IS NULL", (skill_id, args.user, tag),
                )
        print("ZAPISANE.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
