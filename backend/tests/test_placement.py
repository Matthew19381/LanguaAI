"""Tests for /api/placement/* endpoints."""
from unittest.mock import AsyncMock, patch

# ---------------------------------------------------------------------------
# POST /api/placement/create-user
# ---------------------------------------------------------------------------

def test_create_user_minimal(client):
    r = client.post("/api/placement/create-user", json={"name": "Anna"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["name"] == "Anna"
    assert isinstance(data["user_id"], int)
    assert data["cefr_level"] == "A1"


def test_create_user_full(client):
    r = client.post("/api/placement/create-user", json={
        "name": "Marek",
        "native_language": "Polish",
        "target_language": "Spanish",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["native_language"] == "Polish"
    assert data["target_language"] == "Spanish"


def test_create_user_default_languages(client):
    """When languages are omitted, the Settings defaults (German/Polish) are used."""
    r = client.post("/api/placement/create-user", json={"name": "Kasia"})
    data = r.json()
    # defaults from Settings
    assert data["native_language"] == "Polish"
    assert data["target_language"] == "German"


# ---------------------------------------------------------------------------
# GET /api/placement/user/{user_id}
# ---------------------------------------------------------------------------

def test_get_user_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/placement/user/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == uid
    assert data["name"] == "Test User"
    assert "created_at" in data
    assert data["streak_days"] == 0
    assert data["total_xp"] == 0


def test_get_user_not_found(client):
    r = client.get("/api/placement/user/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/placement/start  (AI call is mocked)
# ---------------------------------------------------------------------------

MOCK_PLACEMENT_TEST = {
    "questions": [
        {"id": 1, "question": "Wie heißt du?", "options": ["A", "B", "C", "D"], "correct": "A"},
    ]
}


def test_start_placement_test(client):
    with patch(
        "backend.routers.placement.generate_placement_test",
        new=AsyncMock(return_value=MOCK_PLACEMENT_TEST),
    ):
        r = client.post("/api/placement/start", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["questions"]) == 1
    assert data["total_questions"] == 1


# ---------------------------------------------------------------------------
# POST /api/placement/submit  (AI calls are mocked)
# ---------------------------------------------------------------------------

MOCK_ANALYSIS = {
    "cefr_level": "B1",
    "score": 75.0,
    "strong_areas": ["grammar"],
    "weak_areas": ["vocabulary"],
    "recommendations": "Practice more vocabulary.",
}

MOCK_STUDY_PLAN = {"weeks": []}


def test_submit_placement_without_user(client):
    with patch("backend.routers.placement.analyze_placement_results",
               new=AsyncMock(return_value=MOCK_ANALYSIS)), \
         patch("backend.routers.placement.generate_study_plan",
               new=AsyncMock(return_value=MOCK_STUDY_PLAN)):
        r = client.post("/api/placement/submit", json={
            "questions": [],
            "answers": {},
        })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["cefr_level"] == "B1"
    assert data["score"] == 75.0


def test_submit_placement_with_user(client, sample_user):
    uid = sample_user["user_id"]
    with patch("backend.routers.placement.analyze_placement_results",
               new=AsyncMock(return_value=MOCK_ANALYSIS)), \
         patch("backend.routers.placement.generate_study_plan",
               new=AsyncMock(return_value=MOCK_STUDY_PLAN)):
        r = client.post("/api/placement/submit", json={
            "user_id": uid,
            "questions": [],
            "answers": {},
        })
    assert r.status_code == 200
    # CEFR level should be updated to B1
    user_r = client.get(f"/api/placement/user/{uid}")
    assert user_r.json()["cefr_level"] == "B1"
