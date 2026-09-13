import pytest
from fastapi.testclient import TestClient

from core.app import create_app
from core.db.orm import Automation, Run
from core.db.session import Base, SessionLocal, engine
from core.models.enums import RunStatus


@pytest.fixture(scope="module")
def app_client():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_stream_run_404_for_unknown_run(app_client):
    response = app_client.get("/api/v1/runs/non-existent-run-id/stream")
    assert response.status_code == 404
    assert "Run not found" in response.json()["detail"]


def test_stream_run_completed_snapshot_and_complete(app_client):
    with SessionLocal() as db:
        auto = Automation(raw_goal="Test SSE goal", plan={"objective": "Test"})
        db.add(auto)
        db.commit()
        db.refresh(auto)

        run = Run(
            automation_id=auto.id,
            status=RunStatus.verified,
            extracted_count=10,
            validated_count=10,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    response = app_client.get(f"/api/v1/runs/{run_id}/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "event: snapshot" in content
    assert "event: complete" in content
    assert run_id in content


def test_list_automation_runs_with_results(app_client):
    from core.db.orm import Result

    with SessionLocal() as db:
        auto = Automation(raw_goal="Test runs goal", plan={"objective": "Test list runs"})
        db.add(auto)
        db.commit()
        db.refresh(auto)

        run = Run(
            automation_id=auto.id,
            status=RunStatus.verified,
            extracted_count=1,
            validated_count=1,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        result = Result(
            run_id=run.id,
            url="https://example.com/item",
            data={"title": "Test Item", "price": 99.99},
            valid=True,
            validation_errors=[],
        )
        db.add(result)
        db.commit()
        auto_id = auto.id

    response = app_client.get(f"/api/v1/automations/{auto_id}/runs")
    assert response.status_code == 200
    runs_data = response.json()
    assert len(runs_data) == 1
    assert runs_data[0]["automation_id"] == auto_id
    assert len(runs_data[0]["results"]) == 1
    assert runs_data[0]["results"][0]["valid"] is True
    assert runs_data[0]["results"][0]["data"]["title"] == "Test Item"

