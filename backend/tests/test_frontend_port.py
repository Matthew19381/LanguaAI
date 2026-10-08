"""The dev frontend must not share :5173 with the System-Glowny hub (B7, found 2026-10-08):
whichever started second silently moved to another port and start.bat opened the wrong app.
Port registry: System-Glowny/CLAUDE.md ("Porty frontendu")."""
import re
from pathlib import Path

from backend.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PORT = 5177
HUB_FRONTEND_PORT = 5173


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_vite_dev_server_uses_registered_port():
    server = _read("frontend/vite.config.js").split("server:", 1)[1]
    assert re.search(r"port:\s*(\d+)", server).group(1) == str(FRONTEND_PORT)


def test_launchers_backend_and_docker_agree_on_the_port():
    files = ["start.bat", "start.ps1", "backend/main.py", "docker-compose.yml", "Dockerfile.frontend",
             "Dockerfile.backend", "frontend/playwright.config.js", ".claude/launch.json"]
    for rel in files:
        text = _read(rel)
        assert str(HUB_FRONTEND_PORT) not in text, rel
    assert f"localhost:{FRONTEND_PORT}" in _read("start.bat")
    assert Settings.model_fields["FRONTEND_URL"].default == f"http://localhost:{FRONTEND_PORT}"
