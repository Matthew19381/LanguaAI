"""scripts/sprawdz_lekcje.py: dry run writes nothing, --apply saves the checked lesson."""
import importlib.util
import json
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.services import lesson_check

_spec = importlib.util.spec_from_file_location(
    "sprawdz_lekcje", Path(__file__).resolve().parents[2] / "scripts" / "sprawdz_lekcje.py")
sprawdz_lekcje = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sprawdz_lekcje)


@pytest.fixture
def copy_db(tmp_path):
    path = tmp_path / "kopia.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, native_language TEXT);
        CREATE TABLE lessons (id INTEGER PRIMARY KEY, user_id INTEGER, day_number INTEGER,
                              title TEXT, content TEXT, language TEXT);
        INSERT INTO users VALUES (1, 'Polish');
    """)
    content = {"vocabulary": [{"word": "Käse (KĘ-ze)", "translation": "ser"}],
               "grammar": {"explanation": "ich koste – ja kosztuje"}}
    con.execute("INSERT INTO lessons VALUES (12, 1, 6, 'Zakupy', ?, 'German')", (json.dumps(content),))
    con.commit()
    con.close()
    return path


def _content(path):
    con = sqlite3.connect(path)
    try:
        return json.loads(con.execute("SELECT content FROM lessons WHERE id = 12").fetchone()[0])
    finally:
        con.close()


def test_dry_run_then_apply(copy_db, monkeypatch, capsys):
    monkeypatch.setattr(lesson_check, "generate_json", AsyncMock(return_value={"corrections": [
        {"path": "grammar.explanation", "wrong": "ja kosztuje", "correct": "ja kosztuję", "reason": "1. os."}]}))
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--ids", "12", "99"]) == 1  # 99 does not exist
    out = capsys.readouterr().out
    assert "„ja kosztuje” -> „ja kosztuję”" in out and "Tryb próbny" in out and "Lekcja 99: nie ma" in out
    assert _content(copy_db)["vocabulary"][0]["word"] == "Käse (KĘ-ze)"

    assert sprawdz_lekcje.main(["--db", str(copy_db), "--ids", "12", "--apply"]) == 0
    saved = _content(copy_db)
    assert saved["grammar"]["explanation"] == "ich koste – ja kosztuję"
    assert saved["vocabulary"][0]["word"] == "Käse" and saved["quality"]["review"] == "ok"


def test_model_failure_saves_nothing(copy_db, monkeypatch, capsys):
    monkeypatch.setattr(lesson_check, "generate_json", AsyncMock(side_effect=RuntimeError("no key")))
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--ids", "12", "--apply"]) == 1
    assert "nie zostanie zapisana" in capsys.readouterr().out
    assert _content(copy_db)["vocabulary"][0]["word"] == "Käse (KĘ-ze)"
