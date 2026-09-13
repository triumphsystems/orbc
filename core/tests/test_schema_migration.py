from unittest.mock import MagicMock, patch
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect

from core.db.session import ensure_schema_columns


def test_ensure_schema_columns_adds_missing_columns_sqlite():
    test_engine = create_engine("sqlite:///:memory:")
    meta = MetaData()

    # Create partial results table
    Table(
        "results",
        meta,
        Column("id", String, primary_key=True),
        Column("run_id", String),
    )

    # Create partial runs table
    Table(
        "runs",
        meta,
        Column("id", String, primary_key=True),
        Column("automation_id", String),
    )

    meta.create_all(test_engine)

    # Run migration helper
    ensure_schema_columns(test_engine)

    inspector = inspect(test_engine)
    results_cols = [c["name"] for c in inspector.get_columns("results")]
    runs_cols = [c["name"] for c in inspector.get_columns("runs")]

    assert "valid" in results_cols
    assert "validation_errors" in results_cols
    assert "created_at" in results_cols
    assert "pages_retrieved" in runs_cols
    assert "sources_found" in runs_cols
    assert "reasoning_log" in runs_cols
    assert "condition_matched" in runs_cols
    assert "condition_message" in runs_cols


def test_ensure_schema_columns_migrates_integer_columns_postgresql():
    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"

    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    # Mock inspector
    with patch("sqlalchemy.inspect") as mock_inspect:
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ["runs", "results"]
        mock_inspector.get_columns.side_effect = lambda table: {
            "results": [{"name": "id"}],
            "runs": [
                {"name": "id", "type": "VARCHAR"},
                {"name": "pages_retrieved", "type": "INTEGER"},
                {"name": "sources_found", "type": "INTEGER"},
            ],
        }[table]

        ensure_schema_columns(mock_engine)

        # Check that ALTER TABLE ALTER COLUMN statements were executed for pages_retrieved and sources_found
        executed_sqls = [str(call[0][0]) for call in mock_conn.execute.call_args_list]

        assert any(
            "ALTER TABLE runs ALTER COLUMN pages_retrieved TYPE JSON" in sql
            for sql in executed_sqls
        )
        assert any(
            "ALTER TABLE runs ALTER COLUMN sources_found TYPE JSON" in sql
            for sql in executed_sqls
        )
