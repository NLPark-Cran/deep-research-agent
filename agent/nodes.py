"""LangGraph nodes for the Deep Research Agent.

Each node selects the model best suited for its task:
- analyze_topic: qwen3.7-plus (general analysis and query generation)
- research: unifuncs-s3-pro (deep search specialist; falls back to qwen3.7-plus + DuckDuckGo)
- generate_outline / draft_report / reflect: qwen3.7-plus (fast, reliable)
- finalize: unifuncs-u3-pro (deep polish; falls back to qwen3.7-plus on timeout)
"""

import json
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agent.state import ResearchState
from agent.llm import get_llm
from agent.tools import tools, web_search_concurrent, search_single


# ToolNode executes tool calls produced by any model during the graph run.
tools_node = ToolNode(tools)

# Model assignments per node.
MODEL_ANALYZE = "qwen3.7-plus"
MODEL_RESEARCH = "unifuncs-s3-pro"
MODEL_OUTLINE = "qwen3.7-plus"
MODEL_DRAFT = "qwen3.7-plus"
MODEL_REFLECT = "qwen3.7-plus"
MODEL_FINALIZE = "unifuncs-u3-pro"


def analyze_topic(state: ResearchState) -> dict:
    """Analyze the user's topic and produce research questions + keywords."""
    topic = state["topic"]
    llm = get_llm(MODEL_ANALYZE)
    system = SystemMessage(
        content=(
            "You are an expert research assistant. Your job is to analyze a research topic "
            "and produce a concise analysis including: (1) core research questions, "
            "(2) key concepts/keywords, and (3) recommended search queries. "
            "Keep the output structured and under 400 words."
        )
    )
    user = HumanMessage(content=f"Please analyze this research topic: {topic}")
    response = llm.invoke([system, user])

    return {
        "messages": [user, response],
        "analysis": str(response.content),
    }


def _parse_queries(raw: str, fallback: str) -> list[str]:
    """Extract numbered/bulleted lines into clean search queries."""
    queries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove common leading markers like "1.", "-", "*", quotes
        cleaned = line.lstrip("0123456789.-*•\"'").strip()
        if cleaned:
            queries.append(cleaned)
    queries = [q for q in queries if len(q) > 3][:3]
    if len(queries) < 1:
        queries = [fallback, fallback + " analysis", fallback + " examples"]
    if len(queries) == 1:
        queries.append(fallback + " analysis")
    if len(queries) == 2:
        queries.append(fallback + " examples")
    return queries[:3]


def research(state: ResearchState) -> dict:
    """Conduct web research using multiple models.

    - unifuncs-s3-pro performs a deep search in parallel.
    - qwen3.7-plus generates queries for DuckDuckGo, which feeds downstream nodes.

    This guarantees that downstream outline/draft nodes receive safe, structured
    search results while still invoking the deep-search specialist.
    """
    topic = state["topic"]
    analysis = state.get("analysis", "")

    # Primary path: qwen3.7-plus queries + DuckDuckGo (fast and stable).
    query_llm = get_llm(MODEL_ANALYZE)
    query_system = SystemMessage(
        content=(
            "You are a search specialist. Based on the topic and analysis, "
            "produce exactly 3 diverse, high-quality web search queries. "
            "Each query should target a different angle of the topic. "
            "Return one query per line, no numbering or extra commentary."
        )
    )
    query_user = HumanMessage(
        content=f"Topic: {topic}\n\nAnalysis:\n{analysis}\n\nGenerate 3 search queries:"
    )
    query_response = query_llm.invoke([query_system, query_user])
    queries = _parse_queries(str(query_response.content), topic)
    results = web_search_concurrent(queries, count=3)
    for r in results:
        r["result"] = r["result"][:4000]

    messages = [query_user, query_response]

    # Parallel deep-search attempt with unifuncs-s3-pro (best-effort).
    deep_llm = get_llm(MODEL_RESEARCH, timeout=30)
    deep_system = SystemMessage(
        content=(
            "You are a deep search specialist (unifuncs-s3-pro). "
            "Conduct comprehensive web research on the given topic. "
            "Return a well-structured summary with key findings, facts, figures, "
            "and source URLs. Keep the summary thorough but under 2000 words."
        )
    )
    deep_user = HumanMessage(
        content=f"Topic: {topic}\n\nAnalysis:\n{analysis}\n\nProvide a comprehensive research summary:"
    )
    try:
        deep_response = deep_llm.invoke([deep_system, deep_user])
        messages.extend([deep_user, deep_response])
        # Append deep summary as an extra search result for richer context.
        results.append({"query": f"{topic} (deep search)", "result": str(deep_response.content)[:2000]})
    except Exception:
        # Deep search is best-effort; the DDGS results above are sufficient.
        pass

    tool_messages = [
        ToolMessage(content=json.dumps(r, ensure_ascii=False), tool_call_id=r["query"], name="web_search")
        for r in results
    ]

    return {
        "messages": messages + tool_messages,
        "search_results": results,
    }


def generate_outline(state: ResearchState) -> dict:
    """Generate a structured outline for the research report."""
    topic = state["topic"]
    analysis = state.get("analysis", "")
    search_results = state.get("search_results", [])
    llm = get_llm(MODEL_OUTLINE, temperature=0.5)

    context = "\n\n".join(r["result"] for r in search_results)[:8000]

    system = SystemMessage(
        content=(
            "You are an expert academic writer. Based on the topic, analysis, and search results, "
            "produce a clear, structured report outline in Markdown. "
            "Include: title, abstract, 3-5 main sections with subsections, and a conclusion. "
            "Output ONLY the outline."
        )
    )
    user = HumanMessage(
        content=f"Topic: {topic}\n\nAnalysis:\n{analysis}\n\nSearch Results:\n{context}\n\nGenerate outline:"
    )
    response = llm.invoke([system, user])

    return {
        "messages": [user, response],
        "outline": str(response.content),
    }


def draft_report(state: ResearchState) -> dict:
    """Draft the report based on the outline and search results."""
    topic = state["topic"]
    outline = state.get("outline", "")
    search_results = state.get("search_results", [])
    reflection = state.get("reflection", "")
    iterations = state.get("iterations", 0)
    llm = get_llm(MODEL_DRAFT, temperature=0.7)

    context = "\n\n".join(r["result"] for r in search_results)[:3000]

    system = SystemMessage(
        content=(
            "You are writing a concise research report in Markdown. "
            "Use the provided outline and search results. Cite sources naturally with URLs. "
            "Keep the report between 600-900 words. "
            "Output ONLY the report body, no extra commentary."
        )
    )

    if reflection and iterations > 0:
        user_text = (
            f"Topic: {topic}\n\n"
            f"Outline:\n{outline}\n\n"
            f"Previous Reflection:\n{reflection}\n\n"
            f"Search Results:\n{context[:3000]}\n\n"
            f"Please revise the report to address the reflection. Keep it concise."
        )
    else:
        user_text = (
            f"Topic: {topic}\n\n"
            f"Outline:\n{outline}\n\n"
            f"Search Results:\n{context[:3000]}\n\n"
            f"Write the concise report following the outline."
        )

    user = HumanMessage(content=user_text)
    response = llm.invoke([system, user])

    return {
        "messages": [user, response],
        "draft": str(response.content),
    }


def reflect(state: ResearchState) -> dict:
    """Critique the draft and decide whether to revise or finalize."""
    topic = state["topic"]
    draft = state.get("draft", "")
    outline = state.get("outline", "")
    iterations = state.get("iterations", 0)
    llm = get_llm(MODEL_REFLECT)

    system = SystemMessage(
        content=(
            "You are a critical reviewer. Evaluate the research report against the outline "
            "and topic. Identify strengths and weaknesses (coverage, accuracy, structure, sources). "
            "If the report is already good enough, say so explicitly. "
            "If it needs revision, list concrete, actionable improvements."
        )
    )
    user = HumanMessage(
        content=f"Topic: {topic}\n\nOutline:\n{outline}\n\nDraft Report:\n{draft}\n\nProvide critique:"
    )
    response = llm.invoke([system, user])

    reflection_text = str(response.content)

    return {
        "messages": [user, response],
        "reflection": reflection_text,
        "iterations": iterations + 1,
    }


def should_continue(state: ResearchState) -> Literal["draft_report", "finalize"]:
    """Conditional edge after reflection.

    The reflection node still runs and produces a critique, but we always move
    to finalize to keep end-to-end latency reasonable for the web UI. This
    preserves the reflection step in the graph while avoiding a second draft.
    """
    return "finalize"


def finalize(state: ResearchState) -> dict:
    """Polish the draft into the final report.

    Prefer unifuncs-u3-pro for deep polishing; fall back to qwen3.7-plus if it
    times out or fails.
    """
    topic = state["topic"]
    draft = state.get("draft", "")
    outline = state.get("outline", "")
    reflection = state.get("reflection", "")

    system = SystemMessage(
        content=(
            "You are a final editor. Polish the research report for clarity, consistency, "
            "and readability. Keep all factual content and citations. Output ONLY the final "
            "Markdown report with a title."
        )
    )
    user = HumanMessage(
        content=(
            f"Topic: {topic}\n\n"
            f"Outline:\n{outline}\n\n"
            f"Reflection (address if relevant):\n{reflection}\n\n"
            f"Draft:\n{draft}\n\n"
            f"Produce the final report:"
        )
    )

    try:
        llm = get_llm(MODEL_FINALIZE, timeout=30)
        response = llm.invoke([system, user])
    except Exception:
        llm = get_llm(MODEL_ANALYZE)
        response = llm.invoke([system, user])

    return {
        "messages": [user, response],
        "final_report": str(response.content),
    }
