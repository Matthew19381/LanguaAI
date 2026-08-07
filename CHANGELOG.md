# CHANGELOG — LinguaAI

Format: newest first. Każdy wpis: wersja (jeśli dotyczy) + data + opis.

---

## 2026-08-07

### Docs: audyt dokumentacji + zgodności naukowej (DOC-2…DOC-6)
- **CLAUDE.md** — sekcja Architecture przepisana: usunięta zdezaktualizowana tabela
  10 routerów (realnie jest 20, linkuje teraz do `docs/ARCHITECTURE.md §6`); stack
  poprawiony na React 19/Router 7 (było: 18/v6); „Google Gemini 2.0 Flash"/
  `gemini-2.0-flash` zastąpione opisem tierowanego katalogu `model_router.py`;
  doprecyzowany fallback `generate_json` jako opt-in (`fallback=`), nie uniwersalny.
- **`docs/API_FUNCTIONS.md`** — usunięta nieprawdziwa wzmianka o „neuro-wagach"
  (funkcja usunięta miesiąc temu) i „zmianie API key" (nie istnieje) w opisie Settings.
- **`docs/NEURO_FEATURES.md`** — SCI-1…SCI-7 przeniesione z backlogu (§4) do „Stan
  faktyczny" (§1) jako ✅ Produkcja; dokument sam siebie nazywa źródłem prawdy, ale
  nie był aktualizowany od 3 tygodni mimo wdrożenia tych funkcji.
- **`NEURO_PLAN.md`** — SCI-7 oznaczone jako zaimplementowane (nie „do dodania"),
  SCI-8 jako częściowe; sekcja „Fazy" opisana jako plan pierwotny + rzeczywista
  kolejność wykonania (odjechały od siebie).
- **`docs/ARCHITECTURE.md`** — liczba stron frontendu 19→20 (doszła `Settings.jsx`,
  2026-08-06).
- **`docs/PRODUCTION_AND_MOBILE.md`** — otwierający „current development blocker"
  (brakująca kolumna `isImportant`) oznaczony jako rozwiązany od dawna; treść
  zostawiona jako referencja wzorca migracji, nie jako aktualny problem.
- Kontekst: pełny audyt (dokumentacja + regresja naukowa SCI-1…SCI-7 + 4 nowe
  propozycje SCI-11…SCI-14) w `TASKS.md`.

---

## 2026-07-24

### Docs: audyt dokumentacji D1-D6
- **D1** — usunięty `ADR-003-account-protection.md` (obcy projekt AutoLogic, kontaminacja repo)
- **D2** — `FEEDBACK.md` nie istnieje: odniesienia zastąpione aktualnym stanem
  (modele zarządzane przez `backend/services/model_router.py` + audyt A1-A10 w TASKS.md)
- **D3** — dopisane porzucenie Ollamy (patrz wpis poniżej z 2026-04-05): od
  2026-07-13 wszystko idzie przez OpenRouter; lokalna Ollama nie jest używana
  w kodzie ani w docker-compose
- **D4** — README zaktualizowane: usunięte martwe funkcje (modulacja FSRS,
  gesturalna kotwica, Ollama), dodane brakujące (bank ćwiczeń, PWA, bramka,
  profil JSON); poprawiony provider domyślny na OpenRouter
- **D5+D6** — `docs/deployment.md`: dopisana bramka `APP_ACCESS_TOKEN` jako
  warunek wystawienia (wcześniej przewodnik prowadził do publicznego API bez
  uwierzytelnienia); usunięty martwy `DEBUG=False` (nie istnieje w config.py)

---

## 2026-07-20

### Feat: INT-1 — integracja z Systemem Głównym (pilot ekosystemu)
- **`backend/routers/integration.py`** — nowy `GET /api/v1/summary?user_id&date`
  w ujednoliconym formacie ekosystemu: `{module, user_id, date, summary
  {lessons_completed, tests_submitted, reviews_done, due_reviews, mastered_words,
  streak, total_xp, target_language, cefr_level}, events, wellbeing_contribution}`.
  Read-only agregacja z DB, zero wywołań AI. `wellbeing_contribution` świadomie
  `null` do czasu Affect Engine (zakaz fabrykowanych metryk — NEURO_PLAN).
- **`backend/main.py`** — rejestracja routera `integration`.
- **Testy** — `backend/tests/test_integration_summary.py` (5); pełna suita
  **375 passed**. Zweryfikowane end-to-end: System Główny (:8000) pobiera dane
  przez swój rejestr modułów.

---

## 2026-04-06

### Fix: Deployment & Unicode Resolution
- **npm Unicode bug** — Frontend `node_modules` moved to `C:\LinguaAI` (Windows blocks non-ASCII paths during npm install)
- **Backend** — Running from original `G:\...` path (Python handles Unicode correctly) on port **8001** (port 8000 occupied by ForgeBody)
- **Dockerfile.backend** — Fixed: removed `--no-deps`, all dependencies install correctly now (including `click` for uvicorn)
- **vite.config.js** — Updated proxy to use `VITE_API_URL` environment variable (supports Docker/backend port changes)
- **docker-compose.yml** — Added frontend service, changed backend host port to 8001, Ollama port to 11436 (avoid conflicts)
- **Workflow** — App runs locally: Backend (8001) + Frontend (5173) + Ollama (11434)

### Known Issues
- Frontend cannot run from paths with non-ASCII characters on Windows (npm/Node bug) — requires ASCII path or WSL2
- Docker frontend container pending (volume mount Unicode issue)
- Backend API URL hardcoded to localhost:8001 in frontend when running from C:\

---

## 2026-04-05

### Feature: Phase 3 — Video content balance + Model evaluation
- **VIDEOS-1** — Toggle "Tylko język docelowy" vs "Język docelowy + polskie wyjaśnienia" w zakładce Filmy
- **backend/routers/youtube.py** — `_suggest_queries()` accepts `include_polish` flag, generates 2 additional Polish queries when enabled
- **frontend/src/pages/Videos.jsx** — Added toggle button, passes `include_polish` to API
- ~~FEEDBACK.md~~ — AI model evaluation complete: app uses **Ollama** (qwen2.5:7b, llama3.1, deepseek-coder) with task-based routing — optimal free/local stack. **UPDATE 2026-07-24: decyzja porzucona bez wpisu — od 2026-07-13 app używa OpenRouter (płatny, chmurowy); Ollama nie istnieje w kodzie ani docker-compose. Plik FEEDBACK.md zniknął z repo.**
- **.gitignore** — Added logs and temp plugin caches

### Feature: Phase 2 — Learning enhancements
- **READ-1** — Added "Dodaj całe zdanie do fiszek" button in DailyLesson reading section (comprehensible input)
- **NEWS-1** — Daily localStorage cache for news articles (language + user specific keys) to reduce API calls
- **PRONUN-1** — Session summary already present: shows phrases practiced, avg/best scores, problem words, reset button
- **LANG-SWITCH** — Language switching already implemented in Stats.jsx with backend PATCH `/placement/{id}/language`

### Feature: Phase 1 — Core UX improvements
- **VOICE-1** — Speech recognition (Web Speech API) in Conversation: microphone button, transcript appends to input, language auto-detection
- **VOICE-2** — TTS (edge-tts) on AI messages in Conversation: play button on each assistant bubble
- **UI-POLISH** — Fixed English strings: PlacementTest (language display), Videos (placeholder), ErrorReview (lang fallback)
- **TIPS-4** — Daily tips already cached via localStorage (tips_date, tips_data)
- **VOICE-1** — Voice Chat prompt export already exists in Conversation page (generate + editable + copy)

---

## 2026-03-26

### Fix: Audio, UI, Logika zakładek
- **audio_service.py** — retry 3x z backoff dla błędów edge-tts 403
- **achievement_service.py** — wszystkie osiągnięcia przetłumaczone na polski
- **lesson_generator.py** — tipy generowane w native_language (wzmocniony prompt)
- **routers/lessons.py** — concept-flashcards: czytelny błąd gdy AI zwraca 0 konceptów
- **DailyLesson.jsx** — renderMarkdown: obsługa `#`, `##`, `###`, `**bold**`, list
- **DailyLesson.jsx** — dialog: układ lewa/prawa na podstawie pola `speaker`
- **placement.py** — needs_placement: True tylko dla nowych języków (`was_new`)
- **Stats.jsx** — zmiana języka: natychmiastowy reload, czyszczenie lesson cache
- **Stats.jsx** — TodayCompletion: reaktywny useState, odświeżanie na focus
- **DailyTest.jsx** — cache pytań testu w localStorage (nie regeneruje się przy re-wejściu)

---

## Wcześniej (przed 2026-03-26)

Historia commitów w git: `git log --oneline`
