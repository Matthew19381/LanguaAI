"""Today's lesson in System-Glowny's day plan, ticked by a lesson_completed event.

Contract: docs/INTEGRACJA-MODULOW.md in System-Glowny, 1.1a (suggested_items,
complete_on) and 1.2 (POST /api/v1/integrations/event with X-Module-Key).
"""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend.models.hub_outbox import HubOutbox
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.services import hub_events
from backend.services.curriculum import build_curriculum_plan
from backend.tests.conftest import TestingSessionLocal

# The contract's required event fields (hub services/schemas.py ModuleEvent)
REQUIRED = {"event_type", "module", "user_id", "timestamp", "data"}


def _plan(db, uid):
    db.add(StudyPlan(user_id=uid, language="German", cefr_level="A2",
                     plan_data=json.dumps(build_curriculum_plan(1)), is_active=True))
    db.commit()


def _lesson(db, uid, day=1, done=False, content=None, created=None):
    lesson = Lesson(user_id=uid, day_number=day, title=f"Dzień {day}: Ja i moja codzienność",
                    topic="Szyk zdania", content=json.dumps(content or {"day_type": "nowy_material",
                                                                         "module_id": "M00"}),
                    cefr_level="A2", language="German", is_completed=done,
                    completed_at=datetime.now(timezone.utc) if done else None,
                    created_at=created or datetime.now(timezone.utc))
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _items(client, uid):
    r = client.get("/api/v1/summary", params={"user_id": uid})
    assert r.status_code == 200
    return r.json()["summary"]["suggested_items"]


@pytest.fixture
def hub(monkeypatch):
    """A fake System-Glowny that records what LinguaAI sends."""
    calls, replies = [], []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status = replies.pop(0) if replies else 200
        if status == "down":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(status, json={"status": "ok", "plan_item": None})

    monkeypatch.setattr(hub_events, "hub_config", lambda: ("http://hub.test", "klucz-testowy"))
    monkeypatch.setattr(hub_events, "session_factory", TestingSessionLocal)
    monkeypatch.setattr(hub_events, "transport", httpx.MockTransport(handler))
    return calls, replies


def test_no_plan_no_item(client, sample_user):
    assert _items(client, sample_user["user_id"]) == []


def test_next_plan_day_is_suggested(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    [item] = _items(client, uid)
    assert item["title"].startswith("LinguaAI: lekcja dnia 1 (nowy materiał): ")
    assert item["complete_on"] == ["lesson_completed"]
    assert item["includes_due_reviews"] is False
    assert item["estimated_minutes"] == 30


def test_waiting_lesson_is_suggested(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, day=4, content={"day_type": "zadanie_mowione"},
            created=datetime.now(timezone.utc) - timedelta(days=30))
    [item] = _items(client, uid)
    assert item["title"] == "LinguaAI: lekcja dnia 4 (zadanie mówione): Ja i moja codzienność"


def test_no_item_after_todays_lesson(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    _lesson(db, uid, done=True)
    assert _items(client, uid) == []


def test_old_date_has_no_item(client, sample_user, db):
    uid = sample_user["user_id"]
    _plan(db, uid)
    r = client.get("/api/v1/summary", params={"user_id": uid, "date": "2026-01-05"})
    assert r.json()["summary"]["suggested_items"] == []


def test_disabled_without_key_stores_nothing(client, sample_user, db):
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid)
    assert client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid}).status_code == 200
    assert db.query(HubOutbox).count() == 0


def test_completion_is_sent_to_hub(client, sample_user, db, hub):
    calls, _ = hub
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid, day=8, content={"day_type": "nowy_material", "module_id": "M00"})
    answered = datetime.now(timezone.utc) - timedelta(hours=20)
    r = client.post(f"/api/lessons/{lesson.id}/complete",
                    json={"user_id": uid, "client_event_id": "lekcja-8", "completed_at": answered.isoformat()})
    assert r.status_code == 200
    assert len(calls) == 1
    req = calls[0]
    assert str(req.url) == "http://hub.test/api/v1/integrations/event"
    assert req.headers["X-Module-Key"] == "klucz-testowy"
    body = json.loads(req.content)
    assert REQUIRED <= body.keys()
    assert (body["event_type"], body["module"], body["user_id"]) == ("lesson_completed", "lingua-ai", str(uid))
    assert body["data"]["day_number"] == 8 and body["data"]["module_id"] == "M00"
    # Offline completion: the hub must tick the day it was done, not the sync day
    sent_at = datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))
    assert abs(sent_at - answered) < timedelta(seconds=1)
    db.expire_all()
    row = db.query(HubOutbox).one()
    assert row.done_at is not None and row.attempts == 1
    # A replayed completion sends nothing new
    client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid, "client_event_id": "lekcja-8"})
    assert len(calls) == 1


def test_hub_down_keeps_event_for_later(client, sample_user, db, hub):
    calls, replies = hub
    replies.append("down")
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid)
    assert client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid}).status_code == 200
    db.expire_all()
    row = db.query(HubOutbox).one()
    assert row.done_at is None and row.attempts == 1 and row.last_error.startswith("network")
    # Next flush (next lesson or the next start) delivers it
    assert hub_events.flush(db, transport=hub_events.transport)["sent"] == 1
    db.expire_all()
    assert db.query(HubOutbox).one().done_at is not None
    assert len(calls) == 2


def test_rejected_event_is_not_resent(client, sample_user, db, hub):
    calls, replies = hub
    replies.append(422)
    uid = sample_user["user_id"]
    lesson = _lesson(db, uid)
    client.post(f"/api/lessons/{lesson.id}/complete", json={"user_id": uid})
    db.expire_all()
    row = db.query(HubOutbox).one()
    assert row.done_at is not None and row.last_error.startswith("HTTP 422")
    assert hub_events.flush(db, transport=hub_events.transport)["sent"] == 0
    assert len(calls) == 1


def test_key_read_from_backend_env(tmp_path, monkeypatch):
    """The hub's provision_module_keys.py writes the key to backend/.env."""
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / ".env").write_text("SYSTEM_GLOWNY_MODULE_KEY=abc\nSYSTEM_GLOWNY_URL=http://127.0.0.1:8000/\n")
    monkeypatch.setattr(hub_events, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("SYSTEM_GLOWNY_MODULE_KEY", raising=False)
    monkeypatch.delenv("SYSTEM_GLOWNY_URL", raising=False)
    monkeypatch.setenv("TESTING", "0")
    assert hub_events.hub_config() == ("http://127.0.0.1:8000", "abc")
    monkeypatch.setenv("TESTING", "1")
    assert hub_events.hub_config() == ("", "")
