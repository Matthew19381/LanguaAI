"""Tests for /api/settings/* endpoints."""
from unittest.mock import AsyncMock, patch


def test_ui_translations_returns_english_for_english(client):
    """UI translations endpoint returns EN dict for English."""
    with patch(
        "backend.services.gemini_service.generate_json",
        new=AsyncMock(return_value={"nav.home": "Home"}),
    ):
        r = client.get("/api/settings/ui-translations?language=English")
        assert r.status_code == 200
        data = r.json()
        assert "nav.home" in data


def test_ui_translations_fallback_on_error(client):
    """UI translations returns EN fallback when AI fails."""
    with patch(
        "backend.services.gemini_service.generate_json",
        side_effect=Exception("AI error"),
    ):
        r = client.get("/api/settings/ui-translations?language=German")
        assert r.status_code == 200
        data = r.json()
        # Should return the EN dict as fallback
        assert "nav.home" in data
        assert data["nav.home"] == "Home"


def test_gdrive_status_not_authorized(client):
    """Google Drive status returns False when not authorized."""
    with patch(
        "backend.services.google_drive_service.is_authorized",
        return_value=False,
    ):
        r = client.get("/api/settings/gdrive/status")
        assert r.status_code == 200
        data = r.json()
        assert data["authorized"] is False


def test_gdrive_status_authorized(client):
    """Google Drive status returns True when authorized."""
    with patch(
        "backend.services.google_drive_service.is_authorized",
        return_value=True,
    ):
        r = client.get("/api/settings/gdrive/status")
        assert r.status_code == 200
        data = r.json()
        assert data["authorized"] is True


def test_gdrive_auth_url(client):
    """Google Drive auth returns URL when not authorized."""
    with patch(
        "backend.services.google_drive_service.is_authorized",
        return_value=False,
    ), patch(
        "backend.services.google_drive_service.get_auth_url",
        return_value="https://accounts.google.com/o/oauth2/auth?...",
    ):
        r = client.get("/api/settings/gdrive/auth")
        assert r.status_code == 200
        data = r.json()
        assert data["authorized"] is False
        assert "auth_url" in data


def test_gdrive_auth_already_authorized(client):
    """Google Drive auth returns message when already authorized."""
    with patch(
        "backend.services.google_drive_service.is_authorized",
        return_value=True,
    ):
        r = client.get("/api/settings/gdrive/auth")
        assert r.status_code == 200
        data = r.json()
        assert data["authorized"] is True


def test_gdrive_callback_success(client):
    """Google Drive callback redirects on success."""
    with patch(
        "backend.services.google_drive_service.save_token_from_code",
        return_value=True,
    ):
        r = client.get("/api/settings/gdrive/callback?code=test_code", follow_redirects=False)
        assert r.status_code == 302
        assert "/?gdrive=success" in r.headers["location"]


def test_gdrive_callback_failure(client):
    """Google Drive callback redirects on failure."""
    with patch(
        "backend.services.google_drive_service.save_token_from_code",
        return_value=False,
    ):
        r = client.get("/api/settings/gdrive/callback?code=invalid_code", follow_redirects=False)
        assert r.status_code == 302
        assert "/?gdrive=error" in r.headers["location"]
