import sys
import json
import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from mcp.server.fastmcp import FastMCP
from database.models import engine
from utils.config import settings
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage

mcp = FastMCP("review-analysis")

CLUSTER_PROMPT = """你是电商评论分析专家。对下面的差评做主题聚类。
要求：
1. 输出严格JSON，不要markdown代码块，不要任何解释文字。
2. 格式：{{"themes":[{{"theme":"主题名","count":数量,"samples":["样例1","样例2"]}}]}}
3. 主题名要简短具体，例如：物流破损、漏水、尺码偏小、色差、做工差、快递慢，不要用"其他问题"这种泛泛的词。
4. 每个主题给1-2条最典型的差评原文作为样例。

差评列表：
{reviews}
"""


@mcp.tool()
def cluster_reviews(product_id: str, days: int = 14) -> str:
    """对指定商品最近N天的差评(rating<=3)做主题聚类，返回各主题数量和典型样例。用于根因归因。"""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days)
    df = pd.read_sql(
        "SELECT content, rating FROM reviews WHERE product_id=? AND rating<=3 AND date(create_time)>=? ORDER BY create_time DESC",
        engine, params=(product_id, start.isoformat()),
    )
    if len(df) == 0:
        return json.dumps({"themes": [], "total_bad_reviews": 0,
                           "message": f"近{days}天无差评"}, ensure_ascii=False)

    reviews_text = "\n".join(f"- {r.content}" for r in df.itertuples())[:3000]
    llm = ChatDeepSeek(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=0,
    )
    resp = llm.invoke([
        SystemMessage(content="只输出JSON，不要markdown代码块，不要解释。"),
        HumanMessage(content=CLUSTER_PROMPT.format(reviews=reviews_text)),
    ])
    text = str(resp.content).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text.strip("`")
        text = text.rstrip("`").strip()
    try:
        data = json.loads(text)
    except Exception:
        data = {"themes": [], "parse_failed": True, "raw": text[:500]}
    data["total_bad_reviews"] = int(len(df))
    return json.dumps(data, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
