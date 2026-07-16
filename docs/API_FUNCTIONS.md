# Dokumentacja funkcji LinguaAI — i ich wpływ na naukę języka

_Ostatnia aktualizacja: 2026-07-15 (po audycie kompleksowym)._

Ten dokument opisuje wszystkie główne funkcje backendu (FastAPI), serwisy i modele
oraz wyjaśnia, **w jaki sposób każda z nich wspiera skuteczną naukę języka** według
współczesnej literatury (zob. sekcję „Zgodność z badaniami” w `TASKS.md`).

---

## 1. Architektura (przepływ żądania)

```
Router (FastAPI) → Service (logika AI/FSRS) → SQLAlchemy Session (get_db)
```

- Każdy endpoint bierze `db: Session = Depends(get_db)`.
- AI jest wywoływane przez `backend.services.gemini_service` (OpenRouter domyślnie,
  model dobierany przez `model_router` per zadanie — patrz `@with_model`).
- Wszystkie endpointy są pod `/api/*` (frontend `baseURL: '/api'`).

---

## 2. Routers (API)

### Placement (`/api/placement/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `POST /start` | `start_placement` — generuje 20-pytań test CEFR | **Diagnoza poziomu** (A1–C2) — warunek adaptacji trudności (Vygotsky ZPD). |
| `POST /submit` | `submit_placement` — analizuje wynik, zapisuje `TestResult`, generuje `StudyPlan` | Personalizacja ścieżki (zgodne z *VanLehn 2011*, adaptywność). |
| `POST /create-user` | `create_user` — tworzy użytkownika (A1) | Punkt wejścia dla wielojęzyczności (`language_profiles`). |

### Lessons (`/api/lessons/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `GET /today/{user_id}` | `get_today_lesson` — pobiera/ generuje lekcję dnia | **Comprehensible input** (Krashen i+1), RAG z fiszek/słabych tematów (interleaving). |
| `GET /{lesson_id}` | `get_lesson` — szczegóły + weryfikacja właściciela | Bezpieczeństwo danych. |
| `POST /{id}/complete` | complete — +25 XP, `check_and_award_achievements` | **Retrieval + motywacja** (XP/streak). |
| `POST /{id}/evaluate-production` | `evaluate_production` — ocenia wypowiedź | **Output forcing** (aktywne produkowanie języka). |
| `GET /export-pdf` | `export_lesson_pdf` — PDF (fpdf2) | Offline review. |
| `GET /audio/{id}` | audio lekcji (edge-tts) | Fonologiczna pętla (słuchanie + powtarzanie). |

**Struktura lekcji** (`generate_daily_lesson`): warmup, vocabulary (10–15),
grammar, exercises, cultural_note, speaking_practice, writing_exercise, wrap_up,
**interleaved_review** (z poprzednich tematów — interleaving!), **output_forcing**
(zakryj/odtwórz — active recall), **comprehensible_input** (i+1, 90% znane/10% nowe).

### Tests (`/api/tests/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `GET /daily/{user_id}` | `get_daily_test` — test z lekcji dnia | **Testing effect** (Karpicke & Roediger 2008). |
| `POST /submit` | `submit_test` — analiza błędów, XP `score×0.5` (max 50), achievements | **Retrieval + error correction** (Lyster & Ranta 1997). |
| `GET /weekly/{user_id}` | `get_weekly_test` — test z planu | Rozłożona powtórka (spacing). |
| `GET /errors/{user_id}` | `get_errors_test` — test z historii błędów | **Targeted retrieval** (naprawianie słabości). |

### Flashcards (`/api/flashcards/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `GET /{user_id}` | lista fiszek (aktywne) | Przegląd materiału. |
| `GET /{user_id}/due` | fiszki do powtórki (`next_review_date <= now`) | **Spaced repetition** (FSRS). |
| `POST /{id}/review` | `review_flashcard` — rating 1–4, neuro-FSRS (sen/circadian/interference), achievements | Optymalne interwały + **desirable difficulties** (Bjork). |
| `POST /{user_id}/export-anki` | eksport `.apkg` | Przenośność do Anki. |
| `POST /add`, `/add-ai`, `/batch-add` | dodawanie fiszek | Kontrola ucznia (autonomia). |

### Topics (`/api/topics/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `GET /{user_id}` | lista tematów (FSRS state) | Organizacja wiedzy. |
| `GET /{user_id}/due` | tematy do powtórki | Spaced repetition per topic. |
| `POST /{id}/review` | `review_topic` — `topic.apply_fsrs` (prawdziwa lib `fsrs` v6) | Najdokładniejszy scheduler w systemie. |
| `GET /tree`, `/stats`, `/detail/{id}` | przegląd/hierarchia | Metapoznanie. |

### Conversation (`/api/conversation/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `POST /start/{user_id}` | `start_conversation` — scenariusz AI | **Negotiation of meaning** (Long 1996). |
| `POST /message` | `send_message` — odpowiedź AI (historia 10 msgs) | Interakcja językowa w czasie rzeczywistym. |
| `POST /analyze` | `analyze_session` — błędy + XP + **achievements** | **Feedback + metapoznanie**. |
| `POST /analyze-text` | `analyze_pasted_text` — analiza wklejonego tekstu + achievements | Autonomia (własny materiał). |
| `POST /translate`, `/question` | tłumaczenie / pytania o język | Wsparcie w czasie nauki. |

### Stats (`/api/stats/`)
| Endpoint | Funkcja | Wpływ na naukę |
|---|---|---|
| `GET /{user_id}` | `get_stats` — lekcje/testy/fiszki/achievements/toasty | **Metapoznanie + motywacja** (SDT). |
| `GET /{user_id}/leaderboard` | pozycja wg XP | Gamifikacja (umiar — rywalizacja może szkodzić słabym). |
| `GET /{user_id}/export-csv` | CSV postępu | Śledzenie trendu. |
| `GET /{user_id}/errors` | grupowane błędy | **Error analysis**. |
| `GET /tips/{user_id}` | `generate_daily_tips` | Mikro-nauka codzienna. |

### News (`/api/news/`), Pronunciation (`/api/pronunciation/`), YouTube (`/api/youtube/`), Voice-Chat (`/api/voice-chat/`), QuickMode (`/api/quickmode/`), Settings (`/api/...`)
- **News**: RSS + uproszczenie do CEFR → **autentyczny input** (real-world i+1).
- **Pronunciation**: faster-whisper + word-level score → **sensory-motor loop** (Derwing & Munro 2015).
- **YouTube**: wyszukiwanie materiałów → autentyczny input wideo.
- **Voice-Chat**: rozmowa głosowa → płynność.
- **QuickMode**: 15-min plan → **dostępność** (małe sesje = wyższa regularność).
- **Settings**: zmiana języka/API key/neuro-wag → personalizacja.

---

## 3. Serwisy (logika)

| Serwis | Rola | Uwagi naukowe |
|---|---|---|
| `gemini_service` | Jedyny punkt kontaktu z AI (`generate_json`/`generate_text`). `@with_model` dobiera model z `model_router`. | **Brak fallbacku JSON** przy błędzie (rzuca `ValueError`→500) — do poprawy (CLAUDE.md obiecuje fallback). |
| `model_router` | Kuratela 50+ modeli OpenRouter, tiery free/cheap/best, mapa per-zadanie. | Centralizacja — brak hardcoded `:free`. |
| `lesson_generator` | `generate_daily_lesson` (RAG+i+1+interleaving), `generate_iplus1_content`, `analyze_test_errors`, `analyze_conversation`. | Rdzeń pedagogiczny. |
| `fsrs_service` | Prawdziwa lib `fsrs` v6 (`apply_fsrs`, `calculate_memory_strength_fsrs`). | Używana przez **topics**. |
| `fsrs_neuro` | Heurystyka neuro (sen/circadian/interference). | Używana przez **flashcards** — przybliżenie, nie kalibrowane (rek. migracja na `fsrs_service`). |
| `test_generator` | `submit_test` (idempotentny, XP), `get_or_create_*`. | Bezpieczna powtórka. |
| `achievement_service` | `calculate_level_from_xp` (krzywa `(n-1)²×20`), `check_and_award_achievements` (wywoływane w lessons/tests/conversation/flashcards). | Gamifikacja (SDT). |
| `streak_service` | `calculate_streak` (dni + freezes). | Nawyk (regularność > intensywność). |
| `topic_service` | Ekstrakcja tematów AI, CRUD, `review_topic` (FSRS lib). | Organizacja wiedzy. |
| `flashcard_service` | `create_flashcards_from_vocab` (dedup). | Wydajne tworzenie fiszek. |
| `pdf_service`, `audio_service`, `anki_service`, `obsidian_service`, `pronunciation_service`, `backup_service` | Eksporty/audio/backup. | Wsparcie offline. |

---

## 4. Modele (SQLAlchemy)

`User` (XP, streak, języki, neuro_wagi), `Lesson` (content JSON), `TestResult`
(błędy JSON), `Flashcard` (FSRS: difficulty/stability/retrievability/interval/
repetitions/lapses/fsrs_state/next_review_date), `Topic`/`TopicItem` (FSRS per temat),
`StudyPlan`, `Achievement` (type/unlocked_at/notified), `ConversationSession`,
`PronunciationAttempt`, `ErrorLog`.

---

## 5. Konfiguracja (`backend/config.py`)

- `AI_PROVIDER=openrouter` (domyślnie), `AI_MODEL_TIER=cheap`.
- `OPENROUTER_API_KEY` / `GEMINI_API_KEY` — wymagane dla AI.
- `DATABASE_URL`, `SECRET_KEY`, `ADMIN_API_KEY`, `TARGET_LANGUAGE`, `NATIVE_LANGUAGE`.

---

## 6. Jak funkcje wspierają naukę (podsumowanie)

1. **Spaced Repetition** (FSRS) → flashcards + topics → długotrwałe zapamiętywanie.
2. **i+1 / Comprehensible Input** → lekcje, i+1 content, news → zrozumiały progres.
3. **Retrieval Practice** → testy codzienne/tygodniowe/błędy → testing effect.
4. **Output Forcing** → lekcje + conversation → aktywne produkowanie.
5. **Error Analysis** → analyze_test_errors + stats/errors → korekta błędów.
6. **Interleaving** → interleaved_review + NEURO-12 → różnorodność wzmacnia.
7. **Personalizacja** → placement + RAG + study plan → adaptacja do ZPD.
8. **Motywacja** → XP/streak/achievements → SDT (autonomia, kompetencja, przynależność).
9. **Autonomia** → własne fiszki/news/tekst → uczeń kontroluje materiał.
10. **Dostępność** → QuickMode/audio/PDF → nauka wszędzie.

---

## 7. Znane luki (stan 2026-07-15 — WSZYSTKIE NAPRAWIONE, patrz TASKS.md → Status napraw luk)

- [NAPRAWIONE] Achievements nieosiągalne (brak `check_and_award_achievements` w conversation/flashcards).
- [NAPRAWIONE] `interleaved_review` puste.
- [NAPRAWIONE] Niezgodność sygnatur `generate_daily_lesson` (TypeError na żywo).
- [NAPRAWIONE] `gemini_service` brak fallbacku JSON (dodano `fallback` param).
- [NAPRAWIONE] Flashcards używały `fsrs_neuro` (heurystyka) → zmigrowano na `fsrs_service` (lib FSRS v6).
- [NAPRAWIONE] `stats.export_progress_csv` liczyło streak lokalnie → `streak_service.streak_at_date`.
