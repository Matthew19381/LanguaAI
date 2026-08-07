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
| SCI-7 | ✅ **Zaimplementowane 2026-07-25** — Production effect: etap „powtórz na głos" w Quick Mode (`routers/quickmode.py` `get_read_aloud`), bez rozpoznawania mowy, samoocena | MacLeod et al. 2010: materiał czytany na głos pamiętany lepiej niż czytany cicho | RCT |
| SCI-8 | ✅ **Zamknięte 2026-08-07** — zweryfikowane w kodzie: `DailyTest.jsx`, `Practice.jsx` i `Conversation.jsx` już pokazują poprawną odpowiedź + wyjaśnienie po błędzie. Fiszki celowo bez tego — przepływ Anki pokazuje odpowiedź *przed* oceną, więc nie ma momentu, do którego odnosi się poniższy cytat | Metcalfe 2017 (przegląd: uczenie się z błędów wymaga korekcyjnego feedbacku) | META |
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

## 6. Fazy (plan pierwotny) → rzeczywista kolejność wykonania

Plan zakładał kolejność 1) SCI-1…SCI-3, 2) SCI-8+SCI-9, 3) SCI-4…SCI-7+SCI-10.
W praktyce zrealizowano **SCI-1…SCI-7 w całości** (2026-07-18…07-25) przed
dotknięciem SCI-8/9/10 — SCI-8 jest częściowe, SCI-9 i SCI-10 wciąż otwarte
(wymagają integracji z Systemem Głównym / eksperymentu n-of-1). Ten plan
fazowania ma wartość historyczną; aktualny stan i kolejność napraw — w
[`TASKS.md`](TASKS.md).
