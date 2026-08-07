# LinguaAI — Dokumentacja systemu

Kompletny opis architektury, przepływów i decyzji projektowych. Dla szybkiego
startu zobacz [README.md](../README.md); dla wskazówek pracy z kodem —
[CLAUDE.md](../CLAUDE.md); dla wdrożenia — [deployment.md](deployment.md) i
[PRODUCTION_AND_MOBILE.md](PRODUCTION_AND_MOBILE.md).

_Ostatnia aktualizacja: 2026-08-07 (dodano stronę Settings) · Backend: 457 testów · Frontend: 75 testów._

---

## 1. Czym jest LinguaAI

Jednoosobowa (self-hosted) aplikacja do nauki języków wspierana przez AI, z
polskim interfejsem. Prowadzi ucznia przez pełną pętlę: test poziomujący → plan
nauki → codzienne lekcje → fiszki (powtórki w odstępach) → ćwiczenia → testy →
rozmowa. Adaptuje się do poziomu i słabości, a materiał do powtórek planuje
algorytmem **FSRS v6**.

**Zasada projektowa:** mechanizmy uczenia opierają się na recenzowanych badaniach,
nie na pop-neuronauce. FSRS jest czysty (bez „mnożników" za sen/porę dnia);
telemetria kontekstu jest tylko *zbierana* do analizy, nie modyfikuje harmonogramu.
Każde wywołanie AI ma **hardkodowany fallback**, więc awaria dostawcy nie wywraca
aplikacji, a wydatek na AI jest **jawny i ograniczony**.

---

## 2. Architektura w skrócie

```mermaid
flowchart LR
    subgraph Client["Frontend (React SPA / PWA)"]
        UI[Strony i komponenty]
        SW[Service Worker<br/>cache + push + background sync]
        LS[(localStorage<br/>outbox, cache lekcji)]
        IDB[(IndexedDB<br/>lustro outboxa)]
    end
    subgraph Server["Backend (FastAPI)"]
        MW[Middleware:<br/>v1-alias · gate · rate-limit · CORS]
        R[Routery]
        S[Serwisy]
        AI[gemini_service +<br/>model_router]
        DB[(SQLite / PostgreSQL)]
    end
    Ext[OpenRouter / Gemini]
    UI -->|/api/...| MW --> R --> S --> DB
    S --> AI -->|HTTP| Ext
    SW -. push .- Push[Push service VAPID]
    SW <-. replay .- IDB
```

**Przepływ żądania:** `Router → Service → SQLAlchemy Session (get_db) → DB`.
Warstwa AI jest odizolowana w `gemini_service`; dobór modelu — w `model_router`.

---

## 3. Stack technologiczny

| Warstwa | Technologie |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 (SQLite, gotowe na PostgreSQL) · Pydantic · Alembic |
| AI | OpenRouter (domyślny) lub Google Gemini Direct; `httpx` |
| Uczenie | `fsrs` v6 (powtórki w odstępach) |
| Media | edge-tts (TTS) · faster-whisper `tiny` (ASR) · fpdf2 (PDF) · genanki (Anki) · feedparser (RSS) |
| Powiadomienia | pywebpush (Web Push/VAPID) · Discord webhook (notifier) |
| Frontend | React 19 · React Router 7 · Vite 8 · Tailwind 3 · Axios · lucide-react · vite-plugin-pwa (Workbox) |
| Testy | pytest · Vitest · Playwright (E2E) · fake-indexeddb |

---

## 4. Układ repozytorium

```
backend/
  main.py              # montaż aplikacji, middleware, lifespan (create_all + migracje kolumn)
  config.py            # ustawienia (pydantic-settings, .env)
  database.py          # engine, SessionLocal, Base, get_db
  routers/             # warstwa HTTP (20 routerów)
  services/            # logika domenowa (+ lesson_generator/ jako pakiet)
  models/              # modele SQLAlchemy (11 tabel)
  schemas/             # modele Pydantic (walidacja I/O)
  alembic/             # migracje (env.py czyta DATABASE_URL)
  notifier.py          # standalone scheduler (Discord + Web Push)
  tests/               # 45 plików testowych
frontend/
  src/pages/           # 20 stron (route = funkcja), w tym Settings.jsx (2026-08-06:
                       # przełącznik języka UI + zmiana języka nauki, wcześniej w Stats.jsx)
  src/components/       # Layout, NavBar, OfflineBanner, PushToggle, UnlockGate, ...
  src/api/client.js     # wszystkie wywołania API (axios, interceptor)
  src/utils/            # offlineQueue, outboxDB, push, i18n
  public/               # push-sw.js, sync-sw.js, ikony PWA
docs/                  # ta dokumentacja + wdrożenie/API/mobilka
```

---

## 5. Warstwa AI

Cały kontakt z modelami przechodzi przez **`services/gemini_service.py`**:

- `generate_json(prompt, fallback=None)` — wymusza JSON na poziomie dostawcy
  (OpenRouter `response_format=json_object`, Gemini `responseMimeType`), zdejmuje
  ewentualne znaczniki markdown i parsuje. Na błędzie zwraca `fallback` (o ile
  podany) — graceful degradation.
- `generate_text(prompt)` — surowy tekst.
- `@with_model("<task>")` — dekorator ustawiający model dla danego zadania na
  czas wywołania (async-safe przez `contextvars`).

**Dobór modelu — `services/model_router.py`:**

- Katalog OpenRouter (zweryfikowany wobec `GET /api/v1/models`) w tierach
  `free` / `cheap` / `best`; mapa `zadanie → model` per tier.
- Aktywny tier: `AI_MODEL_TIER` (env). **Cap per-zadanie** (`TASK_TIER_CAP`):
  zadanie może być *ograniczone* do tańszego tieru niż globalny, nigdy podbite.
  Jedyny cap: `news → cheap` (upraszczanie artykułu ≈ tak samo na flash co pro,
  a leci najczęściej).
- Rozstrzyganie: jawny `tier=` > cap > globalny (`_effective_tier`).
- Walidacja katalogu przy starcie (`main.py` lifespan) — literówka w id jest
  głośna, nie cicho degraduje.

Używane zadania: `placement · lesson · conversation · test · news`.

---

## 6. Backend — routery

Wszystkie ścieżki `/api/...`; dodatkowo **każdy endpoint jest osiągalny pod
`/api/v1/...`** (middleware-alias, patrz §12). Wyjątki natywnie na `/api/v1`:
`users`, `voice-chat`, `summary`.

| Router | Prefiks | Odpowiedzialność |
|---|---|---|
| `placement.py` | `/api/v1/placement/` | Tworzenie usera, test CEFR (20 pytań), generowanie planu nauki |
| `lessons.py` | `/api/lessons/` | Lekcja dnia (get/create/next), ukończenie (+25 XP), audio, PDF/Obsidian, koncepcje, i+1 |
| `tests.py` | `/api/tests/` | Test dnia/tygodnia get + submit (XP), test z błędów |
| `flashcards.py` | `/api/flashcards/` | Powtórki FSRS, dodawanie (ręczne/AI/batch), z błędów/tematu, eksport Anki, offline-pack |
| `exercises.py` | `/api/exercises/` | Bank ćwiczeń: practice, answer (+ auto-warianty), stats, generate-variants, offline-pack |
| `conversation.py` | `/api/conversation/` | Sesje rozmowy AI (start/message/analyze), pytania, tłumaczenie |
| `voice_chat.py` | `/api/v1/voice-chat/` | Rozmowa głosowa (prompt + tekst/głos) |
| `stats.py` | `/api/stats/`, `/api/tips/` | XP/poziom, osiągnięcia, leaderboard, błędy, najlepsza pora nauki, tipy |
| `quickmode.py` | `/api/quickmode/` | Plan 15-min, dyktando, „powtórz na głos" |
| `news.py` | `/api/news/` | RSS (feedparser) + upraszczanie AI per CEFR |
| `pronunciation.py` | `/api/pronunciation/` | Transkrypcja faster-whisper + word-level scoring |
| `topics.py` | `/api/topics/` | Tematy jako jednostki FSRS (drzewo, due, review, stats) |
| `push.py` | `/api/push/` | Web Push (VAPID): klucz publiczny, subscribe/unsubscribe, test |
| `users.py` | `/api/v1/users/` | Sen, sync-sleep, eksport/import profilu, magic-link |
| `auth.py` | `/api/auth/`, `/api/v1/users/.../login-link` | Bramka dostępu (unlock → cookie), link logowania |
| `settings.py` | `/api/settings/` | Tłumaczenia UI, Google Drive OAuth |
| `audio.py` | `/api/audio/` | TTS na żądanie |
| `youtube.py` | `/api/youtube/` | Wyszukiwanie filmów (YouTube API) |
| `integration.py` | `/api/v1/summary` | INT-1: read-only podsumowanie dla Systemu Głównego |
| `admin.py` | `/api/admin/` | Backup (ADMIN_API_KEY) |

**Dodanie routera:** zaimportuj w `main.py` i `app.include_router(...)`.

---

## 7. Backend — serwisy (wybór)

| Serwis | Rola |
|---|---|
| `gemini_service` | Jedyny punkt kontaktu z AI (JSON/text, fallbacki) |
| `model_router` | Katalog modeli + mapa zadanie→model + cap tierów |
| `lesson_generator/` | Prompty: placement, plan, lekcja dnia (SCI-2/3/4/7), test, rozmowa, warianty, i+1 |
| `flashcard_service` | Tworzenie fiszek z vocab, successive relearning (SCI-1), semantic spacing (SCI-4) |
| `exercise_service` | Bank: ekstrakcja z lekcji, `build_practice_set`, słabe skille, review FSRS, auto-warianty (błąd/zapamiętanie) |
| `fsrs_service` | Wrapper `fsrs` v6 (`apply_fsrs`) — wspólny scheduler fiszek/ćwiczeń/tematów |
| `test_generator` | Tworzenie/ocena testów, XP (`score×0.5`, max 50), zapis `TestResult` |
| `achievement_service` | XP↔poziom (50 poziomów, `(n-1)²×20`), przyznawanie osiągnięć |
| `streak_service` | Passa (kolejne dni z ukończoną lekcją) + „freezes" |
| `topic_service` | Ekstrakcja tematów z lekcji (background), FSRS tematów |
| `analytics_service` | Najlepsza pora nauki (SCI-5), buckety pór dnia |
| `dictation_service` | Dyktando: diff słów, generowanie zdań |
| `sync_service` | Wspólne `parse_occurred_at` / `already_applied` / `record_event` dla offline |
| `push_service` | Web Push: upsert subskrypcji, wysyłka, kasowanie martwych (404/410) |
| `audio_service` | edge-tts (lekcja, vocab, pakiet ZIP) |
| `pronunciation_service` | faster-whisper `tiny` + scoring |
| `news_service` | RSS + upraszczanie AI |
| `profile_backup` / `backup_service` / `google_drive_service` | Eksport/import profilu (JSON), kopie zapasowe (lokalne/Drive) |
| `pdf_service` / `anki_service` / `obsidian_service` | Eksporty |

---

## 8. System uczenia (pedagogika)

### 8.1 Onboarding
`placement` generuje 20-pytaniowy test CEFR → ocena poziomu → `study_plan`
(zapisany jako JSON w `StudyPlan.plan_data`).

### 8.2 Lekcja dnia
`generate_daily_lesson` tworzy jeden blob JSON z sekcjami (renderowanymi
warunkowo we froncie): **pretest** (SCI-2), warm-up, słownictwo (z etykietą
kategorii semantycznej), gramatyka, ćwiczenia (z `skill_tag`), nota kulturowa,
mówienie, pisanie, wrap-up, **output_forcing** (SCI-7 production effect),
**interleaved_review** (przeplatanie ostatnich tematów).

Lekcja jest generowana **raz dziennie** i zapisywana w `Lesson.content` —
kolejne wejścia tylko ją odczytują (bez regeneracji). Test dnia jest cache'owany
w `lesson.content["daily_test"]` po pierwszej generacji.

### 8.3 Co kształtuje lekcję (adaptacja)
Lekcja adaptuje się **grubą kreską**:
- **słabe tematy** (niska `memory_strength`) → więcej wzmocnienia,
- **mocne tematy** → przeplatanie na wyższym poziomie,
- **ostatnie tematy** → sekcja `interleaved_review` + kontekst „recently studied",
- **znane słownictwo** (fiszki, mastered-first) → materiał i+1,
- **błędy testów** → miękki „nudge" w prompcie.

Świadoma decyzja: **pojedyncze pomyłki w ćwiczeniach NIE trafiają do promptu
lekcji** — precyzyjna remediacja żyje w banku ćwiczeń (§8.5), a lekcja pozostaje
o wprowadzaniu materiału.

### 8.4 Fiszki — FSRS v6
`fsrs` v6 planuje powtórki (samoocena 1–4). Kluczowe:
- **SCI-1 successive relearning:** słowo „opanowane" (`is_mastered`) po 3
  poprawnych przypomnieniach w **odrębnych dniach**; do tego czasu interwał
  capowany (≤2 dni), by karta wracała.
- **SCI-4 semantic spacing:** nowe fiszki z tej samej kategorii dostają rozsunięte
  daty (0,1,2… dni, cap 3), by nie wchodziły do kolejki razem (redukcja
  interferencji).
- Telemetria (`session_type`, `sleep_quality`, `interleaving_bonus`,
  `interference_penalty`) jest **tylko zapisywana** — nie modyfikuje harmonogramu.

### 8.5 Bank ćwiczeń + warianty
Ćwiczenia z każdej lekcji są **zapisywane raz** (`create_exercises_from_lesson`)
i **reużywane** — `build_practice_set` składa zestaw z: (1) zaległych wg FSRS,
(2) przeplatanych z innych tematów, (3) świeżych wariantów dla skilli w potrzebie.
Nic nie jest regenerowane od nowa.

**Auto-tworzenie wariantu** (w `answer_exercise`, tylko na żywej odpowiedzi,
z bezpiecznikiem „nie generuj, jeśli świeże warianty już czekają"):
- **struggle** — seria błędów na skillu (agregatowa celność ≤ 0.5 po ≥3 próbach),
- **mastery** — ćwiczenie widziane ≥4× i odpowiedź poprawna (zapamiętanie
  odpowiedzi, nie reguły; Schmidt & Bjork 1992).

Odpowiedź zwraca `auto_generated` / `auto_generated_reason` (`struggle`|`mastery`)
/ `auto_generated_exercises`; front dokłada je do bieżącej sesji + baner. Wydatek
AI jest jawny i samoograniczający się.

### 8.6 Tematy, testy, XP, osiągnięcia, passa
- **Tematy** to osobne jednostki FSRS (`Topic`), z `memory_strength` napędzającą
  słabe/mocne tematy w lekcji.
- **Testy:** submit liczy XP = `score×0.5` (max 50), zapisuje `TestResult` (błędy
  do analizy).
- **XP/poziom:** ukończenie lekcji +25 XP; 50 poziomów, krzywa `(n-1)²×20` XP.
- **Osiągnięcia:** `check_and_award_achievements` po każdej akcji dającej XP;
  nieodczytane osiągnięcia napędzają toasty w `Layout` (flaga `notified`).
- **Passa:** kolejne dni z ukończoną lekcją, z „freezes" na pojedyncze luki.

### Backlog naukowy (SCI)
SCI-1…SCI-8 zaimplementowane/zamknięte (successive relearning, pretesting, walidator
pokrycia i+1, semantic spacing, najlepsza pora nauki, dyktando, production effect,
feedback korekcyjny — SCI-8 zweryfikowany 2026-08-07 jako już kompletny w
teście/ćwiczeniach/konwersacji). SCI-9/SCI-10 otwarte (integracja z Systemem
Głównym / hipoteza wieczornej konsolidacji) — patrz [NEURO_FEATURES.md](NEURO_FEATURES.md)
i [TASKS.md](../TASKS.md) (propozycje SCI-12…SCI-14).

---

## 9. Model danych (SQLite/PostgreSQL, SQLAlchemy)

| Tabela | Kluczowe kolumny |
|---|---|
| `users` | `name, native_language, target_language, cefr_level, total_xp, streak_days, streak_freezes, language_profiles(JSON), sleep_data(JSON), login_token` |
| `study_plans` | `user_id, language, cefr_level, plan_data(JSON), is_active` |
| `lessons` | `user_id, day_number, title, topic, content(JSON blob — wszystkie sekcje), cefr_level, language, is_completed, completed_at` |
| `flashcards` | `word, translation, example_sentence, audio_path, is_active, isImportant` + FSRS (`difficulty, stability, retrievability, interval_days, repetitions, lapses, fsrs_state, next_review_date, last_review_date`) + SCI-1 (`correct_recall_sessions, last_recall_date, is_mastered`) + telemetria |
| `exercises` | `exercise_type, instruction, prompt, answer, feedback, skill_tag, topic, source_lesson_id, variant_of, times_seen, times_correct` + FSRS |
| `topics` | `name, category, memory_strength, total_items, avg_score` + FSRS; `topic_items` (powiązania lekcja↔temat) |
| `test_results` | `test_type, score, answers(JSON), errors(JSON), cefr_level, language` |
| `conversation_sessions` | `id(UUID), scenario(JSON), system_prompt, history(JSON), language, cefr_level` |
| `achievements` | `achievement_type, unlocked_at, notified` |
| `sync_events` | `client_event_id(unique), kind, target_id, occurred_at` — księga idempotencji offline |
| `push_subscriptions` | `endpoint(unique), p256dh, auth` — subskrypcje Web Push |

Schemat powstaje przez `Base.metadata.create_all` (start) + migracje kolumn w
`main.py`; równolegle dostępny Alembic (§13).

---

## 10. Offline i PWA

**Service Worker** (vite-plugin-pwa, tryb `generateSW`/Workbox) cache'uje
odpowiedzi GET (`StaleWhileRevalidate` dla ćwiczeń/lekcji/fiszek/staty;
`CacheFirst` dla `/audio/*`). Do wygenerowanego SW dołączane są przez
`workbox.importScripts` dwa skrypty z `public/`: `push-sw.js` (§11) i
`sync-sw.js` (background sync).

**Kolejka offline (outbox):** praca wykonana bez sieci (odpowiedź na ćwiczenie,
ocena fiszki, ukończenie lekcji) jest oceniana lokalnie i **kolejkowana**:
- Źródło prawdy: `localStorage` (`utils/offlineQueue.js`). `useOfflineSync`
  drenuje kolejkę przy zdarzeniu `online` i wejściu na ekran (apka otwarta).
- **Lustro w IndexedDB** (`utils/outboxDB.js`), bo Service Worker nie czyta
  localStorage. Każdy enqueue mirroruje zdarzenie i rejestruje **Background Sync**.
- `public/sync-sw.js` na zdarzeniu `sync` odtwarza z IndexedDB przez `fetch` —
  odtwarza kolejkę **nawet gdy apka jest zamknięta** (Chromium). Degradacja: bez
  IndexedDB/SyncManager (Firefox/Safari/iOS) zostaje sync online/focus.

**Gwarancje:** każde zdarzenie niesie `client_event_id`; serwer jest
**idempotentny** (tabela `sync_events`) — powtórka to no-op (`duplicate`).
Znacznik czasu z urządzenia (`answered_at`/`reviewed_at`/`completed_at`) planuje
FSRS/passę od momentu wykonania, nie od powrotu sieci (zegar z przyszłości
przycinany). Ocena lokalna wiernie odwzorowuje serwerowe `grade_answer` (te same
przypadki testowe po obu stronach; JS używa `\p{L}\p{N}` zamiast ASCII `\w`).

**Instalacja jako appka + offline wymagają HTTPS** — lokalnie przez tunel
(Cloudflare) lub wdrożenie. Szczegóły: [PRODUCTION_AND_MOBILE.md](PRODUCTION_AND_MOBILE.md).

---

## 11. Web Push (VAPID)

- Config: `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT`. Puste =
  push wyłączony (jak `DISCORD_WEBHOOK_URL`). Klucze:
  `python -m backend.scripts.generate_vapid_keys`.
- Backend: model `PushSubscription` (upsert po `endpoint`), `push_service`
  (wysyłka przez pywebpush, kasowanie 404/410), router `/api/push/*`.
- Frontend: `PushToggle` na stronie Profil (włącz/wyłącz per urządzenie + test);
  `public/push-sw.js` obsługuje zdarzenia `push` i `notificationclick`.
- Wyzwalanie: `notifier.py` (standalone scheduler, Windows Task Scheduler) wysyła
  push obok Discorda — rano „lekcja", wieczorem „zaległe fiszki".
- **Uwaga:** realne dostarczenie push wymaga HTTPS + prawdziwego push service —
  weryfikowalne tylko na urządzeniu.

---

## 12. Bezpieczeństwo i middleware

Kolejność (od zewnątrz): **v1-alias → rate-limit → gate → CORS → routing**.

- **Alias `/api/v1`:** middleware przepisuje `/api/v1/X` → `/api/X` przed
  routingiem, więc każdy endpoint jest pod v1 bez ruszania dekoratorów. Natywne
  segmenty v1 (`users`, `voice-chat`, `summary`) auto-wykrywane z `app.routes`.
- **Bramka dostępu:** gdy `APP_ACCESS_TOKEN` ustawiony, każde `/api/*` i
  `/audio/*` wymaga sekretu. `POST /api/auth/unlock` wymienia go na ciasteczko
  **HttpOnly** (`secrets.compare_digest`). Otwarte: `/api/health`, `/api/auth/*`.
  Pusty token = bramka wyłączona (localhost bez zmian). **Warunek wystawienia na
  internet** — inaczej obcy czyta/zmienia dane i pali kredyty AI.
- **Rate limit:** 30 żądań / 60 s / IP na endpointy AI (pomijany w testach).
- **CORS:** ograniczony do `ALLOWED_ORIGINS`.

---

## 13. Integracja z ekosystemem (System Główny)

**INT-1** `GET /api/v1/summary` — read-only, bez AI: ujednolicony format
`{module, user_id, date, summary:{lessons_completed, tests_submitted,
reviews_done, due_reviews, mastered_words, streak, total_xp, target_language,
cefr_level}, events, wellbeing_contribution:null}`. Pozostałe kroki integracji
(publisher eventów, dyrektywy, sen przez Affect Engine) — backlog w
[TASKS.md](../TASKS.md).

---

## 14. Konfiguracja (`backend/.env`)

| Zmienna | Znaczenie |
|---|---|
| `AI_PROVIDER` | `openrouter` (domyślny) / `gemini` |
| `AI_MODEL_TIER` | `free` / `cheap` / `best` |
| `OPENROUTER_API_KEY` / `GEMINI_API_KEY` | Klucze dostawców |
| `DATABASE_URL` | `sqlite:///./lingua_ai.db` lub PostgreSQL |
| `APP_ACCESS_TOKEN` | Bramka dostępu (puste = wyłączona) |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web Push |
| `TARGET_LANGUAGE` / `NATIVE_LANGUAGE` | Domyślne języki |
| `DISCORD_WEBHOOK_URL`, `NOTIFY_LESSON_HOUR`, `NOTIFY_REVIEW_HOUR` | Notifier |
| `ALLOWED_ORIGINS`, `ADMIN_API_KEY`, `SECRET_KEY`, `YOUTUBE_API_KEY`, `GDRIVE_*` | Pozostałe |

---

## 15. Uruchamianie

Z **katalogu głównego** (żeby importy `backend.*` się rozwiązały):

```bash
# Backend
uvicorn backend.main:app --reload --port 8001
# Frontend (osobny terminal)
cd frontend && npm install && npm run dev      # :5173, proxy /api i /audio -> :8001
```

Skróty: `start.bat` (CMD) / `start.ps1` (PowerShell). API docs: `http://localhost:8001/docs`.
Frontendowy timeout API: **240 s** (best-tier lekcja/test bywa >110 s).

---

## 16. Migracje bazy (Alembic)

Z katalogu `backend/`. Cel bazy z `DATABASE_URL` (env), fallback do `alembic.ini`
— te same migracje na SQLite lokalnie i PostgreSQL we wdrożeniu.

```bash
cd backend
python -m alembic upgrade head        # zbuduj/zaktualizuj schemat
python -m alembic check               # wykryj dryf modeli vs migracje
python -m alembic revision --autogenerate -m "opis"
python -m alembic stamp head          # bazy sprzed Alembica (schemat już przez create_all)
```

Bazowa migracja `ff1cf77eb17f` + `5a6d111e51d9` (push_subscriptions). `env.py`
importuje wszystkie modele; nowy model dopisz też tam. Szczegóły:
`backend/alembic/README`.

---

## 17. Testy

```bash
python -m pytest backend/tests/ -q     # 457 (jednostkowe + endpointowe, AI mockowane)
cd frontend && npm test                # 75 (Vitest; IndexedDB przez fake-indexeddb)
cd frontend && npx playwright test      # E2E smoke
python -m ruff check backend/           # lint
```

Wzorce: AI jest mockowane (`AsyncMock`), więc testy nie palą kredytów; offline
i idempotencja mają lustrzane przypadki po obu stronach (backend + frontend);
adaptacja lekcji i auto-warianty mają testy przechwytujące prompt/parametry.

---

## 18. Wdrożenie i mobilka

- **Lokalnie na telefonie (Wi-Fi):** `--host 0.0.0.0`, otwórz `http://<IP>:5173`
  (bez instalacji PWA/offline — te wymagają HTTPS).
- **Pełne PWA (HTTPS):** tunel Cloudflare albo chmura — instrukcja krok-po-kroku
  w [PRODUCTION_AND_MOBILE.md](PRODUCTION_AND_MOBILE.md).
- **Chmura:** externalizacja bazy (PostgreSQL przez `DATABASE_URL`), `alembic
  upgrade head` w entrypoincie, CI/CD, obserwowalność, sekrety — backlog w
  [deployment.md](deployment.md) i [TASKS.md](../TASKS.md).

**Zanim wystawisz na internet:** ustaw `APP_ACCESS_TOKEN` (§12) — inaczej API bez
ochrony = wyciek danych i palenie kredytów AI.
