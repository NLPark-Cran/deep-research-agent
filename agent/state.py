"""Agent state definition for the Deep Research Agent."""

from typing import Annotated, List, Optional
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState


class ResearchState(MessagesState):
    """Extended state for the research agent.

    Inherits `messages` (list[AnyMessage]) with the `add_messages` reducer.
    """
    # User's research topic
    topic: str = ""

    # Analyzed research questions / keywords
    analysis: str = ""

    # Raw search results (list of {"title", "url", "snippet"})
    search_results: Annotated[List[dict], lambda x, y: x + y] = []

    # Generated report outline
    outline: str = ""

    # Current draft report
    draft: str = ""

    # Reflection / critique of the draft
    reflection: str = ""

    # Iteration counter for the reflection loop
    iterations: int = 0

    # Final report (Markdown)
    final_report: str = ""

    # Path to generated Word document
    report_path: str = ""
