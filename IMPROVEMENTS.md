# LinguaAI — Usprawnienia

> Ostatnia aktualizacja: 2026-06-07

## ✅ Zrobione

- [x] **CLAUDE.md** — dokumentacja projektu istnieje
- [x] **.gitignore** — reguły VCS istnieją
- [x] **Testy** — 25 plików testowych w `backend/tests/`
- [x] **requirements.txt** — zależności zdefiniowane (2 pliki: root + backend/)

## 📋 Do zrobienia

### Wysoki priorytet
- [ ] **Refaktoryzacja dużych plików**:
  - `backend/services/lesson_generator.py` (1,076 LOC) — podziel na mniejsze moduły
  - `backend/routers/lessons.py` (1,054 LOC) — wyodrębnij logikę do serwisów
- [ ] **Dodaj pyproject.toml** — brak metadanych pakietu
- [ ] **Dodaj .pre-commit-config.yaml** — ruff lint+format, trailing whitespace

### Średni priorytet
- [ ] **Uzupełnij type hints** — niekonsekwentne typowanie:
  - `lesson_generator.py` — typy zwrotne OK, brak parametrów
  - `lessons.py` — częściowe typowanie
  - Modele SQLAlchemy — brak Python type hints (tylko Column)
- [ ] **Usuń martwy kod** — `frontend/src/pages/Conversation.jsx.bak`

### Niski priorytet
- [ ] **Dodaj README.md** — opis projektu, stack, quick start

---

## 📁 Struktura

```
LinguaAI/
├── backend/
│   ├── routers/              # API endpoints (lessons, tests, flashcards, etc.)
│   ├── services/             # Logika biznesowa
│   │   └── lesson_generator.py  # 1,076 LOC — DO REFAKTORYZACJI
│   ├── models/               # SQLAlchemy models
│   ├── tests/                # 25 plików testowych ✅
│   └── requirements.txt      # Zależności
├── frontend/                 # React + Vite
│   └── src/pages/            # Strony (Conversation.jsx.bak do usunięcia)
├── tests/                    # Testy poziomu projektu
├── decisions/                # ADR docs
└── CLAUDE.md                 # ✅ Dokumentacja
```

## 🔗 Linki

- [CLAUDE.md](CLAUDE.md)
- [CHANGELOG](CHANGELOG.md)
