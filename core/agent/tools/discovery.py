import logging
from strands import tool
from core.pipeline.discovery.composite import CompositeDiscovery

logger = logging.getLogger("core.agent.tools.discovery")


@tool
async def search_web_sources(query: str, max_results: int = 8) -> list[str]:
    """
    Searches the web using Orbit's composite search discovery engine (Google, SearXNG, SerpAPI).
    Returns a list of candidate web URLs relevant to the search query.

    Args:
        query: Search query or topic to discover relevant web sources.
        max_results: Maximum number of search result URLs to return (default: 8).
    """
    logger.info("Strands tool search_web_sources: query='%s' (max=%d)", query, max_results)
    discovery = CompositeDiscovery()
    return await discovery.discover(query=query, max_results=max_results)
