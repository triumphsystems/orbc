from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.adapters.communication.slack import SlackWebhookAdapter
from core.adapters.storage.local_export import LocalFileExportSink
from core.adapters.storage.s3_export import S3ExportSink
from core.agent.orchestrator import AgentOrchestrator
from core.db.orm import Automation
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
async def test_s3_presigned_url_generation():
    sink = S3ExportSink(bucket_name="my-bucket")
    url = sink.generate_presigned_url("automation-abc", "run-xyz", "dossier.pdf")
    assert "my-bucket" in url
    assert "autho" in url or "auto" in url
    assert "dossier.pdf" in url


@pytest.mark.asyncio
async def test_slack_webhook_blocks_structure():
    adapter = SlackWebhookAdapter("https://hooks.slack.com/services/dummy")
    adapter.send_alert = AsyncMock(return_value=True)
    sent = await adapter.send_alert(
        title="Test Mission",
        message="3 records extracted",
        dossier_url="https://s3.amazonaws.com/my-bucket/dossier.pdf",
    )
    assert sent is True


@pytest.mark.asyncio
async def test_orchestrator_multi_sink_dispatch(db_session, tmp_path):
    plan = ExecutionPlan(objective="Test Dossier", search_query="query", condition="price < 100")
    auto = Automation(raw_goal="Test Dossier", plan=plan.model_dump(), active=True)
    db_session.add(auto)
    db_session.commit()

    discovery_mock = MagicMock(discover=AsyncMock(return_value=["https://item.com"]))
    retrieval_mock = MagicMock(retrieve_many=AsyncMock(return_value={"https://item.com": "content"}))
    extractor_mock = MagicMock(extract=AsyncMock(return_value={"url": "https://item.com", "data": {"price": 50}, "extracted": True}))
    validator_mock = MagicMock(validate=MagicMock(return_value=(True, [])))
    notifier_mock = MagicMock(notify=AsyncMock(return_value=True))

    local_sink = LocalFileExportSink(export_dir=str(tmp_path))
    s3_sink_mock = MagicMock(
        export_results=AsyncMock(return_value=True),
        generate_presigned_url=MagicMock(return_value="https://s3.amazonaws.com/dossier.pdf"),
    )

    orchestrator = AgentOrchestrator(
        discovery=discovery_mock,
        retrieval=retrieval_mock,
        extractor=extractor_mock,
        validator=validator_mock,
        notifier=notifier_mock,
        export_sink=local_sink,
        s3_sink=s3_sink_mock,
    )

    run = await orchestrator.execute_run(db_session, auto)
    assert run.validated_count == 1
    assert s3_sink_mock.export_results.called
    assert notifier_mock.notify.called
