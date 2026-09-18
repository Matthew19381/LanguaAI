"""Tests for POST /api/assistant/ask (docs/ASYSTENT_AI_SPEC.md, t_5fa240f2)."""
from unittest.mock import patch


def test_ask_happy_path(client, sample_user):
    """Basic question with a user_id returns success + answer."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.assistant.answer_assistant_question",
        return_value="FSRS planuje powtórki na podstawie Twojej historii ocen.",
    ):
        r = client.post("/api/assistant/ask", json={
            "user_id": uid,
            "question": "Dlaczego ta karta wraca za 3 dni?",
            "route": "/flashcards",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "FSRS" in data["answer"]


def test_ask_without_element_or_selection(client, sample_user):
    """Question with no element_context/selected_text still works (both optional)."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.assistant.answer_assistant_question",
        return_value="To jest przycisk do ukończenia lekcji.",
    ) as mock_answer:
        r = client.post("/api/assistant/ask", json={
            "user_id": uid,
            "question": "Co robi ten ekran?",
            "route": "/lesson",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["answer"]
        # element_context/selected_text default to None when omitted
        _, kwargs = mock_answer.call_args
        assert kwargs["element_context"] is None
        assert kwargs["selected_text"] is None


def test_ask_with_element_context_and_selected_text(client, sample_user):
    """Element context (click-to-pick, D-1) and selected text are forwarded."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.assistant.answer_assistant_question",
        return_value="To przycisk 'Ukończ lekcję'.",
    ) as mock_answer:
        r = client.post("/api/assistant/ask", json={
            "user_id": uid,
            "question": "Co to za przycisk?",
            "route": "/lesson",
            "element_context": {
                "tag": "BUTTON",
                "text": "Ukończ lekcję",
                "aria_label": None,
                "nearest_heading": "Lekcja dnia",
                "testid": None,
            },
            "selected_text": "Ukończ lekcję",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True
        _, kwargs = mock_answer.call_args
        assert kwargs["element_context"]["tag"] == "BUTTON"
        assert kwargs["selected_text"] == "Ukończ lekcję"


def test_ask_without_user_id_still_answers(client):
    """user_id is optional — falls back to a default CEFR level (A2)."""
    with patch(
        "backend.routers.assistant.answer_assistant_question",
        return_value="Ogólna odpowiedź.",
    ) as mock_answer:
        r = client.post("/api/assistant/ask", json={
            "question": "Co to jest XP?",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True
        _, kwargs = mock_answer.call_args
        assert kwargs["cefr_level"] == "A2"


def test_ask_empty_question_rejected(client, sample_user):
    """Pydantic min_length=1 rejects an empty question with 422."""
    r = client.post("/api/assistant/ask", json={
        "user_id": sample_user["user_id"],
        "question": "",
    })
    assert r.status_code == 422


def test_ask_ai_failure_returns_graceful_message(client, sample_user):
    """AI errors never surface a 500 — success:false + a clear Polish message,
    per docs/ASYSTENT_AI_SPEC.md §4 (\"nigdy nie wywraca UI\")."""
    uid = sample_user["user_id"]
    with patch(
        "backend.routers.assistant.answer_assistant_question",
        side_effect=ValueError("Invalid JSON response from AI"),
    ):
        r = client.post("/api/assistant/ask", json={
            "user_id": uid,
            "question": "Cokolwiek",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert "niedostępny" in data["answer"]


def test_ask_rate_limited(client, sample_user):
    """The AI rate-limit middleware (30 req/60s/IP) already covers every
    /api/* AI endpoint (backend/main.py AI_ENDPOINT_PREFIXES); /api/assistant
    is now in that list. The middleware is skipped under TESTING=1
    (backend/main.py rate_limit_middleware), so this test drives the limiter
    logic directly instead of relying on live 429s through the test client."""
    from backend.main import AI_ENDPOINT_PREFIXES

    assert any("/api/assistant" == p or "/api/assistant".startswith(p) for p in AI_ENDPOINT_PREFIXES)


def test_ask_rate_limit_returns_429_when_exceeded(client, sample_user, monkeypatch):
    """Directly exercise rate_limit_middleware's counting logic against the
    /api/assistant prefix by temporarily lifting the TESTING bypass."""
    import backend.main as main_module

    monkeypatch.delenv("TESTING", raising=False)
    main_module._ai_rate_limits.clear()
    uid = sample_user["user_id"]
    try:
        with patch(
            "backend.routers.assistant.answer_assistant_question",
            return_value="ok",
        ):
            responses = []
            for _ in range(main_module.AI_RATE_LIMIT + 1):
                responses.append(client.post("/api/assistant/ask", json={
                    "user_id": uid,
                    "question": "test",
                }))
            assert responses[-1].status_code == 429
            assert all(r.status_code == 200 for r in responses[:-1])
    finally:
        import os
        os.environ["TESTING"] = "1"
        main_module._ai_rate_limits.clear()
