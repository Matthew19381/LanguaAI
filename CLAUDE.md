# LinguaAI

Nauka języka (niemiecki) z lekcjami AI, fiszkami FSRS, rozmową i wymową. Moduł ekosystemu System-Główny.

## Najpierw mapa, nie dokumenty
- Porty, uruchamianie, API, zależności: `C:\Projects\KB\mapa\INDEX.md` (w chmurze: repo `Matthew19381/KB`, katalog `mapa/`);
  ten moduł: `mapa/moduly/LinguaAI.md`. Czytaj tylko potrzebną sekcję.
- Architektura (routery, serwisy, model danych): `docs/ARCHITECTURE.md` (wygrywa przy rozbieżności).
- `TASKS.md` ma 138 KB: czytaj fragmentami (najnowsze na górze), nie w całości.
- Pełna dawna wersja tego pliku: `docs/archiwum/CLAUDE-do-2026-11-06.md`.

## Zasady (Mateusz)
- Usługi uruchamiaj tylko przez `Start-ScheduledTask -TaskName Ekosystem-Start`.
- Push i scalanie tylko po zgodzie Mateusza (dawna reguła „push po każdej zmianie” nie obowiązuje).
- Repo jest **publiczne**: przed push skan sekretów. Nie zmieniaj plików `.env`.

## Pułapki
- Backend uruchamiaj z **korzenia repo** (`backend.main:app`), nigdy z `backend/` (importy `backend.*`).
- Schemat tylko przez Alembic, zero ręcznych `ALTER TABLE`. Zmiana modelu w `backend/models/*.py` w jednym commicie z rewizją:
  z korzenia `.venv\Scripts\python.exe -m alembic -c backend/alembic.ini revision --autogenerate -m "opis"` (dawny zapis: `py -3.11 -m alembic ...`); przejrzyj rewizję (SQLite autogenerate bywa
  niedokładny, przykłady w `backend/alembic/README`). Nowy model: import w `backend/alembic/env.py`. Start robi `upgrade head` (pomijane przy `TESTING=1`).
- Baza `lingua_ai.db` jest w korzeniu repo; względny `DATABASE_URL` liczy się od repo, nie od cwd.
- AI tylko przez `backend/services/gemini_service.py` (`generate_json`, `generate_text`); model wybiera `services/model_router.py`
  (`@with_model("<zadanie>")`, `AI_MODEL_TIER`) — nigdy nie wpisuj id modelu. `generate_json` zwraca fallback tylko, gdy wywołujący go podał; inaczej `ValueError`.
- `Lesson.content` to JSON: nowe sekcje lekcji bez migracji, frontend sprawdza ich obecność.
- Frontend: wszystkie wywołania w `frontend/src/api/client.js` (interceptor zwraca `response.data`; wyjątki: eksport PDF i wymowa przez surowy axios).
  Routery mają pełne ścieżki `/api/...`, wyjątek `users` pod `/api/v1/users`.
- Nowy router: import i `include_router` w `main.py`, tabela w `docs/ARCHITECTURE.md §6`.

## Konwencje
Commity `<typ>: co i dlaczego` z listą plików; typy feat, fix, refactor, style, docs, chore.
Nie trafiają do git: `backend/.env`, `*.db`, `backend/audio/`, `backend/exports/`, `frontend/dist/`.
