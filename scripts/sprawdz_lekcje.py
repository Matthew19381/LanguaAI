"""Check and correct the German of already saved lessons (A7, 26.10.2026; review step 27.10).

    py -3.11 scripts/sprawdz_lekcje.py --db COPY.db --ids 8 12 13 --out zamiany.json
    (read zamiany.json, delete the replacements you do not want)
    py -3.11 scripts/sprawdz_lekcje.py --db REAL.db --apply zamiany.json

New lessons are checked when they are generated (services/lesson_check.py).
The first command runs the same check on lessons saved before that
(pronunciation in Polish letters removed, nouns without an article flagged,
replacements confirmed by two model reviews) and writes nothing to the
database: it prints the proposed replacements and saves them to --out. The
model needs the API key from .env, so run it from the LinguaAI folder.

--apply uses no model: it writes exactly the replacements left in the file,
each only if its wrong text is still in that field, so what is saved is what
was read. The model's answer differs between runs, which is why --apply never
asks it again. Run --apply with LinguaAI stopped and after a backup.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
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


def propose(con, ids: list[int]) -> tuple[dict, int]:
    from backend.services.lesson_check import is_german
    proposals, failed = {}, 0
    for lesson_id in ids:
        row = con.execute("SELECT l.day_number, l.title, l.content, l.language, u.native_language "
                          "FROM lessons l JOIN users u ON u.id = l.user_id WHERE l.id = ?",
                          (lesson_id,)).fetchone()
        if row is None:
            print(f"Lekcja {lesson_id}: nie ma jej w bazie.")
            failed += 1
            continue
        day, title, raw, language, native = row
        print(f"\nLekcja {lesson_id} (dzień {day}): {title}")
        if not is_german(language):
            print("  Pomijam: lekcja nie jest po niemiecku.")
            continue
        quality = asyncio.run(check(json.loads(raw), native or "Polish"))
        if quality["review"] == "failed":
            print("  Model nie odpowiedział (klucz API w .env?). Brak propozycji dla tej lekcji.")
            failed += 1
            continue
        for c in quality["corrections"]:
            print(f"  {c['path']}: „{c['wrong']}” -> „{c['correct']}”  ({c['reason']})")
        for i in quality["open_issues"]:
            print(f"  DO SPRAWDZENIA {i['path']}: {i['text']}: {i['issue']}")
        if quality.get("unconfirmed"):
            print(f"  Odrzucone, bo drugi przebieg ich nie potwierdził: {quality['unconfirmed']}")
        if not quality["corrections"] and not quality["open_issues"]:
            print("  Bez poprawek.")
        proposals[str(lesson_id)] = {"day": day, "title": title, "corrections": quality["corrections"],
                                     "open_issues": quality["open_issues"]}
    return proposals, failed


def apply_file(con, data: dict) -> int:
    from backend.services.lesson_check import apply_corrections
    failed = 0
    for lesson_id, entry in (data.get("lessons") or {}).items():
        row = con.execute("SELECT content FROM lessons WHERE id = ?", (int(lesson_id),)).fetchone()
        if row is None:
            print(f"Lekcja {lesson_id}: nie ma jej w bazie.")
            failed += 1
            continue
        content = json.loads(row[0])
        applied, rejected = apply_corrections(content, entry.get("corrections") or [])
        print(f"\nLekcja {lesson_id}: zapisane zamiany {len(applied)}, pominięte {len(rejected)}")
        for c in rejected:
            print(f"  POMINIĘTA (tekstu już nie ma w polu): {c.get('path')}: „{c.get('wrong')}”")
        quality = content.get("quality") or {}
        quality["applied_from_file"] = {"at": datetime.now(timezone.utc).isoformat(), "corrections": applied}
        content["quality"] = quality
        con.execute("UPDATE lessons SET content = ? WHERE id = ?",
                    (json.dumps(content, ensure_ascii=False), int(lesson_id)))
    con.commit()
    return failed


def main(argv: list[str] | None = None) -> int:
    _console_safe()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--ids", type=int, nargs="+", help="lesson ids (column lessons.id) to check")
    ap.add_argument("--out", default="zamiany_lekcji.json", help="file for the proposed replacements")
    ap.add_argument("--apply", metavar="FILE", help="write the replacements from FILE (no model)")
    args = ap.parse_args(argv)

    path = Path(args.db).resolve()
    if not path.is_file():
        print(f"Nie ma pliku {path}.")
        return 2
    if bool(args.ids) == bool(args.apply):
        print("Podaj albo --ids (propozycje), albo --apply PLIK (zapis).")
        return 2
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    con = sqlite3.connect(path)
    try:
        if args.apply:
            data = json.loads(Path(args.apply).read_text(encoding="utf-8"))
            failed = apply_file(con, data)
            print("\nZAPISANE.")
            return 1 if failed else 0
        proposals, failed = propose(con, args.ids)
        out = Path(args.out).resolve()
        out.write_text(json.dumps({"db": str(path), "created": datetime.now(timezone.utc).isoformat(),
                                   "lessons": proposals}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nTryb próbny: baza bez zmian. Propozycje zapisane w {out}.")
        print("Usuń z pliku zamiany, których nie chcesz, potem uruchom z --apply PLIK.")
        return 1 if failed else 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
