#!/usr/bin/env python3
"""
Alembic wrapper: ensures alembic always runs from project root.
This solves CWD isolation issues when agents run commands from kanban workspace.
Usage: python alembic_wrapper.py [alembic args...]
"""

import os
import subprocess
import sys
from pathlib import Path

# Get the directory containing this script (backend/)
backend_dir = Path(__file__).parent

# Get the project root (parent of backend/)
project_root = backend_dir.parent

# Change to project root
os.chdir(project_root)

# Run alembic with -c pointing to backend/alembic.ini
alembic_ini = backend_dir / "alembic.ini"

cmd = [
    sys.executable,
    "-m",
    "alembic",
    "-c",
    str(alembic_ini)
] + sys.argv[1:]

# Execute alembic
sys.exit(subprocess.call(cmd))
