# 技术调研笔记

调研日期：2026-06-12
项目：AI 课程期末大作业 — Deep Research Agent

---

## 1. LangGraph（2025–2026）

### 1.1 核心概念

LangGraph 是 LangChain 的扩展，用于构建具有循环、条件分支和持久化状态的多步 Agent。

关键抽象：
- **StateGraph**：显式定义状态图，节点是函数，边控制流程。
- **MessagesState**：预置状态，包含 `messages: list[AnyMessage]`，使用 `add_messages` reducer。
- **Node**：接收 state，返回 state updates。
- **Edge / Conditional Edges**：普通边和条件边，条件边返回下一个节点名称。
- **START / END**：预置入口和出口节点。

### 1.2 节点与循环模式

本作业采用 **Reflection Loop（反思-迭代循环）**：

```
draft_report → reflect → [conditional] → draft_report (loop)
                         ↓
                      finalize
```

实现要点：
- `reflect` 节点生成 critique。
- `should_continue` 条件边检查迭代次数和 critique 内容。
- 循环次数上限防止无限循环。

### 1.3 MessageState 类型

使用 `langchain_core.messages`：
- `HumanMessage`：用户输入。
- `AIMessage`：模型输出，可包含 `tool_calls`。
- `SystemMessage`：系统提示。
- `ToolMessage`：工具执行结果。

### 1.4 工具调用

- 使用 `@tool` 装饰器定义工具。
- 使用 `bind_tools(tools)` 让 LLM 获得工具调用能力。
- 使用 `langgraph.prebuilt.ToolNode` 自动执行工具。

---

## 2. TokenDance（词元跳动）

### 2.1 平台概述

TokenDance 是一个多模型聚合网关，兼容 OpenAI API 协议。

- Base URL：`https://tokendance.space/gateway/v1`
- 鉴权：`Authorization: Bearer <API_KEY>`
- 模型列表：`GET https://tokendance.space/gateway/v1/models`

### 2.2 主模型选择

- **Moonshot (Kimi)**：`kimi-k2.6`，Base URL `https://api.moonshot.cn/v1`
- **TokenDance**：`qwen3.7-plus`，Base URL `https://tokendance.space/gateway/v1`

两者均通过 `langchain_openai.ChatOpenAI` 以 OpenAI 兼容协议调用。本项目默认优先使用 Moonshot (Kimi)。

### 2.3 UniFuncs 工具

本项目同时支持两种搜索后端：

#### DuckDuckGo（默认，免费）

使用 `ddgs` 包调用 DuckDuckGo 文本搜索，无需 API Key。

```python
from ddgs import DDGS
with DDGS() as ddgs:
    results = ddgs.text(query, max_results=5)
```

#### unifuncs-web-search（TokenDance）


- 端点：`POST https://tokendance.space/gateway/unifuncs/web-search`
- 参数：`query`（必填）、`count`（1-50，默认 10）、`freshness`、`includeImages`、`format`
- 返回：`data.webPages[]`，含 `name` / `url` / `snippet` / `summary`
- 用途：替代 DuckDuckGo，提供更稳定的实时搜索结果

#### unifuncs-web-reader（TokenDance）

- 端点：`POST https://tokendance.space/gateway/unifuncs/web-reader`
- 参数：`url`（必填）、`format`（md/text）、`liteMode`、`maxWords`
- 返回：网页正文 Markdown
- 用途：深度阅读网页内容，提取正文

### 2.4 接入 langchain_openai

```python
from langchain_openai import ChatOpenAI

# Moonshot (Kimi)
llm = ChatOpenAI(
    model="kimi-k2.6",
    base_url="https://api.moonshot.cn/v1",
    api_key=os.environ["MOONSHOT_API_KEY"],
)

# TokenDance
llm = ChatOpenAI(
    model="qwen3.7-plus",
    base_url="https://tokendance.space/gateway/v1",
    api_key=os.environ["TOKENDANCE_API_KEY"],
)
```

---

## 3. Gradio 6.x Web UI

### 3.1 版本选择

- 当前最新稳定版：6.18.0
- 安装：`pip install gradio==6.18.0`

### 3.2 ChatInterface 与 Blocks

- `gr.ChatInterface`：高层抽象，适合快速构建聊天机器人。
- `gr.Blocks`：低层 API，适合自定义布局和复杂交互。
- 本作业使用 `gr.Blocks` 以获得更精美的研究流程展示。

### 3.3 关键 API（6.x）

| 功能 | 写法 |
|------|------|
| 主题 | `gr.themes.Soft()` / `gr.themes.Ocean()` |
| 标签页 | `gr.TabItem()` inside `gr.Tabs()` |
| Markdown | `gr.Markdown()` |
| 文件下载 | `gr.File()` |
| 流式更新 | generator `yield` |
| 隐藏 footer | `css="footer {display:none}"` |

### 3.4 部署

```python
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False,
)
```

Nginx 反代配置：

```nginx
location / {
    proxy_pass http://127.0.0.1:7860;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

---

## 4. Python Web UI 框架对比（调研结论）

| 框架 | 首屏速度 | 资源占用 | 聊天支持 | 部署难度 | 推荐度 |
|------|----------|----------|----------|----------|--------|
| Gradio | 快 | 低 | 极强 | 极易 | ⭐⭐⭐⭐⭐ |
| Streamlit | 中等 | 高 | 强 | 较易 | ⭐⭐⭐⭐ |
| Reflex | 中等 | 中高 | 强 | 中等 | ⭐⭐⭐⭐ |
| Flet | 慢 | 高 | 需手工 | 中等 | ⭐⭐⭐ |

最终选择 **Gradio 6.18.0**。

---

## 5. 参考资源

- LangGraph Docs: https://langchain-ai.github.io/langgraph/
- Gradio Docs: https://www.gradio.app/docs
- TokenDance Docs: https://tokendance.space/docs
- python-docx: https://python-docx.readthedocs.io/
