"""Tools for the Deep Research Agent.

Supports two search backends:
1. DuckDuckGo (free, default) — no API key required.
2. TokenDance UniFuncs web-search — requires TOKENDANCE_API_KEY and quota.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import requests
from langchain.tools import tool


_UNIFUNCS_SEARCH_URL = "https://tokendance.space/gateway/unifuncs/web-search"
_UNIFUNCS_READER_URL = "https://tokendance.space/gateway/unifuncs/web-reader"


def _get_tokendance_headers() -> Dict[str, str]:
    api_key = os.environ.get("TOKENDANCE_API_KEY")
    if not api_key:
        raise RuntimeError("TOKENDANCE_API_KEY is not set.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _search_tokendance(query: str, count: int) -> dict:
    """Execute a single TokenDance UniFuncs search."""
    count = max(1, min(50, count))
    try:
        resp = requests.post(
            _UNIFUNCS_SEARCH_URL,
            headers=_get_tokendance_headers(),
            json={"query": query, "count": count},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"query": query, "result": f"Search failed: {type(e).__name__}: {e}"}

    pages = data.get("data", {}).get("webPages", [])
    if not pages:
        return {"query": query, "result": "No search results found."}

    lines: List[str] = []
    for i, item in enumerate(pages, 1):
        title = item.get("name", "Untitled")
        url = item.get("url", "")
        snippet = item.get("snippet", "")
        summary = item.get("summary", "")
        lines.append(f"[{i}] {title}\nURL: {url}\nSnippet: {snippet or summary}\n")

    return {"query": query, "result": "\n".join(lines)}


def _search_duckduckgo(query: str, count: int) -> dict:
    """Execute a single DuckDuckGo search."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=count)
    except Exception as e:
        return {"query": query, "result": f"Search failed: {type(e).__name__}: {e}"}

    if not results:
        return {"query": query, "result": "No search results found."}

    lines: List[str] = []
    for i, item in enumerate(results, 1):
        title = item.get("title", "Untitled")
        url = item.get("href", "")
        snippet = item.get("body", "")
        lines.append(f"[{i}] {title}\nURL: {url}\nSnippet: {snippet}\n")

    return {"query": query, "result": "\n".join(lines)}


def search_single(query: str, count: int = 5, backend: str | None = None) -> dict:
    """Run a single search with the configured backend."""
    backend = backend or os.environ.get("SEARCH_BACKEND", "duckduckgo").lower()
    if backend == "tokendance":
        return _search_tokendance(query, count)
    return _search_duckduckgo(query, count)


@tool
def web_search(query: str, count: int = 5) -> str:
    """Search the web and return summarized results.

    Args:
        query: Search query string.
        count: Number of results to return (default 5).

    Returns:
        A formatted string containing search results with title, URL, and snippet.
    """
    result = search_single(query, count)
    return f"Query: {result['query']}\n{result['result']}"


@tool
def web_reader(url: str, lite_mode: bool = True, max_words: int = 50000) -> str:
    """Fetch and extract the content of a web page as Markdown.

    Args:
        url: Target URL to read.
        lite_mode: Whether to apply readability trimming (default True).
        max_words: Maximum characters to return (default 50000).

    Returns:
        Markdown content of the page or an error message.
    """
    try:
        resp = requests.post(
            _UNIFUNCS_READER_URL,
            headers=_get_tokendance_headers(),
            json={
                "url": url,
                "format": "md",
                "liteMode": lite_mode,
                "maxWords": max_words,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Failed to read {url}: {type(e).__name__}: {e}"


def web_search_concurrent(queries: List[str], count: int = 5) -> List[dict]:
    """Run multiple web searches concurrently (internal helper, not exposed as LLM tool).

    Args:
        queries: List of search query strings.
        count: Number of results per query.

    Returns:
        List of {"query", "result"} dicts.
    """
    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
        futures = {executor.submit(search_single, q, count): q for q in queries}
        for future in as_completed(futures):
            results.append(future.result())
    return results


tools = [web_search, web_reader]
