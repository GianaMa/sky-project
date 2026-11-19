"""同一片天空，三种解读：中国 / 西方 / 日本
运行：streamlit run app.py
"""
import math
import datetime as dt

import ephem
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ---------- 基础数据 ----------
PLANETS = {  # 名称: (ephem类, 公转周期/年, 颜色)
    "水星": (ephem.Mercury, 0.2408, "#9a9a9a"),
    "金星": (ephem.Venus, 0.6152, "#e0b050"),
    "火星": (ephem.Mars, 1.8808, "#d9533a"),
    "木星": (ephem.Jupiter, 11.862, "#c99a6b"),
    "土星": (ephem.Saturn, 29.457, "#c8b36a"),
    "天王星": (ephem.Uranus, 84.02, "#6fc2c9"),
    "海王星": (ephem.Neptune, 164.8, "#4a6fe0"),
}
SIGNS = ["白羊", "金牛", "双子", "巨蟹", "狮子", "处女",
         "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"]
TERMS = ["春分", "清明", "谷雨", "立夏", "小满", "芒种", "夏至", "小暑",
         "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬",
         "小雪", "大雪", "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰"]
# 宿曜27宿，从昴宿（Krittika）开始
SUKUYO = ["昴", "畢", "觜", "参", "井", "鬼", "柳", "星", "張", "翼", "軫", "角", "亢",
          "氐", "房", "心", "尾", "箕", "斗", "女", "虚", "危", "室", "壁", "奎", "婁", "胃"]


# ---------- 天文计算 ----------
def geo_lon(body, d):
    """地心视黄经（回归黄道，度）——星座和节气用的就是这个"""
    body.compute(d, epoch=d)
    return math.degrees(ephem.Ecliptic(body, epoch=d).lon) % 360


def helio(name, d):
    """日心黄道坐标 (经度rad, 距离AU)，用于太阳系俯视图"""
    if name == "地球":
        s = ephem.Sun()
        s.compute(d)
        return (math.radians(geo_lon(ephem.Sun(), d)) + math.pi) % (2 * math.pi), s.earth_distance
    p = PLANETS[name][0]()
    p.compute(d)
    return float(p.hlon), float(p.sun_distance)


def ayanamsa(year):
    """恒星黄道岁差（Lahiri近似），约24度"""
    return 23.85 + 0.01397 * (year - 2000)


def orbit_xy(name, d, period):
    pts = []
    for k in range(120):
        lon, r = helio(name, ephem.Date(d + k * period * 365.25 / 120))
        pts.append((math.sqrt(r) * math.cos(lon), math.sqrt(r) * math.sin(lon)))
    pts.append(pts[0])
    return zip(*pts)


# ---------- 页面 ----------
st.set_page_config(page_title="同一片天空，三种解读", layout="wide")
st.title("🌌 同一片天空，三种解读")
st.caption("中国二十四节气 · 西方星座 · 日本宿曜道 —— 用真实天文算法还原你出生那天的天空")

with st.sidebar:
    st.header("出生信息")
    date = st.date_input("出生日期", dt.date(2005, 1, 1),
                         min_value=dt.date(1900, 1, 1), max_value=dt.date(2100, 12, 31))
    time = st.time_input("出生时间", dt.time(12, 0))
    tz = st.number_input("时区（北京时间=8）", value=8.0, step=0.5)
    st.caption("轨道图半径做了开方压缩，否则内行星会挤成一团。")

local = dt.datetime.combine(date, time)
utc = local - dt.timedelta(hours=tz)
d = ephem.Date(utc)

# 计算
sun_lon = geo_lon(ephem.Sun(), d)
moon = ephem.Moon()
moon_lon = geo_lon(moon, d)
moon_pct = moon.phase
sid_moon = (moon_lon - ayanamsa(utc.year)) % 360
nak = int(sid_moon // (360 / 27))
sukuyo = SUKUYO[(nak - 2) % 27]
term = TERMS[int(sun_lon // 15)]
sign = SIGNS[int(sun_lon // 30)]

# 三种解读卡片
c1, c2, c3 = st.columns(3)
c1.metric("🇨🇳 中国 · 所在节气", term, f"太阳黄经 {sun_lon:.1f}°")
c2.metric("🌐 西方 · 太阳星座", sign + "座", f"度数 {sun_lon % 30:.1f}°")
c3.metric("🇯🇵 日本 · 本命宿（月亮）", sukuyo + "宿", f"月亮恒星黄经 {sid_moon:.1f}°")
st.caption(f"月亮回归黄经 {moon_lon:.1f}° ，月面照亮 {moon_pct:.0f}% 。"
           "宿曜这里用月亮真实位置计算，传统做法是查旧历对照表，两者可能差一宿。")

left, right = st.columns(2)

# 图1：太阳系俯视图
with left:
    st.subheader("太阳系俯视图（日心视角）")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["太阳"],
                             textposition="top center",
                             marker=dict(size=16, color="#ffb300"), showlegend=False))
    names = ["地球"] + list(PLANETS)
    for n in names:
        period = 1.0 if n == "地球" else PLANETS[n][1]
        color = "#2e8b57" if n == "地球" else PLANETS[n][2]
        xs, ys = orbit_xy(n, d, period)
        fig.add_trace(go.Scatter(x=list(xs), y=list(ys), mode="lines",
                                 line=dict(color=color, width=1), opacity=0.5,
                                 hoverinfo="skip", showlegend=False))
        lon, r = helio(n, d)
        fig.add_trace(go.Scatter(x=[math.sqrt(r) * math.cos(lon)], y=[math.sqrt(r) * math.sin(lon)],
                                 mode="markers+text", text=[n], textposition="top center",
                                 marker=dict(size=9, color=color), showlegend=False,
                                 hovertemplate=f"{n}<br>距太阳 {r:.2f} AU<extra></extra>"))
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis=dict(visible=False, scaleanchor="y"), yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True)

# 图2：地心黄道盘
with right:
    st.subheader("黄道盘（地心视角）")
    bodies = {"太阳": (ephem.Sun(), "#ffb300"), "月亮": (ephem.Moon(), "#bbbbbb")}
    for n, (cls, _, col) in PLANETS.items():
        bodies[n] = (cls(), col)
    wheel = go.Figure()
    wheel.add_trace(go.Scatterpolar(theta=[t * 15 + 7.5 for t in range(24)], r=[1.12] * 24,
                                    mode="text", text=TERMS, textfont=dict(size=10),
                                    hoverinfo="skip", showlegend=False))
    for i, (n, (body, col)) in enumerate(bodies.items()):
        lon = geo_lon(body, d)
        wheel.add_trace(go.Scatterpolar(
            theta=[lon], r=[0.35 + 0.08 * i], mode="markers+text", text=[n],
            textposition="middle right", marker=dict(size=10, color=col), showlegend=False,
            hovertemplate=f"{n}<br>黄经 {lon:.1f}°（{SIGNS[int(lon // 30)]}座）<extra></extra>"))
    wheel.update_layout(
        height=560, margin=dict(l=30, r=30, t=20, b=20),
        polar=dict(radialaxis=dict(visible=False, range=[0, 1.2]),
                   angularaxis=dict(tickmode="array", tickvals=[i * 30 + 15 for i in range(12)],
                                    ticktext=SIGNS, direction="counterclockwise", rotation=0)))
    st.plotly_chart(wheel, use_container_width=True)
    st.caption("外圈小字是二十四节气（每15°一个），12星座每30°一个，同一套黄经刻度。")
