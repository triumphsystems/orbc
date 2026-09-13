import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.app import create_app
from core.api.dependencies import get_db, resolve_entity_by_id_or_prefix
from core.db.orm import Automation, Run
from core.db.session import Base
from core.models.enums import RunStatus

# In-memory SQLite for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_resolve_exact_match(db_session):
    auto = Automation(
        id="01d6a05b-8f12-4c3e-9012-3456789abcde",
        raw_goal="Monitor tech jobs",
        plan={"objective": "Monitor tech jobs"},
        active=True,
    )
    db_session.add(auto)
    db_session.commit()

    resolved = resolve_entity_by_id_or_prefix(
        db_session, Automation, "01d6a05b-8f12-4c3e-9012-3456789abcde", "automation"
    )
    assert resolved.id == auto.id


def test_resolve_prefix_match(db_session):
    auto = Automation(
        id="01d6a05b-8f12-4c3e-9012-3456789abcde",
        raw_goal="Monitor tech jobs",
        plan={"objective": "Monitor tech jobs"},
        active=True,
    )
    db_session.add(auto)
    db_session.commit()

    resolved = resolve_entity_by_id_or_prefix(db_session, Automation, "01d6a05b", "automation")
    assert resolved.id == auto.id

    resolved_4chars = resolve_entity_by_id_or_prefix(db_session, Automation, "01d6", "automation")
    assert resolved_4chars.id == auto.id


def test_resolve_ambiguous_prefix(db_session):
    auto1 = Automation(
        id="01d6a05b-1111-1111-1111-111111111111",
        raw_goal="Goal 1",
        plan={"objective": "Goal 1"},
        active=True,
    )
    auto2 = Automation(
        id="01d6a05b-2222-2222-2222-222222222222",
        raw_goal="Goal 2",
        plan={"objective": "Goal 2"},
        active=True,
    )
    db_session.add_all([auto1, auto2])
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        resolve_entity_by_id_or_prefix(db_session, Automation, "01d6a05b", "automation")

    assert "Ambiguous automation identifier" in str(exc_info.value.detail)
    assert "01d6a05b-111" in str(exc_info.value.detail)
    assert "01d6a05b-222" in str(exc_info.value.detail)


def test_resolve_too_short_prefix(db_session):
    with pytest.raises(Exception) as exc_info:
        resolve_entity_by_id_or_prefix(db_session, Automation, "01d", "automation")

    assert "too short" in str(exc_info.value.detail)
    assert "at least 4 characters" in str(exc_info.value.detail)


def test_api_automation_and_run_prefix_resolution(client, db_session):
    auto = Automation(
        id="abcd1234-5678-90ab-cdef-1234567890ab",
        raw_goal="Monitor prices",
        plan={"objective": "Monitor prices", "search_query": "prices"},
        active=True,
    )
    run = Run(
        id="9876fedc-ba09-8765-4321-fedcba098765",
        automation_id=auto.id,
        status=RunStatus.verified,
        reasoning_log=[],
    )
    db_session.add_all([auto, run])
    db_session.commit()

    # Test GET /api/v1/automations/{prefix}
    resp = client.get("/api/v1/automations/abcd1234")
    assert resp.status_code == 200
    assert resp.json()["id"] == auto.id

    # Test GET /api/v1/runs/{prefix}
    resp = client.get("/api/v1/runs/9876fedc")
    assert resp.status_code == 200
    assert resp.json()["id"] == run.id

    # Test GET /api/v1/automations/{prefix}/runs
    resp = client.get("/api/v1/automations/abcd1234/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == run.id
