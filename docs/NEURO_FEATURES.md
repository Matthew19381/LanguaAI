# Funkcje oparte na nauce o uczeniu się w LinguaAI

> **Zasada projektowa**: każda funkcja wpływająca na naukę musi mieć (a) wsparcie w recenzowanych badaniach, (b) implementację zgodną z tym, co badania faktycznie pokazują. Konkretne stałe liczbowe bez podstawy empirycznej traktujemy jako hipotezy do zweryfikowania na danych — nie jako fakty.

## Spis treści
1. [Stan faktyczny — co jest zaimplementowane](#stan)
2. [Podstawy naukowe zaimplementowanych mechanizmów](#nauka)
3. [Funkcje wycofane i dlaczego](#wycofane)
4. [Zaplanowane funkcje (backlog, poparte badaniami)](#backlog)

---

## 1. Stan faktyczny — co jest zaimplementowane <a name="stan"></a>

| Mechanizm | Status | Kod |
|---|---|---|
| **Spaced repetition (FSRS v6)** | ✅ Produkcja — scheduler fiszek i tematów to biblioteka `fsrs` v6 (model DSR), bez żadnych dodatkowych mnożników | `backend/services/fsrs_service.py`, `backend/routers/flashcards.py` |
| **Interleaved review** (Mixed Review w lekcji) | ✅ Produkcja — 2-3 prompty przypominające z ostatnich tematów | `backend/services/lesson_generator/daily_lesson.py` (`_build_interleaved_review`) |
| **Output forcing** (retrieval practice) | ✅ Produkcja — 5 zdań w języku docelowym generowanych per lekcja z jej słownictwa; czytaj → zakryj → odtwórz | `daily_lesson.py` (sekcja 9 promptu) |
| **Comprehensible input (i+1)** | ✅ Produkcja — tekst z ≥95% znanego słownictwa + 3-5 nowych słów | `daily_lesson.py` (`generate_iplus1_content`) |
| **Telemetria kontekstu powtórki** (NEURO-11/12/13) | 📊 Zbieranie danych — `session_type`, `sleep_quality`, `interleaving_bonus`, `interference_penalty` zapisywane przy każdej powtórce. **Nie wpływają na scheduler** — służą przyszłej analizie | `backend/routers/flashcards.py`, `backend/models/flashcard.py` |
| **Dziennik snu** (NEURO-11/14/16) | 📊 Zbieranie danych — ręczny wpis 1-5 + endpoint synchronizacji z sensorów; osiągnięcie `sleep_tracker` | `backend/routers/users.py` |

## 2. Podstawy naukowe zaimplementowanych mechanizmów <a name="nauka"></a>

- **FSRS / spaced repetition** — efekt rozłożenia powtórek w czasie to jeden z najlepiej udokumentowanych efektów w badaniach nad pamięcią (Cepeda et al. 2006, meta-analiza). FSRS jest optymalizowany empirycznie na dziesiątkach milionów rzeczywistych powtórek; jego przewaga nad SM-2 jest mierzalna. Dlatego **nie modyfikujemy jego interwałów ręcznymi mnożnikami**.
- **Retrieval practice (output forcing, mixed review)** — aktywne przypominanie bije ponowne czytanie (testing effect; Roediger & Karpicke 2006). Output w języku obcym dodatkowo ujawnia luki w wiedzy (hipoteza outputu; Swain 1985).
- **Interleaving** — przeplatanie tematów daje lepszą retencję długoterminową niż praktyka blokowa (Rohrer & Taylor 2007; Kornell & Bjork 2008).
- **i+1 / pokrycie leksykalne** — do komfortowego rozumienia tekstu potrzeba **95-98% znanych słów** (Hu & Nation 2000; Nation 2006; Schmitt, Jiang & Grabe 2011). Stąd reguła: ≥95% znanego słownictwa, 3-5 nowych słów na 100-150 słów tekstu (~96-97% pokrycia).
- **Sen a konsolidacja** — sen konsoliduje świeżo nauczone słownictwo (Diekelmann & Born 2010; Stickgold 2005). To uzasadnia *zbieranie* danych o śnie i ewentualne przypomnienia wieczorne/poranne — ale **nie** uzasadnia konkretnych mnożników interwałów, więc żadnych nie stosujemy.

## 3. Funkcje wycofane i dlaczego <a name="wycofane"></a>

| Funkcja | Powód wycofania |
|---|---|
| **„Neuro-FSRS" (`fsrs_neuro.py`)** — mnożniki stabilności za sen/porę dnia/interleaving | Usunięty (2026-07). Uproszczona reimplementacja FSRS była matematycznie błędna (stabilność nie rosła w fazie Review; interwał `stability × (rating−1)` bez podstaw), a same mnożniki (±10-12% za samoocenę snu, okno „kortyzolowe" 6-10 ze współczynnikiem 1.1) nie mają wsparcia empirycznego. Efekty pory dnia zależą od chronotypu (synchrony effect) — sztywne okna godzinowe są nieuzasadnione. Produkcja zawsze używała FSRS v6; ten moduł był martwym kodem. |
| **Endpointy `neuro-weights` (NEURO-15)** + kolumna `users.neuro_weights` | Usunięte — konfigurowały wagi, których nic nie konsumowało. |
| **Kolumny `gesture_anchor`, `spatial_anchor`** | Usunięte z modelu — nic ich nie zapisywało ani nie czytało. Wrócą razem z implementacją funkcji, które ich potrzebują. |
| **NEURO-3 „optymalizacja dopaminy" (loot box)** | Wycofane z planu w tej formie. Zmienne wzmocnienie (variable-ratio reinforcement) jest realnym zjawiskiem behawioralnym, ale narracja „dopaminowa" to pop-neuronauka, a mechanika loot boxów budzi zastrzeżenia etyczne (wzorce znane z hazardu). Jeśli wróci — jako zwykła, jawna losowa premia XP, bez pseudonaukowych uzasadnień. |
| Sfabrykowane liczby w tipach („+200% retencji — Ebbinghaus", „3× lepsza retencja w kontekście — Nation") | Zastąpione twierdzeniami zgodnymi ze źródłami (`backend/notifier.py`). |

## 4. Zaplanowane funkcje (backlog, poparte badaniami) <a name="backlog"></a>

Ponumerowane od SCI-1, w kolejności proponowanej implementacji:

| ID | Funkcja | Podstawa naukowa | Szkic implementacji |
|----|---------|------------------|---------------------|
| SCI-1 | **Successive relearning** — słowo liczy się jako „opanowane" dopiero po 3 poprawnych przypomnieniach rozłożonych na ≥2 sesje; do tego czasu wraca w kolejce mimo oceny „Good" | Rawson & Dunlosky (2011): kryterialne ponowne uczenie się daje duże, trwałe zyski retencji | Pole `correct_recall_sessions` na fiszce; status „mastered" sterujący statystykami i doborem słów do i+1 |
| SCI-2 | **Pretesting** — 3-5 pytań-zgadywanek o nowe słowa *przed* lekcją; błędne odpowiedzi są oczekiwane i nieszkodliwe | Efekt pretestingu: nieudane próby odpowiedzi przed nauką poprawiają późniejsze zapamiętanie (Kornell, Hays & Bjork 2009; Richland et al. 2009) | Sekcja `pretest` w treści lekcji, renderowana przed `vocabulary`; bez kar XP |
| SCI-3 | **Walidator pokrycia leksykalnego** — po wygenerowaniu tekstu i+1 backend liczy, jaki % tokenów należy do znanego słownictwa; przy <95% regeneruje (max 2 próby) | Hu & Nation (2000), Nation (2006): pokrycie 95-98% to warunek zrozumiałości — warto je *mierzyć*, nie tylko deklarować w promptcie | Funkcja `lexical_coverage(text, known_words)` w `lesson_generator`; prosty tokenizer + porównanie lematów |
| SCI-4 | **Rozpraszanie podobnych słów** — przy tworzeniu fiszek z lekcji słowa z tej samej kategorii semantycznej (kolory, dni tygodnia, bliskoznaczne) dostają rozsunięte `next_review_date`, zamiast wchodzić do kolejki razem | Interferencja przy uczeniu klastrów semantycznych (Tinkham 1993; Nakata & Suzuki 2019) | Przy batchu nowych fiszek: prompt klasyfikujący kategorie + przesunięcie startowych dat o 1-2 dni wewnątrz klastra |
| SCI-5 | **Przypomnienia dopasowane do osobistego rytmu** — zamiast sztywnych okien godzinowych: po zebraniu ≥200 powtórek analiza skuteczności per pora dnia (z istniejącej telemetrii `session_type`) i sugestia najlepszej pory nauki dla *tego* użytkownika | Synchrony effect — szczyt sprawności poznawczej zależy od chronotypu (May & Hasher 1998; Goldstein et al. 2007); podejście data-driven zamiast uniwersalnych stałych | Endpoint `GET /stats/{user_id}/best-study-time` liczący accuracy per przedział godzinowy z historii powtórek; wykorzystywany przez notifier |
| SCI-6 | **Dyktando** — odsłuch zdania TTS (istniejący edge-tts) i zapis ze słuchu, z diffem błędów | Dekodowanie ze słuchu wspiera słuchanie i pisownię (Nation & Newton 2009) | Nowa aktywność w Quick Mode; porównanie tekstu po normalizacji + podświetlenie różnic |

---

*Ten dokument jest źródłem prawdy o funkcjach „learning science" w LinguaAI. Aktualizuj tabelę statusu po każdej zmianie. Nowe funkcje wpływające na naukę muszą przejść przez sekcję 4 (z cytowaniem źródła) zanim trafią do kodu.*
