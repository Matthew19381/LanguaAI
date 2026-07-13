"""
Shared test fixtures for the Language Tutor backend.

Uses an in-memory SQLite database (separate from production) and overrides
the get_db dependency so each test runs in isolation.
"""
import os

# CRITICAL: Set env vars BEFORE any backend module imports
# This ensures the Settings singleton picks up the correct values
os.environ.setdefault("OPENROUTER_API_KEY", "test-dummy-key")
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")
os.environ.setdefault("ADMIN_API_KEY", "test-key")
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_language_tutor.db"

test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session, drop them at the end."""
    # Import all models so SQLAlchemy registers them with Base
    # Achievement must be imported BEFORE User (User has relationship to Achievement)
    from backend.models.achievement import Achievement  # noqa
    from backend.models.user import User          # noqa
    from backend.models.lesson import Lesson      # noqa
    from backend.models.test_result import TestResult  # noqa
    from backend.models.flashcard import Flashcard  # noqa
    from backend.models.study_plan import StudyPlan  # noqa
    from backend.models.conversation_session import ConversationSession  # noqa
    from backend.models.topic import Topic, TopicItem  # noqa
    from backend.database import Base

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables(create_tables):
    """Truncate all tables between tests to ensure isolation."""
    yield
    db = TestingSessionLocal()
    try:
        from backend.models.achievement import Achievement
        from backend.models.conversation_session import ConversationSession
        from backend.models.flashcard import Flashcard
        from backend.models.lesson import Lesson
        from backend.models.study_plan import StudyPlan
        from backend.models.test_result import TestResult
        from backend.models.topic import Topic, TopicItem
        from backend.models.user import User
        # Delete in FK-safe order (children first)
        for model in [TopicItem, Topic, ConversationSession, Achievement, Flashcard, TestResult, Lesson, StudyPlan, User]:
            db.query(model).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db():
    """Raw DB session for unit-level tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """TestClient with get_db overridden to use the test database."""
    from backend.database import get_db
    from backend.main import app

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(client):
    """Create and return a basic test user via the API."""
    r = client.post("/api/placement/create-user", json={
        "name": "Test User",
        "native_language": "Polish",
        "target_language": "German",
    })
    assert r.status_code == 200
    return r.json()
