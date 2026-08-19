"""Tests for /api/topics/* endpoints."""
from backend.models.topic import Topic


def _create_topic(db, user_id, name="Gramatyka", category="grammar",
                  language="German", cefr_level="A1"):
    """Helper to create a topic directly in the DB."""
    topic = Topic(
        user_id=user_id,
        name=name,
        category=category,
        description=f"Test topic: {name}",
        language=language,
        cefr_level=cefr_level,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


# ── GET /api/topics/{user_id} ───────────────────────────────────────────────

def test_list_topics_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["topics"] == []
    assert data["count"] == 0


def test_list_topics_returns_created(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Perfekt", "grammar")
    _create_topic(db, uid, "Wokabular", "vocabulary")

    r = client.get(f"/api/topics/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    names = [t["name"] for t in data["topics"]]
    assert "Perfekt" in names
    assert "Wokabular" in names


def test_list_topics_filter_by_language(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Perfekt", "grammar", language="German")
    _create_topic(db, uid, "Present Simple", "grammar", language="English")

    r = client.get(f"/api/topics/{uid}?language=German")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["topics"][0]["name"] == "Perfekt"


def test_list_topics_filter_by_category(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Perfekt", "grammar")
    _create_topic(db, uid, "Wokabular", "vocabulary")

    r = client.get(f"/api/topics/{uid}?category=grammar")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["topics"][0]["category"] == "grammar"


def test_list_topics_sorted_by_name(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Zebra", "other")
    _create_topic(db, uid, "Apfel", "other")
    _create_topic(db, uid, "Mitte", "other")

    r = client.get(f"/api/topics/{uid}?sort=name")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["topics"]]
    assert names == ["Apfel", "Mitte", "Zebra"]


# ── GET /api/topics/{user_id}/tree ──────────────────────────────────────────

def test_topic_tree_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/{uid}/tree")
    assert r.status_code == 200
    assert "tree" in r.json()


def test_topic_tree_grouped(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Perfekt", "grammar")
    _create_topic(db, uid, "Wokabular", "vocabulary")

    r = client.get(f"/api/topics/{uid}/tree")
    assert r.status_code == 200
    tree = r.json()["tree"]
    assert "grammar" in tree
    assert "vocabulary" in tree


# ── GET /api/topics/{user_id}/hierarchy (P2-4) ──────────────────────────────

def test_topic_hierarchy_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/{uid}/hierarchy")
    assert r.status_code == 200
    assert r.json()["topics"] == []


def test_topic_hierarchy_flat_topics_are_roots(client, sample_user, db):
    uid = sample_user["user_id"]
    _create_topic(db, uid, "Perfekt", "grammar")
    _create_topic(db, uid, "Wokabular", "vocabulary")

    r = client.get(f"/api/topics/{uid}/hierarchy")
    assert r.status_code == 200
    nodes = r.json()["topics"]
    assert len(nodes) == 2
    assert all(n["subtopics"] == [] for n in nodes)


def test_topic_hierarchy_nests_children_under_parent(client, sample_user, db):
    uid = sample_user["user_id"]
    parent = _create_topic(db, uid, "Czasy przeszłe", "grammar")
    child = _create_topic(db, uid, "Perfekt mit haben", "grammar")
    child.parent_id = parent.id
    db.commit()

    r = client.get(f"/api/topics/{uid}/hierarchy")
    assert r.status_code == 200
    nodes = r.json()["topics"]
    assert len(nodes) == 1  # only the parent is a root
    assert nodes[0]["name"] == "Czasy przeszłe"
    assert len(nodes[0]["subtopics"]) == 1
    assert nodes[0]["subtopics"][0]["name"] == "Perfekt mit haben"


def test_topic_hierarchy_group_mastery_averages_subtopics(client, sample_user, db):
    uid = sample_user["user_id"]
    parent = _create_topic(db, uid, "Czasy przeszłe", "grammar")
    c1 = _create_topic(db, uid, "Perfekt", "grammar")
    c2 = _create_topic(db, uid, "Präteritum", "grammar")
    c1.parent_id = parent.id
    c2.parent_id = parent.id
    c1.memory_strength = 0.8   # 80%
    c2.memory_strength = 0.4   # 40%
    db.commit()

    r = client.get(f"/api/topics/{uid}/hierarchy")
    nodes = r.json()["topics"]
    assert nodes[0]["group_mastery_percent"] == 60  # avg(80, 40), parent itself has 0 items


def test_topic_hierarchy_orphaned_parent_id_falls_back_to_root(client, sample_user, db):
    """A parent_id pointing at a non-existent/other-user topic must not crash —
    the node just becomes a root instead."""
    uid = sample_user["user_id"]
    t = _create_topic(db, uid, "Perfekt", "grammar")
    t.parent_id = 999999
    db.commit()

    r = client.get(f"/api/topics/{uid}/hierarchy")
    assert r.status_code == 200
    nodes = r.json()["topics"]
    assert len(nodes) == 1
    assert nodes[0]["name"] == "Perfekt"


# ── GET /api/topics/{user_id}/due ───────────────────────────────────────────

def test_due_topics_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/{uid}/due")
    assert r.status_code == 200
    data = r.json()
    assert "topics" in data
    assert "count" in data


# ── GET /api/topics/{user_id}/stats ─────────────────────────────────────────

def test_topic_stats_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/{uid}/stats")
    assert r.status_code == 200


# ── GET /api/topics/detail/{topic_id} ───────────────────────────────────────

def test_topic_detail(client, sample_user, db):
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    r = client.get(f"/api/topics/detail/{topic.id}?user_id={uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["topic"]["name"] == "Perfekt"
    assert data["topic"]["category"] == "grammar"
    assert "items" in data


def test_topic_detail_not_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/topics/detail/99999?user_id={uid}")
    assert r.status_code == 404


def test_topic_detail_wrong_user(client, sample_user, db):
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    r = client.get(f"/api/topics/detail/{topic.id}?user_id={uid + 1}")
    assert r.status_code == 403


# ── POST /api/topics/{topic_id}/review ──────────────────────────────────────

def test_review_topic(client, sample_user, db):
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    r = client.post(f"/api/topics/{topic.id}/review", json={"rating": 3, "user_id": uid})
    assert r.status_code == 200
    data = r.json()
    assert data["topic_id"] == topic.id
    assert "interval" in data
    assert "repetitions" in data
    assert "next_review" in data


def test_review_topic_invalid_rating(client, sample_user, db):
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    r = client.post(f"/api/topics/{topic.id}/review", json={"rating": 5, "user_id": uid})
    assert r.status_code == 400

    r = client.post(f"/api/topics/{topic.id}/review", json={"rating": 0, "user_id": uid})
    assert r.status_code == 400


def test_review_topic_not_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post("/api/topics/99999/review", json={"rating": 3, "user_id": uid})
    assert r.status_code == 404


def test_review_topic_wrong_user(client, sample_user, db):
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    r = client.post(f"/api/topics/{topic.id}/review", json={"rating": 3, "user_id": uid + 1})
    assert r.status_code == 403


def test_review_topic_rating_again_resets(client, sample_user, db):
    """Rating 1 (Again) should reset interval to 1 day."""
    uid = sample_user["user_id"]
    topic = _create_topic(db, uid, "Perfekt", "grammar")

    # First review: Good
    r1 = client.post(f"/api/topics/{topic.id}/review", json={"rating": 3, "user_id": uid})
    assert r1.status_code == 200

    # Second review: Again (forgot)
    r2 = client.post(f"/api/topics/{topic.id}/review", json={"rating": 1, "user_id": uid})
    assert r2.status_code == 200
    assert r2.json()["interval"] == 1  # Again resets to 1
