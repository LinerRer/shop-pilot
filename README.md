# ShopPilot

基于 MCP 协议的电商运营 Agent。接入经营数据后，能用自然语言查数据、自动扫异常、聚差评、归因、出 Word 日报。

## 能做什么

- 自然语言问答，流式输出，过程中能看到 Agent 调了哪些工具
- 一键体检：扫全店异常 → 下钻商品 → 差评聚类 → 给原因和建议
- 差评主题聚类：把差评自动分成"物流破损""漏水""尺码偏小"这类主题，附数量和样例
- 经营图表：GMV 趋势、渠道拆分、商品排行
- Word 日报：异常表格 + AI 归因，生成完自动入库
- 异常推送：发现高级异常后走飞书/钉钉 webhook 告警（没配就打印到控制台）
- 定时任务：每天 8 点自动跑日报
- REST API：FastAPI 暴露 `/api/ask`、`/api/health`

## 架构

```
Streamlit / FastAPI
      │
      ▼
DeepSeek + LangGraph ReAct Agent（流式 + 并行工具调用）
      │ MCP (stdio)
      ├──────────────┐
      ▼              ▼
 ecomdb Server    review Server
 (7个数据工具)     (差评聚类)
      │              │
      └──────┬───────┘
             ▼
     SQLite（45天数据 + 日报历史）
```

核心思路：指标计算和异常判断用 Python 写死，不让大模型算数字；LLM 只负责理解问题、决定调什么工具、读结果、组织语言。从根源上防止编数字。

## 技术栈

Python 3.11 / DeepSeek / LangGraph ReAct / MCP 1.30 (FastMCP) / SQLAlchemy + SQLite / pandas / Streamlit + Plotly / python-docx / FastAPI / APScheduler / pydantic-settings

## 跑起来

```bash
# 1. 建 .env，填 DeepSeek key
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 2. 装依赖
pip install -r requirements.txt

# 3. 生成模拟数据（45天，含3个预埋异常）
python src/database/seed.py

# 4. 启动网页
streamlit run src/ui/app.py
```

其他入口：
```bash
python src/agent/health_check.py      # 命令行一键体检
python src/agent/generate_report.py   # 生成 Word 日报 + 入库 + 推送
uvicorn api:app --app-dir src --port 8000   # REST API
python src/scheduler.py               # 定时任务
```

## 目录

```
src/
├── agent/          # ReAct Agent：问答、体检、日报
├── analytics/      # 确定性指标计算 + 异常扫描
├── mcp_servers/    # ecomdb（数据）、review（差评聚类）
├── database/       # 模型、mock 数据、验证脚本
├── ui/             # Streamlit 三 Tab
├── utils/          # 配置、Trace 日志、推送
├── api.py          # FastAPI
└── scheduler.py    # APScheduler
```

## 踩过的坑

- **MCP 版本**：默认装到 2.x，FastMCP 改名了 API 全变，锁定 1.30.0
- **Streamlit + 异步 Agent**：直接 `asyncio.run` 会 Event loop closed，用 `nest_asyncio` + 线程池解决
- **异常召回**：纯靠 LLM 自己找异常会漏断货（差评率不高但 GMV 跌），加了确定性 `scan_anomalies` 工具先扫一遍再归因
- **GitHub push**：HTTPS 443 端口被封，改用 SSH 22 端口才推上去
- **数据库路径**：相对路径依赖运行目录，统一用 `Path(__file__).resolve().parents[2]` 算绝对路径

## 没做的

- 多轮对话记忆
- 对接真实电商平台 API
- 多用户/账号系统
- 评论聚类用的 LLM 直接聚，没上 embedding + KMeans
