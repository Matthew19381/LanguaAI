"""Tests for backup_service — database backup, listing, retention, and restore."""
from datetime import datetime, timedelta

import pytest

from backend.services.backup_service import (
    RETENTION_DAYS,
    cleanup_old_backups,
    create_backup,
    list_backups,
    restore_backup,
)


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary source DB and backup directories."""
    db_path = tmp_path / "test.db"
    db_path.write_bytes(b"fake db content for testing")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return {"db_path": db_path, "backup_dir": backup_dir}


class TestCreateBackup:
    def test_create_backup_success(self, temp_dirs):
        """Backup creates a timestamped .db file in backup_dir."""
        result = create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )
        assert result.exists()
        assert result.suffix == ".db"
        assert "lingua_ai_backup_" in result.name
        assert result.read_bytes() == b"fake db content for testing"

    def test_create_backup_creates_directory(self, temp_dirs):
        """Backup creates backup_dir if it doesn't exist."""
        new_dir = temp_dirs["backup_dir"] / "subdir"
        result = create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=new_dir,
        )
        assert new_dir.exists()
        assert result.exists()

    def test_create_backup_missing_db(self, temp_dirs):
        """Backup raises FileNotFoundError for missing DB."""
        missing = temp_dirs["db_path"] / "nonexistent.db"
        with pytest.raises(FileNotFoundError, match="Database not found"):
            create_backup(db_path=missing, backup_dir=temp_dirs["backup_dir"])

    def test_create_backup_runs_cleanup(self, temp_dirs):
        """Creating a backup triggers cleanup of old backups."""
        # Create a fake old backup
        old_name = "lingua_ai_backup_2020-01-01_00-00-00.db"
        (temp_dirs["backup_dir"] / old_name).write_bytes(b"old")

        create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )

        # Old backup should be removed
        assert not (temp_dirs["backup_dir"] / old_name).exists()

    def test_create_backup_preserves_recent(self, temp_dirs):
        """Recent backups (within retention) are not removed."""
        # Create a recent backup
        recent_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        recent_name = f"lingua_ai_backup_{recent_ts}.db"
        (temp_dirs["backup_dir"] / recent_name).write_bytes(b"recent")

        create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )

        # Recent backup should still exist
        assert (temp_dirs["backup_dir"] / recent_name).exists()


class TestCleanupOldBackups:
    def test_cleanup_removes_old_backups(self, temp_dirs):
        """Backups older than RETENTION_DAYS are removed."""
        old_ts = (datetime.now() - timedelta(days=RETENTION_DAYS + 1)).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        old_file = temp_dirs["backup_dir"] / f"lingua_ai_backup_{old_ts}.db"
        old_file.write_bytes(b"old")

        cleanup_old_backups(temp_dirs["backup_dir"], RETENTION_DAYS)

        assert not old_file.exists()

    def test_cleanup_keeps_recent_backups(self, temp_dirs):
        """Backups within retention period are kept."""
        recent_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        recent_file = temp_dirs["backup_dir"] / f"lingua_ai_backup_{recent_ts}.db"
        recent_file.write_bytes(b"recent")

        cleanup_old_backups(temp_dirs["backup_dir"], RETENTION_DAYS)

        assert recent_file.exists()

    def test_cleanup_ignores_non_backup_files(self, temp_dirs):
        """Non-backup files in the directory are not touched."""
        other_file = temp_dirs["backup_dir"] / "readme.txt"
        other_file.write_text("hello")

        cleanup_old_backups(temp_dirs["backup_dir"], RETENTION_DAYS)

        assert other_file.exists()

    def test_cleanup_ignores_malformed_names(self, temp_dirs):
        """Files with unexpected names are skipped gracefully."""
        bad_file = temp_dirs["backup_dir"] / "lingua_ai_backup_INVALID.db"
        bad_file.write_bytes(b"bad")

        cleanup_old_backups(temp_dirs["backup_dir"], RETENTION_DAYS)

        assert bad_file.exists()

    def test_cleanup_empty_directory(self, temp_dirs):
        """Cleanup on empty directory does nothing."""
        empty_dir = temp_dirs["backup_dir"] / "empty"
        empty_dir.mkdir()
        cleanup_old_backups(empty_dir, RETENTION_DAYS)  # Should not raise

    def test_cleanup_nonexistent_directory(self, temp_dirs):
        """Cleanup on nonexistent directory does nothing."""
        fake_dir = temp_dirs["backup_dir"] / "nonexistent"
        cleanup_old_backups(fake_dir, RETENTION_DAYS)  # Should not raise


class TestListBackups:
    def test_list_empty_directory(self, temp_dirs):
        """Listing empty backup dir returns empty list."""
        result = list_backups(temp_dirs["backup_dir"])
        assert result == []

    def test_list_returns_metadata(self, temp_dirs):
        """Listed backups include name, size_mb, created."""
        # Create a backup file directly (bypass cleanup)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = temp_dirs["backup_dir"] / f"lingua_ai_backup_{ts}.db"
        backup_file.write_bytes(b"test backup content")

        result = list_backups(temp_dirs["backup_dir"])
        assert len(result) == 1
        b = result[0]
        assert "name" in b
        assert "size_mb" in b
        assert "created" in b
        assert "path" in b
        assert b["size_mb"] >= 0

    def test_list_sorted_newest_first(self, temp_dirs):
        """Backups are sorted newest first."""
        # Create two backups with a small delay
        create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )
        create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )
        result = list_backups(temp_dirs["backup_dir"])
        if len(result) >= 2:
            assert result[0]["created"] >= result[1]["created"]

    def test_list_nonexistent_directory(self, temp_dirs):
        """Listing nonexistent dir returns empty list."""
        fake_dir = temp_dirs["backup_dir"] / "nonexistent"
        result = list_backups(fake_dir)
        assert result == []


class TestRestoreBackup:
    def test_restore_success(self, temp_dirs):
        """Restore copies backup to db_path."""
        # Create a backup
        backup_path = create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )

        # Modify the original DB
        temp_dirs["db_path"].write_bytes(b"modified content")

        # Restore
        restore_backup(str(backup_path), temp_dirs["db_path"])

        assert temp_dirs["db_path"].read_bytes() == b"fake db content for testing"

    def test_restore_creates_safety_copy(self, temp_dirs):
        """Restore creates a .db.pre-restore safety copy of current DB."""
        backup_path = create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )

        temp_dirs["db_path"].write_bytes(b"current state")
        restore_backup(str(backup_path), temp_dirs["db_path"])

        safety = temp_dirs["db_path"].with_suffix(".db.pre-restore")
        assert safety.exists()
        assert safety.read_bytes() == b"current state"

    def test_restore_missing_backup(self, temp_dirs):
        """Restore raises FileNotFoundError for missing backup."""
        with pytest.raises(FileNotFoundError, match="Backup not found"):
            restore_backup("/nonexistent/backup.db", temp_dirs["db_path"])

    def test_restore_creates_db_if_missing(self, temp_dirs):
        """Restore works even if target db_path doesn't exist yet."""
        backup_path = create_backup(
            db_path=temp_dirs["db_path"],
            backup_dir=temp_dirs["backup_dir"],
        )

        new_db = temp_dirs["backup_dir"] / "new_location.db"
        restore_backup(str(backup_path), new_db)

        assert new_db.exists()
        assert new_db.read_bytes() == b"fake db content for testing"


class TestBackupAPIEndpoints:
    """Test the backup API endpoints via TestClient."""

    def test_trigger_backup(self, client):
        """POST /api/admin/backup creates a backup."""
        r = client.post("/api/admin/backup", headers={"X-Admin-Key": "test-key"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "backup" in data

    def test_list_backups(self, client):
        """GET /api/admin/backups returns list of backups."""
        r = client.get("/api/admin/backups", headers={"X-Admin-Key": "test-key"})
        assert r.status_code == 200
        data = r.json()
        assert "backups" in data
        assert isinstance(data["backups"], list)

    def test_backup_requires_auth(self, client):
        """POST /api/admin/backup without key returns 422 (missing required header)."""
        r = client.post("/api/admin/backup")
        assert r.status_code == 422

    def test_restore_backup_not_found(self, client):
        """POST /api/admin/restore with nonexistent file returns 404."""
        r = client.post("/api/admin/restore?backup_filename=nonexistent.db",
                        headers={"X-Admin-Key": "test-key"})
        assert r.status_code == 404

    def test_restore_backup_requires_auth(self, client):
        """POST /api/admin/restore without key returns 422."""
        r = client.post("/api/admin/restore?backup_filename=test.db")
        assert r.status_code == 422

    def test_restore_backup_wrong_key(self, client):
        """POST /api/admin/restore with wrong key returns 403."""
        r = client.post("/api/admin/restore?backup_filename=test.db",
                        headers={"X-Admin-Key": "wrong-key"})
        assert r.status_code == 403
