from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.agent.orchestrator import AgentOrchestrator
from core.db.orm import Automation, Run
from core.db.session import Base
from core.models.execution_plan import ExecutionPlan


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_self_correction_on_zero_discovery(db_session):
    plan = ExecutionPlan(objective="Find cheap GPU", search_query="cheap gpu")
    auto = Automation(raw_goal="Find cheap GPU", plan=plan.model_dump(), active=True)
    db_session.add(auto)
    db_session.commit()

    discovery_mock = MagicMock()
    discovery_mock.discover = AsyncMock(side_effect=[[], ["https://recovered-gpu.com/card"]])

    brain_mock = MagicMock()
    brain_mock.diagnose_and_recover = AsyncMock(return_value={"can_recover": True, "new_search_query": "affordable rtx"})

    retrieval_mock = MagicMock()
    retrieval_mock.retrieve_many = AsyncMock(return_value={"https://recovered-gpu.com/card": "GPU details"})

    extractor_mock = MagicMock()
    extractor_mock.extract = AsyncMock(return_value={"url": "https://recovered-gpu.com/card", "data": {"price": 300}, "extracted": True})

    validator_mock = MagicMock()
    validator_mock.validate = MagicMock(return_value=(True, []))

    orchestrator = AgentOrchestrator(
        discovery=discovery_mock,
        brain=brain_mock,
        retrieval=retrieval_mock,
        extractor=extractor_mock,
        validator=validator_mock,
    )

    run = await orchestrator.execute_run(db_session, auto)
    assert run.sources_found == ["https://recovered-gpu.com/card"]
    assert any(log.get("stage") == "discovery" for log in run.reasoning_log)
    assert brain_mock.diagnose_and_recover.called


@pytest.mark.asyncio
async def test_autonomous_two_hop_detail_navigation(db_session):
    plan = ExecutionPlan(objective="Jobs in London", search_query="london jobs")
    auto = Automation(raw_goal="Jobs in London", plan=plan.model_dump(), active=True)
    db_session.add(auto)
    db_session.commit()

    discovery_mock = MagicMock()
    discovery_mock.discover = AsyncMock(return_value=["https://jobs.com/list"])

    retrieval_mock = MagicMock()
    retrieval_mock.retrieve_many = AsyncMock(side_effect=[
        {"https://jobs.com/list": "<a href='/item1'>Job 1</a>"},
        {"https://jobs.com/item1": "Job 1 content", "https://jobs.com/item2": "Job 2 content"}
    ])

    link_extractor_mock = MagicMock()
    link_extractor_mock.extract_child_links = MagicMock(return_value=["https://jobs.com/item1", "https://jobs.com/item2"])

    extractor_mock = MagicMock()
    extractor_mock.extract = AsyncMock(return_value={"data": {"title": "Dev"}, "extracted": True})

    orchestrator = AgentOrchestrator(
        discovery=discovery_mock,
        retrieval=retrieval_mock,
        link_extractor=link_extractor_mock,
        extractor=extractor_mock,
    )

    run = await orchestrator.execute_run(db_session, auto)
    assert len(run.pages_retrieved) == 2
    assert "https://jobs.com/item1" in run.pages_retrieved
