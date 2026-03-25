"""
config.py — ThingSpeak channel definitions and shared data helpers.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ThingSpeak channels

CHANNELS = {
    "indoor": {
        "id": st.secrets["indoor"]["id"],
        "key": st.secrets["indoor"]["key"],
        "fields": {
            "field1": "indoor_co2_ppm",
            "field2": "indoor_humidity_percent",
            "field3": "indoor_temp_c",
        },
    },
    "weather": {
        "id": st.secrets["weather"]["id"],
        "key": st.secrets["weather"]["key"],
        "fields": {
            "field1": "outdoor_temp_c",
            "field2": "outdoor_humidity_percent",
        },
    },
    "output": {
        "id": st.secrets["output"]["id"],
        "key": st.secrets["output"]["key"],
        "fields": {
            "field1": "fan_activation",
        },
    },
    "factors": {
        "id": st.secrets["factors"]["id"],
        "key": st.secrets["factors"]["key"],
        "write_key": st.secrets["factors"]["write_key"],
        "fields": {
            "field1": "number_of_occupants",
            "field4": "concentration_level",
            "field3": "window_open",
        },
    },
}

REFRESH_SECONDS = 30

# CO2 thresholds

CO2_GREEN = 800
CO2_AMBER = 1000

# Ventilation rate mode
# "default" → uses CO2_DECAY_RATE_DEFAULT (safe, tested)
# "dynamic" → estimates rate from last 5 window-open events (experimental)
VENTILATION_RATE_MODE = "default"
CO2_DECAY_RATE_DEFAULT = 10  # ppm per minute


def _dynamic_decay_rate(df: "pd.DataFrame") -> float:
    """Compute median CO₂ decay rate (ppm/min) from last 5 window-open events."""
    if df is None or df.empty:
        return CO2_DECAY_RATE_DEFAULT
    opens = df.index[df["window_open"].diff() == 1][-5:]
    rates = []
    for t_open in opens:
        seg = df.loc[t_open: t_open + pd.Timedelta(minutes=15), "indoor_co2_ppm"].dropna()
        if len(seg) >= 2:
            elapsed = (seg.index[-1] - seg.index[0]).total_seconds() / 60
            if elapsed > 0:
                rates.append((seg.iloc[0] - seg.iloc[-1]) / elapsed)
    if len(rates) < 2:
        return CO2_DECAY_RATE_DEFAULT
    return float(np.median(rates))

# Data fetch helpers


def _fetch_channel(channel_key: str, results: int = 120) -> pd.DataFrame:
    """Fetch the last *results* entries from a single ThingSpeak channel."""
    ch = CHANNELS[channel_key]
    url = (
        f"https://api.thingspeak.com/channels/{ch['id']}"
        f"/feeds.json?api_key={ch['key']}&results={results}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    feeds = resp.json().get("feeds", [])
    if not feeds:
        return pd.DataFrame()

    df = pd.DataFrame(feeds)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.set_index("created_at").sort_index()

    rename = {k: v for k, v in ch["fields"].items() if k in df.columns}
    df = df.rename(columns=rename)
    for col in ch["fields"].values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    keep = [c for c in ch["fields"].values() if c in df.columns]
    return df[keep]


def _fetch_channel_range(channel_key: str, start: str, end: str) -> pd.DataFrame:
    """Fetch a date range by walking forward in 4-day windows.

    ThingSpeak always returns the LAST N results within a start+end window,
    so large ranges get truncated. Splitting into small windows guarantees
    each window stays under 8000 readings and we always get the earliest data.
    """
    ch = CHANNELS[channel_key]
    WINDOW = pd.Timedelta(days=1)
    all_frames = []

    window_start = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    while window_start < end_ts:
        window_end = min(window_start + WINDOW, end_ts)
        s_str = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        e_str = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        url = (
            f"https://api.thingspeak.com/channels/{ch['id']}"
            f"/feeds.json?api_key={ch['key']}"
            f"&start={s_str}&end={e_str}&results=8000"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            feeds = resp.json().get("feeds", [])
        except Exception:
            feeds = []

        if feeds:
            page_df = pd.DataFrame(feeds)
            page_df["created_at"] = pd.to_datetime(page_df["created_at"])
            page_df = page_df.set_index("created_at").sort_index()

            rename = {k: v for k, v in ch["fields"].items() if k in page_df.columns}
            page_df = page_df.rename(columns=rename)
            for col in ch["fields"].values():
                if col in page_df.columns:
                    page_df[col] = pd.to_numeric(page_df[col], errors="coerce")

            keep = [c for c in ch["fields"].values() if c in page_df.columns]
            all_frames.append(page_df[keep])

        window_start = window_end + pd.Timedelta(seconds=1)

    if not all_frames:
        return pd.DataFrame()

    df = pd.concat(all_frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


@st.cache_data(ttl=REFRESH_SECONDS)
def fetch_latest(results: int = 120) -> pd.DataFrame:
    """Merge latest data from all four channels into one DataFrame."""
    frames = []
    for key in CHANNELS:
        try:
            f = _fetch_channel(key, results=results)
            if not f.empty:
                frames.append(f)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    df = frames[0]
    for f in frames[1:]:
        df = df.join(f, how="outer")

    df = df.sort_index().ffill()
    if "indoor_co2_ppm" in df.columns:
        df["indoor_co2_ppm"] = df["indoor_co2_ppm"].rolling(window=2, min_periods=1).mean()
    return df


@st.cache_data(ttl=600)
def fetch_range(start_date, end_date) -> pd.DataFrame:
    """Merge data for a date range from all channels."""
    start_str = pd.Timestamp(start_date).strftime("%Y-%m-%dT00:00:00Z")
    end_str = pd.Timestamp(end_date).strftime("%Y-%m-%dT23:59:59Z")

    frames = []
    for key in CHANNELS:
        try:
            f = _fetch_channel_range(key, start_str, end_str)
            if not f.empty:
                frames.append(f)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    df = frames[0]
    for f in frames[1:]:
        df = df.join(f, how="outer")

    df = df.sort_index()
    return df


def log_window_status(status: int) -> bool:
    """Write window status (1=open, 0=closed) to ThingSpeak."""
    ch = CHANNELS["factors"]
    url = (
        f"https://api.thingspeak.com/update"
        f"?api_key={ch['write_key']}&field3={status}"
    )
    try:
        resp = requests.get(url, timeout=10)
        return resp.text.strip() != "0"
    except Exception:
        return False


def log_concentration(level: int) -> bool:
    """Write self-reported concentration level (1-5) to ThingSpeak."""
    ch = CHANNELS["factors"]
    url = (
        f"https://api.thingspeak.com/update"
        f"?api_key={ch['write_key']}&field2={level}"
    )
    try:
        resp = requests.get(url, timeout=10)
        return resp.text.strip() != "0"
    except Exception:
        return False


# Ventilation advisor


def ventilation_advice(
    indoor_co2: float,
    outdoor_temp: float,
    outdoor_humidity: float,
    co2_threshold: float = 800.0,
    temp_threshold: float = 5.0,
    df=None,
) -> dict:
    """
    Evaluate whether opening a window is advised.
    Returns dict with 'advised' bool, 'reasons' list, and 'estimated_minutes'.
    """
    reasons = []
    advised = True

    if pd.isna(indoor_co2) or pd.isna(outdoor_temp) or pd.isna(outdoor_humidity):
        return {"advised": False, "reasons": ["Insufficient data"], "estimated_minutes": None}

    if indoor_co2 <= co2_threshold:
        advised = False
        reasons.append(f"CO₂ is {indoor_co2:.0f} ppm — already below {co2_threshold:.0f} ppm")

    if outdoor_temp < temp_threshold:
        advised = False
        reasons.append(f"Outdoor temp is {outdoor_temp:.1f}°C — below {temp_threshold:.1f}°C minimum")

    if outdoor_humidity >= 85:
        advised = False
        reasons.append(f"Outdoor humidity is {outdoor_humidity:.0f}% — above 85%")

    if advised:
        reasons.append("All conditions met for ventilation")

    est_min = None
    if advised and indoor_co2 > co2_threshold:
        excess = indoor_co2 - co2_threshold
        rate = (
            _dynamic_decay_rate(df)
            if VENTILATION_RATE_MODE == "dynamic"
            else CO2_DECAY_RATE_DEFAULT
        )
        est_min = max(5, int(excess / rate))

    return {"advised": advised, "reasons": reasons, "estimated_minutes": est_min}


# Styling helpers

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,300;1,9..40,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Tighter header spacing */
    h1, h2, h3 { font-weight: 600; letter-spacing: -0.02em; }

    /* Remove default Streamlit padding bloat */
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }

    /* Cleaner metric cards */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stMetricLabel"] { font-size: 0.8rem; color: #64748b; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 600; color: #1e293b; }

    /* Sidebar clean-up */
    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    section[data-testid="stSidebar"], section[data-testid="stSidebar"] * {
        color: #1e293b !important;
    }

    /* Plotly chart containers */
    .js-plotly-plot { border-radius: 12px; }

    /* Status badge */
    .badge {
        display: inline-block;
        padding: 0.35rem 0.9rem;
        border-radius: 99px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.01em;
    }
    .badge-green  { background: #dcfce7; color: #166534; }
    .badge-amber  { background: #fef3c7; color: #92400e; }
    .badge-red    { background: #fee2e2; color: #991b1b; }
    .badge-blue   { background: #dbeafe; color: #1e40af; }
    .badge-gray   { background: #f1f5f9; color: #475569; }

    /* Ventilation banner */
    .vent-banner {
        padding: 1rem 1.25rem;
        border-radius: 12px;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .vent-open {
        background: #dcfce7;
        border-left: 4px solid #22c55e;
        color: #14532d;
    }
    .vent-closed {
        background: #f1f5f9;
        border-left: 4px solid #94a3b8;
        color: #334155;
    }

    /* Hide Streamlit branding and sidebar entirely */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    section[data-testid="stSidebar"] { display: none; }
    button[data-testid="collapsedControl"] { display: none; }
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def co2_badge(value):
    """Return an HTML badge coloured by CO₂ level."""
    if pd.isna(value):
        return '<span class="badge badge-gray">—</span>'
    v = float(value)
    if v < CO2_GREEN:
        cls = "badge-green"
    elif v < CO2_AMBER:
        cls = "badge-amber"
    else:
        cls = "badge-red"
    return f'<span class="badge {cls}">{v:,.0f} ppm</span>'
