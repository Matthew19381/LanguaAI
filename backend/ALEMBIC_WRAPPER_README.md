# Alembic Wrapper Guide

This document explains the `alembic_wrapper.py` solution for CWD isolation issues.

## Problem

When running Alembic migrations from a kanban workspace (agent's current working directory), the command fails with:

```
FAILED: No config file 'alembic.ini' found, or file has no '[alembic]' section
Exit code: 127
```

This happens because Alembic looks for `alembic.ini` in the current working directory (CWD), not in the project root.

## Solution

`backend/alembic_wrapper.py` is a Python script that:
1. Detects its own location (`backend/` directory)
2. Changes CWD to the project root (parent of `backend/`)
3. Runs Alembic with an absolute path to `alembic.ini`
4. Passes all arguments through to Alembic

## Usage

From anywhere (kanban workspace, project root, anywhere):

```bash
python backend/alembic_wrapper.py revision --autogenerate -m "add users table"
python backend/alembic_wrapper.py upgrade head
python backend/alembic_wrapper.py current
python backend/alembic_wrapper.py history
```

## Why This Works

- **Absolute path to alembic.ini**: `backend/alembic_wrapper.py` uses `Path(__file__).parent` to find its own location, then constructs the absolute path to the config file.
- **CWD change**: `os.chdir(project_root)` ensures DATABASE_URL (a relative path) is resolved correctly from the project root.
- **Transparent to Alembic**: All Alembic arguments are passed through unchanged, so the wrapper is 100% compatible with existing Alembic commands.

## Alternative (Manual)

If you prefer not to use the wrapper, you can specify the absolute path to `alembic.ini` directly:

```bash
python -m alembic -c "C:\Projects\LinguaAI\backend\alembic.ini" revision --autogenerate -m "..."
```

On Linux/Mac:

```bash
python -m alembic -c "/home/user/projects/LinguaAI/backend/alembic.ini" revision --autogenerate -m "..."
```

## Testing

Test that the wrapper works from any directory:

```bash
# From project root
cd C:\Projects\LinguaAI
python backend/alembic_wrapper.py current

# From a different directory (e.g., kanban workspace)
cd C:\Users\Acer\AppData\Local\hermes\kanban\workspaces\some_task
python C:\Projects\LinguaAI\backend\alembic_wrapper.py current

# Both should succeed with exit code 0 and show the current migration head
```

## Implementation Notes

- Wrapper is pure Python 3.12+, using only `subprocess` and `pathlib` (stdlib)
- No dependencies required
- Works on Windows, Linux, and macOS
- Exit code matches Alembic's exit code (0 for success, non-zero for failure)
