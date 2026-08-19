# LinguaAI — Backlog jakości i UX (rewizja użytkownika, 2026-08-02)

Źródło: przegląd użytkownika po realnym używaniu aplikacji. Każde zadanie ma:
**Problem → Przyczyna (plik) → Co zrobić → Kryteria akceptacji (DoD)**.
Priorytety: **P0** regresje/krytyczne, **P1** zepsute rdzenne UX, **P2** przebudowy funkcji, **P3** polish.

---

## P0 — Regresje konfiguracji (skutek przenosin projektu)

### P0-1. Przywrócić utracone klucze i tier w `backend/.env` — ✅ Zamknięte (zweryfikowano 2026-08-19)
Zweryfikowano bezpośrednio w `backend/.env`: `AI_MODEL_TIER=best` ustawiony, `YOUTUBE_API_KEY`,
`GEMINI_API_KEY`, `ADMIN_API_KEY` wszystkie obecne i niepuste (wartości nie były wypisywane —
tylko sprawdzenie obecności).
- **Problem:** treści generują się na tanim modelu; YouTube zwraca błąd API; admin-endpointy nie działają.
- **Przyczyna:** migracja do `C:\Projects\LinguaAI` zgubiła w nowym `backend/.env`:
  `AI_MODEL_TIER=best`, `YOUTUBE_API_KEY`, `GEMINI_API_KEY` (realny), `ADMIN_API_KEY`.
  Stary `.env` (`C:\GoogleDriveSync\Projekty\LinguaAI\backend\.env`) je ma.
- **Co zrobić:** przenieść brakujące wartości ze starego `.env`; rozważyć rotację kluczy (były wypisane w logach sesji).
- **DoD:** `AI_MODEL_TIER=best` aktywny; YouTube działa; `/api/admin/*` autoryzuje.

---

## P1 — Zepsute rdzenne UX (dotyka codziennego użycia)

### P1-1. Znaki specjalne kradną fokus / kursor znika — ✅ Zamknięte (zweryfikowano 2026-08-19)
`frontend/src/components/SpecialChars.jsx` — dokładnie ten wzorzec: `onMouseDown preventDefault`,
wstawianie na `selectionStart`/`selectionEnd`, przywrócenie karetki po re-renderze.
- **Problem:** kliknięcie ä/ö/ü przenosi fokus z pola tekstowego; kursor „znika".
- **Przyczyna:** `frontend/src/pages/DailyLesson.jsx` `SpecialCharHelper` (~1251) — `<button onClick>` bez `onMouseDown preventDefault`, a `onInsert` dokleja znak na koniec zamiast w pozycji kursora.
- **Co zrobić:** wydzielić wspólny komponent `SpecialChars` (np. `components/SpecialChars.jsx`):
  - `onMouseDown={e => e.preventDefault()}` (nie zabiera fokusu),
  - wstawianie w miejsce kursora (selectionStart/End), utrzymanie fokusu i pozycji karetki po wstawieniu.
- **DoD:** po kliknięciu znaku fokus zostaje w polu, znak ląduje w miejscu kursora, można pisać dalej.

### P1-2. Brak znaków specjalnych w: teście dnia, ćwiczeniach, dyktandzie — ✅ Zamknięte (zweryfikowano 2026-08-19)
`SpecialChars` już podpięty w `DailyTest.jsx`, `Practice.jsx`, `Dictation.jsx`.
- **Problem:** te ekrany nie mają paska znaków (są tylko w lekcji/konwersacji/news/flashcards).
- **Przyczyna:** `SpecialCharHelper` używany lokalnie w DailyLesson; brak w `DailyTest.jsx`, `Practice.jsx`, `Dictation.jsx`.
- **Co zrobić:** po P1-1 podpiąć wspólny `SpecialChars` pod każde pole odpowiedzi w tych stronach (język z profilu użytkownika).
- **DoD:** we wszystkich polach tekstowych do odpowiedzi jest pasek znaków dla języka docelowego.

### P1-3. Ćwiczenia bez treści („co mam uzupełniać, skoro nic nie ma") — ✅ Zamknięte 2026-08-19
Backend: `_clean_exercises()` w `daily_lesson.py` odrzuca bloki/pozycje bez `instruction`/
`prompt`/`answer`; generacja retry'uje raz całą lekcję, jeśli po odfiltrowaniu ćwiczenia
wyszły puste. Frontend: `normalizeExercises` w `DailyLesson.jsx` odrzuca pozycję bez
`content`, oraz bez `answer` dla zamkniętych typów (nie dla `sentence_creation`, gdzie
"answer" to tylko przykład, ocenia AI). Testy: `test_lesson_content_completeness.py` (7),
`DailyLesson.test.jsx` (+1).
- **Problem:** część ćwiczeń renderuje puste zdanie/brak luki.
- **Przyczyna:** `ExerciseCard` (DailyLesson ~1270) zakłada `exercise.content` z `___`; przy pustym/niepełnym `content` nie ma czego pokazać. Generacja (tani model) bywa niekompletna.
- **Co zrobić:**
  - Backend `services/lesson_generator.py`: wymusić w prompt+walidacji, że każde ćwiczenie ma pełne `content` z wyraźną luką `___`, `answer` oraz `instruction`; odrzucać/ponawiać niekompletne.
  - Frontend: guard — nie renderować ćwiczenia bez `content`/`answer`; pokazać placeholder zamiast pustki.
- **DoD:** każde wyświetlone ćwiczenie ma czytelne zdanie z luką i sprawdzalną odpowiedź.

### P1-4. Brak wyjaśnienia gramatyki w lekcji — ✅ Zamknięte 2026-08-19
Ta sama retry pętla co P1-3 (jedna generacja, jeden JSON) sprawdza też
`grammar.explanation` niepuste; jeśli po retry wciąż puste, wstawiany jest jawnie
oznaczony fallback tekstowy odnoszący się do tematu gramatycznego (nie cichy/generyczny).
- **Problem:** sekcja gramatyki pusta.
- **Przyczyna:** UI ma sekcję (`content.explanation`, DailyLesson ~557), ale generacja jej nie zwraca (albo pusta na tanim modelu).
- **Co zrobić:** w `lesson_generator.generate_daily_lesson` zagwarantować niepustą sekcję `explanation` (reguła + 2–3 przykłady + typowe błędy PL→DE); walidacja obecności; fallback treściowy.
- **DoD:** każda lekcja ma widoczne, konkretne wyjaśnienie gramatyczne powiązane z tematem.

### P1-5. Recall (OutputForcingCard) — tekst znika, brak sprawdzenia — ✅ Zamknięte (zweryfikowano 2026-08-19)
`OutputForcingCard` w `DailyLesson.jsx` ma przycisk „Sprawdź", word-level diff
(zielone/czerwone), tekst użytkownika nigdy nie jest kasowany.
- **Problem:** po wypisaniu z pamięci brak przycisku pokazującego poprawny tekst / zaznaczającego błędne wyrazy; wpisane znika.
- **Przyczyna:** `OutputForcingCard` (DailyLesson ~1144) liczy tylko `similarity()`; brak trybu porównania i utrzymania wpisu.
- **Co zrobić:** dodać przycisk „Sprawdź": zachować `userRecall`, pod spodem pokazać poprawny tekst i **diff słowo-po-słowie** (zielone=trafione, czerwone=błędne/brakujące). Nic nie kasować automatycznie.
- **DoD:** po „Sprawdź" widać swój tekst + poprawny + kolorowe zaznaczenie różnic; wpis nie znika.

### P1-6. Test dnia → przycisk „przejdź do lekcji" generuje NOWĄ lekcję — ✅ Zamknięte (zweryfikowano 2026-08-19)
`getTodayLesson`/`get_today_lesson` sprawdza istniejącą dzisiejszą lekcję przed
generacją (naprawione już przy okazji fixu `4af0665`), więc `navigate('/lesson')` z
`DailyTest.jsx` zawsze otwiera tę samą lekcję. Osobny, jawny przycisk „Wygeneruj nową
lekcję" istnieje niezależnie (`DailyLesson.jsx` + `Settings.jsx`).
- **Problem:** po teście przycisk tworzy świeżą lekcję (z tymi samymi wadami), zamiast otworzyć dzisiejszą istniejącą.
- **Przyczyna:** `DailyTest.jsx` (~160, `onRetry`) `navigate('/lesson')`; `/lesson` auto-generuje przy braku „dzisiejszej".
- **Co zrobić:** kierować do istniejącej dzisiejszej lekcji (bez regeneracji); rozdzielić „otwórz dzisiejszą" od „generuj nową". Zweryfikować `onRegenerateFromErrors`, by nie produkował niekompletnych ćwiczeń (zależ. od P1-3).
- **DoD:** po teście „przejdź do lekcji" otwiera tę samą dzisiejszą lekcję; nowa powstaje tylko na jawne żądanie.

### P1-7. Ćwiczenia — Enter zatwierdza, drugi Enter = następne — ✅ Zamknięte (zweryfikowano 2026-08-19)
`Practice.jsx` ma dokładnie ten dwustanowy handler (`onKeyDown`, linie ok. 162-168, 317).
- **Problem:** brak szybkiej obsługi klawiatury w `Practice.jsx`.
- **Przyczyna:** obecny handler nie ma dwustanowego Enter (sprawdź → dalej).
- **Co zrobić:** w polu odpowiedzi: 1. Enter = sprawdź (gdy niesprawdzone), 2. Enter = następne ćwiczenie (gdy sprawdzone).
- **DoD:** cały cykl ćwiczeń przechodzi się samą klawiaturą.

---

## P2 — Przebudowy funkcji

### P2-1. Fiszki — całkowita przebudowa
- **Problem:** „mogę tylko odwrócić kartę"; ocena zapamiętania niewidoczna/nieczytelna.
- **Przyczyna:** `Flashcards.jsx` (816 l.) ma oceny 1–4 (Again/Hard/Good/Easy, ~569), ale pojawiają się dopiero po odwróceniu i UX jest mylący.
- **Co zrobić:** przeprojektować przepływ:
  - front karty → „Pokaż odpowiedź" → tył + **wyraźne 4 przyciski oceny** (z interwałami FSRS) zawsze widoczne,
  - skróty 1–4, licznik due/postęp sesji, wynik na koniec sesji,
  - audio słowa, przykładowe zdanie, powiązanie z tematem.
- **DoD:** użytkownik dla każdej karty świadomie ocenia pamięć; FSRS aktualizuje `next_review`; sesja ma jasny koniec.

### P2-2. Konwersacja — realna rozmowa + właściwy model
- **Problem:** nie da się „normalnie porozmawiać".
- **Przyczyna:** `Conversation.jsx` (699 l.) oparte o start/send/analyze; model rozwiązywany serwerowo, obecnie tier `cheap`.
- **Co zrobić:**
  - płynny czat turowy (kontekst historii, krótkie naturalne odpowiedzi, delikatna korekta błędów w tle),
  - dobrać model konwersacyjny w `services/model_router.py` (dedykowany tier/задanie „conversation" na dobrym modelu), streaming odpowiedzi,
  - tryb głosowy opcjonalny, ale tekstowy ma działać bez tarcia.
- **DoD:** można prowadzić wielozdaniową, sensowną rozmowę w języku docelowym z korektą.

### P2-3. News — zaznaczanie słów w treści → lista boczna → do fiszek
- **Problem:** obecnie tylko gotowa lista słówek z przyciskiem; brak zaznaczania dowolnych słów w tekście.
- **Przyczyna:** `News.jsx` (~171) dodaje z predefiniowanego `vocabulary`, nie z klikniętego słowa w artykule.
- **Co zrobić:** klik w wyraz w treści → podświetlenie na zielono + dodanie do panelu (bok/dół) z tłumaczeniem (`translateWord`); dopiero przycisk „Dodaj zaznaczone do fiszek" zapisuje wybrane.
- **DoD:** dowolne słowo z artykułu można zaznaczyć, zebrać na liście i zbiorczo dodać do fiszek.

### P2-4. Bank wiedzy — budowa/przebudowa (największe)
- **Problem:** brak realnego dostępu do „banku wiedzy" z hierarchią i opanowaniem.
- **Przyczyna:** `TopicsPage.jsx` (783 l.) istnieje, ale nie realizuje struktury tematy→podtematy→materiały; słabo dostępny z nawigacji.
- **Co zrobić (model + UI):**
  - Hierarchia: **Główny temat → Podtematy → (Ćwiczenia + Materiały edukacyjne)** z przyciskiem „Rozpocznij naukę".
  - Każdy temat/podtemat/ćwiczenie ma **stopień opanowania** (mastery %), napędzany FSRS.
  - **Ponowne przepytywanie podstaw** po czasie (spaced review na poziomie tematów) — sprawdzić, czy `reviewTopic`/FSRS tematów już to robi; jeśli tak, wyeksponować; jeśli nie, dodać harmonogram i alerty „powtórz podstawy".
  - Backend: model tematów/podtematów/materiałów + powiązania z lekcjami/ćwiczeniami/fiszkami; endpoint drzewa z mastery.
  - Wejście w nawigacji głównej („Bank wiedzy").
- **DoD:** użytkownik widzi drzewo tematów z % opanowania, wchodzi w materiały/ćwiczenia, jest cyklicznie przepytywany z podstaw.

---

## P3 — Polish / dostępność funkcji

### P3-1. Nawigacja — wyeksponować WSZYSTKIE funkcje — ✅ Zamknięte 2026-08-08 (`3549dad`)
`NavBar.jsx` przebudowany: `flex flex-wrap` zamiast `overflow-x-auto` + `hidden md:block`,
5 nazwanych kategorii (Nauka/Ćwiczenia/Media/Postępy/Konto), wszystkie 18 funkcji z trwałą
etykietą tekstową na każdej szerokości ekranu. Regression-lock testy w `NavBar.test.jsx`.
- **Problem:** górny panel nie pokazuje wszystkiego; część stron bez wejścia; etykiety znikają poniżej `md` (same ikony).
- **Przyczyna:** `NavBar.jsx` — `hidden md:block` na etykietach; brak w menu m.in. `ReadAloud`, `LessonHistory`, `PronunciationTrainer`.
- **Co zrobić:** przeprojektować nawigację (rozwijane menu/drawer „Więcej" grupujące funkcje: Nauka / Ćwiczenia / Media / Postępy / Konto), z etykietami także na węższych ekranach; dodać brakujące strony.
- **DoD:** każda istniejąca funkcja jest osiągalna z nawigacji z czytelną etykietą.

### P3-2. Tryb jasny — kremowy zamiast oślepiającej bieli — ✅ Zamknięte (commit `445e0b9`, przed tym audytem)
Zweryfikowano w `frontend/src/index.css`: `body` używa `#f2ece0` (ciepły kremowy), nie
`bg-gray-50`; `.light .bg-white`/`.card`/`.bg-gray-100` mają dedykowane kremowe odcienie
(`#fcf9f3`, `#efe8db`). Ten wpis pozostał oznaczony jako otwarty w `ACTION_PLAN.md` F4-12
mimo że kod już to realizował — poprawione tu.
- **Problem:** jasny motyw oślepia.
- **Przyczyna:** `frontend/src/index.css` `body { @apply bg-gray-50 ... }` (prawie biel); powierzchnie `bg-white`.
- **Co zrobić:** wprowadzić ciepłą, niską-kontrastowo paletę (tło ~`#faf6ec`/kremowe, karty lekko jaśniejsze, tekst ciemnografitowy zamiast czystej czerni); spójnie przez zmienne/utility.
- **DoD:** tryb jasny czytelny i nieoślepiający; kontrast zgodny z WCAG AA.

### P3-3. Dzienne wskazówki powiązane z bieżącą nauką
- **Problem:** wskazówki generyczne.
- **Przyczyna:** `routers/stats.py` `get_daily_tips` → `generate_daily_tips` bez pełnego kontekstu bieżących tematów/słabych miejsc.
- **Co zrobić:** przekazać do generacji ostatnie tematy, słabe ćwiczenia/fiszki (niski mastery), ostatnie błędy — wskazówki mają odnosić się do tego, czego user się teraz uczy.
- **DoD:** wskazówki wyraźnie nawiązują do aktualnych tematów i słabych punktów użytkownika.

---

## Kolejność sugerowana
1. **P0-1** (natychmiast — przywraca `best` i YouTube, podnosi jakość generacji „za darmo").
2. **P1-1/P1-2** (znaki specjalne — dotyczy wielu ekranów, wspólny komponent).
3. **P1-3/P1-4** (kompletność ćwiczeń + gramatyka — sedno „lekcja to gówno").
4. **P1-5/P1-6/P1-7** (recall, przepływ test→lekcja, klawiatura).
5. **P2-1** (fiszki) → **P2-2** (konwersacja) → **P2-3** (news) → **P2-4** (bank wiedzy — największe).
6. **P3-1/P3-2/P3-3** (nawigacja, motyw, wskazówki).
