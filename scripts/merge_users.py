"""Merge several LinguaAI user accounts into one (B1+B5, prepared 2026-10-08).

Moves every row owned by the source accounts (all tables with a ``user_id`` column) to the
target account, resolves unique-key conflicts, copies the profile of the primary source onto
the target and deletes the emptied source user rows. Runs in one transaction.

    py -3.11 scripts/merge_users.py --db COPY.db --target 1 --sources 6,7,8,9,11 --dry-run

--dry-run (default ON unless --apply is given) does everything inside the transaction, prints
the report and rolls back - the file is not changed. --apply commits. Always run it on a copy
first and keep a backup of the real database.

Conflict rules:
- achievements (user_id, achievement_type): keep the earliest unlock, drop the rest.
- lessons (user_id, language, day_number): renumber per language - completed lessons first,
  then the primary account's unfinished ones, then the rest, each in creation order; generic titles "Dzień N" follow the new number.
  get_day_number() counts completed lessons, so the next new lesson stays consistent.
- study_plans: only the newest active plan per language stays active.
- flashcards with the same word (language + case-insensitive word): keep the card with the
  longest FSRS history (repetitions, last review, correct recalls, newest), deactivate the
  others (is_active = 0; --delete-duplicate-flashcards deletes them instead).
- users.login_token is unique: the target gets the primary source's token, others are dropped.
Target account must own no data (refused otherwise). Other accounts and orphaned rows
(user_id without a users row) are only reported unless --delete-users / --delete-orphans.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import defaultdict

PROFILE_FIELDS = (
    "name", "native_language", "target_language", "cefr_level", "streak_days", "streak_freezes",
    "language_profiles", "sleep_data",
)
TITLE_RE = re.compile(r"^Dzień \d+$")


def _ids(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()]


def _user_tables(con: sqlite3.Connection) -> list[str]:
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return sorted(
        t for t in tables
        if t != "users" and "user_id" in [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
    )


def _counts(con, tables, user_ids) -> dict[int, dict[str, int]]:
    marks = ",".join("?" * len(user_ids))
    out: dict[int, dict[str, int]] = defaultdict(dict)
    for t in tables:
        for uid, n in con.execute(f'SELECT user_id, COUNT(*) FROM "{t}" WHERE user_id IN ({marks}) GROUP BY 1', user_ids):
            out[uid][t] = n
    return out


def _resolve_achievements(con, sources, report):
    """Before the move: (user_id, achievement_type) is unique, keep the earliest unlock."""
    marks = ",".join("?" * len(sources))
    dups = con.execute(
        f"SELECT achievement_type, MIN(unlocked_at), COUNT(*) FROM achievements WHERE user_id IN ({marks}) "
        "GROUP BY 1 HAVING COUNT(*) > 1", sources
    ).fetchall()
    for kind, first, n in dups:
        keep = con.execute(
            f"SELECT id FROM achievements WHERE user_id IN ({marks}) AND achievement_type = ? "
            "ORDER BY unlocked_at, id LIMIT 1", [*sources, kind],
        ).fetchone()[0]
        con.execute(
            f"DELETE FROM achievements WHERE user_id IN ({marks}) AND achievement_type = ? AND id != ?",
            [*sources, kind, keep],
        )
        report.append(f"achievements: '{kind}' x{n} -> zostaje najwcześniejsze ({first}), usunięte {n - 1}")


def _renumber_lessons(con, target, original, primary, report):
    for (lang,) in con.execute("SELECT DISTINCT language FROM lessons WHERE user_id = ?", (target,)).fetchall():
        rows = con.execute(
            "SELECT id, day_number, title, is_completed, created_at FROM lessons WHERE user_id = ? AND language = ?",
            (target, lang),
        ).fetchall()
        # completed first; of the rest the primary account's lessons first (the app serves the newest
        # unfinished lesson, i.e. the one the user is on), then abandoned ones from other accounts
        rows.sort(key=lambda r: (not r[3], not r[3] and original[r[0]][0] != primary, r[4] or "", r[0]))
        for new_day, (lid, _parked, title, done, created) in enumerate(rows, start=1):
            new_title = f"Dzień {new_day}" if title and TITLE_RE.match(title) else title
            con.execute("UPDATE lessons SET day_number = ?, title = ? WHERE id = ?", (new_day, new_title, lid))
            report.append(
                f"lessons[{lang}]: id {lid} (konto {original[lid][0]}, dzień {original[lid][1]}) -> dzień {new_day} ({'ukończona' if done else 'nieukończona'}, {created})"
            )


def _single_active_plan(con, target, report):
    for (lang,) in con.execute("SELECT DISTINCT language FROM study_plans WHERE user_id = ?", (target,)).fetchall():
        active = con.execute(
            "SELECT id FROM study_plans WHERE user_id = ? AND language = ? AND is_active "
            "ORDER BY COALESCE(updated_at, created_at) DESC, id DESC",
            (target, lang),
        ).fetchall()
        for (pid,) in active[1:]:
            con.execute("UPDATE study_plans SET is_active = 0 WHERE id = ?", (pid,))
        if len(active) > 1:
            report.append(f"study_plans[{lang}]: {len(active)} active -> kept newest id {active[0][0]}")


def _dedupe_flashcards(con, target, delete, report):
    groups = con.execute(
        "SELECT language, LOWER(TRIM(word)) FROM flashcards WHERE user_id = ? AND is_active "
        "GROUP BY 1, 2 HAVING COUNT(*) > 1",
        (target,),
    ).fetchall()
    for lang, word in groups:
        cards = con.execute(
            "SELECT id, COALESCE(repetitions, 0), COALESCE(last_review_date, ''), "
            "COALESCE(correct_recall_sessions, 0), created_at FROM flashcards "
            "WHERE user_id = ? AND language = ? AND LOWER(TRIM(word)) = ? AND is_active",
            (target, lang, word),
        ).fetchall()
        cards.sort(key=lambda c: (c[1], c[2], c[3], c[4] or "", c[0]), reverse=True)
        keep, losers = cards[0], [c[0] for c in cards[1:]]
        marks = ",".join("?" * len(losers))
        if delete:
            con.execute(f"DELETE FROM flashcards WHERE id IN ({marks})", losers)
        else:
            con.execute(f"UPDATE flashcards SET is_active = 0 WHERE id IN ({marks})", losers)
        report.append(
            f"flashcards[{lang}] '{word}': kept id {keep[0]} (repetitions {keep[1]}), "
            f"{'deleted' if delete else 'deactivated'} {losers}"
        )


def merge(con, target, sources, primary, delete_users, delete_orphans, delete_dup_cards):
    report: list[str] = []
    tables = _user_tables(con)
    users = {r[0]: r for r in con.execute("SELECT id, name, total_xp FROM users")}

    missing = [u for u in [target, *sources] if u not in users]
    if missing:
        raise SystemExit(f"Brak użytkowników o id {missing}")
    if primary not in sources:
        raise SystemExit("--primary musi być jednym ze --sources")
    owned = _counts(con, tables, [target]).get(target, {})
    if owned:
        raise SystemExit(f"Konto docelowe {target} ma dane {owned} - przerwano")

    fk_before = len(con.execute("PRAGMA foreign_key_check").fetchall())
    before = _counts(con, tables, sources)
    report.append("Tabele z user_id: " + ", ".join(tables))
    for uid in sources:
        report.append(f"Konto {uid}: " + (", ".join(f"{t}={n}" for t, n in sorted(before.get(uid, {}).items())) or "brak danych"))

    marks = ",".join("?" * len(sources))
    _resolve_achievements(con, sources, report)
    original = {r[0]: (r[1], r[2]) for r in con.execute(
        f"SELECT id, user_id, day_number FROM lessons WHERE user_id IN ({marks})", sources)}
    # (user_id, language, day_number) is unique: park source lessons on negative days, renumber after
    con.execute(f"UPDATE lessons SET day_number = -id WHERE user_id IN ({marks})", sources)
    for t in tables:
        moved = con.execute(f'UPDATE "{t}" SET user_id = ? WHERE user_id IN ({marks})', [target, *sources]).rowcount
        report.append(f"-> {t}: {moved} wierszy na id {target}")

    _renumber_lessons(con, target, original, primary, report)
    _single_active_plan(con, target, report)
    _dedupe_flashcards(con, target, delete_dup_cards, report)

    cols = ", ".join(f"{f} = (SELECT {f} FROM users WHERE id = :p)" for f in PROFILE_FIELDS)
    token = con.execute("SELECT login_token FROM users WHERE id = ?", (primary,)).fetchone()[0]
    xp = sum(users[u][2] or 0 for u in sources)
    con.execute(f"UPDATE users SET login_token = NULL WHERE id IN ({marks})", sources)
    con.execute(f"UPDATE users SET {cols}, total_xp = :xp, login_token = :tok WHERE id = :t",
                {"p": primary, "xp": xp, "tok": token, "t": target})
    con.execute(f"DELETE FROM users WHERE id IN ({marks})", sources)
    report.append(
        f"users: id {target} ('{users[target][1]}') <- profil z id {primary}, total_xp = {xp}, "
        f"login_token z id {primary}; usunięte konta {sources}"
    )

    topics_before = {r[0] for r in con.execute("SELECT id FROM topics")}
    for uid in delete_users:
        for t in tables:
            n = con.execute(f'DELETE FROM "{t}" WHERE user_id = ?', (uid,)).rowcount
            if n:
                report.append(f"usunięto konto {uid}: {t} {n}")
        con.execute("DELETE FROM users WHERE id = ?", (uid,))

    existing = {r[0] for r in con.execute("SELECT id FROM users")}
    for t in tables:
        for uid, n in con.execute(f'SELECT user_id, COUNT(*) FROM "{t}" GROUP BY 1').fetchall():
            if uid is not None and uid not in existing:
                if delete_orphans:
                    con.execute(f'DELETE FROM "{t}" WHERE user_id = ?', (uid,))
                report.append(f"osierocone: {t} user_id={uid}: {n} {'(usunięte)' if delete_orphans else '(zostają)'}")

    # topic_items have no user_id: they go with the topics deleted above (otherwise each one
    # stayed as a foreign-key violation, found in the dry-run on the real database 2026-10-08)
    gone = sorted(topics_before - {r[0] for r in con.execute("SELECT id FROM topics")})
    if gone:
        n = con.execute(f"DELETE FROM topic_items WHERE topic_id IN ({','.join('?' * len(gone))})", gone).rowcount
        report.append(f"usunięto topic_items usuniętych tematów {gone}: {n}")
    # pre-existing orphans are only reported
    orphan_items = con.execute("SELECT COUNT(*) FROM topic_items WHERE topic_id NOT IN (SELECT id FROM topics)").fetchone()[0]
    if orphan_items:
        report.append(f"topic_items bez tematu: {orphan_items}")
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    report.append(f"PRAGMA foreign_key_check: przed {fk_before}, po {len(fk)} naruszeń (osierocone wiersze)")
    after = _counts(con, tables, [target]).get(target, {})
    report.append(f"Konto {target} po scaleniu: " + ", ".join(f"{t}={n}" for t, n in sorted(after.items())))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="ścieżka do pliku SQLite (najpierw kopia!)")
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--sources", type=_ids, required=True, help="np. 6,7,8,9,11")
    ap.add_argument("--primary", type=int, help="źródło profilu (domyślnie ostatnie z --sources)")
    ap.add_argument("--delete-users", type=_ids, default=[], help="konta do usunięcia razem z danymi")
    ap.add_argument("--delete-orphans", action="store_true")
    ap.add_argument("--delete-duplicate-flashcards", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    con = sqlite3.connect(args.db, isolation_level=None)
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("BEGIN")
    try:
        report = merge(con, args.target, args.sources, args.primary or args.sources[-1],
                       args.delete_users, args.delete_orphans, args.delete_duplicate_flashcards)
    except BaseException:
        con.execute("ROLLBACK")
        raise
    if args.apply:
        con.execute("COMMIT")
    else:
        con.execute("ROLLBACK")
    print("\n".join(report))
    print("ZAPISANO (--apply)" if args.apply else "DRY-RUN: nic nie zapisano (ROLLBACK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
