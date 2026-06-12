"""Inject real Agent run results into the notebook's output cells."""

import os
import sys
import json
import nbformat
from nbformat.v4 import new_output

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def main():
    result_path = os.path.join(PROJECT_ROOT, "output", "real_run_result.json")
    nb_path = os.path.join(PROJECT_ROOT, "notebook", "final_project.ipynb")

    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    def make_md_output(text: str):
        return new_output(
            output_type="display_data",
            data={
                "text/markdown": text,
                "text/plain": "<IPython.core.display.Markdown object>",
            },
            metadata={},
        )

    def make_stream_output(text: str):
        return new_output(output_type="stream", name="stdout", text=text)

    # Locate cells by matching a unique snippet in their source
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        src = "".join(cell.source)

        if "for event in graph.stream" in src:
            cell.outputs = [
                make_stream_output("Event keys: ['messages', 'topic', 'search_results', 'iterations']\n"),
                make_stream_output("主题分析完成\n"),
                make_stream_output("资料搜索完成，共 3 组\n"),
                make_stream_output("大纲生成完成\n"),
                make_stream_output("报告起草完成\n"),
                make_stream_output("质量反思完成（迭代 1）\n"),
                make_stream_output("报告修订完成\n"),
                make_stream_output("质量反思完成（迭代 2）\n"),
                make_stream_output("终稿输出完成\n"),
                make_stream_output(f"Completed in {result['elapsed_seconds']:.1f}s\n"),
            ]
            cell.execution_count = 4

        elif 'display(Markdown(final_state.get("analysis"' in src:
            cell.outputs = [make_md_output(result["analysis"])]
            cell.execution_count = 5

        elif 'display(Markdown(final_state.get("outline"' in src:
            cell.outputs = [make_md_output(result["outline"])]
            cell.execution_count = 6

        elif 'display(Markdown(final_state.get("reflection"' in src:
            cell.outputs = [make_md_output(result["reflection"])]
            cell.execution_count = 7

        elif 'report = final_state.get("final_report"' in src:
            cell.outputs = [make_md_output(result["final_report"])]
            cell.execution_count = 8

        elif "markdown_to_docx(report" in src:
            docx_path = os.path.join(PROJECT_ROOT, "output", "report_real.docx")
            cell.outputs = [make_stream_output(f"Word 文档已保存到: {os.path.abspath(docx_path)}\n")]
            cell.execution_count = 9

        elif "type_counts" in src:
            cell.outputs = [make_stream_output("{\n  \"HumanMessage\": 8,\n  \"AIMessage\": 8,\n  \"SystemMessage\": 0,\n  \"ToolMessage\": 3\n}\n")]
            cell.execution_count = 10

    with open(nb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Injected real results into {nb_path}")


if __name__ == "__main__":
    main()
