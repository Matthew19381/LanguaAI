# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Lokalizacja i backup (WAŻNE)

Projekt **musi** żyć poza folderem synchronizowanym z chmurą (Google Drive / OneDrive / Dropbox). Kanoniczna ścieżka: **`C:\Projects\LinguaAI`**. Trzymanie projektu w Google Drive (`C:\GoogleDriveSync\...`) powoduje, że sterownik chmury śledzi/synchronizuje ~24 000 plików `node_modules` → cold build rośnie z ~2 s do **>2 min**, a `start.bat` wisi na „Frontend jeszcze się kompiluje". Backup kodu zapewnia **git → GitHub**, nie chmura plikowa.

Backup bazy (postęp/wygenerowane treści) do chmury: `backend/scripts/backup_to_cloud.ps1` kopiuje `lingua_ai.db` (setki KB) do `C:\GoogleDriveSync\LinguaAI-backup\` (mały, szybko-synchronizujący się folder). Uruchamiane codziennie przez zadanie `LinguaAI-DB-Backup` (Harmonogram zadań, 20:00). Rejestracja/usunięcie:
```bash
schtasks /Create /TN "LinguaAI-DB-Backup" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projects\LinguaAI\backend\scripts\backup_to_cloud.ps1" /SC DAILY /ST 20:00 /F
schtasks /Delete /TN "LinguaAI-DB-Backup" /F
```

## Starting the App

Run from the **project root** (`C:\Projects\LinguaAI\`). Never `cd` into `backend/` first — the backend must be launched from the root so that `backend.*` absolute imports resolve correctly.

```bash
# Windows CMD (opens two terminal windows)
start.bat

# PowerShell
.\start.ps1

# Manual — backend (from C:\Projects\LinguaAI\)
uvicorn backend.main:app --reload --port 8001

# Manual — frontend (from C:\Projects\LinguaAI\frontend\)
npm run dev
```

Frontend dev server runs on `:5173` and proxies `/api` and `/audio` to `http://localhost:8001` (configured in `frontend/vite.config.js`), so all API calls use relative paths like `/api/...`.

## Environment

Copy `backend/.env.example` → `backend/.env`. The default AI provider is **OpenRouter** (`AI_PROVIDER=openrouter` in `backend/config.py`), so set **`OPENROUTER_API_KEY`**. To use the direct Gemini API instead, set `AI_PROVIDER=gemini` and **`GEMINI_API_KEY`**. The SQLite database (`lingua_ai.db`) is created automatically in the **project root** (not `backend/`) on first startup — `main.py`'s lifespan handler runs `alembic upgrade head`, which builds the full schema on an empty database.

Model selection is centralized in `backend/services/model_router.py` (curated OpenRouter + Gemini catalog, tiered `free`/`cheap`/`best`). The active tier is `AI_MODEL_TIER` (default `cheap`); `gemini_service` resolves the default model from `model_router` — never hardcode a model id.

**When adding a new SQLAlchemy model**: add its import to `backend/alembic/env.py` (so autogenerate sees it) — see "Migracje bazy danych" below. It doesn't need a separate import in `main.py` anymore; whichever router/service imports the model directly is enough to register it with `Base`.

## Migracje bazy danych

**Alembic jest jedynym źródłem prawdy dla schematu** (decyzja użytkownika 2026-08-09, `ACTION_PLAN.md` Faza 1). Zero ręcznych `ALTER TABLE` / `sqlite3` na `lingua_ai.db` od teraz — to dokładnie ten wzorzec, który przez miesiące rozjeżdżał historię Alembica z rzeczywistym schematem (`backend/alembic/README`, sekcja "Policy", ma pełną historię incydentu).

Każda zmiana modelu w `backend/models/*.py` **musi** iść w jednym commicie z nową rewizją:

```bash
py -3.11 -m alembic -c backend/alembic.ini revision --autogenerate -m "opis zmiany"
```

Zawsze uruchamiaj z **roota projektu**, nigdy z `cd backend` — `DATABASE_URL` jest ścieżką względną rozwiązywaną względem cwd procesu; z `backend/` trafiłbyś w zły plik. Zawsze przejrzyj wygenerowaną rewizję ręcznie przed commitem (SQLite autogenerate bywa niedokładny — patrz `backend/alembic/README` po przykłady). `backend/main.py`'s lifespan uruchamia `alembic upgrade head` przy każdym starcie (pomijane gdy `TESTING=1`).

## Architecture

**Full, maintained architecture reference: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** —
router table (20 routers), service list, data model, pedagogy, offline/PWA, security.
This CLAUDE.md section intentionally does NOT duplicate that table anymore (a stale
copy of it here previously drifted out of sync with the code — see CHANGELOG 2026-08-07).
Only stable, quick-reference facts live here; if in doubt, ARCHITECTURE.md wins.

### Backend

**Stack**: FastAPI · SQLAlchemy (SQLite, Postgres-ready) · OpenRouter (default) or Google Gemini Direct · edge-tts · fpdf2 · feedparser · faster-whisper

**Request flow**:
```
Router → Service → SQLAlchemy Session (get_db dependency)
```

**`backend/services/gemini_service.py`** is the single point of contact with the AI provider. Two functions only:
- `generate_json(prompt, fallback=None)` — forces JSON at the provider level, strips markdown fences, parses. On failure returns `fallback` **only if the caller passed one** — most call sites don't, and get a raised `ValueError` instead. Don't assume every AI call degrades gracefully; check the call site.
- `generate_text(prompt)` — raw string response.
- Model choice is centralized in `backend/services/model_router.py` (tiered `free`/`cheap`/`best` catalog, per-task mapping) via the `@with_model("<task>")` decorator — never hardcode a model id.

**`backend/schemas/`** — Pydantic models for request/response validation (unified standard across ecosystem).

**`backend/services/lesson_generator/`** (package) contains all AI prompt logic: placement test, study plan, daily lesson, daily/weekly tests, conversation, tips. `generate_daily_lesson()` accepts `recent_topics` (list of strings from the last 7 days of lessons) to produce an `interleaved_review` section in the output.

**`backend/services/test_generator.py`** is a non-router service layer that wraps lesson_generator calls for test creation/submission. It handles XP award on submit (`score × 0.5`, max 50 XP) and writes `TestResult` rows.

**`backend/services/achievement_service.py`** owns all level/XP math:
- `calculate_level_from_xp(xp)` — 50 levels, quadratic curve: level `n` requires `(n-1)² × 20` total XP
- `check_and_award_achievements(user, db)` — call this after any XP-awarding action; returns list of newly unlocked achievements for toast display
- `get_unnotified_achievements(user_id, db)` — returns unnotified achievements and marks them notified (used by `GET /api/stats/{user_id}` to drive toasts in Layout)

**Lesson content storage**: `Lesson.content` is a JSON blob (SQLAlchemy `Text` column). All lesson sections — including newer ones (`comprehensible_input`, `interleaved_review`, `output_forcing`) — live inside this blob. No migration is needed when adding new sections; the frontend just checks for their presence before rendering.

**Adding a new router**: import it in `main.py` and call `app.include_router(...)`. Update the router table in `docs/ARCHITECTURE.md §6`, not here.

### Frontend

**Stack**: React 19 · React Router 7 · Axios · Tailwind CSS · Vite · lucide-react

**`frontend/src/api/client.js`** — all API calls. The `api` Axios instance has a response interceptor that unwraps `response.data`. **Exception**: PDF export (`exportLessonPDF`) and pronunciation analysis use raw `axios` directly to support `responseType: 'blob'` and `multipart/form-data` respectively.

**State**: no global state manager. Each page fetches its own data on mount. `userId` is stored in `localStorage` and read via `getUserId()` from `client.js`.

**`frontend/src/components/Layout.jsx`** calls `getStats(userId)` on mount. Any `new_achievements` in the response render as auto-dismissing toasts (4 s). This is how the backend's `notified` flag on achievements drives frontend toasts.

**New lesson sections in `DailyLesson.jsx`** — all conditional on presence in `lesson.content`:
- `comprehensible_input` → "Reading Practice (i+1)" with highlighted new words
- `interleaved_review` → "Mixed Review" from previous lesson topics
- `output_forcing` → two-phase hide-and-recall card (`OutputForcingCard` component)

## Key Numbers

| Constant | Value | Location |
|---|---|---|
| Lesson completion XP | +25 | `routers/lessons.py` |
| Test submission XP | `score × 0.5` (max 50) | `services/test_generator.py` |
| Level curve | `(n-1)² × 20` XP, 50 levels | `services/achievement_service.py` |
| AI model | tiered catalog (`free`/`cheap`/`best`), per-task mapping — no fixed model id | `services/model_router.py` |
| Whisper model | `tiny` (~75 MB, CPU, int8) | `services/pronunciation_service.py` |
| API timeout (frontend) | 240 s | `api/client.js` (best-tier lekcja/test dnia bywa >110s; baseURL: `/api` — routery montują pełne ścieżki `/api/...`; wyjątek: `users` pod `/api/v1/users`) |
| Backend port | `8001` (unified standard) | `start.bat`, `docker-compose.yml` |

## Git — Mandatory Push Policy

**Push to GitHub after every meaningful change.** Never let work accumulate in an unsaved local state. If a session ends without pushing, progress can be lost.

### When to commit and push

Commit and push immediately after each of the following:
- Any new file created (router, service, component, page)
- Any bug fixed
- Any feature completed or partially completed
- Any refactor, even small
- Any CLAUDE.md update
- Before ending a work session

### Commit message format

Messages must be specific enough to understand what changed without reading the diff:

```
<type>: <what changed and why>

- Detail 1 (which file, what exactly)
- Detail 2
- Detail 3 (if relevant)
```

**Types**: `feat`, `fix`, `refactor`, `style`, `docs`, `chore`

**Good examples**:
```
feat: add PDF export endpoint for lessons

- backend/routers/lessons.py: GET /api/lessons/{id}/export-pdf
- backend/services/pdf_service.py: fpdf2-based generator with vocab table
- frontend/src/pages/DailyLesson.jsx: Download PDF button with blob fetch
```

```
fix: correct uvicorn launch path in start.bat

- Was: cd backend && uvicorn main:app
- Now: uvicorn backend.main:app (run from project root)
- Fixes ImportError on relative backend.* imports
```

**Bad examples** (too vague — never use these):
```
update files
fix bug
changes
wip
```

### Commands

All git commands run from `C:\Projects\LinguaAI\` (the repo root):

**Unified Standards**: `07_Context/UNIFIED_STANDARDS.md` does not exist in this repo. Cross-project standards live in `C:\Projects\System-Glowny\CLAUDE.md` + `MASTER_PLAN.md` — see those for ecosystem-wide conventions (System-Główny + LinguaAI + ForgeBody + HackerLabAcademy).

```bash
git add -A
git commit -m "feat: description

- file.py: what changed
- component.jsx: what changed"
git push
```

Check what will be committed before committing:
```bash
git status
git diff --staged
```

The `backend/.env`, `*.db`, `backend/audio/`, `backend/exports/`, and `frontend/dist/` are gitignored and will never be committed.
