import re
from typing import ClassVar
from urllib.parse import urljoin, urlparse


class LinkExtractor:
    """Discovers child detail URLs from listing/catalog/search pages for 2-hop navigation."""

    # Keywords commonly found in product/job/dataset/paper/detail URLs
    DETAIL_PATTERNS: ClassVar[list[str]] = [
        r"/p/[a-zA-Z0-9_\-]+",             # e-commerce product
        r"/product/[a-zA-Z0-9_\-]+",       # product detail
        r"/item/[a-zA-Z0-9_\-]+",          # item detail
        r"/dp/[a-zA-Z0-9]+",               # Amazon detail page
        r"/jobs?/[a-zA-Z0-9_\-]+",         # job listing
        r"/property/[a-zA-Z0-9_\-]+",      # real estate property
        r"/listing/[a-zA-Z0-9_\-]+",       # general listing
        r"/datasets?/[a-zA-Z0-9_\-\./]+",  # ML dataset pages (e.g. HuggingFace, Kaggle)
        r"/models?/[a-zA-Z0-9_\-\./]+",    # ML model pages
        r"/abs/\d+\.\d+",                  # ArXiv abstract pages
        r"/papers?/[a-zA-Z0-9_\-\./]+",    # Academic papers
        r"/r/[a-zA-Z0-9_]+/comments/",     # Reddit discussion thread
        r"/posts?/[a-zA-Z0-9_\-]+",        # Blog or news post
        r"/articles?/[a-zA-Z0-9_\-]+",     # Article detail
        r"/[a-zA-Z0-9_\-]+\.html",         # specific html article/page
    ]

    def extract_child_links(
        self, base_url: str, markdown_content: str, max_links: int = 5
    ) -> list[str]:
        """Finds promising detail URLs from page markdown."""
        if not markdown_content:
            return []

        base_domain = urlparse(base_url).netloc

        # Extract markdown link targets [title](url)
        raw_links = re.findall(r'\[([^\]]+)\]\((https?://[^\s\)]+|/[^\s\)]+)\)', markdown_content)

        candidate_urls: list[str] = []
        for anchor_text, href in raw_links:
            # Resolve relative links
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Must stay on the same domain
            if parsed.netloc != base_domain:
                continue

            # Check if matches detail patterns or has informative slug
            if any(re.search(p, parsed.path, re.IGNORECASE) for p in self.DETAIL_PATTERNS) or len(parsed.path.strip("/").split("/")) >= 2 and len(anchor_text.strip()) > 10:
                candidate_urls.append(full_url)

        # Deduplicate
        seen = set()
        deduped: list[str] = []
        for u in candidate_urls:
            if u not in seen and u != base_url:
                seen.add(u)
                deduped.append(u)

        return deduped[:max_links]
