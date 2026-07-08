# Neuro‑naukowe funkcje językowe w LinguaAI (Faza 2)

## Spis treści
1. [Faza 2A – Optymalizacja snu i pamięci](#faza2a)
2. [Faza 2B – Motoryczna wymowa](#faza2b)
3. [Faza 2C – Przeplatanie i pożądane trudności](#faza2c)
4. [Faza 2C – Embodiment i słownictwo przestrzenne](#faza2c2)
5. [Powiązania z kodem](#kod)

---

## Faza 2A – Optymalizacja snu i pamięci <a name="faza2a"></a>

| ID | Funkcja | Opis | Gdzie zaimplementować |
|----|---------|------|------------------------|
| NEURO‑1 | **Harmonogram świadomości snu** | Planowanie powtórek w optymalnych oknach kodowania (wieczór) i odtwarzania (rano) na podstawie jakości snu i pory dnia. | - Backend: dodaj pole `session_type` (wieczór/rano/dzień) do modelu `Lesson`. <br> - Frontend: planuj powiadomienia w odpowiednich oknach. <br> - Opcjonalnie: integracja z wearable API (Google Fit, Apple Health) dla pomiaru jakości snu. |
| NEURO‑2 | **Generator treści i+1 (zrozumiały input)** | Tworzy tekst, w którym ~90 % słów jest już znanych użytkownikowi, a ~10 % nowych, zgodnie z hipotezą Krashena i kodowaniem predykcyjnym. | - Backend: nowy endpoint `/api/lessons/iplus1/{user_id}` generujący tekst z podświetleniem nowych słów. <br> - Wykorzystuje historię fiszek (`known_words`) oraz ukończone lekcje do kalibracji trudności. <br> - Zwraca: `i_plus_1_text`, `new_words_highlighted`, `cefr_level`. |
| NEURO‑3 | **Zmienna nagroda (optymalizacja dopaminy)** | Wprowadza nieprzewidywalne bonusy (loot box) oraz dodatkowe XP za trafne przewidywania kontekstu, aby zwiększyć sygnał błędu przewidywania dopaminowego. | - Backend: rozszerz `achievement_service.py` o `surprise_loot` (15 % szans) oraz `prediction_bonus` (+50 % XP za poprawne zgadywanie). <br> - Frontend: animacja skrzyni z łupem, licznik „serii przewidywań”. <br> - Konfiguracja: `target_success_rate: 0.85` (strefa i+1). |

---

## Faza 2B – Motoryczna wymowa <a name="faza2b"></a>

| ID | Funkcja | Opis | Gdzie zaimplementować |
|----|---------|------|------------------------|
| NEURO‑4 | **Mechanizm shadowing z opóźnionym odtwarzaniem** | Użytkownik słucha native speech, po określonym opóźnieniu (np. 0,5 s) odtwarza własną wypowiedź, co wzmacnia połączenie percepcyjno‑motoryczne. | - Frontend: odtwarzacz audio z regulowanym opóźnieniem (domyślnie 0,5 s). Tryb „choralny” (jednoczesne odtwarzanie użytkownika i AI). |
| NEURO‑5 | **Kotwice gestowe dla fonetów niemieckich** | Przypisanie konkretnych gestów do trudnych dźwięków (np. 🤲 dla „ch”, 👉 dla „ü/ö”, 🤏 dla „r” uvularnego, ✋ dla „sch”, 👌 dla „pf/ts”). Gest działa jako wskazówka artikulacyjna, angażując korę ruchową. | - Frontend: karta z podpowiedzią gestu podczas treningu wymowy. <br> - Backend: przechowuj pole `gesture_anchor` przy fiszce/frazie. |
| NEURO‑6 | **Wizualizacja artykulacji (3D)** | Pokazuje animację języka, podniebienia i warg podczas artykulacji dźwięków niemieckich, wspierając naukę poprzez zwrotny wzrok. | - Frontend: model 3D w Three.js/WebGL w sekcji wymowy, włączany przełącznikiem „Pokaż artykulację”. |

---

## Faza 2C – Przeplatanie i pożądane trudności <a name="faza2c"></a>

| ID | Funkcja | Opis | Gdzie zaimplementować |
|----|---------|------|------------------------|
| NEURO‑7 | **Mieszacz sesji (interleaving)** | Losowo miesza bloki materiału (słownictwo, gramatyka, wymowa, słuchanie, produkcja) aby zwiększyć interferencję kontekstową i poprawić długoterminowe retenowanie. | - Backend: usługa `session_mixer` tworząca zróżnicowane sekwencje nauki. <br> - Szczególny nacisk na niemieckie struktury proceduralne (der/die/das, pozycja czasownika V2, trenne czasowniki). |
| NEURO‑8 | **Neuro‑uświadomiony FSRS V2** | Rozszerzenie klasycznego FSRS o czynniki neurobiologiczne: modulację snu, wpływ pory dnia, bonus za interleaving, karę za interferencję. | - Biblioteka: `backend/services/fsrs_neuro.py` (funkcja `neuro_fsrs_next_interval`). <br> - Parametry: `sleep_modulator_weight`, `time_of_day_weight`, `interleaving_bonus_weight`, `interference_penalty_weight`. <br> - Przechowywane pola w modelu `Flashcard`: `session_type`, `sleep_quality`, `interleaving_bonus`, `interference_penalty`. |

---

## Faza 2C – Embodiment i słownictwo przestrzenne <a name="faza2c2"></a>

| ID | Funkcja | Opis | Gdzie zaimplementować |
|----|---------|------|------------------------|
| NEURO‑9 | **Pałac pamięci / mapa słownictwa przestrzennego** | Przestrzenna reprezentacja leksyki: pokoje = tematy, obiekty = słowa. Nawiązuje do pamięci episodycznej i nawigacji przestrzennej. | - Frontend: siatka 2D (Canvas/SVG) reprezentująca „Pałac pamięci”. Kliknięcie w pokój pokazuje przypisane słowa z kontekstem. <br> - Backend: przechowuj `spatial_anchor` (x, y, room) przy fiszce. |
| NEURO‑10 | **Społeczne kodowanie predykcyjne (AI rozmowa)** | Model przewiduje, kiedy użytkownik zakończy wypowiedź; błąd predykcji sygnalizuje możliwość nauki. Agentowie o różnej „osobowości” modelują Teorię Umysłu, zwiększając zaangażowanie społeczne. | - Backend: rozszerz moduł rozmowy głosowej o przewidywanie turn‑taking i adaptacyjne sprzężenie zwrotne. <br> - Frontend: interfejs rozmowy z wizualizacją pewności predykcji AI. |

---

## Powiązania z kodem (obecny stan) <a name="kod"></a>

| Plik | Co już zostało zrobione | Co pozostało do zrobienia |
|------|------------------------|---------------------------|
| `backend/services/fsrs_neuro.py**` | Pełna implementacja neuro‑FSRS (funkcja `neuro_fsrs_next_interval`, klasy `NeuroFSRSParams`, `NeuroCardState`). | Integracja z endpointem fiszki (już zrobiona w `backend/routers/flashcards.py`). |
| `backend/models/flashcard.py` | Dodane pola: `session_type`, `sleep_quality`, `interleaving_bonus`, `interference_penalty`. | Brak. |
| `backend/routers/flashcards.py` | Import i użycie `neuro_fsrs_next_interval` w endpointzie `review_flashcard`. Pobiera `session_type` na podstawie godziny UTC; pozostałe pola neuro pobierane z rekordu fiszki. | Konieczne: rzeczywiste zbieranie `sleep_quality` i `interleaving_bonus`/`interference_penalty` od użytkownika (np. przez UI lub zdrowotne wearables). |
| `backend/services/lesson_generator/daily_lesson.py` | Zaktualizowany o sekcje `interleaved_review` i `output_forcing` (zgodne z neuro‑FSRS i efektem testu). | Brak. |
| `backend/services/achievement_service.py` | Dodane osiągnięcia neuro‑naukowe (np. *First Review*, *Night‑Owl Learner*, *Morning Bird*, *Interleaver*, *Sleep‑Consolidator*, serie poprawnych odpowiedzi). | Można dodać dodatkowe odznaki za korzystanie z funkcji shadowing, gestów, czy pałacu pamięci. |
| `frontend/src/components/…` | Brak jeszcze dedykowanych UI dla neurofunkcji (np. podpowiedzi gestów, wizualizacji 3D, harmonogramu snu). | Do implementacji w kolejnych sprintach zgodnie z harmonogramem MVP. |

---

## Proponowany kolejny krok (MVP)

1. **Tydzień 1** – NEURO‑1 (harmonogram snu) + NEURO‑3 (zmienna nagroda).  
2. **Tydzień 2** – NEURO‑2 (generator i+1) + NEURO‑4 (shadowing).  
3. **Tydzień 3** – NEURO‑5 (kotwice gestowe) + NEURO‑7 (przeplatanie).  
4. **Tydzień 4** – NEURO‑8 (neuro‑FSRS) – integracja już częściowo istniejąca; pozostało tylko zbieranie danych neuro od użytkownika i wyświetlanie efektów w UI.  

Po zakończeniu tego cyklu podstawowe funkcje neuronaukowe będą dostępne i przetestowane.

--- 

*Uwaga: Niniejszy dokument stanowi źródło prawdy dotyczące zaproponowanych i częściowo zaimplementowanych funkcji neuronawkowych w projekcie LinguaAI. Aktualizuj go po każdym zakończonym etapie pracy.*