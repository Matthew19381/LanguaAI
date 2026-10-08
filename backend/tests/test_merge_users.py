"""scripts/merge_users.py (B1+B5): merge duplicate accounts into one, on a throwaway database."""
import importlib.util
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from backend.database import Base

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "merge_users.py"
spec = importlib.util.spec_from_file_location("merge_users", SCRIPT)
merge_users = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge_users)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "merge.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(bind=engine)  # models registered by conftest
    engine.dispose()
    con = sqlite3.connect(path)
    con.executescript(
        """
        INSERT INTO users (id, name, native_language, target_language, cefr_level, total_xp, login_token)
        VALUES (1, 'Target', 'Polish', 'German', 'A1', 0, NULL),
               (2, 'Old', 'Polish', 'German', 'A1', 40, 'old-token'),
               (3, 'Current', 'Polish', 'German', 'A2', 60, 'current-token'),
               (4, 'Other', 'Polish', 'German', 'A1', 5, NULL);
        INSERT INTO achievements (user_id, achievement_type, unlocked_at, notified)
        VALUES (2, 'first_lesson', '2026-08-01 10:00:00', 1), (3, 'first_lesson', '2026-09-01 10:00:00', 1),
               (3, 'first_test', '2026-09-02 10:00:00', 1);
        INSERT INTO lessons (id, user_id, day_number, title, topic, content, cefr_level, language, is_completed, created_at)
        VALUES (10, 2, 1, 'Dzień 1', 't', '{}', 'A1', 'German', 1, '2026-08-01 09:00:00'),
               (11, 2, 2, 'Dzień 2', 't', '{}', 'A1', 'German', 0, '2026-08-02 09:00:00'),
               (12, 3, 1, 'Dzień 1', 't', '{}', 'A2', 'German', 1, '2026-09-01 09:00:00'),
               (13, 3, 2, 'Dzień 2', 't', '{}', 'A2', 'German', 0, '2026-09-02 09:00:00');
        INSERT INTO study_plans (user_id, language, cefr_level, plan_data, is_active, created_at, updated_at)
        VALUES (2, 'German', 'A1', '{}', 1, '2026-08-01', '2026-08-01'),
               (3, 'German', 'A2', '{}', 1, '2026-09-01', '2026-09-01');
        INSERT INTO flashcards (id, user_id, word, translation, language, cefr_level, is_active, repetitions, created_at)
        VALUES (20, 2, 'Essen', 'jedzenie', 'German', 'A1', 1, 0, '2026-08-01'),
               (21, 3, 'essen ', 'jeść', 'German', 'A2', 1, 3, '2026-09-01'),
               (22, 3, 'gehen', 'iść', 'German', 'A2', 1, 0, '2026-09-01'),
               (23, 4, 'essen', 'jeść', 'German', 'A1', 1, 0, '2026-09-01');
        """
    )
    con.commit()
    yield path, con
    con.close()


def _run(path, *extra):
    return merge_users.main(["--db", str(path), "--target", "1", "--sources", "2,3", *extra])


def test_dry_run_changes_nothing(db):
    path, con = db
    before = path.read_bytes()
    assert _run(path) == 0
    assert path.read_bytes() == before


def test_apply_moves_everything_and_resolves_conflicts(db):
    path, con = db
    assert _run(path, "--apply") == 0
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731

    assert q("SELECT id FROM users ORDER BY id") == [(1,), (4,)]
    assert q("SELECT name, cefr_level, total_xp, login_token FROM users WHERE id = 1") == [
        ("Current", "A2", 100, "current-token")
    ]
    assert q("SELECT achievement_type, unlocked_at FROM achievements ORDER BY 1") == [
        ("first_lesson", "2026-08-01 10:00:00"), ("first_test", "2026-09-02 10:00:00")
    ]
    # completed in order, then the primary account's unfinished lesson, then the abandoned one
    assert q("SELECT id, day_number, title FROM lessons WHERE user_id = 1 ORDER BY day_number") == [
        (10, 1, "Dzień 1"), (12, 2, "Dzień 2"), (13, 3, "Dzień 3"), (11, 4, "Dzień 4")
    ]
    assert q("SELECT user_id, is_active FROM study_plans ORDER BY created_at") == [(1, 0), (1, 1)]
    # the card with FSRS history wins; another account's card is not touched
    assert q("SELECT id, user_id, is_active FROM flashcards ORDER BY id") == [
        (20, 1, 0), (21, 1, 1), (22, 1, 1), (23, 4, 1)
    ]


def test_refuses_target_with_own_data(db):
    path, con = db
    with pytest.raises(SystemExit):
        merge_users.main(["--db", str(path), "--target", "4", "--sources", "2,3", "--apply"])
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4


def test_deleted_accounts_take_their_topic_items_along(db):
    """topic_items have no user_id; left behind they were 30 FK violations on the real database."""
    path, con = db
    cols = {r[1]: r for r in con.execute("PRAGMA table_info(topics)")}
    required = [n for n, r in cols.items() if r[3] and r[4] is None and not r[5] and n != "user_id"]
    values = {n: "x" for n in required}
    con.execute(
        f"INSERT INTO topics (id, user_id, {', '.join(values)}) VALUES (7, 4, {', '.join('?' * len(values))})",
        list(values.values()),
    )
    con.execute("INSERT INTO topic_items (topic_id, item_type, item_id, title) VALUES (7, 'lesson', 1, 't')")
    con.commit()
    assert _run(path, "--apply", "--delete-users", "4") == 0
    assert con.execute("SELECT COUNT(*) FROM topic_items").fetchone()[0] == 0
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
