# ACTION PLAN — LinguaAI

**Data:** 2026-08-09
**Autor:** Claude Code (Sonnet 5) — re-audyt na aktywnej kopii `C:\Projects\LinguaAI` + plan działania
**Cel dokumentu:** jedno źródło prawdy, po którym DOWOLNY model AI (bez pamięci tej rozmowy, bez dodatkowych
pytań do użytkownika) może wykonać pracę na LinguaAI krok po kroku, w kolejności faz, z jasnym kryterium
akceptacji dla każdego zadania.

**Uwaga o poprzedniej wersji:** ten plik **zastępuje** wcześniejszą wersję `ACTION_PLAN.md`, jeśli istniała.
Wcześniejszy audyt, na którym mogła bazować poprzednia wersja, opierał się podejrzanie o nieaktywny klon
(`C:\GoogleDriveSync\Projekty\LinguaAI`). Ten plan bazuje wyłącznie na re-audycie **aktywnej** kopii
`C:\Projects\LinguaAI` (git status czysty, 5 ostatnich commitów zweryfikowanych w historii, testy realnie
uruchomione: **481/481 backend pytest, 91/91 frontend vitest**).

---

## Streszczenie stanu

LinguaAI jest **najdojrzalszym modułem ekosystemu** i wzorcem stacku (Python 3.12, FastAPI, React 19.2,
Router 7.13, Vite 8, Tailwind). Stan techniczny: dobry. 20 routerów, wzorzec Router→Service→Session
w większości przestrzegany (wyjątek: `lessons.py` ma za dużo logiki biznesowej — patrz Faza 2).
Alembic zainicjalizowany (`backend/alembic/`, 2 rewizje: `ff1cf77eb17f_baseline_schema.py`,
`5a6d111e51d9_add_push_subscriptions.py`), ale historyczne zmiany schematu poza tymi dwiema rewizjami
były robione ręcznie (`ALTER TABLE` ad-hoc) — patrz Faza 1 (decyzja: pełne przejście na Alembic).

Zweryfikowane fakty (nie założenia):
- `git status` czysty, branch zgodny z `origin`.
- Backend: `py -3.11 -m pytest backend/tests/ -q` → **481 passed** (uwaga: lokalnie zainstalowany jest
  Python 3.11.9/3.11.15 i 3.14.2, **brak 3.12** — `pyproject.toml` wymaga `>=3.12`, CI (`.github/workflows/ci.yml`)
  poprawnie pinuje `PYTHON_VERSION: "3.12"`; to luka **środowiska developerskiego tej maszyny**, nie repo).
- Frontend: `npm test -- --run` → **91 passed (11 plików testowych)**.
- `frontend/package.json`: `react ^19.2.4`, `react-router-dom ^7.13.1`, `vite ^8.0.0`, `tailwindcss ^3.4.19` —
  dokładnie zgodne ze standardem ekosystemu.
- `pyproject.toml`: `requires-python = ">=3.12"`, FastAPI ≥0.115, SQLAlchemy ≥2.0.35 — zgodne.
- Integracja z System-Głównym: **tylko `GET /api/v1/summary`** istnieje (`backend/routers/integration.py`,
  oznaczone w `TASKS.md` jako `INT-1 ✅ 2026-07-20`). `INT-2` (publisher eventów `POST .../integrations/event`
  z `X-Module-Key`) i `INT-3`..`INT-6` **nie są jeszcze zaimplementowane** — są opisane jako plan w
  `TASKS.md` linie 625-641, ten ACTION_PLAN je operacjonalizuje jako stuby (patrz Faza 3).
- `.env`/`.db` nigdy niecommitowane (`git ls-files | grep -E "\.env$|\.db$"` → puste), `.gitignore` poprawny.
- Realna baza: `C:\Projects\LinguaAI\lingua_ai.db` (864 KB, `backend/config.py`:
  `DATABASE_URL = "sqlite:///./lingua_ai.db"`, uruchamiane z root). Martwy plik-relikt:
  `C:\Projects\LinguaAI\backend\lingua_ai.db` (0 bajtów, 10 lipca) — do usunięcia (Faza 0).

Główne braki (uszeregowane w fazach niżej):
1. Dług dokumentacyjny (stała ścieżka `GoogleDriveSync` w `CLAUDE.md:162` i `:172`, `07_Context/UNIFIED_STANDARDS.md`
   w `CLAUDE.md`, `CHANGELOG.md` nieaktualny od 2026-08-07, `README.md` zaniżona liczba testów, backlog UX
   nieaktualny o zamknięte pozycje).
2. Brak pełnej integracji z System-Głównym (`INT-2`..`INT-6`).
3. Migracje historyczne poza Alembikiem (dług techniczny, ryzyko dryfu schematu).
4. Otwarte pozycje UX z `docs/BACKLOG_UX_2026-08.md` (P1-1, P1-2, P1-5, P1-7, P2-1..P2-4, P3-1..P3-3) —
   P0-1 i P3-1 są już naprawione w kodzie, ale backlog wciąż je opisuje jako otwarte.
5. `ruff` niedostępny lokalnie (nie zweryfikowany w audycie) — do doinstalowania.

---

## Cel projektu i mierzalne kryteria sukcesu

**Cel:** LinguaAI ma być (a) technicznie czystym wzorcem stacku ekosystemu System-Główny, (b) w pełni
zintegrowany z System-Głównym przez udokumentowany kontrakt REST, (c) wolny od rozjazdu
dokumentacja-vs-kod, (d) z rozwiązanymi zgłoszonymi przez użytkownika tarciami UX (backlog P1/P2/P3).

Mierzalne kryteria (sprawdzalne bez interpretacji):

| # | Kryterium | Jak zweryfikować |
|---|---|---|
| K1 | `python --version` w env projektu (venv/CI) = 3.12.x | `py -3.12 -m pytest backend/tests/ -q` przechodzi w całości |
| K2 | Wszystkie testy przechodzą | `pytest backend/tests/ -q` → 0 failed; `npm test -- --run` we `frontend/` → 0 failed |
| K3 | `ruff check backend/` → 0 błędów | uruchomienie po doinstalowaniu `ruff` (Faza 0) |
| K4 | `eslint` we `frontend/` → 0 błędów (ostrzeżenia dopuszczalne, ale policzone i uzasadnione) | `npm run lint` |
| K5 | Zero wzmianek o `C:\GoogleDriveSync\Projekty\LinguaAI` jako lokalizacji roboczej w `CLAUDE.md` | `grep -rn "GoogleDriveSync" CLAUDE.md` → tylko w kontekście backupu bazy (dozwolone), nie jako ścieżka repo/git |
| K6 | `CHANGELOG.md` zawiera wpis dla każdego commitu od ostatniego wpisu do HEAD | `git log --oneline` vs sekcje `CHANGELOG.md` |
| K7 | `docs/BACKLOG_UX_2026-08.md` — P0-1 i P3-1 oznaczone `[x]`/zamknięte | odczyt pliku |
| K8 | Cała historia schematu bazy odtwarzalna przez `alembic upgrade head` na pustej bazie | `alembic downgrade base && alembic upgrade head` bez błędów, tabele = modele SQLAlchemy |
| K9 | `GET /api/v1/summary` nadal zielony (regresja zero) | `pytest backend/tests/test_integration_summary.py -q` |
| K10 | `POST /api/v1/integrations/event` istnieje, przyjmuje `X-Module-Key`, zwraca 401 bez klucza | test integracyjny + `curl`/httpx w testach |
| K11 | `POST /api/v1/directives` istnieje i zapisuje dyrektywy w DB | test integracyjny |
| K12 | Każde zadanie z `docs/BACKLOG_UX_2026-08.md` P1 ma zielone DoD zweryfikowane ręcznie w przeglądarce (opisane w notatce weryfikacyjnej w `TASKS.md`) | manualny test + wpis w `TASKS.md` |
| K13 | Brak plików `.env`/`.db` w `git ls-files` | `git ls-files \| grep -E "\.env$|\.db$"` → puste |
| K14 | Martwy `backend/lingua_ai.db` (0 B) usunięty | `Test-Path backend/lingua_ai.db` → False |

Definition of Done całego planu: wszystkie kryteria K1–K14 spełnione ORAZ wszystkie zadania Faz 0–5 (poniżej)
oznaczone jako zrealizowane w `TASKS.md` z odpowiadającym wpisem w `CHANGELOG.md`.

---

## Architektura docelowa

### Stack (already committed — LinguaAI jest wzorcem, zero downgrade'u)

| Warstwa | Technologia | Wersja | Status |
|---|---|---|---|
| Backend | Python | 3.12 | ⚠️ deklarowane (`pyproject.toml`), brak lokalnie na tej maszynie — patrz Faza 0 |
| Backend | FastAPI | ≥0.115.0 | ✅ |
| Backend | SQLAlchemy | ≥2.0.35 | ✅ |
| Backend | Pydantic-settings | ≥2.5.0 | ✅ |
| Migracje | Alembic | zainicjalizowany, 2 rewizje | ⚠️ niepełne pokrycie historii — Faza 1 |
| Frontend | React | 19.2.4 | ✅ |
| Frontend | React Router | 7.13.1 | ✅ |
| Frontend | Vite | 8.0.0 | ✅ |
| Frontend | Tailwind | 3.4.19 | ✅ |
| Baza danych | SQLite lokalnie (`lingua_ai.db` w root) → PostgreSQL (plan, poza zakresem tego planu) | — | ✅ zgodne z planem ekosystemu |
| Port backend | `:8001` (`backend/config.py`: `BACKEND_URL = "http://localhost:8001"`) | — | ✅ |
| Port frontend dev | `:5173` | — | ✅ |

### Kontrakt integracji z System-Głównym

Źródło prawdy: `C:\Projects\System-Glowny\CLAUDE.md` + `MASTER_PLAN.md` (przeczytane przy tworzeniu tego planu).

1. **`GET /api/v1/summary?user_id=&date=`** (pull, System-Główny → LinguaAI) — **już zaimplementowane**
   (`backend/routers/integration.py`). Zwraca:
   ```json
   {
     "module": "lingua-ai",
     "user_id": 123,
     "date": "2026-08-09",
     "summary": {
       "lessons_completed": 1, "tests_submitted": 1, "reviews_done": 12,
       "due_reviews": 5, "mastered_words": 340, "streak": 14, "total_xp": 2200,
       "target_language": "German", "cefr_level": "B1"
     },
     "events": [],
     "wellbeing_contribution": null
   }
   ```
   `wellbeing_contribution` świadomie `null` — nieuczciwe byłoby fabrykować liczbę bez Affect Engine
   (MASTER_PLAN §0.3, zakaz fabrykowania metryk). **Nie zmieniać tego na wartość liczbową** dopóki
   System-Główny nie ma Affect Engine (MASTER_PLAN Faza 1, pkt 4).

2. **`POST /api/v1/integrations/event`** (push, LinguaAI → System-Główny), nagłówek `X-Module-Key` —
   **nie istnieje jeszcze**, do zbudowania jako stub w Fazie 3 (`INT-2` z `TASKS.md`). System-Główny
   może jeszcze nie mieć odbiorcy tego endpointu gotowego — LinguaAI buduje **klienta** (publisher) już
   teraz, zgodnie z decyzją użytkownika 2026-08-09 ("budować tymczasowe stuby już teraz, nie czekać biernie
   na hub"). Eventy: `lesson_completed`, `review_session_done`, `test_submitted`, `sleep_logged`.
   Wzorzec: `backend/services/sync_service.py` (kolejka + retry + idempotencja przez `client_event_id`,
   funkcje `already_applied()`/`record_event()`) — **rozszerzyć ten wzorzec, nie pisać nowego mechanizmu
   od zera**. Zasada: błąd sieci/timeout nigdy nie blokuje UX użytkownika (fire-and-forget z lokalną
   kolejką retry, np. tabela `outbound_event_queue`).

3. **`POST /api/v1/directives`** (pull na żądanie / push z System-Głównego → LinguaAI) — przyjmowanie
   dyrektyw: `survival_mode` (cel dzienny zredukowany do 5 min / 1 sesji fiszek), `priority` (np. egzamin
   → więcej powtórek danego tematu), `quiet_hours`. Zapis w nowej tabeli DB, odczyt przez Quick Mode i
   notifier. Stub w Fazie 3 (`INT-3`).

4. Poziomy dowodów przy każdej funkcji wpływającej na zachowanie/naukę: **META > RCT > OBS > HIPOTEZA**,
   zakaz fabrykowania statystyk — LinguaAI już to robi wzorcowo w `docs/NEURO_FEATURES.md` i `NEURO_PLAN.md`;
   **utrzymać ten standard przy każdej nowej funkcji** dodawanej w tym planie (P2-1..P2-4).

5. Zakaz dark patterns: karzące streaki, loot-boxy, sztuczna pilność, shaming — LinguaAI już zgodny
   (streak z "freezes", loot-box `NEURO-3` jawnie wycofany z uzasadnieniem w `docs/NEURO_FEATURES.md`).
   **Żadne zadanie w tym planie nie wprowadza takich mechanizmów.**

6. Konwencja commitów: `<type>: co i dlaczego` + lista zmienionych plików z detalami — kontynuować
   dokładnie ten wzorzec z 5 ostatnich commitów.

---

## Fazy działania

Kolejność faz jest wiążąca — Faza N zakłada ukończenie Fazy N-1, chyba że jawnie zaznaczono "niezależne".
Każde zadanie ma unikalny identyfikator `F<faza>-<numer>` do odhaczania w `TASKS.md`.

### Faza 0 — Higiena i blokery natychmiastowe (0.5–1 dzień)

Cel fazy: zero mylących śladów w dokumentacji, środowisko dev gotowe na 3.12, martwe pliki usunięte.
Można wykonać w dowolnej kolejności wewnątrz fazy, ale przed Fazą 1.

**F0-1. Poprawić stałą ścieżkę `GoogleDriveSync` w `CLAUDE.md`**
- Plik: `C:\Projects\LinguaAI\CLAUDE.md`
- Problem: linia ok. 162 (sekcja "Commands"): `All git commands run from `C:\GoogleDriveSync\Projekty\LinguaAI\` (the repo root):` — sprzeczne z linią 7 tego samego pliku ("Kanoniczna ścieżka: `C:\Projects\LinguaAI`") i z realnym stanem repo.
- Akcja: zmienić na `All git commands run from `C:\Projects\LinguaAI\` (the repo root):`. Sprawdzić też
  wzmiankę `07_Context/UNIFIED_STANDARDS.md` w tej samej sekcji ("**Unified Standards**: See
  `07_Context/UNIFIED_STANDARDS.md`...") — zweryfikować, czy ta ścieżka istnieje w `C:\Projects\LinguaAI`
  (`Test-Path 07_Context/UNIFIED_STANDARDS.md`); jeśli nie istnieje, zastąpić poprawnym odniesieniem
  (prawdopodobnie `C:\Projects\System-Glowny\CLAUDE.md` + `MASTER_PLAN.md` pełnią dziś tę rolę) albo usunąć
  zdanie, jeśli nieaktualne.
- Kryterium akceptacji: `grep -rn "GoogleDriveSync" C:\Projects\LinguaAI\CLAUDE.md` zwraca wyłącznie linie
  dotyczące backupu bazy (`backup_to_cloud.ps1` → `C:\GoogleDriveSync\LinguaAI-backup\`), nigdy jako
  lokalizacja repo/git.
- Zależności: brak.

**F0-2. Usunąć martwy plik `backend/lingua_ai.db`**
- Plik: `C:\Projects\LinguaAI\backend\lingua_ai.db` (0 bajtów, relikt z 10 lipca)
- Akcja: `git rm --cached` jeśli przypadkiem śledzony (weryfikacja: `git ls-files | grep lingua_ai.db` powinno
  pokazać tylko ewentualnie root-owy, którego i tak nie ma w gicie), potem fizyczne usunięcie pliku.
  Sprawdzić, czy żaden kod nie tworzy go ponownie przy starcie (`grep -rn "backend/lingua_ai.db\|backend\\\\lingua_ai.db" backend/`) — jeśli jakiś skrypt startowy tworzy plik w złym katalogu, naprawić ścieżkę.
- Kryterium akceptacji: plik nie istnieje po `git status` czystym starcie aplikacji (`start.bat` z roota
  nie odtwarza pliku w `backend/`).
- Zależności: brak.

**F0-3. Doinstalować `ruff` w środowisku dev i zweryfikować `ruff check backend/`**
- Akcja: `pip install ruff` (lub `pip install -e ".[dev]"` z `pyproject.toml`, sekcja `[project.optional-dependencies] dev`), potem `ruff check backend/`.
- Kryterium akceptacji: komenda się wykonuje (nie "not found"); zanotować w `TASKS.md` realny wynik
  (liczbę błędów, jeśli >0 — nie zakładać "0 errors" bez uruchomienia).
- Zależności: brak.

**F0-4. Zainstalować Python 3.12 lokalnie i zweryfikować testy na docelowej wersji**
- Problem: `pyproject.toml` wymaga `>=3.12`, lokalnie dostępne tylko 3.11.9/3.11.15/3.14.2. CI już pinuje
  3.12 poprawnie — to luka środowiska deweloperskiego, nie repo.
- Akcja: zainstalować Python 3.12.x (np. przez `winget install Python.Python.3.12` lub instalator z
  python.org), utworzyć/zaktualizować venv projektu na 3.12, `pip install -r requirements.txt` (lub
  `pip install -e .`), uruchomić `py -3.12 -m pytest backend/tests/ -q`.
- Kryterium akceptacji: 481/481 testów przechodzi na Python 3.12 (liczba może się różnić jeśli w
  międzyczasie dodano testy — kryterium to "0 failed", nie sztywna liczba 481).
- Zależności: brak. Może być wykonane równolegle z F0-1..F0-3.

**F0-5. Zaktualizować `CHANGELOG.md` o wpisy 2026-08-08/2026-08-09**
- Plik: `C:\Projects\LinguaAI\CHANGELOG.md`
- Akcja: dodać sekcje dla 5 ostatnich commitów (`80882fd` dark mode Bank wiedzy, `bf3933e` fix lesson audio,
  `4af0665` fix `/api/lessons/today` 500, `3549dad` fix nav, oraz commit najnowszy jeśli istnieje ponad te 5)
  — format zgodny z istniejącymi wpisami (nagłówek `## YYYY-MM-DD`, potem `### <type>: opis`, potem lista
  zmienionych plików z detalem). Źródło treści: `git log --stat` dla tych commitów + `TASKS.md` (ma już
  pełne opisy tych zmian).
- Kryterium akceptacji: `git log --oneline -5` — każdy z tych commitów ma odpowiadającą sekcję w
  `CHANGELOG.md` z datą i listą plików.
- Zależności: brak.

**F0-6. Poprawić `README.md` — liczba testów**
- Plik: `C:\Projects\LinguaAI\README.md`, linie 63 i 67 (sekcja "## Testy")
- Akcja: zmienić `# Backend (457 testów)` → realną liczbę (uruchomić `pytest backend/tests/ -q` i wziąć
  liczbę z outputu, nie wpisywać na sztywno 481 bez ponownej weryfikacji w momencie edycji — liczba mogła
  urosnąć po Fazie 1-3 tego planu). Podobnie `# Frontend (75 testów, Vitest)` → realną liczbę z
  `npm test -- --run`.
- Kryterium akceptacji: liczby w `README.md` zgodne z faktycznym outputem testów w momencie ostatniej
  edycji tego pliku (rekomendacja: aktualizować to jako ostatni krok całego planu, nie na starcie).
- Zależności: wykonać na końcu (po Fazie 5), nie w Fazie 0 — zostawiam numer F0-6 dla śledzenia, ale
  faktyczne wykonanie odłożyć do checklisty Definition of Done.

**F0-7. Odświeżyć `docs/BACKLOG_UX_2026-08.md` — oznaczyć zamknięte pozycje**
- Plik: `C:\Projects\LinguaAI\docs\BACKLOG_UX_2026-08.md`
- Akcja: P0-1 (klucze/`AI_MODEL_TIER=best` w `.env`) — zweryfikować ponownie `backend/.env` zawiera
  `AI_MODEL_TIER=best` i pozostałe klucze (audyt to potwierdził), oznaczyć sekcję nagłówkiem
  `✅ Zamknięte 2026-08-0X` z krótkim uzasadnieniem. P3-1 (nawigacja `hidden md:block`) — zweryfikować że
  `frontend/src/components/NavBar.jsx` już ma `flex flex-wrap` (zamiast `overflow-x-auto` + `hidden md:block`)
  i 5 kategorii (Nauka/Ćwiczenia/Media/Postępy/Konto — potwierdzone w audycie, linie ok. 264-268), oznaczyć
  jako zamknięte tym samym wzorcem nagłówka.
- Kryterium akceptacji: dokument nie przedstawia jako "otwarte" żadnej pozycji, którą audyt potwierdził
  jako naprawioną w kodzie.
- Zależności: brak.

---

### Faza 1 — Baza danych: pełne przejście na Alembic (2–4 dni)

Cel fazy: cała historia schematu odtwarzalna z Alembica, zero przyszłych ręcznych `ALTER TABLE`.
Decyzja użytkownika 2026-08-09 (wiążąca, nie do kwestionowania): pełne przejście na Alembic.

**F1-1. Audyt rozbieżności między aktualnym schematem bazy a modelami SQLAlchemy**
- Pliki: `C:\Projects\LinguaAI\backend\models\*.py` (11 modeli: `achievement.py`, `conversation_session.py`,
  `exercise.py`, `flashcard.py`, `lesson.py`, `push_subscription.py`, `study_plan.py`, `sync_event.py`,
  `test_result.py`, `topic.py`, `user.py`), `backend\alembic\versions\ff1cf77eb17f_baseline_schema.py`,
  `backend\alembic\versions\5a6d111e51d9_add_push_subscriptions.py`.
- Akcja: `alembic check` (Alembic ≥1.13 ma `alembic check` — porównuje modele z ostatnią rewizją i zgłasza
  dryf). Jeśli `alembic check` niedostępne w zainstalowanej wersji, alternatywa: `alembic revision
  --autogenerate -m "audit_drift"` na kopii bazy i ręczne przejrzenie wygenerowanego diffu — **nie
  aplikować** tej rewizji, to tylko narzędzie diagnostyczne; usunąć plik po przejrzeniu jeśli nie ma
  realnych rozbieżności.
- Kryterium akceptacji: pisemna lista (w `TASKS.md`, nowa sekcja "Alembic — audyt drift") wszystkich pól/
  tabel, które istnieją w bazie SQLite (`lingua_ai.db`) a nie mają odpowiadającej rewizji Alembic, LUB
  potwierdzenie "brak rozbieżności — dwie istniejące rewizje pokrywają cały schemat".
- Zależności: brak (pierwsze zadanie fazy).

**F1-2. Wygenerować brakujące rewizje Alembic dla historycznych zmian ad-hoc**
- Pliki: nowe pliki w `C:\Projects\LinguaAI\backend\alembic\versions\`.
- Akcja: dla każdej rozbieżności znalezionej w F1-1, wygenerować osobną, opisową rewizję
  (`alembic revision --autogenerate -m "<opis_zmiany>"`, np. `add_isImportant_column_to_lessons` —
  nazwa nawiązuje do przykładu z `docs/PRODUCTION_AND_MOBILE.md`, gdzie brakująca kolumna `isImportant`
  była już raz opisanym blokerem). Każdą rewizję ręcznie przejrzeć (autogenerate bywa niedokładny z typami
  SQLite) przed zatwierdzeniem.
- Kryterium akceptacji: `alembic upgrade head` na **pustej** bazie SQLite tworzy schemat identyczny
  (nazwy tabel, kolumn, typów, indeksów) z tym używanym przez aplikację na `lingua_ai.db`. Weryfikacja:
  `alembic downgrade base && alembic upgrade head` w izolowanej kopii bazy testowej, potem porównanie
  `sqlite3 <db> ".schema"` przed/po.
- Zależności: F1-1.

**F1-3. Ustawić politykę: zero ręcznych `ALTER TABLE` od teraz**
- Plik: `C:\Projects\LinguaAI\CLAUDE.md` (dodać sekcję "Migracje bazy danych") + `C:\Projects\LinguaAI\backend\alembic\README`.
- Akcja: dopisać jawną zasadę: każda zmiana modelu w `backend/models/*.py` **musi** iść w parze z
  `alembic revision --autogenerate -m "..."` w tym samym commicie; zakaz `sqlite3`/ręcznych `ALTER TABLE`
  na produkcyjnej bazie poza kontrolowanym `alembic upgrade`.
- Kryterium akceptacji: sekcja istnieje w `CLAUDE.md`, widoczna dla każdej przyszłej sesji AI/dewelopera.
- Zależności: F1-2 (polityka ma sens dopiero gdy historia jest kompletna).

**F1-4. Dodać krok `alembic upgrade head` do sekwencji startowej aplikacji**
- Plik: `C:\Projects\LinguaAI\start.bat`, `C:\Projects\LinguaAI\start.ps1` (i/lub `backend/main.py` lifespan
  jeśli tam jest wygodniej — sprawdzić istniejący `lifespan` handler w `main.py`).
- Akcja: przed uruchomieniem `uvicorn`, wykonać `alembic upgrade head` (idempotentne — no-op jeśli już
  aktualne). Dla baz sprzed Alembica (jeśli taki przypadek istnieje u użytkownika) zachować istniejącą
  wzmiankę o `alembic stamp head` z `TASKS.md` linia 602-603 jako udokumentowaną procedurę ratunkową w
  `backend/alembic/README`.
- Kryterium akceptacji: świeże uruchomienie `start.bat` na czystym sklonowanym repo (pusta baza) kończy się
  działającą aplikacją z pełnym schematem, bez ręcznej interwencji.
- Zależności: F1-2, F1-3.

---

### Faza 2 — Porządki architektoniczne w kodzie (2–3 dni, niezależne od Fazy 1, może iść równolegle)

**F2-1. Wydzielić logikę biznesową z `lessons.py` do serwisu**
- Plik źródłowy: `C:\Projects\LinguaAI\backend\routers\lessons.py` (własne przyznanie długu w `TASKS.md`).
- Akcja: zidentyfikować funkcje w routerze, które robią więcej niż walidację request/response i wywołanie
  serwisu (np. logika generowania/odzyskiwania po `IntegrityError` opisana w fixie `4af0665`, linie 200-219
  — recovery query filtrujący po `Lesson.day_number == day_number`). Przenieść tę logikę do
  `backend/services/lesson_generator.py` lub nowej funkcji w tym module, router ma tylko wołać serwis.
- Kryterium akceptacji: `lessons.py` po zmianie zawiera wyłącznie: parsowanie requestu (Pydantic), wywołanie
  1-2 funkcji serwisowych, mapowanie wyjątków na `HTTPException`. Wszystkie istniejące testy
  `backend/tests/` dot. lekcji (`test_lessons*.py` — sprawdzić realną nazwę pliku w `backend/tests/`)
  przechodzą bez zmian w assercjach (refaktor, nie zmiana zachowania).
- Zależności: brak.

**F2-2. Ujednolicić prefiksy API (dług uznany w `TASKS.md`)**
- Kontekst: `users` pod `/api/v1/users`, `topics` pod `/api/topics`, reszta pod `/api/*`. Middleware w
  `backend/main.py` już przepisuje `/api/v1/X` → `/api/X` (alias, `test_api_v1_alias.py` zielony) — więc
  funkcjonalnie działa, to czysto porządkowy dług.
- Plik: `C:\Projects\LinguaAI\backend\routers\topics.py` (prefix `/api/topics` → docelowo `/api/v1/topics`
  jako natywny prefix, nie tylko alias) i przegląd pozostałych routerów w `backend/routers/` pod kątem
  spójnego `prefix="/api/v1/<resource>"`.
- Akcja: zmienić natywne prefiksy routerów na `/api/v1/*` bezpośrednio; middleware aliasu może zostać jako
  zabezpieczenie wsteczne (nie usuwać, żeby nie złamać ewentualnych zewnętrznych integracji/PWA cache
  wskazanych w `TASKS.md`).
- Kryterium akceptacji: `grep -rn 'prefix="/api/' backend/routers/*.py` pokazuje wyłącznie `/api/v1/...`
  jako natywne prefiksy; `test_api_v1_alias.py` nadal zielony (regresja zero).
- Zależności: brak, ale wykonać PO F2-1 żeby uniknąć konfliktów mergowania w tych samych plikach.

**F2-3. Zweryfikować `ruff check backend/` po F2-1/F2-2 i naprawić realne błędy**
- Akcja: uruchomić `ruff check backend/` (po F0-3) ponownie po refaktorach, naprawić zgłoszone błędy.
- Kryterium akceptacji: `ruff check backend/` → 0 błędów (zanotować w `TASKS.md` faktyczny wynik, nie
  zakładać z góry).
- Zależności: F2-1, F2-2, F0-3.

---

### Faza 3 — Integracja z System-Głównym: `INT-2`, `INT-3` jako stuby (3–5 dni)

Cel fazy: LinguaAI nie czeka biernie na gotowość System-Głównego — buduje klienta/serwer stuby zgodnie z
kontraktem opisanym w `TASKS.md` i `System-Glowny/MASTER_PLAN.md`, gotowe do podłączenia gdy hub będzie
gotowy (System-Głowny Faza 0 wg `MASTER_PLAN.md` — JWT, klucze modułów, Alembic, `.env` — patrz punkt 5
tego dokumentu, "Ryzyka i decyzje otwarte").

**F3-1. `INT-2` — Publisher eventów: tabela kolejki wychodzącej**
- Nowy plik: `C:\Projects\LinguaAI\backend\models\outbound_event.py`
- Akcja: nowy model SQLAlchemy `OutboundEvent` (wzorować na `backend/models/sync_event.py`):
  pola: `id`, `event_type` (enum/str: `lesson_completed`, `review_session_done`, `test_submitted`,
  `sleep_logged`), `payload` (JSON), `client_event_id` (unikalny, idempotencja — ten sam wzorzec co
  `sync_service.already_applied()`), `created_at`, `sent_at` (nullable — `null` = jeszcze niewysłane),
  `attempts` (int, retry counter), `last_error` (nullable str).
- Alembic: `alembic revision --autogenerate -m "add_outbound_event_queue"` (zgodnie z polityką z F1-3).
- Kryterium akceptacji: tabela istnieje po `alembic upgrade head`; model importowalny bez błędów.
- Zależności: Faza 1 (polityka Alembic musi już obowiązywać).

**F3-2. `INT-2` — Serwis publikujący eventy**
- Nowy plik: `C:\Projects\LinguaAI\backend\services\integration_publisher.py`
- Akcja: funkcja `enqueue_event(db, event_type, payload, client_event_id)` — zapisuje do `OutboundEvent`
  (idempotentnie, jak `sync_service.record_event()`). Osobna funkcja/task `flush_pending_events(db)` —
  wysyła `POST {SYSTEM_GLOWNY_URL}/api/v1/integrations/event` z nagłówkiem `X-Module-Key: {MODULE_KEY}`
  dla wszystkich rekordów z `sent_at IS NULL`, oznacza `sent_at`/`attempts`/`last_error` wg wyniku.
  **Zasada twarda**: błąd sieci/timeout/5xx **nigdy nie propaguje wyjątku do wywołującego endpointu
  użytkownika** — `enqueue_event` jest synchroniczne i szybkie (tylko zapis do lokalnej DB), `flush_pending_events`
  jest wywoływane osobno (background task/scheduler, nie w request-response cyklu użytkownika).
- Plik konfiguracyjny: `C:\Projects\LinguaAI\backend\config.py` — dodać `SYSTEM_GLOWNY_URL: str = "http://localhost:8000"`
  i `MODULE_KEY: str = ""` (pusty domyślnie = wysyłka wyłączona, analogicznie do `DISCORD_WEBHOOK_URL`/`VAPID_*`
  — wzorzec "empty = disabled" już ugruntowany w tym pliku).
- Plik: `C:\Projects\LinguaAI\backend\.env.example` — dodać `SYSTEM_GLOWNY_URL=` i `MODULE_KEY=` z komentarzem.
- Kryterium akceptacji: wywołanie `enqueue_event` z pustym `MODULE_KEY` w konfiguracji nie rzuca wyjątku i
  nie próbuje wysyłki sieciowej (analogicznie do istniejącego wzorca push/Discord).
- Zależności: F3-1.

**F3-3. `INT-2` — Podpięcie `enqueue_event` w punktach zdarzeń**
- Pliki do zmiany: `backend/routers/lessons.py` (po zakończeniu lekcji → `lesson_completed`),
  `backend/services/flashcard_service.py` lub `backend/routers/flashcards.py` (po sesji powtórek →
  `review_session_done`), `backend/routers/tests.py` (po zapisaniu wyniku testu → `test_submitted`).
  `sleep_logged` — **pominąć w tej fazie** jeśli LinguaAI nie ma dziś dziennika snu jako osobnej funkcji
  (zweryfikować `grep -rn "sleep" backend/routers/ backend/models/` — jeśli brak, oznaczyć jako
  "poza zakresem, brak źródła danych w LinguaAI" i nie tworzyć fikcyjnego eventu).
- Akcja: w każdym z tych miejsc, po pomyślnym zapisie encji (commit), wywołać `enqueue_event(db, ...)` z
  odpowiednim `payload` (minimalnie: `user_id`, `occurred_at`, istotne pola encji) i deterministycznym
  `client_event_id` (np. `f"lesson_completed:{lesson.id}"` — idempotencja przy retry/podwójnym wywołaniu).
- Kryterium akceptacji: test integracyjny (nowy plik `backend/tests/test_integration_publisher.py`) —
  ukończenie lekcji tworzy dokładnie jeden rekord `OutboundEvent` z `event_type="lesson_completed"`;
  ponowne wywołanie z tym samym `client_event_id` nie duplikuje rekordu.
- Zależności: F3-2.

**F3-4. `INT-2` — Endpoint diagnostyczny kolejki (opcjonalny, ułatwia debug)**
- Plik: `backend/routers/admin.py` (istniejący router admina, ma już wzorzec autoryzacji przez
  `ADMIN_API_KEY` — użyć tego samego mechanizmu).
- Akcja: `GET /api/admin/outbound-events?status=pending|sent|failed` — podgląd stanu kolejki dla debugowania
  integracji, chronione tym samym `ADMIN_API_KEY` co reszta `admin.py`.
- Kryterium akceptacji: endpoint zwraca 401 bez klucza, 200 z listą eventów z kluczem.
- Zależności: F3-1.

**F3-5. `INT-3` — `POST /api/v1/directives` (przyjmowanie dyrektyw z System-Głównego)**
- Nowy plik modelu: `C:\Projects\LinguaAI\backend\models\directive.py` — pola: `id`, `directive_type`
  (`survival_mode`, `priority`, `quiet_hours`), `payload` (JSON — np. dla `priority`: `{"topic_id": ...}`,
  dla `quiet_hours`: `{"start": "22:00", "end": "07:00"}`), `active` (bool), `created_at`, `expires_at`
  (nullable).
- Alembic: nowa rewizja `add_directives_table`.
- Nowy plik routera: `C:\Projects\LinguaAI\backend\routers\directives.py` — `POST /api/v1/directives`
  (przyjmuje `directive_type` + `payload`, autoryzacja przez `X-Module-Key` tak samo jak w F3-2, bo to
  System-Główny → LinguaAI, symetryczny kontrakt), `GET /api/v1/directives/active` (do odczytu przez
  Quick Mode/notifier — wewnętrzne, bez autoryzacji modułowej, tylko sesja użytkownika jak reszta API).
- Podpięcie efektu: `backend/services/streak_service.py` lub `backend/routers/quickmode.py` — gdy istnieje
  aktywna dyrektywa `survival_mode`, cel dzienny redukowany do 5 min/1 sesji fiszek (zweryfikować dokładny
  mechanizm celu dziennego w kodzie przed implementacją — `grep -rn "daily_goal\|survival" backend/`).
- Kryterium akceptacji: `POST /api/v1/directives` z poprawnym `X-Module-Key` zapisuje dyrektywę; bez klucza
  → 401; `GET /api/v1/directives/active` zwraca tylko nieprzedawnione (`expires_at` w przyszłości lub null)
  i `active=true`; test `backend/tests/test_directives.py` (nowy plik) pokrywa te 3 przypadki + efekt na
  Quick Mode.
- Zależności: F3-1 (wzorzec tabeli/Alembic), F1 (polityka migracji).

**F3-6. Aktualizacja `TASKS.md` — oznaczyć `INT-2`, `INT-3` jako zrealizowane (stub)**
- Plik: `C:\Projects\LinguaAI\TASKS.md`, linie 625-634.
- Akcja: zmienić `- [ ] **INT-2...**` i `- [ ] **INT-3...**` na `- [x] ... ✅ <data> (stub — czeka na
  odbiorcę/nadawcę po stronie System-Głównego, patrz ryzyka)`. **Nie oznaczać `INT-4`/`INT-5`/`INT-6` jako
  zrobione** — te zostają poza zakresem tego planu (zależą od Affect Engine i centralnego notifiera, które
  nie istnieją jeszcze po stronie System-Głównego wg `MASTER_PLAN.md` Faza 1-2).
- Kryterium akceptacji: `TASKS.md` odzwierciedla realny stan po F3-1..F3-5.
- Zależności: F3-1..F3-5.

---

### Faza 4 — Backlog UX zgłoszony przez użytkownika (`docs/BACKLOG_UX_2026-08.md`) (5-8 dni)

Kolejność wewnątrz fazy dokładnie wg "Kolejność sugerowana" już ustalonej w `docs/BACKLOG_UX_2026-08.md`
(nie zmieniać bez powodu — to była świadoma decyzja poprzedniej sesji). P0-1 i P3-1 **pominąć** — już
naprawione (zweryfikowane w audycie), zamknięte w F0-7.

**F4-1 (P1-1). Znaki specjalne — fokus i pozycja kursora**
- Plik: `C:\Projects\LinguaAI\frontend\src\pages\DailyLesson.jsx` (`SpecialCharHelper`, ok. linii 1251).
- Akcja: wydzielić `frontend/src/components/SpecialChars.jsx` — wspólny komponent przyjmujący
  `targetRef` (ref pola tekstowego) i `onInsert`. Przycisk znaku: `onMouseDown={e => e.preventDefault()}`
  (zapobiega utracie fokusu), wstawianie znaku w `selectionStart`/`selectionEnd` pola (nie na końcu), po
  wstawieniu ustawić kursor za wstawionym znakiem i przywrócić fokus (`inputRef.current.focus()` +
  `setSelectionRange`).
- Kryterium akceptacji (z backlogu): po kliknięciu znaku fokus zostaje w polu, znak ląduje w miejscu
  kursora, można pisać dalej bez klikania z powrotem w pole. Test manualny w przeglądarce + jeśli możliwe
  test komponentu (Vitest + Testing Library) symulujący klik i sprawdzający `document.activeElement`.
- Zależności: brak.

**F4-2 (P1-2). Znaki specjalne w teście dnia, ćwiczeniach, dyktandzie**
- Pliki: `frontend/src/pages/DailyTest.jsx`, `frontend/src/pages/Practice.jsx`, `frontend/src/pages/Dictation.jsx`
  (zweryfikować dokładne nazwy plików przez `Glob frontend/src/pages/*.jsx` przed edycją — nazwy w tym
  planie pochodzą z audytu i backlogu, mogły się nieznacznie zmienić).
- Akcja: podpiąć `SpecialChars` (z F4-1) pod każde pole odpowiedzi tekstowej w tych trzech ekranach, język
  znaków dobrany z profilu użytkownika (`target_language` — sprawdzić skąd frontend dziś czyta ten profil,
  prawdopodobnie z kontekstu użytkownika/`api/client.js` odpowiedzi).
- Kryterium akceptacji: we wszystkich polach tekstowych do odpowiedzi na tych trzech ekranach widoczny jest
  pasek znaków dla języka docelowego, działający tak samo jak w F4-1.
- Zależności: F4-1.

**F4-3 (P1-3). Ćwiczenia bez treści**
- Backend: `C:\Projects\LinguaAI\backend\services\lesson_generator.py` (i/lub pliki w
  `backend/services/lesson_generator/` — sprawdzić czy to pakiet czy pojedynczy plik, oba istnieją wg
  listingu; prawdopodobnie `lesson_generator.py` to fasada, `lesson_generator/` zawiera submoduły).
- Akcja: w promptcie generacji + walidacji odpowiedzi modelu wymusić, że każde ćwiczenie ma niepuste
  `content` z wyraźną luką (`___`), niepuste `answer`, niepuste `instruction`; przy niekompletnej
  odpowiedzi — retry generacji (z limitem prób, np. 2) zamiast zapisu niekompletnego rekordu.
- Frontend: `frontend/src/pages/DailyLesson.jsx` (`ExerciseCard`, ok. linii 1270) — dodać guard: nie
  renderować ćwiczenia bez `content`/`answer`, pokazać czytelny placeholder ("To ćwiczenie nie wygenerowało
  się poprawnie — pomiń lub wygeneruj ponownie") zamiast pustego pola.
- Kryterium akceptacji: żadne ćwiczenie wyświetlone użytkownikowi nie ma pustej treści; test backendowy
  weryfikujący, że walidacja odrzuca/ponawia niekompletną odpowiedź modelu (mockować odpowiedź AI w
  teście, nie wołać realnego API).
- Zależności: brak, ale logicznie ułatwia weryfikację F4-4 (ta sama ścieżka kodu generacji).

**F4-4 (P1-4). Brak wyjaśnienia gramatyki**
- Plik: `backend/services/lesson_generator.py` (funkcja `generate_daily_lesson` lub jej odpowiednik w
  pakiecie `lesson_generator/`).
- Akcja: zagwarantować niepustą sekcję `explanation` (reguła + 2-3 przykłady + typowe błędy PL→target
  language) w wygenerowanej lekcji; walidacja obecności analogiczna do F4-3 (retry przy pustej sekcji,
  fallback treściowy jeśli retry też zawiedzie — np. szablon generyczny dla danego tematu gramatycznego,
  jawnie oznaczony jako fallback w logach, nie cichy).
- Frontend: `frontend/src/pages/DailyLesson.jsx` (`content.explanation`, ok. linii 557) — potwierdzić że UI
  już poprawnie renderuje tę sekcję gdy niepusta (audyt nie zgłaszał buga UI, tylko brak danych z backendu).
- Kryterium akceptacji: każda nowo wygenerowana lekcja ma niepustą, konkretną sekcję `explanation`; test
  backendowy z mockowanym AI sprawdzający walidację pustej odpowiedzi.
- Zależności: F4-3 (wspólny kod walidacji generacji, sensowniej robić razem lub bezpośrednio po sobie).

**F4-5 (P1-5). Recall (OutputForcingCard) — diff i przycisk "Sprawdź"**
- Plik: `frontend/src/pages/DailyLesson.jsx` (`OutputForcingCard`, ok. linii 1144).
- Akcja: dodać przycisk "Sprawdź": zachować wpisany przez użytkownika tekst (`userRecall`) w stanie
  komponentu (nie czyścić), pod spodem pokazać poprawny tekst referencyjny i diff słowo-po-słowie
  (algorytm: tokenizacja po spacjach/interpunkcji, prosty word-level diff — np. LCS-based, biblioteka nie
  jest konieczna dla krótkich zdań lekcyjnych, można napisać ręcznie ~30-50 linii). Kolorowanie: zielone =
  trafione, czerwone = błędne/brakujące. Nic nie kasować automatycznie po sprawdzeniu.
- Kryterium akceptacji (z backlogu): po kliknięciu "Sprawdź" widać własny tekst + poprawny tekst +
  kolorowe zaznaczenie różnic; wpis użytkownika nie znika w żadnym momencie tego przepływu.
- Zależności: brak.

**F4-6 (P1-6). Test dnia → "przejdź do lekcji" nie generuje nowej lekcji**
- Plik: `frontend/src/pages/DailyTest.jsx` (ok. linii 160, handler `onRetry`).
- Akcja: zmienić nawigację żeby otwierała **istniejącą dzisiejszą** lekcję zamiast generować nową —
  sprawdzić czy istnieje endpoint/query "dzisiejsza lekcja bez auto-generacji" (np.
  `GET /api/lessons/today?generate=false` lub podobny — jeśli nie istnieje, dodać parametr w
  `backend/routers/lessons.py` rozróżniający "pobierz jeśli istnieje" od "wygeneruj jeśli brak", obecne
  zachowanie `/lesson` auto-generuje przy braku "dzisiejszej" — zachować to zachowanie dla normalnego
  wejścia na `/lesson`, ale dodać osobną ścieżkę dla przycisku z `DailyTest.jsx`). Rozdzielić wyraźnie
  "otwórz dzisiejszą" (nowy handler) od "generuj nową" (zostaje jak jest, ale tylko na jawne żądanie
  użytkownika, np. osobny przycisk "Wygeneruj nową lekcję").
- Weryfikacja poboczna: `onRegenerateFromErrors` w tym samym pliku — sprawdzić że nie produkuje
  niekompletnych ćwiczeń (zależność od F4-3 — ten sam mechanizm walidacji generacji powinien to pokrywać).
- Kryterium akceptacji: po teście dnia przycisk "przejdź do lekcji" otwiera dokładnie tę samą dzisiejszą
  lekcję (ten sam `lesson.id` co przed testem); nowa lekcja powstaje wyłącznie po jawnym kliknięciu
  osobnego przycisku "Wygeneruj nową".
- Zależności: F4-3 (dla `onRegenerateFromErrors`).

**F4-7 (P1-7). Dwustanowy Enter w ćwiczeniach**
- Plik: `frontend/src/pages/Practice.jsx`.
- Akcja: handler klawiatury na polu odpowiedzi: pierwszy `Enter` (gdy ćwiczenie niesprawdzone) = wywołuje
  akcję "sprawdź" (ten sam handler co przycisk "Sprawdź"); drugi `Enter` (gdy już sprawdzone, wynik
  widoczny) = wywołuje akcję "następne ćwiczenie". Stan "sprawdzone/niesprawdzone" już musi istnieć w
  komponencie (skoro jest wynik do pokazania) — użyć go jako warunku w handlerze `onKeyDown`.
- Kryterium akceptacji: cały cykl ćwiczeń (odpowiedz → sprawdź → następne → ...) da się przejść wyłącznie
  klawiaturą, bez klikania myszką.
- Zależności: brak.

**F4-8 (P2-1). Fiszki — przebudowa przepływu oceny**
- Plik: `frontend/src/pages/Flashcards.jsx` (816 linii; oceny 1-4 Again/Hard/Good/Easy już istnieją, ok.
  linii 569, ale ukryte do momentu odwrócenia karty i mylące).
- Akcja: przeprojektować przepływ: front karty → przycisk "Pokaż odpowiedź" → tył karty + **4 przyciski
  oceny zawsze widoczne i wyraźne** (z etykietami interwałów FSRS obok, np. "Again (10 min)" — pobrać
  rzeczywisty przewidywany interwał z `backend/services/fsrs_service.py`, nie hardkodować), skróty
  klawiszowe 1-4, licznik "X/Y kart due" widoczny podczas sesji, ekran podsumowania na koniec sesji
  (liczba ocenionych, rozkład ocen). Zachować: audio słowa, przykładowe zdanie, powiązanie z tematem —
  już istnieją, nie usuwać.
- Kryterium akceptacji (z backlogu): użytkownik dla każdej karty świadomie ocenia pamięć (widzi 4 opcje
  bez dodatkowej interakcji poza odwróceniem); FSRS aktualizuje `next_review` (zweryfikować przez test
  backendowy istniejący lub nowy); sesja ma jasny, widoczny koniec.
- Zależności: brak, ale duży zakres — rozważyć podział na PR-y (front karty / ocena / podsumowanie sesji)
  jeśli wykonawca chce mniejszych, weryfikowalnych kroków.

**F4-9 (P2-2). Konwersacja — realna rozmowa + lepszy model**
- Pliki: `frontend/src/pages/Conversation.jsx` (699 linii), `backend/services/model_router.py`,
  `backend/routers/conversation.py`.
- Akcja: (a) `model_router.py` — dodać dedykowany tier/task `"conversation"` mapowany na model wyższej
  jakości niż domyślny `cheap` (dokładny model do wyboru przez wykonawcę wg dostępnych w `model_router.py`
  — **nie fabrykować nazwy modelu bez sprawdzenia co router faktycznie obsługuje**, `grep -rn "tier\|model"
  backend/services/model_router.py` przed edycją); (b) backend: streaming odpowiedzi (SSE lub podobne —
  sprawdzić czy FastAPI + istniejący `httpx`/`google-genai` już wspiera streaming w innych miejscach
  projektu, np. `gemini_service.py`, i wzorować się na tym); (c) frontend: płynny czat turowy z historią
  kontekstu, delikatna korekta błędów w tle (nie przerywająca rozmowy) — zgodnie z zasadą "feedback na
  poziomie zadania, nie osoby" z `MASTER_PLAN.md`. Tryb głosowy zostaje opcjonalny, ale tekstowy ma działać
  bez tarcia jako priorytet.
- Kryterium akceptacji: można prowadzić wielozdaniową, spójną rozmowę w języku docelowym z korektą błędów
  niewybijającą z rytmu rozmowy; manualny test w przeglądarce (min. 5 wymian zdań) + zanotowanie wyniku w
  `TASKS.md`.
- Zależności: brak.

**F4-10 (P2-3). News — zaznaczanie słów w treści**
- Plik: `frontend/src/pages/News.jsx` (ok. linii 171).
- Akcja: klik w dowolne słowo w treści artykułu → podświetlenie (np. zielone tło) + dodanie do panelu
  bocznego/dolnego z tłumaczeniem (użyć istniejącej funkcji `translateWord` — potwierdzić że istnieje
  przez `grep -n "translateWord" frontend/src/pages/News.jsx`); przycisk "Dodaj zaznaczone do fiszek"
  zapisuje zbiorczo wybrane słowa (zamiast obecnego dodawania z gotowej listy `vocabulary`).
  **Uwaga bezpieczeństwa**: tekst artykułu prawdopodobnie już przechodzi przez `dangerouslySetInnerHTML`
  gdzieś w tym komponencie (wzorem `TopicsPage.jsx` z audytu, gdzie był fix XSS) — jeśli klikalne słowa
  wymagają owinięcia w `<span>` wstrzykiwane do HTML, **obowiązkowo** przepuścić przez `escapeHtml()` (ten
  sam wzorzec co w `TopicsPage.jsx`, linie 62-69) przed renderowaniem, żeby nie cofnąć fixa XSS.
- Kryterium akceptacji: dowolne słowo z artykułu można kliknąć, trafia na listę boczną z tłumaczeniem,
  zbiorcze dodanie do fiszek działa; brak regresji XSS (zweryfikować testem z `<script>` w treści newsa,
  jeśli test na `TopicsPage` ma odpowiednik do skopiowania wzorca).
- Zależności: brak.

**F4-11 (P2-4). Bank wiedzy — hierarchia temat→podtemat→mastery (największe zadanie backlogu)**
- Pliki: `frontend/src/pages/TopicsPage.jsx` (783 linii), nowy/rozszerzony model
  `backend/models/topic.py`, nowy endpoint w `backend/routers/topics.py`.
- Akcja (backend): rozszerzyć model tematów o hierarchię (temat główny → podtematy) i powiązania z
  lekcjami/ćwiczeniami/fiszkami (sprawdzić istniejącą strukturę `topic.py` przed projektowaniem — może już
  częściowo istnieć relacja, audyt nie potwierdził ani nie zaprzeczył). Endpoint zwracający drzewo tematów
  z polem `mastery` (%) per węzeł — mastery liczone z danych FSRS/wyników ćwiczeń powiązanych z danym
  tematem (zdefiniować wzór jawnie w kodzie i skomentować, np. średnia ważona `stability`/`retrievability`
  z `fsrs_service.py` dla fiszek powiązanych z tematem — **oznaczyć w `docs/NEURO_FEATURES.md` jako
  OBS/HIPOTEZA odpowiednio do tego, czy wzór ma podstawę empiryczną**, zgodnie ze standardem ekosystemu
  zakazującym fabrykowania metryk bez podstawy). Sprawdzić czy `reviewTopic`/FSRS tematów już implementuje
  cykliczne przepytywanie podstaw (`grep -rn "reviewTopic" backend/ frontend/src/`) — jeśli tak, wyeksponować
  w UI; jeśli nie, dodać harmonogram (np. temat nieodwiedzany >N dni → alert "powtórz podstawy", N do
  ustalenia na podstawie interwałów FSRS tego tematu, nie sztywnej stałej arbitralnej bez uzasadnienia).
- Akcja (frontend): przebudować `TopicsPage.jsx` na widok drzewa: Główny temat → Podtematy → (Ćwiczenia +
  Materiały) z przyciskiem "Rozpocznij naukę" i widocznym % mastery per węzeł.
- Nawigacja: dodać/potwierdzić wejście "Bank wiedzy" w `frontend/src/components/NavBar.jsx` (po F4-może
  już istnieć po P3-1, zweryfikować).
- Kryterium akceptacji: użytkownik widzi drzewo tematów z % opanowania, może wejść w materiały/ćwiczenia
  per podtemat, dostaje sygnał do powtórki podstaw gdy temat "wystygł". Nowe testy backendowe dla
  endpointu drzewa (`backend/tests/test_topics_tree.py` lub podobna nazwa) + manualna weryfikacja UI.
- Zależności: żadne twarde w tym planie, ale to największe zadanie fazy — rozważyć wykonanie jako ostatnie
  w Fazie 4, po mniejszych zadaniach, żeby ewentualne zmiany w modelu `Topic` nie kolidowały z wcześniejszymi
  edycjami innych plików.

**F4-12 (P3-2). Tryb jasny — kremowa paleta zamiast bieli**
- Plik: `frontend/src/index.css` (`body { @apply bg-gray-50 ... }`), oraz wystąpienia `bg-white` na
  powierzchniach kart w całym `frontend/src/`.
- Akcja: wprowadzić ciepłą, niską-kontrastową paletę jasnego motywu — tło ok. `#faf6ec` (kremowe), karty
  lekko jaśniejsze niż tło ale nie czysta biel, tekst ciemnografitowy (nie czarny `#000`). Zaimplementować
  przez zmienne CSS/Tailwind config (`tailwind.config.js` — dodać custom colors) tak, żeby zmiana była
  spójna przez cały frontend, nie punktowe podmiany `bg-white`.
- Kryterium akceptacji (z backlogu): tryb jasny czytelny, nieoślepiający; kontrast tekst/tło zgodny z
  WCAG AA (sprawdzić narzędziem typu axe DevTools lub ręcznym wyliczeniem współczynnika kontrastu ≥4.5:1
  dla tekstu podstawowego).
- Zależności: brak.

**F4-13 (P3-3). Dzienne wskazówki powiązane z bieżącą nauką**
- Plik: `backend/routers/stats.py` (`get_daily_tips` → `generate_daily_tips`).
- Akcja: przekazać do generacji wskazówek: ostatnie tematy użytkownika, ćwiczenia/fiszki o niskim mastery,
  ostatnie błędy (źródło danych: te same tabele co reszta analityki — `test_result.py`, `flashcard.py`,
  ewentualnie nowy widok z F4-11 jeśli gotowy). Wskazówki generowane przez AI mają jawnie odnosić się do
  tych konkretnych danych w promptcie (nie generyczne "ćwicz więcej").
- Kryterium akceptacji: wskazówki wyraźnie nawiązują do aktualnych tematów/słabych punktów danego
  użytkownika — zweryfikować manualnie na koncie testowym z historią nauki.
- Zależności: korzystnie wykonać po F4-11 (może korzystać z gotowego widoku mastery per temat), ale nie
  blokujące — może być zrobione niezależnie z istniejącymi danymi.

---

### Faza 5 — Weryfikacja końcowa i zamknięcie planu (0.5–1 dzień)

**F5-1. Pełny przebieg testów na docelowym stacku**
- Akcja: `py -3.12 -m pytest backend/tests/ -q` (0 failed), `cd frontend && npm test -- --run` (0 failed),
  `ruff check backend/` (0 błędów), `cd frontend && npm run lint` (0 błędów, ostrzeżenia policzone).
- Kryterium akceptacji: wszystkie 4 komendy zielone, wyniki wklejone do `TASKS.md` w nowej sekcji
  "Weryfikacja końcowa ACTION_PLAN <data>".
- Zależności: wszystkie poprzednie fazy.

**F5-2. Aktualizacja `README.md` (liczby testów) — dokończenie F0-6**
- Akcja: wpisać realne liczby z F5-1.
- Zależności: F5-1.

**F5-3. Aktualizacja `CHANGELOG.md` — wpis zbiorczy dla całego planu**
- Akcja: sekcja `## <data zakończenia>` z podsumowaniem zmian per faza (odnośniki do commitów).
- Zależności: F5-1.

**F5-4. `alembic check` finalny**
- Akcja: potwierdzić `alembic check` (lub równoważna metoda z F1-1) → brak dryfu między modelami a
  najnowszą rewizją.
- Zależności: wszystkie zadania Fazy 1 i Fazy 3 (które dodają nowe tabele).

**F5-5. Przegląd `docs/NEURO_FEATURES.md` / `NEURO_PLAN.md` pod kątem nowych funkcji z Fazy 4**
- Akcja: dla każdej nowej/zmienionej funkcji wpływającej na naukę/zachowanie z Fazy 4 (F4-8 fiszki, F4-9
  konwersacja, F4-11 bank wiedzy mastery) dodać/zaktualizować wpis w `docs/NEURO_FEATURES.md` z poziomem
  dowodu (META/RCT/OBS/HIPOTEZA) — zero nowych funkcji bez tej adnotacji, zgodnie ze standardem, który
  LinguaAI już wzorcowo utrzymuje.
- Zależności: Faza 4 ukończona.

---

## Ryzyka i decyzje otwarte

Poniżej **wyłącznie** kwestie faktycznie nierozstrzygnięte. Cztery decyzje z briefu użytkownika
(stack-wzorzec bez downgrade'u, pełny Alembic, stuby INT-3..6 budowane teraz, LinguaAI w pierwszej grupie
priorytetowej) są already committed — nie wracać do nich, nie pytać użytkownika ponownie.

1. **Gotowość odbiorcy `POST /api/v1/integrations/event` po stronie System-Głównego.** Ten plan buduje
   stronę LinguaAI (publisher, Faza 3) jako stub niezależnie od stanu huba — `MASTER_PLAN.md` System-Głównego
   pokazuje Event Bus jako "już istnieje" (linia 48) ogólnie, ale konkretny endpoint
   `POST /api/v1/integrations/event` + `X-Module-Key` nie jest potwierdzony jako zaimplementowany po
   stronie System-Głównego w audycie tego dokumentu. Ryzyko: `flush_pending_events` będzie się kolejkować
   bez faktycznego dostarczenia dopóki System-Główny nie wystawi odbiornika. Mitygacja: kolejka w F3-1
   jest trwała (DB), więc brak utraty danych — eventy czekają na `sent_at` aż odbiorca zacznie działać.
   Nie jest to blokerem dla wykonania Fazy 3, tylko oczekiwanie na integrację end-to-end.
2. **Dokładny wzór `mastery %` w F4-11 (Bank wiedzy).** Audyt nie potwierdził istnienia gotowego wzoru w
   kodzie. Wykonawca Fazy 4 musi sam zdecydować o formule na bazie danych FSRS dostępnych w
   `fsrs_service.py` i **jawnie oznaczyć poziom dowodu** tej formuły w `docs/NEURO_FEATURES.md` (prawdopodobnie
   HIPOTEZA/OBS, nie META/RCT — to metryka produktowa, nie efekt z badania). To nie jest decyzja do
   podjęcia teraz — to instrukcja dla wykonawcy, żeby nie fabrykował pozornie naukowej liczby.
3. **Model docelowy dla trybu konwersacji (F4-9).** `model_router.py` ma dziś tiery `free/cheap/best`
   (z `config.py`: `AI_MODEL_TIER`), ale plan celowo nie przesądza czy nowy tier "conversation" mapuje na
   `best` wprost, czy na osobny model dobrany pod latencję rozmowy (stream). Wykonawca ma sprawdzić
   realną zawartość `model_router.py` przed decyzją — nie zgadywać nazwy modelu.
4. **Zakres "sleep_logged" w F3-3.** Audyt nie potwierdził istnienia dziennika snu jako osobnej funkcji w
   LinguaAI dzisiaj (wzmianka `sync-sleep` w `TASKS.md` INT-4 sugeruje że coś istnieje, ale nie zostało to
   zweryfikowane w kodzie w tym audycie). Wykonawca Fazy 3 musi to zweryfikować (`grep -rn "sleep"
   backend/`) przed próbą wysyłki tego typu eventu — jeśli nie istnieje, pominąć `sleep_logged` w F3-3 bez
   fabrykowania źródła danych.
5. **Kolejność F4-11 vs pozostałe zadania Fazy 4.** Plan sugeruje wykonanie F4-11 jako ostatnie w fazie
   (największy zakres, ryzyko konfliktów w modelu `Topic`), ale to rekomendacja, nie twardy wymóg — jeśli
   wykonawca (człowiek lub inny model AI) ma powód zrobić inaczej, może, o ile udokumentuje uzasadnienie w
   `TASKS.md`.

---

## Definition of Done całego planu

Plan uznaje się za w pełni wykonany, gdy **wszystkie** poniższe są prawdziwe jednocześnie:

- [ ] Wszystkie zadania F0-1 do F5-5 oznaczone jako ukończone w `TASKS.md` (z datą i, gdzie dotyczy, hashem commita).
- [ ] Kryteria K1–K14 (sekcja "Cel projektu i mierzalne kryteria sukcesu") wszystkie spełnione i zweryfikowane, nie założone.
- [ ] `git log` pokazuje commity zgodne z konwencją ekosystemu (`<type>: co i dlaczego`, lista plików) dla każdej fazy.
- [ ] `CHANGELOG.md` nie ma luki między ostatnim wpisem a `HEAD`.
- [ ] `docs/BACKLOG_UX_2026-08.md` — zero pozycji P0/P1/P2/P3 bez adnotacji zamknięcia lub jawnego przeniesienia do przyszłego backlogu z uzasadnieniem.
- [ ] `docs/NEURO_FEATURES.md`/`NEURO_PLAN.md` zaktualizowane o każdą nową funkcję z Fazy 4 z poziomem dowodu.
- [ ] Zero ręcznych `ALTER TABLE` od zakończenia Fazy 1 — cała historia schematu w Alembicu.
- [ ] `GET /api/v1/summary` (INT-1), `POST /api/v1/integrations/event` (INT-2 stub), `POST /api/v1/directives` (INT-3 stub) wszystkie pokryte testami i zielone.
- [ ] Sekcja "Ryzyka i decyzje otwarte" — każdy punkt albo rozstrzygnięty (z notatką kto/kiedy zdecydował), albo świadomie pozostawiony otwarty z uzasadnieniem w `TASKS.md`.
