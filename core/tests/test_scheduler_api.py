import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from core.app import create_app
from core.db.orm import Automation
from core.db.session import SessionLocal
from core.models.enums import Frequency
from core.models.execution_plan import ExecutionPlan, DynamicExtractionSchema, ExtractionField


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_scheduler_trigger_due_endpoint(client):
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        plan = ExecutionPlan(
            objective="Scheduled test goal",
            domain="general",
            search_query="test search",
            frequency=Frequency.hourly,
            extraction_schema=DynamicExtractionSchema(
                entity_name="item",
                fields=[ExtractionField(name="title", type="string", required=True)]
            )
        )

        # Create an automation due in the past
        auto = Automation(
            raw_goal="Test scheduled automation",
            plan=plan.model_dump(),
            active=True,
            next_run_at=now_utc - timedelta(minutes=5),
        )
        db.add(auto)
        db.commit()
        db.refresh(auto)
        auto_id = auto.id

        # Call the cloud scheduler hook asynchronously (default)
        resp = client.post("/api/v1/scheduler/trigger-due")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["due_count"] >= 1
        assert auto_id in data["triggered_automation_ids"]
        assert data["wait"] is False

        # Create another due automation for testing ?wait=true
        auto2 = Automation(
            raw_goal="Test scheduled sync automation",
            plan=plan.model_dump(),
            active=True,
            next_run_at=now_utc - timedelta(minutes=10),
        )
        db.add(auto2)
        db.commit()
        db.refresh(auto2)
        auto2_id = auto2.id

        # Call with ?wait=true (Cloud Run synchronous mode)
        resp_sync = client.post("/api/v1/scheduler/trigger-due?wait=true")
        assert resp_sync.status_code == 200
        data_sync = resp_sync.json()
        assert data_sync["status"] == "success"
        assert data_sync["wait"] is True
        assert auto2_id in data_sync["triggered_automation_ids"]

        # Call scheduler status
        status_resp = client.get("/api/v1/scheduler/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "server_time_utc" in status_data
        assert "schedules" in status_data
    finally:
        db.close()

