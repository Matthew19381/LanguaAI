from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.test_generator import (
    calculate_score,
    get_test_history,
    submit_test,
)


class TestCalculateScore:
    def test_perfect_score(self):
        questions = [
            {"id": 1, "correct": "A", "points": 10},
            {"id": 2, "correct": "B", "points": 10},
            {"id": 3, "correct": "C", "points": 10},
        ]
        answers = {"1": "A", "2": "B", "3": "C"}
        score = calculate_score(questions, answers)
        assert score == 100.0

    def test_half_score(self):
        questions = [
            {"id": 1, "correct": "A", "points": 10},
            {"id": 2, "correct": "B", "points": 10},
            {"id": 3, "correct": "C", "points": 10},
        ]
        answers = {"1": "A", "2": "X", "3": "X"}
        score = calculate_score(questions, answers)
        assert score == pytest.approx(33.33, abs=1)

    def test_zero_score(self):
        questions = [
            {"id": 1, "correct": "A", "points": 10},
            {"id": 2, "correct": "B", "points": 10},
        ]
        answers = {"1": "X", "2": "Y"}
        score = calculate_score(questions, answers)
        assert score == 0.0

    def test_empty_questions(self):
        score = calculate_score([], {})
        assert score == 0.0

    def test_string_numeric_ids(self):
        questions = [
            {"id": 1, "correct": "A", "points": 10},
            {"id": 2, "correct": "B", "points": 10},
        ]
        answers = {"1": "A", "2": "B"}
        score = calculate_score(questions, answers)
        assert score == 100.0

    def test_default_points(self):
        questions = [
            {"id": 1, "correct": "A"},
            {"id": 2, "correct": "B"},
        ]
        answers = {"1": "A", "2": "B"}
        score = calculate_score(questions, answers)
        assert score == 100.0

    def test_case_insensitive_answers(self):
        questions = [
            {"id": 1, "correct": "a", "points": 10},
            {"id": 2, "correct": "B", "points": 10},
        ]
        answers = {"1": "A", "2": "b"}
        score = calculate_score(questions, answers)
        assert score == 100.0

    def test_partial_points(self):
        questions = [
            {"id": 1, "correct": "A", "points": 20},
            {"id": 2, "correct": "B", "points": 30},
            {"id": 3, "correct": "C", "points": 50},
        ]
        answers = {"1": "A", "2": "B", "3": "X"}
        score = calculate_score(questions, answers)
        assert score == 50.0  # (20+30)/100


class TestGetTestHistory:
    def test_empty_history(self):
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        mock_db = MagicMock()
        mock_db.query.return_value = mock_query

        result = get_test_history(1, mock_db)
        assert result == []

    def test_with_results(self):
        mock_results = [
            MagicMock(
                id=1, test_type="daily", score=80.0, cefr_level="A1",
                created_at=MagicMock(isoformat=MagicMock(return_value="2024-01-01T10:00:00")),
            ),
            MagicMock(
                id=2, test_type="weekly", score=90.0, cefr_level="A2",
                created_at=MagicMock(isoformat=MagicMock(return_value="2024-01-02T10:00:00")),
            )
        ]
        for r in mock_results:
            r.errors = '[{"type": "grammar"}]'

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        mock_db = MagicMock()
        mock_db.query.return_value = mock_query

        result = get_test_history(1, mock_db, limit=20)
        assert len(result) == 2
        assert result[0]["test_type"] == "daily"
        assert result[0]["score"] == 80.0
        assert result[0]["errors_count"] == 1
        assert result[1]["test_type"] == "weekly"

    def test_custom_limit(self):
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        mock_db = MagicMock()
        mock_db.query.return_value = mock_query

        get_test_history(1, mock_db, limit=5)
        mock_query.filter.return_value.order_by.return_value.limit.assert_called_with(5)


class TestSubmitTest:
    @pytest.mark.asyncio
    async def test_submit_daily_test(self):
        mock_user = MagicMock()
        mock_user.target_language = "German"
        mock_user.native_language = "Polish"
        mock_user.cefr_level = "A1"
        mock_user.total_xp = 0

        mock_db = MagicMock()
        # First .first() returns user, second (idempotency check) returns None
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, None]

        mock_analysis = {
            "score": 80.0,
            "errors": [{"type": "grammar", "description": "Wrong case"}]
        }

        with patch("backend.services.test_generator.analyze_test_errors", AsyncMock(return_value=mock_analysis)):
            with patch("backend.services.test_generator.generate_daily_test", AsyncMock()):
                result = await submit_test(
                    user_id=1,
                    test_type="daily",
                    questions=[{"id": 1, "correct": "A"}],
                    answers={"1": "A"},
                    db=mock_db
                )

                assert result["score"] == 80.0
                assert result["xp_earned"] == 40  # 80 * 0.5
                assert len(result["errors"]) == 1
                assert mock_user.total_xp == 40
                mock_db.add.assert_called()
                mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_submit_test_user_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="User 999 not found"):
            await submit_test(
                user_id=999,
                test_type="daily",
                questions=[],
                answers={},
                db=mock_db
            )

    @pytest.mark.asyncio
    async def test_submit_weekly_test(self):
        mock_user = MagicMock()
        mock_user.target_language = "German"
        mock_user.native_language = "Polish"
        mock_user.cefr_level = "B1"
        mock_user.total_xp = 100

        mock_db = MagicMock()
        # First .first() returns user, second (idempotency check) returns None
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, None]

        mock_analysis = {
            "score": 100.0,
            "errors": []
        }

        with patch("backend.services.test_generator.analyze_test_errors", AsyncMock(return_value=mock_analysis)):
            result = await submit_test(
                user_id=1,
                test_type="weekly",
                questions=[{"id": 1, "correct": "A"}],
                answers={"1": "A"},
                db=mock_db
            )

            assert result["score"] == 100.0
            assert result["xp_earned"] == 50  # Max 50
            assert mock_user.total_xp == 150
