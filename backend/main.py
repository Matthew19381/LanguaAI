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
    conversation,
    exercises,
    flashcards,
    lessons,
    news,
    placement,
    pronunciation,
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
    from backend.models import achievement, user, lesson, test_result, study_plan, flashcard, topic, conversation_session, exercise  # noqa
    Base.metadata.create_all(bind=engine)

    _sa = __import__('sqlalchemy')
    from sqlalchemy.exc import OperationalError, ProgrammingError
    # SQLite migrations — add missing columns safely
    _migrations = [
        ("users", "ALTER TABLE users ADD COLUMN language_profiles TEXT DEFAULT '{}'"),
        ("users", "ALTER TABLE users ADD COLUMN streak_freezes INTEGER DEFAULT 2"),
        ("users", "ALTER TABLE users ADD COLUMN sleep_data TEXT DEFAULT '{}'"),
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
app.include_router(exercises.router, tags=["Exercises"])
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(admin.router, tags=["Admin"])

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
if os.path.exists(frontend_simple_dir):
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