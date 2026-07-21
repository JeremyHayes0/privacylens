import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_database_session
from app.main import app
from app.services import scan_service

# Tests run against an in-memory SQLite database, not the real
# Postgres instance. This keeps the test suite fast and hermetic (no
# external service required to run `pytest`) at the cost of not
# exercising Postgres-specific behavior -- an acceptable tradeoff for
# these fast unit/integration tests. A smaller number of tests against
# a real Postgres container (e.g. in CI, via a service container) is
# the natural complement to this, not a replacement for it.
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def stub_scan_enqueue(monkeypatch):
    """
    Every test in this suite runs with no live Redis instance. Rather
    than requiring one just to collect `pytest`, this autouse fixture
    replaces scan_service.enqueue_scan with a no-op for every test.
    enqueue_scan's own contract (it calls RQ's Queue.enqueue with the
    right arguments) is tested in isolation, without a real Redis
    connection either, in tests/unit/test_queue.py.

    Patching `scan_service.enqueue_scan` (where the name is *used*)
    rather than `app.core.queue.enqueue_scan` (where it's *defined*) is
    deliberate -- scan_service imported the name directly via `from
    app.core.queue import enqueue_scan`, so it holds its own reference
    that patching the origin module wouldn't affect.
    """
    monkeypatch.setattr(scan_service, "enqueue_scan", lambda scan_id: None)


@pytest.fixture()
def db_session():
    """A fresh, empty database (all tables created) for a single test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """
    A TestClient wired to the test database via FastAPI's dependency
    override mechanism -- the app code under test is completely
    unaware it's talking to SQLite instead of Postgres; it just
    receives whatever Session `get_database_session` yields.
    """

    def _override_get_database_session():
        yield db_session

    app.dependency_overrides[get_database_session] = _override_get_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
