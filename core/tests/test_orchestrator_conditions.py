from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.agent.orchestrator import AgentOrchestrator
from core.db.orm import Automation, Result, Run
from core.db.session import Base
from core.models.enums import RunStatus
from core.models.execution_plan import ExecutionPlan


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_verification_gate_failure_on_zero_valid_records(db_session):
    plan = ExecutionPlan(objective="Flights", search_query="cheap flights")
    auto = Automation(raw_goal="Flights", plan=plan.model_dump(), active=True)
    db_session.add(auto)
    db_session.commit()

    discovery_mock = MagicMock(discover=AsyncMock(return_value=["https://flights.com"]))
    retrieval_mock = MagicMock(retrieve_many=AsyncMock(return_value={"https://flights.com": "page"}))
    link_extractor_mock = MagicMock(extract_child_links=MagicMock(return_value=[]))
    extractor_mock = MagicMock(extract=AsyncMock(return_value={"url": "https://flights.com", "data": {"price": "invalid"}}))
    validator_mock = MagicMock(validate=MagicMock(return_value=(False, ["Price must be numeric"])))

    orchestrator = AgentOrchestrator(
        discovery=discovery_mock,
        retrieval=retrieval_mock,
        link_extractor=link_extractor_mock,
        extractor=extractor_mock,
        validator=validator_mock,
    )

    run = await orchestrator.execute_run(db_session, auto)
    assert run.status == RunStatus.failed
    assert run.validated_count == 0
    assert "Verification failed" in (run.error or "")


@pytest.mark.asyncio
async def test_historical_delta_condition_and_notification(db_session):
    plan = ExecutionPlan(objective="Salary", search_query="dev salary", condition="salary drops by 10%")
    auto = Automation(raw_goal="Salary", plan=plan.model_dump(), active=True)
    db_session.add(auto)
    db_session.commit()

    prev_run = Run(automation_id=auto.id, status=RunStatus.verified, validated_count=1)
    db_session.add(prev_run)
    db_session.commit()
    db_session.add(Result(run_id=prev_run.id, url="https://jobs.com/1", data={"salary": 150000}, valid=True))
    db_session.commit()

    discovery_mock = MagicMock(discover=AsyncMock(return_value=["https://jobs.com/1"]))
    retrieval_mock = MagicMock(retrieve_many=AsyncMock(return_value={"https://jobs.com/1": "content"}))
    link_extractor_mock = MagicMock(extract_child_links=MagicMock(return_value=[]))
    extractor_mock = MagicMock(extract=AsyncMock(return_value={"url": "https://jobs.com/1", "data": {"salary": 120000}, "extracted": True}))
    validator_mock = MagicMock(validate=MagicMock(return_value=(True, [])))
    notifier_mock = MagicMock(notify=AsyncMock(return_value=True))
    export_mock = MagicMock(export_results=AsyncMock(return_value=True))

    orchestrator = AgentOrchestrator(
        discovery=discovery_mock,
        retrieval=retrieval_mock,
        link_extractor=link_extractor_mock,
        extractor=extractor_mock,
        validator=validator_mock,
        notifier=notifier_mock,
        export_sink=export_mock,
    )

    run = await orchestrator.execute_run(db_session, auto)
    assert run.condition_matched is True
    assert notifier_mock.notify.called
    assert export_mock.export_results.called
