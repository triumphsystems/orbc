import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.strands_orchestrator import StrandsAgentOrchestrator
from core.models.enums import RunStatus
from core.models.execution_plan import ExecutionPlan


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.rollback = MagicMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_automation():
    auto = MagicMock()
    auto.id = "auto-test-1234"
    auto.raw_goal = "Extract AI research grants"
    auto.plan = {
        "objective": "Extract AI research grants",
        "search_query": "AI research grants 2026",
        "extraction_schema": {
            "entity_name": "Grant",
            "fields": {"title": "str", "amount": "str"},
        },
    }
    return auto


@pytest.fixture
def mock_run():
    run = MagicMock()
    run.id = "run-test-5678"
    run.automation_id = "auto-test-1234"
    run.status = RunStatus.pending
    run.reasoning_log = []
    run.sources_found = []
    run.pages_retrieved = []
    run.results = []
    return run


@pytest.mark.asyncio
async def test_strands_orchestrator_initialization():
    mock_model = MagicMock()
    orch = StrandsAgentOrchestrator(model=mock_model)
    assert orch.model == mock_model


@pytest.mark.asyncio
async def test_strands_agent_loop_execution(mock_db, mock_automation, mock_run):
    orch = StrandsAgentOrchestrator(model=MagicMock())

    with patch("strands.Agent", create=True) as mock_agent_cls, \
         patch("core.events.bus.event_bus.publish", new_callable=AsyncMock):

        mock_agent_instance = MagicMock()
        mock_agent_instance.return_value = "Mission complete. Extracted 2 records."
        mock_agent_cls.return_value = mock_agent_instance

        # Execute run
        result_run = await orch.execute_run(
            db=mock_db,
            automation=mock_automation,
            run=mock_run,
        )

        assert result_run.status == RunStatus.verified
        assert mock_db.commit.called
