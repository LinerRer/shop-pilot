import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from mcp.server.fastmcp import FastMCP
from database.models import engine
import json
from analytics import metrics
mcp = FastMCP("ecomdb")


@mcp.tool()
def list_products() -> str:
    """查询店铺所有商品的列表，返回每个商品的ID、名称、品类、价格、库存和上架状态。"""
    df = pd.read_sql(
        "SELECT product_id, name, category, price, stock, status "
        "FROM products ORDER BY product_id",
        engine,
    )
    return df.to_string(index=False)

@mcp.tool()
def get_metrics(period: str = "yesterday", product_id: str = "") -> str:
    """查询店铺或某个商品在某时间段的核心经营指标及环比。
    period 取值：yesterday=昨天，last_7d=最近7天，last_30d=最近30天。
    product_id 留空查全店，填商品ID(如 P1008)查单个商品。
    返回 GMV、订单数、客单价(aov)、UV、转化率(cvr)、加购率、退款率、差评率，
    以及各指标相对上一等长周期的环比变化百分比 change_pct，比率字段单位为百分比。"""
    data = metrics.get_metrics(period, product_id)
    return json.dumps(data, ensure_ascii=False)
@mcp.tool()
def get_trend(metric: str = "gmv", days: int = 14, product_id: str = "") -> str:
    """查询某指标最近若干天的每日趋势序列，用于画折线图和判断异常从哪天开始。
    metric 可选：gmv(成交额)、orders(订单数)、uv(访客数)、cvr(转化率)、
    refund_rate(退款率)、bad_review_rate(差评率)。
    days 为返回天数(默认14)；product_id 留空查全店，填商品ID查单品。"""
    return json.dumps(metrics.get_trend(metric, days, product_id), ensure_ascii=False)


@mcp.tool()
def get_channel_breakdown(date: str = "", product_id: str = "") -> str:
    """查询某一天(默认昨天)各流量渠道的UV、订单数、GMV和转化率拆分。
    date 格式 YYYY-MM-DD，留空默认昨天；product_id 留空查全店。
    用于判断销量下滑是某个渠道异常还是整体下滑。"""
    return json.dumps(metrics.get_channel_breakdown(date, product_id), ensure_ascii=False)


@mcp.tool()
def get_product_ranking(metric: str = "gmv", period: str = "last_7d", top_n: int = 5) -> str:
    """查询商品排行榜，按指定指标降序，用于定位问题商品或头部商品。
    metric 可选 gmv/orders/uv/refund_rate/bad_review_rate；
    period 可选 yesterday/last_7d/last_30d；top_n 为返回条数。"""
    return json.dumps(metrics.get_product_ranking(metric, period, top_n), ensure_ascii=False)


@mcp.tool()
def get_product_detail(product_id: str, days: int = 14) -> str:
    """查询单个商品详细档案：价格、库存、上架状态、近期核心指标，以及最近的差评原文。
    product_id 必填(如 P1008)，days 为统计窗口。
    归因关键：库存为0且状态已售罄=断货；库存正常但差评集中在破损/漏水=物流问题。"""
    return json.dumps(metrics.get_product_detail(product_id, days), ensure_ascii=False)

@mcp.tool()
def scan_anomalies() -> str:
    """确定性扫描全店最近7天经营异常，返回结构化异常清单(含严重级别high/medium)。
    覆盖：全店差评率/退款率环比异常、单商品差评率偏高、退款率偏高、GMV环比暴跌(疑似断货)。
    运营体检第一步先调用本工具拿到异常清单，再对可疑商品调 get_product_detail 做根因归因。"""
    return json.dumps(metrics.detect_anomalies(), ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")
