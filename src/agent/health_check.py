import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.config import settings
from utils.trace import log_trace
from langchain_deepseek import ChatDeepSeek
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage

SERVER = settings.mcp_server_path

SYSTEM = """你是一名资深电商运营分析师。对店铺做自动体检，严格按流程：
1. 第一步调用 scan_anomalies 获取确定性的异常清单。
2. 对清单中 severity=high 的异常商品，逐个调用 get_product_detail(product_id, days=14)，
   查看库存状态；对差评率偏高的商品再调用 cluster_reviews(product_id, days=14) 查看差评主题分布，
   结合库存和差评主题做根因归因：
   - 库存为0且状态已售罄 -> 断货，建议立即补货；
   - 库存正常但差评主题集中在破损/漏水/包装/快递 -> 物流包装问题，建议换快递/加固包装；
   - 差评主题集中在质量/尺码/色差 -> 商品质量与详情页问题。
3. 所有结论必须来自工具返回，禁止编造数字。
4. 输出一份简洁中文体检报告：异常清单(表格：商品/异常类型/数据证据)、根因判断、可执行建议。"""

QUESTION = "请对店铺做一次自动运营体检，找出最近7天的异常并给出归因和建议。"

async def main():
    client = MultiServerMCPClient({
        "ecomdb": {"command": sys.executable, "args": [str(settings.mcp_server_path)], "transport": "stdio"},
        "review": {"command": sys.executable, "args": [str(settings.review_server_path)], "transport": "stdio"},
    })
    tools = await client.get_tools()
    print("可用工具：", [t.name for t in tools])

    llm = ChatDeepSeek(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=settings.llm_temperature,
    )
    agent = create_react_agent(llm, tools)
    resp = await agent.ainvoke({"messages": [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=QUESTION),
    ]})
    log_trace("health_check", resp["messages"])
    print("=" * 70)
    print(resp["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())