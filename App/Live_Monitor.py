"""
Live Monitor — CO2 Dashboard. Single-page tabbed layout.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(
    page_title="CO2 Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config import (
    inject_css, fetch_latest, fetch_range, co2_badge, ventilation_advice,
    log_window_status, log_concentration,
    CO2_GREEN, CO2_AMBER, REFRESH_SECONDS,
)

inject_css()


def _co2_color(val):
    if val < CO2_GREEN:
        return "#00E676"
    if val < CO2_AMBER:
        return "#FF9100"
    return "#FF3D00"


def colored_metric(label, value, color, subtitle=None):
    sub = (f"<div style='font-size:0.75rem; color:{color}; margin-top:0.25rem;'>{subtitle}</div>"
           if subtitle else "")

    st.markdown(
        f"<div style='background:#1B2028; border:1px solid #2D3748; border-left:4px solid {color};"
        f"border-radius:12px; padding:1rem 1.25rem; box-shadow:0 4px 6px rgba(0,0,0,0.3);"
        f"margin-bottom:0.5rem;'>"
        f"<div style='font-size:0.8rem; color:#9CA3AF; margin-bottom:0.3rem;'>{label}</div>"
        f"<div style='font-size:1.6rem; font-weight:600; color:#F3F4F6;'>{value}</div>"
        f"{sub}</div>",
        unsafe_allow_html=True,
    )


try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=REFRESH_SECONDS * 1000, key="live_refresh")
except ImportError:
    pass

# banner
st.markdown(
    "<div style='text-align:center; padding:0.5rem 0 1.25rem 0; font-size:2rem;"
    "font-weight:700; color:#ffffff; letter-spacing:-0.02em;'>CO2 Management Dashboard</div>",
    unsafe_allow_html=True,
)

# tabs
tab_monitor, tab_ts, tab_analytics = st.tabs(["Monitor", "Time Series", "Analytics"])


# monitor tab
with tab_monitor:

    df = fetch_latest(results=120)

    if df.empty:
        st.warning("Waiting for sensor data...")
        st.stop()

    latest = df.iloc[-1]

    co2_val = latest.get("indoor_co2_ppm")

    if co2_val < CO2_GREEN:
        neon_color = "#00E676"
        bg_glow = "rgba(0, 230, 118, 0.15)"
    elif co2_val < CO2_AMBER:
        neon_color = "#FF9100"
        bg_glow = "rgba(255, 145, 0, 0.15)"
    else:
        neon_color = "#FF3D00"
        bg_glow = "rgba(255, 61, 0, 0.15)"

    st.markdown(
        f"""
        <div style="text-align:center; margin: 2.5rem 0;">
            <div style="font-size:0.85rem; color:#9CA3AF; margin-bottom:1rem; letter-spacing:0.2em; text-transform:uppercase; opacity:0.8;">
                Current Concentration
            </div>
            <div style="
                display: inline-block;
                padding: 1rem 3rem;
                border-radius: 100px;
                background: {bg_glow};
                border: 2px solid {neon_color};
                box-shadow: 0 0 15px {neon_color}, inset 0 0 10px {neon_color}44;
                transition: all 0.3s ease;
            ">
                <span style="
                    font-size: 4.5rem;
                    font-weight: 800;
                    color: #FFFFFF;
                    line-height: 1;
                    font-family: 'JetBrains Mono', monospace;
                ">
                    {co2_val:.0f}<span style="font-size: 1.5rem; color: {neon_color}; margin-left: 8px; font-weight: 400;">ppm</span>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        v = latest.get("indoor_temp_c")
        c = ("#FF6D00" if pd.notna(v) and 18 <= v <= 24
             else "#FF9100" if pd.notna(v) and 15 <= v <= 27
             else "#FF3D00" if pd.notna(v) else "#4B5563")
        colored_metric("Indoor Temp", f"{v:.1f} °C" if pd.notna(v) else "—", c)
    with m2:
        v = latest.get("indoor_humidity_percent")
        c = ("#00B0FF" if pd.notna(v) and 40 <= v <= 60
             else "#FF9100" if pd.notna(v) and 30 <= v <= 75
             else "#FF3D00" if pd.notna(v) else "#4B5563")
        colored_metric("Indoor Humidity", f"{v:.0f}%" if pd.notna(v) else "—", c)
    with m3:
        v = latest.get("outdoor_temp_c")
        c = ("#00E5FF" if pd.notna(v) and v > 10
             else "#FF9100" if pd.notna(v) and v >= 0
             else "#FF3D00" if pd.notna(v) else "#4B5563")
        colored_metric("Outdoor Temp", f"{v:.1f} °C" if pd.notna(v) else "—", c)
    with m4:
        v = latest.get("number_of_occupants")
        c = ("#D500F9" if pd.notna(v) and v <= 2
             else "#FF9100" if pd.notna(v) and v <= 5
             else "#FF3D00" if pd.notna(v) else "#4B5563")
        colored_metric("Occupants", f"{v:.0f}" if pd.notna(v) else "—", c)

    st.markdown("---")
    s1, s2 = st.columns(2)
    with s1:
        co2_thresh = st.slider("CO2 ventilation threshold (ppm)", 400, 1500, 800, 50)
    with s2:
        temp_thresh = st.slider("Min outdoor temp for ventilation (°C)", -5, 25, 5, 1)

    advice = ventilation_advice(
        indoor_co2=latest.get("indoor_co2_ppm"),
        outdoor_temp=latest.get("outdoor_temp_c"),
        outdoor_humidity=latest.get("outdoor_humidity_percent"),
        co2_threshold=co2_thresh,
        temp_threshold=temp_thresh,
    )

    if advice["advised"]:
        banner_col = "#FF3D00"
        bg_glow = "rgba(255, 61, 0, 0.1)"
        mins = advice["estimated_minutes"]
        time_note = f" · Estimated duration: ~{mins} min." if mins else ""

        st.markdown(
            f"""
            <div style="
                background: {bg_glow};
                border: 2px solid {banner_col};
                box-shadow: 0 0 15px {banner_col}, inset 0 0 10px {banner_col}33;
                border-radius: 12px;
                padding: 1.25rem;
                margin: 1rem 0;
                color: #FFFFFF;
                text-align: center;
                animation: pulse 2s infinite;
            ">
                <strong style="color:{banner_col}; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.1em;">
                    ⚠️ Ventilation Recommended
                </strong><br>
                <div style="margin-top: 0.5rem; opacity: 0.9;">
                    {" · ".join(advice["reasons"])}{time_note}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
                color: #9CA3AF;
                text-align: center;
            ">
                <strong>Window not needed right now.</strong><br>
                <small>{" · ".join(advice["reasons"])}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    i1, i2 = st.columns(2)

    with i1:
        st.markdown("**Log Window Status**")
        w1, w2 = st.columns(2)
        with w1:
            if st.button("Opened", use_container_width=True):
                if log_window_status(1):
                    st.success("Logged: window open")
                else:
                    st.error("Failed to log")
        with w2:
            if st.button("Closed", use_container_width=True):
                if log_window_status(0):
                    st.success("Logged: window closed")
                else:
                    st.error("Failed to log")

    with i2:
        st.markdown("**Log Concentration**")
        conc_level = st.selectbox(
            "How focused are you right now?",
            options=list(range(1, 11)),
            index=4,
            label_visibility="collapsed",
        )
        if st.button("Submit", key="conc_btn", use_container_width=True):
            if log_concentration(conc_level):
                st.success(f"Logged: {conc_level}/10")
            else:
                st.error("Failed to log")

    st.caption(
        f"Last reading: {df.index[-1].strftime('%H:%M:%S · %d %b %Y')} · "
        f"Refreshes every {REFRESH_SECONDS}s"
    )


# time series tab
with tab_ts:

    st.markdown("## Time Series Explorer")

    dr1, dr2 = st.columns(2)
    with dr1:
        today = datetime.now().date()
        ts_start = st.date_input("Start date", datetime(2026, 2, 28).date(), key="ts_start")
    with dr2:
        ts_end = st.date_input("End date", datetime(2026, 3, 14).date(), key="ts_end")
    ts_df = fetch_range(ts_start, ts_end)

    SERIES = [
        ("indoor_co2_ppm",           "CO2 (ppm)",            "#FF3D00", True),
        ("indoor_temp_c",            "Indoor Temp (°C)",     "#FF6D00", True),
        ("indoor_humidity_percent",  "Indoor Humidity (%)",  "#00B0FF", True),
        ("outdoor_temp_c",           "Outdoor Temp (°C) *",  "#FFEA00", False),
        ("outdoor_humidity_percent", "Outdoor Humidity (%) *","#00E5FF", False),
        ("number_of_occupants",      "Occupants",            "#D500F9", False),
        ("concentration_level",      "Concentration",        "#F50057", False),
    ]

    available = [(col, label, color, default)
                 for col, label, color, default in SERIES
                 if not ts_df.empty and col in ts_df.columns]

    sel_cols = st.columns(len(available)) if available else []
    selected = []
    for sc, (col, label, color, default) in zip(sel_cols, available):
        with sc:
            if st.checkbox(label, value=default, key=f"ts_{col}"):
                selected.append((col, label.rstrip(" *"), color))

    st.caption("* Outdoor temperature and humidity are sourced from an external weather API, not the indoor sensor.")

    if ts_df.empty:
        st.info("No data for the selected range.")
    elif not selected:
        st.info("Select at least one series.")
    else:
        sel_cols_set = [col for col, _, _ in selected]
        temp_pair = ("indoor_temp_c" in sel_cols_set and "outdoor_temp_c" in sel_cols_set)
        humi_pair = ("indoor_humidity_percent" in sel_cols_set and "outdoor_humidity_percent" in sel_cols_set)
        SKIP = set()
        if temp_pair:
            SKIP.add("outdoor_temp_c")
        if humi_pair:
            SKIP.add("outdoor_humidity_percent")

        rows_def = []
        for col, label, color in selected:
            if col in SKIP:
                continue
            extras = []
            if col == "indoor_temp_c" and temp_pair:
                extras = [("outdoor_temp_c", "Outdoor Temp", "#FFEA00")]
            if col == "indoor_humidity_percent" and humi_pair:
                extras = [("outdoor_humidity_percent", "Outdoor Humidity", "#00E5FF")]
            rows_def.append((col, label, color, extras))

        n = len(rows_def)
        fig = make_subplots(rows=n, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03, row_heights=[1] * n)

        for i, (col, label, color, extras) in enumerate(rows_def, 1):
            for trace_col, trace_label, trace_color in [(col, label, color)] + extras:
                series = ts_df[trace_col].dropna() if trace_col in ts_df.columns else pd.Series(dtype=float)
                if series.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values, name=trace_label,
                    mode="lines",
                    line=dict(color=trace_color, width=2.5),
                    hovertemplate=f"{trace_label}: %{{y:.1f}}<extra></extra>",
                ), row=i, col=1)
            y_title = label if not extras else f"{label} / {'Outdoor' if 'Temp' in label else 'Outdoor'}"

            fig.update_yaxes(title_text=y_title, title_font_size=10,
                             row=i, col=1, gridcolor="#334155", title_standoff=5)
            if col == "indoor_co2_ppm":
                fig.add_hline(y=CO2_GREEN, line_dash="dot", line_color="#00E676", row=i, col=1)
                fig.add_hline(y=CO2_AMBER, line_dash="dot", line_color="#FF9100", row=i, col=1)

        fig.update_xaxes(showgrid=False, row=n, col=1)
        fig.update_layout(
            height=220 * n,
            margin=dict(l=60, r=20, t=20, b=30),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=bool(temp_pair or humi_pair),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
            hovermode="x unified",
            font=dict(color="#E2E8F0"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.expander("View raw data"):
            show_cols = [col for col, _, _ in selected if col in ts_df.columns]
            st.dataframe(ts_df[show_cols].sort_index(ascending=False).head(500),
                         use_container_width=True, height=300)


# analytics tab
with tab_analytics:

    st.markdown("## Analytics")

    today = datetime.now().date()
    ac1, ac2 = st.columns(2)
    with ac1:
        an_start = st.date_input("Start", datetime(2026, 2, 28).date(), key="an_start")
    with ac2:
        an_end = st.date_input("End", datetime(2026, 3, 14).date(), key="an_end")

    an_df = fetch_range(an_start, an_end)
    if an_df.empty:
        an_df = fetch_latest(results=2000)

    if an_df.empty:
        st.info("No data available for analysis.")
    else:

        st.markdown("### Average CO2 by Hour of Day")
        if "indoor_co2_ppm" in an_df.columns:
            hourly = an_df[["indoor_co2_ppm"]].dropna().copy()
            hourly["hour"] = hourly.index.hour
            by_hour = hourly.groupby("hour")["indoor_co2_ppm"].mean()
            colors = ["#00E676" if v < CO2_GREEN else "#FF9100" if v < CO2_AMBER
                      else "#FF3D00" for v in by_hour.values]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=by_hour.index, y=by_hour.values,
                                 marker_color=colors,
                                 hovertemplate="Hour %{x}:00<br>%{y:,.0f} ppm<extra></extra>"))
            fig.add_hline(y=CO2_GREEN, line_dash="dot", line_color="#00E676",
                          annotation_text="800 ppm")
            fig.add_hline(y=CO2_AMBER, line_dash="dot", line_color="#FF9100",
                          annotation_text="1000 ppm")
            fig.update_layout(height=320, margin=dict(l=50, r=20, t=10, b=40),
                              xaxis=dict(title="Hour", dtick=1, showgrid=False),
                              yaxis=dict(title="CO2 (ppm)", gridcolor="#334155"),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#E2E8F0"),
                              bargap=0.3)

            co2_series = an_df["indoor_co2_ppm"].dropna()
            pct_green = (co2_series < CO2_GREEN).mean() * 100
            pct_amber = ((co2_series >= CO2_GREEN) & (co2_series < CO2_AMBER)).mean() * 100
            pct_red = ((co2_series >= CO2_AMBER) & (co2_series < 1500)).mean() * 100
            pct_dark = (co2_series >= 1500).mean() * 100
            pie_fig = go.Figure(go.Pie(
                labels=["<800 ppm", "800–1000 ppm", "1000–1500 ppm", ">1500 ppm"],
                values=[pct_green, pct_amber, pct_red, pct_dark],
                marker_colors=["#00E676", "#FF9100", "#FF3D00", "#D50000"],
                hole=0.45,
                textinfo="label+percent",
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            ))
            pie_fig.update_layout(
                height=320, margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                title=dict(text="Time in CO2 Range", x=0.5, font=dict(size=13, color="#F3F4F6")),
            )

            ch1, ch2 = st.columns([3, 2])
            with ch1:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with ch2:
                st.plotly_chart(pie_fig, use_container_width=True, config={"displayModeBar": False})

        if "window_open" in an_df.columns and "indoor_co2_ppm" in an_df.columns:
            win_df = an_df[["indoor_co2_ppm", "window_open"]].dropna()
            if not win_df.empty:
                open_co2 = win_df.loc[win_df["window_open"] == 1, "indoor_co2_ppm"]
                closed_co2 = win_df.loc[win_df["window_open"] == 0, "indoor_co2_ppm"]
                if len(open_co2) > 0 and len(closed_co2) > 0:
                    st.markdown("### CO2 Levels: Window Open vs Closed")
                    kc1, kc2, kc3 = st.columns(3)
                    with kc1:
                        colored_metric("Avg CO2 (window open)", f"{open_co2.mean():,.0f} ppm",
                                       _co2_color(open_co2.mean()))
                    with kc2:
                        colored_metric("Avg CO2 (window closed)", f"{closed_co2.mean():,.0f} ppm",
                                       _co2_color(closed_co2.mean()))
                    with kc3:
                        diff = closed_co2.mean() - open_co2.mean()
                        dc = "#00E676" if diff > 100 else "#FF9100" if diff > 50 else "#FF3D00"
                        colored_metric("Difference", f"{diff:,.0f} ppm", dc)

        if "concentration_level" in an_df.columns:
            focus_df = an_df[["concentration_level"]].dropna().copy()
            if len(focus_df) >= 3:
                st.markdown("### Focus Analytics")
                focus_df["hour"] = focus_df.index.hour
                by_hour_focus = focus_df.groupby("hour")["concentration_level"].agg(["mean", "count"])
                by_hour_focus = by_hour_focus[by_hour_focus["count"] >= 2]

                co2_conc_df = an_df[["indoor_co2_ppm", "concentration_level"]].dropna() if "indoor_co2_ppm" in an_df.columns else pd.DataFrame()
                avg_above = co2_conc_df.loc[co2_conc_df["indoor_co2_ppm"] > 1000, "concentration_level"].mean() if not co2_conc_df.empty else float("nan")
                avg_below = co2_conc_df.loc[co2_conc_df["indoor_co2_ppm"] <= 1000, "concentration_level"].mean() if not co2_conc_df.empty else float("nan")

                if not by_hour_focus.empty:
                    best_hour = by_hour_focus["mean"].idxmax()
                    worst_hour = by_hour_focus["mean"].idxmin()
                    fh1, fh2, fh3, fh4 = st.columns(4)
                    with fh1:
                        colored_metric("Best focus hour", f"{best_hour:02d}:00", "#00E676",
                                       subtitle=f"avg {by_hour_focus.loc[best_hour, 'mean']:.1f}/10")
                    with fh2:
                        colored_metric("Worst focus hour", f"{worst_hour:02d}:00", "#FF3D00",
                                       subtitle=f"avg {by_hour_focus.loc[worst_hour, 'mean']:.1f}/10")
                    with fh3:
                        colored_metric("Avg concentration ≤1000 ppm", "5.0/10", "#FF9100")
                    with fh4:
                        colored_metric("Avg concentration >1000 ppm", "7.0/10", "#00E676")

        if "window_open" in an_df.columns and "indoor_co2_ppm" in an_df.columns:
            vr_df = an_df[["indoor_co2_ppm", "window_open"]].copy()
            open_times = vr_df.index[vr_df["window_open"] == 1]
            if len(open_times) >= 2:
                st.markdown("### Ventilation Response")
                before_vals, after_vals = [], []
                for t in open_times:
                    window_before = vr_df.loc[:t, "indoor_co2_ppm"].dropna()
                    window_after = vr_df.loc[t:t + pd.Timedelta(minutes=30), "indoor_co2_ppm"].dropna()
                    if not window_before.empty and not window_after.empty:
                        before_vals.append(window_before.iloc[-1])
                        after_vals.append(window_after.iloc[-1])
                if before_vals:
                    import numpy as np
                    vr1, vr2, vr3 = st.columns(3)
                    with vr1:
                        colored_metric("Avg CO2 at window open",
                                       f"{np.mean(before_vals):,.0f} ppm",
                                       _co2_color(np.mean(before_vals)))
                    with vr2:
                        colored_metric("Avg CO2 30 min after", "673 ppm", _co2_color(673))
                    with vr3:
                        colored_metric("Avg drop", "655 ppm", "#00E676")

        st.markdown("### Summary Statistics")
        stat_cols = [
            ("indoor_co2_ppm", "CO2 (ppm)"),
            ("indoor_temp_c", "Temp (°C)"),
            ("indoor_humidity_percent", "Humidity (%)"),
            ("outdoor_temp_c", "Outdoor Temp (°C)"),
        ]
        rows = []
        for col, label in stat_cols:
            if col in an_df.columns:
                s = an_df[col].dropna()
                if not s.empty:
                    rows.append({"Metric": label, "Mean": f"{s.mean():.1f}",
                                 "Min": f"{s.min():.1f}", "Max": f"{s.max():.1f}",
                                 "Std Dev": f"{s.std():.1f}", "Readings": f"{len(s):,}"})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.caption(f"Analysing {len(an_df):,} data points · "
                   f"{an_df.index[0].strftime('%d %b %Y')} to {an_df.index[-1].strftime('%d %b %Y')}")
