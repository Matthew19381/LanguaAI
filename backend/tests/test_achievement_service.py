"""Pure unit tests for achievement_service — no HTTP client needed."""
from datetime import datetime, timezone

from backend.services.achievement_service import (
    ACHIEVEMENT_DEFS,
    calculate_level_from_xp,
    check_and_award_achievements,
    get_all_achievements_for_user,
    get_unnotified_achievements,
)

# ---------------------------------------------------------------------------
# calculate_level_from_xp
# ---------------------------------------------------------------------------

class TestCalculateLevelFromXP:
    def test_zero_xp_is_level_1(self):
        result = calculate_level_from_xp(0)
        assert result["level"] == 1
        assert result["xp"] == 0

    def test_level_2_at_20_xp(self):
        result = calculate_level_from_xp(20)
        assert result["level"] == 2

    def test_level_5_at_320_xp(self):
        result = calculate_level_from_xp(320)
        assert result["level"] == 5

    def test_level_10_at_1620_xp(self):
        result = calculate_level_from_xp(1620)
        assert result["level"] == 10

    def test_level_50_at_48020_xp(self):
        result = calculate_level_from_xp(48020)
        assert result["level"] == 50

    def test_max_level_is_50(self):
        result = calculate_level_from_xp(999999)
        assert result["level"] == 50
        assert result["max_level"] == 50
        assert result["progress_percent"] == 100.0

    def test_progress_percent_between_0_and_100(self):
        for xp in [0, 10, 100, 500, 1000, 5000]:
            result = calculate_level_from_xp(xp)
            assert 0.0 <= result["progress_percent"] <= 100.0

    def test_result_keys(self):
        result = calculate_level_from_xp(100)
        expected_keys = {"level", "level_name", "xp", "current_level_xp",
                         "next_level_xp", "progress_percent", "max_level"}
        assert expected_keys == set(result.keys())

    def test_level_name_beginner_at_level_1(self):
        result = calculate_level_from_xp(0)
        assert result["level_name"] == "Początkujący"

    def test_level_name_grand_master_at_level_50(self):
        result = calculate_level_from_xp(48020)
        assert result["level_name"] == "Wielki Mistrz"

    def test_level_names_progress(self):
        names_seen = set()
        for xp in [0, 20, 180, 500, 1620, 3920, 5620, 7920, 14420, 22420, 32420, 48020]:
            name = calculate_level_from_xp(xp)["level_name"]
            names_seen.add(name)
        # Should cover multiple distinct names across the 50 levels
        assert len(names_seen) >= 5


# ---------------------------------------------------------------------------
# check_and_award_achievements
# ---------------------------------------------------------------------------

class TestCheckAndAwardAchievements:
    """These tests use the real DB via the db fixture from conftest."""

    def _make_user(self, db, xp=0, streak=0):
        from backend.models.user import User
        user = User(
            name="Tester",
            native_language="Polish",
            target_language="German",
            cefr_level="A1",
            total_xp=xp,
            streak_days=streak,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_no_achievements_on_fresh_user(self, db):
        user = self._make_user(db)
        result = check_and_award_achievements(user, db)
        assert result == []

    def test_first_lesson_achievement(self, db):
        from backend.models.lesson import Lesson
        user = self._make_user(db)
        lesson = Lesson(
            user_id=user.id, day_number=1, title="T", topic="T",
            content="{}", cefr_level="A1", language="German",
            is_completed=True, completed_at=datetime.now(timezone.utc),
        )
        db.add(lesson)
        db.commit()

        result = check_and_award_achievements(user, db)
        types = [r["type"] for r in result]
        assert "first_lesson" in types

    def test_xp_100_achievement(self, db):
        user = self._make_user(db, xp=100)
        result = check_and_award_achievements(user, db)
        types = [r["type"] for r in result]
        assert "xp_100" in types

    def test_xp_500_achievement(self, db):
        user = self._make_user(db, xp=500)
        result = check_and_award_achievements(user, db)
        types = [r["type"] for r in result]
        assert "xp_100" in types
        assert "xp_500" in types

    def test_streak_3_achievement(self, db):
        user = self._make_user(db, streak=3)
        result = check_and_award_achievements(user, db)
        types = [r["type"] for r in result]
        assert "streak_3" in types

    def test_no_duplicate_achievements(self, db):
        user = self._make_user(db, xp=100)
        first = check_and_award_achievements(user, db)
        second = check_and_award_achievements(user, db)
        assert "xp_100" in [r["type"] for r in first]
        # Second call should return nothing new
        assert second == []

    def test_achievement_dict_has_required_keys(self, db):
        user = self._make_user(db, xp=100)
        result = check_and_award_achievements(user, db)
        for ach in result:
            assert "type" in ach
            assert "title" in ach
            assert "description" in ach
            assert "icon" in ach


# ---------------------------------------------------------------------------
# get_all_achievements_for_user
# ---------------------------------------------------------------------------

class TestGetAllAchievements:
    def _make_user(self, db):
        from backend.models.user import User
        user = User(
            name="T", native_language="Polish", target_language="German",
            cefr_level="A1", total_xp=0, streak_days=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_total_matches_defs(self, db):
        user = self._make_user(db)
        result = get_all_achievements_for_user(user.id, db)
        assert result["total"] == len(ACHIEVEMENT_DEFS)

    def test_earned_zero_initially(self, db):
        user = self._make_user(db)
        result = get_all_achievements_for_user(user.id, db)
        assert result["earned"] == 0

    def test_earned_increments(self, db):
        user = self._make_user(db)
        user.total_xp = 100
        db.commit()
        check_and_award_achievements(user, db)

        result = get_all_achievements_for_user(user.id, db)
        assert result["earned"] >= 1

    def test_each_achievement_has_earned_flag(self, db):
        user = self._make_user(db)
        result = get_all_achievements_for_user(user.id, db)
        for ach in result["achievements"]:
            assert "earned" in ach
            assert isinstance(ach["earned"], bool)


# ---------------------------------------------------------------------------
# get_unnotified_achievements
# ---------------------------------------------------------------------------

class TestGetUnnotifiedAchievements:
    def _make_user(self, db, xp=100):
        from backend.models.user import User
        user = User(
            name="T", native_language="Polish", target_language="German",
            cefr_level="A1", total_xp=xp, streak_days=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_unnotified_returned_once(self, db):
        user = self._make_user(db, xp=100)
        check_and_award_achievements(user, db)

        first_call = get_unnotified_achievements(user.id, db)
        assert len(first_call) >= 1

        second_call = get_unnotified_achievements(user.id, db)
        assert second_call == []   # Already marked as notified

    def test_unnotified_has_required_keys(self, db):
        user = self._make_user(db, xp=100)
        check_and_award_achievements(user, db)
        result = get_unnotified_achievements(user.id, db)
        for ach in result:
            assert "type" in ach
            assert "title" in ach
            assert "icon" in ach
            assert "unlocked_at" in ach
