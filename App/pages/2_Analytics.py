"""
📊 Analytics — summary insights: hourly CO₂ patterns, concentration correlation, stats.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Analytics · CO₂ Dashboard", page_icon="📊", layout="wide")

from config import inject_css, fetch_latest, fetch_range, CO2_GREEN, CO2_AMBER

inject_css()

st.markdown("## 📊 Analytics")

# ── Data source ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📅 Data Range")
    today = datetime.now().date()
    col_a, col_b = st.columns(2)
    with col_a:
        start = st.date_input("Start", today - timedelta(days=7), key="an_start")
    with col_b:
        end = st.date_input("End", today, key="an_end")

df = fetch_range(start, end)

if df.empty:
    df = fetch_latest(results=2000)

if df.empty:
    st.info("No data available for analysis.")
    st.stop()

# ── 1. Summary statistics ───────────────────────────────────────────────────
st.markdown("### Summary Statistics")

stat_cols = [
    ("indoor_co2_ppm", "CO₂ (ppm)"),
    ("indoor_temp_c", "Temp (°C)"),
    ("indoor_humidity_percent", "Humidity (%)"),
    ("outdoor_temp_c", "Outdoor Temp (°C)"),
]

rows = []
for col, label in stat_cols:
    if col in df.columns:
        s = df[col].dropna()
        if not s.empty:
            rows.append({
                "Metric": label,
                "Mean": f"{s.mean():.1f}",
                "Min": f"{s.min():.1f}",
                "Max": f"{s.max():.1f}",
                "Std Dev": f"{s.std():.1f}",
                "Readings": f"{len(s):,}",
            })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── 2. Average CO₂ by hour ──────────────────────────────────────────────────
st.markdown("### Average CO₂ by Hour of Day")

if "indoor_co2_ppm" in df.columns:
    hourly = df[["indoor_co2_ppm"]].dropna().copy()
    hourly["hour"] = hourly.index.hour
    by_hour = hourly.groupby("hour")["indoor_co2_ppm"].mean()

    colors = []
    for val in by_hour.values:
        if val < CO2_GREEN:
            colors.append("#22c55e")
        elif val < CO2_AMBER:
            colors.append("#f59e0b")
        else:
            colors.append("#ef4444")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=by_hour.index,
        y=by_hour.values,
        marker_color=colors,
        hovertemplate="Hour %{x}:00<br>%{y:,.0f} ppm<extra></extra>",
    ))
    fig.add_hline(y=CO2_GREEN, line_dash="dot", line_color="#22c55e",
                  annotation_text="800 ppm")
    fig.add_hline(y=CO2_AMBER, line_dash="dot", line_color="#f59e0b",
                  annotation_text="1000 ppm")
    fig.update_layout(
        height=320,
        margin=dict(l=50, r=20, t=10, b=40),
        xaxis=dict(title="Hour", dtick=1, showgrid=False),
        yaxis=dict(title="CO₂ (ppm)", gridcolor="#f1f5f9"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 3. CO₂ vs Concentration ─────────────────────────────────────────────────
if "concentration_level" in df.columns and "indoor_co2_ppm" in df.columns:
    conc_df = df[["indoor_co2_ppm", "concentration_level"]].dropna()

    if len(conc_df) >= 3:
        st.markdown("### CO₂ Level vs Self-Reported Concentration")

        # Bin concentration levels and compute mean CO₂
        conc_summary = conc_df.groupby("concentration_level")["indoor_co2_ppm"].agg(["mean", "count"])
        conc_summary = conc_summary.reset_index()

        c1, c2 = st.columns([2, 1])

        with c1:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=conc_summary["concentration_level"],
                y=conc_summary["mean"],
                marker_color="#8b5cf6",
                text=conc_summary["mean"].round(0).astype(int),
                textposition="outside",
                hovertemplate="Concentration: %{x}/5<br>Avg CO₂: %{y:,.0f} ppm<extra></extra>",
            ))
            fig2.update_layout(
                height=300,
                margin=dict(l=50, r=20, t=10, b=40),
                xaxis=dict(title="Self-Reported Concentration (1–5)", dtick=1, showgrid=False),
                yaxis=dict(title="Avg CO₂ (ppm)", gridcolor="#f1f5f9"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                bargap=0.4,
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        with c2:
            st.markdown("**Readings per level**")
            for _, row in conc_summary.iterrows():
                lev = int(row["concentration_level"])
                cnt = int(row["count"])
                avg = row["mean"]
                st.markdown(
                    f"{'⬤' * lev}{'○' * (5 - lev)} **{lev}/5** — "
                    f"{cnt} readings, avg {avg:,.0f} ppm"
                )
    else:
        st.info("Not enough concentration readings for analysis (need at least 3).")

# ── 4. Window open impact ────────────────────────────────────────────────────
if "window_open" in df.columns and "indoor_co2_ppm" in df.columns:
    win_df = df[["indoor_co2_ppm", "window_open"]].dropna()
    if not win_df.empty:
        open_co2 = win_df.loc[win_df["window_open"] == 1, "indoor_co2_ppm"]
        closed_co2 = win_df.loc[win_df["window_open"] == 0, "indoor_co2_ppm"]

        if len(open_co2) > 0 and len(closed_co2) > 0:
            st.markdown("### CO₂ Levels: Window Open vs Closed")

            kc1, kc2, kc3 = st.columns(3)
            with kc1:
                st.metric("Avg CO₂ (window open)", f"{open_co2.mean():,.0f} ppm")
            with kc2:
                st.metric("Avg CO₂ (window closed)", f"{closed_co2.mean():,.0f} ppm")
            with kc3:
                diff = closed_co2.mean() - open_co2.mean()
                st.metric("Difference", f"{diff:,.0f} ppm", delta=f"-{diff:,.0f}")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Analysing {len(df):,} data points · "
    f"{df.index[0].strftime('%d %b %Y')} to {df.index[-1].strftime('%d %b %Y')}"
)
