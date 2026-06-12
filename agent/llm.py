"""LLM configuration supporting TokenDance and Moonshot (Kimi)."""

import os
from langchain_openai import ChatOpenAI

from agent.mock_llm import MockChatModel


def get_llm(model: str | None = None, temperature: float = 0.7, timeout: int | None = None):
    """Create a ChatOpenAI instance.

    Priority:
    1. If MOONSHOT_API_KEY is set, use Moonshot (Kimi) API.
    2. Else if TOKENDANCE_API_KEY is set, use TokenDance API.
    3. Otherwise raise an error.

    Args:
        model: Model ID. Defaults to env var or provider default.
        temperature: Sampling temperature.

    Returns:
        Configured ChatOpenAI instance.
    """
    if os.environ.get("MOCK_LLM") == "1":
        return MockChatModel()

    moonshot_key = os.environ.get("MOONSHOT_API_KEY")
    tokendance_key = os.environ.get("TOKENDANCE_API_KEY")

    if moonshot_key:
        base_url = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
        default_model = "kimi-k2.6"
        api_key = moonshot_key
    elif tokendance_key:
        base_url = os.environ.get("TOKENDANCE_BASE_URL", "https://tokendance.space/gateway/v1")
        default_model = "qwen3.7-plus"
        api_key = tokendance_key
    else:
        raise RuntimeError(
            "No API key found. Please set MOONSHOT_API_KEY or TOKENDANCE_API_KEY "
            "in your .env file."
        )

    model = model or os.environ.get("LLM_MODEL") or default_model

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout or int(os.environ.get("LLM_TIMEOUT_SECONDS", "300")),
        max_retries=1,
    )
