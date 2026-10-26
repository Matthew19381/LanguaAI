"""Mock Goethe B1 Sprechen (A5): flow, Goethe points and the goal rule."""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import mock_exam as svc


def _levels(level="A", **over):
    out = {part: {name: {"level": level, "reason": "r", "errors": []} for name, _ in crits}
           for part, crits in svc.RUBRIC.items()}
    for key, lvl in over.items():
        part, name = key.split("__")
        out[part][name]["level"] = lvl
    return out


def test_rubric_matches_goethe_points():
    # 28 + 40 + 16 assessed, Aussprache 16 not: 100 in the real exam
    assert svc.MAX_POINTS == 84
    assert svc.MAX_POINTS + sum(svc.NOT_ASSESSED.values()) == 100
    assert sum(m for _, m in svc.RUBRIC["teil1"]) == 28
    assert sum(m for _, m in svc.RUBRIC["teil2"]) == 40
    assert len(svc.SLIDES) == 5


def test_points_levels_and_erfuellung_e_zeroes_part():
    pts = svc.points_of(_levels("B"))
    assert pts["teil1"] == {"erfuellung": 6, "interaktion": 3, "wortschatz": 6, "strukturen": 6}
    pts = svc.points_of(_levels("A", teil2__erfuellung="E"))
    assert sum(pts["teil2"].values()) == 0
    assert sum(pts["teil1"].values()) == 28


def test_goal_needs_two_consecutive_passes():
    assert svc.goal_status([61, 60])["reached"] is True
    assert svc.goal_status([70, 55, 80])["reached"] is False
    assert svc.goal_status([90])["reached"] is False


def _exam_dict(t1="Ich schlage Samstag vor.", t2="Mein Thema ist ...", answer="Ja, weil ...", feedback="Danke, ..."):
    return {"tasks": svc.FALLBACK_TASKS, "teil2_topic": 0, "teil2_transcript": t2,
            "teil1_history": [{"role": "assistant", "content": "Hallo"}, {"role": "user", "content": t1}],
            "teil3": {"question": "Warum?", "answer": answer, "feedback": feedback}}


async def test_score_averages_two_scorings(monkeypatch):
    runs = iter([_levels("A"), _levels("C")])
    monkeypatch.setattr(svc, "generate_json", AsyncMock(side_effect=lambda p: next(runs)))
    result = await svc.score(_exam_dict())
    # A = 84, C = 42, average 63 → 75 %
    assert result["points"] == 63 and result["percent"] == 75.0 and result["passed"] is True
    assert result["parts"]["teil1"]["erfuellung"]["levels"] == ["A", "C"]
    assert result["scorings"] == 2


async def test_score_uses_one_run_if_other_fails_and_none_if_both(monkeypatch):
    calls = iter([{"broken": True}, _levels("B")])
    monkeypatch.setattr(svc, "generate_json", AsyncMock(side_effect=lambda p: next(calls)))
    result = await svc.score(_exam_dict())
    assert result["scorings"] == 1 and result["percent"] == 75.0
    monkeypatch.setattr(svc, "generate_json", AsyncMock(side_effect=RuntimeError("down")))
    assert await svc.score(_exam_dict()) is None


async def test_silent_part_is_zero_whatever_the_model_says(monkeypatch):
    monkeypatch.setattr(svc, "generate_json", AsyncMock(return_value=_levels("A")))
    result = await svc.score(_exam_dict(t2=""))
    assert sum(c["points"] for c in result["parts"]["teil2"].values()) == 0
    assert result["points"] == 44  # 28 + 16


async def test_bad_task_shape_falls_back(monkeypatch):
    monkeypatch.setattr(svc, "generate_json", AsyncMock(return_value={"teil1": {}}))
    assert await svc.generate_tasks() == svc.FALLBACK_TASKS


async def test_scoring_prompt_has_goethe_slide_rule_and_ignores_pronunciation():
    prompt = svc._scoring_prompt(_exam_dict())
    assert "A all 5 slides" in prompt and "B 3-4 slides" in prompt
    assert "do not judge pronunciation" in prompt


@pytest.fixture
def ai():
    with patch.object(svc, "generate_json", AsyncMock(return_value=svc.FALLBACK_TASKS)) as gj, \
         patch.object(svc, "generate_text", AsyncMock(return_value="Gut, und wann treffen wir uns?")) as gt:
        yield gj, gt


def test_full_flow_scores_and_counts_towards_goal(client, sample_user, ai):
    uid = sample_user["user_id"]
    gj, _ = ai
    r = client.post(f"/api/exam/start/{uid}")
    assert r.status_code == 200, r.text
    exam = r.json()
    eid = exam["exam_id"]
    assert exam["status"] == "teil1" and len(exam["slides"]) == 5
    assert exam["teil1_history"][0]["content"] == svc.FALLBACK_TASKS["teil1"]["partner_opening"]

    r = client.post(f"/api/exam/{eid}/teil1", json={"user_id": uid, "message": "Am Samstag?"})
    assert r.json()["reply"].startswith("Gut") and r.json()["turns_left"] == svc.TEIL1_MAX_TURNS - 1
    # Out of order is refused
    assert client.post(f"/api/exam/{eid}/teil3", json={"user_id": uid}).status_code == 409
    assert client.post(f"/api/exam/{eid}/teil1/finish", json={"user_id": uid}).json()["status"] == "teil2"

    r = client.post(f"/api/exam/{eid}/teil2", json={"user_id": uid, "topic_index": 1, "transcript": "Mein Thema ..."})
    assert r.json()["status"] == "teil3" and r.json()["teil3"]["question"]
    r = client.post(f"/api/exam/{eid}/teil3", json={"user_id": uid, "answer": "Weil ...", "feedback": "Danke ..."})
    assert r.json()["status"] == "scoring"

    gj.return_value = _levels("B")
    gj.side_effect = None
    r = client.post(f"/api/exam/{eid}/score", json={"user_id": uid})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "scored" and r.json()["score"]["percent"] == 75.0

    hist = client.get(f"/api/exam/history/{uid}").json()
    assert [e["percent"] for e in hist["exams"]] == [75.0]
    assert hist["goal"]["reached"] is False and hist["unfinished_exam_id"] is None


def test_scoring_failure_keeps_answers_for_retry(client, sample_user, ai):
    uid = sample_user["user_id"]
    gj, _ = ai
    eid = client.post(f"/api/exam/start/{uid}").json()["exam_id"]
    client.post(f"/api/exam/{eid}/teil1/finish", json={"user_id": uid})
    client.post(f"/api/exam/{eid}/teil2", json={"user_id": uid, "topic_index": 0, "transcript": ""})
    client.post(f"/api/exam/{eid}/teil3", json={"user_id": uid, "answer": "Ja", "feedback": ""})
    gj.side_effect = RuntimeError("down")
    assert client.post(f"/api/exam/{eid}/score", json={"user_id": uid}).status_code == 503
    assert client.get(f"/api/exam/{eid}", params={"user_id": uid}).json()["status"] == "scoring"
    assert client.get(f"/api/exam/history/{uid}").json()["unfinished_exam_id"] == eid


def test_other_user_cannot_see_exam(client, sample_user, ai):
    uid = sample_user["user_id"]
    eid = client.post(f"/api/exam/start/{uid}").json()["exam_id"]
    assert client.get(f"/api/exam/{eid}", params={"user_id": uid + 999}).status_code == 404
