"""Tests for /api/stats/* and /api/tips/* endpoints."""
from unittest.mock import AsyncMock, patch

# ---------------------------------------------------------------------------
# GET /api/stats/{user_id}
# ---------------------------------------------------------------------------

def test_get_stats_user_not_found(client):
    r = client.get("/api/stats/99999")
    assert r.status_code == 404


def test_get_stats_basic_structure(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/stats/{uid}")
    assert r.status_code == 200
    data = r.json()

    # Top-level keys
    for key in ("user", "level_info", "lessons", "tests", "flashcards",
                "error_categories", "achievements", "new_achievements"):
        assert key in data, f"Missing key: {key}"

    # User sub-object
    assert data["user"]["id"] == uid
    assert data["user"]["name"] == "Test User"
    assert data["user"]["total_xp"] == 0

    # Level info
    li = data["level_info"]
    assert li["level"] == 1
    assert li["xp"] == 0
    assert li["max_level"] == 50

    # Empty lessons / tests
    assert data["lessons"]["total"] == 0
    assert data["tests"]["total_taken"] == 0
    assert data["flashcards"]["total"] == 0


def test_get_stats_achievements_shape(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/stats/{uid}")
    ach = r.json()["achievements"]
    assert "total" in ach
    assert "earned" in ach
    assert isinstance(ach["achievements"], list)
    assert ach["earned"] == 0


# ---------------------------------------------------------------------------
# POST /api/stats/{user_id}/xp  — REMOVED (XP injection vulnerability)
# XP is now only awarded through legitimate actions:
#   - Lesson completion (+25 XP)  → POST /api/lessons/{id}/complete
#   - Test submission (score × 0.5, max 50) → POST /api/tests/submit
# ---------------------------------------------------------------------------

def test_add_xp_endpoint_removed(client, sample_user):
    """The add_xp endpoint must not exist — it was an XP injection backdoor."""
    uid = sample_user["user_id"]
    r = client.post(f"/api/stats/{uid}/xp", json={"amount": 50, "reason": "test"})
    assert r.status_code in (404, 405)


def test_xp_only_via_legitimate_paths(client, sample_user):
    """Verify XP is 0 without completing lessons or tests."""
    uid = sample_user["user_id"]
    stats = client.get(f"/api/stats/{uid}").json()
    assert stats["user"]["total_xp"] == 0


# ---------------------------------------------------------------------------
# GET /api/stats/{user_id}/leaderboard
# ---------------------------------------------------------------------------

def test_leaderboard_single_user(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/stats/{uid}/leaderboard")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == uid
    assert data["position"] == 1
    assert data["total_users"] == 1
    assert len(data["top_users"]) == 1


def test_leaderboard_ranking(client, db):
    """User with more XP should rank higher."""
    from backend.models.user import User

    # Create users directly with different XP
    u1 = User(name="Alice", target_language="German", native_language="Polish",
              cefr_level="A1", total_xp=100)
    u2 = User(name="Bob", target_language="German", native_language="Polish",
              cefr_level="A1", total_xp=10)
    db.add_all([u1, u2])
    db.commit()

    r1 = client.get(f"/api/stats/{u1.id}/leaderboard").json()
    r2 = client.get(f"/api/stats/{u2.id}/leaderboard").json()

    assert r1["position"] < r2["position"]  # Alice ranks higher


def test_leaderboard_not_found(client):
    r = client.get("/api/stats/99999/leaderboard")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/tips/{user_id}  (AI call mocked)
# ---------------------------------------------------------------------------

def test_get_tips(client, sample_user):
    uid = sample_user["user_id"]
    mock_tips = {"tips": ["Practice every day", "Use flashcards"]}
    with patch("backend.routers.stats.generate_daily_tips",
               new=AsyncMock(return_value=mock_tips)):
        r = client.get(f"/api/tips/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["tips"]) == 2


def test_get_tips_not_found(client):
    r = client.get("/api/tips/99999")
    assert r.status_code == 404
