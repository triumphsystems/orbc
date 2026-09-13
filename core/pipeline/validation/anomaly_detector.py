import statistics
from typing import Any

from core.models.execution_plan import ExecutionPlan


class AnomalyDetector:
    """Detects statistical outliers and anomalies across extracted records for any numeric metric."""

    @staticmethod
    def _extract_data(r: Any) -> dict[str, Any]:
        if not isinstance(r, dict):
            return {}
        data = r.get("data")
        if isinstance(data, dict):
            return data
        if not any(k in r for k in ("url", "extracted", "notes", "anomalies")):
            return r
        return {}

    def filter_and_annotate_outliers(
        self,
        records: list[dict[str, Any]],
        plan: ExecutionPlan | None = None,
        numeric_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if len(records) < 3:
            return records

        target_fields: set[str] = set()

        if numeric_fields:
            target_fields.update(numeric_fields)

        if plan and plan.extraction_schema:
            for f in plan.extraction_schema.fields:
                if f.type == "number":
                    target_fields.add(f.name)

        # If no target fields specified or discovered via schema, discover numeric fields across records
        if not target_fields:
            for r in records:
                data = self._extract_data(r)
                for k, v in data.items():
                    if v is not None and not isinstance(v, bool):
                        try:
                            float(v)
                            target_fields.add(k)
                        except (ValueError, TypeError):
                            pass

        for field_name in target_fields:
            values: list[float] = []
            for r in records:
                data = self._extract_data(r)
                v = data.get(field_name)
                if v is not None and not isinstance(v, bool):
                    try:
                        values.append(float(v))
                    except (ValueError, TypeError):
                        pass

            if len(values) < 3:
                continue

            median = statistics.median(values)
            if median == 0:
                continue

            # Flag extreme statistical outliers (e.g. 10x higher or 10x lower than sample median)
            for r in records:
                data = self._extract_data(r)
                v = data.get(field_name)
                if v is not None and not isinstance(v, bool):
                    try:
                        num = float(v)
                        if median > 0:
                            if num < median * 0.1:
                                r.setdefault("anomalies", []).append(
                                    f"Value {num} for '{field_name}' is suspiciously low compared to median {median:.2f}"
                                )
                            elif num > median * 10.0:
                                r.setdefault("anomalies", []).append(
                                    f"Value {num} for '{field_name}' is suspiciously high compared to median {median:.2f}"
                                )
                        elif median < 0:
                            if num > median * 0.1:
                                r.setdefault("anomalies", []).append(
                                    f"Value {num} for '{field_name}' is suspiciously high compared to median {median:.2f}"
                                )
                            elif num < median * 10.0:
                                r.setdefault("anomalies", []).append(
                                    f"Value {num} for '{field_name}' is suspiciously low compared to median {median:.2f}"
                                )
                    except (ValueError, TypeError):
                        pass

        return records
