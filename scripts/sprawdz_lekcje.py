"""Check and correct the German of already saved lessons (A7, 26.10.2026).

    py -3.11 scripts/sprawdz_lekcje.py --db COPY.db --ids 8 12 13
    py -3.11 scripts/sprawdz_lekcje.py --db COPY.db --ids 8 12 13 --apply

New lessons are checked when they are generated (services/lesson_check.py).
This runs the same check on lessons saved before that: pronunciation in Polish
letters removed, nouns without an article flagged, and one review by the
lesson model whose exact replacements are applied. The model needs the API key
from .env, so run it from the LinguaAI folder. Without --apply nothing is
written; the corrections are only printed. Run it on a copy first, then on the
real database with LinguaAI stopped and after a backup.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _console_safe() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(errors="replace")


async def check(content: dict, native_language: str) -> dict:
    from backend.config import settings
    from backend.services.gemini_service import with_model
    from backend.services.lesson_check import check_lesson

    @with_model("lesson")
    async def run():
        return await check_lesson(content, native_language, settings.LANGUAGETOOL_URL)
    return await run()


def main(argv: list[str] | None = None) -> int:
    _console_safe()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--ids", type=int, nargs="+", required=True, help="lesson ids (column lessons.id)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.db).resolve()
    if not path.is_file():
        print(f"Nie ma pliku {path}.")
        return 2
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    con = sqlite3.connect(path)
    try:
        failed = 0
        for lesson_id in args.ids:
            row = con.execute("SELECT l.day_number, l.title, l.content, l.language, u.native_language "
                              "FROM lessons l JOIN users u ON u.id = l.user_id WHERE l.id = ?",
                              (lesson_id,)).fetchone()
            if row is None:
                print(f"Lekcja {lesson_id}: nie ma jej w bazie.")
                failed += 1
                continue
            day, title, raw, language, native = row
            print(f"\nLekcja {lesson_id} (dzień {day}): {title}")
            from backend.services.lesson_check import is_german
            if not is_german(language):
                print("  Pomijam: lekcja nie jest po niemiecku.")
                continue
            content = json.loads(raw)
            quality = asyncio.run(check(content, native or "Polish"))
            if quality["review"] == "failed":
                print("  Model nie odpowiedział (klucz API w .env?). Ta lekcja nie zostanie zapisana.")
                failed += 1
                continue
            for c in quality["corrections"]:
                print(f"  {c['path']}: „{c['wrong']}” -> „{c['correct']}”  ({c['reason']})")
            for i in quality["open_issues"]:
                print(f"  DO SPRAWDZENIA {i['path']}: {i['text']}: {i['issue']}")
            if not quality["corrections"] and not quality["open_issues"]:
                print("  Bez poprawek.")
            if args.apply:
                con.execute("UPDATE lessons SET content = ? WHERE id = ?",
                            (json.dumps(content, ensure_ascii=False), lesson_id))
        if args.apply:
            con.commit()
            print("\nZAPISANE.")
        else:
            print("\nTryb próbny: nic nie zapisano. Dodaj --apply, żeby zapisać.")
        return 1 if failed else 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
