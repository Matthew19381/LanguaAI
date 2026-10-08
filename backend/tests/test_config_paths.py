"""A relative SQLite DATABASE_URL must not depend on the directory uvicorn was started from
(B4, found 2026-10-08): start.bat runs from the repo root (lingua_ai.db there), a start from
backend/ silently opened a second, empty backend/lingua_ai.db."""
from pathlib import Path

from backend.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_relative_sqlite_path_means_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # anywhere but the repo
    url = Settings(DATABASE_URL="sqlite:///./lingua_ai.db").DATABASE_URL
    assert url == "sqlite:///" + (REPO_ROOT / "lingua_ai.db").as_posix()


def test_absolute_memory_and_other_urls_untouched():
    absolute = "sqlite:///" + (REPO_ROOT / "x.db").as_posix()
    assert Settings(DATABASE_URL=absolute).DATABASE_URL == absolute
    assert Settings(DATABASE_URL="sqlite:///:memory:").DATABASE_URL == "sqlite:///:memory:"
    assert Settings(DATABASE_URL="postgresql://u@h/db").DATABASE_URL == "postgresql://u@h/db"
