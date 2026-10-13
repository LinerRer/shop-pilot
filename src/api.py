import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_deepseek import ChatDeepSeek
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from utils.config import settings
from utils.trace import log_trace

app = FastAPI(title="ShopPilot Agent API", version="1.0")

HEALTH_SYSTEM = """你是一名资深电商运营分析师。严格按流程：
1. 先调用 scan_anomalies 获取异常清单。
2. 对 severity=high 的商品调用 get_product_detail(product_id, days=14)，根据库存和差评原文归因：
   库存0已售罄=断货；差评集中破损/漏水/快递=物流包装；差评集中质量/尺码=商品详情页。
3. 结论基于工具返回，禁止编造数字。输出异常清单、根因、建议。"""


async def build_agent():
    client = MultiServerMCPClient({
        "ecomdb": {"command": sys.executable, "args": [str(settings.mcp_server_path)], "transport": "stdio"}
    })
    tools = await client.get_tools()
    llm = ChatDeepSeek(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=settings.llm_temperature,
    )
    return create_react_agent(llm, tools)


class AskReq(BaseModel):
    question: str


@app.post("/api/ask")
async def ask(req: AskReq):
    agent = await build_agent()
    resp = await agent.ainvoke({"messages": [HumanMessage(content=req.question)]})
    log_trace("api_ask", resp["messages"])
    return {"answer": resp["messages"][-1].content}


@app.post("/api/health")
async def health():
    agent = await build_agent()
    resp = await agent.ainvoke({"messages": [
        SystemMessage(content=HEALTH_SYSTEM),
        HumanMessage(content="请对店铺做一次自动运营体检，找出最近7天异常并归因。"),
    ]})
    log_trace("api_health", resp["messages"])
    return {"report": resp["messages"][-1].content}


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok"}
