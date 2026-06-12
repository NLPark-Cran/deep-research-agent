# Deep Research Agent — AI 课程期末大作业

一个基于 **LangGraph** 的深度研究助手 Agent，支持调用 **Moonshot (Kimi)** 或 **TokenDance** 云端大模型，并配以 **Gradio 6.x** Web UI。

## 功能

输入研究主题后，Agent 自动完成：
1. **主题分析**（analyze_topic）— 提炼研究问题与关键词
2. **资料搜索**（research）— 调用 `web_search` 工具实时搜索网络资料
3. **大纲生成**（generate_outline）— 根据主题与资料生成报告大纲
4. **报告撰写**（draft_report）— 基于大纲与资料撰写正文
5. **质量反思**（reflect）— 评估报告并给出改进意见
6. **终稿输出**（finalize）— 输出 Markdown / Word 研究报告

其中 `reflect → draft_report` 构成条件循环边，最多迭代 `MAX_ITERATIONS` 次。

## 技术栈

| 组件 | 版本/说明 |
|------|-----------|
| Python | 3.11+ |
| LangGraph | 1.2.4 |
| langchain_openai | 1.3.0 |
| 云端模型 | kimi-k2.6（Moonshot）或 qwen3.7-plus（TokenDance） |
| 搜索工具 | DuckDuckGo（免费）/ TokenDance UniFuncs web-search |
| Web UI | Gradio 6.18.0 |
| 文档生成 | python-docx 1.2.0 |

## 环境配置

1. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，填入有效的 API Key：
   - 推荐：`MOONSHOT_API_KEY`（Kimi / Moonshot）
   - 备选：`TOKENDANCE_API_KEY`（词元跳动）

3. （可选）启用 Mock LLM 模式以离线测试结构：
   ```bash
   export MOCK_LLM=1
   export SEARCH_BACKEND=duckduckgo
   ```

## 快速开始

1. 安装依赖：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. 运行 Notebook（展示执行结果）：
   ```bash
   jupyter notebook notebook/final_project.ipynb
   ```

3. 启动 Web UI：
   ```bash
   python -m app.main
   ```
   浏览器访问 `http://服务器IP:7860`。

## 项目结构

```
agent/           # LangGraph Agent 核心代码
app/             # Gradio Web UI
notebook/        # 作业提交 Notebook（含执行结果）
docs/            # 说明文档与技术调研笔记
output/          # 生成的报告文件
```

## 部署（可选）

使用 Nginx 反向代理到 `*.hub.tt2.li`：

```nginx
server {
    listen 80;
    server_name aiagent.hub.tt2.li;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

然后启动 Gradio：

```bash
GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860 python -m app.main
```

## 注意事项

- 当前 `.env` 中填入了用户提供的 API Key。如果额度不足或认证失败，可启用 `MOCK_LLM=1` 先验证代码结构，再充值或更换有效 Key。
- Notebook `final_project.ipynb` 默认在 `MOCK_LLM=1` 模式下执行并保存结果，用于展示 Agent 完整流程。

## 作者

Cran — 杭州电子科技大学英语专业
