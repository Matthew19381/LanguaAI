# Przewodnik Wdrożeniowy LinguaAI

Kompletny przewodnik wdrażania platformy LinguaAI w środowisku produkcyjnym.

## Spis treści

- [Przegląd](#przegląd)
- [Wymagania systemowe](#wymagania-systemowe)
- [Przygotowanie serwera](#przygotowanie-serwera)
- [Wdrożenie Backendu](#wdrożenie-backendu)
- [Wdrożenie Frontendu](#wdrożenie-frontendu)
- [Konfiguracja Nginx](#konfiguracja-nginx)
- [SSL/TLS (HTTPS)](#ssltls-https)
- [Baza danych](#baza-danych)
- [Monitorowanie i logi](#monitorowanie-i-logi)
- [Backup i przywracanie](#backup-i-przywracanie)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

## Przegląd

LinguaAI składa się z dwóch głównych komponentów:
- **Backend**: FastAPI + Uvicorn (port 8001)
- **Frontend**: React + Vite (build statyczny serwowany przez Nginx)

Architektura wdrożeniowa:
```
Internet → Nginx (443) → Frontend (static) + Proxy /api → Backend (8001)
```

## Wymagania systemowe

### Minimalna konfiguracja serwera
- **CPU**: 2 cores
- **RAM**: 2 GB
- **Dysk**: 10 GB SSD
- **OS**: Ubuntu 22.04 LTS / Debian 11+

### Wymagane oprogramowanie
- Python 3.10+
- Node.js 18+ (tylko do buildowania frontendu)
- Nginx 1.18+
- Certbot (Let's Encrypt)
- SQLite3 (lub PostgreSQL)

## Przygotowanie serwera

```bash
# Aktualizacja systemu
sudo apt update && sudo apt upgrade -y

# Instalacja podstawowych pakietów
sudo apt install -y python3.10 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Utworzenie użytkownika aplikacji
sudo useradd -m -s /bin/bash linguaai
sudo mkdir -p /opt/linguaai
sudo chown linguaai:linguaai /opt/linguaai
```

## Wdrożenie Backendu

### 1. Klonowanie repozytorium

```bash
sudo -u linguaai git clone https://github.com/Matthew19381/LanguaAI.git /opt/linguaai/app
cd /opt/linguaai/app
```

### 2. Konfiguracja środowiska Python

```bash
cd /opt/linguaai/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Konfiguracja zmiennych środowiskowych

Utwórz plik `/opt/linguaai/app/backend/.env`:

```env
OPENROUTER_API_KEY=«redacted:sk-…»
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./lingua_ai.db
APP_ACCESS_TOKEN=<wygenerowany_sekret>
```

**⚠️ KRYTYCZNE — bramka dostępu:** przed wystawieniem aplikacji do internetu
**musi** być ustawiony `APP_ACCESS_TOKEN` (losowy sekret, min. 32 znaki). Bez
niego każdy, kto zna adres, może czytać/zmieniać dane użytkownika i palić
Twoje kredyty OpenRouter. Wygeneruj:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Bramka wymaga jednorazowego odblokowania na każdym urządzeniu (ekran
"Aplikacja zablokowana" → wklejenie tokenu). Lokalny localhost bez tokenu
działa bez zmian (bramka wyłączona gdy zmienna pusta).

### 4. Inicjalizacja bazy danych

```bash
cd /opt/linguaai/app
source venv/bin/activate
python -c "from backend.main import app; print('DB initialized')"
```

### 5. Konfiguracja systemd service

Utwórz plik `/etc/systemd/system/linguaai-backend.service`:

```ini
[Unit]
Description=LinguaAI Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=linguaai
Group=linguaai
WorkingDirectory=/opt/linguaai/app
Environment="PATH=/opt/linguaai/app/venv/bin"
ExecStart=/opt/linguaai/app/venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Uruchom service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable linguaai-backend
sudo systemctl start linguaai-backend
sudo systemctl status linguaai-backend
```

### 6. Sprawdzenie backendu

```bash
curl http://localhost:8001/docs
```

## Wdrożenie Frontendu

### 1. Build statyczny

```bash
cd /opt/linguaai/app/frontend
npm install
npm run build
```

Pliki trafią do `frontend/dist/`.

### 2. Konfiguracja API URL (opcjonalnie)

Jeśli frontend komunikuje się z backendem przez inny URL niż `/api`, utwórz plik `.env` w katalogu `frontend/`:

```env
VITE_API_URL=https://api.twoja-domena.pl
```

Następnie przebuduj: `npm run build`.

## Konfiguracja Nginx

Utwórz plik `/etc/nginx/sites-available/linguaai`:

```nginx
server {
    listen 80;
    server_name twoja-domena.pl www.twoja-domena.pl;

    # Frontend (static files)
    location / {
        root /opt/linguaai/app/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Audio files proxy
    location /audio/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

Aktywuj konfigurację:

```bash
sudo ln -s /etc/nginx/sites-available/linguaai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS (HTTPS)

### Certbot (Let's Encrypt)

```bash
sudo certbot --nginx -d twoja-domena.pl -d www.twoja-domena.pl
```

Certbot automatycznie zmodyfikuje konfigurację Nginx i doda przekierowanie HTTP → HTTPS.

### Automatyczne odnawianie

```bash
sudo systemctl status certbot.timer
# Powinien być aktywny domyślnie
```

## Baza danych

### SQLite (domyślna)

Dla małych instalacji (do ~1000 użytkowników):

```bash
# Lokalizacja pliku
ls -la /opt/linguaai/app/lingua_ai.db

# Backup
cp /opt/linguaai/app/lingua_ai.db /opt/linguaai/backups/lingua_ai_$(date +%Y%m%d).db
```

### Migracja do PostgreSQL (dla skali)

1. Zainstaluj PostgreSQL:
```bash
sudo apt install -y postgresql postgresql-contrib
```

2. Utwórz bazę i użytkownika:
```bash
sudo -u postgres psql
CREATE DATABASE linguaai;
CREATE USER linguaai_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE linguaai TO linguaai_user;
\q
```

3. Zmień `DATABASE_URL` w `backend/.env`:
```env
DATABASE_URL=postgresql://linguaai_user:strong_password@localhost:5432/linguaai
```

4. Zrestartuj backend:
```bash
sudo systemctl restart linguaai-backend
```

## Monitorowanie i logi

### Logi systemd (backend)

```bash
# Podgląd logów w czasie rzeczywistym
sudo journalctl -u linguaai-backend -f

# Ostatnie 100 linii
sudo journalctl -u linguaai-backend -n 100
```

### Logi Nginx

```bash
# Access log
tail -f /var/log/nginx/access.log

# Error log
tail -f /var/log/nginx/error.log
```

### Monitorowanie zasobów

```bash
# Status serwisu
sudo systemctl status linguaai-backend

# Użycie CPU/RAM przez procesy Python
ps aux | grep uvicorn

# Użycie dysku
df -h
```

## Backup i przywracanie

### Skrypt backupu

Utwórz `/opt/linguaai/scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/linguaai/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/linguaai/app"

mkdir -p "$BACKUP_DIR"

# Backup bazy danych
if [ -f "$APP_DIR/lingua_ai.db" ]; then
    cp "$APP_DIR/lingua_ai.db" "$BACKUP_DIR/lingua_ai_$DATE.db"
    echo "Database backed up: lingua_ai_$DATE.db"
fi

# Backup .env
cp "$APP_DIR/backend/.env" "$BACKUP_DIR/env_$DATE.bak"

# Usuń backupy starsze niż 30 dni
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Nadaj uprawnienia i dodaj do crona:

```bash
chmod +x /opt/linguaai/scripts/backup.sh

# Cron (codziennie o 2:00 w nocy)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/linguaai/scripts/backup.sh >> /opt/linguaai/logs/backup.log 2>&1") | crontab -
```

### Przywracanie bazy danych

```bash
# Zatrzymaj backend
sudo systemctl stop linguaai-backend

# Przywróć backup
cp /opt/linguaai/backups/lingua_ai_20260508_020000.db /opt/linguaai/app/lingua_ai.db

# Uruchom backend
sudo systemctl start linguaai-backend
```

## Docker

W repozytorium znajdują się:
- `Dockerfile.backend` — obraz backendu (Python 3.14 + FastAPI)
- `Dockerfile.frontend` — obraz frontendu (Node 18 build + nginx production)
- `docker-compose.yml` — produkcjna konfiguracja (backend + frontend)
- `docker-compose.dev.yml` — deweloperska konfiguracja (hot-reload)

```bash
# Produkcja
docker-compose up -d

# Development (hot-reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Backup — Windows Task Scheduler

Na Windows backup można zautomatyzować przez Task Scheduler:

```powershell
# Rejestracja codziennego backupu o 2:00 AM
powershell -ExecutionPolicy Bypass -File scripts\register-backup-task.ps1

# Usunięcie zaplanowanego backupu
powershell -ExecutionPolicy Bypass -File scripts\register-backup-task.ps1 -Remove
```

Backup jest przechowywany w `backups/` z retencją 7 dni.

## Rozwiązywanie problemów

### Backend nie startuje

```bash
# Sprawdź logi
sudo journalctl -u linguaai-backend -n 50

# Sprawdź czy port 8001 jest wolny
sudo lsof -i :8001

# Sprawdź zmienne środowiskowe
cat /opt/linguaai/app/backend/.env
```

### Frontend nie ładuje się / błędy API

1. Sprawdź czy Nginx proxy działa:
```bash
curl http://localhost/api/placement/
```

2. Sprawdź CORS w `backend/main.py` — czy domena jest na whitelist?

3. Sprawdź w przeglądarce (F12 → Network) czy requesty do `/api/` trafiają na właściwy adres.

### Błędy 502 Bad Gateway

```bash
# Sprawdź czy backend działa
sudo systemctl status linguaai-backend

# Sprawdź czy Nginx może połączyć się z backendem
curl http://127.0.0.1:8001/docs
```

### Problemy z Gemini API

```bash
# Test połączenia z API
cd /opt/linguaai/app
source venv/bin/activate
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('OK')"
```

### Brak audio (TTS)

Upewnij się, że `edge-tts` działa na serwerze (wymaga dostępu do internetu):

```bash
source /opt/linguaai/app/venv/bin/activate
python -c "import edge_tts; print('edge-tts OK')"
```
