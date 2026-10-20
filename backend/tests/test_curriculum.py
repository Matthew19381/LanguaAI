"""A2→B1 curriculum: plan shape, skill ids, link to the lesson prompt, plan switch script."""
import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import curriculum as cur
from backend.services.lesson_generator.daily_lesson import (
    curriculum_context,
    generate_daily_lesson,
    plan_entry_for_day,
    tag_exercise_skills,
)


def test_every_module_uses_known_skills_and_has_two_weeks():
    ids = [m["id"] for m in cur.MODULES]
    assert len(ids) == len(set(ids)) == 23
    for m in cur.MODULES:
        assert len(m["vocab"]) == 2 and len(m["grammar"]) == 2
        assert all(g in cur.SKILLS and cur.SKILLS[g][0] == "grammar" for g in m["grammar"])
        assert cur.SKILLS[m["speaking"]][0] == "speaking"
        assert m["task"]


def test_b1_grammar_missing_from_the_old_plan_is_covered():
    taught = {g for m in cur.MODULES for g in m["grammar"]}
    for skill in ("G-TRENN", "G-REFL", "G-WECHSEL", "G-K2", "G-REL", "G-ZU", "G-PASSIV"):
        assert skill in taught


def test_word_order_comes_before_verb_final_clauses():
    first = {}
    for i, m in enumerate(cur.MODULES):
        for g in m["grammar"]:
            first.setdefault(g, i)
    assert first["G-V2"] < first["G-WEIL-DASS"] < first["G-REL"]
    # accusative before dative, and both before the two-way prepositions that need them
    assert first["G-AKK"] <= first["G-DAT"] <= first["G-WECHSEL"]
    assert [g for m in cur.MODULES for g in m["grammar"]].index("G-AKK") < \
        [g for m in cur.MODULES for g in m["grammar"]].index("G-DAT")


def test_plan_starts_at_the_next_lesson_and_has_the_stored_shape():
    plan = cur.build_curriculum_plan(start_day=8)
    days = plan["daily_topics"]
    assert days[0]["day"] == 8
    assert [d["day"] for d in days] == list(range(8, 8 + 23 * 14))
    assert len(plan["weekly_goals"]) == 46
    for d in days:
        assert d["grammar_topic"] and d["vocabulary_theme"] and d["conversation_topic"]
        assert all(s in cur.SKILLS for s in d["skill_ids"])
    assert plan["curriculum_id"] == cur.CURRICULUM_ID


def test_two_week_rhythm_and_mock_exam_every_third_module():
    days = cur.build_curriculum_plan()["daily_topics"]
    m01 = [d for d in days if d["module_id"] == "M01"]
    assert [d["day_type"] for d in m01[:7]] == cur.DAY_TYPES
    exams = sorted({d["module_id"] for d in days if d["day_type"] == "probny_egzamin"})
    assert exams[:3] == ["M03", "M06", "M09"]
    assert "M22" in exams
    # the speaking task is practised on task and fluency days
    assert m01[2]["conversation_topic"] == cur.MODULES[1]["task"]
    # week 2 uses the module's second grammar point
    assert m01[7]["grammar_topic"] == cur.skill_name("G-TRENN")


def test_curriculum_only_for_german_a2_b1():
    assert cur.uses_curriculum("German", "A2")
    assert cur.uses_curriculum("German", "B1")
    assert not cur.uses_curriculum("German", "A1")
    assert not cur.uses_curriculum("Spanish", "A2")


@pytest.mark.asyncio
async def test_study_plan_for_german_a2_comes_from_the_curriculum_without_the_model():
    from backend.services.lesson_generator.study_plan import generate_study_plan

    with patch("backend.services.lesson_generator.study_plan.generate_json",
               new=AsyncMock(side_effect=AssertionError("model must not be called"))):
        plan = await generate_study_plan({"cefr_level": "A2", "start_day": 5}, "German", "Polish")
    assert plan["curriculum_id"] == cur.CURRICULUM_ID
    assert plan["daily_topics"][0]["day"] == 5


def test_curriculum_context_names_module_task_kind_of_day_and_skill_ids():
    day = plan_entry_for_day(cur.build_curriculum_plan(), 3)
    text = curriculum_context(day)
    assert "module M00" in text
    assert day["module_task"] in text
    assert "Speaking-task day" in text
    assert "G-V2" in text and "S-OPIS" in text
    assert curriculum_context({"grammar_topic": "x"}) == ""


def test_tag_exercise_skills_keeps_only_real_ids():
    blocks = [
        {"skill_tag": "G-PERFEKT"},
        {"skill_tag": "G-PERFEKT – Perfekt z haben"},
        {"skill_tag": "Perfekt with haben"},
        {"skill_tag": "G-NIEMA"},
        "zepsute",
    ]
    out = tag_exercise_skills(blocks, ["G-PERFEKT", "S-OPIS"])
    assert [b["skill_tag"] if isinstance(b, dict) else b for b in out] == [
        "G-PERFEKT", "G-PERFEKT", "Perfekt with haben", "G-NIEMA", "zepsute"]


@pytest.mark.asyncio
async def test_lesson_from_curriculum_day_records_module_and_skills():
    plan = cur.build_curriculum_plan(start_day=1)
    captured = {}

    async def fake(prompt, *a, **k):
        captured["prompt"] = prompt
        return {
            "vocabulary": [{"word": "aufstehen", "translation": "wstawać"}],
            "grammar": {"topic": "V2", "explanation": "x"},
            "exercises": [{"type": "translation", "instruction": "x", "skill_tag": "G-V2",
                           "items": [{"prompt": "a", "answer": "b"}]}],
        }

    with patch("backend.services.lesson_generator.daily_lesson.generate_json",
               new=AsyncMock(side_effect=fake)):
        lesson = await generate_daily_lesson(
            user_id=1, target_language="German", native_language="Polish", cefr_level="A2",
            recent_topics=[], day_number=17, db=None, study_plan_data=plan)
    assert lesson["module_id"] == "M01"
    assert lesson["day_type"] == "zadanie_mowione"
    assert lesson["skill_ids"] == ["G-V2", "S-OPIS"]
    assert lesson["exercises"][0]["skill_tag"] == "G-V2"
    assert "8-12 new words" in captured["prompt"]


def _make_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, cefr_level TEXT);
        CREATE TABLE lessons (id INTEGER PRIMARY KEY, user_id INT, day_number INT, title TEXT,
            topic TEXT, language TEXT, is_completed INT);
        CREATE TABLE study_plans (id INTEGER PRIMARY KEY, user_id INT, language TEXT, cefr_level TEXT,
            plan_data TEXT, created_at TEXT, updated_at TEXT, is_active INT);
        INSERT INTO users VALUES (1, 'A2');
        INSERT INTO lessons VALUES (1,1,1,'Dzień 1','General','German',1),
                                   (2,1,2,'Dzień 2','General','German',0);
        INSERT INTO study_plans VALUES (7,1,'German','A2','{}','2026-09-01','2026-09-01',1);
    """)
    con.commit()
    con.close()


def test_switch_script_dry_run_changes_nothing(tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "plan_z_programu", Path(__file__).resolve().parents[2] / "scripts" / "plan_z_programu.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    db = tmp_path / "copy.db"
    _make_db(db)
    assert mod.main(["--db", str(db), "--user", "1"]) == 0
    out = capsys.readouterr().out
    assert "Tryb próbny" in out and "dni 3–" in out and "dzień 2: Dzień 2" in out
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*), SUM(is_active) FROM study_plans").fetchone() == (1, 1)

    assert mod.main(["--db", str(db), "--user", "1", "--apply"]) == 0
    rows = con.execute("SELECT id, is_active, plan_data FROM study_plans ORDER BY id").fetchall()
    assert [(r[0], r[1]) for r in rows][0] == (7, 0)
    new = json.loads(rows[1][2])
    assert rows[1][1] == 1 and new["daily_topics"][0]["day"] == 3
    assert mod.main(["--db", str(db), "--user", "99"]) == 2
