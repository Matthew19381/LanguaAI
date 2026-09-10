# DONE_CHECKLIST — LinguaAI (wzorzec ekosystemu)

Wersja 1.0 · utworzono 2026-09-10 · zadanie t_0900e3c2
Status: **WZORZEC** — do skopiowania/adaptacji dla pozostałych projektów.

Definicja: **DONE = mogę spokojnie sprawdzić i wszystko działa zgodnie z założeniami.**
Nie „testy przeszły u bota", tylko „właściciel siada, klika i to działa".

Każdy punkt ma: komendę do wklejenia, oczekiwany wynik, warunek FAIL.
Wszystkie komendy poniżej **zostały wykonane 2026-09-10** — nie są propozycją,
tylko zapisem tego, co realnie działa na tej maszynie.

---

## 0. Zasada nadrzędna: G0 przed wszystkim

Punkty G1–G7 mogą świecić na zielono przy aplikacji, która **nie wstaje**.
Tak było 2026-09-10: 519/519 testów backendu + 116/116 frontendu przechodziło,
a serwer wychodził z kodem 3 przy starcie. Testy używają własnej bazy testowej
i nigdy nie dotykają bazy produkcyjnej — więc nie widzą tej klasy błędu.

**Dlatego G0 (smoke realnego startu) jest pierwszy i jest blokujący.**
Zielone testy przy martwej aplikacji to najgroźniejszy fałszywy pozytyw w tym projekcie.

---

## G0. Aplikacja realnie wstaje i odpowiada na produkcyjnej bazie [BLOKUJĄCY]

Warunek: uruchomienie na **tej bazie, której używa właściciel**, nie na świeżej/testowej.

```bash
cd /c/Projects/LinguaAI
PYTHONPATH= "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" \
  -m uvicorn backend.main:app --port 8001 --host 127.0.0.1
```

OK: w logu pojawia się `Application startup complete` i proces **żyje dalej**.
FAIL: proces kończy się (exit code 3) na etapie
`Applying database migrations (alembic upgrade head)`.

Smoke endpointów — dopiero gdy proces żyje:

```bash
for ep in /api/health "/api/flashcards/1/due" "/api/topics/1/due"; do
  echo "$ep -> $(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:8001$ep)"
done
```

OK (zweryfikowane): `/api/health -> 200`, `/api/flashcards/1/due -> 200`,
`/api/topics/1/due -> 200`. `/api/health` zwraca
`{"status":"healthy","service":"LinguaAI API","version":"1.0.0"}`.

Pułapki potwierdzone empirycznie:
- Endpoint zdrowia to **`/api/health`, nie `/health`** — `/health` daje 404. Nie diagnozuj tego jako awarii.
- `/api/flashcards/due` bez `user_id` → 422; poprawna ścieżka to `/api/flashcards/{user_id}/due`.
- Brak `/api/integration/due_reviews` pod tą nazwą — sprawdzaj realne ścieżki w `/openapi.json`,
  nie w dokumentacji.
- Uruchomienie „wisi bez odpowiedzi" ≠ uruchomienie działa. Sprawdź `process poll` —
  proces mógł już wyjść, a curl zwraca `000` (brak połączenia), nie błąd HTTP.

## G0b. Spójność migracji z bazą produkcyjną [BLOKUJĄCY]

Najczęstsza przyczyna FAIL w G0 i jedyna, której testy nie wykryją.

```bash
cd /c/Projects/LinguaAI/backend
PYTHONPATH= "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" -m alembic heads
PYTHONPATH= "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" -m alembic current
```

OK: `current` == `heads` (obecnie `9792016c36df (head)`).
FAIL: rozjazd rewizji.

Uwaga na **dwie bazy o tej samej nazwie** — to realna pułapka tego projektu:

| Plik | Rola | Stan 2026-09-10 |
|---|---|---|
| `C:\Projects\LinguaAI\lingua_ai.db` | **produkcyjna** (253 fiszki, 52 tematy, 5 użytkowników) | rewizja `ff1cf77eb17f` — ZA STARA |
| `C:\Projects\LinguaAI\backend\lingua_ai.db` | pusta (0 fiszek) | rewizja `9792016c36df` (head) |

`alembic` uruchamiany z `backend/` widzi tę **pustą**, więc raportuje „head" —
podczas gdy aplikacja startowana z katalogu głównego ładuje tę **produkcyjną** i pada.
`alembic current` sam w sobie potrafi więc skłamać. Zawsze sprawdzaj, na którą bazę patrzysz.

Reguła: **nie ufaj `alembic current` bez sprawdzenia, czy baza ma dane.**

## G0c. Migracja nie wywraca się na istniejącym schemacie [BLOKUJĄCY]

Rewizje LinguaAI zakładają czystą bazę i wywracają się na bazie, która ma już te obiekty
(dziedzictwo „ewolucji SQLite bez Alembica"). Zaobserwowane 2026-09-10:

- `5a6d111e51d9` → `table push_subscriptions already exists`
- `9c1a1e9b7b4f` → `duplicate column name: mnemonic_image_path`

Weryfikuj **zawsze na kopii**, nigdy na oryginale:

```bash
cp /c/Projects/LinguaAI/lingua_ai.db /tmp/probna.db
cd /c/Projects/LinguaAI/backend
PYTHONPATH= DATABASE_URL="sqlite:///C:/pelna/sciezka/probna.db" \
  "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" -m alembic upgrade head
```

OK: kończy się bez traceback.
FAIL: `OperationalError` — schemat bazy wyprzedza jej rewizję.

## G1. Testy backendu

```bash
cd /c/Projects/LinguaAI
PYTHONPATH= "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" -m pytest -q
```

OK: `519 passed` (~30 s). Baseline 2026-09-10: **519** (poprzedni 517, +2 bez regresji).
FAIL: mniej niż 519 albo jakikolwiek `failed`.

Puste `PYTHONPATH=` i pełna ścieżka do `pythoncore-3.11-64` są **konieczne** — gołe
`python -m pytest` trafia na interpreter Hermesa i daje
`ModuleNotFoundError: No module named 'fsrs'`. To artefakt środowiska agenta,
**nie błąd projektu** — nie diagnozuj go jako buga.

## G2. Testy frontendu

```bash
cd /c/Projects/LinguaAI/frontend && npm test
```

OK: `Test Files 13 passed (13)`, `Tests 116 passed (116)`. Baseline: **116**.
FAIL: spadek poniżej 116 = regresja, zgłoś jawnie.

## G3. Ruff czysty — z rozróżnieniem szumu od realnego długu

```bash
cd /c/Projects/LinguaAI
PYTHONPATH= "C:/Users/Acer/AppData/Local/Python/pythoncore-3.11-64/python.exe" \
  -m ruff check . --output-format=concise
```

OK: 0 błędów **w plikach śledzonych przez git**.
Stan 2026-09-10: 6 błędów, ale **wszystkie w plikach spoza repozytorium**
(`.worktrees/`, `fix_database.py`, `test_edge_tts.py` — nieśledzone scratch/agentowe).

Reguła: zanim zgłosisz „ruff brudny", odetnij nieśledzone:
```bash
git status --short   # pliki z "??" nie liczą się do bramki
```
Ale: nieśledzone śmieci w katalogu głównym to osobny dług — patrz G6.

## G4. ESLint bez błędów

```bash
cd /c/Projects/LinguaAI/frontend && npm run lint
```

OK: **0 errors**. Warningi (~49–50) są tolerowane jako zastane — liczy się brak wzrostu.
FAIL 2026-09-10: `51 problems (1 error, 50 warnings)` — **1 błąd, baseline miał 0**:
`Practice.jsx:301 — React Hook "useEffect" is called conditionally` (`react-hooks/rules-of-hooks`).
To nie jest kosmetyka: warunkowy hook łamie kolejność hooków Reacta i daje realne
błędy w czasie działania. Powiązane z niescommitowanymi zmianami w `Practice.jsx`.

## G5. Stan repozytorium

```bash
cd /c/Projects/LinguaAI
git status --short
git log origin/master..HEAD --oneline    # nic = wszystko wypchnięte
```

OK: brak zmian w plikach śledzonych, nic niewypchniętego.
FAIL 2026-09-10: **9 zmodyfikowanych plików śledzonych**, w tym warstwa ćwiczeń
(`backend/models/exercise.py`, `backend/routers/exercises.py`,
`backend/services/exercise_service.py`) i frontend (`Practice.jsx`, `DailyLesson.jsx`,
`SpecialChars.jsx`, `translations.js`) plus `CHANGELOG.md`, `docs/PRODUCTION_AND_MOBILE.md`.
Commity są wypchnięte (`origin/master..HEAD` puste), ale praca w toku nie jest zapisana.

Reguła: **niescommitowana praca w toku = NIE DONE**, nawet jeśli testy przechodzą.
Właściciel nie może „spokojnie sprawdzić" stanu, którego nie ma w historii.

## G6. Katalog roboczy bez śmieci

```bash
git status --short | grep '^??'
```

OK: pusto lub wyłącznie świadomie ignorowane.
FAIL 2026-09-10: `.worktrees/`, `fix_database.py`, `test_edge_tts.py`,
`backend/tests/test_image_service.py` — nieśledzone. Ostatni to **plik testowy poza
repozytorium**: jego testy mogą lokalnie przechodzić i znikać w CI.
Decyzja: dodać do repo albo do `.gitignore` — nie zostawiać w zawieszeniu.

## G7. Dokumentacja zgodna ze stanem faktycznym

Sprawdź, czy liczby w dokumentach zgadzają się z tym, co właśnie zmierzyłeś:

```bash
cd /c/Projects/LinguaAI
grep -rn "517\|519\|116" TASKS.md CHANGELOG.md docs/*.md | head
```

OK: liczby testów w `TASKS.md`/`CHANGELOG.md` == wynik G1/G2.
FAIL: rozjazd. Stan 2026-09-10: dokumenty deklarują **517** backendu, realnie jest **519**
— do aktualizacji. `TASKS.md` trzyma najnowsze wpisy **na górze**.

Dodatkowo: `docs/NEURO_FEATURES.md` to standard dowodowy ekosystemu — zmiany w FSRS
lub logice powtórek wymagają aktualizacji tam, a nie tylko w CHANGELOG.

---

## Bramka końcowa

DONE wolno ogłosić **tylko** gdy G0 + G0b + G0c są zielone **i** G1–G7 są zielone
lub mają jawnie zapisane, świadome odstępstwo.

Kolejność jest istotna: G0 pierwszy, bo najtaniej wykrywa najgroźniejszy błąd.
Jeśli G0 jest czerwony, reszta jest bez znaczenia — aplikacja nie działa,
niezależnie od tego, ile testów przechodzi.

Stan LinguaAI 2026-09-10 według tej checklisty:
G0 **FAIL** · G0b **FAIL** · G0c **FAIL** · G1 OK (519) · G2 OK (116) ·
G3 OK z zastrzeżeniem · G4 **FAIL** (1 error) · G5 **FAIL** · G6 **FAIL** · G7 **FAIL**

→ **LinguaAI nie jest DONE.** Aplikacja nie wstaje na bazie właściciela.

---

## Jak adaptować do innych projektów

Szkielet jest przenośny, konkrety nie. Przy kopiowaniu:

1. **Zachowaj strukturę G0-przed-G1.** To główna lekcja tego wzorca: bramka
   „aplikacja realnie wstaje na danych właściciela" musi wyprzedzać bramki testowe.
   Zielone testy przy martwej aplikacji zdarzają się w każdym projekcie z migracjami.
2. **Wymień komendy na zweryfikowane w danym projekcie.** Nie kopiuj ścieżki
   `pythoncore-3.11-64` ani portu 8001 w ciemno — każdy projekt ma swoje.
   Każdą komendę uruchom raz, zanim wpiszesz ją do checklisty.
3. **Wpisz realne baseline'y liczbowe** (liczba testów, liczba warningów).
   Bramka bez liczby jest nieweryfikowalna — „testy przechodzą" nie wykrywa regresji z 519 na 400.
4. **Dopisz pułapki specyficzne dla projektu** w miejscu, gdzie się o nie potkniesz,
   nie w osobnym rozdziale na końcu.
5. **Rozróżniaj FAIL blokujący od zastanego długu** (jak warningi eslinta) —
   checklista, która zawsze świeci na czerwono, przestaje być czytana.
