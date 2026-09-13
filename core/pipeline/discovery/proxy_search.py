import asyncio
import re

import httpx

from core.config.settings import get_settings
from core.models.execution_plan import ExecutionPlan
from core.pipeline.discovery.source_resolver import (
    build_scoped_search_query,
    extract_domains_from_hints,
    filter_urls_by_sources,
    interleave_source_results,
)


class ProxySearchDiscovery:
    """Discovery strategy using proxy-routed search endpoint."""

    def __init__(self):
        self.settings = get_settings()

    async def discover(self, plan: ExecutionPlan, max_results: int = 10) -> list[str]:
        if not self.settings.retrieval_api_key or not self.settings.retrieval_zone:
            return []

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
        search_url = f"https://www.google.com/search?q={scoped_query}&num={max_results * 2}"

        headers = {
            "Authorization": f"Bearer {self.settings.retrieval_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "zone": self.settings.retrieval_zone,
            "url": search_url,
            "format": "raw",
            "data_format": "markdown",
        }
        if country_code:
            payload["country"] = country_code.lower()

        request_url = f"{self.settings.retrieval_base_url}/request"

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(request_url, headers=headers, json=payload)
                if resp.status_code != 200:
                    return []

                # Extract markdown links
                links = re.findall(r'\[.*?\]\((https?://[^\s\)]+)\)', resp.text)
                clean_links = [
                    l for l in links
                    if not any(ex in l for ex in ["google.com", "gstatic.com", "schema.org", "youtube.com"])
                ]

                seen = set()
                deduped: list[str] = []
                for l in clean_links:
                    if l not in seen:
                        seen.add(l)
                        deduped.append(l)

                if domain:
                    filtered = filter_urls_by_sources(deduped, [domain])
                    return filtered[:max_results]

                return deduped[:max_results]
        except Exception:  # noqa: BLE001
            return []


