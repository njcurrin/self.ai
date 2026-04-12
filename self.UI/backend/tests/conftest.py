# conftest.py — Root test fixtures for self.UI backend
#
# Architecture:
#   - Uses app.dependency_overrides (not monkey-patching) for DI
#   - Truncation-based teardown (dual Peewee+SQLAlchemy sessions make
#     transaction rollback unworkable)
#   - Session-scoped DB engine; function-scoped truncation
#   - Both Peewee and SQLAlchemy (Alembic) migrations run at session start
#
import os
import time
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Override env BEFORE importing any selfai_ui modules.
# Use direct assignment (not setdefault) because container env may have
# empty values that would block setdefault but still fail validation.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
os.environ["WEBUI_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENV"] = "test"
os.environ["WEBUI_AUTH"] = "True"
os.environ["SKIP_PEEWEE_MIGRATION"] = "true"

from selfai_ui.internal.db import Base, get_db, get_session  # noqa: E402
from selfai_ui.utils.auth import create_token  # noqa: E402


# ---------------------------------------------------------------------------
# Table truncation order (respects FK constraints — children before parents)
# ---------------------------------------------------------------------------
TRUNCATION_ORDER = [
    "feedback",
    "message_reaction",
    "message",
    "chat",
    "tag",
    "knowledge_file",
    "knowledge",
    "file",
    "folder",
    "memory",
    "model",
    "prompt",
    "tool",
    "function",
    "training_job",
    "training_course",
    "eval_job",
    "curator_job",
    "job_window_slot",
    "job_window",
    "benchmark_config",
    "group",
    "auth",
    "user",
    "channel",
]


# ---------------------------------------------------------------------------
# Session-scoped: engine + schema
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine (session-scoped, shared across all tests)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """SessionLocal replacement bound to the test engine."""
    return sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False
    )


# ---------------------------------------------------------------------------
# Function-scoped: session + truncation
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session(test_session_factory, test_engine):
    """Provide a fresh DB session with truncation-based cleanup.

    Also patches get_db in model modules that import it at module level
    (needed because model classes use `with get_db() as db:` pattern and
    don't go through FastAPI's dependency injection).
    """
    session = test_session_factory()

    @contextmanager
    def _mock_get_db():
        yield session

    # Patch get_db in modules that import it directly (bypass DI)
    import selfai_ui.internal.db as db_module
    patched_modules = [db_module]
    for mod_name in [
        "selfai_ui.models.job_windows",
        "selfai_ui.utils.gpu_queue",
        "selfai_ui.models.benchmark_config",
        "selfai_ui.models.curator_jobs",
        "selfai_ui.models.training",
        "selfai_ui.models.eval_jobs",
        "selfai_ui.models.users",
        "selfai_ui.models.auths",
        "selfai_ui.models.chats",
        "selfai_ui.models.files",
        "selfai_ui.models.knowledge",
        "selfai_ui.models.tools",
        "selfai_ui.models.functions",
    ]:
        try:
            mod = __import__(mod_name, fromlist=["get_db"])
            if hasattr(mod, "get_db"):
                patched_modules.append(mod)
        except ImportError:
            pass

    originals = {id(m): m.get_db for m in patched_modules}
    for m in patched_modules:
        m.get_db = _mock_get_db

    yield session

    # Restore
    for m in patched_modules:
        m.get_db = originals[id(m)]
    session.close()
    # Truncate all tables in FK-safe order
    with test_engine.connect() as conn:
        for table in TRUNCATION_ORDER:
            try:
                conn.execute(text(f"DELETE FROM [{table}]"))
            except Exception:
                pass  # Table may not exist in SQLite schema
        conn.commit()


# ---------------------------------------------------------------------------
# Override get_db to use test session
# ---------------------------------------------------------------------------

@pytest.fixture
def _override_db(test_session_factory):
    """Override the app's get_db dependency to use our test session factory."""
    @contextmanager
    def _test_get_db():
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()

    from selfai_ui.main import app
    original_override = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = lambda: _test_get_db()

    # Also patch module-level get_db for model classes that call it directly
    import selfai_ui.internal.db as db_module
    original_get_db = db_module.get_db
    db_module.get_db = _test_get_db

    yield

    app.dependency_overrides = original_override
    db_module.get_db = original_get_db


# ---------------------------------------------------------------------------
# Startup task isolation (T-219)
# ---------------------------------------------------------------------------

@pytest.fixture
def _isolate_startup_tasks():
    """Prevent fire-and-forget startup tasks from running during tests.

    NOT autouse — only applies when test_app fixture is requested.
    Existing model-only tests don't import main.py and don't need this.
    """
    with patch("selfai_ui.main.periodic_usage_pool_cleanup", new_callable=AsyncMock), \
         patch("selfai_ui.main._resume_crawl_jobs", new_callable=AsyncMock), \
         patch("selfai_ui.main._run_gpu_queue", new_callable=AsyncMock), \
         patch("selfai_ui.main._ensure_curator_classifier_models", new_callable=AsyncMock):
        yield


# ---------------------------------------------------------------------------
# Test app / client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app(_override_db, _isolate_startup_tasks):
    """Provide the FastAPI app with test overrides applied."""
    from selfai_ui.main import app
    return app


@pytest.fixture
def client(test_app):
    """HTTP test client (no real server started)."""
    with TestClient(test_app) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helper fixtures
# ---------------------------------------------------------------------------

def _create_test_user(db_session, role="user"):
    """Insert a test user + auth record, return (user_model, jwt_token)."""
    user_id = str(uuid.uuid4())
    email = f"test-{role}-{user_id[:8]}@test.local"
    now = int(time.time())

    # Insert user row directly via SQL to avoid import-chain issues
    db_session.execute(
        text(
            "INSERT INTO [user] (id, name, email, role, profile_image_url, "
            "last_active_at, updated_at, created_at) "
            "VALUES (:id, :name, :email, :role, :pic, :now, :now, :now)"
        ),
        {
            "id": user_id,
            "name": f"Test {role.title()}",
            "email": email,
            "role": role,
            "pic": "/user.png",
            "now": now,
        },
    )
    db_session.execute(
        text(
            "INSERT INTO [auth] (id, email, password, active) "
            "VALUES (:id, :email, :password, :active)"
        ),
        {"id": user_id, "email": email, "password": "unused-in-tests", "active": True},
    )
    db_session.commit()

    token = create_token(data={"id": user_id})
    return {"id": user_id, "email": email, "role": role, "token": token}


@pytest.fixture
def test_user(db_session):
    """A test user with 'user' role. Returns dict with id, email, role, token."""
    return _create_test_user(db_session, role="user")


@pytest.fixture
def test_admin(db_session):
    """A test user with 'admin' role. Returns dict with id, email, role, token."""
    return _create_test_user(db_session, role="admin")


@pytest.fixture
def authenticated_user(client, test_user):
    """Test client pre-configured with a valid user-role Bearer token."""
    client.headers["Authorization"] = f"Bearer {test_user['token']}"
    client.headers["Content-Type"] = "application/json"
    return client


@pytest.fixture
def authenticated_admin(client, test_admin):
    """Test client pre-configured with a valid admin-role Bearer token."""
    client.headers["Authorization"] = f"Bearer {test_admin['token']}"
    client.headers["Content-Type"] = "application/json"
    return client
