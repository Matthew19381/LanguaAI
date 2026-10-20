"""Mastery per curriculum skill: attempt log, status, review warm-up, module gate,
conversation errors as review items, old-tag mapping script."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.exercise import Exercise
from backend.models.skill_attempt import SkillAttempt
from backend.models.study_plan import StudyPlan
from backend.services import curriculum as cur
from backend.services import mastery

DAY = timedelta(days=1)
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def _attempts(db, uid, skill, results, start=T0, step=DAY, **kw):
    for i, ok in enumerate(results):
        mastery.record_attempt(db, user_id=uid, language="German", skill_id=skill,
                               source="exercise", correct=ok, occurred_at=start + i * step, **kw)
    db.commit()


def test_record_attempt_needs_a_catalog_id_and_marks_same_day_repeats(db, sample_user):
    uid = sample_user["user_id"]
    assert mastery.record_attempt(db, user_id=uid, language="German", skill_id="Perfekt with haben",
                                  source="exercise", correct=True) is None
    ex = Exercise(user_id=uid, language="German", prompt="a", answer="b", skill_id="G-DAT")
    db.add(ex)
    db.commit()
    for when in (T0, T0 + timedelta(hours=2), T0 + DAY):
        mastery.record_attempt(db, user_id=uid, language="German", skill_id="G-DAT",
                               source="exercise", correct=True, occurred_at=when, exercise_id=ex.id)
        db.commit()
    rows = db.query(SkillAttempt).order_by(SkillAttempt.occurred_at).all()
    assert [r.first_try for r in rows] == [True, False, True]


def test_status_needs_data_accuracy_and_different_days(db, sample_user):
    uid = sample_user["user_id"]
    _attempts(db, uid, "G-V2", [True] * 4)                                     # too few
    _attempts(db, uid, "G-DAT", [False, False, True, False, True])            # 40%
    _attempts(db, uid, "G-AKK", [True] * 5, step=timedelta(minutes=5))         # one day only
    _attempts(db, uid, "G-K2", [True, True, False, True, True, True])          # 83%, 5 days
    m = mastery.skill_mastery(db, uid, "German")
    assert m["G-V2"]["status"] == "za_malo_danych"
    assert m["G-DAT"]["status"] == "slaba" and m["G-DAT"]["accuracy"] == 0.4
    assert m["G-AKK"]["status"] == "w_nauce" and m["G-AKK"]["correct_days"] == 1
    assert m["G-K2"]["status"] == "opanowana"


def test_only_the_last_ten_first_tries_count(db, sample_user):
    uid = sample_user["user_id"]
    _attempts(db, uid, "G-REL", [False] * 10 + [True] * 10)
    assert mastery.skill_mastery(db, uid, "German")["G-REL"]["accuracy"] == 1.0


def test_answer_endpoint_logs_the_attempt_once(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = Exercise(user_id=uid, language="German", prompt="Ich gebe ___ Mann das Buch.",
                  answer="dem", skill_tag="G-DAT", skill_id="G-DAT")
    db.add(ex)
    db.commit()
    body = {"user_id": uid, "answer": "den", "client_event_id": "e-1"}
    assert client.post(f"/api/exercises/{ex.id}/answer", json=body).status_code == 200
    assert client.post(f"/api/exercises/{ex.id}/answer", json=body).json()["duplicate"] is True
    rows = db.query(SkillAttempt).all()
    assert len(rows) == 1 and rows[0].skill_id == "G-DAT" and rows[0].correct is False
    assert json.loads(rows[0].detail) == {"prompt": "Ich gebe ___ Mann das Buch.",
                                          "wrong": "den", "correct": "dem"}


def test_answer_without_catalog_skill_is_not_logged(client, db, sample_user):
    uid = sample_user["user_id"]
    ex = Exercise(user_id=uid, language="German", prompt="a", answer="b", skill_tag="Wortschatz")
    db.add(ex)
    db.commit()
    assert client.post(f"/api/exercises/{ex.id}/answer", json={"user_id": uid, "answer": "b"}).status_code == 200
    assert db.query(SkillAttempt).count() == 0


def test_lesson_exercises_get_the_skill_id(db, sample_user):
    from backend.services.exercise_service import create_exercises_from_lesson

    uid = sample_user["user_id"]
    content = {"exercises": [
        {"type": "x", "instruction": "x", "skill_tag": "G-PERFEKT", "items": [{"prompt": "p1", "answer": "a1"}]},
        {"type": "x", "instruction": "x", "skill_tag": "Wortschatz", "items": [{"prompt": "p2", "answer": "a2"}]},
    ]}
    create_exercises_from_lesson(db, content, uid, "German", "A2")
    db.commit()
    ids = {e.prompt: e.skill_id for e in db.query(Exercise).all()}
    assert ids == {"p1": "G-PERFEKT", "p2": None}


def test_conversation_errors_become_review_items(db, sample_user):
    uid = sample_user["user_id"]
    errors = [
        {"type": "word_order", "question": "Gestern ich habe gearbeitet",
         "correct_answer": "Gestern habe ich gearbeitet", "explanation": "V2", "skill_id": "G-V2"},
        {"type": "vocabulary", "question": "Ich bin 30 Jahre", "correct_answer": "Ich bin 30 Jahre alt",
         "skill_id": None},
        {"type": "grammar", "question": "ok", "correct_answer": "ok"},          # nothing to correct
        {"type": "grammar", "question": "", "correct_answer": "x"},             # no phrase
        "zepsute",
    ]
    n = mastery.cards_from_conversation_errors(db, user_id=uid, language="German", cefr_level="A2",
                                               errors=errors)
    db.commit()
    assert n == 2
    cards = {e.prompt: e for e in db.query(Exercise).all()}
    assert cards["Gestern ich habe gearbeitet"].skill_id == "G-V2"
    assert cards["Gestern ich habe gearbeitet"].exercise_type == "error_correction"
    assert cards["Ich bin 30 Jahre"].skill_id is None
    attempts = db.query(SkillAttempt).all()
    assert [(a.skill_id, a.correct, a.source) for a in attempts] == [("G-V2", False, "conversation")]
    # the same error again: a new failed attempt, no duplicate card
    assert mastery.cards_from_conversation_errors(db, user_id=uid, language="German", cefr_level="A2",
                                                  errors=errors[:1]) == 0
    db.commit()
    assert db.query(SkillAttempt).count() == 2


def test_pasted_text_analysis_adds_review_items(client, db, sample_user):
    uid = sample_user["user_id"]
    analysis = {"summary": "s", "score": 60, "errors": [
        {"type": "grammar", "question": "mit der Mann", "correct_answer": "mit dem Mann",
         "explanation": "mit + Dativ", "skill_id": "G-DAT"}]}
    with patch("backend.routers.conversation.analyze_pasted_conversation",
               new=AsyncMock(return_value=analysis)):
        r = client.post("/api/conversation/analyze-text", json={"user_id": uid, "pasted_text": "x"})
    assert r.status_code == 200 and r.json()["review_cards_added"] == 1
    assert db.query(Exercise).filter(Exercise.skill_id == "G-DAT").count() == 1


@pytest.mark.asyncio
async def test_analysis_prompt_asks_for_skill_ids_only_for_german():
    from backend.services.lesson_generator import conversation as conv

    prompts = []

    async def fake(prompt, *a, **k):
        prompts.append(prompt)
        return {"errors": []}

    with patch.object(conv, "generate_json", new=AsyncMock(side_effect=fake)):
        await conv.analyze_conversation([{"role": "user", "content": "x"}], "A2", "German", "Polish")
        await conv.analyze_pasted_conversation("x", "A2", "German", "Polish")
        await conv.analyze_conversation([{"role": "user", "content": "x"}], "A2", "Spanish", "Polish")
    assert all('"skill_id"' in p and "G-DAT" in p for p in prompts[:2])
    assert '"skill_id"' not in prompts[2] and "G-DAT" not in prompts[2]


def test_review_context_and_warmup_prompt(db, sample_user):
    from backend.services.lesson_generator.daily_lesson import review_warmup

    uid = sample_user["user_id"]
    now = datetime.now(timezone.utc)
    assert mastery.review_context(db, uid, "German") is None
    _attempts(db, uid, "G-DAT", [False] * 5, start=now - 5 * DAY,
              detail={"wrong": "mit der Mann", "correct": "mit dem Mann"})
    ctx = mastery.review_context(db, uid, "German", now=now)
    assert ctx["weak_skills"][0]["skill_id"] == "G-DAT"
    assert ctx["errors"] == [{"skill_id": "G-DAT", "wrong": "mit der Mann", "correct": "mit dem Mann"}]
    text = review_warmup(ctx)
    assert "WARM-UP FROM REVIEWS" in text and "G-DAT" in text and "mit dem Mann" in text
    assert review_warmup(None) == ""
    # errors older than the look-back stay out of the warm-up
    assert mastery.review_context(db, uid, "German", now=now + 30 * DAY)["errors"] == []


def _plan(db, uid, start_day=1):
    plan = StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(cur.build_curriculum_plan(start_day=start_day)), is_active=True)
    db.add(plan)
    db.commit()
    return plan


def test_gate_inserts_repair_days_for_a_weak_skill_at_most_twice(db, sample_user):
    uid = sample_user["user_id"]
    plan = _plan(db, uid)
    _attempts(db, uid, "G-V2", [False] * 5)            # M00 grammar, weak
    first_m01 = 15                                    # M00 = days 1-14

    data = mastery.apply_module_gate(db, plan, first_m01)
    day15 = next(d for d in data["daily_topics"] if d["day"] == 15)
    assert day15["day_type"] == "naprawa" and day15["repair_of"] == "M00"
    assert day15["skill_ids"] == ["G-V2", "S-OPIS"]
    assert next(d for d in data["daily_topics"] if d["day"] == 16)["module_id"] == "M01"
    assert len(data["daily_topics"]) == 323
    assert json.loads(db.get(StudyPlan, plan.id).plan_data) == data          # saved

    mastery.apply_module_gate(db, plan, 16)                                   # still weak: 2nd repair
    data = mastery.apply_module_gate(db, plan, 17)                            # cap reached
    assert [d["day_type"] for d in data["daily_topics"][14:17]] == ["naprawa", "naprawa", "nowy_material"]
    assert [d["day"] for d in data["daily_topics"]] == list(range(1, 325))


def test_gate_does_nothing_without_weak_skill_mid_module_or_for_a_model_plan(db, sample_user):
    uid = sample_user["user_id"]
    plan = _plan(db, uid)
    _attempts(db, uid, "G-V2", [False] * 4)            # not enough data: does not block
    assert len(mastery.apply_module_gate(db, plan, 15)["daily_topics"]) == 322
    _attempts(db, uid, "G-V2", [False] * 5, start=T0 + 10 * DAY)
    assert len(mastery.apply_module_gate(db, plan, 16)["daily_topics"]) == 322  # day 2 of M01
    assert len(mastery.apply_module_gate(db, plan, 1)["daily_topics"]) == 322   # first module
    plan.plan_data = json.dumps({"daily_topics": [{"day": 15, "day_in_module": 1}]})
    db.commit()
    assert mastery.apply_module_gate(db, plan, 15) == {"daily_topics": [{"day": 15, "day_in_module": 1}]}


def test_next_lesson_endpoint_uses_the_gated_plan_and_warmup(client, db, sample_user):
    from backend.models.lesson import Lesson

    uid = sample_user["user_id"]
    _plan(db, uid)
    for day in range(1, 15):
        db.add(Lesson(user_id=uid, day_number=day, title=f"D{day}", topic="t", content="{}",
                      cefr_level="A2", language="German", is_completed=True))
    db.commit()
    _attempts(db, uid, "G-V2", [False] * 5, start=datetime.now(timezone.utc) - 6 * DAY,
              detail={"wrong": "Heute ich gehe", "correct": "Heute gehe ich"})
    captured = {}

    async def fake_gen(**kwargs):
        captured.update(kwargs)
        return {"title": "x", "topic": "t", "vocabulary": [], "exercises": []}

    with patch("backend.routers.lessons.generate_daily_lesson", new=AsyncMock(side_effect=fake_gen)):
        r = client.post(f"/api/lessons/next/{uid}")
    assert r.status_code == 200
    assert captured["day_number"] == 15
    day = next(d for d in captured["study_plan_data"]["daily_topics"] if d["day"] == 15)
    assert day["day_type"] == "naprawa"
    assert captured["skill_review"]["errors"][0]["correct"] == "Heute gehe ich"


def test_curriculum_context_for_a_repair_day():
    from backend.services.lesson_generator.daily_lesson import curriculum_context

    text = curriculum_context({"module_id": "M00", "phase": "Diagnoza", "day_type": "naprawa",
                               "skill_ids": ["G-V2"], "module_task": "t"})
    assert "repair day after module M00" in text and "Repair day" in text


def test_mastery_endpoint(client, db, sample_user):
    uid = sample_user["user_id"]
    _attempts(db, uid, "G-DAT", [False] * 5)
    body = client.get(f"/api/skills/{uid}/mastery").json()
    assert body["thresholds"]["accuracy"] == 0.8
    assert [(s["skill_id"], s["status"]) for s in body["skills"]] == [("G-DAT", "slaba")]


def _load_script():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "mapuj_umiejetnosci", Path(__file__).resolve().parents[2] / "scripts" / "mapuj_umiejetnosci.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_old_tags_map_only_when_they_name_one_skill():
    mod = _load_script()
    # tags as they were on 17.10.2026
    assert mod.guess_skill_id("verb-second word order in declarative sentences") == "G-V2"
    assert mod.guess_skill_id("budowanie zdań oznajmujących z podmiotem i czasownikiem") == "G-V2"
    assert mod.guess_skill_id("sentence construction with V2 order and correct articles") == "G-V2"
    assert mod.guess_skill_id("odmiana czasownika sein w czasie teraźniejszym") == "G-PRAES"
    assert mod.guess_skill_id("Präsens conjugation regular verbs") == "G-PRAES"
    assert mod.guess_skill_id("rozpoznawanie rodzajnika określonego der/die/das") == "G-ARTIKEL"
    assert mod.guess_skill_id("produkcja zdań – słownictwo zakupowe + koniugacja Präsens") is None
    assert mod.guess_skill_id("tworzenie zdań opisujących dom z przymiotnikami") is None
    assert mod.guess_skill_id("rozpoznawanie słownictwa zakupowego") is None
    assert mod.guess_skill_id("G-DAT – Dativ") == "G-DAT"


def test_mapping_script_dry_run_then_apply(tmp_path, capsys):
    mod = _load_script()
    db = tmp_path / "copy.db"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE exercises (id INTEGER PRIMARY KEY, user_id INT, skill_tag TEXT);
        INSERT INTO exercises VALUES (1, 1, 'Präsens conjugation regular verbs'),
                                     (2, 1, 'rozpoznawanie słownictwa zakupowego');
    """)
    con.commit()
    assert mod.main(["--db", str(db), "--user", "1"]) == 3                    # no column yet
    con.execute("ALTER TABLE exercises ADD COLUMN skill_id TEXT")
    con.commit()
    assert mod.main(["--db", str(db), "--user", "1"]) == 0
    out = capsys.readouterr().out
    assert "Tryb próbny" in out and "G-PRAES" in out
    assert con.execute("SELECT COUNT(*) FROM exercises WHERE skill_id IS NOT NULL").fetchone() == (0,)
    assert mod.main(["--db", str(db), "--user", "1", "--apply"]) == 0
    assert con.execute("SELECT id, skill_id FROM exercises ORDER BY id").fetchall() == [(1, "G-PRAES"), (2, None)]
