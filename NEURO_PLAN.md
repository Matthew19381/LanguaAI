# NEURO_PLAN — LinguaAI (v1.0)

> Część ekosystemu: `System-Glowny/MASTER_PLAN.md`. Standard naukowy: sekcja 0 MASTER_PLAN.
> Ten plan NIE zastępuje `docs/NEURO_FEATURES.md` — tamten dokument pozostaje
> źródłem prawdy o funkcjach learning science i jest **wzorcem dla całego ekosystemu**.
> Tu: rola w ekosystemie + rozszerzenia.

## 1. Rola w ekosystemie
- Najdojrzalszy naukowo moduł — jego standard (cytowania, poziomy dowodów,
  wycofywanie pseudonauki) został przyjęty jako standard ekosystemu.
- **Dawca Learning Engine**: FSRS v6 + retrieval practice + interleaving + i+1
  zostaną wydzielone jako usługa wspólna (MASTER_PLAN faza 3) — LinguaAI jest
  implementacją referencyjną i pierwszym konsumentem.

## 2. Stan naukowy (potwierdzony, bez zmian)
Zaimplementowane i poprawnie ugruntowane (szczegóły i kod w NEURO_FEATURES.md):
FSRS v6 (Cepeda 2006, META), retrieval practice/output forcing (Roediger &
Karpicke 2006, RCT; Swain 1985), interleaving (Rohrer & Taylor 2007, RCT),
i+1 z pokryciem ≥95% (Hu & Nation 2000; Nation 2006), telemetria snu i kontekstu
(Diekelmann & Born 2010 — tylko zbieranie danych, bez mnożników).

## 3. Plan funkcji (kolejność = SCI-1…SCI-6 z NEURO_FEATURES + rozszerzenia)

### Przejęte z backlogu NEURO_FEATURES (bez zmian, priorytet 1)
SCI-1 successive relearning · SCI-2 pretesting · SCI-3 walidator pokrycia
leksykalnego · SCI-4 rozpraszanie klastrów semantycznych · SCI-5 pora nauki
data-driven · SCI-6 dyktando. Podstawy naukowe — w NEURO_FEATURES sekcja 4.

### Rozszerzenia (priorytet 2, do przejścia przez proces NEURO_FEATURES §4)
| ID | Funkcja | Podstawa naukowa | Poziom |
|---|---|---|---|
| SCI-7 | **Production effect**: głośne wypowiadanie nowych słów podczas nauki (TTS jest — dodać etap "powtórz na głos" w Quick Mode; bez rozpoznawania mowy w v1, samoocena) | MacLeod et al. 2010: materiał czytany na głos pamiętany lepiej niż czytany cicho | RCT |
| SCI-8 | **Feedback korekcyjny natychmiastowy** przy błędnej odpowiedzi: poprawna odpowiedź + 1 zdanie wyjaśnienia (nie sama informacja błąd/dobrze) | Metcalfe 2017 (przegląd: uczenie się z błędów wymaga korekcyjnego feedbacku) | META |
| SCI-9 | **Kolejka powtórek dnia w Systemie Głównym**: FSRS publikuje liczbę zaległych fiszek → planner wstawia blok powtórek jako implementation intention | Gollwitzer & Sheeran 2006 (META) + spacing | META |
| SCI-10 | **Konsolidacja przez sen — przypomnienie wieczorne** (opcjonalne): sesja powtórek przed snem jako *hipoteza* testowana eksperymentem n-of-1 (SG-18), nie jako reguła | sen konsoliduje pamięć (Diekelmann & Born 2010, META), ale przewaga pory wieczornej u konkretnej osoby = do zmierzenia | HIPOTEZA |

## 4. Anty-wzorce (utrzymać zakazy z NEURO_FEATURES §3)
Zakaz powrotu: mnożników interwałów za sen/porę dnia, sztywnych okien
godzinowych, loot-boxów, fabrykowanych liczb w tipach.

## 5. Integracje
- **Publikuje**: eventy sesji (accuracy, czas, pora), zaległe powtórki,
  sleep log; `wellbeing_contribution` (frustracja/flow z samooceny sesji).
- **Subskrybuje**: plan dnia (kiedy blok nauki), tryb przetrwania (redukcja
  dziennego celu do 5 min), sen z Affect Engine.

## 6. Fazy
1. SCI-1…SCI-3 (największy wpływ na retencję przy małym koszcie).
2. SCI-8 + SCI-9 (integracja z ekosystemem).
3. SCI-4…SCI-7, SCI-10 po zebraniu danych.
