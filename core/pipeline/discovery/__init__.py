from core.pipeline.discovery.composite import CompositeDiscovery
from core.pipeline.discovery.open_search import OpenWebSearchDiscovery
from core.pipeline.discovery.proxy_search import ProxySearchDiscovery
from core.pipeline.discovery.search_engine import SearchEngineDiscovery
from core.pipeline.discovery.source_resolver import (
    build_scoped_search_query,
    extract_domain,
    extract_domains_from_hints,
    extract_sources_from_goal,
    filter_urls_by_sources,
    interleave_source_results,
    is_url_matching_sources,
    normalize_source_hint,
)
from core.pipeline.discovery.static import StaticDiscovery

__all__ = [
    "CompositeDiscovery",
    "OpenWebSearchDiscovery",
    "ProxySearchDiscovery",
    "SearchEngineDiscovery",
    "StaticDiscovery",
    "build_scoped_search_query",
    "extract_domain",
    "extract_domains_from_hints",
    "extract_sources_from_goal",
    "filter_urls_by_sources",
    "interleave_source_results",
    "is_url_matching_sources",
    "normalize_source_hint",
]


