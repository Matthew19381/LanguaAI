"""SCI-7 (production effect): read-aloud deck from the newest flashcards."""
from backend.models.flashcard import Flashcard


def _seed_cards(db, user_id, n=5, language="German"):
    for i in range(n):
        db.add(Flashcard(
            user_id=user_id, word=f"Wort{i}", translation=f"słowo{i}",
            language=language, cefr_level="A1", is_active=True,
        ))
    db.commit()


def test_read_aloud_returns_newest_cards(client, sample_user, db):
    uid = sample_user["user_id"]
    _seed_cards(db, uid, n=5)

    r = client.get(f"/api/quickmode/read-aloud/{uid}?count=3")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == uid
    assert data["target_language"] == "German"
    assert len(data["items"]) == 3
    # newest first (Wort4 created last)
    assert data["items"][0]["word"] == "Wort4"
    for item in data["items"]:
        assert "flashcard_id" in item
        assert "translation" in item
    assert "NA GŁOS" in data["instruction"]


def test_read_aloud_count_clamped(client, sample_user, db):
    uid = sample_user["user_id"]
    _seed_cards(db, uid, n=3)
    r = client.get(f"/api/quickmode/read-aloud/{uid}?count=999")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 3


def test_read_aloud_empty_when_no_cards(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/quickmode/read-aloud/{uid}")
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_read_aloud_skips_inactive_and_other_languages(client, sample_user, db):
    uid = sample_user["user_id"]
    db.add(Flashcard(user_id=uid, word="Hallo", translation="cześć",
                     language="German", cefr_level="A1", is_active=False))
    db.add(Flashcard(user_id=uid, word="Hello", translation="cześć",
                     language="English", cefr_level="A1", is_active=True))
    db.commit()

    r = client.get(f"/api/quickmode/read-aloud/{uid}")
    assert r.json()["items"] == []


def test_read_aloud_unknown_user_404(client):
    r = client.get("/api/quickmode/read-aloud/999999")
    assert r.status_code == 404


def test_quickmode_plan_includes_read_aloud_activity(client, sample_user):
    uid = sample_user["user_id"]
    r = client.get(f"/api/quickmode/{uid}")
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["activities"]]
    assert "read-aloud" in ids
    ra = next(a for a in r.json()["activities"] if a["id"] == "read-aloud")
    assert ra["route"] == "/read-aloud"
    assert ra["estimated_minutes"] > 0


# ── SCI-12: desirable difficulty — lapsed cards get a different modality ──

def test_read_aloud_prioritizes_lapsed_cards(client, sample_user, db):
    uid = sample_user["user_id"]
    _seed_cards(db, uid, n=3)  # Wort0, Wort1, Wort2 — all "Learning" by default
    lapsed = Flashcard(
        user_id=uid, word="Verloren", translation="stracone",
        language="German", cefr_level="A1", is_active=True, fsrs_state="Relearning",
    )
    db.add(lapsed)
    db.commit()

    r = client.get(f"/api/quickmode/read-aloud/{uid}?count=2")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    # The lapsed card comes first and is flagged; the newest non-lapsed card fills the rest.
    assert items[0]["word"] == "Verloren"
    assert items[0]["lapsed"] is True
    assert items[1]["word"] == "Wort2"
    assert items[1]["lapsed"] is False


def test_read_aloud_lapsed_cards_not_duplicated_in_recent_fill(client, sample_user, db):
    uid = sample_user["user_id"]
    lapsed = Flashcard(
        user_id=uid, word="Verloren", translation="stracone",
        language="German", cefr_level="A1", is_active=True, fsrs_state="Relearning",
    )
    db.add(lapsed)
    db.commit()

    r = client.get(f"/api/quickmode/read-aloud/{uid}?count=5")
    words = [item["word"] for item in r.json()["items"]]
    assert words.count("Verloren") == 1


def test_read_aloud_no_lapsed_cards_behaves_as_before(client, sample_user, db):
    uid = sample_user["user_id"]
    _seed_cards(db, uid, n=3)
    r = client.get(f"/api/quickmode/read-aloud/{uid}?count=3")
    items = r.json()["items"]
    assert all(item["lapsed"] is False for item in items)
    assert items[0]["word"] == "Wort2"


def test_quickmode_plan_boosts_read_aloud_priority_with_lapsed_cards(client, sample_user, db):
    uid = sample_user["user_id"]
    db.add(Flashcard(
        user_id=uid, word="Verloren", translation="stracone",
        language="German", cefr_level="A1", is_active=True, fsrs_state="Relearning",
    ))
    db.commit()

    r = client.get(f"/api/quickmode/{uid}")
    ra = next(a for a in r.json()["activities"] if a["id"] == "read-aloud")
    assert ra["priority"] == 2
    assert "trudności" in ra["description"]
