"""/api/v1 alias: every /api/* endpoint is also reachable under /api/v1/*,
while the routers already native to /api/v1 (users, voice-chat) keep working."""


def test_v1_health_alias(client):
    """/api/v1/health rewrites to /api/health."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_v1_matches_plain_api(client, sample_user):
    """/api/v1/stats/{id} returns the same payload as /api/stats/{id}."""
    uid = sample_user["user_id"]
    plain = client.get(f"/api/stats/{uid}")
    v1 = client.get(f"/api/v1/stats/{uid}")
    assert plain.status_code == 200 and v1.status_code == 200
    assert v1.json()["user"]["id"] == plain.json()["user"]["id"]


def test_v1_alias_on_prefixed_router(client, sample_user):
    """Routers mounted with their own prefix (topics -> /api/topics) alias too."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/v1/topics/{uid}/stats")
    assert r.status_code == 200


def test_plain_api_still_works(client, sample_user):
    """The historical /api/* path is untouched."""
    uid = sample_user["user_id"]
    assert client.get(f"/api/lessons/list/{uid}").status_code == 200


def test_native_v1_router_not_broken(client, sample_user):
    """users is natively mounted at /api/v1/users — the rewrite must skip it,
    otherwise /api/v1/users/{id}/sleep would 404 as /api/users/{id}/sleep."""
    uid = sample_user["user_id"]
    r = client.get(f"/api/v1/users/{uid}/sleep")
    assert r.status_code == 200  # not a 404 from an errant rewrite
