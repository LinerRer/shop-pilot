import datetime
from functools import lru_cache
import pandas as pd
from database.models import engine
from utils.config import settings
CHANNELS = ["搜索", "推荐", "直播", "广告", "直接"]

@lru_cache(maxsize=1)
def load_frames():
    orders = pd.read_sql("SELECT * FROM orders", engine)
    items = pd.read_sql("SELECT * FROM order_items", engine)
    traffic = pd.read_sql("SELECT * FROM traffic", engine)
    reviews = pd.read_sql("SELECT * FROM reviews", engine)
    refunds = pd.read_sql("SELECT * FROM refunds", engine)
    products = pd.read_sql("SELECT * FROM products", engine)

    oi = orders.merge(items, on="order_id")
    oi["date"] = pd.to_datetime(oi["create_time"]).dt.date
    traffic["date"] = pd.to_datetime(traffic["date"]).dt.date
    reviews["date"] = pd.to_datetime(reviews["create_time"]).dt.date
    refunds["date"] = pd.to_datetime(refunds["create_time"]).dt.date
    return {
        "oi": oi, "traffic": traffic, "reviews": reviews,
        "refunds": refunds, "products": products,
    }


def _range(period):
    today = datetime.date.today()
    if period == "yesterday":
        cur = (today - datetime.timedelta(days=1), today - datetime.timedelta(days=1))
        prev = (today - datetime.timedelta(days=2), today - datetime.timedelta(days=2))
    elif period == "last_7d":
        cur = (today - datetime.timedelta(days=7), today - datetime.timedelta(days=1))
        prev = (today - datetime.timedelta(days=14), today - datetime.timedelta(days=8))
    elif period == "last_30d":
        cur = (today - datetime.timedelta(days=30), today - datetime.timedelta(days=1))
        prev = (today - datetime.timedelta(days=60), today - datetime.timedelta(days=31))
    else:
        raise ValueError("period 只能是 yesterday / last_7d / last_30d")
    return cur, prev


def _filter(df, start, end, product_id):
    mask = (df["date"] >= start) & (df["date"] <= end)
    if product_id:
        mask &= (df["product_id"] == product_id)
    return df[mask]


def _metrics_in_range(start, end, product_id=""):
    f = load_frames()
    oi = _filter(f["oi"], start, end, product_id)
    tr = _filter(f["traffic"], start, end, product_id)
    rv = _filter(f["reviews"], start, end, product_id)
    rf = _filter(f["refunds"], start, end, product_id)

    gmv = round(float(oi["amount"].sum()), 2)
    n_orders = int(oi["order_id"].nunique())
    uv = int(tr["uv"].sum())
    add_cart = int(tr["add_cart"].sum())
    n_refund = int(rf["refund_id"].nunique())
    n_review = int(rv["review_id"].nunique())
    n_bad = int((rv["rating"] <= 3).sum())

    return {
        "gmv": gmv,
        "orders": n_orders,
        "aov": round(gmv / n_orders, 2) if n_orders else 0.0,
        "uv": uv,
        "cvr": round(n_orders / uv * 100, 2) if uv else 0.0,
        "add_cart_rate": round(add_cart / uv * 100, 2) if uv else 0.0,
        "refund_rate": round(n_refund / n_orders * 100, 2) if n_orders else 0.0,
        "reviews": n_review,
        "bad_review_rate": round(n_bad / n_review * 100, 2) if n_review else 0.0,
    }


def get_metrics(period="yesterday", product_id=""):
    (cs, ce), (ps, pe) = _range(period)
    cur = _metrics_in_range(cs, ce, product_id)
    prev = _metrics_in_range(ps, pe, product_id)
    change = {}
    for key, value in cur.items():
        old = prev.get(key, 0)
        change[key] = round((value - old) / old * 100, 1) if old else None
    return {
        "period": period,
        "product_id": product_id or "ALL",
        "current": cur,
        "previous": prev,
        "change_pct": change,
    }

def get_trend(metric="gmv", days=14, product_id=""):
    today = datetime.date.today()
    series = []
    for i in range(days, 0, -1):
        d = today - datetime.timedelta(days=i)
        m = _metrics_in_range(d, d, product_id)
        series.append({"date": d.isoformat(), metric: m[metric]})
    return {"metric": metric, "days": days, "product_id": product_id or "ALL", "series": series}


def get_channel_breakdown(date_str="", product_id=""):
    today = datetime.date.today()
    d = datetime.date.fromisoformat(date_str) if date_str else today - datetime.timedelta(days=1)
    f = load_frames()
    tr = _filter(f["traffic"], d, d, product_id)
    oi = _filter(f["oi"], d, d, product_id)
    rows = []
    for ch in CHANNELS:
        uv = int(tr[tr.channel == ch].uv.sum())
        sub = oi[oi.channel == ch]
        orders = int(sub.order_id.nunique())
        gmv = round(float(sub.amount.sum()), 2)
        rows.append({
            "channel": ch, "uv": uv, "orders": orders, "gmv": gmv,
            "cvr": round(orders / uv * 100, 2) if uv else 0.0,
        })
    return {"date": d.isoformat(), "product_id": product_id or "ALL", "channels": rows}


def get_product_ranking(metric="gmv", period="last_7d", top_n=5):
    (cs, ce), _ = _range(period)
    f = load_frames()
    prods = f["products"]
    rows = []
    for pid in sorted(prods.product_id.unique()):
        m = _metrics_in_range(cs, ce, pid)
        name = prods[prods.product_id == pid].name.iloc[0]
        rows.append({"product_id": pid, "name": name, metric: m[metric]})
    rows.sort(key=lambda x: x[metric], reverse=True)
    return {"metric": metric, "period": period, "ranking": rows[:top_n]}


def get_product_detail(product_id, days=14):
    f = load_frames()
    p = f["products"][f["products"].product_id == product_id]
    if p.empty:
        return {"error": f"商品 {product_id} 不存在"}
    p = p.iloc[0]
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days)
    end = today - datetime.timedelta(days=1)
    m = _metrics_in_range(start, end, product_id)
    rv = _filter(f["reviews"], start, end, product_id)
    bad = rv[rv.rating <= 3].sort_values("date", ascending=False).head(5)
    samples = [
        {"date": r.date.isoformat(), "rating": int(r.rating), "content": r.content}
        for r in bad.itertuples()
    ]
    return {
        "product_id": product_id, "name": p["name"], "category": p["category"],
        "price": float(p["price"]), "stock": int(p["stock"]), "status": p["status"],
        "recent_days": days, "metrics": m, "recent_bad_reviews": samples,
    }

def detect_anomalies():
    today = datetime.date.today()
    cur_s = today - datetime.timedelta(days=settings.recent_days)
    cur_e = today - datetime.timedelta(days=1)
    prev_s = today - datetime.timedelta(days=settings.compare_days)
    prev_e = today - datetime.timedelta(days=settings.recent_days + 1)
    f = load_frames()
    anomalies = []

    c = _metrics_in_range(cur_s, cur_e)
    p = _metrics_in_range(prev_s, prev_e)
    if p["bad_review_rate"] > 0 and c["bad_review_rate"] - p["bad_review_rate"] >= settings.store_bad_review_jump:
        anomalies.append({"scope": "全店", "type": "差评率环比上升",
                          "evidence": f"{p['bad_review_rate']}% -> {c['bad_review_rate']}%",
                          "severity": "high"})
    if p["refund_rate"] > 0 and c["refund_rate"] - p["refund_rate"] >= settings.store_refund_jump:
        anomalies.append({"scope": "全店", "type": "退款率环比上升",
                          "evidence": f"{p['refund_rate']}% -> {c['refund_rate']}%",
                          "severity": "high"})

    prods = f["products"]
    for pid in sorted(prods.product_id.unique()):
        row = prods[prods.product_id == pid].iloc[0]
        name, stock, status = row["name"], int(row["stock"]), row["status"]
        cc = _metrics_in_range(cur_s, cur_e, pid)
        pp = _metrics_in_range(prev_s, prev_e, pid)

        if cc["bad_review_rate"] >= settings.bad_review_threshold:
            anomalies.append({"scope": pid, "product": name, "type": "差评率偏高",
                              "evidence": f"{cc['bad_review_rate']}% (上期{pp['bad_review_rate']}%)",
                              "severity": "high" if cc["bad_review_rate"] >= settings.bad_review_high else "medium"})
        if cc["refund_rate"] >= settings.refund_threshold:
            anomalies.append({"scope": pid, "product": name, "type": "退款率偏高",
                              "evidence": f"{cc['refund_rate']}% (上期{pp['refund_rate']}%)",
                              "severity": "high"})
        if pp["gmv"] > 500 and (cc["gmv"] - pp["gmv"]) / pp["gmv"] <= -settings.gmv_drop_ratio:
            if stock == 0 and status == "已售罄":
                atype = "疑似断货"
                note = f"库存0/已售罄；UV {cc['uv']} 正常但GMV {cc['gmv']} (上期{pp['gmv']})"
            else:
                atype = "GMV环比大幅下跌"
                note = f"GMV {pp['gmv']} -> {cc['gmv']}"
            anomalies.append({"scope": pid, "product": name, "type": atype,
                              "evidence": note, "severity": "high"})
    return anomalies

