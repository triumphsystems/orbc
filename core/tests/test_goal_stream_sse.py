import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from core.app import create_app
from core.db.session import Base, engine


@pytest.fixture(scope="module")
def app_client():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_stream_goal_plan_validation_error(app_client):
    response = app_client.get("/api/v1/automations/plan/stream?goal=")
    assert response.status_code == 400
    assert "goal description must be provided" in response.json()["detail"].lower()


@patch("core.llm.factory.get_llm_client")
def test_stream_goal_plan_success(mock_get_llm, app_client):
    mock_client = AsyncMock()
    mock_client.call_json.return_value = {
        "objective": "Track GPU prices",
        "domain": "compute",
        "search_query": "gpu prices",
        "frequency": "daily",
        "extraction_schema": {
            "entity_name": "gpu_item",
            "fields": [{"name": "price", "type": "number", "required": True}],
        },
    }
    mock_get_llm.return_value = mock_client

    response = app_client.get("/api/v1/automations/plan/stream?goal=Track%20GPU%20prices")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "event: reasoning" in content
    assert "event: plan" in content
    assert "event: complete" in content
    assert "Track GPU prices" in content
