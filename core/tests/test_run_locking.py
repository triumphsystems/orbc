import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.app import create_app
from core.api.dependencies import get_db
from core.db.orm import Automation, Run
from core.db.session import Base
from core.models.enums import RunStatus

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


def test_active_run_lock_prevents_duplicate_runs(client, db_session):
    auto = Automation(
        id="auto-12345678-aaaa-bbbb-cccc-111122223333",
        raw_goal="Monitor stock market",
        plan={"objective": "Monitor stock market", "search_query": "stocks"},
        active=True,
    )
    db_session.add(auto)
    db_session.commit()

    # 1. First run creation succeeds
    res1 = client.post(f"/api/v1/automations/{auto.id}/run")
    assert res1.status_code == 200
    run1_id = res1.json()["id"]

    # 2. Second run creation while run1 is active (discovering) fails with 409 Conflict
    res2 = client.post(f"/api/v1/automations/{auto.id}/run")
    assert res2.status_code == 409
    assert "already has an active run" in res2.json()["detail"]
    assert "discovering" in res2.json()["detail"]

    # 3. Complete run1 (status = verified)
    run1 = db_session.query(Run).filter(Run.id == run1_id).first()
    run1.status = RunStatus.verified
    db_session.commit()

    # 4. Now triggering a new run succeeds
    res3 = client.post(f"/api/v1/automations/{auto.id}/run")
    assert res3.status_code == 200
    assert res3.json()["id"] != run1_id


def test_retry_run_lock(client, db_session):
    auto = Automation(
        id="auto-88888888-aaaa-bbbb-cccc-111122223333",
        raw_goal="Track flights",
        plan={"objective": "Track flights", "search_query": "flights"},
        active=True,
    )
    run = Run(
        id="run-99999999-aaaa-bbbb-cccc-111122223333",
        automation_id=auto.id,
        status=RunStatus.extracting,
        reasoning_log=[],
    )
    db_session.add_all([auto, run])
    db_session.commit()

    # 1. Retrying an already active run fails with 409 Conflict
    res_active = client.post(f"/api/v1/runs/{run.id}/retry")
    assert res_active.status_code == 409
    assert "already active" in res_active.json()["detail"]

    # 2. Set run to failed
    run.status = RunStatus.failed
    db_session.commit()

    # 3. Retrying failed run succeeds
    res_retry = client.post(f"/api/v1/runs/{run.id}/retry")
    assert res_retry.status_code == 200
