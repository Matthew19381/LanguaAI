# TASKS – LinguaAI

_Ostatnia aktualizacja: 2026-07-23_

---

## 🔴 AUDYT ENDPOINTÓW + ZGODNOŚĆ NEURO (2026-07-23)

_Pełny przegląd: 375 backend testów ✅, 65 frontend ✅, ruff ✅, uvicorn live ✅
(`/api/health` 200, INT-1 `summary` 200/404/422 poprawnie). Werdykt naukowy poniżej._

### Werdykt neuronaukowy (vs `docs/NEURO_FEATURES.md` + `NEURO_PLAN.md`)
- ✅ **Kod jest zgodny z obiema specyfikacjami.** FSRS v6 bez mnożników
  (`fsrs_neuro.py` nie istnieje w backendzie — potwierdzone grepem);
  telemetria `session_type`/`sleep_quality`/`interleaving_bonus`/`interference_penalty`
  jest TYLKO zapisywana (`flashcards.py:277-280`), nic jej nie konsumuje —
  zgodnie z zasadą "zbieranie, nie modulacja".
- ✅ **Anty-wzorce nie wróciły:** zero `loot`/`surprise` w achievement_service,
  zero fabrykowanych liczb w notifierze, zero sztywnych okien godzinowych.
- ✅ **Martwe sekcje WYCZYSZCZONE (2026-07-23):** usunięto z TASKS.md plan
  "Neuro‑naukowe funkcje Faza 2" (NEURO-1…16 z loot boxami, mnożnikami FSRS,
  oknami kortyzolowymi, gesture anchors) oraz macierz priorytetów, MVP 1-4,
  "Analiza kodu", adaptacje DE i "Źródła badań" (Friston/Schultz) — łącznie
  ~186 linii pseudonauki sprzed audytu naukowego. Aktualny backlog naukowy
  to SCI-1…SCI-10 (sekcja PLAN v2 + `docs/NEURO_FEATURES.md`).

### 🔴 Znalezione bugi (6 funkcji client.js woła nieistniejące endpointy)
Zweryfikowane live na uvicornie + w openapi.json — wszystkie 404/405:

- [x] **BUG-1: Voice chat całkowicie zepsuty (zły prefix)** ✅ — client.js:175,178,181
      wołał `/api/voice-chat/*`, router ma `/api/v1/voice-chat/*`. Naprawione
      (3 linie, dodane `v1/`). Zweryfikowane live: `GET /api/v1/voice-chat/prompt/1` → 200.
- [x] **BUG-2: `addXP` cicho połyka 404** ✅ — endpoint `/api/stats/{id}/xp` był
      **celowo usunięty w commicie d339b59 jako backdoor do farmienia XP**
      (test `test_add_xp_endpoint_removed` pilnuje jego nieobecności). Nie
      przywracać! Naprawa = usunięcie martwych wywołań: `addXP` z client.js
      oraz wywołania w News/PronunciationTrainer/Videos (były w `try/catch {}`,
      więc użytkownik nic nie traci — nigdy nie działały).
- [x] **BUG-3: `generateFlashcardsFromErrors` → 404** ✅ — dodany endpoint
      `POST /api/flashcards/generate-from-errors` w flashcards.py: zbiera ostatnie
      błędy z TestResult (max 15, tylko dict-wpisy), buduje prompt z poprawnych
      form, filtruje duplikaty istniejących fiszek. Błąd AI → pusta lista
      (graceful). Testy: 3 w test_missing_endpoints.py.
- [x] **BUG-4: `batchAddFlashcards` → 404** ✅ — dodany endpoint
      `POST /api/flashcards/batch-add`: walidacja Pydantic, dedup po słowie
      per język, pomija puste wiersze. Zweryfikowane live: create=1, retry →
      skipped=1. Testy: 4 w test_missing_endpoints.py.

### ⚠️ Drobne
- [x] `test_language_tutor.db` (176 KB, 0 tabel) w korzeniu repo — usunięty 2026-07-24;
      był już w .gitignore.
- [ ] Alembic: szkielet bez `alembic.ini` — `alembic heads` nie działa
      (schema przez `create_all`, więc bez szkody; martwy katalog).

---

## 🔗 PLAN v2 — INTEGRACJA Z SYSTEMEM GŁÓWNYM (2026-07-19)

_Kontekst: `NEURO_PLAN.md` (ten projekt) + `System-Glowny/MASTER_PLAN.md`.
Werdykt audytu kodu 2026-07-19: **rdzeń jest dobry — nie przerabiać.**
321 testów, FSRS v6, offline-sync z idempotencją, bramka dostępu, świeże audyty
naukowe i logiczne. Braki dotyczą wyłącznie integracji (zero połączenia
z Systemem Głównym) i znanych porządków (audyt modeli A1-A10 poniżej)._

### Integracja (kolejność implementacji)
- [x] **INT-1: `GET /api/v1/summary`** ✅ 2026-07-20 — `backend/routers/integration.py`:
      ujednolicony format `{module, user_id, date, summary:{lessons_completed,
      tests_submitted, reviews_done, due_reviews, mastered_words, streak, total_xp,
      target_language, cefr_level}, events, wellbeing_contribution:null}`.
      Read-only, bez AI. `wellbeing_contribution` świadomie null do czasu Affect
      Engine (bez fabrykowanych metryk). Testy: `test_integration_summary.py` (5);
      cała suita **375 passed**. **Zweryfikowane end-to-end**: System Główny (:8000)
      pobiera realne dane przez rejestr modułów.
- [ ] **INT-2: Publisher eventów** do Systemu Głównego
      (`POST http://localhost:8000/api/v1/integrations/event`, nagłówek
      `X-Module-Key`). Eventy: `lesson_completed`, `review_session_done`,
      `test_submitted`, `sleep_logged`. **Wzorzec: istniejący `sync_service`**
      (kolejka + retry + idempotencja przez `client_event_id`) — nie pisać od zera;
      błąd sieci nigdy nie blokuje UX.
- [ ] **INT-3: `POST /api/v1/directives`** — przyjmowanie dyrektyw:
      `survival_mode` (cel dzienny → 5 min / 1 sesja fiszek),
      `priority` (np. egzamin → więcej powtórek tematu), `quiet_hours`.
      Zapis w DB + odczyt przez Quick Mode/notifier.
- [ ] **INT-4: Sen przez Affect Engine** — `sync-sleep`/dziennik snu LinguaAI
      przestaje być osobnym źródłem: subskrypcja snu z Systemu Głównego
      (jedno źródło prawdy), lokalne endpointy zostają jako fallback offline.
- [ ] **INT-5: Zaległe powtórki → planner dnia** — System Główny odpytuje
      `summary.due_reviews` i wstawia blok powtórek do planu (SCI-9 z NEURO_PLAN).
- [ ] **INT-6: Web Push przez centralny notifier Systemu Głównego** zamiast
      własnego workera VAPID (powiadomienia batched, zgodnie z MASTER_PLAN SG-7).

### Porządki przed/przy integracji
- [ ] Ujednolicenie prefixów API do `/api/v1/*` (dziś mieszanka `/api` i `/api/v1`;
      zrobić z aliasami przejściowymi, żeby nie zepsuć PWA cache).
- [ ] Audyt modeli A1–A10 (sekcja niżej) — minimum A2+A3 przed INT-2 (koszty).
- [ ] **NIE wydzielać jeszcze FSRS jako wspólnej usługi** — to faza 3 MASTER_PLAN;
      LinguaAI pozostaje implementacją referencyjną do tego czasu.

_Źródło: audyt własny + `backend/services/model_router.py`_

---

## ✅ DO SPRAWDZENIA PRZEZ UŻYTKOWNIKA

- [ ] **Test PWA na telefonie przez tunel HTTPS** (instrukcja: `docs/PRODUCTION_AND_MOBILE.md`)
    1. `python -c "import secrets; print(secrets.token_urlsafe(32))"` → wpisz jako `APP_ACCESS_TOKEN` w `backend/.env`
    2. `winget install --id Cloudflare.cloudflared`
    3. backend `--host 0.0.0.0 --port 8001`, frontend `npm run build && npm run preview`, `cloudflared tunnel --url http://localhost:4173`
    4. Na telefonie: otwórz adres `*.trycloudflare.com`, odblokuj tokenem, dodaj do ekranu głównego
    - **Co zweryfikować:** instalacja PWA (ikona), tryb offline fiszek (samolotowy), synchronizacja po powrocie sieci, czytelność na małym ekranie
    - **Pamiętaj:** po teście zamknij tunel (adres jest publiczny — chroni bramka, nie losowość adresu)

---

## 🤖 AUDYT DOBORU MODELI AI (2026-07-19)

_Zakres: `model_router.py`, wszystkie wywołania `@with_model`, ścieżka `gemini_service` → OpenRouter._

### 🔴 Istotne

- [x] **A1. W domyślnym tierze router nie różnicuje modeli** ✅ 2026-07-25 — rozwiązane przez A4: mapa per zadanie (lesson/conversation/news → gemini/claude, test → deepseek/gpt-5, placement → flash-lite/gpt-5-mini). Żadne dwa zadania o różnych wymaganiach nie dzielą już jednego modelu w cheap tierze.
- [x] **A2. Dwa serwisy omijają router** ✅ 2026-07-24 — `news_service.py`
      (`simplify_article`, `_generate_sample_news` → `@with_model("news")`) i
      `topic_service.py` (`extract_topics_from_lesson` → `@with_model("lesson")`)
      wpięte w router. Zamierzony model dla newsów (gemini-2.5-flash) jest
      teraz faktycznie używany.
- [x] **A3. Brak walidacji istnienia modelu → ciche pogorszenie jakości** ✅
      2026-07-24 — `main.py` lifespan waliduje katalog przy starcie (5 zadań ×
      `validate_model()`, log: "Model catalog OK (47 entries)"); `gemini_service`
      loguje nazwę modelu przy błędzie OpenRoutera (`model=%s`).
- [x] **A4. Dobór nie uwzględnia kryterium najważniejszego dla tej aplikacji: jakości generowania w języku docelowym** ✅ 2026-07-25 — mapa per zadanie: lesson/conversation → claude-sonnet-4.6 (best) / gemini-2.5-flash (cheap); test → gpt-5 / deepseek-v3.2; news → gemini-2.5-pro / flash; placement → gpt-5-mini / flash-lite. Tier=best w .env. Szacunek: cheap ~$1.05/mies, best ~$6.48/mies.
- [x] **A5. `deepseek-v3.2` to wariant „thinking"** ✅ 2026-07-24 — cheap tier
      przełączony na `deepseek-v3.2-non-thinking` (placement/lesson/conversation/test
      + domyślny tier); `reasoning` świadomie zostaje na thinking. Szybciej i taniej
      przy tej samej jakości generowania. **UPDATE 2026-07-25:** `deepseek-v3.2-non-thinking`
      **nie istniał na OpenRouter** (wykryte przez A9) — cheap domyślny to teraz
      `google/gemini-2.5-flash`; mapa per zadanie w A4.

### 🟡 Średnie

- [x] **A6. Martwe mapowania zadań** ✅ 2026-07-25 — potwierdzone grepem: używane są tylko `lesson, conversation, test, placement, news`. Dodana stała `USED_TASKS` w model_router (walidacja startowa używa jej zamiast hardkodowanej listy); martwe zadania (`pronunciation`, `code`, `reasoning`, `multimodal`) usunięte z docstringów — mapowania zostają w MAPPINGS jako inertne do czasu pierwszego wywołania.
- [x] **A7. Tier jest globalny** ✅ 2026-07-25 — dodany **cap per-zadanie** `TASK_TIER_CAP` w model_router: zadanie może być *ograniczone* do tańszego tieru niż globalny, nigdy podbite w górę. Rozstrzyganie: jawny `tier=` > cap > globalny (`_effective_tier`, kolejność free<cheap<best). Jedyny cap: `news → cheap` (upraszczanie artykułu ≈ tak samo na flash co pro, a leci najczęściej = jedyny realny driver kosztu). lesson/conversation/test/placement zostają na globalnym best. Testy: `test_model_router.py` (11).
- [x] **A8. Klasyfikacja tierów przez podłańcuch w opisie** ✅ 2026-07-25 — `_tier_of()` parsuje pole `parts[2]` zamiast `"| free " in v`; zero overlapów między tierami (test: free=4, cheap=8, best=5, rozłączne).
- [x] **A9. Katalog niezweryfikowany** ✅ 2026-07-25 — katalog oczyszczony 47 → 17 modeli; wszystkie zweryfikowane skryptem jako ISTNIEJĄCE na OpenRouter (`GET /api/v1/models`). Usunięte 30 martwych id (m.in. `deepseek-v3.2-non-thinking`, `claude-sonnet-4-6` z mylnikiem, `llama-4-*-17b`, 13 martwych `:free`). Walidacja przy starcie (A3) pilnuje regresji.
- [x] **A10. Brak trybu strukturalnego wyjścia** ✅ 2026-07-25 — ścieżki JSON wymuszają teraz JSON na poziomie dostawcy: OpenRouter `response_format={"type":"json_object"}`, Gemini `responseMimeType="application/json"`. Ścieżki `generate_text` bez zmian. Prompt „Respond ONLY with valid JSON" i `_parse_json_response` (zdejmowanie fence'ów + fallback) zostają jako siatka bezpieczeństwa — OpenRouter po cichu pomija param dla modeli bez wsparcia, więc bezpieczne dla całego katalogu (w tym `:free`). Nie wprowadzono per-call schematów (duży zasięg, niski dodatkowy zysk vs json_object). Testy: 6 w `test_gemini_service.py` (kształt payloadu + e2e że JSON wymusza, a text nie).

### 📄 Audyt dokumentacji (po ponownej lekturze wszystkich dokumentów)

- [x] **D1. `ADR-003-account-protection.md` należy do INNEGO PROJEKTU** ✅ 2026-07-24 — usunięty (`git rm`). Treść: circuit breaker tradingowy, alpha decay, MT5 — zero związku z nauką języków.
- [x] **D2. `FEEDBACK.md` nie istnieje** ✅ 2026-07-24 — odniesienia zastąpione: nagłówek TASKS.md → „audyt własny + model_router.py", CHANGELOG 2026-04-05 → przekreślone + UPDATE o porzuceniu Ollamy.
- [x] **D3. Udokumentowana decyzja o modelach po cichu porzucona** ✅ 2026-07-24 — dopisane w CHANGELOG: od 2026-07-13 app używa OpenRouter; Ollama nie istnieje w kodzie ani docker-compose.
- [x] **D4. README opisuje funkcje, których nie ma** ✅ 2026-07-24 — usunięte: modulacja FSRS, gesturalna kotwica, Gemini jako domyślny, „Frontend TODO". Dodane: bank ćwiczeń, dyktando, PWA/offline, bramka, profil JSON, czysty FSRS z telemetrią, 393+65 testów.
- [x] **D5. `docs/deployment.md` prowadzi wprost do niebezpiecznego wdrożenia** ✅ 2026-07-24 — sekcja env zawiera teraz `APP_ACCESS_TOKEN` z generatorem i ostrzeżeniem, że bez niej publiczne API = wyciek danych + palenie kredytów.
- [x] **D6. `deployment.md` każe ustawić `DEBUG=False`** ✅ 2026-07-24 — usunięte (nie istnieje w `config.py`; instrukcja nic nie robiła, a dawała złudzenie zabezpieczenia).

### Proponowana kolejność napraw

0. **D5 + D1** — najpilniejsze: dopisać bramkę do przewodnika wdrożeniowego (inaczej dokumentacja prowadzi do wycieku) i usunąć obcy ADR.
1. **A2 + A3** — najmniejszy koszt, największy zysk: wpiąć brakujące `@with_model`, wołać `validate_model()` przy starcie i logować nazwę modelu przy błędzie (koniec cichego fallbacku).
2. **A1 + A4 + A5** — przemyśleć mapę: inny model do generowania treści językowych, inny do analizy błędów; rozważyć non-thinking do prostych zadań.
3. **A9** — skrypt weryfikujący katalog wobec API OpenRoutera.
4. **A6 + A7 + A8** — sprzątanie: usunąć martwe zadania, dodać tier per-zadanie, zamienić parsowanie opisu na jawne pole.

---

## 🔬 AUDYT SPÓJNOŚCI NAUKOWEJ I LOGICZNEJ (2026-07-18)

_Polecenie: sprawdź spójność logiczną mechanizmów nauki i ich zgodność z badaniami naukowymi; napraw znalezione problemy; zaproponuj nowe funkcje poparte badaniami._

### ✅ Naprawione (9 punktów — commit `72c5f2a`)

**Niespójności logiczne (5):**
1. **`output_forcing` — zahardkodowany niemiecki tekst z błędami dla wszystkich języków.** Każdy użytkownik (nawet uczący się hiszpańskiego) dostawał ten sam niemiecki akapit z polskimi wtrąceniami („Warschau **i** wir", „**często** am **Weekend**"). **Naprawa:** generowany per lekcja w języku docelowym z jej słownictwa; brak sekcji = pomijana (frontend renderuje warunkowo). `backend/services/lesson_generator/daily_lesson.py`.
2. **Sprzeczność w generatorze i+1.** Prompt żądał jednocześnie „10% nowych słów" i „3-5 max" (to 2-5%, nie 10%). **Naprawa:** spójna reguła ≥95% znanych + 3-5 nowych.
3. **`fsrs_neuro.py` — martwy kod z zepsutą matematyką.** Dokumentacja twierdziła, że jest zintegrowany; w rzeczywistości produkcja używa FSRS v6. Stabilność nie rosła w fazie Review (`w[12]=0.0`), interwał `stability × (rating−1)` wymyślony. **Naprawa:** plik + testy usunięte.
4. **Endpointy `neuro-weights` konfigurowały nieistniejący mechanizm.** NEURO-15 (GET/PATCH wag, kolumna `users.neuro_weights`, osiągnięcie `neuro_tuned`, kolumny `gesture_anchor`/`spatial_anchor`) zasilały wyłącznie martwy kod. **Naprawa:** usunięte.
5. **Notifier czytał złą bazę.** `backend/LinguaAI.db` zamiast `lingua_ai.db`. **Naprawa:** lista kandydatów jak w `backup_service`.

**Twierdzenia bez pokrycia w badaniach (4):**
6. **Sfabrykowane liczby w tipach.** „+200% retencji — Ebbinghaus (1885)" i „3× retencja w kontekście — Nation (2001)" — obie zmyślone. **Naprawa:** zastąpione twierdzeniami zgodnymi ze źródłami (`notifier.py`).
7. **Proporcja i+1 „90/10" niezgodna z badaniami.** Pokrycie leksykalne wymaga 95-98% (Hu & Nation 2000; Nation 2006). **Naprawa:** ≥95%/3-5 słów; usunięto pseudonaukowy dopisek „Friston".
8. **Mnożniki „neuro" bez podstaw empirycznych** (okno kortyzolowe, bonus za sen). **Naprawa:** usunięte wraz z `fsrs_neuro.py`; telemetria pozostała jako czyste zbieranie danych.
9. **`NEURO_FEATURES.md` — fałszywy status integracji + pop-neuronauka.** **Naprawa:** przepisany — rzeczywisty status, sekcja funkcji wycofanych, backlog SCI.

**Weryfikacja:** pytest 273 passed (−12 testów martwego kodu), aplikacja importuje się czysto (82 routy).

### 📋 Nowe funkcje poparte badaniami (backlog SCI — do implementacji)

> Każda z cytowaniem recenzowanego źródła. Kolejność = priorytet implementacji.

- [x] **SCI-1 Successive relearning** ✅ — słowo „opanowane" po 3 poprawnych przypomnieniach na odrębnych dniach; do tego czasu interwał FSRS capowany (≤2 dni), by karta wracała na kolejną sesję. _Rawson & Dunlosky (2011)._
    - `backend/services/flashcard_service.py`: czysta funkcja `advance_relearning_criterion` (rating≥3 liczy raz/dzień, rating==1 resetuje, rating==2 neutralny) + stałe `MASTERY_SESSIONS_REQUIRED=3`, `MASTERY_REVIEW_CAP_DAYS=2`.
    - `backend/models/flashcard.py` + migracja w `main.py`: `correct_recall_sessions`, `last_recall_date`, `is_mastered`.
    - `backend/routers/flashcards.py`: wpięte w `review_flashcard`; cap interwału dla niezmasterowanych; `is_mastered`/`correct_recall_sessions` w odpowiedziach + `mastered_count` w liście.
    - `backend/routers/lessons.py`: słowa `mastered` mają pierwszeństwo jako „known vocabulary" dla i+1 (oba miejsca).
    - Testy: `backend/tests/test_successive_relearning.py` (7 testów: kryterium przez daty + integracja).
- [x] **SCI-2 Pretesting** ✅ — 3-5 zgadywanek (multiple-choice) o nowe słowa PRZED lekcją; bez punktów/XP, błędna odpowiedź komunikowana jako pożądana. _Kornell, Hays & Bjork (2009)._
    - `daily_lesson.py`: sekcja `pretest` w promptcie (pkt 0, przed warm-up) + schema JSON; `_sanitize_pretest` waliduje (word ∈ vocabulary, answer ∈ options, ≥2 opcje, max 5); fallback zawiera pretest.
    - `frontend/src/pages/DailyLesson.jsx`: komponenty `PretestCard`/`PretestItem` renderowane przed słownictwem; ujawnienie poprawnej odpowiedzi po wyborze, bez oceny.
    - `frontend/src/i18n/translations.js`: klucze `lesson.pretest*` (PL+EN).
    - Testy: `backend/tests/test_pretest.py` (6 testów sanitizer). Frontend build + 43 testy OK.
- [x] **SCI-3 Walidator pokrycia leksykalnego** ✅ — po wygenerowaniu tekstu i+1 backend mierzy pokrycie i regeneruje (1 próba + max 2 regeneracje) gdy <95%; zwraca najlepszą próbę. _Hu & Nation (2000); Nation (2006)._
    - `daily_lesson.py`: `lexical_coverage(text, known_words)` — pokrycie liczone z markerów `**nowe**` (słowo znane omyłkowo oznaczone jako nowe nie jest karane); stałe `COVERAGE_TARGET=0.95`, `COVERAGE_MAX_REGENERATIONS=2`. Pętla w `generate_iplus1_content` z zaostrzającym się promptem; wynik zawiera `lexical_coverage` i `coverage_attempts`.
    - `routers/lessons.py`: **żywy endpoint** `GET /api/lessons/iplus1/{user_id}` (mastered-first known vocab z SCI-1); eksport funkcji z pakietu.
    - Testy: `backend/tests/test_lexical_coverage.py` (10: metryka + pętla regeneracji + endpoint).
    - _Follow-up:_ dedykowane UI czytania i+1 (backend + endpoint gotowe; frontend renderuje już `comprehensible_input`)._
- [x] **SCI-4 Rozpraszanie podobnych słów** ✅ — nowe fiszki z tej samej kategorii semantycznej dostają rozsunięte `next_review_date` (0,1,2… dni, cap 3) zamiast wchodzić do kolejki razem. _Tinkham (1993); Nakata & Suzuki (2019)._
    - `flashcard_service.py`: czysta funkcja `assign_cluster_offsets(categories)` (case-insensitive, blank=0, cap `SEMANTIC_STAGGER_MAX_DAYS=3`); `create_flashcards_from_vocab` staguje daty per klaster + dedup w obrębie batcha + fallback `example_sentence`.
    - `daily_lesson.py`: pole `category` w słownictwie (prompt + schema JSON) — bez dodatkowego wywołania AI.
    - Testy: `backend/tests/test_semantic_spacing.py` (7: offsety + integracja z DB + dedup).
- [x] **SCI-5 Osobista najlepsza pora nauki** ✅ — analiza skuteczności per pora dnia z realnych, znaczonych czasem wyników testów (nie uniwersalna „szczytowa godzina"); sugestia data-driven. _May & Hasher (1998); Goldstein et al. (2007) — synchrony effect._
    - `services/analytics_service.py`: `bucket_for_hour` (morning/afternoon/evening/night) + `analyze_best_study_time(samples)` — średni wynik per bucket, próg `MIN_SAMPLES=8`, `MIN_PER_BUCKET=3`, zwraca `best_bucket` tylko przy wystarczających danych.
    - `routers/stats.py`: `GET /api/stats/{user_id}/best-study-time` (źródło: `TestResult.created_at`+`score`).
    - `frontend`: `getBestStudyTime` w client.js + karta na stronie Stats (pokazywana tylko gdy `enough_data`); klucze `stats.bestTime*`/`stats.timeBucket.*` (PL+EN).
    - Testy: `backend/tests/test_best_study_time.py` (8: buckety, próg, wybór najlepszego, endpoint 200/404). Frontend build + 43 testy OK.
    - _Uwaga:_ używamy wyników testów (znaczonych czasem), bo pojedyncze powtórki fiszek nie są logowane per-event; telemetria `session_type` na fiszce to tylko ostatnia wartość. Realistyczny próg 8 zamiast 200.
- [x] **SCI-6 Dyktando** ✅ — odsłuch zdania (edge-tts) + zapis ze słuchu, z word-level diffem (correct/wrong/missing/extra) i trafnością. _Nation & Newton (2009)._
    - `services/dictation_service.py`: czysty `diff_transcription` (difflib, normalizacja wielkości liter/interpunkcji) + `generate_dictation_sentences` (AI, fallback offline).
    - `routers/quickmode.py`: `GET /api/quickmode/dictation/{user_id}` (zdania + audio edge-tts, degradacja gdy TTS pada), `POST /api/quickmode/dictation/check`; aktywność „Dyktando" w planie Quick Mode.
    - `frontend`: nowa strona `Dictation.jsx` + route `/dictation` + `getDictation`/`checkDictation` w client.js; odtwarzanie z `audio_path` (nie ujawnia tekstu przed sprawdzeniem); ikona Headphones w QuickMode; klucze `dictation.*` (PL+EN).
    - Testy: `backend/tests/test_dictation.py` (10: diff correct/wrong/missing/extra + endpointy 200/404 + degradacja audio). Frontend build + 43 testy OK.

---

### 🏦 Bank ćwiczeń (2026-07-18) — zapisywanie zamiast regeneracji

**Powód:** ćwiczenia generowane z każdą lekcją ginęły w blobie JSON — nie dało się ich ponownie użyć, wymieszać ani zaplanować. Dodatkowo **test dnia był generowany od nowa przy każdym otwarciu strony** (`get_or_create_daily_test` zwracał `test_id: None` i nic nie zapisywał).

- [x] Model `Exercise` (treść, `skill_tag`, `topic`, `variant_of`, `times_seen`/`times_correct`, pola FSRS) + rejestracja w `main.py` i `conftest.py`
- [x] `exercise_service`: ekstrakcja z lekcji z dedupem, `build_practice_set` (zaległe wg FSRS + przeplatane z innych tematów), `find_weak_skills`, `review_exercise`
- [x] Router `/api/exercises/`: `practice` (bez wycieku odpowiedzi), `answer`, `stats`, `generate-variants`
- [x] `skill_tag` w schemacie ćwiczeń + `generate_exercise_variants` — nowe warianty dla słabych umiejętności (chroni transfer; Schmidt & Bjork 1992)
- [x] **Naprawa marnotrawstwa:** pytania testu dnia cache'owane w `lesson.content["daily_test"]`
- [x] **Frontend:** strona `/practice` — zadanie po zadaniu, ocena + poprawna odpowiedź + feedback, licznik źródeł zestawu (do powtórki / z innych tematów / nowe), podsumowanie sesji; aktywność „Ćwiczenia do powtórki" w Quick Mode (widoczna tylko gdy coś jest zaległe)
- [x] Dogenerowanie na słabe punkty: `include_new=true` w `/practice` (top-up przy chudym banku) + przycisk w podsumowaniu sesji. **Wydatek na AI jest zawsze jawny** — bez `include_new` endpoint nigdy nie woła AI (pokryte testem).
- [x] Słabe umiejętności odświeżane **po** sesji (`GET /stats`), nie z danych sprzed jej rozpoczęcia — inaczej przycisk nie pojawiał się po sesji, która dopiero ujawniła słabość (błąd znaleziony przy weryfikacji w przeglądarce).
- [ ] Automatyczne (bez klikania) dogenerowanie po serii błędów na tej samej umiejętności — dziś wymaga `include_new` lub przycisku

### 📱 PWA / mobilka (2026-07-18) — ZROBIONE

- [x] `vite-plugin-pwa` + service worker (`registerType: autoUpdate`), manifest standalone ze skrótami do `/practice`, `/flashcards`, `/lesson`
- [x] Ikony PNG 192/512 + maskable + apple-touch-icon (wygenerowane z `logo.svg`, `frontend/public/icons/`) + meta iOS w `index.html`
- [x] Cache offline (`workbox.runtimeCaching`): ćwiczenia, lekcje, fiszki, staty (StaleWhileRevalidate) oraz `/audio/*` (CacheFirst, 30 dni)
- [x] `OfflineBanner` — informuje, że dane są z cache i że **zapis wymaga sieci**
- [x] `host: true` w dev + nowa sekcja `preview` z proxy (build też sięga do API)
- [x] **Zweryfikowane na żywo:** przy wyłączonym backendzie `/practice` renderuje komplet zadań z cache (200 z SW)
- [ ] **Web Push (VAPID)** — powiadomienia o powtórkach; wymaga endpointu subskrypcji + workera
- [x] **Offline dla zapisów — ĆWICZENIA** ✅ (2026-07-18): pakiet zadań na urządzeniu + ocena lokalna + kolejka odpowiedzi + synchronizacja po powrocie sieci
    - `GET /api/exercises/{id}/offline-pack` — zadania **z odpowiedziami** (osobny endpoint, żeby różnica wobec `/practice` była jawna; `/practice` nadal ich nie zwraca)
    - `POST /answer` przyjmuje `client_event_id` (idempotencja przez tabelę `sync_events`) i `answered_at` (harmonogram FSRS liczony od momentu odpowiedzi; zegar z przyszłości jest przycinany)
    - `frontend/src/utils/offlineQueue.js`: pakiet w localStorage, outbox z UUID, `syncQueue` (błędy sieci → retry, odrzucenia 4xx → usuwane, żeby nie blokowały kolejki)
    - **Ocena lokalna wiernie odwzorowuje `grade_answer`** — JS `\w` jest ASCII-only, więc użyto `\p{L}\p{N}` (inaczej „schön" oceniałoby się inaczej na urządzeniu niż na serwerze). Te same przypadki testowe po obu stronach.
    - UI: znaczniki „Tryb offline" / „Do wysłania: N", komunikat po synchronizacji, przycisk pobrania pakietu
    - **Zweryfikowane end-to-end:** przy wyłączonym backendzie 3 odpowiedzi ocenione lokalnie (2/3) i zakolejkowane; po restarcie liczniki wzrosły dokładnie o 1, `correct` tylko przy poprawnych; ponowne odtworzenie tego samego zdarzenia → `duplicate: true`, bez zmiany licznika
- [x] **Offline dla FISZEK** ✅ (2026-07-18) — największy wolumen powtórek, więc największy zysk na telefonie
    - `GET /api/flashcards/{id}/offline-pack` — treść kart + `audio_path` (SW pre-cache'uje wymowę) + harmonogram. Fiszki są samooceniane (1–4), więc **offline nie wymaga żadnej logiki oceniania** — w przeciwieństwie do ćwiczeń nie ma ryzyka rozjazdu z serwerem
    - `POST /{id}/review` przyjmuje `client_event_id` + `reviewed_at` (idempotencja + harmonogram od momentu powtórki)
    - `services/sync_service.py`: wspólne `parse_occurred_at` / `already_applied` / `record_event` — ćwiczenia przeniesione na ten sam kod (koniec duplikacji)
    - `hooks/useOfflineSync.js`: **synchronizacja na poziomie całej aplikacji** (w `OfflineBanner`), więc praca offline wysyła się z dowolnego ekranu; wspólny outbox z polem `kind`
    - Baner pokazuje też stan „Wysyłanie postępów: N" po powrocie sieci
    - **Zweryfikowane end-to-end:** przy martwym backendzie 3 karty ocenione offline (Dobra/Jeszcze raz/Dobra) i zakolejkowane; po restarcie kolejka pusta, `reps=1` na każdej karcie, a karta z oceną „Jeszcze raz" ma `lapses=1` (dowód, że ocena przeszła wiernie); ponowne odtworzenie → `duplicate: true`, `reps` bez zmian
- [ ] Offline dla ukończenia lekcji (ten sam wzorzec)
- [ ] Prawdziwy Background Sync API (dziś synchronizacja odpala się przy zdarzeniu `online` i przy wejściu na ekran — wystarcza, ale nie działa gdy aplikacja jest zamknięta)
- [x] **Bramka dostępu** ✅ (2026-07-19) — warunek wystawienia aplikacji na internet
    - Odkrycie: poza `/api/admin/*` **żaden endpoint nie miał uwierzytelnienia**; tunel bez ochrony = obcy może czytać/zmieniać dane i palić kredyty OpenRouter
    - `APP_ACCESS_TOKEN` w configu (pusty = bramka wyłączona, localhost bez zmian); middleware chroni `/api/*` i `/audio/*`, otwarte zostają `/api/health` i `/api/auth/*`
    - `routers/auth.py`: wymiana sekretu na ciasteczko **HttpOnly** (JS go nie trzyma, pliki audio autoryzują się same); `secrets.compare_digest` przeciw atakom czasowym
    - `UnlockGate` na froncie: ekran „Aplikacja zablokowana", token wpisywany raz na urządzenie; dowolny 401 w aplikacji przełącza w stan zablokowany
    - Testy: `backend/tests/test_auth_gate.py` (11)
    - **Zweryfikowane na żywo:** bez tokenu 401 (także `/audio/*`), health otwarty, zły token odrzucony, poprawny odblokowuje i aplikacja działa normalnie
- [x] **Naprawa przy okazji:** interceptor w `client.js` gubił kod statusu HTTP (`new Error(message)`), więc kolejka offline nigdy nie odróżniała trwałego odrzucenia 4xx od błędu sieci — zdarzenia byłyby ponawiane w nieskończoność. Testy tego nie łapały, bo mockowały poster z pominięciem interceptora. Dodane `err.status` + testy na realny kształt błędu i na 401 (zatrzymanie kolejki bez gubienia zdarzeń)
- [ ] **Tunel HTTPS / wdrożenie** — instrukcja gotowa w `docs/PRODUCTION_AND_MOBILE.md`; do wykonania po stronie użytkownika (`winget install Cloudflare.cloudflared`)

### 🧹 Nieaktualne wpisy NEURO (uspójnione 2026-07-18)

- **NEURO-15** (konfigurowalne wagi) — oznaczone wyżej jako ✅, ale **usunięte**: endpointy `neuro-weights`, kolumna `users.neuro_weights` i osiągnięcie `neuro_tuned` konfigurowały martwy kod.
- **NEURO-8** (neuro-FSRS) — **wycofane**, `fsrs_neuro.py` usunięty; jedynym schedulerem jest FSRS v6.
- **NEURO-3** (loot box „dopaminowy") — **odradzone** (pop-neuronauka + wzorce hazardowe); ewentualnie jako zwykła jawna premia XP.
- **NEURO-5 / NEURO-9** — kolumny `gesture_anchor`/`spatial_anchor` usunięte; wrócą razem z faktyczną implementacją tych funkcji.

Szczegóły i uzasadnienia: `docs/NEURO_FEATURES.md` → „Funkcje wycofane i dlaczego".

### 📌 Zgodność z NEURO_PLAN.md (odkryte 2026-07-19)

`NEURO_PLAN.md` (plan ekosystemowy, wcześniej nieczytany) potwierdza i rozszerza backlog:

- ✅ **Zrealizowane SCI-1…SCI-6 to dokładnie „priorytet 1"** z planu — zgodność pełna.
- ✅ **Anty-wzorce z planu = dokładnie to, co usunąłem** w audycie naukowym: zakaz mnożników interwałów za sen/porę dnia, sztywnych okien godzinowych, loot-boxów i fabrykowanych liczb w tipach.
- ℹ️ Plan wskazuje `docs/NEURO_FEATURES.md` jako **wzorzec dla całego ekosystemu** — czyli przepisany przeze mnie dokument pełni rolę standardu poza tym projektem.
- ⚠️ **Kolejność faz w planie jest inna niż wykonana.** Plan: faza 1 = SCI-1…SCI-3, faza 2 = **SCI-8 + SCI-9**, faza 3 = SCI-4…SCI-7 + SCI-10. Zrobiłem SCI-4…SCI-6 przed SCI-8/SCI-9 (nie wiedząc o planie).

**Rozszerzenia z planu, których nie było w backlogu:**

- [~] **SCI-8 Natychmiastowy feedback korekcyjny** _(Metcalfe 2017, META)_ — poprawna odpowiedź + zdanie wyjaśnienia zamiast samego „źle". **W dużej części już działa**: ekran ćwiczeń pokazuje `expected_answer` + `feedback` przy błędzie. Do sprawdzenia: czy testy dzienne i fiszki też dają korekcyjny feedback, czy tylko wynik.
- [ ] **SCI-9 Kolejka powtórek dnia w Systemie Głównym** _(Gollwitzer & Sheeran 2006, META)_ — FSRS publikuje liczbę zaległych → planner wstawia blok powtórek jako implementation intention. Wymaga integracji międzyprojektowej.
- [x] **SCI-7 Production effect** ✅ 2026-07-25 _(MacLeod et al. 2010, RCT)_ —
      etap „Powtórz na głos" w Quick Mode: `GET /api/quickmode/read-aloud/{id}`
      (najnowsze fiszki + cache'owane TTS, `card.audio_path` zapisywane przy
      pierwszym użyciu), strona `/read-aloud` (słuchaj → powiedz głośno → odkryj
      → samoocena, bez rozpoznawania mowy w v1), aktywność w planie (2 min,
      priorytet 3). Testy: `test_read_aloud.py` (6). Zweryfikowane live: endpoint
      zwraca słowo + audio (MP3 10.6 KB, 200); plan mieści się w 20 min
      (news 4→3 min dla bilansu).
- [ ] **SCI-10 Wieczorna konsolidacja** — **jako hipoteza do eksperymentu n-of-1**, nie jako reguła. Zgodne z zasadą, że sen konsoliduje pamięć (META), ale przewaga pory wieczornej u konkretnej osoby wymaga zmierzenia.

### ✅ Backlog SCI: 6/6 ukończone (2026-07-18)

Wszystkie funkcje z audytu spójności naukowej zaimplementowane, przetestowane i wypchnięte. Łącznie ~48 nowych testów backendu (273 → 321). Każda funkcja poparta cytowanym recenzowanym źródłem i zweryfikowana testami jednostkowymi + integracyjnymi.

---

## ✅ Zakończone (wybrane)

- Naprawiono problemy z audio (edge‑tts retry)  
- Dodano przyciski odtwarzania w różnych sekcjach  
- Spolszczono nazwy języków w UI  
- Usunięto niepotrzebne opóźnienia przy zmianie języka  
- Naprawiono liczenie lekcji, cache testów, promirty testowe, obsługę błędów, renderowanie markdowna, nawigację klawiaturą, filtrowanie fiszek, audio fiszek, statystyki ukończenia lekcji lekcji, itp.  
- Wszystkie zadania oznaczone `[x]` w poprzedniej wersji pliku są uznane za zakończone.

---

## 📦 Backlog (do zrobienia)

- [ ] **Unicode/npm permanent fix** – zmiana nazwy katalogu projektu na ścieżkę bez znaków Unicode (np. `G:\\Projects\\LinguaAI`) lub migracja do WSL2, aby umożliwić pełny przepływ Docker/dev  
- [ ] **Docker frontend** – zbudować gotowy kontener frontendu (nginx) i zintegrować z docker‑compose (obecnie tylko backend w Dockerze)  
- [ ] **Testy.exe** – stworzyć zautomatyzowany zestaw testów: pytest (backend API) + Playwright/Cypress (testy UI smoke)  
- [ ] **Dokumentacja użytkownika** – przewodnik „Rozpoczęcie” ze zrzutami ekranu, FAQ (PDF/HTML)  

---

## ⚪️ Otwarte decyzje / wymagające ustalenia

- [ ] **Finalny wybór architektury** – pełna dockerizacja całego stacku vs. lokalne uruchamianie (backend+frontend z różnych ścieżek)  
- [ ] **Ścieżki projektu** – zmiana nazwy katalogu na ASCII (np. `C:\\LinguaAI` lub `G:\\Projects\\LinguaAI`) – rozwiązanie błędu npm Unicode  
- [ ] **Backup DB** – automatyzacja i lokalizacja kopii zapasowych (chmura? lokalny NAS?)  
- [ ] **Framework testów** – wybór (zalecane: pytest + Playwright)  
- [ ] **Format dokumentacji** – PDF vs online README oraz poziom szczegółowości  

## 🔍 Audyt logiczny systemu (2026-07-12)

Przeprowadzono audyt poprawności działania algorytmów i przepływu danych
(FSRS / neuro‑FSRS, XP/poziomy, osiągnięcia, testy, recenzje fiszek).
Wynik: **2 błędy logiczne naprawione, 3 obserwacje (niski priorytet)**.

### ✅ Naprawione błędy logiczne
- **[BUG] `backend/routers/tests.py:123` — operator precedence → 500 na `GET /api/tests/errors/{id}`**
  Stara linia: `if isinstance(err, dict) and err.get("correct_answer") or err.get("correction"):`
  Ewaluuje się jako `(isinstance(...) and err.get(...)) or err.get("correction")`.
  Gdy `err` nie jest dictem (np. plain string / lista z AI) → `AttributeError` na `err.get(...)`
  → łapane przez zewnętrzny `except Exception` → endpoint zwraca **500**.
  **Naprawa:** osobna guarda `if not isinstance(err, dict): continue` przed sprawdzeniem pól.
  Test regresji: `backend/tests/test_tests.py::test_errors_test_handles_non_dict_entries`.
- **[BUG] `backend/services/achievement_service.py:151` — `first_test_perfect` nieosiągalne przy floacie**
  Warunek `t.score >= 100` nigdy się nie odpalał, gdy `analyze_test_errors` zwracał
  score jako float (np. 99.5) — osiągnięcie „Idealny wynik” było martwe.
  **Naprawa:** próg obniżony do `>= 99.5`.

### 📋 Obserwacje (do rozważenia, bez akcji teraz)
- **Duplikacja schedulera FSRS:** `backend/services/fsrs_service.py` (`apply_fsrs`,
  `calculate_memory_strength_fsrs`) jest **martwym kodem** — `review_flashcard` używa
  `neuro_fsrs_next_interval` z `fsrs_neuro.py`. Dwie różne implementacje FSRS w repo
  (uproszczona neuro + pełna `fsrs` lib). Warto ujednolicić lub usunąć martwą ścieżkę.
- **Heurystyka neuro‑FSRS przy `rating == 1` (Again):** w `neuro_fsrs_next_interval`
  `stability` się nie zmniejsza (problem z `w[12]=0.0` w `pow(s, -w[12]) - 1 = 0`).
  Dla uproszczonego modelu akceptowalne, ale warto zweryfikować vs pełna lib `fsrs`.
- **Niespójność wersjonowania API:** `topics` → `/api/topics`, `users` → `/api/v1/users`,
  reszta → `/api/...`. Frontend używa `baseURL: '/api'`, więc działa, ale warto
  ujednolicić prefixy (np. wszędzie `/api/v1`).

### ✅ Weryfikacja
- Backend: **284 passed** (2 nowe testy na errors endpoint)
- Frontend: 43 passed (bez zmian)
- Ruff (F401/F811/F841/F823/F822/F405/F403/F821): czysty

---

## 🔧 Naprawa CI — E2E Tests (Playwright) fail przy "Start backend" (2026-07-13)

**Symptom:** GitHub Actions job `e2e-tests` failował w kroku "Start backend".

**Root cause (główny):** `requirements.txt` zawierał **tylko `alembic==1.13.1`**
(brak fastapi/uvicorn/sqlalchemy/pytest). CI robiło `pip install -r requirements.txt`,
więc `python -m uvicorn backend.main:app` rzucało `ModuleNotFoundError: No module named 'uvicorn'`.
Pełne zależności były poprawnie w `pyproject.toml`, ale CI go nie używało.

**Drugi błąd:** hard-pinned `==` w wygenerowanym requirements (skopiowane z pyproject)
powodowało `ResolutionImpossible` (konflikt `google-genai==1.56.0` vs `httpx==0.27.2`).

**Trzeci (słabość kroku):** `python -m uvicorn ... &` + `sleep 3` bez sprawdzenia
czy backend wstał; proces w tle w GA ginie między krokami → Playwright łączył z martwym backendem.

**Naprawa:**
- `requirements.txt`: wypełniony pełnymi zależnościami z `pyproject.toml`, ale z `>=`
  (instalowalne, brak konfliktów — zweryfikowane w czystym venv).
- `ci.yml`: zamieniono `pip install -r requirements.txt` → `pip install -e .`
  (instaluje z `pyproject.toml`, źródło prawdy, elastyczne wersje).
- `ci.yml`: połączono "Start backend" + "Run E2E" w **jeden step**; backend startuje w tle
  i przetrwa; dodano **health-check loop** (curl `/api/health`, do 30s) z głośnym failem
  jeśli nie wstanie. Playwright nadal sam zarządza frontendem (`webServer: npm run dev`).

**Weryfikacja:**
- `requirements.txt` instalowalny w czystym venv; `uvicorn/fastapi/sqlalchemy/pytest/fsrs` importowalne.
- `ci.yml` YAML poprawny (yaml.safe_load).
- Backend lokalnie wstaje: `/docs` → 200, `/api/health` → `{"status":"healthy"}`.
- Backend pytest: 284 passed (repo bez zmian w kodzie).

---

## 🤖 Model router — podłączenie do OpenRouter (2026-07-13)

Rozpiska modeli (dobrana per-zadanie dla najlepszego generowania) **istnieje**: `backend/services/model_router.py` (katalog 50+ modeli OpenRouter w tierach `free`/`cheap`/`best` + mapowanie `task → model`). Domyślny provider to **OpenRouter** (`config.py: AI_PROVIDER="openrouter"`), zgodnie z wolą użytkownika.

**Błąd (wykryty audytem):** `gemini_service` hardkodował `_OPENROUTER_DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"` — słaby darmowy model, omijający `model_router`. 3 ścieżki wołały `generate_json/text` bez `@with_model`, więc spadały na ten `:free`.

**Naprawa:**
- `gemini_service.py`: `_OPENROUTER_DEFAULT_MODEL` → `_default_openrouter_model()` pobierająca z `model_router._tier_default_openrouter(tier)` (cheap → `deepseek/deepseek-v3.2-non-thinking`).
- `routers/settings.py` (`ui-translations`), `voice_chat.py` (2 endpointy), `youtube.py` (`_suggest_queries`) → dodano `@with_model(...)` (lesson / conversation / news).
- `CLAUDE.md`: poprawiono Environment (OpenRouter zamiast GEMINI_API_KEY domyślnie) + sekcja o `model_router`; poprawiono proxy `/api` (nie `/api/v1`).

**Weryfikacja:**
- `_default_openrouter_model()` → `deepseek/deepseek-v3.2-non-thinking` (brak `:free`) ✓
- pytest: **285 passed** (nowy test `TestDefaultModelResolution` blokuje regresję `:free`) ✓
- Brak cyklu importu (gemini_service ↔ model_router) ✓

---

## 🧹 Lint cleanup — ruff w pełni czysty (2026-07-13)

`ruff check backend/` wcześniej zgłaszał setki błędów (ANN ×120, E501 ×115, B008 ×71, UP, E7xx, W, F401/811/841). Większość to styl, nie błędy.

**Zakres (Opcja 1 — bezpieczna):** naprawiono realne/bezpieczne, resztę zignorowano w configu z uzasadnieniem.

**Zmiany:**
- `pyproject.toml [tool.ruff]`: dodano do `ignore`: `ANN` (brak adnotacji — projekt nie wymusza, ~120 sygnatur), `B008` (FastAPI `Depends()` to standard), `E501` (limit 120 intencjonalny), `E402` (alembic env), `E701` (FastAPI one-liners), `B904`/`E741`/`B017` (styl/niskie ryzyko), `UP`/`E712`/`E711`/`W`/`F541` (styl; **autofix na UP/E zepsuł test logiczny — dlatego tylko ignore, nie --fix**). `per-file-ignores` dla testów: `ANN` + `F841`.
- Usunięto 2 nieprawidłowe `# noqa: BLE-001` (ruff nie ma takiego kodu) w `achievement_service.py` / `test_generator.py`.
- `ruff --fix` tylko na **F401/F811/F841/I** (usunięcie martwego kodu + sort importów, zero mutacji logiki) — 136 plików wyczyszczonych.
- Ręcznie: `main.py` `for table, sql` → `for _, sql` (B007); `achievement_service.py` `except (Exception,):` → `except Exception:` (B013).

**Weryfikacja:**
- `ruff check backend/` → **All checks passed!** ✓
- pytest: **285 passed** (po cofnięciu ryzykownych --fix: UP042 `timezone`→`UTC` zepsuł `test_unnotified_returned_once` — przywrócono) ✓

## 🚀 Produkcja i gotowość mobilna

### ✅ Natychmiastowa naprawa (dev)
- [x] Dodaj skrypt migracji `backend/migrations/add_isimportant_to_flashcard.sql`.  
- [x] Zaktualizuj `backend/main.py`, aby automatycznie dodawał kolumnę `isImportant` przy starcie SQLite.  

### 📦 Przygotowanie do wdrożenia w chmurze
- [ ] **Zewnętrz baza** – polegaj wyłącznie na zmiennej `DATABASE_URL`; usuń wszelkie wbudowane pliki SQLite z Dockerfile.  
- [ ] **Zainicjalizuj i skonfiguruj Alembic** (`alembic init alembic`).  
- [ ] Utwórz bazową migrację (zawiera `isImportant` oraz ewentualne przyszłe zmiany).  
- [ ] Zmodyfikuj punkt wejścia kontenera, aby uruchomił `alembic upgrade head` przed startem Uvicorn.  
- [ ] Dodaj lokalny `docker-compose.override.yml`, który uruchamia usługę PostgreSQL i wskazuje `DATABASE_URL` na nią.  
- [ ] Wybierz dostawcę chmury (AWS RDS, GCP Cloud SQL, Azure Database for PostgreSQL) i przygotuj instancję.  
- [ ] Skonfiguruj CI/CD (GitHub Actions): buduj + testuj + wypychaj obrazy Docker → wdrażaj na wybraną usługę (ECS/Fargate, Cloud Run, Azure Container Apps).  
- [ ] Skonfiguruj obserwowalność: przekieruj stdout/stderr kontenera do logów chmury; opcjonalnie dodaj endpoint `/metrics` (Prometheus).  
- [ ] Skonfiguruj zarządzanie sekretami (AWS Secrets Manager / GCP Secret Manager / Azure Key Vault) dla kluczy API i poświadczeń bazy danych.  
- [ ] Zapewnij strategię zerowego przestoju (ECS rolling update, Cloud Run traffic split, K8s rollingUpdate).  

### 📱 Ulepszenia mobilne / PWA
- [ ] Sprawdź/dodaj `manifest.json` z właściwymi ikonami, `display: "standalone"`.  
- [ ] Zainstaluj `vite-plugin-pwa` i skonfiguruj buforowanie w czasie wykonywania dla `/api/lessons/*` oraz `/api/flashcards/due`.  
- [ ] Przetestuj „Dodaj do ekranu głównego” w Chrome/Android Safari oraz iOS Safari.  
- [ ] Zaimplementuj powiadomienia Web Push oparte na VAPID:  
    - Wygeneruj parę VAPID‑key.  
    - Dodaj endpoint backendu `/api/users/{id}/push-subscription`.  
    - Przechowuj subskrypcję (zaszyfrowaną) powiązaną z użytkownikiem.  
    - Utwórz lekki worker (Cloudflare Workers / Lambda) wysyłający przypomnienia o lekcjach do powtórzenia, seriach, nowych osiągnięciach.  
- [ ] (Opcjonalnie) Dodaj otoczkę Capacitor, jeśli potrzebny dostęp do natywnych funkcji (np. odczyt danych snu z Health Kit/Google Fit):  
    - `npm i @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios`.  
    - Skopiuj zbudowane zasoby webowe do projektu capacitor.  
    - Zintegruj wtyczki: push notifications, health, preferences.  
- [ ] (Opcjonalnie) Opublikuj w Google Play / App Store po pomyślnym zbudowaniu natywnej wersji.  

### 🧪 Testing & QA
- [x] Dodaj test jednostkowy potwierdzający, że pole `isImportant` pojawia się w odpowiedzi GET/POST `/api/flashcards/*`.  
- [x] Dodaj test punktu końcowego `/api/health` zwracający `{status:\"healthy\"}`.  
- [ ] Po gotowości PWA dodaj test Cypress/Playwright sprawdzający buforowanie offline tras lekcji i fiszek.

---

## 🔬 AUDYT KOMPLEKSOWY (2026-07-15)

_Polecenie: przeczytaj wszystkie pliki → audyt logiczny → audyt kodu → zgodność z badaniami o nauce języka → dokumentacja. Przeczytano rdzeń: `main.py`, `config.py`, `achievement_service.py`, `fsrs_service.py`, `fsrs_neuro.py`, `streak_service.py`, `daily_lesson.py`, `test_generator.py`, `flashcard_service.py`, `lessons.py`, `flashcards.py`, `topics.py`, `topic_service.py`, `models/topic.py`, `placement.py`, `conversation.py`, `stats.py`, `tests.py`, `gemini_service.py`, `client.js`._

### 📋 Plan
1. Przeczytaj wszystkie pliki (backend rdzeń + frontend client) — ✅
2. Audyt logiczny (XP/level, FSRS, achievements, flow lekcji, prefixy) — ✅ poniżej
3. Audyt kodu (architektura, duplikacje, bezpieczeństwo, błędy) — ✅ poniżej
4. Zgodność z badaniami naukowymi (SLA, i+1, interleaving, retrieval, output) — ✅ poniżej
5. Dokumentacja funkcji + wpływ na naukę — ✅ sekcja osobna
6. Naprawa krytycznych błędów (achievements, interleaved_review) — ✅ commited
7. Commit + push — ✅

---

### 🧠 Audyt logiczny

#### ✅ Działa poprawnie
- **Krzywa XP/level** (`achievement_service.calculate_level_from_xp`): `(n-1)² × 20`, 50 poziomów — monotoniczna, poprawna. `progress_percent` clampowany 0–100.
- **FSRS dla topics** (`models/topic.py` → `fsrs_service.apply_fsrs`): używa prawdziwej lib `fsrs` (v6), `Card.from_json`/`review_card`. Poprawne mapowanie rating 1–4 → `Rating`.
- **Streak** (`streak_service.calculate_streak`): liczy kolejne dni z ukończoną lekcją, obsługuje `streak_freezes` (mostek 1 dnia = 1 freeze). Logika `gap==2 + freeze` → `+2` dni OK.
- **Idempotencja testów** (`test_generator.submit_test`): blokuje podwójne zgłoszenie tego samego dnia (UNIQUE/date check + rollback na race). XP `score×0.5` max 50 — zgodne z CLAUDE.md.
- **Przypisywanie tematów** (`topic_service`): dedup przez `func.lower(name)`, `assign_item_to_topic` duplicate-safe.
- **Prefixy API**: `users`=`/api/v1/users`, `topics`=`/api/topics`, reszta `/api/*` (nie `/api/v1`). Niespójne, ale frontend (`client.js` baseURL `/api`) jest zgodny ze wszystkimi — więc **nie łamie** niczego w praktyce (tylko estetyka/maintenance).

#### 🔴 BŁĘDY KRYTYCZNE (naprawione w tym commicie)
1. **Achievements są w większości nieosiągalne.** `check_and_award_achievements()` wołane TYLKO w `lessons.py:308` (complete) i `tests.py:88` (submit test). Endpoints przyznające XP — `conversation.py` (XP za rozmowę + analizę tekstu), `news.py`, `pronunciation.py`, `flashcards.py` (review), `placement.py` — **NIE** wołają `check_and_award_achievements`. Skutek: achievements `first_conversation`, `conversations_*`, `first_pronunciation`, `pronunciation_*`, `first_news`, `news_*`, `first_topic`, `topics_*`, `second/third_language`, `flashcards_review_*`, `first_error_review`, `errors_reviewed_50`, `sleep_tracker`, `neuro_tuned` **nigdy się nie odblokowują** (bo `get_stats` tylko czyta tabelę `achievements`, nie wylicza). **Naprawa:** dodano wywołanie `check_and_award_achievements` w `conversation.py` (analyze + analyze-text) i `flashcards.py` (review). Dla `news`/`pronunciation`/topic dodano w odpowiednich routerach (patrz commity).
2. **`interleaved_review` zawsze puste.** `daily_lesson.py:111` hardkoduje `lesson["interleaved_review"] = []`. CLAUDE.md obiecuje, że `generate_daily_lesson(recent_topics=...)` produkuje sekcję "Mixed Review" z poprzednich tematów — ale kod ignoruje `recent_topics` i zwraca `[]`. Frontend renderuje pustą sekcję. **Naprawa:** `generate_daily_lesson` teraz buduje `interleaved_review` z `recent_topics` (2–3 pytania/przypomnienia) gdy `recent_topics` podane.
3. **KRYTYCZNY: niezgodność sygnatur `generate_daily_lesson`.** `lessons.py` wołał `generate_daily_lesson(language=..., study_plan_data=..., user_errors=..., user_vocabulary=..., weak_topics=..., strong_topics=...)` ale sygnatura w `daily_lesson.py` przyjmowała tylko `(user_id, target_language, native_language, cefr_level, recent_topics, day_number, db)`. Na żywo `GET /api/lessons/today/{id}` rzucało `TypeError` (nieznane kwargs) — generowanie lekcji było całkowicie zablokowane. Testy tego NIE łapały (mockują `generate_daily_lesson`). **Naprawa:** rozszerzono sygnaturę `generate_daily_lesson` o opcjonalne parametry RAG (`study_plan_data`, `user_errors`, `user_vocabulary`, `weak_topics`, `strong_topics`) i wpleciono je w prompt (lepsza personalizacja); w `lessons.py` poprawiono `language=` → `target_language=` + dodano `user_id`/`db`.

#### 🟡 BŁĘDY MNIEJSZE (do rozważenia)
- `stats.py:240-243` (CSV export): `streak` nadpisywany per-lekcja, `lesson.completed_at` może być `None` → `AttributeError` przy braku daty. Używa własnej heurystyki zamiast `calculate_streak`.
- `achievement_service.py:182/195/212`: `except (ImportError, Exception)` — `Exception` już łapie wszystko, `ImportError` nadmiarowy (harmless).
- `achievement_service.py:201-204`: `news_flashcards` proxy przez `example_sentence.like('From article:%')` — kruche (zależy od stringu w fiszce, nie od dedykowanej flagi).
- `test_generator.py:118` i `achievement_service.py:328`: `# noqa: BLE-001` — ruff nie ma BLE w select, dyrektywa zbędna (pozostawiona, harmless).
- `flashcards.py:22` importuje `fsrs_neuro` (uproszczona heurystyka) zamiast `fsrs_service` (prawdziwa lib). **Niespójność:** topics mają lepszy scheduler (FSRS v6) niż flashcards (heurystyka). Rekomendacja: przenieść flashcards na `fsrs_service.apply_fsrs` (jak topics).

#### 🟢 Obserwacje (nie błędy)
- `gemini_service` — dodano `fallback` param do `generate_json`/`_parse_json_response` (graceful degradation zgodnie z CLAUDE.md). Wszystkie wywołania `generate_json` już były w `try/except` (serwisy/routery), więc 500 nie występowało, ale fallback czyni to explicite (użyty w helperach flashcards jako `fallback={}`).
- `fsrs_neuro.py` to samodzielna heurystyka NEURO — **od teraz nieużywana w produkcji** (flashcards zmigrowano na `fsrs_service.apply_fsrs` / lib FSRS v6). Plik pozostawiony (testy `test_fsrs_neuro.py`).

---

### ✅ Status napraw luk (2026-07-15, po audycie)
- [x] Achievements nieosiągalne → dodano `check_and_award_achievements` w conversation/flashcards
- [x] `interleaved_review` puste → budowane z `recent_topics`
- [x] Niezgodność sygnatur `generate_daily_lesson` → rozszerzona sygnatura + RAG
- [x] `gemini_service` brak fallbacku JSON → `fallback` param w `generate_json`
- [x] Flashcards `fsrs_neuro` → zmigrowano na `fsrs_service` (FSRS v6), +kolumna `last_review_date` +migracja w `main.py`
- [x] `stats.export_progress_csv` streak → `streak_service.streak_at_date` (usunięcie duplikacji)
- [x] `achievement_service` `except (ImportError, Exception)` → `except Exception` (3 miejsca)

**Weryfikacja:** `ruff check backend/` → All checks passed! · `pytest backend/tests/` → 285 passed.

### 🛠️ Audyt kodu

#### Architektura
- **Router → Service → Session**: przestrzegana. Wyjątek: `lessons.py` zawiera dużo logiki (powinno iść do `lesson_service`). `flashcards.py` miesza router + neuro-FSRS.
- **`with_model` decorator** (`gemini_service`): czysty wzorzec per-task model selection przez `model_router`. Dobre.
- **Circular import**: `gemini_service` importuje `model_router` wewnątrz funkcji — OK. `achievement_service` importuje modele wewnątrz funkcji — OK.

#### Duplikacje
- `flashcards.py` (review) i `topic_service.review_topic` implementują FSRS osobno (neuro vs lib). Duplikacja logiki schedulera.
- `streak_service` i `stats.export_progress_csv` liczą streak niezależnie (różne wyniki!).

#### Bezpieczeństwo
- **CORS**: `allow_credentials=True` z jawną listą originów (z env) — OK.
- **Rate limit**: middleware 30 req/60s na endpointy AI, pomija `TESTING=1` i `OPTIONS` — OK.
- **Auth/autoryzacja**: weryfikacja właściciela (`lesson.user_id != user_id` → 403) w większości routerów — OK. Ale `topics.py:225` sprawdza `if review.user_id and ...` — gdy `user_id` puste, pomija check (CSRF-ish, ale wymaga znajomości topic_id).
- **Sekrety**: `SECRET_KEY`/`ADMIN_API_KEY` ostrzegają w lifespan gdy puste/krótkie — OK. Brak `.env` w repo (gitignore) — OK.
- **SQL injection**: wszędzie SQLAlchemy ORM/parametryzowane — OK.

#### Jakość
- Ruff: czysty (po commicie lint cleanup).
- Testy: 285 backend passed, 43 frontend passed.
- `except Exception` w wielu miejscach bez kontekstu — akceptowalne dla graceful degradation, ale `gemini_service` rzuca surowy `ValueError` zamiast fallbacku.

---

### 🎓 Zgodność z badaniami naukowymi o nauce języka

| Mechanizm | Status | Literatura |
|---|---|---|
| **Spaced Repetition (FSRS)** | 🟡 Częściowo | Topics: FSRS v6 (zgodne z *Muralidharan et al. 2023*, optymalne interwały). Flashcards: heurystyka neuro (przybliżenie, nie kalibrowane). |
| **i+1 Comprehensible Input** | 🟢 Tak | `generate_iplus1_content` wymusza 90% znanych / 10% nowych (Krashen 1985, *Input Hypothesis*). |
| **Interleaving** | 🟡 Częściowo | `interleaved_review` było puste (NAPRAWIONE). NEURO-12 w flashcards liczy bonus za różnorodność tematów (zgodne z *Carpenter et al. 2012*). |
| **Retrieval Practice (testy)** | 🟢 Tak | Daily/weekly testy, `analyze_test_errors` (zgodne z *Karpicke & Roediger 2008*, testing effect). |
| **Output Forcing** | 🟢 Tak | Sekcja `output_forcing` (zakryj/odtwórz) — *active recall* (zgodne z *Bjork desirable difficulties*). |
| **Error Analysis / Feedback** | 🟢 Tak | `analyze_test_errors` + `stats/errors` grupują błędy (zgodne z *Lyster & Ranta 1997*). |
| **Pronunciation (sensory-motor)** | 🟢 Tak | faster-whisper + word-level scoring (zgodne z *Derwing & Munro 2015*). |
| **Sleep Consolidation** | 🟡 Heurystyka | `fsrs_neuro` moduluje przez jakość snu (zgodne z *Diekelmann & Born 2010*), ale niekalibrowane. |
| **Conversation / Negotiation of Meaning** | 🟢 Tak | AI rozmowa z naturalną korektą (Long 1996, *interaction hypothesis*). |
| **Autonomy / Personalizacja** | 🟢 Tak | Study plan z placement (CEFR), per-language profiles. |
| **Gamifikacja (XP/achievements/streak)** | 🟡 Częściowo | Streak/XP motywują (Deci & Ryan SDT), ale **achievements były nieosiągalne** (NAPRAWIONE). |

**Wniosek:** Rdzeń pedagogiczny jest zgodny z literaturą. Główne luki: (1) flashcards FSRS heurystyka zamiast lib, (2) nieosiągalne achievements (naprawione), (3) puste interleaved_review (naprawione).