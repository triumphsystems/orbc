import pytest
from sqlalchemy import create_engine, text

from core.adapters.storage.database_sink import DatabaseExportSink


@pytest.mark.asyncio
async def test_database_export_sink_sqlite():
    db_uri = "sqlite:///./test_sink.db"
    sink = DatabaseExportSink(connection_uri=db_uri, target_table="test_records")

    records = [
        {"url": "https://item.com/1", "data": {"title": "Widget Alpha", "price": 49.99}},
        {"url": "https://item.com/2", "data": {"title": "Widget Beta", "price": 99.00}},
    ]

    success = await sink.export_results("auto-test-1", "run-test-1", records)
    assert success is True

    # Verify rows in destination database
    engine = create_engine(db_uri)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM test_records")).scalar()
        assert result == 2

    # Clean up test db file
    import os
    if os.path.exists("./test_sink.db"):
        os.remove("./test_sink.db")


def test_database_sink_test_connection():
    # Valid sqlite memory URI
    sink = DatabaseExportSink(connection_uri="sqlite:///:memory:")
    ok, msg = sink.test_connection()
    assert ok is True
    assert "verified" in msg

    # Empty URI
    sink_empty = DatabaseExportSink(connection_uri="")
    ok, msg = sink_empty.test_connection()
    assert ok is False
    assert "not configured" in msg
