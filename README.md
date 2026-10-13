# ShopPilot：基于 MCP 协议的电商智能运营 Agent

一个面向电商运营场景的垂直智能体：接入经营数据库后，能自然语言问答、一键自动体检、归因异常并生成 Word 日报。

## 能做什么

- **自然语言问答**："保温杯最近怎么样？昨天 GMV 多少？"——Agent 自动调用数据工具回答，不编造数字。
- **一键自动体检**：自动扫描全店异常 → 下钻可疑商品 → 根因归因 → 给出可执行建议。
- **经营看板**：GMV 趋势、渠道拆分、商品排行的交互图表。
- **自动生成 Word 日报**：结构化异常表格 + AI 根因分析，可直接发给运营。

## 核心架构

```
┌─────────────┐   Streamlit UI   ┌──────────────────────┐
│  网页界面    │ ◀──────────────▶ │  DeepSeek + ReAct Agent │
└─────────────┘                  └──────────┬───────────┘
                                           │ 标准 MCP 协议 (stdio)
                                ┌──────────▼───────────┐
                                │  ecomdb MCP Server     │  7 个工具
                                │  (FastMCP)            │  get_metrics / get_trend
                                │                       │  get_product_detail ...
                                │  确定性指标计算        │  scan_anomalies
                                └──────────┬────────────┘
                                           │ SQLAlchemy
                                ┌──────────▼───────────┐
                                │   SQLite (45天经营数据) │
                                └───────────────────────┘
```

**关键设计原则**：确定性计算（指标、阈值判断）归 Python 代码，语言理解与归因建议归 LLM。让模型只做它擅长的事，数字永远由代码算。

## 技术栈

- 大模型：DeepSeek (deepseek-chat)
- Agent 框架：LangGraph `create_react_agent`（ReAct 模式）
- 工具协议：MCP (Model Context Protocol)，FastMCP stdio Server
- 数据：SQLAlchemy 2.0 + SQLite，pandas 指标计算
- 界面：Streamlit + Plotly
- 日报：python-docx

## 快速开始

```bash
# 1. 配置环境变量
# 复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化并生成模拟数据（含预埋异常）
python src/database/seed.py

# 4. 启动网页
streamlit run src/ui/app.py
# 打开 http://localhost:8501
```

## 目录结构

```
src/
├── database/      # SQLAlchemy 模型、数据生成、异常验证
├── analytics/     # 确定性指标计算 + 异常扫描
├── mcp_servers/   # FastMCP Server（对外暴露工具）
├── agent/         # ReAct Agent：问答、体检、日报生成
├── ui/            # Streamlit 三 Tab 界面
└── utils/         # 配置读取
```
