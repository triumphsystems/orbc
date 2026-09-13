import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.agent.orchestrator import AgentOrchestrator, RunPoolManager
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


@pytest.mark.asyncio
async def test_global_run_pool_concurrency_limiting():
    # Set global pool limit to 2 concurrent missions
    RunPoolManager.set_limit(2)
    assert RunPoolManager.get_active_count() == 0

    orchestrator = AgentOrchestrator()
    # Mock pipeline stages to simulate async processing delay
    orchestrator.discovery.discover = AsyncMock(return_value=["http://example.com"])
    orchestrator.retrieval.retrieve_many = AsyncMock(return_value={"http://example.com": "Page Content"})
    orchestrator.extractor.extract = AsyncMock(return_value={"url": "http://example.com", "extracted": True, "data": {"price": 100}})
    orchestrator.validator.validate_batch = MagicMock(return_value=[MagicMock(valid=True, errors=[])])
    orchestrator.verification.verify = MagicMock(return_value=MagicMock(verified=True, summary="OK"))
    orchestrator.notifier.dispatch_run_notification = AsyncMock()
    orchestrator.export_sink.export = MagicMock()

    peak_active = 0

    # Patch retrieval to simulate a 0.2s running duration and track peak concurrent runs
    async def delayed_retrieve(*args, **kwargs):
        nonlocal peak_active
        current_active = RunPoolManager.get_active_count()
        if current_active > peak_active:
            peak_active = current_active
        await asyncio.sleep(0.2)
        return {"http://example.com": "Page Content"}

    orchestrator.retrieval.retrieve_many = delayed_retrieve

    # Create 4 automations
    db = TestingSessionLocal()
    automations = []
    for i in range(4):
        auto = Automation(
            id=f"auto-test-{i}-1111-2222-3333-444455556666",
            raw_goal=f"Goal {i}",
            plan={
                "objective": f"Goal {i}",
                "search_query": f"query {i}",
                "extraction_schema": {
                    "entity_name": "Product",
                    "fields": [{"name": "price", "field_type": "number", "required": True}],
                },
            },
            active=True,
        )
        db.add(auto)
        automations.append(auto)
    db.commit()

    # Launch all 4 runs concurrently with isolated db sessions
    async def _run_for_auto(auto_id: str):
        with TestingSessionLocal() as session:
            auto = session.query(Automation).filter(Automation.id == auto_id).first()
            return await orchestrator.execute_run(session, auto)

    tasks = [_run_for_auto(auto.id) for auto in automations]
    completed_runs = await asyncio.gather(*tasks)

    # 1. Verify peak concurrent runs never exceeded the pool limit of 2
    assert peak_active <= 2

    # 2. Verify all 4 completed successfully
    assert len(completed_runs) == 4
    for r in completed_runs:
        assert r.status == RunStatus.verified

    # 3. Verify active count returned to 0
    assert RunPoolManager.get_active_count() == 0
    db.close()
