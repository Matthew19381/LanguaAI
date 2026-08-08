import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine
from backend.routers import (
    admin,
    audio,
    auth,
    conversation,
    exercises,
    flashcards,
    integration,
    lessons,
    news,
    placement,
    pronunciation,
    push,
    quickmode,
    settings,
    stats,
    tests,
    topics,
    users,
    voice_chat,
    youtube,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate critical configuration
    from backend.config import settings
    if not settings.SECRET_KEY:
        logger.warning("SECRET_KEY is not set — using insecure default. Set SECRET_KEY in .env for production!")
    if settings.ADMIN_API_KEY and len(settings.ADMIN_API_KEY) < 16:
        logger.warning("ADMIN_API_KEY is too short — should be at least 16 characters")

    # Startup: create database tables and required directories
    logger.info("Creating database tables...")
    # Import all models so SQLAlchemy registers them before create_all
    from backend.models import achievement, user, lesson, test_result, study_plan, flashcard, topic, conversation_session, exercise, sync_event, push_subscription  # noqa
    Base.metadata.create_all(bind=engine)

    _sa = __import__('sqlalchemy')
    from sqlalchemy.exc import OperationalError, ProgrammingError
    # SQLite migrations — add missing columns safely
    _migrations = [
        ("users", "ALTER TABLE users ADD COLUMN language_profiles TEXT DEFAULT '{}'"),
        ("users", "ALTER TABLE users ADD COLUMN streak_freezes INTEGER DEFAULT 2"),
        ("users", "ALTER TABLE users ADD COLUMN sleep_data TEXT DEFAULT '{}'"),
        ("users", "ALTER TABLE users ADD COLUMN login_token VARCHAR"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN lesson_id INTEGER"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN lesson_day INTEGER"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN lesson_topic TEXT"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN gender TEXT"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN isImportant BOOLEAN NOT NULL DEFAULT 0"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN last_review_date TIMESTAMP"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN session_type VARCHAR"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN sleep_quality INTEGER"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN interleaving_bonus FLOAT"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN interference_penalty FLOAT"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN correct_recall_sessions INTEGER DEFAULT 0"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN last_recall_date TIMESTAMP"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN is_mastered BOOLEAN NOT NULL DEFAULT 0"),
        ("flashcards", "ALTER TABLE flashcards ADD COLUMN mnemonic TEXT"),
        # Knowledge bank hierarchy: subtopics point at a parent topic.
        ("topics", "ALTER TABLE topics ADD COLUMN parent_id INTEGER REFERENCES topics(id)"),
    ]
    with engine.connect() as conn:
        # Create conversation_sessions table if it doesn't exist
        try:
            conn.execute(_sa.text(
                "CREATE TABLE IF NOT EXISTS conversation_sessions ("
                "id VARCHAR PRIMARY KEY, "
                "user_id INTEGER NOT NULL REFERENCES users(id), "
                "language VARCHAR NOT NULL, "
                "native_language VARCHAR NOT NULL, "
                "cefr_level VARCHAR NOT NULL, "
                "scenario TEXT NOT NULL, "
                "system_prompt TEXT NOT NULL, "
                "history TEXT NOT NULL, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            ))
            conn.commit()
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not create conversation_sessions table: {e}")
        for _, sql in _migrations:
            try:
                conn.execute(_sa.text(sql))
                conn.commit()
            except (OperationalError, ProgrammingError):
                pass  # Column already exists

    # Ensure audio and exports directories exist
    audio_dir = os.path.join(os.path.dirname(__file__), "audio")
    exports_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(exports_dir, exist_ok=True)

    # A3: validate the model catalog at startup — a typo'd model id should be
    # loud here, not discovered as a silent fallback mid-lesson.
    try:
        from backend.config import settings as _settings
        from backend.services.model_router import (
            OPENROUTER_MODELS,
            get_model_for_task,
            validate_model,
        )

        if _settings.AI_PROVIDER.lower() == "openrouter":
            from backend.services.model_router import USED_TASKS

            invalid = []
            for task in USED_TASKS:
                model = get_model_for_task(task)
                if model and not validate_model(model):
                    invalid.append(f"{task} -> {model}")
            if invalid:
                logger.warning(
                    "Model catalog contains unknown OpenRouter ids (they will fail "
                    "at call time and fall back silently): %s",
                    "; ".join(invalid),
                )
            else:
                logger.info("Model catalog OK: all task models exist in OPENROUTER_MODELS (%d entries)", len(OPENROUTER_MODELS))
    except Exception as e:
        logger.warning("Model catalog validation skipped: %s", e)

    logger.info("LinguaAI API started successfully!")
    yield
    # Shutdown
    logger.info("LinguaAI API shutting down...")


app = FastAPI(
    title="LinguaAI API",
    description="AI-powered language learning application using OpenRouter",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — restrict to trusted origins with explicit methods/headers
# Configure via ALLOWED_ORIGINS env var (comma-separated); defaults to localhost for development
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175")
_cors_origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "Accept", "Origin"],
)

# Access gate — when APP_ACCESS_TOKEN is set, every API/audio request must prove
# the shared secret. Off by default so localhost development is unaffected.
# Registered before the rate limiter so unauthorized traffic is rejected first.
_GATE_EXEMPT_PREFIXES = (
    "/api/health",
    "/api/auth/",          # unlocking must be reachable while locked
    "/api/settings/gdrive/callback",  # Google OAuth redirect cannot send our header
)


@app.middleware("http")
async def access_gate_middleware(request: Request, call_next):
    from backend.routers.auth import gate_enabled, request_is_authorized

    if not gate_enabled() or request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    if any(path.startswith(p) for p in _GATE_EXEMPT_PREFIXES):
        return await call_next(request)

    # Guard the API and the audio files; static frontend assets stay public
    if path.startswith("/api") or path.startswith("/audio"):
        if not request_is_authorized(request):
            return JSONResponse(
                status_code=401,
                content={"detail": "Locked. Unlock this device with the app access token."},
            )
    return await call_next(request)


# Rate limiting middleware — max 30 requests per 60s per IP for AI endpoints
_ai_rate_limits: dict[str, list[float]] = defaultdict(list)
_ai_rate_lock = Lock()
AI_RATE_LIMIT = 30  # requests
AI_RATE_WINDOW = 60  # seconds
AI_ENDPOINT_PREFIXES = (
    "/api/placement",
    "/api/lessons",
    "/api/tests",
    "/api/conversation",
    "/api/quickmode",
    "/news",
    "/api/pronunciation",
    "/api/youtube",
    "/api/voice-chat/flashcards"
)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting during tests
    if os.environ.get("TESTING") == "1":
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if any(path.startswith(p) for p in AI_ENDPOINT_PREFIXES):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        with _ai_rate_lock:
            timestamps = _ai_rate_limits[client_ip]
            # Remove old entries outside the window
            cutoff = now - AI_RATE_WINDOW
            _ai_rate_limits[client_ip] = [t for t in timestamps if t > cutoff]
            if len(_ai_rate_limits[client_ip]) >= AI_RATE_LIMIT:
                logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
                return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
            _ai_rate_limits[client_ip].append(now)
    return await call_next(request)

# ── /api/v1 alias ────────────────────────────────────────────────────────────
# Routers historically mount under a mix of /api/* and /api/v1/* (users,
# voice-chat and the integration summary are v1-native). Rather than rewrite
# every decorator and risk breaking the frontend, the PWA runtime cache and the
# test suite (all of which call /api/*), this middleware makes EVERY /api/*
# endpoint ALSO reachable under /api/v1/* by rewriting the path back to /api/*
# before routing. Existing /api/* paths keep working unchanged; new integration
# code can standardise on /api/v1/*.
#
# The native /api/v1/* segments (users, voice-chat, summary, …) are discovered
# from the router table at startup — see _V1_NATIVE_SEGMENTS below — so a request
# to a genuine v1 route is left alone and new ones need no edit here. Registered
# last so it is the outermost middleware; the rewritten path is what the rate
# limiter and access gate then see.
_V1_NATIVE_SEGMENTS: set[str] = set()


@app.middleware("http")
async def api_v1_alias_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/v1/"):
        segment = path[len("/api/v1/"):].split("/", 1)[0]
        if segment and segment not in _V1_NATIVE_SEGMENTS:
            new_path = "/api/" + path[len("/api/v1/"):]
            request.scope["path"] = new_path
            request.scope["raw_path"] = new_path.encode("utf-8")
    return await call_next(request)


# Include all routers (paths are already defined with /api/... prefix)
app.include_router(placement.router, tags=["Placement"])
app.include_router(lessons.router, tags=["Lessons"])
app.include_router(tests.router, tags=["Tests"])
app.include_router(flashcards.router, tags=["Flashcards"])
app.include_router(conversation.router, tags=["Conversation"])
app.include_router(stats.router, tags=["Stats"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(quickmode.router, tags=["QuickMode"])
app.include_router(news.router, tags=["News"])
app.include_router(pronunciation.router, tags=["Pronunciation"])
app.include_router(settings.router, tags=["Settings"])
app.include_router(audio.router, tags=["Audio"])
app.include_router(youtube.router, tags=["YouTube"])
app.include_router(voice_chat.router, tags=["Voice-Chat"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(exercises.router, tags=["Exercises"])
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(integration.router, tags=["Integration"])  # INT-1: System-Glowny
app.include_router(push.router, tags=["Push"])

# Discover the /api/v1/* segments that are genuinely native (users, voice-chat,
# summary, …) so the alias middleware never rewrites a real v1 route onto a
# non-existent /api/* path. Computed once here, after every router is mounted.
for _route in app.routes:
    _p = getattr(_route, "path", "")
    if _p.startswith("/api/v1/"):
        _V1_NATIVE_SEGMENTS.add(_p[len("/api/v1/"):].split("/", 1)[0])
logger.info("v1-native segments (not aliased): %s", sorted(_V1_NATIVE_SEGMENTS))

# Serve audio files
audio_dir = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "LinguaAI API",
        "version": "1.0.0"
    }

# Serve simple frontend (no Vite, just static files)
# Use relative path to avoid Unicode issues in absolute paths
frontend_simple_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend-simple"))
if os.path.exists(os.path.join(frontend_simple_dir, "index.html")):
    app.mount("/static", StaticFiles(directory=frontend_simple_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_simple_dir, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't catch API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        index_path = os.path.join(frontend_simple_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404)