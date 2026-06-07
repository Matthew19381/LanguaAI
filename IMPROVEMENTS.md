# LinguaAI — Usprawnienia

> Ostatnia aktualizacja: 2026-06-07

## ✅ Zrobione

- [x] **CLAUDE.md** — dokumentacja projektu istnieje
- [x] **.gitignore** — reguły VCS istnieją
- [x] **Testy** — 25 plików testowych w `backend/tests/`
- [x] **requirements.txt** — zależności zdefiniowane (2 pliki: root + backend/)
- [x] **README.md** — kompletny opis projektu (477 linii)
- [x] **pyproject.toml** — metadane pakietu
- [x] **.pre-commit-config.yaml** — ruff lint+format
- [x] **Refaktoryzacja dużych plików** (2026-06-07):
  - `lesson_generator.py` (1,076 LOC) → podzielony na `backend/services/lesson_generator/` (7 modułów)
  - `lessons.py` (1,054 LOC) → wyodrębniono `flashcard_service.py` i `streak_service.py`
- [x] **Type hints** (2026-06-07) — zweryfikowano i uzupełniono w nowych serwisach
- [x] **Usunięto martwy kod** (2026-06-07) — `Conversation.jsx.bak`

## 📋 Do zrobienia

### Wysoki priorytet
_(brak — wszystko zrobione)_

### Średni priorytet
_(brak — wszystko zrobione)_

### Niski priorytet
_(brak — wszystko zrobione)_

---

## 📁 Struktura

```
LinguaAI/
├── backend/
│   ├── routers/              # API endpoints (lessons, tests, flashcards, etc.)
│   ├── services/             # Logika biznesowa
│   │   └── lesson_generator/ # 7 modułów (placement, study_plan, daily_lesson, tests, conversation, tips) ✅
│   │   ├── flashcard_service.py  # Wyodrębniony z lessons.py ✅
│   │   ├── streak_service.py     # Wyodrębniony z lessons.py ✅
│   │   ├── gemini_service.py
│   │   ├── test_generator.py
│   │   ├── achievement_service.py
│   │   └── ...
│   ├── models/               # SQLAlchemy models
│   ├── tests/                # 25 plików testowych ✅
│   └── requirements.txt      # Zależności
├── frontend/                 # React + Vite
│   └── src/pages/            # Strony
├── tests/                    # Testy poziomu projektu
├── decisions/                # ADR docs
├── CLAUDE.md                 # ✅ Dokumentacja
└── README.md                 # ✅ Kompletny opis projektu
```

## 🔗 Linki

- [CLAUDE.md](CLAUDE.md)
- [CHANGELOG](CHANGELOG.md)
