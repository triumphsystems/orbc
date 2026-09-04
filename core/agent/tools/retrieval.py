import logging
from strands import tool
from core.pipeline.retrieval.proxy import ProxyRetrieval

logger = logging.getLogger("core.agent.tools.retrieval")


@tool
async def retrieve_webpage_content(url: str) -> str:
    """
    Retrieves and cleans web page or document content from a target URL.
    Uses Orbit's proxy retrieval engine with SSRF validation, anti-bot bypass, and HTML-to-text cleanup.
    Handles HTML web pages, PDF documents, and academic preprints.

    Args:
        url: The target web URL or document link to retrieve.
    """
    logger.info("Strands tool retrieve_webpage_content: url='%s'", url)
    retrieval = ProxyRetrieval()
    content = await retrieval.retrieve_one(url=url)
    if not content or not content.strip():
        return f"Warning: No readable text content retrieved from {url}. Target may be blocked, require login, or be empty."
    # Truncate to safe token boundary for Strands agent loop
    return content[:25000]
