import asyncio
import logging
import re
from html import unescape
from typing import ClassVar

import httpx

from core.utils.security import safe_redirect_hook, validate_url_target

logger = logging.getLogger("core.pipeline.retrieval.direct")


class DirectHttpRetrieval:
    """Direct HTTP retrieval fallback for public/open endpoints with HTML-to-text cleanup."""

    CLEAN_RE_SCRIPT: ClassVar[re.Pattern] = re.compile(r"<(script|style|nav|footer|header|svg|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
    CLEAN_RE_TAGS: ClassVar[re.Pattern] = re.compile(r"<[^>]+>")
    CLEAN_RE_WHITESPACE: ClassVar[re.Pattern] = re.compile(r"\n\s*\n+")

    async def retrieve_one(self, url: str, country_code: str | None = None) -> str | None:
        # SSRF Protection: Validate target URL before making outbound connection
        is_safe, reason = validate_url_target(url, allow_private=False)
        if not is_safe:
            logger.warning("Direct HTTP retrieval blocked forbidden URL: %s (%s)", url, reason)
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                event_hooks={"response": [safe_redirect_hook]},
            ) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200 or not resp.text:
                    return None
                return self._html_to_markdown_summary(resp.text, base_url=url)
        except Exception as e:
            logger.debug("Direct retrieval failed for %s: %s", url, e)
            return None

    def _html_to_markdown_summary(self, html: str, base_url: str) -> str:
        """Converts raw HTML into clean readable text preserving links for extraction."""
        # 1. Remove non-content blocks
        cleaned = self.CLEAN_RE_SCRIPT.sub(" ", html)

        # 2. Convert links to markdown syntax [anchor](href)
        def replace_link(match):
            href = match.group(1)
            text = self.CLEAN_RE_TAGS.sub("", match.group(2)).strip()
            if text and len(text) > 3 and not href.startswith("#") and not href.startswith("javascript:"):
                return f" [{text}]({href}) "
            return text

        cleaned = re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', replace_link, cleaned, flags=re.IGNORECASE | re.DOTALL)

        # 3. Convert headings and list items to structured markdown
        cleaned = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n### \1\n\n', cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r'<li[^>]*>(.*?)</li>', r'\n* \1', cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n\n', cleaned, flags=re.IGNORECASE | re.DOTALL)

        # 4. Strip remaining HTML tags and unescape entities
        text = self.CLEAN_RE_TAGS.sub(" ", cleaned)
        text = unescape(text)
        text = self.CLEAN_RE_WHITESPACE.sub("\n\n", text).strip()
        return text[:30000]

    async def retrieve_many(
        self, urls: list[str], country_code: str | None = None, concurrency: int = 5
    ) -> dict[str, str | None]:
        semaphore = asyncio.Semaphore(concurrency)
        results: dict[str, str | None] = {}

        async def fetch(u: str):
            async with semaphore:
                content = await self.retrieve_one(u, country_code=country_code)
                results[u] = content

        await asyncio.gather(*(fetch(u) for u in urls))
        return results
