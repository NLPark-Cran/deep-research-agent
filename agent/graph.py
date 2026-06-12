"""LangGraph state graph for the Deep Research Agent."""

from langgraph.graph import StateGraph, START, END

from agent.state import ResearchState
from agent.nodes import (
    analyze_topic,
    research,
    generate_outline,
    draft_report,
    reflect,
    finalize,
    should_continue,
    tools_node,
)


def build_graph() -> StateGraph:
    """Build and compile the research agent graph."""
    builder = StateGraph(ResearchState)

    # Add nodes
    builder.add_node("analyze_topic", analyze_topic)
    builder.add_node("research", research)
    builder.add_node("generate_outline", generate_outline)
    builder.add_node("draft_report", draft_report)
    builder.add_node("reflect", reflect)
    builder.add_node("finalize", finalize)
    builder.add_node("tools", tools_node)

    # Edges
    builder.add_edge(START, "analyze_topic")
    builder.add_edge("analyze_topic", "research")
    builder.add_edge("research", "generate_outline")
    builder.add_edge("generate_outline", "draft_report")
    builder.add_edge("draft_report", "reflect")

    # Conditional loop: reflect -> draft_report or finalize
    builder.add_conditional_edges(
        "reflect",
        should_continue,
        {
            "draft_report": "draft_report",
            "finalize": "finalize",
        },
    )

    builder.add_edge("finalize", END)

    return builder.compile()


# Global compiled graph instance
graph = build_graph()
