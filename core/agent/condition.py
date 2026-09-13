import logging
import re
from typing import Any

from core.agent.baseline_cache import BaselineCache, BaselineCacheFactory

logger = logging.getLogger("core.agent.condition")


class ConditionEvaluator:
    """Domain-agnostic evaluator for threshold alerts, metric aggregations, and historical relative shifts."""

    baseline_cache: BaselineCache

    def __init__(self, baseline_cache: BaselineCache | None = None):
        self.baseline_cache = baseline_cache or BaselineCacheFactory.get_cache()

    def evaluate(
        self,
        condition_expr: str | None,
        records: list[dict[str, Any]],
        previous_records: list[dict[str, Any]] | None = None,
        baseline_metrics: dict[str, float] | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluates a condition string against extracted records with historical comparison support.
        Returns: (condition_met: bool, message: str)
        """
        if not condition_expr or not condition_expr.strip():
            return False, "No condition specified"

        if not records:
            return False, "No extracted records to evaluate against condition"

        expr = condition_expr.strip()

        # 1. Historical Relative Percentage Shifts:
        # e.g., "salary drops by 10%", "lowest price drops by 10%", "rent increases by 5%", "drops by 10%"
        shift_match = re.search(
            r"(?:(?P<field>[a-zA-Z0-9_]+)\s+)?(?:drops?|decreases?|falls?|down|increases?|rises?|up|changes?)\s*(?:by|>=|>|<=|<)?\s*(?P<pct>[0-9.]+)\s*%?",
            expr,
            re.IGNORECASE,
        )
        if shift_match:
            is_increase = bool(re.search(r"increase|rise|up", expr, re.IGNORECASE))
            target_pct = float(shift_match.group("pct"))
            specified_field = shift_match.group("field")

            target_field = specified_field if specified_field and specified_field.lower() not in {"lowest", "highest", "average", "total"} else None

            if not target_field:
                target_field = self._discover_primary_numeric_field(records)

            if not target_field:
                return False, f"Could not determine target numeric field for condition '{expr}'"

            curr_values = self._extract_numeric_values(records, target_field)
            if not curr_values:
                return False, f"Could not extract numeric values for '{target_field}' from current records."

            curr_stat = min(curr_values) if not is_increase else max(curr_values)

            # Resolve historical baseline from baseline_metrics cache or previous_records
            prev_stat: float | None = None
            if baseline_metrics:
                metric_key = f"{target_field}_{'max' if is_increase else 'min'}"
                if metric_key in baseline_metrics:
                    prev_stat = baseline_metrics[metric_key]
                elif f"{target_field}_avg" in baseline_metrics:
                    prev_stat = baseline_metrics[f"{target_field}_avg"]

            if prev_stat is None and previous_records:
                prev_values = self._extract_numeric_values(previous_records, target_field)
                if prev_values:
                    prev_stat = min(prev_values) if not is_increase else max(prev_values)

            if prev_stat is None:
                return False, f"First run: no historical baseline available to compute {target_pct}% delta on '{target_field}'."

            if prev_stat <= 0:
                return False, f"Previous baseline for '{target_field}' was non-positive ({prev_stat})."

            actual_pct_change = ((curr_stat - prev_stat) / prev_stat) * 100.0 if is_increase else ((prev_stat - curr_stat) / prev_stat) * 100.0

            if actual_pct_change >= target_pct:
                direction_str = "increased" if is_increase else "dropped"
                return (
                    True,
                    f"Metric '{target_field}' {direction_str} by {actual_pct_change:.1f}% (from {prev_stat:.2f} to {curr_stat:.2f}, target: >= {target_pct}%)",
                )
            else:
                return (
                    False,
                    f"Metric '{target_field}' delta: {actual_pct_change:+.1f}% (current: {curr_stat:.2f} vs prev: {prev_stat:.2f}, target: >= {target_pct}%)",
                )


        # 2. Aggregations: min(field), max(field), avg(field), count()
        agg_match = re.match(
            r"^(?P<func>min|max|avg|count)\((?P<field>[a-zA-Z0-9_]*)\)\s*(?P<op><=|>=|<|>|==|!=)\s*(?P<val>[0-9.]+)",
            expr,
            re.IGNORECASE,
        )
        if agg_match:
            func = agg_match.group("func").lower()
            field_name = agg_match.group("field") or self._discover_primary_numeric_field(records) or "item"
            op = agg_match.group("op")
            target_val = float(agg_match.group("val"))

            if func == "count":
                actual_val = float(len(records))
            else:
                values = self._extract_numeric_values(records, field_name)
                if not values:
                    return False, f"Could not extract numeric values for field '{field_name}'"
                if func == "min":
                    actual_val = min(values)
                elif func == "max":
                    actual_val = max(values)
                elif func == "avg":
                    actual_val = sum(values) / len(values)
                else:
                    actual_val = 0.0

            matched = self._compare_numeric(actual_val, op, target_val)
            msg = f"Aggregation {func}({field_name}) = {actual_val} vs target {op} {target_val} -> Matched: {matched}"
            return matched, msg

        # 3. Categorical string equality: field == 'value' or field != 'value'
        cat_match = re.match(
            r"^([a-zA-Z0-9_]+)\s*(==|!=)\s*['\"]([^'\"]+)['\"]", expr, re.IGNORECASE
        )
        if cat_match:
            field_name, op, target_str = cat_match.groups()
            matching_records = []
            for r in records:
                data = self._extract_data(r)
                val = str(data.get(field_name, "")).strip().lower()
                target_cmp = target_str.strip().lower()
                is_match = (val == target_cmp) if op == "==" else (val != target_cmp)
                if is_match:
                    matching_records.append(r.get("url") if isinstance(r, dict) else "")

            if matching_records:
                return True, f"Found {len(matching_records)} record(s) matching '{field_name} {op} \"{target_str}\"'"
            else:
                return False, f"No records satisfied categorical condition '{expr}'"

        # 4. Simple numeric field comparison: field < value (matches if ANY record satisfies)
        simple_match = re.match(
            r"^([a-zA-Z0-9_]+)\s*(<=|>=|<|>|==|!=)\s*([0-9.]+)", expr
        )
        if simple_match:
            field_name, op, target_str = simple_match.groups()
            target_val = float(target_str)
            matching_records = []
            for r in records:
                data = self._extract_data(r)
                v = data.get(field_name)
                if v is not None:
                    try:
                        num = float(v)
                        if self._compare_numeric(num, op, target_val):
                            matching_records.append((r.get("url") if isinstance(r, dict) else "", num))
                    except (ValueError, TypeError):
                        pass

            if matching_records:
                sample_url, sample_val = matching_records[0]
                msg = f"Found {len(matching_records)} record(s) satisfying '{field_name} {op} {target_val}' (e.g. {sample_val} at {sample_url})"
                return True, msg
            else:
                return False, f"No records satisfied condition '{expr}'"

        return False, f"Unsupported condition format: '{expr}'"

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

    def _discover_primary_numeric_field(self, records: list[dict[str, Any]]) -> str | None:
        """Dynamically identifies the primary numeric field present across extracted data payloads."""
        if not records:
            return None
        candidate_counts: dict[str, int] = {}
        for r in records:
            data = self._extract_data(r)
            for k, v in data.items():
                if v is not None and not isinstance(v, bool):
                    try:
                        float(v)
                        candidate_counts[k] = candidate_counts.get(k, 0) + 1
                    except (ValueError, TypeError):
                        pass

        if not candidate_counts:
            return None

        # Return the numeric field appearing most frequently across records
        return max(candidate_counts, key=lambda k: candidate_counts[k])

    def _extract_numeric_values(self, records: list[dict[str, Any]], field: str) -> list[float]:
        values: list[float] = []
        for r in records:
            data = self._extract_data(r)
            v = data.get(field)
            if v is not None and not isinstance(v, bool):
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass
        return values

    def _compare_numeric(self, actual: float, op: str, target: float) -> bool:
        if op == "<":
            return actual < target
        if op == "<=":
            return actual <= target
        if op == ">":
            return actual > target
        if op == ">=":
            return actual >= target
        if op == "==":
            return actual == target
        if op == "!=":
            return actual != target
        return False
