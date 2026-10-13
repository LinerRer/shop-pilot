import asyncio
import sys
import concurrent.futures
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import nest_asyncio
nest_asyncio.apply()

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.config import settings
from utils.trace import log_trace
from analytics import metrics
from langchain_deepseek import ChatDeepSeek
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage

SERVER = settings.mcp_server_path

HEALTH_SYSTEM = """你是一名资深电商运营分析师。对店铺做自动体检，严格按流程：
1. 第一步调用 scan_anomalies 获取确定性的异常清单。
2. 对清单中 severity=high 的异常商品，调用 get_product_detail(product_id, days=14) 查看库存；
   对差评率偏高的商品再调用 cluster_reviews(product_id, days=14) 查看差评主题分布，
   结合库存和差评主题归因：
   - 库存为0且状态已售罄 -> 断货，建议立即补货；
   - 库存正常但差评主题集中破损/漏水/包装/快递 -> 物流包装问题；
   - 差评主题集中质量/尺码/色差 -> 商品质量与详情页问题。
3. 所有结论必须来自工具返回，禁止编造数字。
4. 输出简洁中文体检报告：异常清单(表格)、根因判断、可执行建议。"""


def _run_async(coro):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


@st.cache_resource
def get_llm():
    return ChatDeepSeek(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        temperature=settings.llm_temperature,
    )


async def _build_agent():
    client = MultiServerMCPClient({
        "ecomdb": {"command": sys.executable, "args": [str(settings.mcp_server_path)], "transport": "stdio"},
        "review": {"command": sys.executable, "args": [str(settings.review_server_path)], "transport": "stdio"},
    })
    tools = await client.get_tools()
    return create_react_agent(get_llm(), tools)


def ask(question):
    placeholder = st.empty()

    async def run():
        agent = await _build_agent()
        full = ""
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=question)]}, version="v2"
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                text = getattr(chunk, "content", "")
                if text:
                    full += text
                    placeholder.markdown(full + " ▌")
            elif kind == "on_tool_start":
                full += f"\n\n> 正在调用工具：{event.get('name', '')}...\n"
                placeholder.markdown(full)
        placeholder.markdown(full)
        return full

    return asyncio.run(run())


def health_check():
    async def run():
        agent = await _build_agent()
        resp = await agent.ainvoke({"messages": [
            SystemMessage(content=HEALTH_SYSTEM),
            HumanMessage(content="请对店铺做一次自动运营体检，找出最近7天异常并归因。"),
        ]})
        log_trace("health_web", resp["messages"])
        return resp["messages"][-1].content
    return _run_async(run())


st.set_page_config(page_title="ShopPilot 电商智能运营助手", layout="wide")
st.title("ShopPilot 电商智能运营助手")

tab_chat, tab_health, tab_chart = st.tabs(["智能问答", "一键体检", "经营图表"])

with tab_chat:
    st.subheader("向运营助手提问")
    question = st.text_input("问题", placeholder="例如：保温杯最近怎么样？昨天GMV多少？")
    if st.button("发送", key="send") and question:
        with st.spinner("Agent思考并调取数据中..."):
            st.markdown(ask(question))

with tab_health:
    st.subheader("一键自动体检")
    st.write("Agent会自动扫描全店异常、下钻商品、给出根因和建议。约20-40秒。")
    if st.button("开始体检", key="health"):
        with st.spinner("正在扫描异常并归因..."):
            st.markdown(health_check())

with tab_chart:
    st.subheader("经营数据看板")

    anomalies = metrics.detect_anomalies()
    high_count = sum(1 for a in anomalies if a.get("severity") == "high")
    medium_count = sum(1 for a in anomalies if a.get("severity") == "medium")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("当前异常总数", len(anomalies))
    col2.metric("高级异常", high_count)
    col3.metric("中级异常", medium_count)
    col4.metric("监控商品数", 8)

    if anomalies:
        st.warning("检测到异常，下方图表中红色标注为异常商品/日期")

    trend = metrics.get_trend("gmv", 14)
    df_t = pd.DataFrame(trend["series"])
    df_t["gmv"] = pd.to_numeric(df_t["gmv"])
    df_t["prev"] = df_t["gmv"].shift(1)
    df_t["change"] = (df_t["gmv"] - df_t["prev"]) / df_t["prev"] * 100
    anomaly_dates = df_t[df_t["change"] < -20]["date"].tolist()

    fig_gmv = go.Figure()
    fig_gmv.add_trace(go.Scatter(x=df_t["date"], y=df_t["gmv"], mode="lines+markers",
                                 name="GMV", line=dict(color="#1f77b4", width=2)))
    if anomaly_dates:
        df_anom = df_t[df_t["date"].isin(anomaly_dates)]
        fig_gmv.add_trace(go.Scatter(x=df_anom["date"], y=df_anom["gmv"], mode="markers",
                                     name="异常下跌", marker=dict(color="red", size=12, symbol="x")))
    fig_gmv.update_layout(title="近14天GMV趋势（红色×为异常下跌日）", xaxis_title="日期", yaxis_title="GMV")
    st.plotly_chart(fig_gmv, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        ch = metrics.get_channel_breakdown()
        df_c = pd.DataFrame(ch["channels"])
        st.plotly_chart(px.bar(df_c, x="channel", y="gmv", title="昨日各渠道GMV", color="channel"),
                        use_container_width=True)
    with c2:
        rk = metrics.get_product_ranking("gmv", "last_7d", top_n=8)
        df_r = pd.DataFrame(rk["ranking"])
        anomaly_products = set()
        for a in anomalies:
            pid = a.get("scope", "")
            if pid and pid.startswith("P"):
                anomaly_products.add(pid)
        df_r["is_anomaly"] = df_r["product_id"].isin(anomaly_products)
        colors = ["#ff4b4b" if x else "#1f77b4" for x in df_r["is_anomaly"]]
        fig_rk = go.Figure(go.Bar(x=df_r["name"], y=df_r["gmv"], marker_color=colors))
        fig_rk.update_layout(title="近7天商品GMV排行（红色为异常商品）",
                             xaxis_title="商品", yaxis_title="GMV")
        st.plotly_chart(fig_rk, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        trend_p1008 = metrics.get_trend("gmv", 14, product_id="P1008")
        df_p = pd.DataFrame(trend_p1008["series"])
        fig_p = px.line(df_p, x="date", y="gmv", title="P1008保温杯 GMV趋势（物流破损异常）", markers=True)
        fig_p.update_traces(line=dict(color="#ff4b4b"))
        st.plotly_chart(fig_p, use_container_width=True)
    with c4:
        trend_refund = metrics.get_trend("refund_rate", 14)
        df_rf = pd.DataFrame(trend_refund["series"])
        fig_rf = px.line(df_rf, x="date", y="refund_rate", title="近14天退款率趋势", markers=True)
        fig_rf.update_traces(line=dict(color="#ff7f0e"))
        st.plotly_chart(fig_rf, use_container_width=True)
