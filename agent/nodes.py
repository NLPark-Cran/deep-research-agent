"""LangGraph nodes for the Deep Research Agent."""

from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agent.state import ResearchState
from agent.llm import get_llm
from agent.tools import tools, web_search_concurrent, search_single


llm = get_llm()
llm_with_tools = llm.bind_tools(tools)
tools_node = ToolNode(tools)


def analyze_topic(state: ResearchState) -> dict:
    """Analyze the user's topic and produce research questions + keywords."""
    topic = state["topic"]
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


def research(state: ResearchState) -> dict:
    """Use the LLM with web_search tool to gather sources for the report."""
    topic = state["topic"]
    analysis = state.get("analysis", "")

    system = SystemMessage(
        content=(
            "You are a research assistant with access to the web_search tool. "
            "Based on the topic and analysis, call web_search 3 times with different, "
            "high-quality search queries to gather diverse sources for a research report. "
            "Each query should target a different angle of the topic."
        )
    )
    user = HumanMessage(
        content=f"Topic: {topic}\n\nAnalysis:\n{analysis}\n\nSearch for relevant sources."
    )

    # LLM decides search queries and calls web_search tool
    response = llm_with_tools.invoke([system, user])

    tool_messages: list[ToolMessage] = []
    search_results: list[dict] = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "web_search":
                args = tc["args"]
                if isinstance(args, str):
                    import json
                    args = json.loads(args)
                query = args.get("query", topic)
                count = args.get("count", 3)
                observation = search_single(query, count=count)
                tool_messages.append(
                    ToolMessage(content=observation["result"], tool_call_id=tc["id"], name="web_search")
                )
                search_results.append(observation)
            else:
                tool_messages.append(
                    ToolMessage(content="Unknown tool", tool_call_id=tc["id"], name=tc["name"])
                )

    # If no tool calls were made, fall back to a direct search
    if not search_results:
        observation = search_single(topic, count=3)
        search_results.append(observation)

    # Truncate results to avoid overwhelming downstream LLM calls
    for r in search_results:
        r["result"] = r["result"][:4000]

    return {
        "messages": [user, response] + tool_messages,
        "search_results": search_results,
    }


def generate_outline(state: ResearchState) -> dict:
    """Generate a structured outline for the research report."""
    topic = state["topic"]
    analysis = state.get("analysis", "")
    search_results = state.get("search_results", [])

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

    context = "\n\n".join(r["result"] for r in search_results)[:10000]

    system = SystemMessage(
        content=(
            "You are writing a high-quality research report in Markdown. "
            "Use the provided outline and search results. Cite sources naturally with URLs. "
            "Be thorough but concise (around 800-1200 words). "
            "Output ONLY the report body, no extra commentary."
        )
    )

    if reflection and iterations > 0:
        user_text = (
            f"Topic: {topic}\n\n"
            f"Outline:\n{outline}\n\n"
            f"Previous Reflection:\n{reflection}\n\n"
            f"Search Results:\n{context[:15000]}\n\n"
            f"Please revise the report to address the reflection."
        )
    else:
        user_text = (
            f"Topic: {topic}\n\n"
            f"Outline:\n{outline}\n\n"
            f"Search Results:\n{context[:15000]}\n\n"
            f"Write the full report following the outline."
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
    # The decision is actually made by should_continue based on the reflection text.

    return {
        "messages": [user, response],
        "reflection": reflection_text,
        "iterations": iterations + 1,
    }


def should_continue(state: ResearchState) -> Literal["draft_report", "finalize"]:
    """Conditional edge after reflection."""
    iterations = state.get("iterations", 0)
    reflection = state.get("reflection", "")

    # Loop back at most once to keep runtime reasonable while satisfying the "loop" requirement.
    if iterations <= 1 and any(k in reflection.lower() for k in ["revise", "improve", "missing", "weakness", "should", "add"]):
        return "draft_report"
    return "finalize"


def finalize(state: ResearchState) -> dict:
    """Polish the draft into the final report."""
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
    response = llm.invoke([system, user])

    return {
        "messages": [user, response],
        "final_report": str(response.content),
    }
