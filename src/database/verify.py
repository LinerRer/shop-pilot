import datetime
import pandas as pd
from models import engine

today = datetime.date.today()
start = today - datetime.timedelta(days=45)


def di(d):
    return (d - start).days


orders = pd.read_sql("SELECT * FROM orders", engine)
items = pd.read_sql("SELECT * FROM order_items", engine)
traffic = pd.read_sql("SELECT * FROM traffic", engine)
reviews = pd.read_sql("SELECT * FROM reviews", engine)
refunds = pd.read_sql("SELECT * FROM refunds", engine)

oi = orders.merge(items, on="order_id")
oi["date"] = pd.to_datetime(oi["create_time"]).dt.date
oi["d"] = oi["date"].apply(di)

for df in (reviews, refunds):
    df["date"] = pd.to_datetime(df["create_time"]).dt.date
    df["d"] = df["date"].apply(di)

print("=" * 50)
print("异常1：P1008 保温杯（物流破损，第35天起）")
print("=" * 50)
p8 = oi[oi.product_id == "P1008"]
print(f"异常前日均订单: {len(p8[p8.d < 35]) / 35:.1f}")
print(f"异常后日均订单: {len(p8[p8.d >= 35]) / 10:.1f}")
r8 = reviews[reviews.product_id == "P1008"]
print(f"异常前差评率: {(r8[r8.d < 35].rating <= 3).mean():.0%}")
print(f"异常后差评率: {(r8[r8.d >= 35].rating <= 3).mean():.0%}")
f8 = refunds[refunds.product_id == "P1008"]
print(f"异常前退款数: {len(f8[f8.d < 35])} | 异常后退款数: {len(f8[f8.d >= 35])}")

print("=" * 50)
print("异常2：P1004 耳机（第20天直播带货尖峰）")
print("=" * 50)
live = traffic[(traffic.product_id == "P1004") & (traffic.channel == "直播")].copy()
live["date"] = pd.to_datetime(live["date"]).dt.date
top = live.sort_values("uv", ascending=False).head(3)
print(top[["date", "uv"]].to_string(index=False))

print("=" * 50)
print("异常3：P1006 台灯（第40天起断货）")
print("=" * 50)
p6 = oi[oi.product_id == "P1006"]
print(f"断货前日均订单: {len(p6[p6.d < 40]) / 40:.1f}")
print(f"断货后订单总数: {len(p6[p6.d >= 40])}（应为0）")

