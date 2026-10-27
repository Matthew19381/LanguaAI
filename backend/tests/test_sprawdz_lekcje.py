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


def test_proposals_file_then_apply_exactly_that(copy_db, tmp_path, monkeypatch, capsys):
    out = tmp_path / "zamiany.json"
    monkeypatch.setattr(lesson_check, "generate_json", AsyncMock(return_value={"corrections": [
        {"path": "grammar.explanation", "wrong": "ja kosztuje", "correct": "ja kosztuję", "reason": "1. os."}]}))
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--ids", "12", "99", "--out", str(out)]) == 1  # 99 missing
    printed = capsys.readouterr().out
    assert "„ja kosztuje” -> „ja kosztuję”" in printed and "Tryb próbny" in printed and "Lekcja 99: nie ma" in printed
    assert _content(copy_db)["vocabulary"][0]["word"] == "Käse (KĘ-ze)"      # database untouched
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [c["correct"] for c in data["lessons"]["12"]["corrections"]] == ["Käse", "ja kosztuję"]

    # Mateusz removes the replacement he does not want; --apply calls no model
    data["lessons"]["12"]["corrections"] = data["lessons"]["12"]["corrections"][1:]
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(lesson_check, "generate_json", AsyncMock(side_effect=AssertionError("no model in --apply")))
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--apply", str(out)]) == 0
    saved = _content(copy_db)
    assert saved["grammar"]["explanation"] == "ich koste – ja kosztuję"
    assert saved["vocabulary"][0]["word"] == "Käse (KĘ-ze)"                  # removed from the file: kept
    assert len(saved["quality"]["applied_from_file"]["corrections"]) == 1

    # a second --apply finds the wrong text gone and skips it
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--apply", str(out)]) == 0
    assert "pominięte 1" in capsys.readouterr().out


def test_model_failure_gives_no_proposal(copy_db, tmp_path, monkeypatch, capsys):
    out = tmp_path / "z.json"
    monkeypatch.setattr(lesson_check, "generate_json", AsyncMock(side_effect=RuntimeError("no key")))
    assert sprawdz_lekcje.main(["--db", str(copy_db), "--ids", "12", "--out", str(out)]) == 1
    assert "Brak propozycji" in capsys.readouterr().out
    assert json.loads(out.read_text(encoding="utf-8"))["lessons"] == {}


def test_ids_or_apply_required(copy_db):
    assert sprawdz_lekcje.main(["--db", str(copy_db)]) == 2
