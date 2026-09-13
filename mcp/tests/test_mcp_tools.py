import pytest
from unittest.mock import AsyncMock
from orbit.client import OrbitBackendClient
from orbit.tools.automations import create_automation_tool, list_automations_tool
from orbit.tools.execution import execute_goal_tool, run_automation_tool
from orbit.tools.inspection import query_extracted_data_tool


@pytest.mark.asyncio
async def test_create_automation_tool():
    mock_client = AsyncMock(spec=OrbitBackendClient)
    mock_client.create_automation.return_value = {
        "id": "auto-123",
        "plan": {
            "objective": "Find PS5",
            "domain": "ecommerce",
            "search_query": "PS5 Nigeria",
            "frequency": "daily",
            "condition": "min(price) < 400000",
            "extraction_schema": {"entity_name": "product", "fields": []},
        },
    }

    result = await create_automation_tool("Find PS5", mock_client)
    assert result["success"] is True
    assert result["automation_id"] == "auto-123"
    assert result["domain"] == "ecommerce"


@pytest.mark.asyncio
async def test_run_automation_tool():
    mock_client = AsyncMock(spec=OrbitBackendClient)
    mock_client.run_automation.return_value = {
        "id": "run-456",
        "automation_id": "auto-123",
        "status": "verified",
        "sources_found": ["https://example.com/p1"],
        "pages_retrieved": ["https://example.com/p1"],
        "extracted_count": 1,
        "validated_count": 1,
        "condition_matched": True,
        "condition_message": "Price < 400000 matched",
        "results": [
            {
                "url": "https://example.com/p1",
                "valid": True,
                "data": {"product": "PS5", "price": 380000},
            }
        ],
    }

    result = await run_automation_tool("auto-123", mock_client)
    assert result["success"] is True
    assert result["status"] == "verified"
    assert result["condition_matched"] is True
    assert len(result["valid_records"]) == 1


@pytest.mark.asyncio
async def test_query_extracted_data_tool_valid_only():
    mock_client = AsyncMock(spec=OrbitBackendClient)
    mock_client.get_run.return_value = {
        "id": "run-456",
        "status": "verified",
        "results": [
            {"id": "r1", "valid": True, "data": {"product": "PS5"}},
            {"id": "r2", "valid": False, "data": {"product": None}},
        ],
    }

    result = await query_extracted_data_tool("run-456", valid_only=True, client=mock_client)
    assert result["success"] is True
    assert result["total_records"] == 1
    assert result["records"][0]["id"] == "r1"
