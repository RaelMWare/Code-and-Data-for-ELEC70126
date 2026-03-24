"""
📈 Time Series — interactive exploration with date range picker.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="Time Series · CO₂ Dashboard", page_icon="📈", layout="wide")

from config import inject_css, fetch_latest, fetch_range, CO2_GREEN, CO2_AMBER

inject_css()

st.markdown("## 📈 Time Series Explorer")

# ── Date controls ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📅 Date Range")
    mode = st.radio("Range", ["Last N hours", "Custom dates"], label_visibility="collapsed")

    if mode == "Last N hours":
        hours = st.slider("Hours to show", 1, 72, 12)
        # Use latest data with enough points
        results = max(200, hours * 6 * 2)  # ~10 min intervals, 2× buffer
        df = fetch_latest(results=min(results, 8000))
        if not df.empty:
            cutoff = df.index[-1] - timedelta(hours=hours)
            df = df.loc[df.index >= cutoff]
    else:
        today = datetime.now().date()
        col_a, col_b = st.columns(2)
        with col_a:
            start = st.date_input("Start", today - timedelta(days=3))
        with col_b:
            end = st.date_input("End", today)
        df = fetch_range(start, end)

if df.empty:
    st.info("No data for the selected range.")
    st.stop()

# ── Series config ────────────────────────────────────────────────────────────
SERIES = [
    ("indoor_co2_ppm",          "CO₂ (ppm)",           "#ef4444", True),
    ("indoor_temp_c",           "Indoor Temp (°C)",     "#f97316", True),
    ("indoor_humidity_percent", "Indoor Humidity (%)",  "#3b82f6", True),
    ("outdoor_temp_c",          "Outdoor Temp (°C)",    "#eab308", False),
    ("outdoor_humidity_percent","Outdoor Humidity (%)", "#06b6d4", False),
    ("number_of_occupants",     "Occupants",            "#8b5cf6", False),
    ("fan_activation",          "Fan State",            "#22c55e", False),
    ("window_open",             "Window Status",        "#14b8a6", False),
    ("concentration_level",     "Concentration",        "#ec4899", False),
]

available = [(col, label, color, default)
             for col, label, color, default in SERIES if col in df.columns]

with st.sidebar:
    st.markdown("### 📊 Series")
    selected = []
    for col, label, color, default in available:
        if st.checkbox(label, value=default, key=f"ts_{col}"):
            selected.append((col, label, color))

if not selected:
    st.info("Select at least one series from the sidebar.")
    st.stop()

# ── Chart ────────────────────────────────────────────────────────────────────
n = len(selected)
fig = make_subplots(
    rows=n, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[1] * n,
)

for i, (col, label, color) in enumerate(selected, 1):
    series = df[col].dropna()
    if series.empty:
        continue

    is_binary = col in ("fan_activation", "window_open")

    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            name=label,
            mode="lines" if not is_binary else "lines",
            line=dict(
                color=color,
                width=1.5,
                shape="hv" if is_binary else "linear",
            ),
            fill="tozeroy" if is_binary else None,
            fillcolor=f"{color}18" if is_binary else None,
            hovertemplate=f"{label}: %{{y:.1f}}<extra></extra>",
        ),
        row=i, col=1,
    )

    fig.update_yaxes(title_text=label, title_font_size=10, row=i, col=1,
                     gridcolor="#f1f5f9", title_standoff=5)

    # CO₂ threshold lines
    if col == "indoor_co2_ppm":
        fig.add_hline(y=CO2_GREEN, line_dash="dot", line_color="#22c55e",
                      row=i, col=1)
        fig.add_hline(y=CO2_AMBER, line_dash="dot", line_color="#f59e0b",
                      row=i, col=1)

fig.update_xaxes(showgrid=False, row=n, col=1)
fig.update_layout(
    height=220 * n,
    margin=dict(l=60, r=20, t=20, b=30),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    showlegend=False,
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── Data table ───────────────────────────────────────────────────────────────
with st.expander("View raw data"):
    show_cols = [c for c, _, _ in selected if c in df.columns]
    st.dataframe(
        df[show_cols].sort_index(ascending=False).head(500),
        use_container_width=True,
        height=300,
    )
