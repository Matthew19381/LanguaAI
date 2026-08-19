"""P2-4 (docs/BACKLOG_UX_2026-08.md): unit tests for the topic-hierarchy
helpers in topic_service.py — resolving/creating a parent topic and not
letting it flip-flop across lessons.
"""
from backend.services.topic_service import get_or_create_topic, get_or_create_topic_with_parent


def test_creates_parent_and_links_child(db, sample_user):
    uid = sample_user["user_id"]
    topic = get_or_create_topic_with_parent(
        db, uid, "German", "Perfekt mit haben", category="grammar",
        parent_topic_name="Czasy przeszłe",
    )
    db.commit()
    assert topic.parent_id is not None
    parent = get_or_create_topic(db, uid, "German", "Czasy przeszłe")
    assert topic.parent_id == parent.id


def test_no_parent_topic_name_leaves_parent_id_null(db, sample_user):
    uid = sample_user["user_id"]
    topic = get_or_create_topic_with_parent(db, uid, "German", "Begrüßungen", category="vocabulary")
    db.commit()
    assert topic.parent_id is None


def test_self_referential_parent_name_ignored(db, sample_user):
    uid = sample_user["user_id"]
    topic = get_or_create_topic_with_parent(
        db, uid, "German", "Perfekt", category="grammar",
        parent_topic_name="perfekt",  # same name, different case
    )
    db.commit()
    assert topic.parent_id is None


def test_existing_parent_id_not_overwritten_by_a_later_lesson(db, sample_user):
    uid = sample_user["user_id"]
    topic = get_or_create_topic_with_parent(
        db, uid, "German", "Perfekt mit haben", category="grammar",
        parent_topic_name="Czasy przeszłe",
    )
    db.commit()
    first_parent_id = topic.parent_id

    # A later lesson proposes a DIFFERENT parent for the same topic name.
    topic_again = get_or_create_topic_with_parent(
        db, uid, "German", "Perfekt mit haben", category="grammar",
        parent_topic_name="Zupełnie inny temat",
    )
    db.commit()
    assert topic_again.id == topic.id
    assert topic_again.parent_id == first_parent_id
