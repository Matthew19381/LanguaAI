# TASKS – LinguaAI

_Ostatnia aktualizacja: 207-08_

_Źródło: FEEDBACK.md, własne implementacje_

---

## ✅ Zakończone (wybrane)

- Naprawiono problemy z audio (edge‑tts retry)  
- Dodano przyciski odtwarzania w różnych sekcjach  
- Spolszczono nazwy języków w UI  
- Usunięto niepotrzebne opóźnienia przy zmianie języka  
- Naprawiono liczenie lekcji, cache testów, promirty testowe, obsługę błędów, renderowanie markdowna, nawigację klawiaturą, filtrowanie fiszek, audio fiszek, statystyki ukończenia lekcji, itp.  
- Wszystkie zadania oznaczone `[x]` w poprzedniej wersji pliku są uznane za zakończone.  

---

## 📦 Backlog (do zrobienia)

- [ ] **Unicode/npm permanent fix** – zmiana nazwy katalogu projektu na ścieżkę bez znaków Unicode (np. `G:\\Projects\\LinguaAI`) lub migracja do WSL2, aby umożliwić pełny przepływ Docker/dev  
- [ ] **Docker frontend** – zbudować gotowy kontener frontendu (nginx) i zintegrować z docker‑compose (obecnie tylko backend w Dockerze)  
- [ ] **Testy.exe** – stworzyć zautomatyzowany zestaw testów: pytest (backend API) + Playwright/Cypress (testy UI smoke)  
- [ ] **Dokumentacja użytkownika** – przewodnik „Rozpoczęcie” ze zrzutami ekranu, FAQ (PDF/HTML)  

## ⚪️ Otwarte decyzje / wymagające ustalenia

- [ ] **Finalny wybór architektury** – pełna dockerizacja całego stacku vs. lokalne uruchamianie (backend+frontend z różnych ścieżek)  
- [ ] **Ścieżki projektu** – zmiana nazwy katalogu na ASCII (np. `C:\\LinguaAI` lub `G:\\Projects\\LinguaAI`) – rozwiązanie błędu npm Unicode  
- [ ] **Backup DB** – automatyzacja i lokalizacja kopii zapasowych (chmura? lokalny NAS?)  
- [ ] **Framework testów** – wybór (zalecane: pytest + Playwright)  
- [ ] **Format dokumentacji** – PDF vs online README oraz poziom szczegółowości  

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

- [ ] **NEURO‑4** Mechanizm shadowing z odtwarzaniem opóźnioným  
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

- [ ] **NEURO‑11** Zbieranie jakości snu od użytkownika  
    - Po wieczornej lekcji (lub o wybranej godzinie) wyświetl prośbę o ocenę snu w skali 1‑5.  
    - Zapisz tę wartość tymczasowo przy użytkowniku, a przy kolejnej recenzji fiszki wypełnij pole `sleep_quality` w modelu `Flashcard`.  
    - Zaktualizować endpoint `POST /flashcards/{id}/review` tak, aby przyjmował opcjonalne pole `sleep_quality` w żądaniu (lub osobny endpoint `/users/{id}/sleep`).  

- [ ] **NEURO‑12** Obliczanie bonusu za interleaving  
    - Podczas sesji nauki śledź unikalne tematy/lekcje (np. poprzez pole `lesson_topic` lub tagi w fiszkach).  
    - Na koniec sesji wyznacz `interleaving_bonus = min(1.0, unikalne_tematy / maksymalna_liczba_tematów_w_sesji)`.  
    - Przypisz tę wartość wszystkim fiszkom przeglądanych w tej sesji (lub jako średnią dobową dla użytkownika).  

- [ ] **NEURO‑13** Obliczanie kary za interferencję  
    - Dla każdej fiszki określ jej „znak” (np. kombinacja lekcji + temat + lista słów z tego samego korzenia).  
    - Przed każdą recenzją policz liczbę pozostałych fiszek w kolejce do powtórki o tym samym znaku (`similar_count`).  
    - Wykorzystaj istniejącą funkcję `calculate_interference_penalty` aby uzyskać `interference_penalty` i zapisać ją przy fiszce.  

- [ ] **NEURO‑14** Dodanie osiągnięć neuro‑nagród  
    Rozszerz `ACHIEVEMENT_DEFS` w `achievement_service.py` o:  
        * `first_sleep_rating` – „Pierwsza ocena snu” – użytkownik po raz pierwszy ocenił jakość snu po lekcji.  
        * `sleep_aware_streak_3` – „Sen‑świadomy” – 3 kolejne dni z oceną snu ≥ 4.  
        * `interleaver_master` – „Mistrz przeplatania” – średni `interleaving_bonus` ≥ 0.7 przez 5 dni.  
        * `low_interference` – „Precyzja interferencji” – średni `interference_penalty` < 0.1 przez 7 dni.  
        * `neuro_fsrs_explorer` – „Badacz neuro‑FSRS” – użytkownik wypróbował dwa różne zestawy wag neuro‑FSRS (tryb eksperymentalny).  
    Zaktualizować `check_and_award_achievements` tak, aby sprawdzał powyższe warunki (na podstawie dziennych średnich lub liczników dni).  

- [ ] **NEURO‑15** Dostosowanie wag neuro‑FSRS  
    - W `NeuroFSRSParams` uczynić pola `sleep_modulator_weight`, `time_of_day_weight`, `interleaving_bonus_weight`, `interference_penalty_weight` konfigurowalnymi przez użytkownika (endpoint `/users/{id}/neuro-settings`).  
    - Pozwól na włączenie trybu eksperymentalnego A/B, w którym losowo przydzielane są różne kombinacje wag i wyniki są logowane do późniejszej analizy.  

- [ ] **NEURO‑16** Integracja z czujnikami snu (opcjonalnie)  
    - Zaimplementować opcjonalne połączenie z Google Fit / Apple Health (poprzez ich REST API) aby automatycznie pobierać metryki snu (czas snu, fazy REM, głęboki, głęboki sen).  
    - Mapować te metryki na skalę 1‑5 `sleep_quality` lub bezpośrednio wykorzystać je w module `calculate_sleep_modulator`.  

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

## 📊 Priorytetowa macierz wdrożenia

| Feature                              | Wysiłek | Wpływ neuronaukowy | Specyfika niemiecka | Zależności                     |
|--------------------------------------|---------|--------------------|---------------------|--------------------------------|
| NEURO‑1 Harmonogram snu              | 🟢 Niski | ⭐⭐⭐⭐⭐             | Wysoki              | System powiadomień            |
| NEURO‑2 Generator i+1                | 🟡 Średni | ⭐⭐⭐⭐⭐             | Wysoki              | Śledzenie znanych słów        |
| NEURO‑3 Zmienna nagroda              | 🟢 Niski | ⭐⭐⭐               | Średni              | Serwis osiągnięć               |
| NEURO‑4 Shadowing                    | 🟡 Średni | ⭐⭐⭐⭐             | Wysoki              | Odtwarzacz audio               |
| NEURO‑5 Kotwice gestowe              | 🟡 Średni | ⭐⭐⭐⭐             | **Tylko niemiecki** | Interfejs wymowy               |
| NEURO‑6 3D artykulacja               | 🔴 Wysoki| ⭐⭐⭐               | Wysoki              | Three.js                       |
| NEURO‑7 Przeplatanie                 | 🟡 Średni | ⭐⭐⭐⭐             | Wysoki              | Serwis sesji                   |
| NEURO‑8 Neuro‑FSRS                   | 🔴 Wysoki| ⭐⭐⭐⭐⭐            | Średni              | Biblioteka FSRS                |
| NEURO‑9 Pałac pamięci                | 🔴 Wysoki| ⭐⭐⭐               | Średni              | Canvas/SVG                     |
| NEURO‑10 Społeczna AI                | 🔴 Bardzo wysoki | ⭐⭐⭐⭐      | Średni              | Dopasowanie LLM                |
| **NEURO‑11 Zbieranie snu**           | 🟢 Niski | ⭐⭐⭐⭐             | Średni              | UI prosty prompt, storage      |
| **NEURO‑12 Bonus interleaving**      | 🟡 Średni | ⭐⭐⭐⭐             | Średni              | Śledzenie tematów w sesji      |
| **NEURO‑13 Kara interferencja**      | 🟡 Średni | ⭐⭐⭐⭐             | Średni              | Porównywanie znaków fiszek     |
| **NEURO‑14 Osiągnięcia neuro**       | 🟢 Niski | ⭐⭐⭐               | Średni              | Rozszerzenie achievement_service|
| **NEURO‑15 Konfiguro wagi**          | 🟡 Średni | ⭐⭐⭐               | Średni              | Punkt końcowy ustawień użytk. |
| **NEURO‑16 Czujniki snu**            | 🔴 Wysoki| ⭐⭐⭐⭐             | Średni              | Integracja z Google Fit / Apple Health |

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

| Dziedzina                | Mechanizm neuronaukowy                | Implementacja                                     |
|--------------------------|---------------------------------------|---------------------------------------------------|
| **der/die/das**          | Pamięć proceduralna (ganglia bazalne) | Tryb ćwiczeń proceduralnych, nie deklaratywnych   |
| **Pozycja czasownika (V2 ) | Pamięć robocza (DLPFC)                | Ćwiczenia typu n‑back                             |
| **Trenmbare czasowniki** | Pamięć proceduralna + pamięć robocza  | Shadowing + sekwencje ruchowe                     |
| **Ü/Ö/CH/R**             | Kora ruchowa + móżdżek                | Kotwice gestowe + wizualizacja 3D artykulacji     |
| **Przypadki (Mian/Dopełniacz/Dzierżawczy/Biernik)**| Pamięć proceduralna                 | Ćwiczenia proceduralne przeplatane               |

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

*Uwaga: Niniejszy plik jest źródłem prawdy dotyczącym planowanych i już zrealizowanych zadań związanych z neuronaukowo uzasadnionymi funkcjami nauki języków. Aktualizuj go po każdym zakończonym etapie pracy.*

## 🚀 Produkcja i gotowość mobilna

### ✅ Natychmiastowa naprawa (dev)
- [ ] Dodaj skrypt migracji `backend/migrations/add_isimportant_to_flashcard.sql`.
- [ ] Zaktualizuj `backend/main.py`, aby automatycznie dodawał kolumnę `isImportant` przy starcie SQLite.

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
- [ ] Dodaj test jednostkowy potwierdzający, że pole `isImportant` pojawia się w odpowiedzi GET/POST `/api/flashcards/*`.
- [ ] Dodaj test punktu końcowego `/api/health` zwracającego `{status:"healthy"}`.
- [ ] Po gotowości PWA dodaj test Cypress/Playwright sprawdzający buforowanie offline tras lekcji i fiszek.