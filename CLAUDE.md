# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

Copy `backend/.env.example` → `backend/.env`. The default AI provider is **OpenRouter** (`AI_PROVIDER=openrouter` in `backend/config.py`), so set **`OPENROUTER_API_KEY`**. To use the direct Gemini API instead, set `AI_PROVIDER=gemini` and **`GEMINI_API_KEY`**. The SQLite database (`lingua_ai.db`) is created automatically in `backend/` on first startup via `Base.metadata.create_all()` in `main.py`'s lifespan handler.

Model selection is centralized in `backend/services/model_router.py` (curated OpenRouter + Gemini catalog, tiered `free`/`cheap`/`best`). The active tier is `AI_MODEL_TIER` (default `cheap`); `gemini_service` resolves the default model from `model_router` — never hardcode a model id.

**When adding a new SQLAlchemy model**: import it inside the lifespan block in `main.py` (alongside the existing `achievement` import) so it registers with `Base` before `create_all` runs.

## Architecture

### Backend

**Stack**: FastAPI · SQLAlchemy (SQLite) · Google Gemini 2.0 Flash · edge-tts · fpdf2 · feedparser · faster-whisper

**Request flow**:
```
Router → Service → SQLAlchemy Session (get_db dependency)
```

**`backend/services/gemini_service.py`** is the single point of contact with Gemini. Two functions only:
- `generate_json(prompt)` — appends "Respond ONLY with valid JSON" and strips markdown fences before parsing
- `generate_text(prompt)` — raw string response

Every function in every service that calls Gemini has a hardcoded fallback dict/string so the app degrades gracefully when the API fails.

**`backend/schemas/`** — Pydantic models for request/response validation (unified standard across ecosystem).

**`backend/services/lesson_generator.py`** contains all AI prompt logic: placement test, study plan, daily lesson, daily/weekly tests, conversation, tips. `generate_daily_lesson()` accepts `recent_topics` (list of strings from the last 7 days of lessons) to produce an `interleaved_review` section in the output.

**Adding a new router**: import it in `main.py` with `prefix="/api/v1"` and call `app.include_router(...)`.

**`backend/services/test_generator.py`** is a non-router service layer that wraps lesson_generator calls for test creation/submission. It handles XP award on submit (`score × 0.5`, max 50 XP) and writes `TestResult` rows.

**`backend/services/achievement_service.py`** owns all level/XP math:
- `calculate_level_from_xp(xp)` — 50 levels, quadratic curve: level `n` requires `(n-1)² × 20` total XP
- `check_and_award_achievements(user, db)` — call this after any XP-awarding action; returns list of newly unlocked achievements for toast display
- `get_unnotified_achievements(user_id, db)` — returns unnotified achievements and marks them notified (used by `GET /api/stats/{user_id}` to drive toasts in Layout)

**Lesson content storage**: `Lesson.content` is a JSON blob (SQLAlchemy `Text` column). All lesson sections — including newer ones (`comprehensible_input`, `interleaved_review`, `output_forcing`) — live inside this blob. No migration is needed when adding new sections; the frontend just checks for their presence before rendering.

**Routers** (`backend/routers/`):

| File | API prefix | Responsibility |
|---|---|---|
| `placement.py` | `/api/v1/placement/` | User creation, 20-question CEFR test, study plan generation |
| `lessons.py` | `/api/v1/lessons/` | Daily lesson get/create, complete (+25 XP), audio, PDF export |
| `tests.py` | `/api/v1/tests/` | Daily/weekly test get + submit (delegates to `test_generator`) |
| `flashcards.py` | `/api/v1/flashcards/` | Spaced repetition review, Anki deck export |
| `conversation.py` | `/api/v1/conversation/` | AI conversation sessions and analysis |
| `stats.py` | `/api/v1/stats/`, `/api/v1/tips/` | XP/level, achievements, leaderboard, daily tips |
| `quickmode.py` | `/api/v1/quickmode/` | 15-minute daily activity plan |
| `news.py` | `/api/v1/news/` | RSS fetch (feedparser) + Gemini simplification per CEFR level |
| `pronunciation.py` | `/api/v1/pronunciation/` | faster-whisper transcription + word-level scoring |
| `push.py` | `/api/push/` | Web Push (VAPID): public key, subscribe/unsubscribe, test send |

**Adding a new router**: import it in `main.py` and call `app.include_router(...)`.

### Frontend

**Stack**: React 18 · React Router v6 · Axios · Tailwind CSS · Vite · lucide-react

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
| Gemini model | `gemini-2.0-flash` | `services/gemini_service.py` |
| Whisper model | `tiny` (~75 MB, CPU, int8) | `services/pronunciation_service.py` |
| API timeout (frontend) | 120 s | `api/client.js` (baseURL: `/api` — routery montują pełne ścieżki `/api/...`; wyjątek: `users` pod `/api/v1/users`) |
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

All git commands run from `C:\GoogleDriveSync\Projekty\LinguaAI\` (the repo root):

**Unified Standards**: See `07_Context/UNIFIED_STANDARDS.md` for cross-project standards (System-Główny + LinguaAI + ForgeBody + HackerLabAcademy).

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
