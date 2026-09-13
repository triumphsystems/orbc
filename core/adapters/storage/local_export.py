import asyncio
import json
from pathlib import Path
from typing import Any


class LocalFileExportSink:
    """Exports validated records and compiled dossiers to the local filesystem."""

    export_dir: Path

    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _write_files(
        self,
        json_file: Path,
        records: list[dict[str, Any]],
        dossier_files: list[Path] | None = None,
        dossier_bytes: bytes | None = None,
    ) -> None:
        json_file.parent.mkdir(parents=True, exist_ok=True)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
        if dossier_files and dossier_bytes:
            for df in dossier_files:
                df.parent.mkdir(parents=True, exist_ok=True)
                with open(df, "wb") as f:
                    f.write(dossier_bytes)

    async def export_results(
        self,
        automation_id: str,
        run_id: str,
        records: list[dict[str, Any]],
        dossier_bytes: bytes | None = None,
        dossier_filename: str | None = None,
    ) -> bool:
        if not records and not dossier_bytes:
            return True

        prefix = f"{automation_id[:8]}_{run_id[:8]}"
        fname = dossier_filename or "dossier.pdf"
        json_file = self.export_dir / f"{prefix}.json"

        dossier_files = [
            self.export_dir / f"{prefix}_{fname}",
            self.export_dir / automation_id / run_id / fname,
        ] if dossier_bytes else []

        try:
            await asyncio.to_thread(self._write_files, json_file, records, dossier_files, dossier_bytes)
            return True
        except Exception:  # noqa: BLE001
            return False
