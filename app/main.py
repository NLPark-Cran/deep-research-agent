"""Gradio 6.x Web UI for the Deep Research Agent."""

import os
import sys
from datetime import datetime
from typing import Generator

from dotenv import load_dotenv

# Load environment variables before importing agent modules
load_dotenv()

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from agent.graph import graph
from agent.export import markdown_to_docx


THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="slate",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_50",
    block_background_fill="*neutral_100",
    block_border_width="1px",
    block_border_color="*neutral_200",
    button_primary_background_fill="*primary_600",
    button_primary_text_color="white",
)


def run_research_stream(
    topic: str,
) -> Generator[tuple[str, str, str | None], None, None]:
    """Run the research agent and stream updates to the Gradio UI.

    Yields (logs, final_report, docx_path).
    """
    if not topic or not topic.strip():
        yield "请输入研究主题。", "", None
        return

    topic = topic.strip()
    logs = f"# 研究主题\n\n{topic}\n\n---\n\n"

    initial_state = {
        "topic": topic,
        "messages": [],
        "search_results": [],
        "iterations": 0,
    }

    final_report = ""
    docx_path = None

    for update in graph.stream(initial_state, stream_mode="updates"):
        # Each update is {node_name: {state_updates}}
        for node_name, state_update in update.items():
            if node_name == "tools":
                continue

            if node_name == "analyze_topic" and state_update.get("analysis"):
                logs += "## 🔍 阶段 1：主题分析\n\n"
                logs += f"{state_update['analysis']}\n\n"

            elif node_name == "research" and state_update.get("search_results"):
                count = len(state_update["search_results"])
                logs += f"## 📚 阶段 2：资料搜索\n\n已完成 **{count}** 组网络搜索。\n\n"

            elif node_name == "generate_outline" and state_update.get("outline"):
                logs += "## 📝 阶段 3：大纲生成\n\n"
                logs += f"{state_update['outline']}\n\n"

            elif node_name == "draft_report" and state_update.get("draft"):
                logs += f"## ✍️ 阶段 4：报告起草\n\n初稿已完成（{len(state_update['draft'])} 字符）。\n\n"

            elif node_name == "reflect" and state_update.get("reflection"):
                logs += "## 🧐 阶段 5：质量反思\n\n"
                logs += f"{state_update['reflection']}\n\n"
                if state_update.get("iterations", 0) <= 2:
                    logs += "*进入下一轮改进...*\n\n"

            elif node_name == "finalize" and state_update.get("final_report"):
                final_report = state_update["final_report"]
                logs += "## ✅ 阶段 6：终稿输出\n\n最终报告已生成。\n\n"

                # Export to Word
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = "".join(c if c.isalnum() or c in "-_ " else "_" for c in topic)[:40]
                docx_path = os.path.join(PROJECT_ROOT, "output", f"report_{safe_topic}_{timestamp}.docx")
                try:
                    markdown_to_docx(final_report, docx_path, title=topic)
                    logs += f"📄 Word 文档已保存：{docx_path}\n\n"
                except Exception as e:
                    logs += f"⚠️ Word 导出失败：{e}\n\n"

        yield logs, final_report, docx_path


def build_ui() -> gr.Blocks:
    """Build the Gradio Blocks UI."""
    with gr.Blocks(title="Deep Research Agent") as demo:
        gr.Markdown(
            """
            # 🔬 Deep Research Agent

            输入一个研究主题，Agent 将自动分析主题、搜索资料、生成大纲、撰写报告、反思迭代，并输出最终研究报告。
            """
        )

        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                topic_input = gr.Textbox(
                    label="研究主题",
                    placeholder="例如：人工智能对英语专业翻译教育的影响",
                    lines=3,
                    max_lines=5,
                )
                run_btn = gr.Button("🚀 开始研究", variant="primary", size="lg")
                status_text = gr.Textbox(label="状态", value="就绪", interactive=False)

            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.TabItem("📋 研究过程"):
                        logs_md = gr.Markdown(label="过程日志", value="*等待开始...*", height=600)
                    with gr.TabItem("📄 最终报告"):
                        report_md = gr.Markdown(label="最终报告", value="*等待生成...*", height=600)
                    with gr.TabItem("⬇️ 下载"):
                        download_file = gr.File(label="Word 报告下载", interactive=False)

        run_btn.click(
            fn=run_research_stream,
            inputs=topic_input,
            outputs=[logs_md, report_md, download_file],
            show_progress="minimal",
        ).then(
            fn=lambda: "研究完成",
            outputs=status_text,
        )

        gr.Markdown(
            """
            ---
            *Powered by LangGraph + TokenDance (qwen3.7-plus) + Gradio 6.x*
            """
        )

    return demo


def main():
    demo = build_ui()
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        share=False,
        show_error=True,
        theme=THEME,
        css="footer {display:none}",
    )


if __name__ == "__main__":
    main()
