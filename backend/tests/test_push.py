"""Web Push: subscription lifecycle, VAPID key exposure, send + prune."""
from unittest.mock import patch

from backend.models.push_subscription import PushSubscription
from backend.services import push_service

SUB = {
    "endpoint": "https://push.example.com/abc123",
    "keys": {"p256dh": "BPk_key_material", "auth": "auth_secret"},
}


def _subscribe(client, uid, sub=SUB):
    return client.post("/api/push/subscribe", json={"user_id": uid, "subscription": sub})


# ── VAPID key endpoint ────────────────────────────────────────────────────────

def test_vapid_key_reports_disabled_when_unconfigured(client):
    r = client.get("/api/push/vapid-public-key")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["public_key"] is None


def test_vapid_key_exposed_when_configured(client, monkeypatch):
    monkeypatch.setattr(push_service.settings, "VAPID_PUBLIC_KEY", "PUBKEY")
    monkeypatch.setattr(push_service.settings, "VAPID_PRIVATE_KEY", "PRIVKEY")
    body = client.get("/api/push/vapid-public-key").json()
    assert body["enabled"] is True
    assert body["public_key"] == "PUBKEY"


# ── subscription lifecycle ────────────────────────────────────────────────────

def test_subscribe_stores_subscription(client, db, sample_user):
    uid = sample_user["user_id"]
    r = _subscribe(client, uid)
    assert r.status_code == 200 and r.json()["success"] is True
    rows = db.query(PushSubscription).filter(PushSubscription.user_id == uid).all()
    assert len(rows) == 1
    assert rows[0].endpoint == SUB["endpoint"]


def test_subscribe_upserts_on_same_endpoint(client, db, sample_user):
    uid = sample_user["user_id"]
    _subscribe(client, uid)
    # Same endpoint, refreshed keys → update in place, no duplicate row
    updated = {**SUB, "keys": {"p256dh": "NEW_pub", "auth": "NEW_auth"}}
    _subscribe(client, uid, updated)
    rows = db.query(PushSubscription).filter(PushSubscription.endpoint == SUB["endpoint"]).all()
    assert len(rows) == 1
    assert rows[0].p256dh == "NEW_pub"


def test_subscribe_missing_keys_is_422(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post("/api/push/subscribe",
                    json={"user_id": uid, "subscription": {"endpoint": "x"}})
    assert r.status_code == 422


def test_subscribe_unknown_user_404(client):
    r = _subscribe(client, 999999)
    assert r.status_code == 404


def test_unsubscribe_removes(client, db, sample_user):
    uid = sample_user["user_id"]
    _subscribe(client, uid)
    r = client.post("/api/push/unsubscribe", json={"endpoint": SUB["endpoint"]})
    assert r.json()["removed"] == 1
    assert db.query(PushSubscription).filter(PushSubscription.endpoint == SUB["endpoint"]).count() == 0


# ── test-send endpoint ────────────────────────────────────────────────────────

def test_test_send_503_when_disabled(client, sample_user):
    r = client.post(f"/api/push/test/{sample_user['user_id']}")
    assert r.status_code == 503


def test_test_send_delivers_when_enabled(client, sample_user, monkeypatch):
    uid = sample_user["user_id"]
    _subscribe(client, uid)
    monkeypatch.setattr(push_service.settings, "VAPID_PUBLIC_KEY", "PUB")
    monkeypatch.setattr(push_service.settings, "VAPID_PRIVATE_KEY", "PRIV")
    with patch("pywebpush.webpush") as mock_wp:
        r = client.post(f"/api/push/test/{uid}")
    assert r.status_code == 200
    assert r.json()["sent"] == 1
    mock_wp.assert_called_once()


# ── service: send + prune ─────────────────────────────────────────────────────

def test_send_to_user_disabled_is_noop(db, sample_user):
    # Default test config has no VAPID keys
    result = push_service.send_to_user(db, sample_user["user_id"], "{}")
    assert result == {"sent": 0, "pruned": 0, "enabled": False}


def test_send_prunes_gone_subscription(client, db, sample_user, monkeypatch):
    uid = sample_user["user_id"]
    _subscribe(client, uid)
    monkeypatch.setattr(push_service.settings, "VAPID_PUBLIC_KEY", "PUB")
    monkeypatch.setattr(push_service.settings, "VAPID_PRIVATE_KEY", "PRIV")

    class _Resp:
        status_code = 410

    class _Gone(Exception):
        response = _Resp()

    with patch("pywebpush.webpush", side_effect=_Gone()):
        result = push_service.send_to_user(db, uid, push_service.build_payload("t", "b"))

    assert result["sent"] == 0
    assert result["pruned"] == 1
    # The dead subscription was removed
    assert db.query(PushSubscription).filter(PushSubscription.user_id == uid).count() == 0


def test_send_keeps_subscription_on_transient_error(client, db, sample_user, monkeypatch):
    uid = sample_user["user_id"]
    _subscribe(client, uid)
    monkeypatch.setattr(push_service.settings, "VAPID_PUBLIC_KEY", "PUB")
    monkeypatch.setattr(push_service.settings, "VAPID_PRIVATE_KEY", "PRIV")

    with patch("pywebpush.webpush", side_effect=RuntimeError("network blip")):
        result = push_service.send_to_user(db, uid, "{}")

    assert result["sent"] == 0 and result["pruned"] == 0
    # A transient failure must not drop the subscription
    assert db.query(PushSubscription).filter(PushSubscription.user_id == uid).count() == 1
