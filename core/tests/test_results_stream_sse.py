import pytest
from fastapi.testclient import TestClient

from core.app import create_app
from core.db.orm import Automation, Result, Run
from core.db.session import Base, SessionLocal, engine
from core.models.enums import RunStatus


@pytest.fixture(scope="module")
def app_client():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_stream_results_404_for_unknown_run(app_client):
    response = app_client.get("/api/v1/runs/non-existent-run-id/results/stream")
    assert response.status_code == 404
    assert "Run not found" in response.json()["detail"]


def test_stream_results_success(app_client):
    with SessionLocal() as db:
        auto = Automation(raw_goal="Test Results Stream", plan={"objective": "Test"})
        db.add(auto)
        db.commit()
        db.refresh(auto)

        run = Run(
            automation_id=auto.id,
            status=RunStatus.verified,
            extracted_count=2,
            validated_count=2,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        res1 = Result(
            run_id=run.id,
            url="https://example.com/item1",
            data={"title": "Item 1", "price": 100},
            valid=True,
        )
        res2 = Result(
            run_id=run.id,
            url="https://example.com/item2",
            data={"title": "Item 2", "price": 200},
            valid=True,
        )
        db.add_all([res1, res2])
        db.commit()
        run_id = run.id

    response = app_client.get(f"/api/v1/runs/{run_id}/results/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "event: record" in content
    assert "Item 1" in content
    assert "Item 2" in content
    assert "event: complete" in content
