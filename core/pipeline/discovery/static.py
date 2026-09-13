import re
from core.models.execution_plan import ExecutionPlan
from core.pipeline.discovery.source_resolver import normalize_source_hint


class StaticDiscovery:
    """Discovery strategy for explicit target URLs provided directly in plan."""

    async def discover(self, plan: ExecutionPlan, max_results: int = 10) -> list[str]:
        direct_urls: list[str] = []
        seen = set()

        # 1. Inspect source_hints for explicit URLs
        for h in plan.source_hints:
            norm = normalize_source_hint(h)
            if norm.startswith(("http://", "https://")):
                if norm not in seen:
                    seen.add(norm)
                    direct_urls.append(norm)

        # 2. Inspect search_query if it is or contains a direct URL
        if plan.search_query:
            sq = plan.search_query.strip()
            if sq.startswith(("http://", "https://")):
                clean = sq.split()[0]
                if clean not in seen:
                    seen.add(clean)
                    direct_urls.append(clean)
            else:
                found = re.findall(r'https?://[^\s,\)\]]+', sq)
                for u in found:
                    clean = u.rstrip(".,;!?:")
                    if clean not in seen:
                        seen.add(clean)
                        direct_urls.append(clean)

        # 3. Inspect objective if it contains direct URLs
        if plan.objective:
            found = re.findall(r'https?://[^\s,\)\]]+', plan.objective)
            for u in found:
                clean = u.rstrip(".,;!?:")
                if clean not in seen:
                    seen.add(clean)
                    direct_urls.append(clean)

        return direct_urls[:max_results]

