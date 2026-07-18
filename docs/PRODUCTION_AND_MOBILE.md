# Production Readiness & Mobile Support

This document consolidates the steps needed to:

1. Fix the current development blocker (missing `isImportant` column).
2. Prepare the application for a cloud‑hosted production deployment.
3. Enable a solid mobile experience (PWA → optional native wrapper).

---

## 1. Immediate Fix – Missing `isImportant` column

**Problem**  
On startup the backend tries to read `flashcards.isImportant` which does not exist in the local SQLite DB, causing an `OperationalError`.

**Solution** – Add the column automatically on start‑up (dev) and via a migration script (prod).

### 1.1 Migration script (SQL)

Create the SQL
-- Add the missing Boolean column with a safe default
ALTER TABLE flashcards
ADD COLUMN isImportant BOOLEAN NOT NULL DEFAULT 0;
```
### 1.2 Auto‑apply on start‑up (SQLite dev)

Edit `backend/main.py` inside the `lifespan` async context manager, after `Base.metadata.create_all(bind=engine)`:

```python
from sqlalchemy import text

if settings.DATABASE_URL.startswith("sqlite"):
    with engine.connect() as conn:
        # Idempotent: SQLite will ignore if column already exists (depends on version)
        # Using IF NOT EXISTS syntax is not universally supported, so we try/catch.
        try:
            conn.execute(text(
                """
                ALTER TABLE flashcards
                ADD COLUMN isImportant BOOLEAN NOT NULL DEFAULT 0
                """
            ))
            conn.commit()
        except Exception:
            # Column probably already exists – ignore
            pass
```

*For production (PostgreSQL/MySQL) rely on the migration tool (see section 2).*

### 1.3 Verify

Restart the dev server, then:

```bash
curl -s http://localhost:8001/api/flashcards/1 | jq .
```

You should see `"isImportant": false` (or `true` if you set it manually).

---

## 2. Cloud‑Ready Deployment Plan

The goal is to run the same Docker images against a managed PostgreSQL (or similar) database, with automated schema migrations, CI/CD, observability, and secret management.

### 2.1 Externalise the Database

* Replace the hard‑coded SQLite file with a connection string supplied via `DATABASE_URL`.
* In `backend/config.py` (or wherever settings are read this variable using `pydantic.BaseSettings` or `python-dotenv`.
* Ensure the Dockerfile **does not** copy a local `lingua_ai.db`; the container starts with an empty volume and expects the DB to be reachable via the env var.

### 2.2 Adopt Alembic for Schema Migrations

1. Install: `pip install alembic`.
2. Initialise: `alembic init alembic` (inside `backend/`).
3. Edit `alembic.ini`:
   ```
   sqlalchemy.url = driver://user:pass@host/dbname   # will be overridden at runtime
   ```
   In `env.py` replace the hardcoded URL with:
   ```python
   from backend.config import settings
   config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
   ```
4. Generate the base revision:
   ```bash
   alembic revision --autogenerate -m "initial"
   ```
   Verify that the generated migration contains the `isImportant` column (and any other model changes).
5. Add migration execution to the container start‑up script (`start.sh` or the `CMD` in Dockerfile):

   ```bash
   #!/usr/bin/env sh
   # Wait for DB to be reachable (optional, using pg_isready or a simple loop)
   until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
     echo "Waiting for database..."
     sleep 2
   done

   # Apply migrations
   alembic upgrade head

   # Start the app
   exec uvicorn backend.main:app --host 0.0.0.0 --port 8001
   ```

   Ensure the script is executable and set as `ENTRYPOINT`.

### 2.3 CI/CD Pipeline (GitHub Actions example)

Create `.github/workflows/deploy.yml`:

```yaml
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: "20"
      - name: Install backend deps
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run backend tests
        run: |
          cd backend
          pytest -v
      - name: Install frontend deps
        run: cd frontend && npm ci
      - name: Run frontend tests (if any)
        run: cd frontend && npm test
      - name: Build Docker images
        run: |
          docker build -t ${{ secrets.REGISTRY }}/linguaai-backend:${{ github.sha }} -f Dockerfile.backend .
          docker build -t ${{ secrets.REGISTRY }}/linguaai-frontend:${{ github.sha }} -f Dockerfile.frontend .
      - name: Push images
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login ${{ secrets.REGISTRY }} -u ${{ secrets.REGISTRY_USERNAME }} --password-stdin
          docker push ${{ secrets.REGISTRY }}/linguaai-backend:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/linguaai-frontend:${{ github.sha }}

  deploy:
    needs: build-test
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to Cloud (example for AWS ECS/Fargate)
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Update ECS service with new image
        run: |
          aws ecs update-service \
            --cluster linguaai-cluster \
            --service linguaai-service \
            --force-new-deployment \
            --image ${{ secrets.REGISTRY }}/linguaai-backend:${{ github.sha }}
```

Adjust the deploy step for your target platform (Cloud Run, Azure Container Apps, etc.).

### 2.4 Observability & Logging

* **Logs** – Let the container write to `stdout/stderr`; the orchestrator will forward them to the provider’s logging service (CloudWatch, Stackdriver, Azure Monitor).
* **Metrics** – Add a simple `/metrics` endpoint (Prometheus) using `prometheus_fastapi_instrumentator` if you desire scraped metrics.
* **Alerts** – Configure CPU/Memory usage, latency, and error‑rate alerts in your cloud monitoring tool.

### 2.5 Secrets Management

Never bake keys into the image. Use the cloud provider’s secret store:

| Provider | Service |
|----------|---------|
| AWS | Secrets Manager or Parameter Store |
| GCP | Secret Manager |
| Azure | Key Vault |

In your CI/CD pipeline or startup script, retrieve the secret and export it as an environment variable before launching the container.

### 2.6 Zero‑Downtime Deployments

* **ECS/Fargate** – Use a rolling update (`deploymentConfiguration: maximumPercent=200, minimumHealthyPercent=100`).
* **Cloud Run** – Deploy a new revision; traffic is shifted gradually; you can manually allocate 100% to the new revision after health checks pass.
* **Kubernetes** – Use a Deployment with `strategy.type: RollingUpdate`.

---

## 3. Mobile / PWA — STAN: ZAIMPLEMENTOWANE (2026-07-18)

> Sekcje 3.1–3.4 poniżej to oryginalny plan. Poniższa ramka opisuje, co **faktycznie działa** w repo.

### Co jest gotowe

| Element | Stan | Gdzie |
|---|---|---|
| `vite-plugin-pwa` + service worker | ✅ | `frontend/vite.config.js` |
| Manifest (standalone, ikony 192/512 + maskable, skróty) | ✅ | generowany do `dist/manifest.webmanifest` |
| Ikony PNG (192/512, maskable, apple-touch-icon) | ✅ | `frontend/public/icons/` |
| Meta iOS (apple-touch-icon, standalone, theme-color) | ✅ | `frontend/index.html` |
| Cache offline: ćwiczenia, lekcje, fiszki, staty, audio | ✅ | `workbox.runtimeCaching` |
| Baner „jesteś offline" | ✅ | `frontend/src/components/OfflineBanner.jsx` |
| Web Push (VAPID) | ❌ nie zrobione | patrz 3.2 |
| Capacitor / sklepy | ❌ niepotrzebne dziś | patrz 3.3 |

**Zweryfikowane na żywo:** po zatrzymaniu backendu `GET /api/exercises/{id}/practice`
nadal zwraca 200 z cache i strona `/practice` renderuje komplet zadań.

### ⚠️ Ograniczenie: offline działa do *odczytu*

Service worker cache'uje odpowiedzi GET. **Zapis wymaga sieci** — odpowiadanie na
ćwiczenia (`POST /answer`), kończenie lekcji, generowanie treści. Offline zobaczysz
materiał, ale postęp się nie zapisze. Kolejkowanie zapisów (Background Sync) to
osobne zadanie w `TASKS.md`.

### 🔒 ZANIM cokolwiek wystawisz na internet

Poza `/api/admin/*` **żaden endpoint nie ma uwierzytelnienia** — dostęp to
podanie `user_id` w parametrze. Wystawienie API bez ochrony oznacza, że każdy,
kto pozna adres, może czytać i zmieniać Twoje dane oraz **wywoływać endpointy AI
na Twój koszt** (Twój klucz OpenRouter).

Dlatego jest bramka dostępu — jeden wspólny sekret:

1. Wygeneruj token i wpisz go do `backend/.env`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # APP_ACCESS_TOKEN=<wynik>
   ```
2. Zrestartuj backend. Od tej chwili każde żądanie do `/api/*` i `/audio/*` bez
   sekretu dostaje **401**. Otwarte zostaje tylko `/api/health` (do sond) oraz
   `/api/auth/*` (żeby dało się odblokować).
3. W przeglądarce zobaczysz ekran „Aplikacja zablokowana". Wpisujesz token **raz
   na urządzenie** — backend wymienia go na ciasteczko HttpOnly (JavaScript nigdy
   go nie trzyma, a pliki `/audio/*` też się autoryzują).

Pusty `APP_ACCESS_TOKEN` = bramka wyłączona, czyli praca na localhoście bez zmian.

### Tunel HTTPS — test na telefonie bez wdrożenia

Service worker i instalacja PWA wymagają HTTPS, więc `http://<ip>:5173` nie
wystarczy. Najszybsza droga to tunel:

```bash
winget install --id Cloudflare.cloudflared

# 1. backend z bramką (APP_ACCESS_TOKEN ustawiony w backend/.env)
uvicorn backend.main:app --host 0.0.0.0 --port 8001

# 2. frontend (produkcyjny build serwuje też SW)
cd frontend && npm run build && npm run preview   # :4173

# 3. tunel na frontend — proxy przekazuje /api i /audio do backendu
cloudflared tunnel --url http://localhost:4173
```

`cloudflared` wypisze adres `https://<losowy>.trycloudflare.com` — otwórz go na
telefonie, odblokuj tokenem i dodaj do ekranu głównego.

**Pamiętaj:** adres quick tunnela jest losowy, ale publiczny. Bramka jest tym, co
Cię chroni — nie sam fakt, że adres jest trudny do zgadnięcia. Po teście zamknij
tunel (Ctrl+C).

### Jak ćwiczyć na telefonie — dziś, bez chmury

Telefon i komputer w tej samej sieci Wi-Fi:

1. **Backend na wszystkich interfejsach** (z katalogu głównego projektu):
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8001
   ```
2. **Frontend** — `host: true` jest już ustawione w `vite.config.js`:
   ```bash
   cd frontend && npm run dev        # albo: npm run build && npm run preview
   ```
3. **Adres IP komputera**: `ipconfig` → „IPv4 Address" (np. `192.168.0.12`).
4. Na telefonie otwórz `http://192.168.0.12:5173` (dev) lub `:4173` (preview).
5. **Zainstaluj**: Android/Chrome → menu → „Dodaj do ekranu głównego";
   iOS/Safari → Udostępnij → „Dodaj do ekranu głównego".

> **Uwaga o service workerze:** przeglądarki rejestrują SW tylko na HTTPS albo
> `localhost`. Pod adresem IP po HTTP (`http://192.168.0.12:5173`) aplikacja
> zadziała normalnie, ale **bez trybu offline i bez instalacji jako PWA**.
> Pełne PWA wymaga HTTPS — czyli wdrożenia w chmurze (sekcja 2) albo tunelu
> (np. `cloudflared tunnel`, ngrok), który daje adres HTTPS.

### Zapory (Windows)

Przy pierwszym uruchomieniu Windows zapyta o dostęp do sieci dla Pythona/Node —
trzeba zezwolić dla sieci **prywatnej**, inaczej telefon się nie połączy.

---

## 3-plan. Mobile / PWA Strategy (oryginalny plan)

The frontend already works as a SPA built in React + Vite and served as static files. It already behaves as a **Progressive Web App (PWA)** – users can “Add to Home Screen” on Android/iOS and receive an icon, full‑screen mode, and basic asset caching. To obtain a truly mobile‑friendly experience we recommend the following incremental steps.

### 3.1 Make it a Proper PWA

1. **Web App Manifest**  
   Ensure `public/manifest.json` exists (or generate via `vite-plugin-pwa`). Minimum fields:

   ```json
   {
     "name": "LinguaAI",
     "short_name": "Lingua",
     "start_url": "/",
     "display": "standalone",
     "background_color": "#ffffff",
     "theme_color": "#4f46e5",
     "icons": [
       { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
       { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
     ]
   }
   ```

2. **Service Worker**  
   Install `vite-plugin-pwa`:

   ```bash
   npm i -D vite-plugin-pwa
   ```

   Add to `vite.config.js`:

   ```js
   import { VitePWA } from 'vite-plugin-pwa';

   export default defineConfig({
     plugins: [
       react(),
       VitePWA({
         registerType: 'autoUpdate',
         workbox: {
           globPatterns: ['**/*.{js,css,html,svg,png,ico,json}'],
           runtimeCaching: [
             {
               urlPattern: ({url}) => url.startsWith('/api/lessons/'),
               handler: 'StaleWhileRevalidate',
               options: {
                 cacheName: 'lesson-cache',
                 expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 } // 1 day
               }
             },
             {
               urlPattern: ({url}) => url.startsWith('/api/flashcards/due'),
               handler: 'StaleWhileRevalidate',
               options: {
                 cacheName: 'flashcard-cache',
                 expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 12 } // 12h
               }
             }
           ]
         }
       })
     ]
   })
   ```

   Re‑build (`npm run build`) and serve; the browser will prompt “Install” on supported devices.

3. **Offline Fallback**  
   For routes that require API data (lesson, flashcards) the service‑worker will serve cached versions when the network is unavailable. Show a friendly “You’re offline – showing cached data” banner if needed.

### 3.2 Push Notifications (Web Push)

* Generate a VAPID key pair (`web-push generate-vapid-keys`).
* Store the **public** key in the frontend (e.g., `src/utils/vapidPublicKey.js`).
* After the user grants permission, subscribe via the PushManager and send the subscription to a new backend endpoint:

   ```ts
   // src/services/pushService.ts
   export async function registerForPush() {
     const registration = await navigator.serviceWorker.ready;
     const subscription = await registration.pushManager.subscribe({
       userVisibleOnly: true,
       applicationServerKey: urlBase64ToUint8Array('YOUR_PUBLIC_VAPID_KEY')
     });
     await axios.post('/api/users/me/push-subscription', subscription);
   }
   ```

* Backend endpoint (`/api/users/{id}/push-subscription`) stores the subscription (encrypted if needed) linked to the user.
* A lightweight worker (Cloudflare Workers, AWS Lambda, or a simple cron job) reads pending reminders (e.g., “lesson due in 10 min”, streak alerts) and triggers a push via the `web-push` library.

### 3.3 Optional Native Wrapper (Capacitor)

If you later need deeper device access (e.g., reading sleep data from Google Fit/Apple Health for the neuro‑FSRS sleep‑modulator), add Capacitor:

```bash
npm i @capacitor/core @capacitor/cli
npx cap init
npx cap add android
npx cap add ios
```

* Copy the built web assets (`npm run build`) into `capacitor`.
* Use Capacitor plugins:
  * `@capacitor/push-notifications` for unified push (FCM/APNs).
  * `@capacitor/health` (or community plugins) to query sleep metrics.
  * `@capacitor/preferences` to store temporary values like the last‑entered sleep quality score.

You can keep the same React code; Capacitor simply loads `index.html` from its `www` folder.

### 3.4 Publishing to Stores (if you go native)

* Follow the standard Android Studio / Xcode workflow to generate signed APK/AAB and IPA.
* Ensure you declare required permissions (internet, wake_lock for timers, etc.).
* Store the app’s version code/name in `capacitor.config.ts`.

---

## 4. Consolidated Checklist (Copy‑Paste into `TASKS.md`)

You can paste the following into your existing `TASKS.md` under a new section **“🚀 Production & Mobile Readiness”**.

```markdown
## 🚀 Production & Mobile Readiness

### ✅ Immediate Fix (Dev)
- [ ] Add migration script `backend/migrations/add_isimportant_to_flashcard.sql`.
- [ ] Update `backend/main.py` to auto‑add `isImportant` column on SQLite start‑up.

### 📦 Cloud Deployment Preparation
- [ ] Externalise DB: rely solely on `DATABASE_URL` env var; remove any baked‑in SQLite file from Dockerfile.
- [ ] Install & initialise Alembic (`alembic init alembic`).
- [ ] Create base migration (includes `isImportant` and any future changes).
- [ ] Modify container entrypoint to run `alembic upgrade head` before starting Uvicorn.
- [ ] Add a local‑dev `docker-compose.override.yml` that spins up a PostgreSQL service and points `DATABASE_URL` to it.
- [ ] Choose cloud provider (AWS RDS, GCP Cloud SQL, Azure Database for PostgreSQL) and provision an instance.
- [ ] Set up CI/CD (GitHub Actions) to build & push Docker images, then trigger the appropriate deployment method (ECS/Fargate, Cloud Run, Azure Container Apps).
- [ ] Configure observability: forward container stdout/stderr to cloud logs; add `/metrics` endpoint (Prometheus) if desired.
- [ ] Set up secret management (AWS Secrets Manager / GCP Secret Manager / Azure Key Vault) for API keys and DB credentials.
- [ ] Ensure zero‑downtime strategy (ECS rolling update, Cloud Run traffic split, K8s rollingUpdate).

### 📱 Mobile / PWA Enhancements
- [ ] Verify/add `manifest.json` with proper icons, `display: "standalone"`.
- [ ] Install `vite-plugin-pwa` and configure runtime caching for `/api/lessons/*` and `/api/flashcards/due`.
- [ ] Test “Add to Home Screen” on Chrome/Android Safari and iOS Safari.
- [ ] Implement VAPID‑based Web Push:
    - Generate VAPID keys.
    - Add backend endpoint `/api/users/{id}/push-subscription`.
    - Store subscription (encrypted) linked to the user.
    - Create a lightweight worker (Cloudflare Workers / Lambda) to send reminders (lesson due, streak, achievements).
- [ ] (Optional) Add Capacitor wrapper if native device features (e.g., health‑kit sleep data) become necessary:
    - `npm i @capacitor/core @capacitor/cli @capacitor/android @capacitor/ios`.
    - Copy built web assets into capacitor project.
    - Integrate plugins: push notifications, health, preferences.
- [ ] (Optional) Publish to Google Play / Apple App Store after successful native build.

### 🧪 Testing & QA
- [ ] Add unit test confirming `isImportant` field appears in GET/POST `/api/flashcards/*`.
- [ ] Add test for health endpoint `/api/health` returning `{status:"healthy"}`.
- [ ] After PWA is ready, add Cypress/Playwright test verifying offline caching of lesson & flashcard routes.
```

---

## 5. How to Apply the Changes Now

1. **Add migration script** (see 1.1).  
2. **Patch `backend/main.py`** (see 1.2).  
3. **Commit & push** – the development server should start without the `OperationalError`.  
4. After the fix is merged, proceed with the cloud‑readiness steps (external DB, Alembic, CI/CD) at your own pace.  
5. When you’re ready to tackle mobile, start with the PWA manifest & service‑worker (section 3.1), then evaluate if push notifications or a Capacitor wrapper are needed.

---

### References

* SQLite `ALTER TABLE` limitations: https://www.sqlite.org/lang_altertable.html  
* Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html  
* Vite PWA plugin: https://github.com/vitest-dev/vite-plugin-pwa  
* Web Push API overview: https://developers.google.com/web/fundamentals/push-notifications  
* Capacitor documentation: https://capacitorjs.com/docs  

--- 

*This document is the single source of truth for production‑readiness‑first‑time migration steps.*