"""Conversation practises the study plan's module task, and corrects with a
prompt before giving the answer (Lyster & Saito 2010: prompts > recasts).
"""
import json
from unittest.mock import AsyncMock, patch

from backend.models.conversation_session import ConversationSession
from backend.models.study_plan import StudyPlan
from backend.routers.conversation import _build_reply_prompt
from backend.services.curriculum import build_curriculum_plan
from backend.services.lesson_generator import conversation as conv_gen


def _plan(db, uid, start_day=1):
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(start_day)), is_active=True))
    db.commit()


def test_module_task_none_without_plan(client, sample_user):
    r = client.get(f"/api/conversation/module-task/{sample_user['user_id']}")
    assert r.status_code == 200 and r.json() == {"module_task": None}


def test_module_task_from_plan_day(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    task = client.get(f"/api/conversation/module-task/{uid}").json()["module_task"]
    assert task["day_number"] == 1 and task["module_id"] == "M00"
    assert task["task"] and task["topic"]
    # Only grammar targets, by name (the speaking skill is the task itself)
    assert task["target_structures"] == ["Szyk zdania: czasownik na 2. miejscu i inwersja"]


def test_start_with_module_task_passes_task_and_targets(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    expected = client.get(f"/api/conversation/module-task/{uid}").json()["module_task"]
    fake = AsyncMock(return_value={"scenario": "s", "ai_role": "a", "user_role": "u",
                                   "suggested_phrases": [], "system_prompt": "p", "opening_line": "Hallo!",
                                   "task": expected["task"], "target_structures": expected["target_structures"]})
    with patch("backend.routers.conversation.generate_conversation_scenario", fake):
        r = client.post(f"/api/conversation/start/{uid}", json={"module_task": True, "topic": "ignored"})
    assert r.status_code == 200, r.text
    kwargs = fake.call_args.kwargs
    assert kwargs["topic"] == expected["topic"]
    assert kwargs["task"] == expected["task"]
    assert kwargs["target_structures"] == expected["target_structures"]
    assert r.json()["task"] == expected["task"]


def test_start_with_module_task_without_plan_is_404(client, sample_user):
    r = client.post(f"/api/conversation/start/{sample_user['user_id']}", json={"module_task": True})
    assert r.status_code == 404


async def _fake_json(prompt):
    _fake_json.prompt = prompt
    return {"scenario": "s", "system_prompt": "You are a colleague."}


async def test_scenario_prompt_carries_task_and_keeps_it(monkeypatch):
    monkeypatch.setattr(conv_gen, "generate_json", _fake_json)
    scenario = await conv_gen.generate_conversation_scenario(
        topic="t", cefr_level="A2", user_errors=[], language="German", native_language="Polish",
        task="Opowiedz o weekendzie", target_structures=["Perfekt z haben i sein"])
    assert "Opowiedz o weekendzie" in _fake_json.prompt and "Perfekt z haben i sein" in _fake_json.prompt
    assert "incorporate the correct form" not in _fake_json.prompt
    assert scenario["task"] == "Opowiedz o weekendzie"
    assert scenario["target_structures"] == ["Perfekt z haben i sein"]


async def test_fallback_scenario_also_keeps_task(monkeypatch):
    async def broken(prompt):
        raise RuntimeError("no model")
    monkeypatch.setattr(conv_gen, "generate_json", broken)
    scenario = await conv_gen.generate_conversation_scenario(
        topic="t", cefr_level="A2", user_errors=[], language="German", native_language="Polish",
        task="Zaplanuj wyjście", target_structures=[])
    assert scenario["task"] == "Zaplanuj wyjście" and scenario["opening_line"]


def _session(scenario):
    return ConversationSession(id="s1", user_id=1, language="German", native_language="Polish",
                               cefr_level="A2", scenario=json.dumps(scenario), system_prompt="SYS",
                               history="[]")


def test_reply_prompt_cues_before_correcting_targets():
    prompt = _build_reply_prompt(_session({"ai_role": "kolega", "task": "Opowiedz o weekendzie",
                                           "target_structures": ["Perfekt z haben i sein"]}),
                                 [{"role": "user", "content": "Ich habe gegangen."}])
    assert "do not give the correct form yet" in prompt
    assert "the target structures: Perfekt z haben i sein" in prompt
    assert "previous reply and it is still" in prompt
    assert "The student's speaking task: Opowiedz o weekendzie" in prompt
    assert "model the correct form" not in prompt  # the old recast-only rule


def test_reply_prompt_without_targets_focuses_on_basic_errors():
    prompt = _build_reply_prompt(_session({"ai_role": "kelner"}), [{"role": "user", "content": "Hallo"}])
    assert "basic grammar the student should already know" in prompt
    assert "speaking task" not in prompt
