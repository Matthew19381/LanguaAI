# Funkcje oparte na nauce o uczeniu się w LinguaAI

> **Zasada projektowa**: każda funkcja wpływająca na naukę musi mieć (a) wsparcie w recenzowanych badaniach, (b) implementację zgodną z tym, co badania faktycznie pokazują. Konkretne stałe liczbowe bez podstawy empirycznej traktujemy jako hipotezy do zweryfikowania na danych — nie jako fakty.

_Ostatnia aktualizacja: 2026-08-19 — dodana hierarchia tematów + mastery % (P2-4, sekcja 1). Wcześniej (2026-08-07): SCI-1…SCI-7 przeniesione z backlogu (sekcja 4) do „Stan faktyczny" (sekcja 1), zgodnie z rzeczywistym stanem kodu._

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
| **SCI-1 Successive relearning** | ✅ Produkcja (2026-07-18) — słowo „opanowane" dopiero po 3 poprawnych przypomnieniach w odrębne dni; do tego czasu interwał FSRS capowany | `backend/services/flashcard_service.py` (`advance_relearning_criterion`) |
| **SCI-2 Pretesting** | ✅ Produkcja (2026-07-18) — zgadywanki o nowe słowa przed lekcją, bez kar | `backend/services/lesson_generator/daily_lesson.py` (`_sanitize_pretest`) |
| **SCI-3 Walidator pokrycia leksykalnego** | ✅ Produkcja (2026-07-18) — mierzy % znanych słów w tekście i+1, regeneruje przy <95% (max 2 próby) | `daily_lesson.py` (`lexical_coverage`) |
| **SCI-4 Rozpraszanie klastrów semantycznych** | ✅ Produkcja (2026-07-18) — nowe fiszki tej samej kategorii dostają rozsunięte daty pierwszej powtórki | `flashcard_service.py` (`assign_cluster_offsets`) |
| **SCI-5 Pora nauki dopasowana do rytmu** | ✅ Produkcja (2026-07-25) — sugestia data-driven, dopiero po ≥8 próbkach (≥3/przedział) | `backend/services/analytics_service.py` (`analyze_best_study_time`) |
| **SCI-6 Dyktando** | ✅ Produkcja (2026-07-25) — odsłuch TTS + zapis ze słuchu, word-level diff | `backend/services/dictation_service.py` |
| **SCI-7 Production effect** | ✅ Produkcja (2026-07-25) — „powtórz na głos" w Quick Mode, samoocena | `backend/routers/quickmode.py` (`get_read_aloud`) |
| **Hierarchia tematów + mastery %** (P2-4, Bank wiedzy) | ✅ Produkcja (2026-08-19) — drzewo temat→podtemat (`Topic.parent_id`, AI sugeruje przynależność przy ekstrakcji tematów z lekcji); mastery % per węzeł = `round(memory_strength × 100)`, gdzie `memory_strength` to **ta sama** wartość FSRS (OBS — pochodna z parametrów FSRS: difficulty/stability/retrievability, nie osobno wymyślony wskaźnik) już używana w widoku listy/kategorii/szczegółów tematu od dawna. Dla węzła z podtematami dodatkowo `group_mastery_percent` — **zwykła nieważona średnia** mastery węzła (jeśli ma własne materiały) i jego podtematów, jawnie oznaczona jako agregat porządkujący, nie metryka badawcza (HIPOTEZA/brak dowodu na tę konkretną formułę uśredniania — nie fabrykować pewności, której nie ma). Powtórka „podstaw" tematu wykorzystuje istniejący `review_topic`/FSRS-dla-tematów (nie nowy mechanizm) — węzeł oznaczony jako „Do powtórki" gdy `is_due()`. | `backend/services/topic_service.py` (`get_hierarchy_tree`, `get_or_create_topic_with_parent`), `backend/routers/topics.py` (`GET /{user_id}/hierarchy`), `frontend/src/pages/TopicsPage.jsx` (zakładka „Hierarchia") |

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

SCI-1…SCI-7 zostały zaimplementowane — patrz sekcja 1 dla statusu i odnośników do kodu.
Aktualny backlog nowych funkcji (SCI-8 i dalej, w tym rozszerzenia ekosystemowe) jest
prowadzony w [`NEURO_PLAN.md`](../NEURO_PLAN.md) i w [`TASKS.md`](../TASKS.md), żeby
status funkcji nie żył w dwóch rozjeżdżających się miejscach naraz.

---

*Ten dokument jest źródłem prawdy o funkcjach „learning science" w LinguaAI. Aktualizuj tabelę statusu po każdej zmianie. Nowe funkcje wpływające na naukę muszą przejść przez `NEURO_PLAN.md`/`TASKS.md` (z cytowaniem źródła) zanim trafią do kodu — a po wdrożeniu wracają tutaj jako wiersz w sekcji 1.*
