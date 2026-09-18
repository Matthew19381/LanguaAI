# SPEC: Asystent AI wbudowany w projekt — pilotaż LinguaAI

Status: **DO ZATWIERDZENIA PRZEZ WŁAŚCICIELA** (tryb SPEC, zero kodu napisane w tym zadaniu).
Zlecenie: 2026-09-18, `t_316245ca`. Pilotaż w LinguaAI, wzorzec do powielenia w innych modułach.

---

## 0. Streszczenie decyzji do zatwierdzenia

| # | Pytanie | Rekomendacja architekta |
|---|---|---|
| D-1 | Jak użytkownik wskazuje "o co mu chodzi" na ekranie? | **Tryb wskazywania elementu** (click-to-pick, jak "inspect") + zawsze dostępne pole tekstowe. Bez zrzutów ekranu/modeli wizyjnych (koszt, brak w free tier). |
| D-2 | Jak asystent zna domenę projektu? | **Statyczny system prompt + krótki "cheat sheet"** (`docs/ASSISTANT_CONTEXT.md`, ~2–3 KB) doklejany do każdego zapytania + kontekst runtime (strona, wskazany element, poziom CEFR usera). **Nie** pełny RAG/wektorowa baza — dokumentacja projektu mieści się w oknie kontekstu, RAG byłby przerostem formy nad treścią na tym etapie.
| D-3 | Który model / koszt? | Nowy task `"assistant"` w `model_router.py`, **domyślnie capowany na `free`** (`openai/gpt-oss-20b:free`), zgodnie z zasadą kosztów. Podniesienie do `cheap`/`best` wymaga jawnej zgody właściciela (per-projekt override w `.env`, nie w kodzie). |
| D-4 | Wzorzec do powielenia? | Nie wspólna biblioteka (projekty to osobne repo/porty/wdrożenia) — **udokumentowana "recepta"** (5 plików o stałym kształcie) kopiowana do każdego modułu, analogicznie do istniejącego wzorca `gemini_service.py` + `model_router.py`, który już jest duplikowany per-projekt celowo (patrz `spec-architekt` zasada #1 — to nie jest naruszenie, bo każdy moduł ma własną warstwę AI od początku). |

Wszystkie 4 decyzje wymagają jawnego "tak" właściciela przed jakąkolwiek implementacją (patrz §6).

---

## 1. Kontekst i ograniczenia z rejestru architekta

- **Zasada kosztów**: wyłącznie darmowe źródła, chyba że właściciel jawnie zaakceptuje wyjątek (zlecenie, punkt 3).
- **Zasada #1 spec-architekt**: zakaz piątego równoległego miejsca na tę samą funkcję — asystent AI to **nowa** funkcja (nie duplikat nauki/FSRS/testów), więc żyje w LinguaAI jako natywny moduł, nie w osobnym module ekosystemu.
- LinguaAI ma już dokładnie ten wzorzec warstwy AI, który trzeba powielić: `gemini_service.py` (jedyny punkt kontaktu z providerem) + `model_router.py` (tiery `free/cheap/best`, mapa zadanie→model, `TASK_TIER_CAP`/`TASK_TIER_FLOOR`). Asystent **nie wprowadza nowej architektury AI** — dokłada jeden task do istniejącej.
- Istnieje już mini-precedens: `POST /api/conversation/question` (`ask_question` w `conversation.py`) — user zadaje pytanie językowe, backend woła `answer_language_question(question, cefr_level, language, native_language)`. To pokazuje wzorzec "pytanie + kontekst usera → AI", ale **bez** kontekstu ekranu/elementu ani wiedzy o architekturze systemu. Asystent AI to rozszerzenie tego wzorca, nie zamiennik (inny cel: pytania o *aplikację*, nie o *język niemiecki*).

---

## 2. D-1: Mechanizm wskazywania elementu na ekranie

### Rozważone opcje

| Opcja | Opis | Ocena |
|---|---|---|
| A. Zrzut ekranu + model wizyjny | Użytkownik robi screenshot, AI "widzi" ekran | ❌ wymaga modelu multimodalnego (brak w katalogu `free`), koszt tokenów obrazu wysoki, nadmiarowe dla prostych pytań UI |
| B. Wyłącznie opis tekstowy | Użytkownik pisze "chodzi mi o przycisk w lekcji dnia" | ⚠️ działa zawsze jako fallback, ale niejednoznaczne przy złożonym UI |
| **C. Tryb "wskaż element" (click-to-pick)** | Przycisk "🎯 Wskaż na ekranie" przełącza kursor w tryb wskazywania (podświetlenie elementu pod kursorem, jak DevTools "Inspect"), klik zamyka tryb i zapamiętuje element | ✅ **rekomendowane** — zero kosztu AI, natywne w przeglądarce (`document.elementFromPoint`, event delegation), spójne z istniejącym wzorcem `TranslatorWidget` (floating widget) w `Layout.jsx` |
| D. Zaznaczenie tekstu (selection) | Użytkownik zaznacza fragment tekstu myszką | ⚠️ dobre uzupełnienie dla treści (np. "co znaczy to zdanie"), ale nie obejmuje elementów UI bez tekstu (ikony, przyciski) |

### Rekomendacja: C + D + B jako warstwy tego samego mechanizmu

1. **Zawsze dostępne pole tekstowe** (fallback, jak dziś w `TranslatorWidget`/`askQuestion`).
2. **Zaznaczenie tekstu** — jeśli użytkownik ma zaznaczony tekst w momencie otwarcia asystenta, automatycznie dołącz go jako `selected_text` (analogicznie do istniejącego `window.getSelection()`, którego repo jeszcze nie używa, ale to standardowe API).
3. **Tryb wskazywania elementu** — nowy, opisany niżej.

### Jak działa tryb wskazywania (techniczne)

- Przycisk "🎯 Wskaż element" w widgecie asystenta ustawia `document.body.style.cursor = 'crosshair'` i dodaje globalny listener `mousemove` (podświetlenie obrysem `outline` elementu pod kursorem) + `click` (capture, `preventDefault` + `stopPropagation`, żeby klik nie wykonał akcji strony).
- Po kliknięciu zbierany jest **mały, bezpieczny wycinek kontekstu** (nie cały DOM):
  ```js
  {
    tag: el.tagName,                              // "BUTTON"
    text: el.innerText?.slice(0, 200),            // widoczny tekst, ucięty
    aria_label: el.getAttribute('aria-label'),
    nearest_heading: findNearestHeading(el)?.innerText, // najbliższy h1-h3 nad elementem
    route: location.pathname,                      // np. "/lesson"
    testid: el.getAttribute('data-testid') || null, // jeśli komponent go ma
  }
  ```
- **Nic więcej nie jest wysyłane** — brak zrzutu ekranu, brak pełnego DOM, brak danych z innych pól formularza. To minimalizuje ryzyko wycieku (np. danych innego pola) i koszt tokenów.
- UI: po wskazaniu element dostaje chwilowy zielony obrys + widget pokazuje "wskazano: [tekst/tag]" z przyciskiem "✕ anuluj", żeby user widział co poszło do AI.

### Pilotażowe ograniczenie (celowe uproszczenie)

Na start **bez** `data-testid` na wszystkich komponentach frontendu — wycinek `tag + text + aria_label + route + nearest_heading` wystarczy do 90% pytań typu "co robi ten przycisk" / "dlaczego to się tak liczy". Dodanie `data-testid` do kluczowych komponentów to osobna, mała karta do rozważenia po pilotażu, jeśli jakość odpowiedzi będzie niewystarczająca.

---

## 3. D-2: Wiedza domenowa i kontekst systemu

### Dlaczego nie pełny RAG

RAG (embeddings + wektorowa baza) ma sens, gdy korpus wiedzy jest za duży, żeby zmieścić się w kontekście modelu, albo gdy trzeba wyszukiwać po znaczeniu w setkach dokumentów. Tutaj:
- Cała dokumentacja LinguaAI (`docs/ARCHITECTURE.md` + `CLAUDE.md`) to ~35 KB tekstu — mieści się w kontekście nawet darmowych modeli (`openai/gpt-oss-20b:free` ma 131K kontekstu, patrz `model_router.py`).
- RAG dokłada infrastrukturę (baza wektorowa, pipeline embeddingów, kolejny model do embeddingów — zwykle płatny), której projekt dziś nie ma i która nie jest darmowa "za darmo" (embeddingi API to osobny koszt/limit).
- Wprowadzenie RAG teraz byłoby przedwczesną optymalizacją wbrew zasadzie kosztów.

**Rekomendacja: statyczny system prompt + krótki, ręcznie kurowany "cheat sheet".**

### Kształt system promptu

```
[ROLA] Jesteś asystentem AI wbudowanym w LinguaAI — aplikację do nauki
niemieckiego z algorytmem FSRS v6. Odpowiadasz PO POLSKU, krótko i konkretnie.

[WIEDZA O SYSTEMIE] <treść docs/ASSISTANT_CONTEXT.md — patrz niżej>

[KONTEKST BIEŻĄCY]
- Użytkownik jest na stronie: {route}
- Poziom CEFR użytkownika: {cefr_level}
- Wskazany element: {element_context lub "brak"}
- Zaznaczony tekst: {selected_text lub "brak"}

[PYTANIE UŻYTKOWNIKA] {question}

[ZASADY]
- Jeśli pytanie dotyczy słownictwa/gramatyki niemieckiego → odpowiadaj jak
  nauczyciel (już obsługiwane przez /api/conversation/question — nie duplikuj,
  przekieruj tam jeśli pytanie jest czysto językowe).
- Jeśli pytanie dotyczy działania aplikacji (ten ekran/przycisk/liczba) →
  wyjaśnij zwięźle, odwołując się do wskazanego elementu.
- Nie znasz odpowiedzi / brak w kontekście → powiedz to wprost, nie zgaduj.
- Nigdy nie ujawniaj kluczy API, danych innych użytkowników, wewnętrznych ID bazy.
```

### `docs/ASSISTANT_CONTEXT.md` (nowy plik, ~2-3 KB, ręcznie kurowany)

Nie kopia `ARCHITECTURE.md` (za długa, za techniczna) — skrócony "ściągawka" pisana pod kątem *pytań użytkownika końcowego* o samą aplikację, np.:
- Co to jest FSRS i dlaczego karta "wraca" za X dni.
- Co to jest "successive relearning" (dlaczego fiszka nie znika po 1 dobrej odpowiedzi).
- Skąd się bierze XP i poziom.
- Co robią poszczególne ekrany (Lekcja dnia, Fiszki, Bank ćwiczeń, Rozmowa, Newsy, QuickMode).
- Różnica między lekcją a testem dnia.

Ten plik jest **osobny od `ARCHITECTURE.md`** (który jest dla deweloperów) — asystent nie powinien tłumaczyć userowi routerów FastAPI. Utrzymanie: aktualizowany ręcznie przy większych zmianach UX (rzadko, nie przy każdym commit).

### Dynamiczny kontekst runtime (nie RAG, proste query do DB)

Doklejany per-request, analogicznie do już istniejącego `ask_question`:
- `cefr_level`, `target_language`, `native_language` z `User` (już robi to `conversation.py:359-364`).
- Opcjonalnie: nazwa bieżącej lekcji/tematu jeśli `route` zaczyna się od `/lesson` (1 dodatkowe query, tylko gdy potrzebne — nie ładować całej historii usera).

---

## 4. D-3: Model i koszt

### Rejestr modeli — rozszerzenie `model_router.py`

Nowy task `"assistant"` dopisany do `USED_TASKS` i do map `MAPPINGS` wszystkich tierów:

```python
"free":  {..., "assistant": "openai/gpt-oss-20b:free"},
"cheap": {..., "assistant": "google/gemini-2.5-flash-lite"},
"best":  {..., "assistant": "openai/gpt-5-mini"},
```

I **domyślny cap**:
```python
TASK_TIER_CAP = {
    "news": "cheap",
    "assistant": "free",   # NOWE — zgodnie z zasadą "wyłącznie darmowe źródła"
}
```

Efekt: nawet jeśli właściciel ustawi globalnie `AI_MODEL_TIER=best` (bo np. chce `best` dla lekcji), asystent i tak zostaje na `free`, dopóki nie dostanie **jawnego** override (patrz niżej). To lustrzane odbicie istniejącego mechanizmu `TASK_TIER_FLOOR` dla `lesson` (patrz `model_router.py:78-93`) — ten sam wzorzec, przeciwny kierunek.

### Wyjątek (jeśli właściciel zaakceptuje)

Jeśli jakość darmowego modelu okaże się niewystarczająca (typowe ryzyko `:free` modeli: limity 20 req/min / 200 req/day, czasem słabsze podążanie za instrukcją), właściciel może:
- podnieść cap do `cheap` (`google/gemini-2.5-flash-lite` — bardzo tani), **decyzja jawna**, nie domyślna.
- Rekomendacja architekta: **zacząć od `free`**, zmierzyć jakość na realnych pytaniach pilotażu, dopiero potem rozważać `cheap`. Koszt `cheap` na tym wolumenie (1 user, sporadyczne pytania) byłby i tak marginalny, ale zasada kosztów mówi zacząć od darmowego.

### Limity i odporność

- Free-tier ma **globalny** limit 200 req/dzień na cały OpenRouter dla tego klucza (współdzielony z innymi taskami: placement/lesson/conversation/test/news jeśli globalny tier też jest `free`). Przy pilotażu na 1 użytkowniku ryzyko wyczerpania jest niskie, ale warto to **zmierzyć**, nie zakładać.
- Zachować wzorzec `generate_json(prompt, fallback=...)` / `generate_text(prompt)` z gracefully degradation — przy błędzie AI asystent zwraca jasny komunikat ("Asystent jest chwilowo niedostępny, spróbuj ponownie"), nigdy nie wywraca UI.
- Rate-limit AI middleware (30 req/60s/IP, `§12 ARCHITECTURE.md`) już obejmuje wszystkie `/api/*` — nowy endpoint automatycznie pod tą ochroną, zero dodatkowej pracy.

---

## 5. D-4: Wzorzec do powielenia w innych projektach

### Dlaczego nie wspólna biblioteka

Moduły ekosystemu (LinguaAI, ForgeBody, HackerLabAcademy, memory-forge, ...) to **osobne repozytoria, osobne porty, osobne wdrożenia** (patrz rejestr portów `spec-architekt`). Nie ma dziś współdzielonego pakietu Python między nimi — każdy ma własny `gemini_service.py` i `model_router.py` **celowo zduplikowane** (to nie narusza zasady #1 spec-architekt, bo ta zasada dotyczy *funkcji domenowych* uczenia, nie infrastruktury AI, która z natury żyje przy każdym serwisie). Budowa wspólnej biblioteki AI w tym momencie byłaby przedwczesnym uogólnieniem — wymagałaby wydzielonego pakietu, wersjonowania, publikacji (PyPI prywatny/git submodule), co jest kosztem nieproporcjonalnym do 1 pilotażu.

### Rekomendacja: udokumentowana "recepta" (5 elementów o stałym kształcie)

Każdy projekt, który dostanie asystenta, powtarza dokładnie te same 5 elementów (nazwy plików mogą się różnić, kontrakt — nie):

1. **`docs/ASSISTANT_CONTEXT.md`** — krótki cheat sheet domenowy (2-3 KB), pisany pod użytkownika końcowego.
2. **`backend/services/assistant_service.py`** — jedna funkcja `answer_assistant_question(question, page_context, user_context) -> str`, wołająca istniejący `gemini_service.generate_text` z `@with_model("assistant")`.
3. **`backend/routers/assistant.py`** — `POST /api/assistant/ask`, schemat request/response identyczny między projektami:
   ```json
   // request
   {"user_id": int, "question": str, "route": str,
    "element_context": {...} | null, "selected_text": str | null}
   // response
   {"success": true, "answer": str}
   ```
4. **`frontend/src/components/AssistantWidget.jsx`** — floating widget (wzorzec `TranslatorWidget` w `Layout.jsx`) + tryb "wskaż element" (§2), kopiowany 1:1 między projektami (ten sam JS, różni się tylko tekstami UI jeśli projekt nie jest polski).
5. **Wpis w `model_router.py`** projektu: task `"assistant"`, cap `"free"` domyślnie (§4).

### ADR

Jeśli właściciel zaakceptuje ten spec, powstanie krótki ADR (`docs/adr/000X-asystent-ai-wzorzec.md` lub odpowiednik per-projekt) opisujący dokładnie te 5 punktów jako "kontrakt do powielenia" — analogicznie do tego, jak `spec-architekt` dziś traktuje rejestr portów jako źródło prawdy. To odpowiada wymogowi zlecenia punkt 4 ("wzorzec do powielenia, nie rozwiązanie jednorazowe").

---

## 6. Otwarte decyzje dla właściciela (wymagane PRZED implementacją)

1. **Zatwierdzenie D-1..D-4** powyżej (lub korekta).
2. **Nazwa/ścieżka endpointu**: `/api/assistant/ask` — kolizji nazw brak (sprawdzone: `search_files` po `assistant|RAG|chatbot` w repo nie znalazł istniejącego mechanizmu tego typu, jedyny pokrewny to `/api/conversation/question` — inny cel, patrz §1).
3. **Czy dopuszczamy `cheap` jako świadomy wyjątek** od razu, czy startujemy wyłącznie na `free` i eskalujemy dopiero po zmierzonej niewystarczającej jakości (rekomendacja: to drugie).
4. **Zakres pilotażu**: czy asystent ma być widoczny na wszystkich stronach LinguaAI od startu, czy najpierw na 1-2 ekranach (np. Lekcja dnia + Fiszki) do walidacji UX trybu wskazywania, potem reszta.
5. **Język odpowiedzi**: zawsze polski (UI jest polski), niezależnie od `target_language` usera — do potwierdzenia, że to oczywiste założenie jest poprawne.

Po odpowiedzi właściciela na powyższe punkty spec przechodzi do implementacji jako osobna karta Kanban (assignee: koder/frontend-koder), rozbita na: (a) backend endpoint + model_router, (b) frontend widget + tryb wskazywania, (c) `ASSISTANT_CONTEXT.md`, (d) testy. **Ta karta (`t_316245ca`) kończy się na tym dokumencie — implementacja to świadomie osobny krok**, zgodnie z trybem SPEC zlecenia.
