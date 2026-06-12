"""Mock LLM for offline testing and development.

Set MOCK_LLM=1 in the environment to use the mock LLM instead of calling
a real cloud API. This is useful for verifying the agent graph structure
and UI behavior without consuming API quota.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from typing import List, Optional


class MockChatModel(BaseChatModel):
    """A simple rule-based mock chat model for testing."""

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        system_text = str(messages[0].content).lower() if messages else ""

        # If the model is bound with tools and the prompt asks for web_search, return tool_calls
        if "web_search" in system_text and "web_search tool" in system_text:
            message = AIMessage(
                content="",
                tool_calls=[
                    {"id": "search_1", "name": "web_search", "args": {"query": "AI translation education impact", "count": 3}},
                    {"id": "search_2", "name": "web_search", "args": {"query": "人工智能 英语翻译 教学", "count": 3}},
                    {"id": "search_3", "name": "web_search", "args": {"query": "机器翻译 译者能力培养", "count": 3}},
                ],
            )
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

        content = self._reply(messages)
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _reply(self, messages: List[BaseMessage]) -> str:
        # Use the system prompt (first message) for intent detection
        system_text = str(messages[0].content).lower() if messages else ""
        all_text = "\n".join(str(m.content) for m in messages if hasattr(m, "content")).lower()

        # Strongest signal first: final editor / polish
        if "final editor" in system_text:
            return self._final_report()

        if "analyze a research topic" in system_text:
            return (
                "## 主题分析\n\n"
                "**核心研究问题**：\n"
                "1. 人工智能如何改变英语翻译教育的教学模式？\n"
                "2. AI 翻译工具对学生翻译能力培养有何影响？\n"
                "3. 未来英语专业翻译教育应如何与 AI 协同？\n\n"
                "**关键词**：人工智能、翻译教育、英语专业、神经网络机器翻译、CAT 工具、教学变革。\n\n"
                "**推荐搜索词**：AI translation education、机器翻译 英语教学、翻译技术 课程设计。"
            )
        elif "search strategist" in system_text:
            return "1. AI translation education impact\n2. 人工智能 英语翻译 教学\n3. 机器翻译 译者能力培养"
        elif "report outline" in system_text:
            return (
                "# 人工智能对英语专业翻译教育的影响\n\n"
                "## 摘要\n"
                "## 一、引言\n"
                "## 二、人工智能翻译技术概述\n"
                "### 2.1 机器翻译发展历程\n"
                "### 2.2 主流 AI 翻译工具\n"
                "## 三、AI 对翻译教育的积极影响\n"
                "### 3.1 提升教学效率\n"
                "### 3.2 丰富学习资源\n"
                "## 四、AI 带来的挑战与风险\n"
                "### 4.1 学生过度依赖\n"
                "### 4.2 译者主体性弱化\n"
                "## 五、未来展望与教学建议\n"
                "## 六、结论"
            )
        elif "critical reviewer" in system_text:
            return (
                "**质量反思**：\n"
                "- 优点：结构清晰，覆盖了技术、影响、挑战和展望。\n"
                "- 不足：案例分析较少，对英语教学具体课程设计的讨论不够深入。\n"
                "- 建议：补充 1-2 个高校翻译课程的实践案例，并增加对译者伦理的讨论。"
            )
        else:
            # Default fallback for ambiguous prompts: return full report
            return self._final_report()

    def _final_report(self) -> str:
            return (
                "# 人工智能对英语专业翻译教育的影响\n\n"
                "## 摘要\n\n"
                "随着神经网络机器翻译和生成式人工智能的快速发展，翻译行业与教育领域正经历深刻变革。 "
                "本文探讨了人工智能对英语专业翻译教学的积极与消极影响，并提出未来的教学转型建议。\n\n"
                "## 一、引言\n\n"
                "人工智能翻译工具（如 DeepL、Google Translate、ChatGPT）的准确性和流畅性显著提升， "
                "对传统翻译教育提出了新的挑战：英语专业学生是否仍需大量训练笔译技能？教师应如何调整课程？\n\n"
                "## 二、人工智能翻译技术概述\n\n"
                "### 2.1 机器翻译发展历程\n"
                "从基于规则到统计机器翻译，再到神经机器翻译和大型语言模型，翻译质量已接近甚至超越部分人工翻译。\n\n"
                "### 2.2 主流 AI 翻译工具\n"
                "DeepL、Google Translate、GPT-4、Kimi 等工具支持多语言、多领域翻译，并提供术语库、风格控制等功能。\n\n"
                "## 三、AI 对翻译教育的积极影响\n\n"
                "### 3.1 提升教学效率\n"
                "AI 可快速生成参考译文，帮助教师准备教学材料，并为学生提供即时反馈。\n\n"
                "### 3.2 丰富学习资源\n"
                "学生可借助 AI 接触海量平行文本和真实语料，拓展翻译视野。\n\n"
                "## 四、AI 带来的挑战与风险\n\n"
                "### 4.1 学生过度依赖\n"
                "部分学生可能直接复制 AI 译文，忽视译后编辑和批判性思维训练。\n\n"
                "### 4.2 译者主体性弱化\n"
                "长期依赖 AI 可能导致学生丧失独立翻译能力和语言敏感度。\n\n"
                "## 五、未来展望与教学建议\n\n"
                "未来翻译教育应从『教会翻译』转向『教会与 AI 协作翻译』，重点培养译后编辑、跨文化交际、 "
                "译者伦理和创造性表达能力。课程体系可增设 CAT 工具、提示工程、翻译项目管理等内容。\n\n"
                "## 六、结论\n\n"
                "人工智能既是翻译教育的挑战，也是转型的契机。英语专业应主动拥抱技术变革， "
                "在保持人文底蕴的同时提升学生的技术素养与综合能力。"
            )

    def bind_tools(self, tools, **kwargs):
        """Return self; mock model does not actually call tools."""
        return self

    @property
    def _llm_type(self) -> str:
        return "mock_chat_model"

    @property
    def _identifying_params(self) -> dict:
        return {"model": "mock"}
