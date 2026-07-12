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