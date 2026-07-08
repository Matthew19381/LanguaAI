# TASKS – LinguaAI

_Ostatnia aktualizacja: 2026-07-08_

_Źródło: FEEDBACK.md, własne implementacje_

---

## ✅ Zakończone (wybrane)

- Naprawiono problemy z audio (edge‑tts retry)  
- Dodano przyciski odtwarzania w różnych sekcjach  
- Spolszczono nazwy języków w UI  
- Usunięto niepotrzebne opóźnienia przy zmianie języka  
- Naprawiono liczenie lekcji, cache testów, prompty testowe, obsługę błędów, renderowanie markdowna, nawigację klawiaturą, filtrowanie fiszek, audio fiszek, statystyki ukończenia lekcji, itp.  
- Wszystkie zadania oznaczone `[x]` w poprzedniej wersji pliku są uznane za ukończone.

---

## 📦 Backlog (do zrobienia)

- [ ] **Unicode/npm permanent fix** – zmiana nazwy katalogu projektu na ścieżkę bez znaków Unicode (np. `G:\Projects\LinguaAI`) lub migracja do WSL2, aby umożliwić pełny przepływ Docker/dev  
- [ ] **Docker frontend** – zbudować gotowy kontener frontendu (nginx) i zintegrować z docker‑compose (obecnie tylko backend w Dockerze)  
- [ ] **Testy.exe** – stworzyć zautomatyzowany zestaw testów: pytest (backend API) + Playwright/Cypress (testy UI smoke)  
- [ ] **Dokumentacja użytkownika** – przewodnik „Rozpoczęcie” ze zrzutami ekranu, FAQ (PDF/HTML)  

## ⚪️ Otwarte decyzje / wymagające ustalenia

- [ ] **Finalny wybór architektury** – pełna dockerizacja całego stacku vs. lokalne uruchamianie (backend+frontend z różnych ścieżek)  
- [ ] **Ścieżki projektu** – zmiana nazwy katalogu na ASCII (np. `C:\LinguaAI` lub `G:\Projects\LinguaAI`) – rozwiązanie błędu npm Unicode  
- [ ] **Backup DB** – automatyzacja i lokalizacja kopii zapasowych (chmura? lokalny NAS?)  
- [ ] **Framework testów** – wybór (zalecane: pytest + Playwright)  
- [ ] **Format dokumentacji** – PDF vs online README oraz poziom szczegółowości  

## 🧠 Neuro‑naukowe funkcje językowe (Faza 2)

*Na podstawie badań z 2024‑2025 r. dotyczących nabywania języka.*

### Faza 2A – Optymalizacja snu i pamięci (wysoki wpływ, mały nakład)

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

- [ ] **NEURO‑4** Mechanizm shadowing z odtwarzaniem opóźnionym  
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

---

## 🚀 Zalecany MVP (tygodnie 1‑4)

1. **Tydzień 1**: NEURO‑1 (Harmonogram snu) + NEURO‑3 (Zmienna nagroda)  
2. **Tydzień 2**: NEURO‑2 (Generator i+1) + NEURO‑4 (Shadowing)  
3. **Tydzień 3**: NEURO‑5 (Kotwice gestowe) + NEURO‑7 (Przeplatanie)  
4. **Tydzień 4**: NEURO‑8 (Neuro‑FSRS) – rdzenna aktualizacja algorytmu  

---

## � realiza analiza kodu (do wykonania)

- [ ] Przeskanować `backend/services/lesson_generator.py` pod kątem punktów integracji i+1  
- [ ] Przeskanować `backend/services/achievement_service.py` pod kątem rozbudowy systemu nagród  
- [ ] Przeskanować `backend/models/lesson.py` pod kątem pola `session_type`  
- [ ] Przeskanować `frontend/src/components/PlayButton.jsx` pod kątem obsługi opóźnienia (shadowing)  
- [ ] Przeskanować `frontend/src/pages/PronunciationTrainer.jsx` pod kątem integracji gestów oraz wizualizacji 3D  
- [ ] Przeskanować `backend/services/test_generator.py` pod kątem logiki przeplatania  
- [ ] Przeskanować `backend/services/flashcard_service.py` pod kątem kotwic przestrzennych (`spatial_anchor`)  
- [ ] Przejrzeć integrację biblioteki `fsrs` pod kątem parametrów Neuro‑FSRS  

---

## 🇩🇪 Niemiecko‑specyficzne adaptacje neuronaukowe

| Dziedzina                | Mechanizm neuronaukowy                | Implementacja                                     |
|--------------------------|---------------------------------------|---------------------------------------------------|
| **der/die/das**          | Pamięć proceduralna (ganglia bazalne) | Tryb ćwiczeń proceduralnych, nie deklaratywnych   |
| **Pozycja czasownika (V2)**| Pamięć robocza (DLPFC)                | Ćwiczenia typu n‑back                             |
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

- **2026-07-06**: Dodano funkcje neuronaukowe (Faza 2A‑2D) na podstawie badań z 2024‑2025 r.  
- Zdefiniowano macierz priorytetów oraz harmonogram MVP.  
- Utworzono listę kontrolną audytu kodu.  
- Udokumentowano przystosowania neuronaukowe specyficzne dla języka niemieckiego.  

---

*Uwaga: Niniejszy plik jest źródłem prawdy dotyczącym planowanych i już zrealizowanych zadań związanych z neuronaukowo uzasadnionymi funkcjami nauki języków. Aktualizuj go po każdym zakończonym etapie pracy.*