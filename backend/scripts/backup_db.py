"""Daily database backup script for LinguaAI.

Creates timestamped backups of lingua_ai.db in backend/backups/
and keeps the last 7 daily backups.
"""

import glob
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "lingua_ai.db")
KEEP_COUNT = 7


def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if not os.path.exists(DB_PATH):
        logger.warning(f"Database not found: {DB_PATH}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"lingua_ai_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    shutil.copy2(DB_PATH, backup_path)
    logger.info(f"Backup created: {backup_path}")

    # Remove old backups, keep last KEEP_COUNT
    pattern = os.path.join(BACKUP_DIR, "lingua_ai_*.db")
    backups = sorted(glob.glob(pattern), key=os.path.getmtime)
    while len(backups) > KEEP_COUNT:
        old = backups.pop(0)
        os.remove(old)
        logger.info(f"Removed old backup: {old}")


if __name__ == "__main__":
    create_backup()
