# LinguaAI — AI-Powered Language Learning App

Aplikacja do nauki języków obcych wspierana przez AI. Interfejs w języku polskim. Uczy się z Tobą — dostosowuje poziom, generuje lekcje, analizuje błędy i motywuje systemem osiągnięć.

## Szybki start

1. Sklonuj repozytorium
2. Skopiuj `backend/.env.example` → `backend/.env` i uzupełnij klucze API
3. Uruchom:
   - Backend: `uvicorn backend.main:app --reload --port 8001` (z katalogu głównego)
   - Frontend: `cd frontend && npm install && npm run dev`
4. Otwórz http://localhost:5173

## Dokumentacja

- [TASKS.md](TASKS.md) — lista zadań i backlog
- [docs/NEURO_FEATURES.md](docs/NEURO_FEATURES.md) — funkcje neuronaukowe (Faza 2)
- [docs/](docs/) — szczegółowa dokumentacja (wdrożenie, API, architektura itp.)
- [CHANGELOG.md](CHANGELOG.md) — historia zmian

## Tech Stack

**Backend**: FastAPI, SQLAlchemy (SQLite), FSRS v6, edge-tts, faster-whisper, fpdf2, feedparser, genanki  
**Frontend**: React 19, React Router v7, Axios, Tailwind CSS, Vite, lucide-react  
**AI**: Google Gemini 2.0 Flash (lub OpenRouter)  

## Kluczowe funkcje

- Test poziomujący CEFR (20 pytań)
- Codzienne lekcje z AI (słownictwo, gramatyka, i+1 input, przeplatanie, wymuszona produkcja)
- System fiszek z FSRS v6 (z rozszerzeniami neuronaukowymi: modulacja snu, pora dnia, interleaving, interferencja)
- Konwersacja z AI (tekst/glos)
- Analiza wymowy (word-level scoring)
- Czytanie nieuprzedzonych artykułów (RSS + AI upraszczanie)
- System punktów (XP) i poziomów (50 poziomów, kwadratowa krzywa)
- 57+ osiągnięć (w tym neuronaukowe: świadomy sen, przeplatanie, gestualna kotwica)
- Tryb szybki (5-120 min) z niezależnym timerem
- Eksport do Anki, PDF, audio TTS
- Kopie zapasowe (lokalne i Google Drive)

## Wdrożenie Docker

Zobacz [docs/deployment.md](docs/deployment.md) dla pełnych instrukcji.

```
docker-compose up --build
```

Backend: http://localhost:8001  
Frontend: http://localhost:5173  
API Docs: http://localhost:8001/docs

## Testy

```bash
# Backend
py -3.11 -m pytest backend/tests/ -v

# Frontend (Playwright/CSC) - TODO
```

## Licencja

MIT