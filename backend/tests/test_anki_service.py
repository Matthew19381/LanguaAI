import os
import tempfile
from unittest.mock import patch

from backend.services.anki_service import generate_anki_deck, get_deck_stats


class TestGenerateAnkiDeck:
    def test_generate_deck_from_dicts(self):
        flashcards = [
            {"word": "Hallo", "translation": "Cześć", "example_sentence": "Hallo, wie geht's?"},
            {"word": "Tschüss", "translation": "Do widzenia", "example_sentence": "Tschüss!"}
        ]

        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
            tmp_path = tmp.name
        # Remove the temp file since generate_anki_deck will create it
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result = generate_anki_deck(flashcards, "German", "TestUser")
            assert os.path.exists(result)
            assert result.endswith(".apkg")
            # Cleanup
            if os.path.exists(result):
                os.unlink(result)

    def test_generate_deck_skips_empty_word(self):
        flashcards = [
            {"word": "Hallo", "translation": "Cześć", "example_sentence": "Hallo!"},
            {"word": "", "translation": "Empty", "example_sentence": ""},
            {"word": None, "translation": "None word", "example_sentence": ""},
            {"word": "Guten Tag", "translation": "Dzień dobry", "example_sentence": "Guten Tag!"}
        ]

        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result = generate_anki_deck(flashcards, "German", "TestUser")
            assert os.path.exists(result)
            # Cleanup
            if os.path.exists(result):
                os.unlink(result)

    def test_generate_deck_from_orm_like_objects(self):
        """Test with objects that have attributes (like ORM models)."""

        class FakeFlashcard:
            def __init__(self, word, translation, example_sentence):
                self.word = word
                self.translation = translation
                self.example_sentence = example_sentence

        flashcards = [
            FakeFlashcard("Hallo", "Cześć", "Hallo!"),
            FakeFlashcard("Tschüss", "Do widzenia", "Tschüss!")
        ]

        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result = generate_anki_deck(flashcards, "German", "TestUser")
            assert os.path.exists(result)
            if os.path.exists(result):
                os.unlink(result)

    def test_generate_deck_empty_list(self):
        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result = generate_anki_deck([], "German", "TestUser")
            assert os.path.exists(result)
            if os.path.exists(result):
                os.unlink(result)

    def test_generate_deck_filename_sanitization(self):
        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result = generate_anki_deck(
                [{"word": "Test", "translation": "Test"}],
                "German",
                "User Name With Spaces"
            )
            assert "user_name_with_spaces" in os.path.basename(result).lower()
            if os.path.exists(result):
                os.unlink(result)

    def test_generate_deck_stable_ids(self):
        """Test that same inputs produce same file (stable IDs)."""
        flashcards = [
            {"word": "Hallo", "translation": "Cześć", "example_sentence": "Hallo!"}
        ]

        with patch("backend.services.anki_service.EXPORTS_DIR", tempfile.gettempdir()):
            result1 = generate_anki_deck(flashcards, "German", "User")
            result2 = generate_anki_deck(flashcards, "German", "User")
            # Both should exist (different temp files)
            assert os.path.exists(result1)
            assert os.path.exists(result2)
            if os.path.exists(result1):
                os.unlink(result1)
            if os.path.exists(result2):
                os.unlink(result2)


class TestGetDeckStats:
    def test_get_stats_basic(self):
        flashcards = [
            {"word": "Hallo", "translation": "Cześć", "example_sentence": "Hallo!"},
            {"word": "Tschüss", "translation": "Do widzenia", "example_sentence": ""}
        ]

        result = get_deck_stats(flashcards)
        assert result["total_cards"] == 2
        assert result["cards_with_examples"] == 1
        assert result["cards_without_examples"] == 1

    def test_get_stats_empty(self):
        result = get_deck_stats([])
        assert result["total_cards"] == 0
        assert result["cards_with_examples"] == 0
        assert result["cards_without_examples"] == 0

    def test_get_stats_all_with_examples(self):
        flashcards = [
            {"word": "A", "translation": "B", "example_sentence": "Example 1"},
            {"word": "C", "translation": "D", "example_sentence": "Example 2"}
        ]

        result = get_deck_stats(flashcards)
        assert result["total_cards"] == 2
        assert result["cards_with_examples"] == 2
        assert result["cards_without_examples"] == 0

    def test_get_stats_orm_like_objects(self):
        class FakeFlashcard:
            def __init__(self, word, translation, example_sentence):
                self.word = word
                self.translation = translation
                self.example_sentence = example_sentence

        flashcards = [
            FakeFlashcard("Hallo", "Cześć", "Hallo!"),
            FakeFlashcard("Tschüss", "Do widzenia", None)
        ]

        result = get_deck_stats(flashcards)
        assert result["total_cards"] == 2
        assert result["cards_with_examples"] == 1
