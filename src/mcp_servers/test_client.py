import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "ecomdb_server.py"


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            resp = await session.list_tools()
            print("全部工具：", [t.name for t in resp.tools])

            cases = [
                ("商品GMV排行(7天)", "get_product_ranking",
                 {"metric": "gmv", "period": "last_7d", "top_n": 8}),
                ("保温杯差评率趋势(10天)", "get_trend",
                 {"metric": "bad_review_rate", "days": 10, "product_id": "P1008"}),
                ("保温杯详情", "get_product_detail",
                 {"product_id": "P1008", "days": 10}),
                ("昨天全店渠道拆分", "get_channel_breakdown",
                 {"date": "", "product_id": ""}),
            ]
            for title, tool_name, args in cases:
                result = await session.call_tool(tool_name, args)
                print("=" * 60)
                print(title)
                print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
