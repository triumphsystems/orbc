import json
import logging
import re
from typing import Any
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, func, text
from sqlalchemy.dialects.postgresql import JSONB

from core.security.vault import SecretVault

logger = logging.getLogger("core.adapters.storage.database_sink")


class DatabaseExportSink:
    """Direct customer data warehouse export sink (PostgreSQL, MySQL, SQLite, Snowflake)."""

    def __init__(self, connection_uri: str | None = None, target_table: str | None = None):
        raw_uri = (connection_uri or "").strip()
        # Only decrypt if secret is not empty or UI placeholder
        if raw_uri and "••••" not in raw_uri:
            self.connection_uri = SecretVault.decrypt_secret(raw_uri)
        elif raw_uri and "••••" in raw_uri:
            self.connection_uri = ""
        else:
            self.connection_uri = ""
        self.target_table = target_table or "orbit_extracted_records"

    def _sanitize_ident(self, name: str) -> str:
        """Sanitizes identifiers to safe alphanumeric strings."""
        return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()

    async def export_results(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        dossier_bytes: bytes | None = None,
        dossier_filename: str | None = None,
    ) -> bool:
        """Exports validated records directly into customer data warehouse tables."""
        if not self.connection_uri or not records:
            return True

        table_name = self._sanitize_ident(self.target_table)
        engine = None
        try:
            connect_args = {"check_same_thread": False} if self.connection_uri.startswith("sqlite") else {}
            engine = create_engine(self.connection_uri, pool_pre_ping=True, connect_args=connect_args)

            dialect_name = engine.dialect.name.lower()
            if "sqlite" in dialect_name:
                ddl = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        automation_id VARCHAR(64) NOT NULL,
                        run_id VARCHAR(64) NOT NULL,
                        source_url TEXT,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            elif "mysql" in dialect_name:
                ddl = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        automation_id VARCHAR(64) NOT NULL,
                        run_id VARCHAR(64) NOT NULL,
                        source_url TEXT,
                        data JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            else:
                ddl = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        automation_id VARCHAR(64) NOT NULL,
                        run_id VARCHAR(64) NOT NULL,
                        source_url TEXT,
                        data JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """

            with engine.begin() as conn:
                conn.execute(text(ddl))

                # Batch insert records
                insert_stmt = text(f"""
                    INSERT INTO {table_name} (automation_id, run_id, source_url, data)
                    VALUES (:automation_id, :run_id, :source_url, :data)
                """)
                for rec in records:
                    rec_data = rec.get("data") if isinstance(rec, dict) and isinstance(rec.get("data"), dict) else (rec if isinstance(rec, dict) else {})
                    conn.execute(insert_stmt, {
                        "automation_id": automation_id,
                        "run_id": run_id,
                        "source_url": rec.get("url", "") if isinstance(rec, dict) else "",
                        "data": json.dumps(rec_data),
                    })
            return True
        except Exception as e:
            logger.warning(f"Data warehouse export failed: {e}")
            return False
        finally:
            if engine is not None:
                engine.dispose()

    def test_connection(self) -> tuple[bool, str]:
        """Tests live reachability of the customer data warehouse connection URI."""
        if not self.connection_uri:
            return False, "Data warehouse connection URI is not configured."
        engine = None
        try:
            connect_args = {"check_same_thread": False} if self.connection_uri.startswith("sqlite") else {}
            engine = create_engine(self.connection_uri, pool_pre_ping=True, connect_args=connect_args)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Data warehouse connection verified successfully."
        except Exception as e:
            logger.error("Data warehouse connection probe failed: %s", e)
            return False, "Could not connect to the database. Please verify your connection URI and server availability."
        finally:
            if engine is not None:
                engine.dispose()
