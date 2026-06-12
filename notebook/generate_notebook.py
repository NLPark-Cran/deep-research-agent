"""Generate the final_project.ipynb with pre-filled mock outputs."""

import os
import sys
import json
import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
from nbconvert.preprocessors import ExecutePreprocessor


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def build_notebook():
    nb = new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.13.5"},
    }

    # Section 1: Introduction
    nb.cells.append(new_markdown_cell("""# AI 课程期末大作业：Deep Research Agent

**作者**：Cran（杭州电子科技大学英语专业）

**项目地址**：`/root/workspace/test0607/final`

## 1. 项目简介

本作业使用 **LangGraph** 构建了一个深度研究助手 Agent。用户输入一个研究主题后，Agent 会自动完成：

1. **主题分析**（analyze_topic）：提炼研究问题与关键词。
2. **资料搜索**（research）：调用 `web_search` 工具实时搜索网络资料。
3. **大纲生成**（generate_outline）：基于主题与资料生成报告大纲。
4. **报告撰写**（draft_report）：根据大纲与资料撰写正文。
5. **质量反思**（reflect）：评估报告并给出改进意见。
6. **终稿输出**（finalize）：输出最终 Markdown / Word 报告。

其中 **reflect → draft_report** 构成条件循环边，最多迭代 1 次，形成逻辑闭环。

## 2. 技术栈

| 组件 | 版本/说明 |
|------|-----------|
| Python | 3.13 |
| LangGraph | 1.2.4 |
| langchain_openai | 1.3.0 |
| 云端模型 | kimi-k2.6 / qwen3.7-plus（通过环境变量切换） |
| 实时搜索 | DuckDuckGo / TokenDance UniFuncs web-search |
| Web UI | Gradio 6.18.0 |
| 文档导出 | python-docx 1.2.0 |

## 3. 作业要求对照

| 作业要求 | 本作业实现 |
|----------|------------|
| 使用 LangGraph | ✅ `agent/graph.py` 完整 StateGraph |
| 逻辑闭环 | ✅ 主题 → 搜索 → 大纲 → 起草 → 反思 → 终稿 |
| 云端大模型通信 | ✅ 通过 OpenAI 兼容接口调用云端模型 |
| ≥3 种 MessageState | ✅ HumanMessage / AIMessage / SystemMessage / ToolMessage |
| ≥4 个功能节点 | ✅ 6 个节点 |
| ≥1 条 Loop/Concurrency 边 | ✅ reflect → draft_report 条件循环 |
| 复杂度 ≥ Drafter Agent | ✅ 节点更多、流程更长、功能更完整 |
| .ipynb 展示执行结果 | ✅ 本 Notebook |
| Word 说明文档 | ✅ `docs/说明文档.docx` |
"""))

    # Section 4: Setup
    nb.cells.append(new_markdown_cell("""## 4. 环境安装

请先确保 `.env` 文件中已填入有效的 API Key（MOONSHOT_API_KEY 或 TOKENDANCE_API_KEY）。

> 当前 Notebook 使用 `MOCK_LLM=1` 模式运行，以便在无 API 额度时仍能展示完整的 Agent 结构与执行流程。实际运行时，取消该环境变量即可调用真实云端模型。
"""))

    nb.cells.append(new_code_cell("""# 安装依赖（如已安装可跳过）
# !pip install -r ../requirements.txt"""))

    nb.cells.append(new_code_cell("""import os
import sys
import json
from IPython.display import Markdown, display

# 将项目根目录加入路径
sys.path.insert(0, os.path.abspath('..'))

# 如需离线测试，可设置 MOCK_LLM=1；默认使用真实云端 API
# os.environ["MOCK_LLM"] = "1"
os.environ.setdefault("SEARCH_BACKEND", "duckduckgo")

from agent.graph import graph
from agent.export import markdown_to_docx"""))

    # Section 5: Graph visualization
    nb.cells.append(new_markdown_cell("## 5. 图结构可视化"))
    nb.cells.append(new_code_cell("print(graph.get_graph().draw_ascii())"))

    # Section 6: Run agent
    nb.cells.append(new_markdown_cell("""## 6. 运行 Agent

以下输入研究主题并执行完整研究流程。"""))

    nb.cells.append(new_code_cell(r"""TOPIC = "人工智能对英语专业翻译教育的影响"

initial_state = {
    "topic": TOPIC,
    "messages": [],
    "search_results": [],
    "iterations": 0,
}

final_state = None
for event in graph.stream(initial_state, stream_mode="values"):
    final_state = event
    print("Event keys:", list(event.keys()))
    if event.get("analysis"):
        print("主题分析完成")
    if event.get("search_results"):
        print(f"资料搜索完成，共 {len(event['search_results'])} 组")
    if event.get("outline"):
        print("大纲生成完成")
    if event.get("draft"):
        print(f"报告起草完成，长度 {len(event['draft'])} 字符")
    if event.get("reflection"):
        print(f"质量反思完成（迭代 {event.get('iterations', 0)}）")
    if event.get("final_report"):
        print("终稿输出完成")"""))

    # Subsections
    nb.cells.append(new_markdown_cell("### 6.1 主题分析"))
    nb.cells.append(new_code_cell("display(Markdown(final_state.get(\"analysis\", \"\")))"))

    nb.cells.append(new_markdown_cell("### 6.2 报告大纲"))
    nb.cells.append(new_code_cell("display(Markdown(final_state.get(\"outline\", \"\")))"))

    nb.cells.append(new_markdown_cell("### 6.3 质量反思"))
    nb.cells.append(new_code_cell("display(Markdown(final_state.get(\"reflection\", \"\")))"))

    nb.cells.append(new_markdown_cell("### 6.4 最终报告"))
    nb.cells.append(new_code_cell("""report = final_state.get("final_report", "")
display(Markdown(report))"""))

    nb.cells.append(new_markdown_cell("### 6.5 导出 Word 文档"))
    nb.cells.append(new_code_cell("""from datetime import datetime

docx_path = os.path.join("..", "output", f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
markdown_to_docx(report, docx_path, title=TOPIC)
print("Word 文档已保存到:", os.path.abspath(docx_path))"""))

    # Section 7: MessageState
    nb.cells.append(new_markdown_cell("""## 7. MessageState 示例

本 Agent 使用了 LangChain 的四种消息类型：

- `SystemMessage`：各节点的系统提示（如「你是研究助手」）。
- `HumanMessage`：用户输入与节点内的用户角色提示。
- `AIMessage`：模型输出（含 `tool_calls`）。
- `ToolMessage`：`web_search` 工具执行结果。

以下统计 Agent 运行结束后 state 中 `messages` 的类型分布。`SystemMessage` 在节点内部使用，但通常不追加到 state 的 messages 列表中。"""))

    nb.cells.append(new_code_cell("""from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

messages = final_state.get("messages", [])
type_counts = {"HumanMessage": 0, "AIMessage": 0, "SystemMessage": 0, "ToolMessage": 0}
for m in messages:
    if isinstance(m, HumanMessage):
        type_counts["HumanMessage"] += 1
    elif isinstance(m, AIMessage):
        type_counts["AIMessage"] += 1
    elif isinstance(m, SystemMessage):
        type_counts["SystemMessage"] += 1
    elif isinstance(m, ToolMessage):
        type_counts["ToolMessage"] += 1

print(json.dumps(type_counts, ensure_ascii=False, indent=2))"""))

    # Section 8: Web UI
    nb.cells.append(new_markdown_cell("""## 8. 启动 Web UI（Gradio 6.x）

运行以下代码可在本地启动 Gradio Web 界面："""))

    nb.cells.append(new_code_cell("""from app.main import build_ui

demo = build_ui()
demo.launch(share=False, inline=True)"""))

    # Section 9: Summary
    nb.cells.append(new_markdown_cell("""## 9. 总结

本作业实现了一个基于 LangGraph 的 Deep Research Agent，满足全部作业要求：

- 使用 LangGraph 构建完整的状态图。
- 与云端大模型通信（支持 Kimi / TokenDance，当前 Notebook 使用 Mock 模式演示）。
- 使用了 HumanMessage、AIMessage、SystemMessage、ToolMessage 四种消息类型。
- 包含 6 个功能节点和 1 条反思循环边。
- 复杂度明显高于参考的 Drafter Agent。
- 提供了 `.ipynb` 执行结果、Word 说明文档和技术调研笔记。
- 额外提供了基于 Gradio 6.x 的精美 Web UI，可上线部署。"""))

    return nb


def main():
    nb = build_notebook()
    nb_path = os.path.join(PROJECT_ROOT, "notebook", "final_project.ipynb")

    # By default run with real API; set MOCK_LLM=1 externally for offline testing.
    os.environ.setdefault("SEARCH_BACKEND", "duckduckgo")

    ep = ExecutePreprocessor(timeout=300, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": os.path.dirname(nb_path)}})

    with open(nb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Notebook saved to: {nb_path}")


if __name__ == "__main__":
    main()
