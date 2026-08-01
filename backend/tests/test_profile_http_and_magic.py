"""HTTP profile export/import + magic-link login (phone pairing)."""
import io
import json

from backend.models.user import User

# ── Profile export over HTTP ─────────────────────────────────────────────

def test_profile_export_downloads_json(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/v1/users/{uid}/profile-export")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    data = r.json()
    assert data["user"]["id"] == uid
    assert data["user"]["name"] == "Test User"
    assert data["version"] == 1


def test_profile_export_unknown_user_404(client):
    r = client.get("/api/v1/users/999999/profile-export")
    assert r.status_code == 404


def test_profile_import_roundtrip_via_http(client, sample_user, db):
    uid = sample_user["user_id"]
    exported = client.get(f"/api/v1/users/{uid}/profile-export").json()

    # Simulate DB reset
    db.query(User).filter(User.id == uid).delete()
    db.commit()

    files = {"file": ("profile.json", io.BytesIO(json.dumps(exported).encode()), "application/json")}
    r = client.post("/api/v1/users/import-profile", files=files)
    assert r.status_code == 200
    assert r.json()["user_id"] == uid  # same id restored

    user = db.query(User).filter(User.id == uid).first()
    assert user is not None
    assert user.name == "Test User"


def test_profile_import_rejects_invalid_json(client):
    files = {"file": ("bad.json", io.BytesIO(b"not json{{"), "application/json")}
    r = client.post("/api/v1/users/import-profile", files=files)
    assert r.status_code == 400


# ── Magic-link login ─────────────────────────────────────────────────────

def test_login_link_created_lazily_and_stable(client, sample_user):
    uid = sample_user["user_id"]
    r1 = client.get(f"/api/v1/users/{uid}/login-link")
    assert r1.status_code == 200
    token1 = r1.json()["login_token"]
    assert len(token1) >= 24

    # Second call returns the SAME token (no rotation on read)
    r2 = client.get(f"/api/v1/users/{uid}/login-link")
    assert r2.json()["login_token"] == token1


def test_magic_login_resolves_user(client, sample_user):
    uid = sample_user["user_id"]
    token = client.get(f"/api/v1/users/{uid}/login-link").json()["login_token"]

    r = client.get(f"/api/auth/magic?key={token}")
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == uid
    assert body["name"] == "Test User"
    assert body["target_language"] == "German"


def test_magic_login_rejects_bad_key(client):
    r = client.get("/api/auth/magic?key=way-too-short")
    assert r.status_code == 401
    r = client.get("/api/auth/magic?key=" + "x" * 40)
    assert r.status_code == 401
