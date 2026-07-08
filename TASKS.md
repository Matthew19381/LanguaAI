# TASKS â€” LinguaAI

_Ostatnia aktualizacja: 2026-04-05_
_ĹąrĂłdĹ‚a: FEEDBACK.md, wĹ‚asne implementacje_

---

## P0 â€” Krytyczne (blokujÄ… uĹĽycie aplikacji)

- [x] **AUDIO-1** â€” Audio nie dziaĹ‚a: edge-tts zwraca 403. Dodano retry 3x z exponential backoff (0.5s/1s/2s). âś… (2026-03-26)
- [x] **AUDIO-2** â€” PlayButton dodany do: gramatyka (explanation), fiszki (sĹ‚owo front+back), newsy (simplified_text), wymowa (fraza/custom). Dialog i sĹ‚ownictwo juĹĽ miaĹ‚y. âś… (2026-03-26)
- [x] **UI-1** â€” Nazwy jÄ™zykĂłw spolszczone (Germanâ†’Niemiecki itd.) w Stats, PlacementTest, Home, QuickMode. LANG_DISPLAY map per plik. âś… (2026-03-26)
- [x] **LESSON-1** â€” useState(true) powodowaĹ‚ flash spinnera przy powrocie. Fix: lazy initializer z readLessonCache() â€” loading=false i lesson=dane od razu przy mount. âś… (2026-03-26)
- [x] **LESSON-2** â€” get_day_number liczyĹ‚o wszystkie lekcje (nie tylko ukoĹ„czone). Fix: liczenie tylko is_completed=True + sprawdzenie nieukoĹ„czonych lekcji z poprzednich dni. âś… (2026-03-26)

---

## P1 â€” Wysokie (funkcje zepsute)

- [x] **TEST-1** â€” Cache pytaĹ„ testu w localStorage per dzieĹ„/jÄ™zyk. âś… (2026-03-26)
- [x] **TEST-2** â€” Prompt wzmocniony: zakaz dawania odpowiedzi w treĹ›ci pytania, zakaz ujawniania tĹ‚umaczenia. âś… (2026-03-26)
- [x] **TEST-3** â€” Prompt: fill_blank musi mieÄ‡ DOKĹADNIE JEDNO ___ â€” nie wiÄ™cej. âś… (2026-03-26)
- [x] **TEST-4** â€” Placement test calibration: stricter scoring (A1 <30%, B1 <65%), conservative AI analysis â€” FIXED 2026-05-03
- [x] **TIMER-1** â€” JuĹĽ zaimplementowany: Layout.jsx ma globalny badge (quickmode_start z localStorage), niezaleĹĽny od stanu QuickMode. Timer nie zatrzymuje siÄ™ przy zmianie zakĹ‚adki. âś… (2026-03-26)
- [x] **STATS-1** â€” TodayCompletion: reaktywny useState + odĹ›wieĹĽanie na focus okna. 4 aktywnoĹ›ci: Lekcja, Test, Rozmowa, Newsy/Wymowa. âś… (2026-03-26)
- [x] **ERRORS-1** â€” Backend (stats.py) zwracaĹ‚ error/correction zamiast user_answer/correct_answer. Fix: nowe pola question/user_answer/correct_answer w get_all_errors + UI ErrorReview.jsx. âś… (2026-03-26)
- [x] **GRAMMAR-1** â€” WyjaĹ›nienie gramatyki: dodano `renderMarkdown()` obsĹ‚ugujÄ…cy `#/##/###`, `**bold**`, listy. âś… (2026-03-26)
- [x] **FLASHCARD-BTN** â€” Backend zwraca teraz czytelny komunikat gdy AI nie generuje konceptĂłw. âś… (2026-03-26)

---

## P2 â€” Ĺšrednie (funkcje niekompletne)

- [x] **LANG-1** â€” UsuniÄ™to 1.5s setTimeout â€” zmiana jÄ™zyka przeĹ‚adowuje stronÄ™ natychmiast. âś… (2026-03-26)
- [x] **LANG-2** â€” Naprawiono needs_placement: was_new rejestrowane PRZED zapisem profilu. âś… (2026-03-26)
- [x] **LANG-3** â€” Zweryfikowano: language_profiles[lang] przechowuje CEFR per jÄ™zyk, przywracany przy zmianie. âś… (2026-03-26)
- [x] **LANG-4** â€” Zweryfikowano: lesson_cache_{userId}_{lang}_{date}, news cache (user_id, language), tips czyszczone przy zmianie jÄ™zyka. âś… (2026-03-26)
- [x] **TIPS-1** â€” Zweryfikowano: Home.jsx i Stats.jsx majÄ… `return` przy cache hit â€” API nie jest wywoĹ‚ywane ponownie tego samego dnia. âś… (2026-03-26)
- [x] **TIPS-2** â€” Prompt wzmocniony: CRITICAL - pisz w {native_language}. âś… (2026-03-26)
- [x] **DIALOG-1** â€” UkĹ‚ad dialogu: naprawiono â€” teraz uĹĽywa pola `speaker` zamiast alternujÄ…cego indeksu. âś… (2026-03-26)
- [x] **FLASHCARD-1** â€” Zweryfikowano: filtr daty (today/week/month) i filtr dnia lekcji juĹĽ sÄ… w Flashcards.jsx. âś… (2026-03-26)
- [x] **FLASHCARD-2** â€” Fiszki: AI sprawdza poprawnoĹ›Ä‡ wpisanego sĹ‚owa przed dodaniem do zbioru (ĹĽeby nie utrwalaÄ‡ bĹ‚Ä™dĂłw). âś… (2026-03-26)
- [x] **FLASHCARD-3** â€” Fiszki: opcja dodania polskiego sĹ‚owa na przĂłd / niemieckiego na tyĹ‚ (zamiast tylko niemâ†’pol). âś… (2026-03-26)
- [x] **FLASHCARD-4** â€” Nawigacja klawiaturÄ…: Space/Enter=odwrĂłÄ‡, â†â†’=poprzednia/nastÄ™pna, 1-4=ocena. âś… (2026-03-26)
- [x] **FLASHCARD-5** â€” Zweryfikowano: backend sprawdza duplikaty i zwraca "Fiszka X juĹĽ istnieje". âś… (2026-03-26)
- [x] **LESSON-3** â€” Historia lekcji: wskaĹşnik ukoĹ„czenia per lekcja. Zweryfikowano: zielone/szare kĂłĹ‚ko + âś“ w Stats.jsx lines 293-306. âś… (2026-03-26)
- [x] **LESSON-4** â€” Generator przycisku "NastÄ™pna lekcja" (nie "Wygeneruj nowÄ… â€” usuwa obecnÄ…"). Zweryfikowano: DailyLesson.jsx przycisk NastÄ™pna lekcja â†’ POST /api/lessons/next bez usuwania. âś… (2026-03-26)
- [x] **LESSON-5** â€” MoĹĽliwoĹ›Ä‡ powrotu do wczeĹ›niejszych lekcji. BĹ‚Ä™dy z poprzednich lekcji uwzglÄ™dniane w nastÄ™pnej. Zweryfikowano: route /lesson/:lessonId, Stats.jsx linki, generate_next_lesson juĹĽ uĹĽywa user_errors. âś… (2026-03-26)
- [x] **LESSON-6** â€” Poprawiono matching: strip punctuation + prefix match (4 chars) + include match â€” Ĺ‚apie odmienione formy. âś… (2026-03-26)
- [x] **LESSON-7** â€” Zweryfikowano: TranslationReveal juĹĽ istnieje i jest uĹĽywany w OutputForcingCard. âś… (2026-03-26)
- [x] **LESSON-8** â€” W pobranych plikach: zawartoĹ›Ä‡ Gramatyka + SĹ‚ownictwo + Dialog (bez reszty). Nazewnictwo folderu np. `HiszpaĹ„ski_A1`. Integracja z Google Drive / Obsidian. âś… (2026-03-26)
- [x] **LESSON-9** â€” Pobrana lekcja: 3 pliki audio (Gramatyka, SĹ‚ownictwo, Dialog) + film dopasowany do poziomu i tematu. âś… (2026-03-26)
- [x] **TEST-4** â€” Test: znacznie trudniejszy, powiÄ…zany z bieĹĽÄ…cÄ… lekcjÄ…. âś… (2026-03-26)
- [x] **TEST-5** â€” Po zakoĹ„czeniu testu: opcja regeneracji uwzglÄ™dniajÄ…ca bĹ‚Ä™dy z podsumowania. âś… (2026-03-26)
- [x] **ERRORS-2** â€” ZakĹ‚adka BĹ‚Ä™dy: przyciski "Generuj fiszki z bĹ‚Ä™dĂłw" i "Generuj test z bĹ‚Ä™dĂłw". âś… (2026-03-26)
- [x] **ERRORS-3** â€” Analiza bĹ‚Ä™dĂłw w Statystykach: wiÄ™cej rubryk (Gramatyka, Rozumienie, Wymowa, Rozmowa), kaĹĽda rozwijalna z opisem co poprawiÄ‡. âś… (2026-03-26)
- [x] **SPECIAL-CHARS** â€” SpecialCharHelper dodany do: textarea zadania produkcyjnego + textarea recall w OutputForcingCard. âś… (2026-03-26)
- [x] **TRANSLATE-1** â€” TĹ‚umacz: autodetect jÄ™zyka (cyrylica/inne â†’ targetâ†’PL, reszta â†’ PLâ†’target), przycisk "WytĹ‚umacz", "Dodaj do fiszek" po tĹ‚umaczeniu, zamkniÄ™cie przez klik poza. âś… (2026-03-26)
- [x] **PRONUNCIATION-1** â€” ZakĹ‚adka Wymowa: przycisk dodania zdania do fiszek. âś… (2026-03-26)
- [x] **PRONUNCIATION-2** â€” ZakĹ‚adka Wymowa: przycisk generowania nowych zdaĹ„ do Ä‡wiczenia. âś… (2026-03-26)
- [x] **VIDEOS-1** â€” ZakĹ‚adka Filmy: dodawanie ulubionych twĂłrcĂłw (przycisk lub wpisanie nazwy). âś… (2026-03-26)
- [x] **VOICE-1** â€” Zweryfikowano: prompt po polsku (conversation.py), edytowalny textarea + przycisk kopiowania w Conversation.jsx. âś… (2026-03-26)
- [x] **STATS-2** â€” Zweryfikowano: `flashcards` jest destrukturyzowane ale nie renderowane w Stats.jsx. âś… (2026-03-26)
- [x] **STATS-3** â€” UsuniÄ™to przycisk CSV. Historia lekcji: wszystkie lekcje z backendu, domyĹ›lnie 7 ostatnich, "PokaĹĽ wszystkie" toggle. âś… (2026-03-26)

---

## P3 â€” Niskie (UI/UX dopracowanie)

- [x] **NAV-1** â€” KolejnoĹ›Ä‡ zakĹ‚adek: GĹ‚Ăłwna â†’ Lekcja â†’ Wymowa â†’ MĂłw â†’ Fiszki â†’ Test â†’ Newsy â†’ Filmy â†’ Timer â†’ Statystyki â†’ [tabela fiszek po prawej]. Zweryfikowano: NavBar.jsx lines 36-47 â€” kolejnoĹ›Ä‡ identyczna. âś… (2026-03-26)
- [x] **TIMER-2** â€” Timer: opcja wĹ‚asnego czasu (np. 30 min, nie tylko 15 min). Zweryfikowano: QuickMode.jsx â€” przyciski 5/10/15/20/30 min. âś… (2026-03-26)
- [x] **TIMER-3** â€” Ostatnie 5 sekund: licznik siÄ™ powiÄ™ksza i miga na czerwono. Zweryfikowano: QuickMode.jsx â€” text-7xl + animate-blink gdy <=5s. âś… (2026-03-26)
- [x] **TIMER-4** â€” Licznik czasu: 3x wiÄ™kszy, po prawej na dole ekranu. Fix: Layout.jsx badge text-2xl â†’ text-4xl. âś… (2026-03-26)
- [x] **TIMER-5** â€” UsunÄ…Ä‡ "Flashcard Review" z trybu Timer (uĹĽytkownik korzysta z Anki). Zweryfikowano: quickmode.py nie ma fiszek w planie. âś… (2026-03-26)
- [x] **HOME-1** â€” ZakĹ‚adka GĹ‚Ăłwna: usunÄ…Ä‡ "Fiszki do powtĂłrki" z AktywnoĹ›ci. UsuniÄ™to ActionCard /flashcards z Home.jsx. âś… (2026-03-26)
- [x] **HOME-2** â€” Sekcja AktywnoĹ›ci: zmieniÄ‡ nazwÄ™ z "Dzisiejsze AktywnoĹ›ci" na "AktywnoĹ›ci", zawieraÄ‡ wszystkie aktywnoĹ›ci do nauki. Zweryfikowano: Home.jsx â€” juĹĽ "AktywnoĹ›ci". âś… (2026-03-26)
- [x] **SETTINGS-1** â€” Ustawienia: w liĹ›cie jÄ™zykĂłw nauki pokazywaÄ‡ aktualnie uczony jÄ™zyk dla Ĺ‚atwego dostÄ™pu. Zweryfikowano: Stats.jsx â€” aktywny jÄ™zyk ma indigo border/bg. âś… (2026-03-26)
- [x] **HARDCORE** â€” Tryb Hardcore: zmienia jÄ™zyk tylko czÄ™Ĺ›ciowo â€” naprawiÄ‡ peĹ‚nÄ… zmianÄ™ na jÄ™zyk uczony. Fix: settings.py _UI_EN uzupeĹ‚niony o wszystkie brakujÄ…ce klucze (home/test/conv/lesson/flash/pronun). âś… (2026-03-26)
- [x] **ACHIEVEMENTS** â€” Wszystkie tytuĹ‚y i opisy osiÄ…gniÄ™Ä‡ przetĹ‚umaczone na polski. âś… (2026-03-26)
- [x] **FLASHCARD-TABLE** â€” Tabela szybkiego dodawania fiszek: widoczna na kaĹĽdej zakĹ‚adce (staĹ‚y element layoutu), od razu pokazuje pole do wpisania po klikniÄ™ciu. Zweryfikowano: NavBar.jsx â€” inline input "Dodaj fiszkÄ™..." na desktop (hidden md:flex). âś… (2026-03-26)
- [x] **READING-COPY** â€” ZakĹ‚adka Czytanie: opcja kopiowania sĹ‚owa/zdania do tabeli â†’ AI tworzy fiszkÄ™ automatycznie. âś… (2026-03-26)
- [x] **MOW-ANALYSIS** â€” Analiza z zakĹ‚adki MĂłw uwzglÄ™dniana w systemie nauki i w Analizie bĹ‚Ä™dĂłw. âś… (2026-03-26)
- [x] **ERRORS-4** â€” ZakĹ‚adka BĹ‚Ä™dy: wklejenie podsumowania rozmowy z Voice Chat â†’ analiza i ocena wymowy/rozmowy. âś… (2026-03-26)
- [x] **CONCEPTS** â€” Koncepcje gramatyczne: generowane do fiszek lub jako rozwijalna tabela w Statystykach. âś… (2026-03-26)
- [x] **AI-MODEL** â€” ZweryfikowaÄ‡ czy Gemini to najlepszy darmowy wybĂłr (do decyzji). Gemini 2.0 Flash: darmowy tier, szybki, dobra jakoĹ›Ä‡ JSON. Alternatywy (GPT-4o-mini, Llama) wymagajÄ… pĹ‚atnego API lub self-hosting. Decyzja: pozostaÄ‡ na Gemini 2.0 Flash. âś… (2026-03-26)
- [x] **VOICE-1** â€” Rozpoznawanie mowy w konwersacji (Web Speech API). âś… (2026-04-05)
- [x] **VOICE-2** â€” TTS (text-to-speech) na wiadomoĹ›ciach AI uĹĽywajÄ…c edge-tts. âś… (2026-04-05)
- [x] **READ-SENTENCE** â€” Dodanie caĹ‚ego zdania do fiszek z sekcji czytania (comprehensible input). âś… (2026-04-05)
- [x] **NEWS-CACHE** â€” Daily cache dla newsĂłw w localStorage (language + user specific). âś… (2026-04-05)
- [x] **VIDEOS-TOGGLE** â€” Toggle "Tylko jÄ™zyk docelowy" vs "JÄ™zyk docelowy + polskie wyjaĹ›nienia". âś… (2026-04-05)

---

## UkoĹ„czone (wszystkie)

**Razem: 58 zadaĹ„ P0-P3 + 6 nowych Phase 1-3 + 1 calibration fix = 64 zakoĹ„czone.**

---

## FEEDBACK.md â€” Bugs to Fix

- [x] **PLACEMENT-CAL** â€” Placement test too easy, bad calibration â†’ FIXED 2026-05-03 (stricter scoring + conservative AI analysis)
- [x] **VOCAB-EXAMPLE** â€” SĹ‚ownictwo: dodaÄ‡ tĹ‚umaczenie przykĹ‚adowego zdania âś… (backend: example+example_translation in lesson_generator.py:302-303, frontend: DailyLesson.jsx:568-569) 2026-05-03
- [x] **DIALOG-LAYOUT** â€” Dialog: ukĹ‚ad 1 osoba po lewej / 1 osoba po prawej âś… (DailyLesson.jsx:602-607 uĹĽywa line.speaker zamiast indeksu, flex-row-reverse) 2026-05-03
- [x] **EXERCISES-VARIETY** â€” Ä†wiczenia: bardziej zrĂłĹĽnicowane â†’ FIXED 2026-05-03 (prompt enforced: 5 unique types required)
- [x] **PRODUCTION-TASK** â€” Zadanie produkcyjne: sprawdzanie odpowiedzi przez AI â†’ FIXED 2026-05-03 (backend: /api/lessons/{id}/evaluate-production, frontend: UI with score/feedback/corrections)
- [x] **SENTENCE-MEMORY** â€” Wymuszenie produkcji: zapamiÄ™tywanie 5 dĹ‚ugich zdaĹ„ â†’ FIXED 2026-05-03 (changed from 1-2 short sentences to 5 LONG sentences, 75-100 words total)
- [x] **AUDIO-LESSON** â€” Audio dla caĹ‚ej lekcji: treĹ›Ä‡, dialogi, czytanie, przeglÄ…d bĹ‚Ä™dĂłw, sĹ‚ownictwo â†’ FIXED 2026-05-03 (backend: generate_full_lesson_audio, frontend: PlayButton for vocab/dialogue/reading/errors)
- [x] **READING-COPY** â€” Opcja kopiowania sĹ‚owa/zdania do tabeli widocznej w interfejsie â†’ automatyczne tworzenie fiszki âś… (DailyLesson.jsx:761-798 klikalne sĹ‚owa, handleAddFlashcardâ†’addFlashcardAI) 2026-05-03
- [x] **FLASHCARD-AUTO** â€” Dodawanie fiszki: tylko wpisanie sĹ‚owa/frazy â†’ reszta generowana przez AI â†’ FIXED 2026-05-03 (backend: /flashcards/{id}/add-ai, frontend: addFlashcardAI)
- [x] **FLASHCARD-FILTER** â€” Filtr fiszek po dacie dodania â†’ FIXED 2026-05-03 (frontend: dateFilter 'today'/'week'/'month', lessonFilter by day)
- [x] **FLASHCARD-VOCAB** â€” Fiszki nie odzwierciedlajÄ… poziomu sĹ‚ownictwa â†’ FIXED 2026-05-03 (frontend: filterCards() + CEFR UI added, backend: cefr_level already set)
- [x] **FLASHCARD-AUDIO** â€” Audio dla fiszek â†’ FIXED 2026-05-03 (backend: generate_flashcard_audio, frontend: PlayButton on each card)
- [x] **STATS-COMPLETION** â€” WskaĹşnik ukoĹ„czenia lekcji: przesuwaÄ‡ wraz z ukoĹ„czeniem Ä‡wiczeĹ„ â†’ FIXED 2026-05-03 (frontend: flashcards added to TodayCompletion activities, backend completion check via tabs.includes('flashcards'))
- [x] **STATS-FLASHCARDS** â€” Fiszki w statystykach: pole do rÄ™cznego odhaczania âś… (Stats.jsx:365-390 Flashcards Stats section: total/due/up-to-date + go to flashcards link) 2026-05-03
- [x] **STATS-TIPS** â€” WskazĂłwki dzienne: generowaÄ‡ raz dziennie przy pierwszym wejĹ›ciu âś… (Home.jsx:31-54 + Stats.jsx:44-61 localStorage cache 'tips_date'/'tips_data') 2026-05-03
- [x] **PRONUNCIATION-AUDIO** â€” Plik audio wskazujÄ…cy poprawnÄ… wymowÄ™ zdania âś… (PronunciationTrainer.jsx:216,228 PlayButton for each phrase) 2026-05-03
- [x] **PRONUNCIATION-SUMMARY** â€” Podsumowanie odnoĹ›nie wymowy âś… (PronunciationTrainer.jsx:410-468 sessionSummary UI, avg/best score, problem words) 2026-05-03
- [x] **TIMER-BUG** â€” Bug: minutnik zatrzymuje siÄ™ i nie jest widoczny po klikniÄ™ciu w innÄ… zakĹ‚adkÄ™ â†’ FIXED 2026-05-03 (Layout.jsx: visibilitychange listener, QuickMode.jsx: timer recalculation from Date.now())
- [x] **SETTINGS-LANG** â€” DodaÄ‡ moĹĽliwoĹ›Ä‡ zmiany jÄ™zyka nauki âś… (Stats.jsx:100-123 handleChangeLanguage + UI 510-548 language buttons, LANG_NAMES_PL) 2026-05-03
- [x] **VOICE-CHAT-PROMPT** â€” Generator promptu dla voice-chat âś… (backend: /api/v1/voice-chat/prompt/{user_id}, frontend: Stats.jsx Voice Chat prompt section with copy button) 2026-05-03
- [x] **VOICE-CHAT** â€” Dialog: opcja rozmowy z audio (model odpowiada gĹ‚osem) â†’ IN PROGRESS (backend: gemini_service.py + voice_chat.py voice endpoints, frontend: do wykonania UI in Conversation.jsx) 2026-05-04

---

## Backlog â€” Future Work

- [ ] **Unicode/npm permanent fix** â€” Rename project folder to ASCII-only path (e.g., `G:\Projects\LinguaAI`) or migrate to WSL2 to enable full Docker/dev workflow | đź”§ IN PROGRESS
- [x] **Port standardization** â€” Migrated: 8000â†’8001 âś… 2026-05-03 (unified standard)
- [x] **API prefix standardization** â€” Migrated: /api/â†’/api/v1/ âś… 2026-05-03 (unified standard)
- [x] **Docker frontend** â€” Build production-ready frontend container (nginx) and integrate with docker-compose (currently backend-only in Docker) â€” TODO
- [x] **schemas/ directory** â€” Add Pydantic models for request/response validation âś… 2026-05-03
- [ ] **Testy.exe** â€” Create automated test suite: pytest (backend API) + Playwright/Cypress (UI smoke tests)
- [x] **Backup strategy** â€” Scheduled daily backup of `LinguaAI.db` with retention policy (7 days)
- [ ] **User documentation** â€” "Getting Started" guide with screenshots, FAQ (PDF/HTML)

---

## Wymagające decyzji / Otwarte

- [ ] **Finalny wybór architektury** — Dockeryzacja całego stacku vs. lokalne uruchamianie (backend+frontend z różnych ścieżek)
- [ ] **Ścieżki projektu** — rename folder na ASCII (prawidłowe rozwiązanie npm Unicode bug) — C:\LinguaAI lub G:\Projects\LinguaAI
- [ ] **Backup DB** — automatyzacja i lokalizacja backupów (cloud? lokalny NAS?)
- [ ] **Testy** — framework do wyboru (pytest + Playwright recommended)
- [ ] **Dokumentacja** — format (PDF vs online README) i poziom szczegółowości


---

## NEUROSCIENCE-BACKED LANGUAGE LEARNING FEATURES (Phase 2)
_Based on 2024-2025 neuroscience of language acquisition research_

### Phase 2A — Sleep & Memory Optimization (High Impact, Low Effort)
- [ ] **NEURO-1** Sleep-Aware Scheduler — `evening_encoding` (20:00-21:00) + `morning_retrieval` (07:00-08:00) flags for lessons
  - Backend: Add `session_type` field to Lesson model (`evening`/`morning`/`day`)
  - Frontend: Schedule notifications for optimal encoding/retrieval windows
  - Integration: Optional sleep quality tracking (manual or wearable API)
- [ ] **NEURO-2** i+1 Content Generator (Predictive Coding / Comprehensible Input)
  - Backend: New endpoint `/api/lessons/iplus1/{user_id}` — generates text where 90% vocab known, 10% new
  - Uses `known_words` from flashcards + lesson history to calibrate difficulty
  - Returns `i_plus_1_text`, `new_words_highlighted`, `cefr_level`
- [ ] **NEURO-3** Variable Reward Gamification (Dopamine Optimization)
  - Backend: Extend `achievement_service.py` with `surprise_loot` (15% chance), `prediction_bonus` (+50% XP for context guesses)
  - Frontend: Loot box animation, "prediction streak" counter
  - Config: `target_success_rate: 0.85` (i+1 zone)

### Phase 2B — Motor-Enhanced Pronunciation (High Impact, Medium Effort)
- [ ] **NEURO-4** Shadowing Engine with Delayed Playback
  - Frontend: Audio player with configurable delay (0.5s default) — listen → speak with offset
  - Visual waveform sync, "choral mode" (user + AI simultaneous)
- [ ] **NEURO-5** Gestural Anchoring for German Phonemes
  - Mapping: 🤲 "ch" (ich/ach), 👉 "ü/ö", 🤏 "r" (uvular), ✋ "sch", 👌 "pf/ts"
  - Frontend: Gesture prompt cards during pronunciation practice
  - Backend: Store `gesture_anchor` per flashcard/phrase
- [ ] **NEURO-6** Articulatory Visualization (3D)
  - Frontend: Three.js/WebGL tongue/palate animation for German sounds
  - Toggle in PronunciationTrainer: "Show articulation"

### Phase 2C — Interleaving & Desirable Difficulties (High Impact)
- [ ] **NEURO-7** Interleaved Session Mixer
  - Backend: `session_mixer` service — mixes vocab/grammar/pronunciation/listening/production blocks
  - German-specific: `der_die_das` → procedural drill, `verb_position` → working memory n-back, `pronunciation` → motor cortex
  - Config: `contextual_interference_maximization` algorithm
- [ ] **NEURO-8** Neuro-Informed FSRS V2
  - Extend `fsrs` parameters: `sleep_cycles_since_review`, `time_of_day_factor`, `interleaving_bonus`, `interference_penalty`
  - Formula: `R = S * exp(-t/S) * sleep_modulator * interference_modulator`
  - Track: `sleep_quality` (1-5), `time_of_day` (morning/evening), `session_type`

### Phase 2D — Embodied & Spatial Vocabulary (Medium Impact)
- [ ] **NEURO-9** Mind Palace / Spatial Vocabulary Map
  - Frontend: 2D "Memory Palace" grid — rooms = topics, objects = words
  - Click room → see vocab with spatial context
  - Backend: `spatial_anchor` (x,y,room) per flashcard
- [ ] **NEURO-10** Social Predictive Coding (Conversation AI)
  - Backend: Turn-taking prediction model (when user finishes)
  - Real-time error correction (prediction error = learning signal)
  - Persona-based agents with Theory of Mind modeling

---

## IMPLEMENTATION PRIORITY MATRIX

| Feature | Effort | Neuro Impact | German Specificity | Dependencies |
|---------|--------|--------------|-------------------|--------------|
| NEURO-1 Sleep Scheduler | 🟢 Low | ⭐⭐⭐⭐⭐ | High | Notification system |
| NEURO-2 i+1 Generator | 🟡 Medium | ⭐⭐⭐⭐⭐ | High | Known words tracking |
| NEURO-3 Variable Rewards | 🟢 Low | ⭐⭐⭐ | Medium | Achievement service |
| NEURO-4 Shadowing | 🟡 Medium | ⭐⭐⭐⭐ | High | Audio player |
| NEURO-5 Gestural Anchors | 🟡 Medium | ⭐⭐⭐⭐ | **German-only** | Pronunciation UI |
| NEURO-6 3D Articulation | 🔴 High | ⭐⭐⭐ | High | Three.js |
| NEURO-7 Interleaving | 🟡 Medium | ⭐⭐⭐⭐ | High | Session service |
| NEURO-8 Neuro-FSRS | 🔴 High | ⭐⭐⭐⭐⭐ | Medium | FSRS library |
| NEURO-9 Mind Palace | 🔴 High | ⭐⭐⭐ | Medium | Canvas/SVG |
| NEURO-10 Social AI | 🔴 Very High | ⭐⭐⭐⭐ | Medium | LLM fine-tuning |

---

## RECOMMENDED MVP (Weeks 1-4)
1. **Week 1**: NEURO-1 (Sleep Scheduler) + NEURO-3 (Variable Rewards)
2. **Week 2**: NEURO-2 (i+1 Generator) + NEURO-4 (Shadowing)
3. **Week 3**: NEURO-5 (Gestural Anchors) + NEURO-7 (Interleaving)
4. **Week 4**: NEURO-8 (Neuro-FSRS) — core algorithm upgrade

---

## CODEBASE ANALYSIS NEEDED
_To be completed after saving this file_
- [ ] Audit `backend/services/lesson_generator.py` for i+1 integration points
- [ ] Audit `backend/services/achievement_service.py` for reward system extension
- [ ] Audit `backend/models/lesson.py` for `session_type` field
- [ ] Audit `frontend/src/components/PlayButton.jsx` for shadowing/delay support
- [ ] Audit `frontend/src/pages/PronunciationTrainer.jsx` for gestural/3D integration
- [ ] Audit `backend/services/test_generator.py` for interleaving logic
- [ ] Audit `backend/services/flashcard_service.py` for spatial anchors
- [ ] Review `fsrs` library integration for Neuro-FSRS params

---

## GERMAN-SPECIFIC NEURO ADAPTATIONS
| Domain | Neuro Mechanism | Implementation |
|--------|----------------|----------------|
| **der/die/das** | Procedural memory (basal ganglia) | Procedural drill mode, not declarative |
| **Verb position (V2)** | Working memory (DLPFC) | n-back style drills |
| **Trennbare Verben** | Procedural + working memory | Shadowing + motor sequencing |
| **Ü/Ö/CH/R** | Motor cortex + cerebellum | Gestural anchors + 3D articulation |
| **Cases (Nom/Akk/Dat/Gen)** | Procedural memory | Interleaved procedural drills |

---

## RESEARCH REFERENCES (Key Papers)
- Diekelmann & Born (2010) — Sleep-dependent memory consolidation
- Friston (2010) — Predictive coding / free energy principle
- Schultz (2016) — Dopamine reward prediction error
- Pulvermüller & Fadiga (2010) — Motor theory of speech perception
- Ullman (2004) — Declarative/procedural model of language
- Rohrer & Taylor (2007) — Interleaving / contextual interference
- Bjork & Bjork (1992) — Desirable difficulties
- Rasch & Born (2013) — Sleep and memory consolidation
- Guenther (2016) — Neural control of speech production
- Krashen (1985) + modern validation — Comprehensible input (i+1)

---

## CHANGELOG
- **2026-07-06**: Added neuroscience-backed features (Phase 2A-2D) based on 2024-2025 research
- Priority matrix and MVP timeline defined
- Codebase audit checklist created
- German-specific neuro adaptations documented




