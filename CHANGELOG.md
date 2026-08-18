# CHANGELOG — LinguaAI

Format: newest first. Każdy wpis: wersja (jeśli dotyczy) + data + opis.

---

## 2026-08-09

### feat: zwolnione tempo w ReadAloud + pełny dark-mode pass na Banku wiedzy (`80882fd`)
- **`frontend/src/pages/ReadAloud.jsx`** — `play()` przyjmuje teraz `playbackRate`; dodany
  drugi, mniejszy przycisk (ikona żółwia) obok głównego — odtwarza to samo audio na 0.6x.
  Czysto klienckie (`HTMLMediaElement.playbackRate`), zero kosztu backend/AI.
- **`frontend/src/pages/TopicsPage.jsx`** (783 linii) — zgłoszone przez użytkownika jako
  „ohydne"; root cause: cały plik nie miał ani jednej klasy `dark:`, podczas gdy reszta
  aplikacji jest w pełni theme-aware. W trybie ciemnym renderował się jako białe karty,
  pastelowe odznaki i szare obramowania. Systematyczny przegląd dodający warianty `dark:`
  wszędzie (karty, obramowania, tekst, hover, pola), zgodnie z istniejącą konwencją
  (`.card`, `.badge-*`, `.input-field` z `index.css`). `CATEGORY_COLORS`/`GENDER_COLORS`
  rozszerzone o warianty `dark:bg-X-500/20 dark:text-X-300`.
  Zweryfikowane realnym `getComputedStyle()` w przeglądarce w obu motywach (nie tylko
  wizualnie) — ciemny: `rgb(17,24,39)` kafelek statystyk; jasny: potwierdzono, że istniejący
  ciepły kremowy motyw nie został przy okazji zepsuty.
- Testy: `ReadAloud.test.jsx` +1 (playbackRate faktycznie się zmienia na tym samym `Audio`).
  Frontend suite: 91/91, lint 0 błędów.

### fix: audio lekcji (zła głoska, brak stopu) + zepsute ćwiczenia matching/open-ended (`bf3933e`)
- **`frontend/src/pages/DailyLesson.jsx`** — wyjaśnienie gramatyki jest po polsku (native
  language), ale jego `PlayButton` dostawał `lesson.language` (język docelowy) — polski
  tekst czytany był niemieckim głosem. Teraz pobiera `native_language` przez `getUser(userId)`
  i używa go tylko dla tego przycisku (wszystkie inne `PlayButton` w apce już poprawnie
  czytały treść w języku docelowym — zweryfikowano). Przycisk „Przesłuchaj wyjaśnienie"
  przeniesiony na górę sekcji gramatyki (był na końcu).
- **`frontend/src/components/PlayButton.jsx`** — przepisany o obsługę stopu: nie miał w ogóle
  stanu playing/idle, drugie kliknięcie startowało nakładające się drugie `Audio()` bez
  możliwości wyciszenia pierwszego. Teraz śledzi `isPlaying`, klik podczas odtwarzania
  zatrzymuje (ikona zmienia się na kwadrat stop), sprząta przy unmount/onended/onerror.
- Ćwiczenia matching: model nie ma dedykowanego schematu dla N par, więc upycha je w jednym
  polu jako `"a / b / c"` / `"x | y | z"`; `normalizeExercises` brał to za JEDNĄ parę,
  renderując dwie kolumny surowego, niepodzielonego tekstu w tej samej kolejności (prawa
  kolumna to był już klucz odpowiedzi). Teraz dzieli po `/`/`|` na realne pary, `ExerciseCard`
  tasuje prawą kolumnę i robi realny klik-do-dopasowania (trafiona para zieleni się, błędna
  pulsuje na czerwono).
  `sentence_creation` (i inne ćwiczenia otwarte) było oceniane tym samym prostym
  dopasowaniem substring co luki-do-uzupełnienia, przeciw polu „answer" oznaczonemu
  jawnie jako „Przykład:" — poprawna, twórcza odpowiedź była oznaczana jako błędna. Teraz
  przechodzi przez `evaluateProduction` (ten sam grader AI co sekcja Production Task).
- Testy: `PlayButton.test.jsx` nowy (4 testy — pierwsze pokrycie tego komponentu mimo 8+
  użyć w apce), `DailyLesson.test.jsx` +3.

### fix: `/api/lessons/today` 500 przy równoczesnych żądaniach (błędne zapytanie recovery) (`4af0665`)
- Zgłoszone na żywo przez użytkownika: lekcja „prawie się załadowała" i wyskoczył błąd 500.
  Root cause: React dev mode odpala mount effect dwukrotnie (potwierdzone na żywo w Network —
  `GET /api/lessons/today/3` wywołane dwa razy), a gdy na dany dzień nie ma jeszcze lekcji,
  oba żądania generują treść i ścigają się o INSERT tego samego `(user_id, language,
  day_number)`. Przegrany poprawnie trafia na UNIQUE constraint i wchodzi w istniejący blok
  `except IntegrityError` — ale ten blok szukał wiersza zwycięzcy po `date(created_at) ==
  today` zamiast po `day_number` (realnym kluczu ograniczenia), więc mógł nie znaleźć właśnie
  zacommitowanego wiersza i spadał do gołego `raise`, ujawniając się jako nieobsłużone 500.
- **`backend/routers/lessons.py`** — zapytanie recovery filtruje teraz po
  `Lesson.day_number == day_number` zamiast po dacie utworzenia.
- Test: `backend/tests/test_lessons.py` — nowy
  `test_today_lesson_concurrent_requests_both_succeed`.

### fix: nawigacja pokazuje WSZYSTKIE funkcje z trwałymi etykietami + interpreter w `start.bat` (`3549dad`)
- **`frontend/src/components/NavBar.jsx`** — usunięte `hidden md:block` na etykietach oraz
  poziomo przewijany pojedynczy wiersz (`overflow-x-auto`). Wszystkie 18 funkcji ma teraz
  zawsze widoczną etykietę tekstową, pogrupowane w 5 nazwanych kategorii (Nauka/Ćwiczenia/
  Media/Postępy/Konto, zgodnie z `docs/BACKLOG_UX_2026-08.md` P3-1), zawijające się na
  węższych ekranach zamiast chować się lub wymagać przewijania. Zgłaszane wielokrotnie i
  wcześniej naprawione tylko połowicznie (brakujące strony dodano, ale etykiety wciąż
  znikały poniżej `md`).
- **`start.bat`** — uruchomienie backendu używało gołego `python`, który w tym środowisku
  nie ma zależności projektu (ten sam root cause co 2026-08-05/07) — zmienione na
  `py -3.11`, zgodnie z już poprawnym `start.ps1`.
- Test: `NavBar.test.jsx` +2 (regression-lock — żadna etykieta nie siedzi w elemencie z
  klasą `hidden`, wszystkie 5 nagłówków kategorii się renderuje).

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
