import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.config import settings
from langchain_deepseek import ChatDeepSeek
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

SERVER = Path(__file__).resolve().parents[1] / "mcp_servers" / "ecomdb_server.py"

QUESTION = "昨天全店的GMV是多少？用一句话回答，并说一下订单数和环比。"

async def main():
    client = MultiServerMCPClient({
        "ecomdb": {
            "command": sys.executable,
            "args": [str(SERVER)],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    print("Agent 可见工具：", [t.name for t in tools])

    llm = ChatDeepSeek(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=0,
    )
    agent = create_react_agent(llm, tools)

    resp = await agent.ainvoke({"messages": [{"role": "user", "content": QUESTION}]})
    print("=" * 60)
    for m in resp["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())