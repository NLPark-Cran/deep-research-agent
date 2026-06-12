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


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
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
    button_primary_background_fill_hover="*primary_700",
)


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------
STAGES = [
    ("analyze_topic", "🔍 主题分析", 10),
    ("research", "📚 资料搜索", 25),
    ("generate_outline", "📝 大纲生成", 40),
    ("draft_report", "✍️ 报告起草", 60),
    ("reflect", "🧐 质量反思", 80),
    ("finalize", "✅ 终稿输出", 100),
]

NODE_TO_STAGE = {node: (label, pct) for node, label, pct in STAGES}


def _safe_filename(topic: str) -> str:
    """Create a filesystem-safe name from the topic."""
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in topic)[:40]


def _render_stepper(completed: set[str], current: str | None, progress_pct: int) -> str:
    """Render a horizontal stepper as HTML."""
    items = []
    for node, label, pct in STAGES:
        if node in completed:
            color = "#16a34a"  # green-600
            icon = "✓"
            bg = "#dcfce7"  # green-100
        elif node == current:
            color = "#4f46e5"  # indigo-600
            icon = "●"
            bg = "#e0e7ff"  # indigo-100
        else:
            color = "#94a3b8"  # slate-400
            icon = "○"
            bg = "#f1f5f9"  # slate-100

        items.append(
            f"""
            <div style="flex:1;text-align:center;position:relative;">
                <div style="
                    width:36px;height:36px;border-radius:50%;margin:0 auto 6px auto;
                    display:flex;align-items:center;justify-content:center;
                    font-weight:bold;color:{color};background:{bg};border:2px solid {color};
                ">{icon}</div>
                <div style="font-size:12px;color:{color};font-weight:600;">{label}</div>
            </div>
            """
        )

    return f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span style="font-weight:700;color:#1e293b;">研究进度</span>
            <span style="font-weight:700;color:#4f46e5;">{progress_pct}%</span>
        </div>
        <div style="width:100%;height:10px;background:#e2e8f0;border-radius:999px;overflow:hidden;">
            <div style="width:{progress_pct}%;height:100%;background:linear-gradient(90deg,#4f46e5,#7c3aed);transition:width 0.4s ease;border-radius:999px;"></div>
        </div>
    </div>
    <div style="display:flex;justify-content:space-between;gap:8px;margin-top:16px;">
        {''.join(items)}
    </div>
    """


def _render_stage_card(title: str, content: str, color: str = "indigo") -> str:
    """Render a single process card as HTML."""
    color_map = {
        "indigo": ("#4f46e5", "#e0e7ff"),
        "green": ("#16a34a", "#dcfce7"),
        "amber": ("#d97706", "#fef3c7"),
        "blue": ("#2563eb", "#dbeafe"),
    }
    border, bg = color_map.get(color, color_map["indigo"])
    # Escape HTML to safely embed Markdown-like text
    safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_content = safe_content.replace("\n", "<br>")
    return f"""
    <div style="
        background:{bg};border-left:4px solid {border};border-radius:10px;
        padding:14px 18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,0.05);
    ">
        <div style="font-weight:700;color:{border};margin-bottom:8px;font-size:16px;">{title}</div>
        <div style="color:#334155;font-size:14px;line-height:1.7;">{safe_content}</div>
    </div>
    """


def _format_process_html(
    topic: str,
    completed: dict[str, str],
    current_node: str | None,
    current_message: str,
    progress_pct: int,
) -> str:
    """Build the full HTML for the process panel."""
    stepper = _render_stepper(set(completed.keys()), current_node, progress_pct)

    cards = []
    # Render completed stages in order
    for node, label, _ in STAGES:
        if node in completed:
            color = "green" if node in ("finalize",) else "indigo"
            cards.append(_render_stage_card(f"✓ {label}", completed[node], color=color))

    # Render current status card
    if current_node and current_node not in completed:
        label, _ = NODE_TO_STAGE.get(current_node, (current_node, 0))
        cards.append(_render_stage_card(f"⏳ {label}", current_message, color="amber"))

    cards_html = "\n".join(cards) if cards else _render_stage_card("等待开始", "点击左侧“开始研究”按钮启动 Agent。", color="blue")

    return f"""
    <div style="font-family:system-ui,-apple-system,sans-serif;">
        <div style="margin-bottom:20px;">
            <div style="font-size:18px;font-weight:700;color:#1e293b;margin-bottom:6px;">研究主题</div>
            <div style="font-size:15px;color:#475569;background:#f8fafc;padding:10px 14px;border-radius:8px;border:1px solid #e2e8f0;">{topic}</div>
        </div>
        {stepper}
        <div style="margin-top:24px;">
            {cards_html}
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Main streaming handler
# ---------------------------------------------------------------------------
def run_research_stream(
    topic: str,
) -> Generator[tuple[str, str, str, dict, str | None], None, None]:
    """Run the research agent and stream updates to the Gradio UI.

    Yields (process_html, status_text, report_markdown, download_btn_update, download_file).
    """
    if not topic or not topic.strip():
        empty_html = _format_process_html(
            "未输入主题", {}, None, "请输入研究主题。", 0
        )
        yield empty_html, "⚠️ 请输入研究主题", "", gr.update(value=None, interactive=False), None
        return

    topic = topic.strip()

    # Initial state: running
    completed: dict[str, str] = {}
    status_text = "🚀 准备开始研究..."
    process_html = _format_process_html(topic, completed, "analyze_topic", "正在初始化研究流程，即将进行主题分析...", 0)
    yield process_html, status_text, "", gr.update(value=None, interactive=False), None

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

            label, base_pct = NODE_TO_STAGE.get(node_name, (node_name, 0))

            # Determine message/content based on node
            content = ""
            if node_name == "analyze_topic" and state_update.get("analysis"):
                content = str(state_update["analysis"])
                completed[node_name] = content
            elif node_name == "research" and state_update.get("search_results"):
                count = len(state_update["search_results"])
                queries = [r.get("query", "") for r in state_update["search_results"]]
                content = f"已完成 {count} 组网络搜索。\n\n搜索查询：\n" + "\n".join(f"• {q}" for q in queries)
                completed[node_name] = content
            elif node_name == "generate_outline" and state_update.get("outline"):
                content = str(state_update["outline"])
                completed[node_name] = content
            elif node_name == "draft_report" and state_update.get("draft"):
                draft = str(state_update["draft"])
                content = f"初稿已完成，共 {len(draft)} 字符。\n\n{draft[:300]}..." if len(draft) > 300 else draft
                completed[node_name] = content
            elif node_name == "reflect" and state_update.get("reflection"):
                reflection = str(state_update["reflection"])
                iteration = state_update.get("iterations", 1)
                loop_msg = "进入下一轮改进..." if iteration <= 2 else "反思完成。"
                content = f"{reflection}\n\n{loop_msg}"
                completed[node_name] = content
            elif node_name == "finalize" and state_update.get("final_report"):
                final_report = str(state_update["final_report"])
                content = f"最终报告已生成，共 {len(final_report)} 字符。"
                completed[node_name] = content

                # Export to Word
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = _safe_filename(topic)
                docx_path = os.path.join(PROJECT_ROOT, "output", f"report_{safe_topic}_{timestamp}.docx")
                try:
                    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
                    markdown_to_docx(final_report, docx_path, title=topic)
                    content += f"\n\n📄 Word 文档已保存。"
                except Exception as e:
                    content += f"\n\n⚠️ Word 导出失败：{e}"
            else:
                # Node produced no recognized update; still show progress
                content = "正在处理..."

            # Update status and progress
            status_text = f"⏳ {label}..."
            progress_pct = base_pct
            process_html = _format_process_html(
                topic, completed, node_name, content, progress_pct
            )
            yield process_html, status_text, final_report, gr.update(value=None, interactive=False), docx_path

    # Final state
    status_text = "✅ 研究完成"
    process_html = _format_process_html(topic, completed, None, "研究已完成，可切换到“最终报告”或“下载”标签页。", 100)
    yield process_html, status_text, final_report, gr.update(value=docx_path, interactive=True), docx_path


# ---------------------------------------------------------------------------
# UI builder
# ---------------------------------------------------------------------------
def build_ui() -> gr.Blocks:
    """Build the Gradio Blocks UI."""
    with gr.Blocks(title="Deep Research Agent") as demo:
        gr.Markdown(
            """
            <div style="text-align:center;margin-bottom:8px;">
                <h1 style="margin:0;font-size:32px;">🔬 Deep Research Agent</h1>
                <p style="color:#64748b;margin-top:6px;">
                    输入一个研究主题，Agent 将自动分析主题、搜索资料、生成大纲、撰写报告、反思迭代，并输出最终研究报告。
                </p>
            </div>
            """
        )

        with gr.Row(equal_height=False):
            # ---------------- Left column ----------------
            with gr.Column(scale=1, min_width=320):
                with gr.Group():
                    topic_input = gr.Textbox(
                        label="研究主题",
                        placeholder="例如：人工智能对英语专业翻译教育的影响",
                        lines=4,
                        max_lines=6,
                    )
                    run_btn = gr.Button("🚀 开始研究", variant="primary", size="lg")

                with gr.Group():
                    status_text = gr.Textbox(
                        label="当前状态",
                        value="就绪",
                        interactive=False,
                        container=True,
                    )
                    progress_html = gr.HTML(
                        value=_render_stepper(set(), None, 0),
                        label="进度",
                    )

                with gr.Group():
                    gr.Markdown("""
                    **模型分工**
                    - 🔍 主题分析：`qwen3.7-plus`
                    - 📚 资料搜索：`unifuncs-s3-pro`
                    - 📝 大纲/起草/终稿：`unifuncs-u3-pro`
                    - 🧐 质量反思：`qwen3.7-plus`
                    """)

            # ---------------- Right column ----------------
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.TabItem("📋 研究过程"):
                        process_html = gr.HTML(
                            value=_format_process_html("", {}, None, "点击左侧“开始研究”按钮启动 Agent。", 0),
                            height=640,
                        )
                    with gr.TabItem("📄 最终报告"):
                        report_md = gr.Markdown(
                            value="*等待生成...*",
                            height=640,
                            latex_delimiters=[],
                        )
                    with gr.TabItem("⬇️ 下载"):
                        gr.Markdown("### 报告下载")
                        download_btn = gr.DownloadButton(
                            label="⬇️ 下载 Word 报告",
                            value=None,
                            interactive=False,
                            variant="primary",
                            size="lg",
                        )
                        download_file = gr.File(
                            label="Word 报告文件",
                            interactive=False,
                            height=200,
                        )

        gr.Markdown(
            """
            ---
            <div style="text-align:center;color:#64748b;font-size:13px;">
                Powered by LangGraph + TokenDance (qwen3.7-plus / unifuncs-s3-pro / unifuncs-u3-pro) + Gradio 6.x
            </div>
            """
        )

        # Wire up the event
        run_btn.click(
            fn=run_research_stream,
            inputs=topic_input,
            outputs=[process_html, status_text, report_md, download_btn, download_file],
            show_progress="hidden",
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    demo = build_ui()
    demo.queue(
        default_concurrency_limit=1,
        api_open=False,
    )
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
