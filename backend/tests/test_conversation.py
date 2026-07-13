"""Tests for /api/conversation/* endpoints."""
from unittest.mock import patch

MOCK_SCENARIO = {
    "scenario": "Everyday conversation practice",
    "ai_role": "conversation partner",
    "user_role": "learner",
    "system_prompt": "You are a helpful German conversation partner.",
    "opening_line": "Hallo! Wie geht es dir?",
    "suggested_phrases": ["Wie geht es dir?", "Ich lerne Deutsch."]
}


def test_start_conversation_basic(client, sample_user):
    """Start conversation returns scenario and session."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.conversation.generate_conversation_scenario",
        return_value=MOCK_SCENARIO,
    ):
        r = client.post(f"/api/conversation/start/{uid}", json={
            "topic": "everyday conversation"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "session_id" in data
        assert "opening_line" in data
        assert data["opening_line"] == "Hallo! Wie geht es dir?"


def test_start_conversation_user_not_found(client):
    """Start conversation returns 404 for non-existent user."""
    with patch(
        "backend.routers.conversation.generate_conversation_scenario",
        return_value=MOCK_SCENARIO,
    ):
        r = client.post("/api/conversation/start/99999", json={})
        assert r.status_code == 404


def test_send_message(client, sample_user):
    """Send message returns AI response."""
    uid = sample_user["user_id"]
    # First start a conversation
    with patch(
        "backend.routers.conversation.generate_conversation_scenario",
        return_value=MOCK_SCENARIO,
    ), patch(
        "backend.routers.conversation.generate_text",
        return_value="Das ist gut! Weiter so!"
    ):
        r1 = client.post(f"/api/conversation/start/{uid}", json={})
        assert r1.status_code == 200
        session_id = r1.json()["session_id"]

        # Send a message
        r2 = client.post("/api/conversation/message", json={
            "session_id": session_id,
            "user_message": "Ich lerne Deutsch.",
            "user_id": uid
        })
        assert r2.status_code == 200
        data = r2.json()
        assert data["success"] is True
        assert "response" in data


def test_send_message_invalid_session(client):
    """Send message returns 404 for invalid session."""
    r = client.post("/api/conversation/message", json={
        "session_id": "invalid-session-id",
        "user_message": "Hello",
        "user_id": 99999
    })
    assert r.status_code == 404


def test_analyze_conversation(client, sample_user, db):
    """Analyze conversation returns errors and score."""
    uid = sample_user["user_id"]
    # Start conversation first
    with patch(
        "backend.routers.conversation.generate_conversation_scenario",
        return_value=MOCK_SCENARIO,
    ), patch(
        "backend.routers.conversation.generate_text",
        return_value="Test response"
    ), patch(
        "backend.routers.conversation.analyze_conversation",
        return_value={
            "score": 85.0,
            "errors": [],
            "vocabulary_used": ["Hallo"],
            "recommendations": ["Keep practicing!"]
        }
    ):
        r1 = client.post(f"/api/conversation/start/{uid}", json={})
        session_id = r1.json()["session_id"]

        # Send a message to have something to analyze
        client.post("/api/conversation/message", json={
            "session_id": session_id,
            "user_message": "Ich lerne Deutsch."
        })

        # Analyze
        r2 = client.post("/api/conversation/analyze", json={
            "session_id": session_id,
            "user_id": uid
        })
        assert r2.status_code == 200
        data = r2.json()
        assert data["success"] is True
        assert "score" in data


def test_ask_question(client, sample_user):
    """Ask question returns AI answer."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.conversation.answer_language_question",
        return_value="Das ist die Vergangenheit von 'gehen'."
    ):
        r = client.post("/api/conversation/question", json={
            "user_id": uid,
            "question": "What is the past tense of 'gehen'?"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "answer" in data


def test_translate_word(client, sample_user):
    """Translate word returns translation only."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.conversation._ai_translate",
        return_value="Hallo"
    ):
        r = client.post("/api/conversation/translate", json={
            "from_lang": "German",
            "to_lang": "English",
            "text": "Hallo",
            "user_id": uid,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "translation" in data


def test_analyze_pasted_text(client, sample_user, db):
    """Analyze pasted text returns errors."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.conversation.analyze_pasted_conversation",
        return_value={
            "score": 90.0,
            "errors": [],
            "vocabulary_used": [],
            "recommendations": ["Great work!"]
        }
    ):
        r = client.post("/api/conversation/analyze-text", json={
            "user_id": uid,
            "pasted_text": "Ich lerne Deutsch. Das ist gut."
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "score" in data
