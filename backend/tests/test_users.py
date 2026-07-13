"""Tests for /api/v1/users/* neuro-FSRS endpoints (NEURO-11/14/15/16)."""


def _post_sleep(client, uid, quality=4, date=None):
    payload = {"quality": quality}
    if date:
        payload["date"] = date
    return client.post(f"/api/v1/users/{uid}/sleep", json=payload)


def test_set_sleep_data(client, sample_user):
    uid = sample_user["user_id"]
    r = _post_sleep(client, uid, quality=4)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True

    # It should be retrievable
    g = client.get(f"/api/v1/users/{uid}/sleep")
    assert g.status_code == 200
    sd = g.json()["sleep_data"]
    assert sd["last_sleep_quality"] == 4
    assert len(sd["history"]) == 1


def test_sleep_quality_out_of_range(client, sample_user):
    uid = sample_user["user_id"]
    r = _post_sleep(client, uid, quality=9)
    assert r.status_code == 400


def test_sleep_tracker_achievement_awarded_after_3_logs(client, sample_user):
    uid = sample_user["user_id"]
    for i in range(3):
        r = _post_sleep(client, uid, quality=3, date=f"2026-07-1{i}")
        assert r.status_code == 200
    # Third log triggers the achievement
    last = r.json()
    assert last["new_achievement"] is not None
    assert last["new_achievement"]["type"] == "sleep_tracker"


def test_sleep_user_not_found(client):
    r = _post_sleep(client, 99999, quality=3)
    assert r.status_code == 404
    g = client.get("/api/v1/users/99999/sleep")
    assert g.status_code == 404


# ── NEURO-15: configurable weights ──────────────────────────────────────────

def test_get_default_neuro_weights(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/v1/users/{uid}/neuro-weights")
    assert r.status_code == 200
    w = r.json()["neuro_weights"]
    assert w["sleep_modulator_weight"] == 0.15
    assert w["interleaving_bonus_weight"] == 0.05


def test_update_neuro_weights(client, sample_user):
    uid = sample_user["user_id"]
    r = client.patch(
        f"/api/v1/users/{uid}/neuro-weights",
        json={"sleep_modulator_weight": 0.25, "time_of_day_weight": 0.15},
    )
    assert r.status_code == 200
    w = r.json()["neuro_weights"]
    assert w["sleep_modulator_weight"] == 0.25
    assert w["time_of_day_weight"] == 0.15
    # Untouched field keeps its default
    assert w["interleaving_bonus_weight"] == 0.05
    # Achievement awarded
    assert r.json()["new_achievement"]["type"] == "neuro_tuned"


def test_update_neuro_weights_out_of_bounds(client, sample_user):
    uid = sample_user["user_id"]
    r = client.patch(
        f"/api/v1/users/{uid}/neuro-weights",
        json={"sleep_modulator_weight": 0.99},  # max is 0.3
    )
    assert r.status_code == 400


def test_update_neuro_weights_ignores_unknown_field(client, sample_user):
    uid = sample_user["user_id"]
    # Unknown weight keys are ignored (only the 4 known keys are validated)
    r = client.patch(
        f"/api/v1/users/{uid}/neuro-weights",
        json={"sleep_modulator_weight": 0.2, "nonsense": 0.1},
    )
    assert r.status_code == 200
    assert r.json()["neuro_weights"]["sleep_modulator_weight"] == 0.2


# ── NEURO-16: sleep-sensor sync ─────────────────────────────────────────────

def test_sync_sleep_from_sensor_score(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post(
        f"/api/v1/users/{uid}/sync-sleep",
        json={"source": "google_fit", "sleep_score": 80},  # 80/20 -> 4
    )
    assert r.status_code == 200
    data = r.json()
    assert data["quality"] == 4
    assert data["success"] is True

    g = client.get(f"/api/v1/users/{uid}/sleep")
    sd = g.json()["sleep_data"]
    assert sd["last_sleep_quality"] == 4
    assert "google_fit" in sd.get("sources", [])


def test_sync_sleep_requires_quality_or_score(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post(
        f"/api/v1/users/{uid}/sync-sleep",
        json={"source": "apple_health"},
    )
    assert r.status_code == 400
