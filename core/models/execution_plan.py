from typing import Any

from pydantic import BaseModel, Field, model_validator

from core.models.enums import Frequency


class ExtractionField(BaseModel):
    """Definition of a single field to extract dynamically from web pages."""
    name: str = Field(..., description="Field identifier e.g. 'title', 'price', 'salary'")
    type: str = Field(default="string", description="Type: 'string', 'number', 'boolean', 'array', 'object'")
    description: str = Field(default="", description="Description of what to extract for this field")
    required: bool = Field(default=False, description="Whether this field must be present for a valid record")
    enum_values: list[str] | None = Field(default=None, description="Allowed values if categorical")


class DynamicExtractionSchema(BaseModel):
    """Dynamic schema produced by the Goal Interpreter tailored to the specific goal domain."""
    entity_name: str = Field(default="item", description="Entity name e.g. 'product', 'job_listing', 'flight', 'article'")
    fields: list[ExtractionField] = Field(default_factory=list)
    description: str | None = None

    def to_json_schema(self) -> dict[str, Any]:
        """Convert dynamic fields into a standard JSON Schema representation for LLM structured output."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for f in self.fields:
            prop: dict[str, Any] = {"type": f.type if f.type != "number" else ["number", "null"]}
            if f.description:
                prop["description"] = f.description
            if f.enum_values:
                prop["enum"] = f.enum_values
            properties[f.name] = prop
            if f.required:
                required.append(f.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class MissingParameter(BaseModel):
    """A parameter or credential needed for a workflow adapter that must be elicited from the user."""
    node_id: str = Field(default="")
    adapter_type: str = Field(..., description="e.g. 'email_alert', 'sql_database', 'slack_alert', 's3_storage'")
    parameter_name: str = Field(..., description="e.g. 'recipient_email', 'database_url', 'table_name', 'slack_webhook_url'")
    label: str = Field(..., description="Short label for UI input")
    prompt: str = Field(..., description="Question or prompt to ask the user")
    default_value: str | None = None
    required: bool = True


class ExecutionPlan(BaseModel):
    """The complete domain-agnostic execution plan produced by the Goal Interpreter."""
    objective: str = Field(default="", description="Concise summary of the goal")
    domain: str = Field(default="general", description="Identified domain: e.g. 'ecommerce', 'jobs', 'real_estate', 'travel', 'news', 'finance'")
    search_query: str = Field(default="", description="Optimized search query to find candidate sources")
    source_hints: list[str] = Field(default_factory=list, description="Target domain hints or specific URLs requested by user (empty for open web)")
    geography: str | None = Field(default=None, description="Target country or location (e.g. 'Nigeria', 'United States', 'Global')")
    country_code: str | None = Field(default=None, description="2-letter ISO country code for proxy routing if applicable (e.g. 'ng', 'us')")
    extraction_schema: DynamicExtractionSchema = Field(default_factory=DynamicExtractionSchema)
    frequency: Frequency = Field(default=Frequency.once)
    schedule_time: str | None = Field(default=None, description="Preferred execution time e.g. '08:00'")
    timezone: str = Field(default="UTC", description="Timezone name e.g. 'Africa/Lagos', 'UTC'")
    condition: str | None = Field(default=None, description="Alert or filter condition e.g. 'min(price) < 400000' or 'salary >= 120000'")
    notification_channel: str | None = Field(default=None, description="Notification target e.g. 'webhook', 'email', 'log'")
    workflow_nodes: list[dict[str, Any]] = Field(default_factory=list, description="Synthesized DAG nodes for execution pipeline")
    missing_parameters: list[MissingParameter] = Field(default_factory=list, description="Required settings/credentials to elicit from user")

    @model_validator(mode="before")
    @classmethod
    def _normalize_plan_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("search_query") and data.get("objective"):
                data["search_query"] = data["objective"]
            elif not data.get("objective") and data.get("search_query"):
                data["objective"] = data["search_query"]
        return data
