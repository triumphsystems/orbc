import asyncio
import httpx

from core.config.settings import get_settings
from core.models.execution_plan import ExecutionPlan
from core.pipeline.discovery.source_resolver import (
    build_scoped_search_query,
    extract_domains_from_hints,
    filter_urls_by_sources,
    interleave_source_results,
)


class SearchEngineDiscovery:
    """Domain-agnostic web source discovery using search engine API (SerpApi / Google)."""

    SEARCH_ENGINE_URL = "https://serpapi.com/search.json"

    def __init__(self):
        self.settings = get_settings()

    async def discover(self, plan: ExecutionPlan, max_results: int = 10) -> list[str]:
        if not self.settings.search_engine_api_key:
            raise ValueError("SEARCH_ENGINE_API_KEY is not configured in settings or environment.")

        domains = extract_domains_from_hints(plan.source_hints)

        # If multiple distinct domains requested (e.g. github.com, gitlab.com, huggingface.co),
        # query each domain concurrently and interleave results for balanced cross-platform coverage
        if len(domains) > 1:
            per_source_limit = max(3, (max_results // len(domains)) + 2)
            tasks = [
                self._search_single_source(
                    query=plan.search_query,
                    domain=d,
                    country_code=plan.country_code,
                    max_results=per_source_limit,
                )
                for d in domains
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_results = [r for r in results if isinstance(r, list)]
            return interleave_source_results(valid_results, max_results=max_results)

        # Single domain or open-web search
        single_domain = domains[0] if domains else None
        return await self._search_single_source(
            query=plan.search_query,
            domain=single_domain,
            country_code=plan.country_code,
            max_results=max_results,
        )

    async def _search_single_source(
        self,
        query: str,
        domain: str | None = None,
        country_code: str | None = None,
        max_results: int = 10,
    ) -> list[str]:
        scoped_query = build_scoped_search_query(query, [domain] if domain else [])

        params: dict[str, str | int] = {
            "engine": "google",
            "q": scoped_query,
            "num": max_results * 2,
            "api_key": self.settings.search_engine_api_key,
        }

        if country_code:
            params["gl"] = country_code.lower()
            params["hl"] = "en"

        endpoint = self.settings.search_engine_base_url or self.SEARCH_ENGINE_URL

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.get(endpoint, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as err:
            resp_err = getattr(err, "response", None)
            status = resp_err.status_code if resp_err is not None else None
            raise RuntimeError(f"Search API request failed (status: HTTP {status or 'error'})") from None

        raw_links: list[str] = []
        for item in data.get("organic_results", []):
            link = item.get("link")
            if link and link.startswith("http"):
                raw_links.append(link)

        # Deduplicate preserving order
        seen = set()
        deduped: list[str] = []
        for u in raw_links:
            if u not in seen:
                seen.add(u)
                deduped.append(u)

        if domain:
            filtered = filter_urls_by_sources(deduped, [domain])
            return filtered[:max_results]

        return deduped[:max_results]


