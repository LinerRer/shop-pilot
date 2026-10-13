# ShopPilot：基于 MCP 协议的电商智能运营 Agent

一个面向电商运营场景的垂直智能体：接入经营数据库后，能自然语言问答、一键自动体检、差评主题聚类、归因异常并生成 Word 日报，支持定时自动运行与异常主动推送。

## 能做什么

- **自然语言问答（流式输出）**："保温杯最近怎么样？昨天 GMV 多少？"——Agent 自动调用数据工具回答，逐字流式输出，过程中可见工具调用。
- **一键自动体检**：自动扫描全店异常 → 下钻可疑商品 → 差评主题聚类 → 根因归因 → 给出可执行建议。
- **差评主题聚类**：对指定商品近 N 天差评自动聚类（物流破损/漏水/尺码/色差等），辅助精准归因。
- **经营看板**：GMV 趋势、渠道拆分、商品排行的交互图表。
- **自动生成 Word 日报**：结构化异常表格 + AI 根因分析，可直接发给运营。
- **异常主动推送**：体检发现高级异常后，自动通过飞书/钉钉 webhook 告警（未配置时模拟推送）。
- **定时任务**：每天早上 8 点无人值守自动生成日报。
- **REST API**：Agent 能力通过 FastAPI 暴露，外部系统可调用。

## 核心架构

```
┌──────────────┐  ┌──────────────┐
│ Streamlit UI │  │  FastAPI     │  （问答/体检/健康检查接口）
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────────┐
│   DeepSeek + LangGraph ReAct Agent │  （流式输出 / 并行工具调用）
└──────────────┬───────────────────┘
               │ 标准 MCP 协议 (stdio)
    ┌──────────┴──────────┐
    ▼                     ▼
┌───────────────┐  ┌───────────────┐
│ ecomdb MCP    │  │ review MCP    │
│ Server        │  │ Server        │
│ 7个工具        │  │ cluster_reviews│
│ get_metrics   │  │ （差评主题聚类）│
│ get_trend     │  └───────┬───────┘
│ scan_anomalies│          │
│ ...           │          │
└───────┬───────┘          │
        │                  │
        ▼                  ▼
┌──────────────────────────────────┐
│   SQLite（45天经营数据 + 日报历史） │
└──────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│ 定时任务(APScheduler) → 日报 → 推送 │
│ Trace日志 / 历史入库 / 配置集中管理  │
└──────────────────────────────────┘
```

**关键设计原则**：确定性计算（指标公式、异常阈值）归 Python 代码，语言理解与归因建议归 LLM。让模型只做它擅长的事，数字永远由代码算，从根源防止大模型编数字。

## 技术栈

- 大模型：DeepSeek (deepseek-chat)
- Agent 框架：LangGraph `create_react_agent`（ReAct 模式，支持 parallel tool calling）
- 工具协议：MCP (Model Context Protocol)，FastMCP stdio Server（mcp 1.30.0）
- 数据：SQLAlchemy 2.0 + SQLite，pandas 指标计算
- 界面：Streamlit + Plotly（流式输出用 nest_asyncio）
- 日报：python-docx
- 服务化：FastAPI + uvicorn
- 定时任务：APScheduler
- 配置：pydantic-settings + .env

## 快速开始

```bash
# 1. 配置环境变量
# 新建 .env，填入：
# DEEPSEEK_API_KEY=你的key
# DEEPSEEK_BASE_URL=https://api.deepseek.com
# DEEPSEEK_MODEL=deepseek-chat

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化并生成模拟数据（含3个预埋异常）
python src/database/seed.py

# 4. 启动网页
streamlit run src/ui/app.py
# 打开 http://localhost:8501
```

其他入口：
```bash
# 一键体检（命令行）
python src/agent/health_check.py

# 生成Word日报（含异常推送、历史入库）
python src/agent/generate_report.py

# 启动REST API
uvicorn api:app --app-dir src --port 8000

# 启动定时任务（每天8点自动日报）
python src/scheduler.py
```

## 工程化特性

- **配置集中管理**：路径、异常阈值、日期窗口全部在 `utils/config.py`，改配置不改业务代码
- **Agent Trace 日志**：每次调用的工具名、参数、返回摘要写入 `logs/trace_日期.log`，可回溯决策过程
- **历史报告入库**：每次日报结果存入 `daily_reports` 表，支持周环比回看
- **异常主动推送**：飞书/钉钉 webhook 告警
- **流式输出**：问答逐字显示，中间可见工具调用
- **.gitignore**：密钥、虚拟环境、数据库不入库

## 目录结构

```
src/
├── database/      # SQLAlchemy 模型（7表）、数据生成、异常验证
├── analytics/     # 确定性指标计算 + 异常扫描
├── mcp_servers/   # 2个 FastMCP Server：ecomdb（数据）、review（评论聚类）
├── agent/         # ReAct Agent：问答、体检、日报生成
├── ui/            # Streamlit 三 Tab 界面（流式输出）
├── utils/         # 配置、Trace日志、推送通知
├── api.py         # FastAPI REST 接口
└── scheduler.py   # APScheduler 定时任务
```
