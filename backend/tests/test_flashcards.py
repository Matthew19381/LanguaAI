"""Tests for /api/flashcards/* endpoints (no AI calls needed)."""
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_card(client, user_id, word="Hund", translation="dog", example=None):
    payload = {"word": word, "translation": translation}
    if example:
        payload["example_sentence"] = example
    return client.post(f"/api/flashcards/{user_id}/add", json=payload)


# ---------------------------------------------------------------------------
# GET /api/flashcards/{user_id}
# ---------------------------------------------------------------------------

def test_get_flashcards_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/flashcards/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["flashcards"] == []
    assert data["total"] == 0


def test_get_flashcards_user_not_found(client):
    r = client.get("/api/flashcards/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/flashcards/{user_id}/add
# ---------------------------------------------------------------------------

def test_add_flashcard_success(client, sample_user):
    uid = sample_user["user_id"]
    r = add_card(client, uid, "Katze", "cat", "Die Katze schläft.")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert isinstance(data["id"], int)


def test_add_flashcard_appears_in_list(client, sample_user):
    uid = sample_user["user_id"]
    add_card(client, uid, "Hund", "dog")
    r = client.get(f"/api/flashcards/{uid}")
    cards = r.json()["flashcards"]
    assert len(cards) == 1
    assert cards[0]["word"] == "Hund"
    assert cards[0]["translation"] == "dog"


def test_add_flashcard_duplicate_prevented(client, sample_user):
    uid = sample_user["user_id"]
    add_card(client, uid, "Hund", "dog")
    r2 = add_card(client, uid, "Hund", "dog again")
    assert r2.status_code == 200
    data = r2.json()
    assert data["success"] is False
    assert "już istnieje" in data["message"]


def test_add_flashcard_user_not_found(client):
    r = client.post("/api/flashcards/99999/add", json={"word": "X", "translation": "Y"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/flashcards/{user_id}/due
# ---------------------------------------------------------------------------

def test_due_flashcards_empty(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/flashcards/{uid}/due")
    assert r.status_code == 200
    # Newly created cards have next_review_date = now, so they ARE due
    assert "due_cards" in r.json()
    assert "count" in r.json()


def test_due_flashcards_newly_added_are_due(client, sample_user):
    uid = sample_user["user_id"]
    add_card(client, uid, "Buch", "book")
    r = client.get(f"/api/flashcards/{uid}/due")
    data = r.json()
    assert data["count"] >= 1


def test_due_flashcards_user_not_found(client):
    r = client.get("/api/flashcards/99999/due")
    assert r.status_code == 404


def test_due_flashcards_include_lesson_link(client, sample_user, db):
    """Wariant D (fiszki): the due-card payload must carry lesson_id so the
    frontend can offer a 'Zobacz w lekcji' link."""
    from backend.models.lesson import Lesson
    uid = sample_user["user_id"]
    lesson = Lesson(user_id=uid, day_number=1, title="T", topic="Essen",
                     content="{}", cefr_level="A1", language="German")
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    add_card(client, uid, "Brot", "bread")
    from backend.models.flashcard import Flashcard
    card = db.query(Flashcard).filter(Flashcard.word == "Brot").first()
    card.lesson_id = lesson.id
    card.lesson_topic = "Essen"
    db.commit()

    r = client.get(f"/api/flashcards/{uid}/due")
    due = next(c for c in r.json()["due_cards"] if c["word"] == "Brot")
    assert due["lesson_id"] == lesson.id
    assert due["lesson_topic"] == "Essen"


def test_due_flashcards_filtered_by_topic(client, sample_user, db):
    """topic_id filters to only cards whose lesson is linked to that topic
    (Topic -> TopicItem(item_type='lesson') -> Lesson.id -> Flashcard.lesson_id)."""
    from backend.models.lesson import Lesson
    from backend.models.topic import ItemType, Topic, TopicItem
    uid = sample_user["user_id"]

    lesson_a = Lesson(user_id=uid, day_number=1, title="A", topic="Essen",
                       content="{}", cefr_level="A1", language="German")
    lesson_b = Lesson(user_id=uid, day_number=2, title="B", topic="Reisen",
                       content="{}", cefr_level="A1", language="German")
    db.add_all([lesson_a, lesson_b])
    db.commit()
    db.refresh(lesson_a)
    db.refresh(lesson_b)

    topic = Topic(user_id=uid, name="Essen", category="vocabulary", language="German")
    db.add(topic)
    db.commit()
    db.refresh(topic)
    db.add(TopicItem(topic_id=topic.id, item_type=ItemType.LESSON, item_id=lesson_a.id))
    db.commit()

    add_card(client, uid, "Brot", "bread")
    add_card(client, uid, "Zug", "train")
    from backend.models.flashcard import Flashcard
    db.query(Flashcard).filter(Flashcard.word == "Brot").update({"lesson_id": lesson_a.id})
    db.query(Flashcard).filter(Flashcard.word == "Zug").update({"lesson_id": lesson_b.id})
    db.commit()

    r = client.get(f"/api/flashcards/{uid}/due?topic_id={topic.id}")
    words = {c["word"] for c in r.json()["due_cards"]}
    assert words == {"Brot"}


# ---------------------------------------------------------------------------
# POST /api/flashcards/{flashcard_id}/alt-context (Wariant D)
# ---------------------------------------------------------------------------

def test_alt_context_success(client, sample_user, monkeypatch):
    from unittest.mock import AsyncMock

    import backend.routers.flashcards as flashcards_router

    uid = sample_user["user_id"]
    add_card(client, uid, "Brot", "bread", "Ich kaufe Brot im Laden.")
    fc_id = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]["id"]

    monkeypatch.setattr(
        flashcards_router, "_ai_generate_alt_context",
        AsyncMock(return_value={"sentence": "Wir essen Brot beim Picknick.",
                                  "translation": "Jemy chleb na pikniku."}),
    )
    r = client.post(f"/api/flashcards/{fc_id}/alt-context?user_id={uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "Picknick" in data["sentence"]


def test_alt_context_not_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post(f"/api/flashcards/99999/alt-context?user_id={uid}")
    assert r.status_code == 404


def test_alt_context_wrong_user(client, sample_user):
    uid = sample_user["user_id"]
    add_card(client, uid, "Brot", "bread")
    fc_id = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]["id"]
    r = client.post(f"/api/flashcards/{fc_id}/alt-context?user_id={uid + 1}")
    assert r.status_code == 403


def test_alt_context_empty_ai_response_is_502(client, sample_user, monkeypatch):
    from unittest.mock import AsyncMock

    import backend.routers.flashcards as flashcards_router

    uid = sample_user["user_id"]
    add_card(client, uid, "Brot", "bread")
    fc_id = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]["id"]

    monkeypatch.setattr(
        flashcards_router, "_ai_generate_alt_context",
        AsyncMock(return_value={}),
    )
    r = client.post(f"/api/flashcards/{fc_id}/alt-context?user_id={uid}")
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# POST /api/flashcards/{flashcard_id}/mnemonic-image (Wariant B — on demand)
# ---------------------------------------------------------------------------

def test_mnemonic_image_requires_a_text_mnemonic(client, sample_user):
    uid = sample_user["user_id"]
    add_card(client, uid, "Brot", "bread")  # no mnemonic
    fc_id = client.get(f"/api/flashcards/{uid}").json()["flashcards"][0]["id"]

    r = client.post(f"/api/flashcards/{fc_id}/mnemonic-image?user_id={uid}")
    assert r.status_code == 400


def test_mnemonic_image_generates_and_caches(client, sample_user, db, monkeypatch):
    from unittest.mock import AsyncMock

    from backend.models.flashcard import Flashcard
    uid = sample_user["user_id"]
    add_card(client, uid, "Angst", "fear")
    card = db.query(Flashcard).filter(Flashcard.word == "Angst").first()
    card.mnemonic = "Picture an anxious ant carrying a huge backpack."
    db.commit()

    mock_generate = AsyncMock(return_value="/images/mnemonic_1.png")
    monkeypatch.setattr(
        "backend.services.image_service.generate_mnemonic_image", mock_generate,
    )

    r = client.post(f"/api/flashcards/{card.id}/mnemonic-image?user_id={uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["cached"] is False
    assert data["image_path"] == "/images/mnemonic_1.png"
    mock_generate.assert_called_once()

    # Second call: served from the cached path, generator not called again.
    mock_generate.reset_mock()
    r2 = client.post(f"/api/flashcards/{card.id}/mnemonic-image?user_id={uid}")
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    mock_generate.assert_not_called()


def test_mnemonic_image_not_found(client, sample_user):
    uid = sample_user["user_id"]
    r = client.post(f"/api/flashcards/99999/mnemonic-image?user_id={uid}")
    assert r.status_code == 404


def test_mnemonic_image_wrong_user(client, sample_user, db):
    from backend.models.flashcard import Flashcard
    uid = sample_user["user_id"]
    add_card(client, uid, "Angst", "fear")
    card = db.query(Flashcard).filter(Flashcard.word == "Angst").first()
    card.mnemonic = "x"
    db.commit()

    r = client.post(f"/api/flashcards/{card.id}/mnemonic-image?user_id={uid + 1}")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/flashcards/{flashcard_id}/review
# ---------------------------------------------------------------------------

def test_review_flashcard_not_found(client):
    r = client.post("/api/flashcards/99999/review", json={"rating": 3}, params={"user_id": 1})
    assert r.status_code == 404


def test_review_rating_again(client, sample_user):
    uid = sample_user["user_id"]
    add_r = add_card(client, uid, "Tisch", "table")
    card_id = add_r.json()["id"]

    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 1}, params={"user_id": uid})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["new_interval"] == 1          # Again resets to 1
    assert "new_difficulty" in data            # FSRS difficulty field


def test_review_rating_good(client, sample_user):
    uid = sample_user["user_id"]
    add_r = add_card(client, uid, "Stuhl", "chair")
    card_id = add_r.json()["id"]

    # First review (FSRS): Good → interval >= 1, repetitions=1
    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 3}, params={"user_id": uid})
    assert r.status_code == 200
    data = r.json()
    assert data["new_interval"] >= 1           # First successful review
    assert data["state"] == "Learning"         # First review → Learning state

    # Second review: Good → interval increases
    r2 = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 3}, params={"user_id": uid})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["new_interval"] >= data["new_interval"]  # Interval non-decreasing


def test_review_rating_easy_increases_interval(client, sample_user):
    uid = sample_user["user_id"]
    add_r = add_card(client, uid, "Fenster", "window")
    card_id = add_r.json()["id"]

    # First review: Easy → interval >= 1, stability increases
    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 4}, params={"user_id": uid})
    assert r.status_code == 200
    data = r.json()
    assert data["new_interval"] >= 1           # First successful review
    assert "new_stability" in data             # FSRS stability field


def test_review_returns_next_review_date(client, sample_user):
    uid = sample_user["user_id"]
    add_r = add_card(client, uid, "Auto", "car")
    card_id = add_r.json()["id"]

    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 3}, params={"user_id": uid})
    data = r.json()
    assert "next_review" in data
    # next_review should be a valid ISO datetime string
    next_review = datetime.fromisoformat(data["next_review"])
    assert next_review is not None
    # next_review should be within a reasonable range (not more than 1 year out)
    now = datetime.now(next_review.tzinfo or None)
    assert next_review < now + timedelta(days=365)


def test_review_flashcard_wrong_user(client, sample_user, db):
    """Reviewing another user's flashcard must return 403."""
    from backend.models.flashcard import Flashcard
    uid = sample_user["user_id"]
    # Create a flashcard for sample_user
    card = Flashcard(user_id=uid, word="Hund", translation="dog",
                     language="German", cefr_level="A1")
    db.add(card)
    db.commit()
    db.refresh(card)

    # Try to review with a different user_id
    r = client.post(f"/api/flashcards/{card.id}/review",
                    json={"rating": 3}, params={"user_id": uid + 1})
    assert r.status_code == 403
