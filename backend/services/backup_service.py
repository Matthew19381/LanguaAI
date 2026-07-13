"""
Backup Service — automated daily backup of LinguaAI.db with retention policy.

Usage:
    python -m backend.services.backup_service          # Run backup now
    python -m backend.services.backup_service --list   # List backups
    python -m backend.services.backup_service --restore <path>  # Restore from backup
"""
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Default paths — check multiple locations for the database
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Database can be in project root or backend/ (depends on config)
DB_CANDIDATES = [
    PROJECT_ROOT / "lingua_ai.db",
    PROJECT_ROOT / "LinguaAI.db",
    BACKEND_DIR / "lingua_ai.db",
    BACKEND_DIR / "LinguaAI.db",
]
DB_PATH = next((p for p in DB_CANDIDATES if p.exists()), DB_CANDIDATES[0])
BACKUP_DIR = PROJECT_ROOT / "backups"
RETENTION_DAYS = 7


def create_backup(db_path: Path = None, backup_dir: Path = None) -> Path:
    """Create a timestamped backup of the database."""
    db_path = db_path or DB_PATH
    backup_dir = backup_dir or BACKUP_DIR

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"lingua_ai_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name

    shutil.copy2(db_path, backup_path)
    logger.info(f"Backup created: {backup_path}")

    # Clean up old backups
    cleanup_old_backups(backup_dir)

    return backup_path


def cleanup_old_backups(backup_dir: Path = None, retention_days: int = RETENTION_DAYS):
    """Remove backups older than retention_days."""
    backup_dir = backup_dir or BACKUP_DIR
    if not backup_dir.exists():
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0

    for f in backup_dir.glob("lingua_ai_backup_*.db"):
        try:
            ts_str = f.stem.replace("lingua_ai_backup_", "")
            file_time = datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
            if file_time < cutoff:
                f.unlink()
                removed += 1
                logger.info(f"Removed old backup: {f.name}")
        except ValueError:
            continue

    if removed:
        logger.info(f"Removed {removed} backup(s) older than {retention_days} days")


def list_backups(backup_dir: Path = None) -> list:
    """List all available backups with metadata."""
    backup_dir = backup_dir or BACKUP_DIR
    if not backup_dir.exists():
        logger.info("No backups directory found.")
        return []

    backups = []
    for f in sorted(backup_dir.glob("lingua_ai_backup_*.db"), reverse=True):
        size_mb = f.stat().st_size / (1024 * 1024)
        backups.append({
            "path": str(f),
            "name": f.name,
            "size_mb": round(size_mb, 2),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })

    if not backups:
        logger.info("No backups found.")
    else:
        logger.info(f"Backups ({len(backups)} total):")
        for b in backups:
            logger.info(f"  {b['created']}  {b['size_mb']:>8.2f}MB  {b['name']}")

    return backups


def restore_backup(backup_path: str, db_path: Path = None):
    """Restore database from a backup file."""
    db_path = db_path or DB_PATH
    backup = Path(backup_path)

    if not backup.exists():
        raise FileNotFoundError(f"Backup not found: {backup}")

    # Safety: create a backup of current DB before restoring
    if db_path.exists():
        safety_path = db_path.with_suffix(".db.pre-restore")
        shutil.copy2(db_path, safety_path)
        logger.warning(f"Current DB saved to: {safety_path}")

    shutil.copy2(backup, db_path)
    logger.info(f"Database restored from: {backup}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LinguaAI Database Backup Tool")
    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--restore", type=str, metavar="PATH", help="Restore from backup file")
    parser.add_argument("--backup-dir", type=str, default=None, help="Custom backup directory")
    parser.add_argument("--db-path", type=str, default=None, help="Custom database path")
    parser.add_argument("--retention", type=int, default=RETENTION_DAYS, help=f"Retention in days (default: {RETENTION_DAYS})")

    args = parser.parse_args()

    backup_dir = Path(args.backup_dir) if args.backup_dir else None
    db_path = Path(args.db_path) if args.db_path else None

    if args.list:
        list_backups(backup_dir)
    elif args.restore:
        restore_backup(args.restore, db_path)
    else:
        create_backup(db_path, backup_dir)
