import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.models.execution_plan import ExecutionPlan
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
    is_url_matching_sources,
    normalize_source_hint,
)
from core.pipeline.discovery.static import StaticDiscovery
from core.pipeline.retrieval.link_extractor import LinkExtractor


def test_normalize_source_hint_dynamic():
    assert normalize_source_hint("huggingface.co") == "huggingface.co"
    assert normalize_source_hint("github.com") == "github.com"
    assert normalize_source_hint("greenhouse.io") == "greenhouse.io"
    assert normalize_source_hint("https://huggingface.co/datasets/imdb") == "https://huggingface.co/datasets/imdb"
    assert normalize_source_hint("huggingface.co/datasets/imdb") == "https://huggingface.co/datasets/imdb"
    assert normalize_source_hint("news.ycombinator.com") == "news.ycombinator.com"


def test_extract_domain():
    assert extract_domain("huggingface.co") == "huggingface.co"
    assert extract_domain("https://huggingface.co/datasets/imdb") == "huggingface.co"
    assert extract_domain("https://sub.github.com/repo") == "sub.github.com"
    assert extract_domain("arxiv.org") == "arxiv.org"


def test_extract_domains_from_hints():
    hints = ["huggingface.co", "https://github.com/trending", "huggingface.co", "kaggle.com"]
    domains = extract_domains_from_hints(hints)
    assert domains == ["huggingface.co", "github.com", "kaggle.com"]


def test_build_scoped_search_query():
    # Single platform hint
    q1 = build_scoped_search_query("latest ml datasets", ["huggingface.co"])
    assert q1 == "site:huggingface.co latest ml datasets"

    # Multiple platform hints
    q2 = build_scoped_search_query("fine-tuned models", ["huggingface.co", "github.com"])
    assert q2 == "(site:huggingface.co OR site:github.com) fine-tuned models"

    # Already has site: in query
    q3 = build_scoped_search_query("site:arxiv.org transformer papers", ["huggingface.co"])
    assert q3 == "site:arxiv.org transformer papers"

    # Empty source hints
    q4 = build_scoped_search_query("python dev jobs", [])
    assert q4 == "python dev jobs"


def test_is_url_matching_sources_and_filtering():
    sources = ["huggingface.co", "https://github.com/awesome"]

    # Hugging Face match
    assert is_url_matching_sources("https://huggingface.co/datasets/squad", sources) is True
    # Subdomain match
    assert is_url_matching_sources("https://discuss.huggingface.co/t/topic", sources) is True
    # Specific GitHub match
    assert is_url_matching_sources("https://github.com/awesome/repo", sources) is True
    # Non-matching domain
    assert is_url_matching_sources("https://medium.com/@user/article", sources) is False
    assert is_url_matching_sources("https://forbes.com/article", sources) is False

    urls = [
        "https://huggingface.co/datasets/squad",
        "https://medium.com/post",
        "https://huggingface.co/models/llama",
        "https://randomblog.com/123",
    ]
    filtered = filter_urls_by_sources(urls, ["huggingface.co"])
    assert filtered == [
        "https://huggingface.co/datasets/squad",
        "https://huggingface.co/models/llama",
    ]


def test_extract_sources_from_goal():
    # Goal with explicit domain
    g1 = "check for the latest ml dataset from huggingface.co"
    assert "huggingface.co" in extract_sources_from_goal(g1)

    # Goal with direct URL
    g2 = "scrape data from https://huggingface.co/datasets and extract titles"
    extracted_g2 = extract_sources_from_goal(g2)
    assert "https://huggingface.co/datasets" in extracted_g2

    # Goal with multiple domains
    g3 = "find trending repos on github.com and datasets on kaggle.com"
    extracted_g3 = extract_sources_from_goal(g3)
    assert "github.com" in extracted_g3
    assert "kaggle.com" in extracted_g3

    # Goal with standalone domain
    g4 = "find software jobs on greenhouse.io"
    assert "greenhouse.io" in extract_sources_from_goal(g4)


@pytest.mark.asyncio
async def test_static_discovery_with_direct_urls():
    sd = StaticDiscovery()

    # Plan with source_hints URL
    plan1 = ExecutionPlan(
        objective="Scrape datasets",
        search_query="datasets",
        source_hints=["https://huggingface.co/datasets/squad", "https://huggingface.co/datasets/imdb"],
    )
    res1 = await sd.discover(plan1)
    assert res1 == ["https://huggingface.co/datasets/squad", "https://huggingface.co/datasets/imdb"]

    # Plan with URL directly in search_query
    plan2 = ExecutionPlan(
        objective="Extract prices",
        search_query="https://cloud.google.com/pricing",
    )
    res2 = await sd.discover(plan2)
    assert res2 == ["https://cloud.google.com/pricing"]

    # Plan with no direct URLs (domain only)
    plan3 = ExecutionPlan(
        objective="Search huggingface for models",
        search_query="models",
        source_hints=["huggingface.co"],
    )
    res3 = await sd.discover(plan3)
    assert res3 == []


@pytest.mark.asyncio
async def test_search_engine_discovery_strictly_scopes_sources():
    discovery = SearchEngineDiscovery()
    discovery.settings.search_engine_api_key = "test-api-key"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organic_results": [
            {"link": "https://huggingface.co/datasets/glue"},
            {"link": "https://medium.com/ml/best-datasets"},  # Should be filtered out
            {"link": "https://huggingface.co/datasets/squad"},
            {"link": "https://forbes.com/article"},           # Should be filtered out
        ]
    }

    plan = ExecutionPlan(
        objective="Check latest ml dataset from huggingface",
        search_query="latest ml dataset",
        source_hints=["huggingface.co"],
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        urls = await discovery.discover(plan, max_results=5)

        # Verify query was scoped with site:huggingface.co
        call_params = mock_get.call_args[1]["params"]
        assert "site:huggingface.co" in call_params["q"]

        # Verify results ONLY contain huggingface links
        assert urls == [
            "https://huggingface.co/datasets/glue",
            "https://huggingface.co/datasets/squad",
        ]


@pytest.mark.asyncio
async def test_open_search_discovery_strictly_scopes_sources():
    discovery = OpenWebSearchDiscovery()

    html_content = """
    <html>
      <a class="result__url" href="https://huggingface.co/datasets/common_voice">HuggingFace Dataset</a>
      <a class="result__url" href="https://random-blog.com/post">Random Post</a>
      <a class="result__url" href="https://huggingface.co/datasets/c4">HuggingFace C4</a>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_content

    plan = ExecutionPlan(
        objective="Check latest datasets from huggingface",
        search_query="latest datasets",
        source_hints=["huggingface.co"],
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        urls = await discovery.discover(plan, max_results=5)

        # Verify query had site: filter
        call_data = mock_post.call_args[1]["data"]
        assert "site:huggingface.co" in call_data["q"]

        # Verify only HuggingFace links were returned
        assert urls == [
            "https://huggingface.co/datasets/common_voice",
            "https://huggingface.co/datasets/c4",
        ]


def test_link_extractor_dataset_and_model_patterns():
    extractor = LinkExtractor()
    markdown = """
    # Hugging Face Datasets Hub
    - [SQuAD Dataset](/datasets/rajpurkar/squad)
    - [Common Voice](/datasets/mozilla-foundation/common_voice_11_0)
    - [Llama-3-8B](/models/meta-llama/Meta-Llama-3-8B)
    - [External Paper](https://arxiv.org/abs/2104.08691)
    - [Terms of Service](/terms)
    """

    child_links = extractor.extract_child_links("https://huggingface.co/datasets", markdown)
    assert len(child_links) >= 3
    assert "https://huggingface.co/datasets/rajpurkar/squad" in child_links
    assert "https://huggingface.co/datasets/mozilla-foundation/common_voice_11_0" in child_links
    assert "https://huggingface.co/models/meta-llama/Meta-Llama-3-8B" in child_links
    # External domain (arxiv.org) should NOT be in child links because base_domain is huggingface.co
    assert not any("arxiv.org" in l for l in child_links)


@pytest.mark.asyncio
async def test_composite_discovery_prefers_direct_urls():
    comp = CompositeDiscovery()
    plan = ExecutionPlan(
        objective="Extract from dataset",
        search_query="https://huggingface.co/datasets/rajpurkar/squad",
        source_hints=["https://huggingface.co/datasets/rajpurkar/squad"],
    )
    urls = await comp.discover(plan)
    assert urls == ["https://huggingface.co/datasets/rajpurkar/squad"]


@pytest.mark.asyncio
async def test_goal_interpreter_source_hints_handling():
    from core.agent.interpreter import GoalInterpreter

    mock_llm = MagicMock()
    mock_llm.call_json = AsyncMock(return_value={
        "objective": "Check latest ML datasets from Hugging Face",
        "domain": "research",
        "search_query": "latest ml datasets",
        "source_hints": ["huggingface.co"],
        "extraction_schema": {
            "entity_name": "dataset",
            "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "downloads", "type": "number", "required": False},
            ],
        },
    })

    interpreter = GoalInterpreter(llm_client=mock_llm)
    plan = await interpreter.interpret("check for the latest ml dataset from huggingface.co")

    assert "huggingface.co" in plan.source_hints
    assert plan.extraction_schema.entity_name == "dataset"


def test_interleave_source_results():
    from core.pipeline.discovery.source_resolver import interleave_source_results

    github_links = ["https://github.com/1", "https://github.com/2", "https://github.com/3"]
    gitlab_links = ["https://gitlab.com/1", "https://gitlab.com/2"]
    hf_links = ["https://huggingface.co/1", "https://huggingface.co/2", "https://huggingface.co/3"]

    interleaved = interleave_source_results([github_links, gitlab_links, hf_links], max_results=6)
    assert interleaved == [
        "https://github.com/1",
        "https://gitlab.com/1",
        "https://huggingface.co/1",
        "https://github.com/2",
        "https://gitlab.com/2",
        "https://huggingface.co/2",
    ]


@pytest.mark.asyncio
async def test_search_engine_multi_source_parallel_discovery():
    discovery = SearchEngineDiscovery()
    discovery.settings.search_engine_api_key = "test-key"

    plan = ExecutionPlan(
        objective="Check github, gitlab, and hugging face",
        search_query="llama fine-tune",
        source_hints=["github.com", "gitlab.com", "huggingface.co"],
    )

    def fake_search(query, domain=None, country_code=None, max_results=10):
        if domain == "github.com":
            return ["https://github.com/a", "https://github.com/b"]
        elif domain == "gitlab.com":
            return ["https://gitlab.com/c", "https://gitlab.com/d"]
        elif domain == "huggingface.co":
            return ["https://huggingface.co/e", "https://huggingface.co/f"]
        return []

    discovery._search_single_source = AsyncMock(side_effect=fake_search)

    results = await discovery.discover(plan, max_results=6)
    # Verify all three platforms are queried and results are interleaved fairly
    assert discovery._search_single_source.call_count == 3
    assert results == [
        "https://github.com/a",
        "https://gitlab.com/c",
        "https://huggingface.co/e",
        "https://github.com/b",
        "https://gitlab.com/d",
        "https://huggingface.co/f",
    ]


@pytest.mark.asyncio
async def test_open_search_multi_source_parallel_discovery():
    discovery = OpenWebSearchDiscovery()

    plan = ExecutionPlan(
        objective="Check github and gitlab",
        search_query="rust agent",
        source_hints=["github.com", "gitlab.com"],
    )

    def fake_search(query, domain=None, max_results=10):
        if domain == "github.com":
            return ["https://github.com/rust1"]
        elif domain == "gitlab.com":
            return ["https://gitlab.com/rust2"]
        return []

    discovery._search_single_source = AsyncMock(side_effect=fake_search)

    results = await discovery.discover(plan, max_results=4)
    assert discovery._search_single_source.call_count == 2
    assert results == ["https://github.com/rust1", "https://gitlab.com/rust2"]



