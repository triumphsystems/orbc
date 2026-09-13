import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from core.llm.base import LLMClient
from core.llm.factory import get_llm_client
from core.llm.prompts import GOAL_INTERPRETER_PROMPT
from core.models.execution_plan import (
    DynamicExtractionSchema,
    ExecutionPlan,
    ExtractionField,
    MissingParameter,
)


class GoalInterpreter:
    """Interprets natural language goals into structured domain-agnostic ExecutionPlans."""

    _llm: LLMClient | None

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def interpret_stream(self, goal: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Interprets natural language goals and yields progress reasoning events as the plan is synthesized.
        """
        yield {"event": "reasoning", "data": {"stage": "analyzing", "message": "Analyzing natural language objective..."}}
        await asyncio.sleep(0.05)

        yield {"event": "reasoning", "data": {"stage": "synthesizing", "message": "Querying LLM reasoning engine for schema and extraction rules..."}}
        raw = await self.llm.call_json(
            system_prompt=GOAL_INTERPRETER_PROMPT,
            user_prompt=f"USER GOAL: {goal}",
            temperature=0.0,
        )

        yield {"event": "reasoning", "data": {"stage": "validating", "message": "Validating entity schema, field types, and target adapters..."}}
        plan = self._build_plan_from_raw(raw, goal)

        yield {"event": "plan", "data": plan.model_dump()}

    async def interpret(self, goal: str) -> ExecutionPlan:
        raw = await self.llm.call_json(
            system_prompt=GOAL_INTERPRETER_PROMPT,
            user_prompt=f"USER GOAL: {goal}",
            temperature=0.0,
        )
        return self._build_plan_from_raw(raw, goal)

    def _build_plan_from_raw(self, raw: dict[str, Any], goal: str) -> ExecutionPlan:
        # Parse dynamic extraction schema
        schema_raw = raw.get("extraction_schema", {})
        fields = [
            ExtractionField(
                name=f.get("name"),
                type=f.get("type", "string"),
                description=f.get("description", ""),
                required=f.get("required", False),
                enum_values=f.get("enum_values"),
            )
            for f in schema_raw.get("fields", [])
            if f.get("name")
        ]

        # Ensure a fallback identifier field exists if LLM didn't define any
        if not fields:
            fields = [
                ExtractionField(name="title", type="string", description="Name or title of the item", required=True),
                ExtractionField(name="details", type="string", description="Key details or metrics", required=False),
            ]

        dynamic_schema = DynamicExtractionSchema(
            entity_name=schema_raw.get("entity_name", "item"),
            description=schema_raw.get("description"),
            fields=fields,
        )

        # Parse workflow DAG nodes
        workflow_nodes = raw.get("workflow_nodes", [])
        if not workflow_nodes:
            workflow_nodes = [
                {
                    "typeId": "trigger_cron",
                    "label": "Schedule Trigger",
                    "category": "trigger",
                    "adapterType": "managed",
                    "config": {
                        "frequency": raw.get("frequency", "once"),
                        "schedule_time": raw.get("schedule_time", "08:00"),
                        "timezone": raw.get("timezone", "UTC"),
                    },
                },
                {
                    "typeId": "proxy_discovery",
                    "label": "Source Discovery",
                    "category": "discovery",
                    "adapterType": "managed",
                    "config": {"search_query": raw.get("search_query", goal)},
                },
                {
                    "typeId": "schema_extractor",
                    "label": "LLM Schema Extraction",
                    "category": "extraction",
                    "adapterType": "managed",
                    "config": {"entity_name": schema_raw.get("entity_name", "item")},
                },
            ]
            if raw.get("notification_channel") == "email" or "email" in goal.lower():
                workflow_nodes.append({
                    "typeId": "email_alert",
                    "label": "Email Notifications",
                    "category": "notify",
                    "adapterType": "custom",
                    "config": {"recipient_email": ""},
                })
            if "database" in goal.lower() or "postgres" in goal.lower() or "sql" in goal.lower():
                workflow_nodes.append({
                    "typeId": "sql_database",
                    "label": "Database",
                    "category": "storage",
                    "adapterType": "custom",
                    "config": {"database_url": "", "table_name": f"extracted_{schema_raw.get('entity_name', 'items')}"},
                })

        # Parse missing parameters
        missing_params_raw = raw.get("missing_parameters", [])
        missing_parameters = []
        for p in missing_params_raw:
            if isinstance(p, dict) and p.get("parameter_name"):
                from core.models.execution_plan import MissingParameter
                missing_parameters.append(
                    MissingParameter(
                        node_id=p.get("node_id", ""),
                        adapter_type=p.get("adapter_type", "custom"),
                        parameter_name=p.get("parameter_name"),
                        label=p.get("label", p.get("parameter_name", "").replace("_", " ").title()),
                        prompt=p.get("prompt", f"Please provide {p.get('parameter_name')}"),
                        default_value=p.get("default_value"),
                        required=p.get("required", True),
                    )
                )

        # Fallback check for missing email address if email adapter is present but no email was in goal
        has_email_node = any(n.get("typeId") == "email_alert" for n in workflow_nodes)
        has_email_param = any(p.parameter_name == "recipient_email" for p in missing_parameters)
        if has_email_node and not has_email_param and "@" not in goal:
            from core.models.execution_plan import MissingParameter
            missing_parameters.append(
                MissingParameter(
                    node_id="email_alert",
                    adapter_type="email_alert",
                    parameter_name="recipient_email",
                    label="Recipient Email Address",
                    prompt="What email address should Orbit send notifications and reports to?",
                    default_value=None,
                    required=True,
                )
            )

        # Merge and normalize source hints from LLM and deterministic goal inspection
        from core.pipeline.discovery.source_resolver import (
            extract_sources_from_goal,
            normalize_source_hint,
        )

        llm_source_hints = raw.get("source_hints", [])
        deterministic_sources = extract_sources_from_goal(goal)

        merged_hints: list[str] = []
        seen_hints = set()

        for h in [*llm_source_hints, *deterministic_sources]:
            norm = normalize_source_hint(h)
            if norm and norm.lower() not in seen_hints:
                seen_hints.add(norm.lower())
                merged_hints.append(norm)

        return ExecutionPlan(
            objective=raw.get("objective", goal),
            domain=raw.get("domain", "general"),
            search_query=raw.get("search_query", goal),
            source_hints=merged_hints,
            geography=raw.get("geography"),
            country_code=raw.get("country_code"),
            extraction_schema=dynamic_schema,
            frequency=raw.get("frequency", "once"),
            schedule_time=raw.get("schedule_time"),
            timezone=raw.get("timezone", "UTC"),
            condition=raw.get("condition"),
            notification_channel=raw.get("notification_channel"),
            workflow_nodes=workflow_nodes,
            missing_parameters=missing_parameters,
        )

