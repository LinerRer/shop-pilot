import random
import datetime
from sqlalchemy.orm import Session
from models import (
    engine, Base, Product, Order, OrderItem,
    Traffic, Review, Refund,
)

random.seed(42)

DAYS = 45
TODAY = datetime.date.today()
START_DAY = TODAY - datetime.timedelta(days=DAYS)

CHANNELS = ["搜索", "推荐", "直播", "广告", "直接"]
CHANNEL_RATIO = [0.30, 0.25, 0.15, 0.20, 0.10]

# (id, 名称, 品类, 售价, 成本, 热度, 库存, 基础转化率)
PRODUCTS = [
    ("P1001", "纯棉短袖T恤", "服饰", 79, 35, 10, 800, 0.032),
    ("P1002", "高腰牛仔裤", "服饰", 199, 90, 7, 500, 0.030),
    ("P1003", "真丝连衣裙", "服饰", 329, 160, 4, 300, 0.028),
    ("P1004", "无线蓝牙耳机", "数码", 159, 70, 9, 600, 0.035),
    ("P1005", "充电宝20000毫安", "数码", 129, 60, 6, 400, 0.031),
    ("P1006", "北欧风护眼台灯", "家居", 89, 40, 5, 350, 0.033),
    ("P1007", "记忆棉枕头", "家居", 119, 55, 5, 450, 0.029),
    ("P1008", "316不锈钢保温杯", "家居", 69, 28, 8, 700, 0.034),
]
TOTAL_WEIGHT = sum(x[5] for x in PRODUCTS)

GOOD_TEMPLATES = [
    "质量真的不错，{n}物超所值，已经推荐给朋友了",
    "物流很快，包装完好，{n}和描述一致，满意",
    "第二次回购了，一如既往的好",
    "客服态度很好，有问题很快就解决了",
    "性价比很高，这个价位能买到{n}很值",
    "做工精细，没有瑕疵，{n}用着挺好",
    "发货速度快，第二天就到了，{n}不错",
    "{n}收到了，包装严实，体验超出预期",
]
MEDIUM_TEMPLATES = [
    "整体还行，就是{n}和图片有点色差",
    "一般般吧，这个价格也算合理",
    "用着还行，没有特别惊艳的感觉",
    "{n}基本符合描述，就是物流稍慢",
]
BAD_NORMAL = [
    "用了两天就坏了，{n}质量堪忧",
    "{n}做工一般，有明显小瑕疵",
    "尺码偏小，拍大了一码还是紧",
    "色差严重，实物和图片颜色不一样",
    "客服半天不回复，售后体验差",
    "快递太慢了，等了快一周才到",
]
BAD_BROKEN = [
    "收到时包装都破了，{n}磕得变形",
    "快递太暴力，{n}到手有明显磕碰",
    "包装很简陋，{n}收到就凹了一块",
]
BAD_LEAK = [
    "杯盖不密封，放包里漏了一滩水",
    "保温杯漏水严重，书包都被泡湿了",
    "保温差还漏水，{n}不推荐购买",
]
REFUND_REASONS = ["不想要了", "拍错/多拍", "商品质量问题", "物流太慢", "商品与描述不符"]


def make_review(pid, name, rating, d):
    if rating >= 4:
        text = random.choice(GOOD_TEMPLATES)
    elif rating == 3:
        text = random.choice(MEDIUM_TEMPLATES)
    elif pid == "P1008" and d >= 35:
        text = random.choice(BAD_BROKEN + BAD_LEAK)
    else:
        text = random.choice(BAD_NORMAL)
    return text.format(n=name)


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = Session(engine)

    for pid, name, cat, price, cost, hot, stock, cvr in PRODUCTS:
        session.add(Product(
            product_id=pid, name=name, category=cat,
            price=price, cost=cost, stock=stock, status="在售",
        ))

    orders_info = []
    traffic_rows = []
    order_seq = 0

    for d in range(DAYS):
        date = START_DAY + datetime.timedelta(days=d)
        weekend = 1.3 if date.weekday() >= 5 else 1.0
        total_uv = 2800 * weekend * random.uniform(0.85, 1.15)

        for pid, name, cat, price, cost, hot, stock, cvr in PRODUCTS:
            uv = total_uv * (hot / TOTAL_WEIGHT) * random.uniform(0.8, 1.2)
            sold_out = (pid == "P1006" and d >= 40)

            for ch, ratio in zip(CHANNELS, CHANNEL_RATIO):
                ch_uv = uv * ratio
                if pid == "P1004" and d == 20 and ch == "直播":
                    ch_uv *= 7
                ch_uv = int(ch_uv)
                traffic_rows.append(Traffic(
                    date=date, channel=ch, product_id=pid,
                    uv=ch_uv,
                    pv=int(ch_uv * random.uniform(2.5, 4.0)),
                    add_cart=int(ch_uv * random.uniform(0.08, 0.15)),
                ))

            cur_cvr = cvr
            if pid == "P1008" and d >= 35:
                cur_cvr = cvr * 0.45
            if sold_out:
                cur_cvr = 0.0

            n_orders = int(uv * cur_cvr)
            for _ in range(n_orders):
                order_seq += 1
                ch_weights = list(CHANNEL_RATIO)
                if pid == "P1004" and d == 20:
                    ch_weights[2] *= 7
                channel = random.choices(CHANNELS, weights=ch_weights, k=1)[0]
                qty = random.choices([1, 2, 3], weights=[80, 15, 5])[0]
                create_dt = datetime.datetime.combine(
                    date, datetime.time(random.randint(0, 23), random.randint(0, 59))
                )
                oid = f"O{date.strftime('%m%d')}{order_seq:05d}"
                uid = f"U{random.randint(1, 1500):05d}"
                session.add(Order(
                    order_id=oid, user_id=uid, amount=round(price * qty, 2),
                    status="已完成", channel=channel, create_time=create_dt,
                ))
                session.add(OrderItem(
                    order_id=oid, product_id=pid, quantity=qty, unit_price=price,
                ))
                orders_info.append({
                    "oid": oid, "pid": pid, "name": name,
                    "price": price, "d": d, "create_dt": create_dt,
                })

    session.add_all(traffic_rows)

    review_seq = 0
    refund_seq = 0
    for o in orders_info:
        pid, d = o["pid"], o["d"]
        bad_period = (pid == "P1008" and d >= 35)

        if random.random() < 0.55:
            review_seq += 1
            rdt = o["create_dt"] + datetime.timedelta(days=random.randint(1, 6))
            if bad_period:
                rating = random.choices([1, 2, 3, 4, 5], weights=[30, 25, 15, 15, 15])[0]
            else:
                rating = random.choices([1, 2, 3, 4, 5], weights=[3, 4, 6, 25, 62])[0]
            session.add(Review(
                review_id=f"R{review_seq:06d}", product_id=pid, order_id=o["oid"],
                rating=rating, content=make_review(pid, o["name"], rating, d),
                create_time=rdt,
            ))

        refund_prob = 0.26 if bad_period else 0.05
        if random.random() < refund_prob:
            refund_seq += 1
            rdt = o["create_dt"] + datetime.timedelta(days=random.randint(1, 4))
            if bad_period:
                reason = random.choice(["收到商品破损", "商品漏水", "收到商品破损", "保温杯漏水"])
            else:
                reason = random.choice(REFUND_REASONS)
            session.add(Refund(
                refund_id=f"RF{refund_seq:06d}", order_id=o["oid"], product_id=pid,
                amount=o["price"], reason=reason, create_time=rdt,
            ))

    p1006 = session.get(Product, "P1006")
    p1006.stock = 0
    p1006.status = "已售罄"

    session.commit()

    print(f"商品 8 个 | 订单 {len(orders_info)} 条 | 流量 {len(traffic_rows)} 条")
    print(f"评论 {review_seq} 条 | 退款 {refund_seq} 条")
    print(f"数据日期范围：{START_DAY} ~ {TODAY}")


if __name__ == "__main__":
    main()
