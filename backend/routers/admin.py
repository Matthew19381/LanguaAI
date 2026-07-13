"""
Admin router — protected endpoints for maintenance operations.

Requires ADMIN_API_KEY header for all endpoints.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.services.backup_service import create_backup, list_backups, restore_backup

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_admin(x_admin_key: str = Header(...)):
    """Verify admin API key from header."""
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured — set ADMIN_API_KEY in .env")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return True


@router.post("/api/admin/backup")
async def admin_create_backup(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """Create a database backup. Requires admin API key."""
    try:
        backup_path = create_backup()
        return {
            "success": True,
            "backup": str(backup_path.name),
            "path": str(backup_path),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


@router.get("/api/admin/backups")
async def admin_list_backups(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """List all available backups. Requires admin API key."""
    backups = list_backups()
    return {
        "success": True,
        "backups": backups,
        "count": len(backups),
    }


@router.post("/api/admin/restore")
async def admin_restore_backup(
    backup_filename: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin)
):
    """Restore database from a backup file. Requires admin api key. Creates safety backup first."""
    try:
        restore_backup(backup_filename)
        return {"success": True, "restored_from": backup_filename}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")
