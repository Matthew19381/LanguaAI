"""Access gate: one shared secret protecting the whole API."""
import pytest

from backend.config import settings
from backend.routers.auth import COOKIE_NAME

TOKEN = "test-access-token-1234567890"


@pytest.fixture
def gated():
    """Turn the gate on for a test, then restore the default (off)."""
    original = settings.APP_ACCESS_TOKEN
    settings.APP_ACCESS_TOKEN = TOKEN
    yield TOKEN
    settings.APP_ACCESS_TOKEN = original


# ── Gate off (default: localhost development) ────────────────────────────────

def test_api_is_open_when_no_token_configured(client, sample_user):
    """Without APP_ACCESS_TOKEN nothing changes — local dev must stay frictionless."""
    r = client.get(f"/api/flashcards/{sample_user['user_id']}")
    assert r.status_code == 200


def test_status_reports_gate_disabled(client):
    r = client.get("/api/auth/status")
    assert r.json() == {"gate_enabled": False, "unlocked": True}


# ── Gate on ──────────────────────────────────────────────────────────────────

def test_api_blocked_without_credentials(client, sample_user, gated):
    r = client.get(f"/api/flashcards/{sample_user['user_id']}")
    assert r.status_code == 401


def test_audio_is_also_blocked(client, gated):
    """Audio is served as plain files — it must not be a hole in the gate."""
    r = client.get("/audio/anything.mp3")
    assert r.status_code == 401


def test_health_stays_reachable(client, gated):
    """Uptime checks and tunnels need an unauthenticated probe."""
    assert client.get("/api/health").status_code == 200


def test_header_token_grants_access(client, sample_user, gated):
    r = client.get(f"/api/flashcards/{sample_user['user_id']}",
                   headers={"X-App-Token": TOKEN})
    assert r.status_code == 200


def test_wrong_token_rejected(client, sample_user, gated):
    r = client.get(f"/api/flashcards/{sample_user['user_id']}",
                   headers={"X-App-Token": "nope"})
    assert r.status_code == 401


def test_unlock_sets_cookie_and_opens_access(client, sample_user, gated):
    unlocked = client.post("/api/auth/unlock", json={"token": TOKEN})
    assert unlocked.status_code == 200
    assert COOKIE_NAME in unlocked.cookies

    # The TestClient keeps the cookie, so the next call needs no header
    r = client.get(f"/api/flashcards/{sample_user['user_id']}")
    assert r.status_code == 200


def test_unlock_with_wrong_secret_is_rejected(client, gated):
    r = client.post("/api/auth/unlock", json={"token": "wrong"})
    assert r.status_code == 401
    assert COOKIE_NAME not in r.cookies


def test_status_reports_locked_then_unlocked(client, gated):
    assert client.get("/api/auth/status").json() == {
        "gate_enabled": True, "unlocked": False,
    }
    client.post("/api/auth/unlock", json={"token": TOKEN})
    assert client.get("/api/auth/status").json()["unlocked"] is True


def test_lock_forgets_the_device(client, sample_user, gated):
    client.post("/api/auth/unlock", json={"token": TOKEN})
    assert client.get(f"/api/flashcards/{sample_user['user_id']}").status_code == 200

    client.post("/api/auth/lock")
    client.cookies.clear()
    assert client.get(f"/api/flashcards/{sample_user['user_id']}").status_code == 401
