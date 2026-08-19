# TASKS – LinguaAI

_Ostatnia aktualizacja: 2026-08-19_

---

## 🟢 ACTION_PLAN.md Faza 2 — wydzielenie logiki z lessons.py (2026-08-19)

- **F2-1 ✅** — `backend/routers/lessons.py` (1060 linii) miał zduplikowaną (nie tylko
  "za dużo logiki w routerze" ogólnikowo, ale dosłownie skopiowaną 1:1) logikę w dwóch
  miejscach: `get_today_lesson` i `generate_next_lesson`. Wydzielone do nowego
  `backend/services/lesson_service.py`:
  - `gather_lesson_context(db, user)` — zbieranie kontekstu RAG (błędy z testów, tematy do
    interleavingu, słownictwo, słabe/mocne tematy) pod `generate_daily_lesson`. Wcześniej
    ta sama logika istniała dosłownie dwukrotnie — realne ryzyko rozjazdu przy przyszłej
    zmianie jednej kopii bez drugiej.
  - `create_and_persist_lesson(db, user, day_number, content)` — zapis lekcji + fiszek +
    ćwiczeń. Recovery po `IntegrityError` (bug naprawiony w `4af0665`) **zostało w routerze**
    świadomie — to jedyny endpoint z realnym race condition (podwójny mount reacta), a
    decyzja "co zwrócić po złapaniu wyjątku" to kształtowanie odpowiedzi, nie logika
    biznesowa.
  - `lesson_to_dict(lesson)` — serializacja, wcześniej powielona w 4 miejscach.
  - Router: 1060 → 869 linii. `481/481` testów przechodzi bez zmian w assercjach (czysty
    refaktor), `ruff check backend/` nadal 0 błędów, zweryfikowane też na żywo
    (`GET /api/lessons/today/4` zwraca poprawną, istniejącą lekcję).
- **F2-2 ❌ Świadomie pominięte.** Ujednolicenie prefiksów (`topics.py` z `/api/topics` na
  natywny `/api/v1/topics`) to czysto porządkowy dług — middleware aliasu już obsługuje
  oba warianty funkcjonalnie (`test_api_v1_alias.py` zielony), więc zero realnej korzyści
  dla użytkownika. Zmiana wymagałaby odwrócenia kierunku aliasu żeby nie złamać
  `frontend/src/api/client.js` (woła `/api/*`, nie `/api/v1/*`) — realne ryzyko regresji za
  zero widocznej wartości. Priorytet oddany zamiast tego na backlog UX (Faza 4), który
  użytkownik faktycznie zgłaszał. Można wrócić do F2-2 później, jeśli ktoś ma konkretny
  powód (np. zewnętrzna integracja wymagająca czystych `/api/v1/*`).
- **F2-3** — `ruff check backend/` zweryfikowany po F2-1 (0 błędów). Nie ma sensu ponownie
  po F2-2, bo F2-2 nie zostało wykonane.

---

## 🟢 ACTION_PLAN.md Faza 1 — pełne przejście na Alembic (2026-08-19)

Decyzja użytkownika: zostać na Python 3.11 lokalnie (F0-4 nie zmienia niczego funkcjonalnie,
CI już pinuje 3.12 poprawnie), kontynuować realizację `ACTION_PLAN.md`, integrację z Systemem
Głównym (Faza 3) zostawić na później.

- **F1-1 ✅ Audyt drift — poważniejszy niż zakładał `ACTION_PLAN.md`.** Realny problem nie był
  tylko "dwie rewizje nie pokrywają całej historii" — `backend/main.py` miał **równoległy,
  własny system migracji** (`_migrations` — lista `ALTER TABLE ADD COLUMN` uruchamiana przy
  starcie), który od miesięcy był FAKTYCZNYM mechanizmem ewolucji schematu, podczas gdy Alembic
  stał w miejscu od `5a6d111e51d9` (add_push_subscriptions). Skutki:
  - `alembic_version` w realnej bazie wskazywał na rewizję `032cedbc2785`, która nie istnieje w
    `backend/alembic/versions/` (fantom — prawdopodobnie z etapu przed uporządkowaniem historii).
  - `topics.parent_id` (hierarchia tematów, kluczowa dla planowanej przebudowy Banku wiedzy,
    P2-4) — dodana WYŁĄCZNIE przez ad-hoc `ALTER TABLE` w `main.py`, nigdy nie było jej w żadnej
    rewizji Alembic. Fresh install przez `alembic upgrade head` budował schemat BEZ tej kolumny.
  - `flashcards.mnemonic` (SCI-13) — ta sama sytuacja.
  - `flashcards.gesture_anchor`/`spatial_anchor`, `users.neuro_weights` — odwrotnie: kolumny
    istniały w realnej bazie (relikty wycofanych funkcji — kinaesthetic anchors, „neuro-wagi"),
    ale nie ma ich w modelach ani w żadnej migracji. Zweryfikowano `grep`, że nic w kodzie ich
    nie używa, przed usunięciem.
  - `users.login_token` — model deklaruje `unique=True`, baseline migration to poprawnie
    zakłada, ale realna baza (stworzona przed Alembikiem, potem tylko "stamp") nigdy realnie nie
    dostała tego ograniczenia.
  - `topics.ix_topics_parent_id` — indeks z modelu, brakujący WSZĘDZIE (fresh i live).
  - **Bonus fix**: `backend/alembic.ini`/`README` instruowały `cd backend` przed komendami — ale
    `DATABASE_URL=sqlite:///./lingua_ai.db` jest ścieżką względną wobec cwd procesu, więc
    uruchomienie z `backend/` migrowałoby **inny plik** (`backend/lingua_ai.db` — właśnie ten
    martwy plik usunięty w Fazie 0!), nie realną bazę. Naprawione: `script_location =
    %(here)s/alembic` w `alembic.ini` (odporne na cwd) + README poprawiony na uruchamianie z roota.
- **F1-2 ✅** — dwie nowe rewizje, obie z `sa.inspect()`-owymi strażnikami istnienia kolumny/
  indeksu/FK, żeby działały bezpiecznie zarówno na świeżej bazie (zbudowanej czysto przez
  `alembic upgrade head`) jak i na realnej, zdryfowanej bazie — zweryfikowane osobno dla obu
  ścieżek (upgrade+downgrade+re-upgrade, dane nienaruszone: 10 users, 225 flashcards przed/po):
  - `8dfdfadd8a31_fix_schema_drift_from_manual_alters.py` — usuwa `gesture_anchor`/
    `spatial_anchor`/`neuro_weights`, dodaje unique constraint na `login_token`, luzuje
    `is_mastered` do nullable (zgodnie z modelem).
  - `9c1a1e9b7b4f_add_topics_hierarchy_and_mnemonic.py` — dodaje `flashcards.mnemonic`,
    `topics.parent_id` + FK + indeks.
  - Po obu: `alembic check` → **"No new upgrade operations detected"** na świeżej bazie ORAZ na
    kopii realnej bazy. Migracja zastosowana na PRODUKCYJNEJ `lingua_ai.db` (po weryfikacji na
    kopii) — `481/481` testów backendu nadal przechodzi, żywy serwer sprawdzony w przeglądarce
    (`/api/stats/4`, `/api/flashcards/4` zwracają realne dane usera z 44 fiszkami, w tym pola
    `is_mastered`/`mnemonic` — bez 500).
- **F1-3 ✅** — sekcja "Migracje bazy danych" dodana do `CLAUDE.md`; `backend/alembic/README`
  rozszerzony o politykę (zero ręcznych ALTER TABLE) + pełną historię incydentu jako ostrzeżenie
  dla przyszłych sesji.
- **F1-4 ✅** — `backend/main.py`'s `lifespan()`: `Base.metadata.create_all()` + 20-liniowa
  lista `_migrations` + ręczny `CREATE TABLE IF NOT EXISTS conversation_sessions` (całkowicie
  zbędny — model już był tworzony przez `create_all`) zastąpione jednym wywołaniem
  `alembic.command.upgrade(cfg, "head")`. Błąd migracji jest teraz głośny (rzuca wyjątek)
  zamiast starego `except: pass` połykającego wszystko po cichu.
  **Uwaga do testów**: to wywołanie jest pomijane gdy `TESTING=1` — inaczej `TestClient(app)`
  (który odpala lifespan) migrowałby PRODUKCYJNĄ `DATABASE_URL` zamiast izolowanej
  `test_language_tutor.db` zarządzanej przez `conftest.py`. Złapane i naprawione przed
  commitem (pierwsza wersja bez tej strażnicy uruchamiała `alembic upgrade head` na realnej
  bazie przy każdym z setek wywołań `client` fixture w testach).
- Nieusunięty `Base`/`engine` import z `main.py` (stał się martwy) — usunięty, `ruff check
  backend/` nadal 0 błędów.

---

## 🟢 ACTION_PLAN.md Faza 0 — higiena i blokery natychmiastowe (2026-08-19)

Realizacja Fazy 0 z `ACTION_PLAN.md` (dokument dodany do repo, jeszcze niecommitowany —
`git status` przed tą sesją pokazywał go jako `??`). Wszystko zweryfikowane na żywo, nie
założone.

- **F0-1 ✅** — `CLAUDE.md:162` wskazywał `C:\GoogleDriveSync\Projekty\LinguaAI\` jako repo
  root, sprzecznie z linią 7 tego samego pliku i realnym stanem. Poprawione na
  `C:\Projects\LinguaAI\`. `07_Context/UNIFIED_STANDARDS.md` nie istnieje w tym repo (
  zweryfikowano `Test-Path`) — odniesienie zastąpione wskazaniem na
  `C:\Projects\System-Glowny\CLAUDE.md` + `MASTER_PLAN.md` (potwierdzone, że istnieją lokalnie).
- **F0-2 ✅** — usunięty martwy `backend/lingua_ai.db` (0 B, relikt z 10 lipca). Zweryfikowano
  że nic w `backend/` tworzy plik pod tą ścieżką przy starcie z roota (`DATABASE_URL` w
  `config.py` jest względne `./lingua_ai.db`, rozwiązuje się względem cwd = root przy
  poprawnym uruchomieniu; `notifier.py`/`backup_service.py` tylko *sprawdzają* oba miejsca
  jako fallback odczytu, nie tworzą pliku).
- **F0-3 ✅** — `ruff` nie był zainstalowany w interpreterze projektu (`py -3.11`), tylko w
  odizolowanym venv samego Claude Code. Doinstalowany (`py -3.11 -m pip install ruff`, wersja
  0.16.3). `py -3.11 -m ruff check backend/` → **0 błędów** ("All checks passed!").
- **F0-4 ⏸️ Wymaga decyzji użytkownika** — lokalnie dostępne interpretery to tylko 3.11.9 i
  3.14.2 (`py -0`), `pyproject.toml` wymaga `>=3.12`. CI (`.github/workflows/ci.yml`) pinuje
  3.12 poprawnie — to luka środowiska dev tej maszyny, nie repo. Instalacja nowego runtime'u
  systemowo nie została wykonana automatycznie (zmiana środowiska systemowego) — do
  potwierdzenia przez użytkownika, patrz podsumowanie na końcu sesji.
- **F0-5 ✅** — `CHANGELOG.md` nie miał wpisów dla ostatnich 4 commitów (`3549dad`, `4af0665`,
  `bf3933e`, `80882fd`, wszystkie 2026-08-08/09). Dopisana sekcja `## 2026-08-09` z pełnym
  opisem każdego (na bazie `git show --stat`, nie zgadywane).
- **F0-6** — odłożone na koniec planu (Faza 5), zgodnie z instrukcją w `ACTION_PLAN.md` (liczby
  testów w `README.md` mają sens dopiero po Fazie 1-4, nie teraz).
- **F0-7 ✅** — `docs/BACKLOG_UX_2026-08.md`: P0-1 (klucze/`AI_MODEL_TIER=best`) zweryfikowane
  bezpośrednio w `backend/.env` (obecność, nie wartości) — zamknięte. P3-1 (nawigacja) —
  potwierdzone w kodzie (`NavBar.jsx`, `flex flex-wrap`, 5 kategorii) — zamknięte. **Dodatkowe
  odkrycie wykraczające poza F0-7**: P3-2 (tryb jasny kremowy) też jest już zaimplementowany
  (`frontend/src/index.css`, commit `445e0b9`, sprzed tego audytu) — `ACTION_PLAN.md` (F4-12)
  błędnie liczy to jako otwarte zadanie Fazy 4; oznaczone jako zamknięte w backlogu, do
  poprawienia świadomości przy realizacji Fazy 4.

**Nie wykonane w tej sesji, pozostaje otwarte:** cała reszta `ACTION_PLAN.md` (Fazy 1–5:
pełne przejście na Alembic, porządki architektoniczne w `lessons.py`, stuby integracji
`INT-2`/`INT-3` z Systemem Głównym, backlog UX P1/P2/reszta P3, weryfikacja końcowa) — plan
wielodniowy, nie rozpoczęty poza Fazą 0.

---

## 🟡 Zgłoszone przez użytkownika: zwolnione tempo + przebudowa Banku wiedzy (2026-08-09)

**1. Brak zwolnionego tempa w „Powtórz na głos"** — `ReadAloud.jsx`: `play()`
tworzył/odtwarzał `Audio` zawsze z domyślnym `playbackRate`. Dodany drugi,
mniejszy przycisk (żółw, `Turtle` z lucide-react) obok głównego — ten sam plik
audio, `playbackRate = 0.6`. Zero kosztu backendu/AI (czysto klienckie).
Test: `ReadAloud.test.jsx` (+1, sprawdza że `playbackRate` faktycznie się
zmienia na tym samym obiekcie `Audio`, nie tylko że przycisk istnieje).

**2. Bank wiedzy „ohydny" → zdiagnozowane i naprawione: strona nie miała ANI
JEDNEJ klasy `dark:` w całym pliku** (783 linie), podczas gdy reszta aplikacji
jest w pełni ciemna/jasna (theme-aware). W trybie ciemnym renderowało się to
jako białe karty (`bg-white`), jasnopastelowe odznaki kategorii
(`bg-blue-100 text-blue-800`) i szare obramowania — wyspa jasnego motywu
wklejona w ciemny interfejs. Stąd wrażenie „ohydne", nie subiektywny gust.
- **Przyczyna:** strona nigdy nie dostała przejścia na dark mode, którym
  przeszła reszta aplikacji dawno temu (widać po `.card`/`.badge-*`/
  `.input-field` — gotowych, już theme-aware klasach w `index.css`, z których
  ta strona w ogóle nie korzystała, tylko pisała styl ad-hoc).
- **Naprawa:** systematyczne przejście przez cały plik — każdy `bg-white`,
  `bg-gray-50/100`, `text-gray-4/5/6/700`, goły `border` dostał parę `dark:`,
  dokładnie w konwencji już używanej w reszcie apki (np. `dark:bg-gray-900
  bg-white`, `dark:text-gray-400 text-gray-500`). `CATEGORY_COLORS` (10
  kategorii) i `GENDER_COLORS` rozszerzone o warianty `dark:bg-X-500/20
  dark:text-X-300 dark:border-X-500/30` — ten sam wzorzec przezroczystości,
  którego już używa `Flashcards.jsx`.
- **Weryfikacja — nie na słowo, realny `getComputedStyle` w żywej
  przeglądarce w obu motywach:**
  - Ciemny: kafelek statystyk `rgb(17,24,39)` (dokładnie `gray-900`), odznaka
    kategorii „Słownictwo" `rgba(16,185,129,0.2)` tło / `rgb(110,231,183)`
    tekst (dokładnie `emerald-500/20` / `emerald-300`).
  - Jasny (przełączone na żywo): karta tematu `rgb(252,249,243)` (kremowy
    `.light .bg-white`), odznaka `rgb(220,252,231)` (`green-100`) — potwierdzone
    że stary, działający tryb jasny nie został zepsuty przy okazji.
- Frontend 91/91 passed, lint 0 błędów (bez nowych ostrzeżeń).

---

## 🟡 Zgłoszone przez użytkownika: ćwiczenia w lekcji — 2 poprawki (2026-08-09)

**Zgłoszone:** ćwiczenie typu „Matching" (9) nie da się połączyć — dwie kolumny
tekstu bez żadnej interakcji; ćwiczenie otwarte „Sentence Creation" (15)
oceniane jak zamknięte (użytkownik napisał własne, poprawne zdanie i dostał
„źle"), a powinno być sprawdzane przez AI pod kątem gramatyki i zgodności z poleceniem.

**1. Matching bez interakcji** — `daily_lesson.py` nie ma dedykowanego schematu
na N par, więc model sam wymyśla format: jeden `item` z `prompt: "Stuhl /
Wohnung / Buch..."` i `answer: "der Stuhl | die Wohnung | das Buch..."`.
Frontend (`normalizeExercises`) brał to 1:1 jako JEDNĄ parę — cała lewa kolumna
i cała prawa kolumna jako pojedyncze bloki tekstu, w dodatku w tej samej
kolejności (prawa kolumna była już gotową odpowiedzią).
- `frontend/src/pages/DailyLesson.jsx` `normalizeExercises`: dzieli teraz
  `prompt` po `/` i `answer` po `|` na osobne pary (wstecznie kompatybilne —
  pojedyncza, niedzielona para nadal działa jak wcześniej).
- `ExerciseCard`: kolumna prawa **przetasowana** raz per ćwiczenie (żeby nie
  była trywialnie wyrównana z lewą), klik lewa→prawa sprawdza parę na żywo
  (zielono = trafione, czerwony pulse = źle, bez usuwania zaznaczenia z gry).
- Zweryfikowane na **prawdziwej, wcześniej zepsutej** lekcji (dzień 2, user 3):
  „Kolumna lewa" pokazuje teraz 5 osobnych słów, „Kolumna prawa" w innej
  kolejności niż lewa (potwierdzone: „die Familie, der Stuhl, das Buch..." nie
  w kolejności z lewej), klik Stuhl→der Stuhl → oba na zielono.

**2. Ćwiczenie otwarte oceniane jak zamknięte** — `sentence_creation` (i każde
inne zadanie bez jednej poprawnej odpowiedzi) leciało przez ten sam
`handleCheck()` co fill-in-the-blank: proste porównanie substring z polem
`answer`, które dla tego typu i tak jest tylko podpisanym „Przykładem", nie
wymogiem. Poprawna, kreatywna odpowiedź użytkownika dostawała „✗ Nie do końca".
- `frontend/src/pages/DailyLesson.jsx`: nowa gałąź dla `sentence_creation` —
  przycisk „Sprawdź z AI" woła **ten sam** `evaluateProduction` co sekcja
  Production Task (nie nowy endpoint), pokazuje wynik/100 + feedback +
  konkretne poprawki, zamiast fałszywego zielono/czerwono.
- Zweryfikowane na żywo (prawdziwe wywołanie AI, nie mock): odpowiedź „Meine
  Schwester ist sehr jung und wohnt in einem Haus." dostała **30/100** z
  trafnym uzasadnieniem („napisano 1 zdanie zamiast wymaganych 3, gramatyka
  samego zdania poprawna") — dokładnie ocena gramatyki + zgodności z
  poleceniem, o którą prosił użytkownik.

**Weryfikacja:** frontend 90/90 passed (+3 nowe testy w `DailyLesson.test.jsx`:
podział par, brak fałszywego dopasowania przy złej parze, ocena AI zamiast
substring match), lint 0 błędów. Oba scenariusze potwierdzone live na
rzeczywistej, wcześniej zepsutej lekcji użytkownika (dzień 2, user 3).

---

## 🟡 Zgłoszone przez użytkownika: audio w lekcji — 3 poprawki (2026-08-09)

**Zgłoszone:** wyjaśnienie gramatyki czytane niemieckim głosem mimo że tekst
jest po polsku; nie da się zatrzymać odtwarzania; przycisk audio powinien być
na początku sekcji, nie na końcu.

**1. Zły język głosu** — `PlayButton` w sekcji gramatyki dostawał
`language={lesson.language}` (język docelowy, np. German), ale
`grammar.explanation` jest generowany **w języku ojczystym** użytkownika
(`daily_lesson.py` prompt: "clear explanation in native language"). Backend
mapuje `language` na konkretny głos TTS (np. `de-DE-KatjaNeural`), więc polski
tekst leciał niemieckim głosem. Sprawdzone: to jedyne takie miejsce w
aplikacji — wszystkie inne użycia `PlayButton` (Conversation, News,
PronunciationTrainer, ErrorReview) czytają treść faktycznie w języku
docelowym, poprawnie.
- `frontend/src/pages/DailyLesson.jsx`: nowy fetch `getUser(userId)` przy
  montowaniu (raz), `nativeLanguage` w stanie, użyte zamiast `lesson.language`
  dla tego jednego PlayButtona. Zweryfikowane live: `GET /api/placement/user/3`
  → 200, `native_language: "Polish"` faktycznie trafia do requestu TTS.

**2. Brak możliwości zatrzymania** — `PlayButton` w ogóle nie miał stanu
"gra"/"nie gra" — kliknięcie zawsze startowało nowe `Audio()`, bez śladu po
poprzednim. Przepisany: `isPlaying` w stanie + ref na bieżący `Audio`; kliknięcie
w trakcie odtwarzania **zatrzymuje** (nie restartuje), ikona zmienia się na
kwadrat (stop), `onended`/`onerror`/odmontowanie komponentu też sprzątają stan.
- `frontend/src/components/PlayButton.jsx` — przepisany.
- Testy: `PlayButton.test.jsx` (nowy plik, 4 testy — wcześniej 0% pokrycia
  tego komponentu, mimo że jest używany w 8+ miejscach w aplikacji).

**3. Przycisk na złym miejscu** — przeniesiony z końca sekcji „Wyjaśnienie
gramatyki” (po regule i przykładach) na początek (zaraz po tytule tematu,
przed treścią wyjaśnienia) w `DailyLesson.jsx`.

**Weryfikacja:** frontend 87/87 passed (+4 nowe), lint 0 błędów. Na żywo:
przycisk teraz nad tekstem wyjaśnienia (potwierdzone przez `innerText` DOM),
kliknięcie → tytuł przycisku `"Zatrzymaj"` w trakcie, drugi klik → wraca do
`"Play: ..."` i faktycznie zatrzymuje `<audio>` (nie tylko UI).

---

## 🔴 Naprawa: `/api/lessons/today` — 500 przy równoczesnych żądaniach (2026-08-09)

**Zgłoszone przez użytkownika na żywo:** lekcja "prawie się załadowała" i
wyskoczył `Request failed with status code 500` na `/lesson`.

**Przyczyna (odtworzona deterministycznie, poza HTTP i przez pełny stos HTTP):**
React w trybie dev podwójnie odpala efekty (potwierdzone live w Network:
`GET /api/lessons/today/3` wywołane dwukrotnie) — gdy lekcji na dziś jeszcze
nie ma, oba żądania widzą "brak lekcji", oba generują treść przez AI (kilka
sekund), oba próbują wstawić wiersz z tym samym `(user_id, language,
day_number)`. Przegrany trafia na `UNIQUE constraint failed` — **to było
zamierzone i miało istniejący blok odzyskiwania** (`except IntegrityError`).
Realny bug: blok odzyskiwania szukał zwycięskiego wiersza po
`date(created_at) == dzisiaj`, a nie po `day_number` (czyli dokładnie tym
polu z ograniczenia UNIQUE) — ta wyszukiwanie potrafiło nie znaleźć
świeżo zacommitowanego wiersza, blok kończył się gołym `raise`, ponownie
podnosząc oryginalny `IntegrityError` jako niezłapany 500.

**Diagnoza — dla porządku, bo była myląca:** najpierw wyglądało, jakby
`except IntegrityError:` w ogóle nie łapał wyjątku (traceback kończył się
czysto na `db.commit()`, bez śladu wejścia w except). Tymczasowa sonda
(`logger.warning` w except) pokazała, że blok **jest** wchodzony — tylko
że zapytanie odzyskujące nic nie znajdowało i kod sam ponownie podnosił
oryginalny wyjątek przez `raise` na końcu bloku. Stąd traceback wyglądał
identycznie jak przy braku obsługi.

**Naprawa (`backend/routers/lessons.py`):** zapytanie odzyskujące filtruje
teraz po `Lesson.day_number == day_number` zamiast po dacie utworzenia.

**Weryfikacja:**
- Bezpośrednio (bez HTTP, `asyncio.gather` na dwóch wywołaniach funkcji) — oba
  zwracają ten sam `lesson_id`.
- Przez pełny stos HTTP/ASGI/middleware — 3 równoczesne żądania curl, wszystkie
  200, wszystkie ten sam `lesson_id`.
- Nowy test regresyjny `test_today_lesson_concurrent_requests_both_succeed`
  (`backend/tests/test_lessons.py`) — **zweryfikowany jako realna ochrona**:
  cofnięty fix → test faktycznie failuje z tym samym `IntegrityError`;
  przywrócony fix → przechodzi. (Pierwsza wersja testu z natychmiastowym
  mockiem AI fałszywie przechodziła nawet bez poprawki — poprawiona na mock
  z `await asyncio.sleep(0.05)`, żeby wymusić realny przeplot.)
- Pełna suita: backend 478/481 passed (3 nieszkodliwe, niepowiązane błędy
  `pywebpush` — brak modułu w tym środowisku, znane od 2026-08-08).
- Na żywo w przeglądarce: `/lesson` ładuje się czysto, Network pokazuje
  podwójne wywołanie `GET /api/lessons/today/3` (React StrictMode) i oba 200.

---

## 🔴 Nawigacja: WSZYSTKIE funkcje trwale widoczne, bez wyjątku (2026-08-08)

**Kontekst:** P3-1 z `docs/BACKLOG_UX_2026-08.md` był zgłaszany wielokrotnie i
tylko **połowicznie** naprawiony wcześniej — commit "feat(P3-1)" dodał
brakujące strony do menu (Czytaj, Historia), ale nie ruszył sedna problemu:
etykiety wciąż znikały poniżej `md` (same ikony), a 18 pozycji żyło w jednym,
poziomo przewijanym rzędzie. Użytkownik to zauważył od razu po realnym
przejściu po stronie.

**Naprawa (`frontend/src/components/NavBar.jsx`):**
- Usunięty `hidden md:block` na etykietach — **każda pozycja ma trwale
  widoczny tekst, na każdej szerokości ekranu**, zweryfikowane realnym
  `element.innerText` (nie samą obecnością w DOM) na 1280px i 375px (telefon).
- Usunięty poziomy scroll (`overflow-x-auto`) — zastąpiony `flex-wrap`: przy
  wąskim ekranie pozycje zawijają się na kolejne linie zamiast znikać albo
  wymagać przewijania.
- 18 funkcji pogrupowanych w 5 widocznych, podpisanych kategorii (zgodnie z
  pierwotną specyfikacją P3-1): **Nauka** (Główna/Lekcja/Test/Mów/Wymowa/
  Newsy/Bank wiedzy), **Ćwiczenia** (Fiszki/Ćwiczenia/Dyktando/Czytaj/Timer),
  **Media** (Filmy), **Postępy** (Statystyki/Błędy/Historia), **Konto**
  (Profil/Ustawienia). Żadna z nich nie jest schowana za dropdownem/hoverem —
  świadoma decyzja, bo to i tak byłoby "ukrywanie", tylko za inną nazwą.
- Testy: `NavBar.test.jsx` +2 — regresja-lock sprawdzający, że żaden label nie
  siedzi w elemencie z klasą zawierającą `hidden` (dokładnie ten bug, który
  wrócił), oraz że wszystkie 5 nagłówków kategorii są widoczne. 9/9 passed.
- **Przy okazji naprawione:** `start.bat` uruchamiał backend przez gołe
  `python`, które (jak ustalono 2026-08-05/07 w tej samej sesji) w wielu
  środowiskach nie ma zainstalowanych zależności projektu — użytkownik trafił
  na dokładnie ten `ModuleNotFoundError: sqlalchemy` po odpaleniu skrótu z
  pulpitu. Zmienione na `py -3.11`, zgodnie z już poprawnym `start.ps1`.
- **Weryfikacja:** frontend 83/83 passed, lint 0 błędów, oraz ręczna kontrola
  `document.querySelector('nav').innerText` w realnej przeglądarce na 1280px
  i 375px — wszystkie 18 etykiet obecne na obu.

---

## 🔧 Naprawa: TTS (edge-tts) zwracał 403 na każde żądanie audio (2026-08-08)

**Objaw:** podczas weryfikacji na żywo w przeglądarce (po sesji audytowej
2026-08-05…07) generowanie audio (PlayButton, offline-pack fiszek, read-aloud)
sypało w logach `WARNING Audio attempt 1-3/3 failed: 403, message='Invalid
response status'` przy każdej próbie — TTS był całkowicie martwy.

**Przyczyna:** w środowisku (`py -3.11`, ten samo, którego używa `start.ps1`)
zainstalowana była **`edge-tts==6.1.12`**, mimo że `backend/requirements.txt`
i `pyproject.toml` od dawna deklarują `edge-tts>=7.0.2`. Microsoft okresowo
zmienia protokół WebSocket używany przez tę (nieoficjalną) bibliotekę;
starsze wersje przestają działać, aż ktoś zaktualizuje pakiet — dokładnie to
się tu stało, environment po prostu nigdy nie dostał `pip install --upgrade`.

**Naprawa:** `py -3.11 -m pip install --upgrade "edge-tts>=7.0.2"` → zainstalowano
`7.2.8`. Nic w kodzie repo się nie zmieniło (deklaracja wersji już była
poprawna) — to czysto lokalny dług środowiska, ale warto o nim wiedzieć, bo
identyczny objaw wróci na każdej świeżej maszynie/venv, dopóki ktoś nie
zainstaluje zależności z `requirements.txt` (nie ręcznie, pojedynczo).

**Weryfikacja:** bezpośredni test `edge_tts.Communicate(...).stream()` → realne
bajty audio; `POST /api/audio/tts` z zupełnie nową, nigdy niesyntezowaną
frazą → plik `.mp3` wygenerowany na świeżo (potwierdzone znacznikiem czasu +
rozmiarem), log `INFO Audio generated` bez żadnego `WARNING`/`ERROR`.

---

## 📄🔬 AUDYT DOKUMENTACJI + ZGODNOŚCI NAUKOWEJ (2026-08-07)

_Polecenie: pełny audyt — przeczytać dokumenty i znaleźć co się mija z prawdą; sprawdzić
zgodność z badaniami i co dodać/zmienić. Metoda: ręczne przeczytanie CLAUDE.md, README.md,
docs/ARCHITECTURE.md, docs/API_FUNCTIONS.md, docs/NEURO_FEATURES.md, NEURO_PLAN.md,
CHANGELOG.md, docs/BACKLOG_UX_2026-08.md + grep docs/PRODUCTION_AND_MOBILE.md i
docs/deployment.md; osobny agent (zakończony) na regresję naukową + nowe propozycje._

### 🔴 Dokumentacja — realne rozbieżności z kodem

- [x] **DOC-2: CLAUDE.md ma błędny stack i dane w kilku miejscach jednocześnie
      sprzeczne z README.md i docs/ARCHITECTURE.md w tym samym repo** ✅ 2026-08-07 —
      sekcja Architecture przepisana: linkuje do `docs/ARCHITECTURE.md` jako źródła
      prawdy zamiast duplikować tabelę routerów (10→ usunięta, zastąpiona odnośnikiem);
      React 18/Router v6 → React 19/Router 7; „Google Gemini 2.0 Flash"/`gemini-2.0-flash`
      w Key Numbers → opis tierowanego katalogu `model_router.py`; fallback
      doprecyzowany jako opt-in (`fallback=`), nie uniwersalny.
  - `CLAUDE.md:94` „React 18 · React Router v6" — `README.md:26` i
    `docs/ARCHITECTURE.md:66` poprawnie mówią **React 19 · React Router 7**
    (zgodne z `frontend/package.json`). CLAUDE.md jest tu jedynym błędnym źródłem.
  - `CLAUDE.md:47,114` „Google Gemini 2.0 Flash" / „Gemini model: gemini-2.0-flash"
    jako **jedyny** model — nieprawda od dawna: `model_router.py` ma katalog 17
    zweryfikowanych modeli OpenRouter, dobór per zadanie/tier (`best`/`cheap`/`free`),
    żadnego hardkodowanego `gemini-2.0-flash`.
  - `CLAUDE.md:58` „Every function... has a hardcoded fallback" — tylko wywołania
    z jawnym `fallback=` (np. `flashcards.py:445,450`) je mają; reszta
    (`lesson_generator/*`, `news_service`, `youtube.py`) rzuca `ValueError`.
  - `CLAUDE.md:75-88` tabela routerów: **10 wpisów**, realnie jest **20**
    (`main.py` — 20× `include_router`). `docs/ARCHITECTURE.md §6` ma poprawną,
    pełną tabelę 20 routerów — użyć jej jako źródła przy odświeżaniu CLAUDE.md.
  - **Naprawa:** przepisać sekcję Architecture w CLAUDE.md, żeby *linkowała* do
    `docs/ARCHITECTURE.md` jako źródła prawdy zamiast duplikować (i rozjeżdżać się z) jego treść.

- [x] **DOC-3: `docs/API_FUNCTIONS.md:115` opisuje nieistniejącą funkcję** ✅ 2026-08-07 —
      „**Settings**: zmiana języka/API key/**neuro-wag** → personalizacja."
      Wszystkie trzy człony są nieprawdziwe: (1) `neuro_weights`/`neuro-wagi` zostały
      **usunięte** (potwierdzone we własnym `docs/NEURO_FEATURES.md §3` — martwy kod,
      nic go nie konsumowało), (2) zmiana klucza API nie ma żadnego endpointu (tylko
      `.env`), (3) zmiana języka nauki żyje w innym miejscu (`updateUserLanguage`,
      teraz na stronie `/settings`), nie w `routers/settings.py` (który robi tylko
      tłumaczenia UI + Google Drive OAuth). Usunąć/przepisać tę linię.

- [x] **DOC-4: `docs/NEURO_FEATURES.md` §1 i §4 nieaktualne mimo własnej instrukcji
      „aktualizuj tabelę statusu po każdej zmianie"** ✅ 2026-08-07 — SCI-1…SCI-7
      przeniesione do §1 jako ✅ Produkcja z odnośnikami do kodu; §4 przepisane tak,
      by nie duplikować statusu (wskazuje na NEURO_PLAN.md/TASKS.md jako jedyne
      źródło bieżącego backlogu). `NEURO_PLAN.md` §3: SCI-7 oznaczone ✅ zaimplementowane.
      §6 „Fazy" przepisane — plan pierwotny zostawiony jako kontekst historyczny +
      jawna notka o rzeczywistej kolejności wykonania. _(Update tego samego dnia:
      SCI-8 pierwotnie oznaczone tu jako „🟡 częściowe" — po dokładniejszej weryfikacji
      przy SCI-11 niżej okazało się w pełni zamknięte, nie częściowe; poprawione
      wszędzie, w tym w `NEURO_PLAN.md`.)_

- [x] **DOC-5: Nowa strona `/settings` (dodana 2026-08-06) nie była udokumentowana
      nigdzie** ✅ 2026-08-07 — `docs/ARCHITECTURE.md §4`: „19 stron" → „20 stron",
      dopisana notka o Settings.jsx i przeniesieniu przełącznika języka ze Stats.

### 🟡 Drobne / kosmetyczne

- [x] **DOC-6:** `docs/PRODUCTION_AND_MOBILE.md:5` otwierał dokument zdaniem „Fix
      the current development blocker (missing `isImportant` column)" ✅ 2026-08-07 —
      oznaczone jako rozwiązane (przekreślone w spisie + notatka „Status: resolved
      long ago" w sekcji 1), treść zostawiona jako referencja wzorca migracji.
- [x] **P0-1 z `docs/BACKLOG_UX_2026-08.md` już rozwiązane** — zweryfikowane
      bezpośrednio (bez odczytu wartości): `ADMIN_API_KEY`, `AI_MODEL_TIER=best`,
      `YOUTUBE_API_KEY`, `GEMINI_API_KEY` wszystkie ustawione w `backend/.env`.
      Reszta tego backlogu (P1-1…P3-3) — sprawdzone git logiem, **wszystko
      zaimplementowane** commitami 9667853…c6f478e (znaki specjalne, gramatyka,
      recall diff, nawigacja, tryb jasny, wskazówki dnia) — dokument jest
      historyczny i w pełni zamknięty, można go oznaczyć jako zarchiwizowany.

### ✅ Zweryfikowane jako zgodne z prawdą (bez akcji)

`docs/ARCHITECTURE.md` (aktualizacja 2026-07-27) jest dokładny i spójny z kodem
niemal wszędzie — poprawny stack, poprawna tabela 20 routerów, poprawny opis
fallbacku `generate_json`, poprawny status SCI-1…SCI-10, poprawny opis migracji
Alembic (jawnie mówi że NIE jest auto-wywoływana przy starcie, zgodnie z SEC-3
z audytu 2026-08-05). Traktować go jako źródło prawdy przy odświeżaniu innych
dokumentów. `docs/deployment.md` i `docs/PRODUCTION_AND_MOBILE.md` (poza DOC-6)
— brak śladu Ollamy, złych portów czy martwego `DEBUG=False` (usunięte D5/D6
2026-07-24, nie wróciło).

---

### 🧠 Zgodność naukowa — kontrola regresji (agent, 2026-08-07)

**Bez regresji.** SCI-1 (successive relearning), SCI-4 (semantic spacing),
SCI-3 (lexical coverage/i+1), SCI-2 (pretesting), interleaved review, SCI-5
(best study time — próg danych, nie sztywna godzina), SCI-6 (dyktando), SCI-7
(production effect) — wszystkie zaimplementowane zgodnie z cytowanym źródłem,
bez dryfu. `fsrs_service`/`achievement_service` — zero mnożników snu/nastroju/
pory dnia; telemetria (`session_type`, `sleep_quality`, `interleaving_bonus`,
`interference_penalty`) potwierdzona jako **tylko zapisywana**, nigdy nie
czytana z powrotem do `apply_fsrs`. Tipy (`lesson_generator/tips.py`,
`notifier.py:45-51`) — cytowania realne, zero sfabrykowanych procentów.
Grep całego `backend/` po `neuro|cortisol|multiplier|loot|gesture_anchor|
spatial_anchor|neuro_weights` — same legalne odniesienia telemetryczne/historyczne,
**żaden antywzorzec nie wrócił**.

### 📋 Nowe funkcje poparte badaniami — propozycje (nie duplikują SCI-9/SCI-10)

- [x] **SCI-11 „Domknięcie SCI-8 dla fiszek i testu dnia"** ❌ **wycofane 2026-08-07
      po weryfikacji kodu — propozycja była błędna.** Sprawdziłem bezpośrednio przed
      implementacją: `DailyTest.jsx:391-405` **już** pokazuje Twoją odpowiedź +
      poprawną (`err.correct_answer`) + regułę (`err.rule`); `Practice.jsx:344-348`
      **już** pokazuje `expected_answer` + `feedback`; `Conversation.jsx:637`
      **już** pokazuje `err.correct_answer || err.correction`. SCI-8 jest więc
      w praktyce kompletne wszędzie poza samą fiszką. Dla fiszki brak jest **zamierzony,
      nie luka**: przepływ Anki (przód → „Pokaż odpowiedź" → tył z tłumaczeniem →
      dopiero wtedy ocena 1-4) już pokazuje poprawną odpowiedź *przed* oceną —
      nie ma tu momentu „odpowiedziałem źle i nie wiem dlaczego", do którego
      odnosi się Metcalfe (2017). Dodanie czegokolwiek tutaj byłoby duplikacją.
      **Wniosek:** SCI-8 zamknięte, żadna dodatkowa zmiana kodu nie jest potrzebna.
- [x] **SCI-12 Zróżnicowana modalność dla świeżo-polapsowanych fiszek** ✅
      2026-08-07 — _Bjork & Bjork (2011)_ „desirable difficulties": powtarzanie
      identycznego formatu (flip-and-rate) po porażce to niska jakość trudności;
      zmiana modalności (usłysz + powiedz na głos) wymusza świeży szlak
      wydobycia dla tej samej treści.
      - `backend/routers/quickmode.py` `get_read_aloud`: karty w stanie FSRS
        `"Relearning"` (czyli świeżo ocenione „Again") mają teraz pierwszeństwo
        w talii read-aloud (sortowane po `next_review_date`), reszta miejsc
        dobierana jak wcześniej (najnowsze aktywne fiszki), bez duplikatów.
        Każdy element odpowiedzi ma nowe pole `lapsed: bool`.
      - `get_quickmode_plan`: aktywność „Powtórz na głos" dostaje wyższy
        priorytet (2 zamiast 3) i inny opis, gdy istnieją karty w Relearning —
        widoczność bez czekania na wejście w Quick Mode.
      - `frontend/src/pages/ReadAloud.jsx`: mały bursztynowy badge „Ostatnio Ci
        to nie poszło — spróbuj innym sposobem: na głos" gdy `current.lapsed`.
      - Testy: `backend/tests/test_read_aloud.py` (+4: priorytet lapsed, brak
        duplikatów, zachowanie bez lapsed = jak wcześniej, boost priorytetu w
        planie) + nowy `frontend/src/pages/__tests__/ReadAloud.test.jsx` (2,
        pierwszy plik testowy dla tej strony — wcześniej 0 pokrycia).
      - **Uwaga techniczna:** pierwsza wersja filtra SQL używała gołego Python
        `True` jako warunku `.filter()` (`Flashcard.id.notin_(...) if lapsed_ids
        else True`) — złapane i poprawione na warunkowe budowanie listy filtrów
        przed uruchomieniem testów, żeby uniknąć niejawnego błędu SQLAlchemy.
      - **Weryfikacja:** backend 467 passed (+4, te same 3 nieszkodliwe błędy
        `pywebpush`), frontend 79 passed (+2), lint 0 błędów. Zero kosztu AI —
        czysta logika SQL/UI, bez wywołań modelu.
- [x] **SCI-13 Metoda słowa-klucza (mnemotechnika) dla słów abstrakcyjnych** ✅
      2026-08-07 — _Atkinson (1975)_: keyword method poprawia zapamiętywanie
      abstrakcyjnego słownictwa L2 ponad zwykłe tłumaczenie. Pole `mnemonic`
      generowane tylko dla słów, które model oceni jako abstrakcyjne — prompt
      jawnie zabrania wymyślać je dla każdego słowa (kontrola kosztu/szumu).
      - `backend/models/flashcard.py` + `main.py` (ALTER TABLE): nowa nullable
        kolumna `mnemonic` — ten sam lekki wzorzec migracji co reszta kolumn
        FSRS/SCI w tym repo (bez ruszania Alembica, zgodnie z ustaloną konwencją).
      - `daily_lesson.py`: prompt słownictwa rozszerzony; nowa funkcja
        `_sanitize_vocabulary_mnemonics()` (wydzielona z inline kodu dla
        testowalności, wzorem `_sanitize_pretest`/`_sanitize_grammar_elaboration`)
        czyści białe znaki i normalizuje brak/pustkę do `""`.
      - `flashcard_service.create_flashcards_from_vocab`: zapisuje `mnemonic`
        na fiszce (`None`, gdy puste).
      - `routers/flashcards.py`: `mnemonic` dodane do odpowiedzi `get_flashcards`,
        `get_due_flashcards`, `get_flashcards_offline_pack`.
      - **Znaleziony przy okazji, prawdziwy istniejący bug:** `get_due_flashcards`
        (zasila DOMYŚLNĄ zakładkę „Do powtórki") nigdy nie zwracał `gender` ani
        `isImportant` — odznaka rodzajnika i podświetlenie ważnych słów były
        martwe na tym ekranie od dawna, bo `Flashcards.jsx` czyta `currentCard`
        z `dueCards`, nie `allCards`. Naprawione przy tej samej okazji (ten sam
        endpoint, ten sam commit).
      - `frontend/src/pages/Flashcards.jsx`: mały bursztynowy „💡 {mnemonic}"
        pod przykładowym zdaniem na tyle karty — jedyna zmiana w tym pliku,
        nic w logice oceniania/FSRS nie ruszone.
      - Testy: `backend/tests/test_mnemonic.py` (10: sanitizer + persystencja +
        3 endpointy) + nowy `frontend/.../Flashcards.test.jsx` (2, pierwszy plik
        testowy dla tej strony — wcześniej 0% pokrycia).
      - **Ważna korekta podczas pisania testu frontendowego:** pierwsza wersja
        zakładała, że tył karty jest niewidoczny w DOM przed kliknięciem —
        nieprawda, front i tył są zamontowane jednocześnie (flip czysto przez
        CSS `flipped`, nie warunkowe renderowanie). Test poprawiony, żeby
        sprawdzać obecność tekstu w dokumencie, nie „widoczność po kliku".
      - **Weryfikacja:** backend 477 passed (+10, te same 3 nieszkodliwe błędy
        `pywebpush`), frontend 81 passed (+2), lint 0 błędów. Zero kosztu AI.
- [x] **SCI-14 Elaboracyjne „dlaczego" przy gramatyce** ✅ 2026-08-07 — _Pressley
      et al. (1987)_: samodzielne wygenerowanie wyjaśnienia „dlaczego to działa"
      przed poznaniem odpowiedzi pogłębia przetwarzanie bardziej niż samo przeczytanie
      reguły. Ungraded, wzorem `PretestCard` (odkryj po swojej próbie, bez oceny).
      - `backend/services/lesson_generator/daily_lesson.py`: prompt gramatyki
        rozszerzony o `elaboration_prompt`/`elaboration_answer`; nowa funkcja
        `_sanitize_grammar_elaboration()` (usuwa oba pola, jeśli któreś puste —
        karta wtedy po prostu się nie renderuje, zero connected pół-wypełnionych);
        fallback też ma przykładowe pola (degradacja przy błędzie AI nie gubi funkcji).
      - `frontend/src/pages/DailyLesson.jsx`: nowy komponent `ElaborationCard` w
        sekcji gramatyki — pytanie „dlaczego", opcjonalne pole na własną próbę
        (tylko lokalny stan, nic nie wysyła na serwer), przycisk „Pokaż wyjaśnienie".
        Renderuje się warunkowo (`grammar.elaboration_prompt && grammar.elaboration_answer`),
        więc stare, zbuforowane lekcje sprzed tej zmiany nie pokazują pustej karty.
      - `frontend/src/i18n/translations.js`: klucze `lesson.elaboration*` (PL+EN).
      - Testy: `backend/tests/test_grammar_elaboration.py` (7, sanitizer) +
        2 nowe w `DailyLesson.test.jsx` (renderowanie pytania, reveal po kliku,
        **oraz że karta znika, gdy pól brak** — zero kosztu AI, w pełni mockowane).
      - **Weryfikacja:** backend 463 passed (+7, te same 3 nieszkodliwe błędy
        `pywebpush` co wcześniej — brak modułu w tym środowisku, niezwiązane),
        frontend 77 passed (+2), `npm run lint` 0 błędów (te same 50 wcześniejszych
        ostrzeżeń, zero nowych). Nie odpalono żywej generacji AI (koszt) — cała
        weryfikacja przez zmockowane testy renderujące realne drzewo komponentów.

---

## 🔒 AUDYT BEZPIECZEŃSTWA I JAKOŚCI (2026-08-05)

_Polecenie: audyt całego projektu (backend + frontend + higiena gita). Metoda: 2 agenty
równoległe (backend, frontend) + ręczna weryfikacja najważniejszych ustaleń przez czytanie
kodu źródłowego. **Audyt read-only — nic nie naprawiono w tym przebiegu**, tylko potwierdzono._

### 🔴 Krytyczne / wysokie

- [x] **SEC-1: Stored XSS przez `dangerouslySetInnerHTML`** ✅ 2026-08-05 —
      `frontend/src/pages/Flashcards.jsx:556` i `frontend/src/pages/TopicsPage.jsx:165`.
      Funkcja `highlightWordInSentence` escapowała do regexu tylko szukane `word` — całe
      zdanie (`example_sentence`/`example`, generowane przez Gemini, częściowo na bazie
      zewnętrznych newsów RSS z `news.py`) nigdy nie było HTML-escapowane przed
      wstrzyknięciem do `__html`. **Naprawa:** dodano `escapeHtml()` w obu plikach —
      `sentence` i `word` są HTML-escapowane przed budową regexu/znacznika `<mark>`.
      Zweryfikowane skryptem Node: `<img onerror=...>` renderuje się teraz jako tekst
      (`&lt;img ...&gt;`), a prawdziwe słowo nadal poprawnie podświetlone.
- [x] **SEC-2: Path traversal w `POST /api/admin/restore`** ✅ 2026-08-05 —
      `backend/routers/admin.py:69-75`. `backup_filename` (surowy string z query) był
      sklejany bezpośrednio z `BACKUP_DIR`. **Naprawa:** `Path(backup_filename).name`
      przed sklejeniem (odrzuca separatory ścieżki/`..`). `backend/tests/test_backup_service.py`
      — 25 passed po zmianie.

### 🟡 Do uporządkowania

- [ ] **SEC-3: Trzy równoległe mechanizmy migracji DB** — `backend/alembic/` (skonfigurowany
      2026-07-25, ale nigdzie nie wywoływany), ad-hoc `ALTER TABLE` w `main.py:59-108` (błędy
      połykane cicho), osobny `backend/migrations/add_isimportant_to_flashcard.sql`. Ryzyko
      rozjazdu schematu — wybrać jeden mechanizm (brakuje tylko wpięcia `alembic upgrade head`
      w start, patrz sekcja „Przygotowanie do wdrożenia w chmurze" niżej).
- [ ] **DOC-1: CLAUDE.md nieaktualne** — lista routerów dokumentuje 10, realnie jest 19
      (brakuje m.in. `admin.py`, `auth.py`, `exercises.py`, `topics.py`, `voice_chat.py`,
      `youtube.py`, `settings.py`); stack frontendu opisany jako „React 18", realnie
      `react@^19.2.4` + `react-router-dom@^7`; twierdzenie że każda funkcja Gemini ma
      „hardcoded fallback" nieprawdziwe — tylko wywołania z jawnym `fallback=`
      (np. `flashcards.py:445,450`) je mają, reszta (`lesson_generator/*`, `news_service`,
      `youtube.py`) rzuca `ValueError` przy błędzie parsowania JSON zamiast degradować się.
- [x] **CLEAN-1: Zabłąkany plik** ✅ 2026-08-05 — `frontend/src/i18n/lingua_ai.db` (0 B,
      przypadkowy artefakt, nieśledzony w gicie) usunięty z dysku.
- [x] **GIT-1: Niezacommitowana zmiana w `frontend/index.html`** ✅ 2026-08-05 — usunięto
      diagnostyczny banner (`DIAG-BANNER`/`DIAG-7788`), zweryfikowane że strona nadal
      renderuje się poprawnie po usunięciu.
- [x] **BUG-5: `GET /` na porcie 8001 zwracał 500** ✅ 2026-08-05 (znaleziony przy
      uruchamianiu apki, nie w audycie) — `backend/main.py:315` sprawdzał istnienie
      katalogu `frontend-simple/`, ale katalog istniał pusty (bez `index.html`), więc
      `FileResponse` rzucał `RuntimeError`. **Naprawa:** warunek sprawdza teraz istnienie
      `frontend-simple/index.html`, nie samego katalogu — `/` zwraca czyste `404` gdy
      statyczny frontend nie jest zbudowany. Nie wpływa na normalny przepływ (frontend
      dev server na :5173 nigdy nie odpytuje `/` na :8001 bezpośrednio).

### 🟢 Pokrycie testami — luki

- [ ] Backend bez testów: `routers/admin.py` (najważniejsze, patrz SEC-2),
      `services/audio_service.py`, `services/analytics_service.py`,
      `services/flashcard_service.py`, `services/google_drive_service.py`,
      `services/obsidian_service.py`, `services/streak_service.py`,
      `services/sync_service.py`, `services/topic_service.py`.
- [ ] Frontend: 16/20 stron bez testu jednostkowego (w tym obie strony z SEC-1: Flashcards,
      TopicsPage) — `Conversation`, `DailyTest`, `Dictation`, `ErrorReview`, `Flashcards`,
      `LessonHistory`, `LoginAs`, `News`, `Practice`, `Profile`, `PronunciationTrainer`,
      `QuickMode`, `ReadAloud`, `Stats`, `TopicsPage`, `Videos`. (E2E Playwright w
      `frontend/e2e/*.spec.js`, w tym `security.spec.js`, częściowo łata tę lukę na poziomie
      przepływów — ale nie na poziomie jednostkowym tych komponentów.)

### ✅ Zweryfikowane jako OK (bez akcji)

CORS (jawna allowlista, nie `*`), brak SQL injection, brak hardkodowanych sekretów,
`ErrorBoundary` poprawnie owinięty (app-wide + per-route), ESLint 9 flat config działa,
offline/sync (`outboxDB`/`offlineQueue`) solidny z retry/dead-letter, VAPID exposuje tylko
klucz publiczny, `.gitignore` poprawny (`.db`/`.env`/audio/exports nieśledzone w gicie).

### Proponowana kolejność napraw
1. **SEC-1 + SEC-2** — najtańsze i najważniejsze: HTML-escape w highlight, `.name` w admin restore.
2. **GIT-1 + CLEAN-1** — trywialne sprzątanie przed kolejnym push.
3. **DOC-1** — odświeżyć CLAUDE.md (lista routerów, wersje React, prawdziwy zakres fallbacków).
4. **SEC-3** — wpiąć `alembic upgrade head` i usunąć ad-hoc migracje z `main.py`.

---

## ✅ PEŁNY PRZEGLĄD NA ŻYWO W PRZEGLĄDARCE (2026-07-27)

_Backend + frontend uruchomione, realna baza, przejście przez wszystkie strony i endpointy._

**Zweryfikowane działające (na żywo):** odczyt (lekcja, fiszki, ćwiczenia, tematy,
statystyki), zapis (ćwiczenie → ocena → FSRS), **generowanie AI po doładowaniu
OpenRouter** — auto-warianty (2 realne ćwiczenia), pełna nowa lekcja (~51s best
tier, komplet sekcji, +13 fiszek/+31 ćwiczeń w banku), test dnia (cache po 1.
generacji), rozmowa (wieloturowa), newsy, dyktando, read-aloud, quickmode, tips,
wymowa, add-ai. **Wszystkie 16 stron renderują się bez crashy i bez surowych kluczy.**

**🐛 Naprawione bugi znalezione podczas przeglądu:**
- [x] **Rozmowa: `sendMessage` nie wysyłał `user_id`** → backend wymaga go
      (weryfikacja właściciela sesji) → **każda wiadomość w rozmowie dawała 422**.
      Fix: `client.js` `sendMessage(...,  userId=getUserId())` + `user_id` w body.
- [x] **22 brakujące klucze i18n** (lesson/flash/stats) pokazywały surowe nazwy
      (`t()` zwraca klucz gdy brak, więc fallback `||` nie wchodził). Audyt
      statyczny wszystkich `t('literał')` → 0 braków po naprawie.

**⚠️ Do rozważenia (nie bug, obserwacja):**
- [ ] Generacja **testu dnia i lekcji na best tier trwa >110s** — blisko/ponad
      frontendowy timeout 120s (`client.js`). Pierwsza generacja może się rozjechać
      z timeoutem; po wygenerowaniu jest cache. Rozważyć niższy tier dla testu/lekcji
      albo podniesienie timeoutu, albo generowanie w tle ze statusem.
- Efekty uboczne testów na kontach testowych (id 4 „AllTest", id 5 „Verify User"):
  dodane lekcje/ćwiczenia/odpowiedzi — bez wpływu na konto „Mateusz" (id 6).

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
- [x] **Alembic: działający szkielet** ✅ 2026-07-25 — `alembic heads`/`check`/
      `upgrade head` działają. `env.py` przepisany: importuje wszystkie 10 modeli
      (pełne `target_metadata`), rozwiązuje cel z **`DATABASE_URL`** (env/.env) z
      fallbackiem do ini → te same migracje na SQLite lokalnie i PostgreSQL we
      wdrożeniu bez edycji plików; batch mode dla SQLite. Bazowa migracja
      `ff1cf77eb17f_baseline_schema` (`down_revision=None`) autogenerowana wobec
      pustej bazy — `alembic check` = „No new upgrade operations detected" (zero
      dryfu wobec modeli). Zweryfikowane: `upgrade head` na czystej bazie tworzy
      wszystkie 11 tabel. README z użyciem (m.in. `alembic stamp head` dla baz
      sprzed Alembica — schema wciąż powstaje przez `create_all`). Odblokowuje
      sekcję wdrożeniową (Postgres + migracje w entrypoincie kontenera).

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
- [x] **Ujednolicenie prefixów API do `/api/v1/*`** ✅ 2026-07-27 — addytywne
      aliasy: middleware w `main.py` przepisuje `/api/v1/X` → `/api/X` przed
      routingiem, więc **każdy endpoint jest osiągalny pod `/api/v1/*`**, a
      istniejące `/api/*` działają bez zmian (frontend, PWA cache, testy nietknięte).
      Natywne trasy v1 (`users`, `voice-chat`, `summary`) są **auto-wykrywane z
      `app.routes`** przy starcie (bez twardej listy — nowe trasy v1 nie wymagają
      edycji). Testy: `test_api_v1_alias.py` (5). 447 passed.
- [ ] Audyt modeli A1–A10 (sekcja niżej) — minimum A2+A3 przed INT-2 (koszty).
- [ ] **NIE wydzielać jeszcze FSRS jako wspólnej usługi** — to faza 3 MASTER_PLAN;
      LinguaAI pozostaje implementacją referencyjną do tego czasu.

_Źródło: audyt własny + `backend/services/model_router.py`_

---

## ✅ DO SPRAWDZENIA PRZEZ UŻYTKOWNIKA

- [ ] **Uruchomienie aplikacji na telefonie — wybór drogi** (pełne wyjaśnienie: `docs/PRODUCTION_AND_MOBILE.md`)
    - **Klucz VAPID i token dostępu to DWIE różne rzeczy:** VAPID = tylko powiadomienia push (opcjonalne); `APP_ACCESS_TOKEN` = zabezpieczenie przed obcymi przy wystawieniu na internet.
    - **Droga A (szybka, ta sama Wi-Fi, bez HTTPS):** `start.bat` → `ipconfig` (IPv4) → na telefonie `http://<IP>:5173`. Działa nauka, ale **bez instalacji jako appka i bez offline** (te wymagają HTTPS).
    - **Droga B (pełne PWA — ikona na ekranie, offline, push):** tunel HTTPS (`cloudflared`) → adres `https://*.trycloudflare.com` → odblokuj tokenem → „Dodaj do ekranu głównego".
    - [ ] (opcjonalnie) **Powiadomienia push:** `python -m backend.scripts.generate_vapid_keys` → wklej `VAPID_*` do `backend/.env` → na telefonie Profil → „Włącz powiadomienia" → „Wyślij test".
    - **Decyzja do podjęcia:** czy zostajemy na Drodze A (lokalnie), czy przygotowujemy stałe wystawienie (Droga B / chmura — sekcja wdrożeniowa niżej).

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
- [x] **Automatyczne (bez klikania) dogenerowanie po serii błędów na tej samej umiejętności** ✅ 2026-07-25
    - `exercise_service.skill_needs_auto_variant()`: sygnał „seria błędów" = agregatowa celność skilla ≤ 0.5 po ≥3 próbach (`AUTO_VARIANT_MIN_ATTEMPTS`/`AUTO_VARIANT_MAX_ACCURACY`), liczone z istniejących `times_seen`/`times_correct` — **bez nowej tabeli stanu**.
    - **Kontrakt „AI spend jawny i ograniczony" uszanowany:** bezpiecznik `AUTO_VARIANT_FRESH_TARGET=2` — nie generuje, jeśli w banku czekają już świeże (nieprzerobione) warianty tego skilla → jedno dogenerowanie na serię, nie jedno na każdy błąd. Odpowiedź zwraca `auto_generated`/`auto_generated_skill`/`_exercises`, więc wydatek jest widoczny mimo braku kliknięcia.
    - `routers/exercises.py answer_exercise`: wyzwalane **tylko na żywej błędnej odpowiedzi** (`client_event_id is None` — replay offline nigdy nie pali AI przy powrocie sieci; błąd generacji nie wywraca odpowiedzi).
    - `frontend Practice.jsx`: nowe ćwiczenia dokładane do bieżącej sesji od razu (wzmocnienie skilla, na którym się potyka) + baner „Widzę serię błędów na X — dołożyłem N zadań". Klucze `practice.autoGenerated` (PL+EN).
    - **UPDATE 2026-07-27 — drugi trigger: ZAPAMIĘTANIE.** `skill_memorized_needs_variant()`: gdy ćwiczenie widziane ≥`VARIANT_AFTER_TIMES_SEEN` (4×) i odpowiedź **poprawna** → uczeń mógł zapamiętać odpowiedź, nie regułę (Schmidt & Bjork) → nowy wariant tego samego skilla. Ten sam wspólny bezpiecznik (`_has_fresh_variants`) i jawność co ścieżka błędów. `answer_exercise` zwraca `auto_generated_reason` = `struggle`|`mastery`; front pokazuje inny baner (`practice.autoGeneratedMastery`). Domyka intencję: **błąd→wariant** ORAZ **zapamiętanie→wariant**. Testy: mastery unit + 2 endpointowe.
    - **UPDATE 2026-07-27 — B: błędy odcięte od generacji LEKCJI.** Konkretne błędy ćwiczeń już **nie** trafiają do promptu lekcji (usunięte z `get_today_lesson` i `generate_next_lesson`) — remediacja żyje w banku wariantów, lekcja adaptuje się przez słabe **tematy** + przeplatanie. Martwe `parse_lesson_exercise_errors` usunięte. Testy: `test_lesson_adaptivity.py` (asertują odcięcie + zachowane przeplatanie).
    - Testy łącznie: `test_exercise_auto_variant.py` (struggle+mastery), `test_lesson_adaptivity.py`. Backend 457 passed, frontend 75 passed, ruff czysty, build OK.
    - _Uwaga:_ live trigger nie odpalany masowo w przeglądarce, by nie palić kredytów; wcześniej auto-wariant potwierdzony na żywo (`auto_generated:2`).

### 📱 PWA / mobilka (2026-07-18) — ZROBIONE

- [x] `vite-plugin-pwa` + service worker (`registerType: autoUpdate`), manifest standalone ze skrótami do `/practice`, `/flashcards`, `/lesson`
- [x] Ikony PNG 192/512 + maskable + apple-touch-icon (wygenerowane z `logo.svg`, `frontend/public/icons/`) + meta iOS w `index.html`
- [x] Cache offline (`workbox.runtimeCaching`): ćwiczenia, lekcje, fiszki, staty (StaleWhileRevalidate) oraz `/audio/*` (CacheFirst, 30 dni)
- [x] `OfflineBanner` — informuje, że dane są z cache i że **zapis wymaga sieci**
- [x] `host: true` w dev + nowa sekcja `preview` z proxy (build też sięga do API)
- [x] **Zweryfikowane na żywo:** przy wyłączonym backendzie `/practice` renderuje komplet zadań z cache (200 z SW)
- [x] **Web Push (VAPID)** ✅ 2026-07-25 — powiadomienia push na telefon o powtórkach/lekcji
    - Backend: model `PushSubscription` (upsert po `endpoint`), `push_service` (send + prune 404/410, `push_enabled()` gdy oba klucze ustawione — graceful jak `DISCORD_WEBHOOK_URL`), router `/api/push/{vapid-public-key,subscribe,unsubscribe,test/{id}}`, config `VAPID_*` + skrypt `scripts/generate_vapid_keys.py`. `pywebpush` w deps. Migracja Alembic `5a6d111e51d9`.
    - Notifier: wysyła web push obok Discorda (poranny → lekcja, wieczorny → zaległe fiszki); odporny (błąd push nie wywraca runa).
    - Frontend: `push-sw.js` (handlery `push`/`notificationclick`) dołączony do wygenerowanego SW przez `workbox.importScripts`; `utils/push.js` (permission + PushManager.subscribe), `PushToggle` na stronie Profil (włącz/wyłącz per urządzenie + „Wyślij test").
    - Testy: `test_push.py` (12: subskrypcja/upsert/422/404, vapid-key enabled/disabled, test-send 503/deliver, send+prune 410, zachowanie przy błędzie przejściowym). Backend 442 passed, frontend 67 passed, build OK.
    - **Zweryfikowane na żywo:** `GET /api/push/vapid-public-key` z kluczami → `enabled:true` + klucz; podpisywanie VAPID (`py_vapid.sign`) działa z wygenerowanym kluczem; SW w dist zawiera `importScripts("push-sw.js")`.
    - _Do zrobienia przez użytkownika:_ wygenerować klucze (`python -m backend.scripts.generate_vapid_keys`), wkleić do `backend/.env`, i przetestować dostarczenie na realnym telefonie przez tunel HTTPS (push wymaga HTTPS + realnego push service — nie da się zweryfikować lokalnie).
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
- [x] **Offline dla ukończenia lekcji** ✅ 2026-07-25 — ten sam wzorzec co fiszki/ćwiczenia
    - `POST /api/lessons/{id}/complete` przyjmuje `client_event_id` (idempotencja przez `sync_events`) + `completed_at` (znacznik z urządzenia). Powtórka → `duplicate: true`, `xp_awarded: 0` — brak podwójnego XP/zepsutej passy. `IntegrityError` na wyścigu dwóch powtórek → też `duplicate`.
    - **Timing passy:** `completed_at` z urządzenia trafia do `lesson.completed_at`, a `calculate_streak` czyta właśnie tę kolumnę — lekcja skończona offline wczoraj, zsynchronizowana dziś, liczy się do wczoraj. Zegar z przyszłości przycinany (`parse_occurred_at`).
    - Kompatybilność wsteczna: online bez `client_event_id` działa jak wcześniej, zero wpisów w ledgerze. `xp_awarded` teraz odzwierciedla faktyczne przyznanie (25 tylko przy realnym ukończeniu).
    - `frontend`: `enqueueLessonComplete` + `KIND_LESSON` w offlineQueue, `replayLessonComplete` w client.js, handler w `useOfflineSync` (drenaż app-wide w OfflineBanner). `DailyLesson.handleComplete`: offline (`navigator.onLine === false`) lub błąd sieci bez statusu → kolejkuje + optymistycznie oznacza ukończone (cache lekcji + daily_tabs); reszta bez zmian.
    - Testy: `backend/tests/test_lesson_offline.py` (5) + `offlineQueue.test.js` (2). Backend 421 passed, frontend 67 passed, build OK.
    - _Uwaga:_ pełny live end-to-end (samolotowy → ukończ → powrót sieci) nie odpalony, by nie palić kredytów AI na generowanie lekcji — wzorzec identyczny z już zweryfikowanym offline fiszek/ćwiczeń.
- [x] **Prawdziwy Background Sync API** ✅ 2026-07-27 — SW odtwarza kolejkę offline
      przy zamkniętej aplikacji (Chromium). Podejście najniższego ryzyka: **nie
      ruszam zweryfikowanej ścieżki localStorage** (page-driven sync działa jak
      wcześniej), tylko **lustro w IndexedDB** (`utils/outboxDB.js`), bo SW nie
      czyta localStorage. Każdy enqueue mirroruje zdarzenie i rejestruje sync
      (`requestBackgroundSync`); `public/sync-sw.js` (dołączony przez
      `workbox.importScripts`) na zdarzeniu `sync` odtwarza z IndexedDB przez
      `fetch` (mapa `replayRequestFor`, wspólna logika z offlineQueue). Podwójne
      odtworzenie (page + SW) nieszkodliwe dzięki idempotencji `client_event_id`;
      każda strona sprząta swoje. Bezpieczne degradacje: bez IndexedDB/SyncManager
      (Firefox/Safari/iOS) → stary sync online/focus. Testy: `outboxDB.test.js`
      (4, fake-indexeddb) + `replayRequestFor` (4). 75 frontend passed, build OK,
      SW w dist zawiera `importScripts("push-sw.js","sync-sw.js")`.
      _Uwaga:_ samo zdarzenie `sync` przy zamkniętej apce weryfikowalne tylko na
      realnym urządzeniu (Chromium + HTTPS + zmiana sieci).
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

- [x] **Unicode/npm permanent fix** ✅ rozwiązane — projekt przeniesiony na
      `C:\Projects\LinguaAI` (ASCII, poza chmurą synchronizowaną), patrz CLAUDE.md
      „Lokalizacja i backup". Cold build wrócił do ~2s.
- [ ] **Docker frontend** – zbudować gotowy kontener frontendu (nginx) i zintegrować z docker‑compose (obecnie tylko backend w Dockerze)  
- [x] **Testy.exe** ✅ rozwiązane — `pytest` (backend, setki testów w `backend/tests/`) +
      `vitest` (frontend, `frontend/src/**/__tests__/`) + Playwright e2e smoke
      (`frontend/e2e/*.spec.js`: basic, navigation, auth, placement, lessons, full-flow,
      api-smoke, edge-cases, security).
- [ ] **Dokumentacja użytkownika** – przewodnik „Rozpoczęcie” ze zrzutami ekranu, FAQ (PDF/HTML)  

---

## ⚪️ Otwarte decyzje / wymagające ustalenia

- [ ] **Finalny wybór architektury** – pełna dockerizacja całego stacku vs. lokalne uruchamianie (backend+frontend z różnych ścieżek)  
- [x] **Ścieżki projektu** ✅ rozwiązane — kanoniczna ścieżka to `C:\Projects\LinguaAI` (ASCII, poza Google Drive), ustalone w CLAUDE.md.
- [x] **Backup DB** ✅ rozwiązane — `backend/scripts/backup_to_cloud.ps1` kopiuje `lingua_ai.db`
      do `C:\GoogleDriveSync\LinguaAI-backup\` codziennie o 20:00 przez zadanie
      `LinguaAI-DB-Backup` w Harmonogramie zadań (rejestracja w CLAUDE.md).
- [x] **Framework testów** ✅ rozwiązane — pytest (backend) + vitest (frontend) + Playwright (e2e), jak wyżej.
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
- [x] **Zainicjalizuj i skonfiguruj Alembic** ✅ 2026-07-25 — `env.py` czyta `DATABASE_URL`, importuje modele, batch mode dla SQLite (szczegóły w sekcji „⚠️ Drobne").  
- [x] Utwórz bazową migrację ✅ 2026-07-25 — `ff1cf77eb17f_baseline_schema` (pełny schemat, `alembic check` bez dryfu).  
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