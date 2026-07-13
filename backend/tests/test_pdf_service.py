import os
import tempfile
from unittest.mock import patch

from backend.services.pdf_service import _safe, generate_lesson_pdf


class TestSafeFunction:
    def test_safe_ascii_text(self):
        result = _safe("Hello World")
        assert result == "Hello World"

    def test_safe_polish_chars(self):
        result = _safe("Zaólć gêsia jaŸñ")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_safe_german_chars(self):
        result = _safe("Schrödinger's Katze")
        assert len(result) > 0

    def test_safe_non_string(self):
        result = _safe(123)
        assert result == "123"

    def test_safe_special_chars(self):
        result = _safe("Line1\nLine2\tTab")
        assert "Line1" in result

    def test_safe_none(self):
        result = _safe(None)
        assert result == "None"


class TestGenerateLessonPdf:
    def test_generate_basic_lesson_pdf(self):
        # Minimal lesson - only title to avoid rendering issues
        lesson = {
            "content": {
                "title": "Simple Lesson",
                "explanation": "Learn basics."
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = generate_lesson_pdf(lesson, tmp_path)
            assert os.path.exists(tmp_path)
            assert result == tmp_path
            assert os.path.getsize(tmp_path) > 0
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_generate_lesson_with_comprehensible_input(self):
        lesson = {
            "title": "Reading Practice",
            "content": {
                "title": "Reading Practice",
                "comprehensible_input": {
                    "text": "I learn English. This is interesting.",
                    "new_words": ["learn", "interesting"]
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = generate_lesson_pdf(lesson, tmp_path)
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_generate_lesson_minimal(self):
        """Test with minimal lesson data."""
        lesson = {
            "content": {
                "title": "Minimal Lesson"
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = generate_lesson_pdf(lesson, tmp_path)
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_generate_lesson_creates_exports_dir(self):
        """Test that exports directory is created if it doesn't exist."""
        lesson = {"content": {"title": "Test"}}

        with patch("os.makedirs") as mock_makedirs:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                generate_lesson_pdf(lesson, tmp_path)
                mock_makedirs.assert_called()
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def test_generate_lesson_with_empty_vocabulary(self):
        lesson = {
            "content": {
                "title": "Empty Vocab",
                "vocabulary": []
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = generate_lesson_pdf(lesson, tmp_path)
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_generate_lesson_without_dialogue_translation(self):
        lesson = {
            "content": {
                "title": "No Translation",
                "dialogue": {
                    "lines": [
                        {"speaker": "A", "text": "Just text, no translation"}
                    ]
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = generate_lesson_pdf(lesson, tmp_path)
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
