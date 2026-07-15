# TASKS – LinguaAI

_Ostatnia aktualizacja: 207-08_

_Źródło: FEEDBACK.md, własne implementacje_

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

---

## 🧠 Neuro‑naukowe funkcje językowe (Faza 2)

*Na podstawie badań z 2024‑2025 r. dotyczących nabywania języka.*

### Faza 2A – Optymalizacja snu i pamięci (wysoki (wysoki wpływ, mały nakład)

- [ ] **NEURO‑1** Harmonogram świadomości snu  
    - Backend: dodaj pole `session_type` (wieczór/rano/dzień) do modelu **Lesson**  
    - Frontend: planuj powiadomienia w optymalnych oknach kodowania/odtworzenia  
    - Integracja: opcjonalne śledzenie jakości snu (ręczne lub przez API wearables)  

- [ ] **NEURO‑2** Generator treści i+1 (kodowanie predykcyjne / zrozumiały input)  
    - Backend: nowy endpoint `/api/lessons/iplus1/{user_id}` – generuje tekst, w którym 90 % słów znanych, 10 % nowych  
    - Wykorzystuje `known_words` z fiszek oraz historię lekcji do kalibracji trudności  
    - Zwraca `i_plus_1_text`, `new_words_highlighted`, `cefr_level`  

- [ ] **NEURO‑3** Zmienna nagroda (optymalizacja dopaminy)  
    - Backend: rozszerz `achievement_service.py` o `surprise_loot` (15 % szans) oraz `prediction_bonus` (+50 % XP za trafne zgadywanie kontekstu)  
    - Frontend: animacja skrzyni z łupem, licznik „serii przewidywań”  
    - Config: `target_success_rate: 0.85` (strefa i+1)  

### Faza 2B – Motoryczna wymowa (wysoki wpływ, średni nakład)

- [ ] **NEURO‑4** Mechanizm shadowing z odtwarzaniem opóźnioním  
    - Frontend: odtwarzacz audio z konfigurowalnym opóźnieniem (domyślnie 0,5 s) – słuchaj → mów z przesunięciem  
    - Synchronizacja fali dźwiękowej, tryb „choralny” (użytkownik + AI jednocześnie)  

- [ ] **NEURO‑5** Kotwice gestowe dla fonetów niemieckich  
    - Mapowanie: 🤲 „ch” (ich/ach), 👉 „ü/ö”, 🤏 „r” (uvular), ✋ „sch”, 👌 „pf/ts”  
    - Frontend: karta z podpowiedzią gestu podczas treningu wymowy  
    - Backend: przechowuj `gesture_anchor` przy fiszce/frazie  

- [ ] **NEURO‑6** Wizualizacja artykulacji (3D)  
    - Frontend: animacja języka/podniebienia w Three.js/WebGL dla dźwięków niemieckich  
    - Przełącznik w `PronunciationTrainer`: „Pokaż artykulację”  

### Faza 2C – Przeplatanie i pożądane trudności (wysoki wpływ)

- [ ] **NEURO‑7** Mieszacz sesji (interleaving)  
    - Backend: usługa `session_mixer` – miesza bloki słownictwa/gramatyki/wymowy/słuchania/produkcji  
    - Specyfika niemiecka: ćwiczenia proceduralne `der/die/das`, pamięć robocza `verb_position` (n‑back), wymowa → kora ruchowa  
    - Algorytm: maksymalizacja interferencji kontekstowej  

- [ ] **NEURO‑8** Neuro‑uświadomiony FSRS V2  
    - Rozszerz parametry FSRS o: `sleep_cycles_since_review`, `time_of_day_factor`, `interleaving_bonus`, `interference_penalty`  
    - Wzór: `R = S * exp(-t/S) * sleep_modulator * interference_modulator`  
    - Śledź: `sleep_quality` (1‑5), `time_of_day` (rano/wieczór), `session_type`  

### Faza 2C – Embodiment i słownictwo przestrzenne (średni wpływ)

- [ ] **NEURO‑9** Pałac pamięci / mapa słownictwa przestrzennego  
    - Frontend: siatka 2D „Pałac pamięci” – pokoje = tematy, obiekty = słowa  
    - Kliknięcie w pokój → pokaz słów z kontekstem przestrzennym  
    - Backend: przechowuj `spatial_anchor` (x,y,room) przy fiszce  

- [ ] **NEURO‑10** Społeczne kodowanie predykcyjne (AI rozmowa)  
    - Backend: model przewidywania tury (kiedy użytkownik kończy wypowiedź)  
    - Korekcja błędów w czasie rzeczywistym (błąd predykcji = sygnał uczenia się)  
    - Agentowie oparte na osobowości z modelowaniem Teorii Umysłu  

### **Udoskonalenia neuro‑FSRS i zbieranie danych** (nowe zadania)

- [x] **NEURO‑11** Zbieranie jakości snu od użytkownika  ✅
    - Endpoint `POST /api/v1/users/{id}/sleep` zapisuje jakość snu w `User.sleep_data` (JSON: historia + `last_sleep_quality`).  \
    - Endpoint `POST /api/v1/flashcards/{id}/review` odczytuje `last_sleep_quality` użytkownika i przekazuje do `NeuroCardState.sleep_quality` (pliki: `backend/routers/users.py`, `backend/routers/flashcards.py`).  \
    - Testy: `backend/tests/test_users.py`, `backend/tests/test_flashcards.py`.

- [x] **NEURO‑12** Obliczanie bonusu za interleaving  ✅
    - W `review_flashcard` liczymy liczbę unikalnych `lesson_topic` wśród fiszek do powtórki (`due_cards`) i ustawiamy `interleaving_bonus = min(1.0, unikalne_tematy/10)`. Wartość trafia do `NeuroCardState` i `Flashcard.interleaving_bonus`.

- [x] **NEURO‑13** Obliczanie kary za interferencję  ✅
    - W `review_flashcard` liczymy fiszki do powtórki o tym samym `lesson_topic` co oceniana karta (`same_topic_count`) i ustawiamy `interference_penalty = min(0.3, same_topic_count/5*0.3)`. Przekazywane do `neuro_fsrs_next_interval(similar_count=same_topic_count+1)`.

- [x] **NEURO‑14** Dodanie nowych osiągnięć związanych z neuro‑FSRS  ✅
    - Nowe osiągnięcia: `sleep_tracker` (3 wpisy snu) i `neuro_tuned` (pierwsza zmiana wag) w `backend/services/achievement_service.py`. Przyznawane w `backend/routers/users.py`.

- [x] **NEURO‑15** Konfigurowalne wagi neuro‑FSRS  ✅
    - Endpointy `GET`/`PATCH /api/v1/users/{id}/neuro-weights` z walidacją zakresów. Funkcja `neuro_fsrs_params_from_user()` w `backend/services/fsrs_neuro.py` buduje `NeuroFSRSParams` z wag użytkownika; używana w `review_flashcard`.

- [x] **NEURO‑16** Czujniki snu (integracja z Google Fit / Apple Health)  ✅ (szkic)
    - Endpoint `POST /api/v1/users/{id}/sync-sleep` przyjmuje payload z `source` (`google_fit`/`apple_health`), `sleep_score` (0‑100 → normalizowane do 1‑5) lub `sleep_quality` (1‑5). Punkt integracji dla OAuth w tle (todo: `backend/services/sleep_sensor_service.py`).

### Faza 2D – Pozostałe (z poprzedniej listy, bez zmian)

- [ ] **NEURO‑1** … (jak wyżej)  
- [ ] **NEURO‑2** …  
- [ ] **NEURO‑3** …  
- [ ] **NEURO‑4** …  
- [ ] **NEURO‑5** …  
- [ ] **NEURO‑6** …  
- [ ] **NEURO‑7** …  
- [ ] **NEURO‑8** …  
- [ ] **NEURO‑9** …  
- [ ] **NEURO‑10** …  

---

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

---

## 📊 Priorytetowa macierz wdrożenia

|| Feature                              | Wysiłek | Wpływ neuronaukowy | Specyfika niemiecka | Zależności                     |
|--------------------------------------|---------|--------------------|---------------------|--------------------------------|
|| NEURO‑1 Harmonogram snu              | 🟢 Niski | ⭐⭐⭐⭐⭐             | Wysoki              | System powiadomień            |
|| NEURO‑2 Generator i+1                | 🟡 Średni | ⭐⭐⭐⭐⭐             | Wysoki              | Śledzenie znanych słów        |
|| NEURO‑3 Zmienna nagroda              | 🟢 Niski | ⭐⭐⭐               | Średni              | Serwis osiągnięć               |
|| NEURO‑4 Shadowing                    | 🟡 Średni | ⭐⭐⭐⭐             | Wysoki              | Odtwarzacz audio               |
|| NEURO‑5 Kotwice gestowe              | 🟡 Średni | ⭐⭐⭐⭐             | **Tylko niemiecki** | Interfejs wymowy               |
|| NEURO‑6 3D artykulacja               | 🔴 Wysoki| ⭐⭐⭐               | Wysoki              | Three.js                       |
|| NEURO‑7 Przeplatanie                 | 🟡 Średni | ⭐⭐⭐⭐             | Wysoki              | Serwis sesji                   |
|| NEURO‑8 Neuro‑FSRS                   | 🔴 Wysoki| ⭐⭐⭐⭐⭐            | Średni              | Biblioteka FSRS                |
|| NEURO‑9 Pałac pamięci                | 🔴 Wysoki| ⭐⭐⭐               | Średni              | Canvas/SVG                     |
|| NEURO‑10 Społeczna AI                | 🔴 Bardzo wysoki | ⭐⭐⭐⭐      | Średni              | Dopasowanie LLM                |
|| **NEURO‑11 Zbieranie snu**           | 🟢 Niski | ⭐⭐⭐⭐             | Średni              | UI prosty prompt, storage      |
|| **NEURO‑12 Bonus interleaving**      | 🟡 Średni | ⭐⭐⭐⭐             | Średni              | Śledzenie tematów w sesji      |
|| **NEURO‑13 Kara interferencja**      | 🟡 Średni | ⭐⭐⭐⭐             | Średni              | Porównywanie znaków fiszek     |
|| **NEURO‑14 Osiągnięcia neuro**       | 🟢 Niski | ⭐⭐⭐               | Średni              | Rozszerzenie achievement_service|
|| **NEURO‑15 Konfiguro wagi**          | 🟡 Średni | ⭐⭐⭐               | Średni              | Punkt końcowy ustawień użytk. |
|| **NEURO‑16 Czujniki snu**            | 🔴 Wysoki| ⭐⭐⭐⭐             | Średni              | Integracja z Google Fit / Apple Health |

---

## 🚀 Zalecany MVP (tygodnie 1‑4)

1. **Tydzień 1**: NEURO‑1 (Harmonogram snu) + NEURO‑3 (Zmienna nagroda) + **NEURO‑11** (Zbieranie snu)  
2. **Tydzień 2**: NEURO‑2 (Generator i+1) + NEURO‑4 (Shadowing) + **NEURO‑12** (Bonus interleaving) + **NEURO‑13** (Kara interferencja)  
3. **Tydzień 3**: NEURO‑5 (Kotwice gestowe) + NEURO‑7 (Przeplatanie) + **NEURO‑14** (Osiągnięcia neuro)  
4. **Tydzień 4**: NEURO‑8 (Neuro‑FSRS – już wdrożone, jedynie konfiguracja wag **NEURO‑15**) + ewaluacja oraz przygotowanie do opcjonalnej integracji **NEURO‑16** (czujniki snu)  

Po zakończeniu tego cyklu podstawowe funkcje neuronaukowe będą dostępne i przetestowane, a system będzie lepiej wspierał szybkość postępów w nauce języka niemieckiego poprzez wykorzystanie mechanizmów snu, interleafingu, modulacji dopaminowej oraz motorycznego zaangażowania.

---

## 📋 Analiza kodu (do wykonania)

- [ ] Przeskanować `backend/services/lesson_generator.py` pod kątem punktów integracji i+1  
- [ ] Przeskanować `backend/services/achievement_service.py` pod kątem rozbudowy systemu nagród (nowe NEURO‑achievements)  
- [ ] Przeskanować `backend/models/lesson.py` pod kątem pola `session_type`  
- [ ] Przeskanować `frontend/src/components/Playbutton.jsx` pod kątem obsługi opóźnienia (shadowing)  
- [ ] Przeskanować `frontend/src/pages/PronunciationTrainer.jsx` pod kątem integracji gestów oraz wizualizacji 3D  
- [ ] Przeskanować `backend/services/test_generator.py` pod kątem logiki przeplatania  
- [ ] Przeskanować `backend/services/flashcard_service.py` pod kątem kotwic przestrzennych (`spatial_anchor`)  
- [ ] Przejrzeć integrację biblioteki `fsrs` pod kątem parametrów Neuro‑FSRS  
- [ ] Zaimplementować i przetestować nowe zadania **NEURO‑11** … **NEURO‑15** (powyżej)  

---

## 🇩🇪 Niemiecko‑specyficzne adaptacje neuronaukowe

|| Dziedzina                | Mechanizm neuronaukowy                | Implementacja                                     |
|--------------------------|---------------------------------------|---------------------------------------------------|
|| **der/die/das**          | Pamięć proceduralna (ganglia bazalne) | Tryb ćwiczeń proceduralnych, nie deklaratywnych   |
|| **Pozycja czasownika (V2 ) | Pamięć robocza (DLPFC)                | Ćwiczenia typu n‑back                             |
|| **Trenmbare czasowniki** | Pamięć proceduralna + pamięć robocza  | Shadowing + sekwencje ruchowe                     |
|| **Ü/Ö/CH/R**             | Kora ruchowa + móżdżek                | Kotwice gestowe + wizualizacja 3D artykulacji     |
|| **Przypadki (Mian/Dopełniacz/Dzierżawczy/Biernik)**| Pamięć proceduralna                 | Ćwiczenia proceduralne przeplatane               |

---

## 📚 Źródła badań (kluczowe prace)

- Diekelmann & Born (2010) – konsolidacja pamięci podczas snu  
- Friston (2010) – kodowanie predykcyjne / zasada wolnej energii  
- Schultz (2016) – błąd przewidywania dopaminy  
- Pulvermüller & Fadiga (2010) – teoria ruchowa percepcji mowy  
- Ullman (2004) – model deklaratywno/proceduralny języka  
- Rohrer & Taylor (2007) – przeplatanie / interferencja kontekstowa  
- Bjork & Bjork (1992) – pożądane trudności  
- Rasch & Born (2013) – sen i konsolidacja pamięci  
- Guenther (2016) – neuronalna kontrola produkcji mowy  
- Krashen (1985) + walidacja współczesna – zrozumiały input (i+1)  

---

## 📓 Rejestr zmian

- **2026-07-06**: Dodano funkcje neuronaukowe (Faza)  
- **2026-07-08**: Zaktualizowano TASKS.md – usunięto zakończone zadania, dodano szczegółowe zadania neuro‑FSRS, osiągnięcia, zbieranie danych snu, interleaving, interferencja, konfigurację wag, nowe osiągnięcia oraz analizę kodu.  
- **2026-07-10**: Zaktualizowano TASKS.md – oznaczone jako zakończone zadania związane z dodaniem kolumny `isImportant` i automatycznym dodawaniem kolumn przy starcie SQLite oraz dodanie testów jednostkowych dla pola `isImportant`.  

*Uwaga: Niniejszy plik jest źródłem prawdy dotyczącym planowanych i już zrealizowanych zadań związanych z neuronaukowo uzasadnionymi funkcjami nauki języków. Aktualizuj go po każdym zakończonym etapie pracy.*

---

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
- `gemini_service` nie ma fallbacku JSON przy błędzie AI — rzuca `ValueError` → 500. CLAUDE.md obiecuje "hardcoded fallback dict" w każdej funkcji; zrealizowane tylko w `daily_lesson`/`conversation`, NIE w `analyze_test_errors`/`analyze_conversation`/itp. (routery łapią `httpx.RequestError` → 503, ale błąd parsowania JSON → 500).
- `fsrs_neuro.py` to samodzielna heurystyka NEURO (sen/circadian/interference) — ciekawa, ale nie używa lib `fsrs`, więc jej interwały są przybliżeniem, nie kalibrowanym FSRS.

---

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