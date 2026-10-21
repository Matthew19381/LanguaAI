"""Bank wiedzy: one entry per curriculum skill, linked to the plan, mastery and
errors; old model-made topics moved under it; the duplicate-merge script."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.topic import Topic, TopicItem
from backend.services import curriculum as cur
from backend.services import knowledge, mastery

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)

# Old topics of user 1 on the 17.10.2026 copy: (id, name, category, parent id, lesson ids)
OLD_TOPICS = [
    (15, "Satzstellung im Aussagesatz", "grammar", None, [5]),
    (16, "Personalpronomina", "grammar", None, [5]),
    (17, "Familie und Berufe", "vocabulary", None, [5]),
    (19, "Verbposition im Aussagesatz", "grammar", None, [6]),
    (20, "Lebensmittel und Einkaufen", "vocabulary", None, [6]),
    (22, "Grammatisches Geschlecht", "grammar", None, [7]),
    (24, "Verb 'sein' - Konjugation", "grammar", None, [8]),
    (26, "Personalpronomen", "grammar", None, [8]),
    (27, "Verb 'heißen'", "vocabulary", None, [8]),
    (32, "Verbkonjugation im Präsens", "grammar", None, [11]),
    (33, "Essen und Trinken", "vocabulary", None, [11]),
    (46, "Czasownik w języku niemieckim", "grammar", None, []),
    (47, "Konjugation der regelmäßigen Verben", "grammar", 46, [11]),
    (48, "Życie codzienne", "vocabulary", None, []),
    (49, "Wortschatz: Essen und Kochen", "vocabulary", 48, [11]),
    (50, "Präsens", "grammar", None, []),
    (51, "Regelmäßige Verben im Präsens", "grammar", 50, [12]),
    (52, "Einkaufen und Lebensmittel", "vocabulary", None, [12]),
    (53, "Czasy teraźniejsze", "grammar", None, []),
    (54, "Präsens – Konjugation regelmäßiger Verben", "grammar", 53, [13]),
]


def _old_topics(db, uid):
    for tid, name, category, parent, lessons in OLD_TOPICS:
        db.add(Topic(id=tid, user_id=uid, language="German", name=name, category=category,
                     parent_id=parent, total_items=len(lessons)))
        for lesson_id in lessons:
            db.add(TopicItem(topic_id=tid, item_type="lesson", item_id=lesson_id))
    db.commit()


def _entries(db, uid):
    return {t.skill_id: t for t in db.query(Topic).filter(Topic.user_id == uid, Topic.skill_id.isnot(None))}


def test_every_skill_has_knowledge_with_rule_examples_and_errors():
    assert set(knowledge.KNOWLEDGE) == set(cur.SKILLS)
    for skill_id, k in knowledge.KNOWLEDGE.items():
        assert k["group"] in knowledge.GROUPS, skill_id
        assert len(k["rule"]) > 40 and k["examples"] and k["errors"], skill_id
        assert all(de and pl for de, pl in k["examples"]), skill_id
    # speaking skills sit in the speaking group, grammar never there
    assert {s for s, k in knowledge.KNOWLEDGE.items() if k["group"] == "mowienie"} == \
        {s for s, (kind, _) in cur.SKILLS.items() if kind == "speaking"}


def test_sync_creates_one_entry_per_skill_and_is_idempotent(db, sample_user):
    uid = sample_user["user_id"]
    entries = knowledge.sync_knowledge_base(db, uid, "German")
    assert set(entries) == set(cur.SKILLS)
    count = db.query(Topic).filter(Topic.user_id == uid).count()
    assert count == len(cur.SKILLS) + len(knowledge.GROUPS) - len(knowledge._ON_DEMAND)
    v2 = entries["G-V2"]
    assert v2.name.endswith("[G-V2]") and v2.description == knowledge.KNOWLEDGE["G-V2"]["rule"]
    assert db.get(Topic, v2.parent_id).name.startswith(knowledge._GROUP_PREFIX)

    v2.description = "stary tekst"
    db.commit()
    knowledge.sync_knowledge_base(db, uid, "German")
    assert db.query(Topic).filter(Topic.user_id == uid).count() == count
    assert db.get(Topic, v2.id).description == knowledge.KNOWLEDGE["G-V2"]["rule"]   # text from the code


def test_sync_only_for_german(db, sample_user):
    assert knowledge.sync_knowledge_base(db, sample_user["user_id"], "Spanish") == {}
    assert db.query(Topic).count() == 0


def test_old_topics_are_moved_under_their_entry_not_deleted(db, sample_user):
    uid = sample_user["user_id"]
    _old_topics(db, uid)
    entries = knowledge.sync_knowledge_base(db, uid, "German")
    parent = {t.id: t.parent_id for t in db.query(Topic)}
    for tid in (15, 19):
        assert parent[tid] == entries["G-V2"].id
    for tid in (24, 27, 32, 46, 47, 50, 51, 53, 54):
        assert parent[tid] == entries["G-PRAES"].id
    assert parent[22] == entries["G-ARTIKEL"].id
    groups = {t.name: t.id for t in db.query(Topic).filter(Topic.name.startswith(knowledge._GROUP_PREFIX))}
    vocab = groups[knowledge._GROUP_PREFIX + knowledge.GROUPS["slownictwo"][1]]
    other = groups[knowledge._GROUP_PREFIX + knowledge.GROUPS["inne"][1]]
    assert parent[17] == parent[49] == vocab
    assert parent[16] == parent[26] == other                    # pronouns: no single skill
    assert all(db.get(Topic, tid) for tid, *_ in OLD_TOPICS)


def test_entry_details_follow_the_plan_mastery_and_errors(db, sample_user):
    uid = sample_user["user_id"]
    plan = StudyPlan(user_id=uid, language="German", cefr_level="A2", is_active=True,
                     plan_data=json.dumps(cur.build_curriculum_plan()))
    db.add(plan)
    db.add(Lesson(user_id=uid, day_number=1, title="D1", topic="t", content="{}",
                  cefr_level="A2", language="German", is_completed=True))
    db.commit()
    entries = knowledge.sync_knowledge_base(db, uid, "German")

    k = knowledge.entry_details(db, entries["G-V2"])
    days = [d["day"] for d in k["plan"]["days"]]
    assert days and days[0] == 1 and k["plan"]["days"][0]["done"] is True
    assert k["plan"]["next_day"] == days[1]
    assert "M00" in k["plan"]["modules"] and k["mastery"] is None and k["recent_errors"] == []
    assert k["plan"]["foundation"] is False
    assert knowledge.FOUNDATIONS == {"G-PRAES", "G-ARTIKEL"}
    praes = knowledge.entry_details(db, entries["G-PRAES"])
    assert praes["plan"]["days"] == [] and praes["plan"]["foundation"] is True

    for i in range(5):                                   # weak V2 -> repair day before M01
        mastery.record_attempt(db, user_id=uid, language="German", skill_id="G-V2", source="exercise",
                               correct=False, occurred_at=T0 + timedelta(days=i),
                               detail={"wrong": "Heute ich gehe", "correct": "Heute gehe ich"})
    db.commit()
    mastery.apply_module_gate(db, plan, 15)
    k = knowledge.entry_details(db, entries["G-V2"])
    repair = [d for d in k["plan"]["days"] if d["repair"]]
    assert [d["day"] for d in repair] == [15]
    assert k["mastery"]["status"] == "slaba"
    assert k["recent_errors"][0]["correct"] == "Heute gehe ich" and len(k["recent_errors"]) == 5
    assert knowledge.entry_strength(k["mastery"]) == 0.0      # 0 of 5 correct
    assert knowledge.entry_details(db, db.get(Topic, entries["G-V2"].parent_id)) is None


def test_topic_api_shows_entries_with_knowledge(client, db, sample_user):
    uid = sample_user["user_id"]
    tree = client.get(f"/api/topics/{uid}/hierarchy", params={"language": "German"}).json()["topics"]
    groups = [n for n in tree if n["name"].startswith(knowledge._GROUP_PREFIX)]
    assert len(groups) == len(knowledge.GROUPS) - len(knowledge._ON_DEMAND)
    entry = next(s for g in groups for s in g["subtopics"] if s["skill_id"] == "G-DAT")
    order = knowledge.learning_order()
    assert sorted(order) == sorted(cur.SKILLS) and order[2] == "G-V2"
    szyk = next(g for g in groups if g["name"].endswith(knowledge.GROUPS["szyk"][1]))
    ids = [s["skill_id"] for s in szyk["subtopics"]]
    assert ids == sorted(ids, key=order.index)                     # programme order, not alphabet
    body = client.get(f"/api/topics/detail/{entry['id']}", params={"user_id": uid}).json()
    assert body["knowledge"]["rule"] == knowledge.KNOWLEDGE["G-DAT"]["rule"]
    assert body["knowledge"]["examples"][0]["de"]

    assert body["topic"]["is_due"] is False
    assert client.get(f"/api/topics/{uid}/due", params={"language": "German"}).json()["count"] == 0
    stats = client.get(f"/api/topics/{uid}/stats", params={"language": "German"}).json()
    assert stats["total_topics"] == len(cur.SKILLS) and stats["due_now"] == 0
    r = client.post(f"/api/topics/{entry['id']}/review", json={"rating": 3, "user_id": uid})
    assert r.status_code == 409

    listed = client.get(f"/api/topics/{uid}", params={"language": "German"}).json()
    assert any(t["skill_id"] == "G-DAT" for t in listed["topics"])

    mastery.record_attempt(db, user_id=uid, language="German", skill_id="G-DAT", source="exercise", correct=False)
    db.commit()
    skills = client.get(f"/api/skills/{uid}/mastery").json()["skills"]
    assert skills[0]["knowledge_topic_id"] == entry["id"]


@pytest.mark.asyncio
async def test_curriculum_lesson_links_to_entries_without_the_model(db, sample_user):
    from backend.services import topic_service
    from backend.tests.conftest import TestingSessionLocal

    uid = sample_user["user_id"]
    with patch.object(topic_service, "SessionLocal", TestingSessionLocal), \
            patch.object(topic_service, "extract_topics_from_lesson") as model:
        await topic_service.process_lesson_topics_bg(
            user_id=uid, language="German", cefr_level="A2", lesson_id=77, day_number=3,
            lesson_title="Dzień 3", content={"skill_ids": ["G-V2", "S-OPIS", "nie-ma"]})
    model.assert_not_called()
    entries = _entries(db, uid)
    linked = {i.topic_id for i in db.query(TopicItem).filter(TopicItem.item_id == 77)}
    assert linked == {entries["G-V2"].id, entries["S-OPIS"].id}


def test_model_topic_naming_a_skill_goes_to_its_entry(db, sample_user):
    from backend.services.topic_service import get_or_create_topic_with_parent

    uid = sample_user["user_id"]
    entry = get_or_create_topic_with_parent(db, uid, "German", "Präsens – Konjugation", category="grammar",
                                            parent_topic_name="Czasy teraźniejsze")
    assert entry.skill_id == "G-PRAES"
    assert db.query(Topic).filter(Topic.name == "Czasy teraźniejsze").count() == 0   # no new umbrella
    other = get_or_create_topic_with_parent(db, uid, "German", "Essen und Trinken", category="vocabulary")
    assert other.skill_id is None
    spanish = get_or_create_topic_with_parent(db, uid, "Spanish", "Präsens", category="grammar")
    assert spanish.skill_id is None                                  # only German has the curriculum


def test_rules_go_into_the_lesson_prompt():
    from backend.services.lesson_generator.daily_lesson import curriculum_context

    text = curriculum_context({"module_id": "M00", "phase": "Diagnoza", "day_type": "nowy_material",
                               "skill_ids": ["G-V2", "S-OPIS"], "module_task": "t"})
    assert knowledge.KNOWLEDGE["G-V2"]["rule"] in text
    assert knowledge.KNOWLEDGE["S-OPIS"]["rule"] not in text      # speaking: task, not a rule
    assert knowledge.rules_for_prompt(["nie-ma"]) == ""


def test_duplicates_are_listed_then_merged_without_losing_lessons(db, sample_user):
    uid = sample_user["user_id"]
    _old_topics(db, uid)
    db.add(Topic(id=90, user_id=uid, language="German", name="Präsens Wiederholung", category="grammar",
                 total_reviews=3))                                      # own reviews: kept
    db.commit()
    knowledge.sync_knowledge_base(db, uid, "German")
    lessons_before = {i for (i,) in db.query(TopicItem.item_id)}

    found = {d["id"]: d for d in knowledge.find_duplicates(db, uid, "German")}
    assert set(found) == {15, 19, 22, 24, 27, 32, 46, 47, 50, 51, 53, 54, 26, 52, 48}
    assert found[26]["into_id"] == 16 and found[52]["into_id"] == 20 and found[48]["into_id"] is None
    assert db.query(Topic).filter(Topic.id.in_(list(found))).count() == len(found)    # nothing changed yet

    knowledge.merge_duplicates(db, uid, "German")
    db.commit()
    entries = _entries(db, uid)
    assert db.query(Topic).filter(Topic.id.in_(list(found))).count() == 0
    assert db.get(Topic, 90) is not None
    praes = {i.item_id for i in db.query(TopicItem).filter(TopicItem.topic_id == entries["G-PRAES"].id)}
    assert praes == {8, 11, 12, 13}                                     # lesson 8 once, not twice
    assert entries["G-PRAES"].total_items == 4
    assert {i for (i,) in db.query(TopicItem.item_id)} == lessons_before
    assert db.get(Topic, 49).parent_id is not None                      # its umbrella went, it did not
    assert knowledge.find_duplicates(db, uid, "German") == []


def _script():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "scal_tematy.py"
    spec = importlib.util.spec_from_file_location("scal_tematy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_dry_run_changes_nothing_and_apply_merges(tmp_path, capsys):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.database import Base

    path = tmp_path / "kopia.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.execute(Base.metadata.tables["users"].insert().values(id=1, name="M", native_language="Polish",
                                                            target_language="German"))
    _old_topics(s, 1)
    s.close()
    engine.dispose()

    def topic_count():
        con = sqlite3.connect(path)
        try:
            return con.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        finally:
            con.close()

    assert _script().main(["--db", str(path), "--user", "1"]) == 0
    out = capsys.readouterr().out
    assert "Tryb próbny" in out and "Personalpronomen" in out and "Do usunięcia: 15" in out
    assert topic_count() == len(OLD_TOPICS)                            # dry run: nothing written

    assert _script().main(["--db", str(path), "--user", "1", "--apply"]) == 0
    assert "ZAPISANE" in capsys.readouterr().out
    assert topic_count() == len(OLD_TOPICS) - 15 + len(cur.SKILLS) + len(knowledge.GROUPS)


def test_script_needs_the_migration(tmp_path, capsys):
    path = tmp_path / "stara.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE topics (id INTEGER PRIMARY KEY, name TEXT)")
    con.close()
    assert _script().main(["--db", str(path), "--user", "1"]) == 3
    assert "migracja" in capsys.readouterr().out


def test_scripts_survive_a_windows_console(tmp_path, monkeypatch):
    """cp1250 console on the PC: a name with "→" must not crash the merge or plan script."""
    import io
    import sys

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.database import Base

    path = tmp_path / "kopia.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.execute(Base.metadata.tables["users"].insert().values(id=1, name="M", native_language="Polish",
                                                            target_language="German"))
    s.add(Topic(id=1, user_id=1, language="German", name="Präsens → Konjugation", category="grammar"))
    s.commit()
    s.close()
    engine.dispose()

    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1250", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    assert _script().main(["--db", str(path), "--user", "1"]) == 0
    console.flush()
    assert "Präsens ? Konjugation" in raw.getvalue().decode("cp1250")
