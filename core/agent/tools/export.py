import logging
from typing import Any
from strands import tool

logger = logging.getLogger("core.agent.tools.export")


@tool
async def export_records_sink(
    automation_id: str,
    run_id: str,
    records: list[dict[str, Any]],
    sink_type: str = "local",
    destination_config: dict[str, Any] = {},
) -> dict[str, Any]:
    """
    Exports verified records to user-specified destination sinks (Local JSON, S3, SQL Database).

    Args:
        automation_id: ID of the parent automation mission.
        run_id: ID of the current run.
        records: List of verified record dictionaries to export.
        sink_type: Target sink type ('local', 's3', 'database').
        destination_config: Configuration parameters (bucket_name, database_url, table_name).
    """
    logger.info("Strands tool export_records_sink: sink_type='%s' count=%d", sink_type, len(records))
    from core.adapters.storage.local_export import LocalFileExportSink

    if sink_type == "local":
        sink = LocalFileExportSink()
        success = await sink.export_results(automation_id, run_id, records)
        return {"status": "success" if success else "failed", "sink": "local"}

    elif sink_type == "s3":
        from core.adapters.storage.s3_export import S3ExportSink

        s3 = S3ExportSink(
            bucket_name=destination_config.get("bucket_name") or "orbit-exports",
            access_key=destination_config.get("access_key") or "",
            secret_key=destination_config.get("secret_key") or "",
            region=destination_config.get("region") or "us-east-1",
            endpoint_url=destination_config.get("endpoint_url") or None,
        )
        success = await s3.export_results(automation_id, run_id, records)
        return {"status": "success" if success else "failed", "sink": "s3"}

    elif sink_type == "database":
        from core.adapters.storage.database_sink import DatabaseExportSink

        db_url = destination_config.get("database_url") or destination_config.get("connection_string")
        if not db_url:
            return {"status": "error", "message": "Missing database_url in destination_config"}
        db_sink = DatabaseExportSink(
            database_url=db_url,
            table_name=destination_config.get("table_name") or f"orbit_{automation_id[:8]}",
        )
        success = await db_sink.export_results(automation_id, run_id, records)
        return {"status": "success" if success else "failed", "sink": "database"}

    return {"status": "error", "message": f"Unknown sink type '{sink_type}'"}
