import re
from urllib.parse import urlparse


def normalize_source_hint(hint: str) -> str:
    """
    Normalizes a user-provided source hint or URL into a clean URL or domain without any hardcoded platform names.
    Works purely via structural URL and domain analysis.
    """
    if not hint:
        return ""

    cleaned = hint.strip()

    # If it's already an explicit HTTP/HTTPS URL
    if cleaned.startswith(("http://", "https://")):
        return cleaned

    # If it looks like a domain with path (e.g., 'example.com/path', 'huggingface.co/datasets')
    if "/" in cleaned and not cleaned.startswith(("/", ".")):
        first_segment = cleaned.split("/")[0]
        # Check if first segment looks like a domain name (contains a dot and valid host characters)
        if re.match(r'^[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$', first_segment):
            return f"https://{cleaned}"

    # If it looks like a clean domain name (e.g., 'example.com', 'news.ycombinator.com')
    if re.match(r'^[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$', cleaned):
        return cleaned.lower()

    return cleaned


def extract_domain(hint_or_url: str) -> str:
    """
    Extracts the root/sub-domain hostname from any source hint or URL dynamically.
    """
    if not hint_or_url:
        return ""

    normalized = normalize_source_hint(hint_or_url)
    if normalized.startswith(("http://", "https://")):
        parsed = urlparse(normalized)
        return parsed.netloc.lower()

    if "/" in normalized:
        normalized = normalized.split("/")[0]

    return normalized.lower()


def extract_domains_from_hints(hints: list[str]) -> list[str]:
    """
    Extracts a deduplicated list of domain names from a list of source hints dynamically.
    """
    domains: list[str] = []
    seen = set()
    for h in hints:
        d = extract_domain(h)
        if d and d not in seen:
            seen.add(d)
            domains.append(d)
    return domains


def build_scoped_search_query(base_query: str, source_hints: list[str]) -> str:
    """
    Constructs an optimized search engine query incorporating site: scoping if source hints are specified.
    Works dynamically for any domain without hardcoded assumptions.
    """
    query = base_query.strip()
    if not source_hints:
        return query

    # If query already contains explicit site: filter, don't duplicate
    if "site:" in query.lower():
        return query

    domains = extract_domains_from_hints(source_hints)
    if not domains:
        return query

    if len(domains) == 1:
        site_filter = f"site:{domains[0]}"
    else:
        site_filter = f"({' OR '.join(f'site:{d}' for d in domains)})"

    return f"{site_filter} {query}".strip()


def is_url_matching_sources(url: str, source_hints: list[str]) -> bool:
    """
    Checks whether a discovered URL dynamically matches any requested source hints or domains.
    """
    if not source_hints:
        return True

    url_lower = url.lower()
    parsed = urlparse(url_lower)
    netloc = parsed.netloc

    for hint in source_hints:
        normalized = normalize_source_hint(hint).lower()

        # If hint is a specific URL prefix (e.g. 'https://example.com/datasets')
        if normalized.startswith(("http://", "https://")):
            if url_lower.startswith(normalized):
                return True
            # Also check domain match
            hint_domain = urlparse(normalized).netloc
            if hint_domain and (netloc == hint_domain or netloc.endswith(f".{hint_domain}")):
                return True

        # If hint is a domain (e.g. 'example.com')
        domain = extract_domain(hint)
        if domain:
            if netloc == domain or netloc.endswith(f".{domain}"):
                return True

    return False


def filter_urls_by_sources(urls: list[str], source_hints: list[str]) -> list[str]:
    """
    Strictly filters candidate URLs against source hints.
    """
    if not source_hints:
        return urls

    return [u for u in urls if is_url_matching_sources(u, source_hints)]


def extract_sources_from_goal(goal: str) -> list[str]:
    """
    Extracts direct URLs and fully qualified domain names dynamically from user goal text.
    Operates purely through structural regex and URL patterns with zero hardcoded website names.
    """
    sources: list[str] = []
    seen = set()

    # 1. Extract explicit HTTP/HTTPS URLs
    url_pattern = r'https?://[^\s,\)\]]+'
    found_urls = re.findall(url_pattern, goal)
    for u in found_urls:
        clean_u = u.rstrip(".,;!?:")
        if clean_u and clean_u not in seen:
            seen.add(clean_u)
            sources.append(clean_u)

    # 2. Extract standalone domain names (e.g. "greenhouse.io", "propertypro.ng", "huggingface.co", "news.ycombinator.com")
    domain_pattern = r'\b([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*\.(?:[a-zA-Z]{2,}))\b'
    found_domains = re.findall(domain_pattern, goal)
    for d in found_domains:
        d_lower = d.lower()
        if d_lower not in seen and not any(d_lower in u.lower() for u in sources):
            seen.add(d_lower)
            sources.append(d_lower)

    return sources


def interleave_source_results(source_results: list[list[str]], max_results: int = 10) -> list[str]:
    """
    Fairly merges results across multiple sources by interleaving items in round-robin fashion.
    Prevents a single high-ranking platform from starving other requested sources.
    """
    interleaved: list[str] = []
    seen = set()
    max_len = max((len(r) for r in source_results), default=0)

    for idx in range(max_len):
        for result_list in source_results:
            if idx < len(result_list):
                url = result_list[idx]
                if url and url not in seen:
                    seen.add(url)
                    interleaved.append(url)
                    if len(interleaved) >= max_results:
                        return interleaved

    return interleaved

