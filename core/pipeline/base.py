from typing import Any, Protocol

from core.models.execution_plan import ExecutionPlan


class DiscoveryStrategy(Protocol):
    """Protocol for finding candidate web sources for an execution plan."""

    async def discover(self, plan: ExecutionPlan, max_results: int = 10) -> list[str]:
        ...


class RetrievalStrategy(Protocol):
    """Protocol for fetching web page content."""

    async def retrieve_one(self, url: str, country_code: str | None = None) -> str | None:
        ...

    async def retrieve_many(
        self, urls: list[str], country_code: str | None = None
    ) -> dict[str, str | None]:
        ...


class ExtractionStrategy(Protocol):
    """Protocol for extracting structured data from retrieved page markdown/HTML."""

    async def extract(
        self, url: str, content: str, plan: ExecutionPlan
    ) -> dict[str, Any]:
        ...


class ValidationStrategy(Protocol):
    """Protocol for validating extracted records against execution plan criteria."""

    def validate(
        self, record: dict[str, Any], plan: ExecutionPlan
    ) -> tuple[bool, list[str]]:
        ...
