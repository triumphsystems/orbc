from typing import Any

from core.models.execution_plan import ExecutionPlan


class SchemaValidator:
    """Validates extracted records dynamically against the ExecutionPlan's schema."""

    def validate(
        self, record: dict[str, Any], plan: ExecutionPlan
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []
        data = record.get("data", {})

        if not data or not isinstance(data, dict):
            return False, ["No structured data payload extracted"]

        schema = plan.extraction_schema

        # Check required fields
        for field in schema.fields:
            val = data.get(field.name)

            if field.required and (val is None or (isinstance(val, str) and not val.strip())):
                errors.append(f"Missing required field: '{field.name}'")
                continue

            if val is not None:
                # Type validation
                if field.type == "number":
                    try:
                        num = float(val)
                        desc = (field.description or "").lower()
                        if ("non-negative" in desc or "must be positive" in desc or ">= 0" in desc) and num < 0:
                            errors.append(f"Field '{field.name}' must be non-negative, got {num}")
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field.name}' expected number, got '{val}'")

                elif field.type == "boolean" and not isinstance(val, bool):
                    errors.append(f"Field '{field.name}' expected boolean, got '{val}'")

                # Enum validation
                if field.enum_values and str(val) not in field.enum_values:
                    errors.append(
                        f"Field '{field.name}' value '{val}' not in allowed values: {field.enum_values}"
                    )

        # Check URL presence
        if not record.get("url"):
            errors.append("Missing source URL")

        is_valid = len(errors) == 0
        return is_valid, errors
