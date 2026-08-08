"""SCI-13: keyword-method mnemonic for abstract vocabulary (Atkinson 1975)."""
from backend.models.flashcard import Flashcard
from backend.services.flashcard_service import create_flashcards_from_vocab
from backend.services.lesson_generator.daily_lesson import _sanitize_vocabulary_mnemonics


def test_sanitize_trims_whitespace():
    vocab = [{"word": "Angst", "mnemonic": "  a jolt of dread  "}]
    out = _sanitize_vocabulary_mnemonics(vocab)
    assert out[0]["mnemonic"] == "a jolt of dread"


def test_sanitize_missing_mnemonic_becomes_empty_string():
    vocab = [{"word": "Tisch"}]
    out = _sanitize_vocabulary_mnemonics(vocab)
    assert out[0]["mnemonic"] == ""


def test_sanitize_whitespace_only_becomes_empty_string():
    vocab = [{"word": "Tisch", "mnemonic": "   "}]
    out = _sanitize_vocabulary_mnemonics(vocab)
    assert out[0]["mnemonic"] == ""


def test_sanitize_non_list_returns_empty_list():
    assert _sanitize_vocabulary_mnemonics(None) == []
    assert _sanitize_vocabulary_mnemonics("not a list") == []


def test_sanitize_skips_non_dict_items_without_crashing():
    vocab = [{"word": "Tisch", "mnemonic": " x "}, "garbage", None]
    out = _sanitize_vocabulary_mnemonics(vocab)
    assert out[0]["mnemonic"] == "x"
    assert out[1] == "garbage"
    assert out[2] is None


def test_mnemonic_persisted_when_present(db, sample_user):
    uid = sample_user["user_id"]
    vocab = [{
        "word": "Sehnsucht", "translation": "longing", "category": "emotions",
        "mnemonic": "Sounds like 'zen zukt' — picture a zen monk yearning quietly.",
    }]
    create_flashcards_from_vocab(db, vocab, uid, "German", "B1", 1, 1, "Feelings")
    db.commit()

    card = db.query(Flashcard).filter(Flashcard.user_id == uid, Flashcard.word == "Sehnsucht").first()
    assert card.mnemonic == "Sounds like 'zen zukt' — picture a zen monk yearning quietly."


def test_mnemonic_none_when_absent(db, sample_user):
    uid = sample_user["user_id"]
    vocab = [{"word": "Tisch", "translation": "table", "category": "furniture"}]
    create_flashcards_from_vocab(db, vocab, uid, "German", "A1", 1, 1, "Home")
    db.commit()

    card = db.query(Flashcard).filter(Flashcard.user_id == uid, Flashcard.word == "Tisch").first()
    assert card.mnemonic is None


def test_mnemonic_blank_string_stored_as_none(db, sample_user):
    uid = sample_user["user_id"]
    vocab = [{"word": "Stuhl", "translation": "chair", "category": "furniture", "mnemonic": ""}]
    create_flashcards_from_vocab(db, vocab, uid, "German", "A1", 1, 1, "Home")
    db.commit()

    card = db.query(Flashcard).filter(Flashcard.user_id == uid, Flashcard.word == "Stuhl").first()
    assert card.mnemonic is None


def test_get_due_flashcards_includes_mnemonic_gender_important(client, db, sample_user):
    uid = sample_user["user_id"]
    db.add(Flashcard(
        user_id=uid, word="Angst", translation="fear", language="German", cefr_level="B1",
        gender=None, isImportant=True, mnemonic="Like 'angst' in English — a jolt of dread.",
    ))
    db.commit()

    r = client.get(f"/api/flashcards/{uid}/due")
    assert r.status_code == 200
    card = r.json()["due_cards"][0]
    assert card["mnemonic"] == "Like 'angst' in English — a jolt of dread."
    assert card["isImportant"] is True
    assert "gender" in card


def test_get_flashcards_includes_mnemonic(client, db, sample_user):
    uid = sample_user["user_id"]
    db.add(Flashcard(
        user_id=uid, word="Tisch", translation="table", language="German",
        cefr_level="A1", mnemonic=None,
    ))
    db.commit()

    r = client.get(f"/api/flashcards/{uid}")
    assert r.status_code == 200
    card = r.json()["flashcards"][0]
    assert "mnemonic" in card
    assert card["mnemonic"] is None
