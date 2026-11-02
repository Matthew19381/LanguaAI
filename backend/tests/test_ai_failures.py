"""Model failures give a clear 503 and save nothing made up (01.11.2026)."""
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.models.conversation_session import ConversationSession
from backend.models.test_result import TestResult
from backend.services import gemini_service
from backend.services.lesson_generator import placement as placement_gen


def _mock_client(monkeypatch, response):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda request: response)
        return real(*args, **kwargs)

    monkeypatch.setattr(gemini_service.httpx, "AsyncClient", factory)


async def test_rate_limit_is_a_request_error(monkeypatch):
    _mock_client(monkeypatch, httpx.Response(429, json={"error": {"message": "rate limited"}}))
    with pytest.raises(httpx.RequestError):                 # routers map it to 503
        await gemini_service._call_openrouter_api("https://x/api", {"model": "m"}, {})


async def test_error_body_without_choices_is_a_request_error(monkeypatch):
    _mock_client(monkeypatch, httpx.Response(200, json={"error": {"message": "no credit"}}))
    with pytest.raises(gemini_service.AIServiceUnavailable):
        await gemini_service._call_openrouter_api("https://x/api", {"model": "m"}, {})


def test_json_object():
    assert gemini_service.json_object([{"a": 1}]) == {"a": 1}
    with pytest.raises(ValueError):
        gemini_service.json_object(["a", "b"])


def _session(db, uid, sid):
    db.add(ConversationSession(id=sid, user_id=uid, language="German", native_language="Polish",
                               cefr_level="A2", scenario="{}", system_prompt="s",
                               history=json.dumps([{"role": "user", "content": "Ich gehe ins Kino."},
                                                   {"role": "assistant", "content": "Schön!"}])))
    db.commit()


def test_failed_conversation_analysis_saves_nothing_and_keeps_the_session(client, sample_user, db):
    uid = sample_user["user_id"]
    _session(db, uid, f"s-fail-{uid}")
    with patch("backend.services.lesson_generator.conversation.generate_json",
               AsyncMock(side_effect=RuntimeError("model down"))):
        r = client.post("/api/conversation/analyze", json={"session_id": f"s-fail-{uid}", "user_id": uid})
    assert r.status_code == 503
    db.expire_all()
    assert db.get(ConversationSession, f"s-fail-{uid}") is not None          # can be retried
    assert db.query(TestResult).filter(TestResult.user_id == uid).count() == 0


def test_analysis_needs_the_owner(client, sample_user, db):
    uid = sample_user["user_id"]
    _session(db, uid, f"s-own-{uid}")
    assert client.post("/api/conversation/analyze", json={"session_id": f"s-own-{uid}"}).status_code == 422


def test_analysis_wrapped_in_a_list_works(client, sample_user, db):
    uid = sample_user["user_id"]
    _session(db, uid, f"s-list-{uid}")
    with patch("backend.services.lesson_generator.conversation.generate_json",
               AsyncMock(return_value=[{"summary": "ok", "errors": [], "score": 80}])):
        r = client.post("/api/conversation/analyze", json={"session_id": f"s-list-{uid}", "user_id": uid})
    assert r.status_code == 200 and r.json()["score"] == 80


async def test_placement_level_and_score_come_from_the_answers():
    questions = [{"id": i, "correct": "A", "cefr_hint": "A1"} for i in range(1, 11)]
    answers = {str(i): ("A" if i <= 5 else "B") for i in range(1, 11)}          # 50 %
    with patch.object(placement_gen, "generate_json",
                      AsyncMock(return_value={"cefr_level": "B1+", "score": 88})):
        r = await placement_gen.analyze_placement_results(questions, answers, "German", "Polish")
    # 50 % of the A1 questions: below the 60 % A1 rule, whatever the model says
    assert r["score"] == 50.0 and r["cefr_level"] == "A1"
    with patch.object(placement_gen, "generate_json", AsyncMock(return_value={"cefr_level": "b1"})):
        r = await placement_gen.analyze_placement_results(questions, answers, "German", "Polish")
    assert r["cefr_level"] == "A1"


def _fallback_answers(right_ids):
    qs = placement_gen._generate_fallback_questions("German", "Polish")
    wrong = {"A": "B", "B": "C", "C": "D", "D": "A"}
    return qs, {str(q["id"]): (q["correct"] if q["id"] in right_ids else wrong[q["correct"]]) for q in qs}


async def test_placement_level_is_computed_not_taken_from_the_model():
    """Review B7: the same answers must give the same level, whatever the model returns."""
    a1 = {1, 2, 3, 4}
    a2 = {5, 6, 7, 8, 16}
    b1 = {9, 10, 11, 12, 13}
    b2 = {14, 15, 17}
    cases = [
        (set(), "A1"),
        (a1, "A1"),                              # 20 % overall
        (a1 | a2, "A2"),                         # 45 %: never B1
        (a1 | a2 | {9, 10, 11}, "B1"),           # 60 %, A1+A2 100 %, B1 60 %
        (a1 | a2 | b1 | {14, 15}, "B2"),         # B1 100 %, B2 67 %, no C1
        (a1 | a2 | b1 | b2 | {18, 19}, "C1"),    # C1 100 %, C1+C2 67 %
        (set(range(1, 21)), "C2"),
    ]
    for right, expected in cases:
        qs, answers = _fallback_answers(right)
        for model_says in ("C2", "A1", "nonsense"):
            with patch.object(placement_gen, "generate_json",
                              AsyncMock(return_value={"cefr_level": model_says})):
                r = await placement_gen.analyze_placement_results(qs, answers, "German", "Polish")
            assert r["cefr_level"] == expected, (sorted(right), model_says, r["cefr_level"])
        with patch.object(placement_gen, "generate_json", AsyncMock(side_effect=RuntimeError("down"))):
            r = await placement_gen.analyze_placement_results(qs, answers, "German", "Polish")
        assert r["cefr_level"] == expected


def test_level_needs_questions_of_that_level():
    """A level the test has no questions for cannot be passed."""
    only_a = [{"cefr_hint": h, "is_correct": True} for h in ("A1",) * 4 + ("A2",) * 4]
    assert placement_gen.level_from_answers(only_a, 100.0) == "A2"


def test_fallback_placement_keys():
    q = {x["id"]: x for x in placement_gen._generate_fallback_questions("German", "Polish")}
    assert "B. zur" in q[8]["options"] and q[8]["correct"] == "B"
    assert q[14]["correct"] == "B" and q[15]["question"].startswith("Mowa zależna (Konjunktiv I)")


def test_failed_plan_leaves_the_level_unchanged(client, sample_user, db):
    from backend.models.user import User
    uid = sample_user["user_id"]
    with patch("backend.routers.placement.analyze_placement_results",
               AsyncMock(return_value={"cefr_level": "B2", "score": 90})), \
         patch("backend.routers.placement.generate_study_plan", AsyncMock(side_effect=ValueError("no plan"))):
        r = client.post("/api/placement/submit", json={"user_id": uid, "answers": {}, "questions": []})
    assert r.status_code == 400
    db.expire_all()
    assert db.get(User, uid).cefr_level == "A1"
