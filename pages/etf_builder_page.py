#claudes  take on my etf builder.
"""
Custom ETF Builder  ·  v5
Streamlit app — equal-dollar and market-cap-weighted baskets from user tickers.
Prices via Financial Modeling Prep (FMP).

Key fix vs. prior version:
  Market-cap weighting now uses a proper buy-and-hold portfolio:
    1. Compute initial market cap for each ticker at t₀.
    2. Derive weights: w_i = mcap_i / Σ mcap.
    3. Buy units: units_i = (w_i × $100) / price_i(t₀).
    4. Portfolio value at t: Σ units_i × price_i(t)  → starts at exactly 100.
  The old formula produced a price-squared-weighted average, which is
  not a meaningful financial metric.
"""

from __future__ import annotations

import datetime as dt
import os
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Custom ETF Builder",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp { background: #0d1117; }
    .block-container { padding: 1.5rem 2.5rem 2rem; max-width: 1300px; }
    section[data-testid="stSidebar"] { background: #0d1117; }
    section[data-testid="stSidebar"] .block-container { padding: 1rem 1rem 1.5rem; }

    .etf-title {
        font-size: 1.85rem; font-weight: 800;
        letter-spacing: .06em; text-transform: uppercase;
        color: #f0f6fc; margin: 0 0 .15rem;
    }
    .etf-sub { font-size: .88rem; color: #8b949e; margin-bottom: .25rem; }

    div[data-testid="metric-container"] {
        background: rgba(22,27,34,0.95);
        border: 1px solid rgba(48,54,61,0.9);
        border-radius: .55rem;
        padding: .75rem 1rem;
    }
    div[data-testid="metric-container"] > label {
        color: #8b949e; font-size: .7rem;
        text-transform: uppercase; letter-spacing: .08em;
    }
    div[data-testid="metric-container"] > div {
        color: #f0f6fc; font-size: 1.2rem; font-weight: 700;
    }

    .stTabs [data-baseweb="tab-list"] { gap: .4rem; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }

    /* tighten sidebar headers */
    .sidebar-head { font-size: .95rem; font-weight: 700; color: #e6edf3; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_TICKERS = ["MAR", "HLT", "IHG", "H", "CHH", "ABNB", "EXPE"]

BENCHMARKS: Dict[str, str] = {
    "SPY": "S&P 500 (SPY)",
    "QQQ": "Nasdaq 100 (QQQ)",
    "DIA": "Dow Jones (DIA)",
    "VTI": "Total Market (VTI)",
    "VT": "Total World Market (VT)",
}

FMP = "https://financialmodelingprep.com"
URL_EOD_STABLE = f"{FMP}/stable/historical-price-eod/full"
URL_EOD_LEGACY = f"{FMP}/api/v3/historical-price-full"
URL_PROFILE    = f"{FMP}/stable/profile"
URL_FLOAT_V4   = f"{FMP}/api/v4/shares_float"
URL_KEYMET     = f"{FMP}/stable/key-metrics"

# Distinct colors: blue = EW ETF, green = MC ETF, then warm tones for benchmarks
# and a full palette for individual constituents
BLUE    = "#3b82f6"
GREEN   = "#10b981"
BENCH_COLORS = ["#f59e0b", "#f43f5e", "#8b5cf6", "#06b6d4", "#fb923c"]
PALETTE = [
    "#3b82f6","#10b981","#f59e0b","#f43f5e","#8b5cf6",
    "#06b6d4","#84cc16","#fb923c","#e11d48","#0ea5e9","#a78bfa",
]
GRID = "rgba(255,255,255,0.06)"

# === MARKET-CAP ETF SWITCH ====================================================
# Set this to False to COMPLETELY turn off the market-cap ETF logic:
# - No share-count API calls
# - No market-cap ETF line on charts
# - No market-cap weights table
USE_MARKET_CAP_ETF = True
# ==============================================================================

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "etf-builder/5.0"})

# ── API key ───────────────────────────────────────────────────────────────────
def _get_fmp_key() -> Optional[str]:
    k = os.environ.get("FMP_API_KEY")
    if k:
        return k
    try:
        return st.secrets.get("FMP_API_KEY")
    except Exception:
        return None

FMP_KEY = _get_fmp_key()
if not FMP_KEY:
    st.error(
        "**FMP_API_KEY not found.**  \n"
        "Add it to `.streamlit/secrets.toml` as `FMP_API_KEY = \"...\"` "
        "or set the environment variable."
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl="4h", show_spinner=False)
def fetch_prices(
    tickers: Tuple[str, ...],
    key: str,
    start: str,
    end: str,
) -> Tuple[Dict[str, pd.Series], List[str], List[Tuple[str, str]]]:
    """
    Fetch daily closing prices for each ticker.
    Returns (prices_dict, successful_tickers, issues_list).
    Tries stable endpoint first, falls back to legacy v3.
    """
    prices: Dict[str, pd.Series] = {}
    ok: List[str] = []
    issues: List[Tuple[str, str]] = []
    start_dt = pd.to_datetime(start)
    end_dt   = pd.to_datetime(end)

    endpoints = [
        (URL_EOD_STABLE, {"from": start, "to": end}),
        (URL_EOD_LEGACY, {"from": start, "to": end}),
    ]

    for i, sym in enumerate(tickers):
        if i:
            time.sleep(0.12)
        fetched = False

        for url, extra in endpoints:
            try:
                params = {"symbol": sym, "apikey": key, **extra}
                r = SESSION.get(url, params=params, timeout=30)
                r.raise_for_status()
                raw = r.json()

                # Legacy endpoint wraps in {"symbol":..., "historical":[...]}
                if isinstance(raw, dict):
                    if raw.get("Error Message"):
                        continue          # FMP error response — try next
                    raw = raw.get("historical", [])

                if not isinstance(raw, list) or not raw:
                    continue

                df = pd.DataFrame(raw)
                price_col = "adjClose" if "adjClose" in df.columns else "close"
                if "date" not in df.columns or price_col not in df.columns:
                    continue

                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
                df = (
                    df.dropna(subset=["date", price_col])
                      .sort_values("date")
                )
                df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
                if df.empty:
                    continue

                prices[sym] = df.set_index("date")[price_col]
                ok.append(sym)
                fetched = True
                break

            except Exception:
                continue

        if not fetched:
            issues.append((sym, "No price data returned from any FMP endpoint."))

    return prices, ok, issues


@st.cache_data(ttl="12h", show_spinner=False)
def fetch_shares(
    tickers: Tuple[str, ...],
    key: str,
) -> Tuple[Dict[str, float], List[Tuple[str, str]]]:
    """
    Fetch shares outstanding per ticker.

    Waterfall:
      1. stable/profile  → sharesOutstanding field
      2. stable/profile  → derive from mktCap ÷ price  (handles ABNB, CHH, EXPE
                            when sharesOutstanding is missing but mktCap is present)
      3. api/v4/shares_float → floatShares / outstandingShares
      4. stable/key-metrics → marketCap ÷ price
    """
    shares: Dict[str, float] = {}
    issues: List[Tuple[str, str]] = []

    for i, sym in enumerate(tickers):
        if i:
            time.sleep(0.12)
        got = False

        # ── 1 & 2. Stable profile ────────────────────────────────────────────
        try:
            r = SESSION.get(
                URL_PROFILE,
                params={"symbol": sym, "apikey": key},
                timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
            if isinstance(rows, list) and rows:
                row = rows[0]

                # Direct field
                so = row.get("sharesOutstanding")
                if so is not None:
                    val = float(so)
                    if val > 0:
                        shares[sym] = val
                        got = True

                # Derived from market cap ÷ current price
                if not got:
                    mktcap = row.get("mktCap") or row.get("marketCap")
                    price  = row.get("price")
                    if mktcap and price:
                        try:
                            derived = float(mktcap) / float(price)
                            if derived > 0:
                                shares[sym] = derived
                                got = True
                        except (TypeError, ZeroDivisionError):
                            pass
        except Exception:
            pass

        if got:
            continue

        # ── 3. api/v4/shares_float ───────────────────────────────────────────
        try:
            r = SESSION.get(
                URL_FLOAT_V4,
                params={"symbol": sym, "apikey": key},
                timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
            if isinstance(rows, list) and rows:
                row = rows[0]
                for field in ("sharesOutstanding", "outstandingShares", "floatShares"):
                    val = row.get(field)
                    if val:
                        fval = float(val)
                        if fval > 0:
                            shares[sym] = fval
                            got = True
                            break
        except Exception:
            pass

        if got:
            continue

        # ── 4. stable/key-metrics (last resort) ──────────────────────────────
        try:
            r = SESSION.get(
                URL_KEYMET,
                params={"symbol": sym, "limit": 1, "apikey": key},
                timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
            if isinstance(rows, list) and rows:
                row = rows[0]
                mktcap = row.get("marketCap")
                price  = row.get("stockPrice") or row.get("price")
                if mktcap and price:
                    derived = float(mktcap) / float(price)
                    if derived > 0:
                        shares[sym] = derived
                        got = True
        except Exception:
            pass

        if not got:
            issues.append((sym, "Could not retrieve shares outstanding from any endpoint."))

    return shares, issues


# ─────────────────────────────────────────────────────────────────────────────
#  PORTFOLIO MATH
# ─────────────────────────────────────────────────────────────────────────────

def build_portfolio(
    price_df: pd.DataFrame,
    tickers: List[str],
    weights: Dict[str, float],
    base_value: float = 100.0,
) -> pd.Series:
    """
    Buy-and-hold portfolio starting at base_value (default = 100).

    Algorithm
    ---------
    At t₀ = first date all tickers have a valid price:
        units_i = (weight_i × base_value) / price_i(t₀)

    Portfolio value at any future date t:
        V(t) = Σ_i  units_i × price_i(t)

    V(t₀) = Σ_i (weight_i × base_value) = base_value  ✓  (weights sum to 1)

    Forward-fill is applied first to close weekend / holiday gaps without
    introducing look-ahead bias (each missing day uses the last known price,
    which is what an investor holding the stock would observe).
    """
    subset = price_df[tickers].ffill()

    # Find t₀: first date every ticker has a non-NaN price
    valid = subset.dropna(how="any")
    if valid.empty:
        # Relax: use first date at least half the tickers are present
        valid = subset.dropna(thresh=max(1, len(tickers) // 2))
    if valid.empty:
        return pd.Series(dtype=float)

    t0 = valid.index[0]
    p0 = valid.iloc[0]  # Series: ticker → price at t₀

    # Compute units held in each ticker
    units: Dict[str, float] = {}
    for t in tickers:
        p = float(p0[t]) if t in p0.index else 0.0
        w = weights.get(t, 0.0)
        if p > 0 and w > 0:
            units[t] = (w * base_value) / p

    if not units:
        return pd.Series(dtype=float)

    # Time-series portfolio value
    portfolio = (
        subset[list(units.keys())]
        .mul(pd.Series(units), axis=1)
        .sum(axis=1, min_count=1)
    )

    # Re-normalise so t₀ is exactly base_value (floating-point safety)
    v0 = float(portfolio.loc[t0])
    if v0 == 0 or pd.isna(v0):
        return pd.Series(dtype=float)

    return portfolio * (base_value / v0)


def compute_mcap_weights(
    price_df: pd.DataFrame,
    tickers: List[str],
    shares: Dict[str, float],
) -> Dict[str, float]:
    """
    Market-cap weights at t₀ (the first date all tickers have price data).
    w_i = (price_i(t₀) × shares_i) / Σ_j (price_j(t₀) × shares_j)
    """
    subset = price_df[tickers].ffill()
    valid  = subset.dropna(how="any")
    if valid.empty:
        valid = subset.dropna(thresh=max(1, len(tickers) // 2))
    if valid.empty:
        return {}

    p0 = valid.iloc[0]
    mcaps: Dict[str, float] = {}
    for t in tickers:
        if t in shares and t in p0.index:
            p = float(p0[t])
            if p > 0:
                mcaps[t] = p * float(shares[t])

    total = sum(mcaps.values())
    return {t: v / total for t, v in mcaps.items()} if total > 0 else {}


def rebase_at(series: pd.Series, date: pd.Timestamp, base: float = 100.0) -> pd.Series:
    """Rebase a price series so it equals `base` at `date`."""
    after = series.loc[series.index >= date].dropna()
    if after.empty:
        return pd.Series(dtype=float)
    v0 = float(after.iloc[0])
    return (after / v0) * base if v0 else pd.Series(dtype=float)


def perf_stats(s: pd.Series, name: str) -> Dict:
    """Annualised return, volatility, and Sharpe from a base-100 series."""
    s = s.dropna()
    blank = {"Name": name, "Total Return": "–", "Ann. Return": "–",
             "Ann. Vol": "–", "Sharpe": "–", "Start Date": "–", "End Date": "–"}
    if len(s) < 5 or float(s.iloc[0]) == 0:
        return blank

    total = float(s.iloc[-1]) / float(s.iloc[0]) - 1
    years = (s.index[-1] - s.index[0]).days / 365.25
    ann_r = ((1 + total) ** (1 / years) - 1) if years > 0.05 else float("nan")
    daily = s.pct_change().dropna()
    ann_v = daily.std() * (252 ** 0.5) if len(daily) > 1 else float("nan")
    sharpe = ann_r / ann_v if (ann_v and ann_v > 0) else float("nan")

    def fmt(v: float, pct: bool = True) -> str:
        if pd.isna(v):
            return "–"
        return f"{v:.1%}" if pct else f"{v:.2f}"

    return {
        "Name":         name,
        "Start Date":   s.index[0].strftime("%Y-%m-%d"),
        "End Date":     s.index[-1].strftime("%Y-%m-%d"),
        "Total Return": fmt(total),
        "Ann. Return":  fmt(ann_r),
        "Ann. Vol":     fmt(ann_v),
        "Sharpe":       fmt(sharpe, pct=False),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_BASE_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="system-ui, -apple-system, sans-serif", size=12, color="#c9d1d9"),
    margin=dict(l=10, r=10, t=8, b=10),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.22,
        xanchor="left",
        x=0,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    ),
    xaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, showline=False),
    yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, showline=False),
    hovermode="x unified",
    height=430,
)


def make_line_chart(
    series_map: Dict[str, pd.Series],
    y_label: str = "",
    dashed_keys: Optional[List[str]] = None,
    colors: Optional[List[str]] = None,
    height: int = 430,
) -> go.Figure:
    """Return a styled Plotly line chart from a {label: Series} dict."""
    dashed_keys = dashed_keys or []
    colors = colors or PALETTE
    fig = go.Figure()

    for i, (name, s) in enumerate(series_map.items()):
        s = s.dropna()
        if s.empty:
            continue
        is_dashed = name in dashed_keys
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.round(2).values,
                name=name,
                mode="lines",
                line=dict(
                    color=colors[i % len(colors)],
                    width=1.8 if is_dashed else 2.6,
                    dash="dot" if is_dashed else "solid",
                ),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<extra></extra>",
            )
        )

    layout = {**_BASE_LAYOUT, "height": height}
    if y_label:
        layout["yaxis"] = {
            **_BASE_LAYOUT["yaxis"],
            "title": dict(text=y_label, font=dict(size=11)),
        }
    fig.update_layout(**layout)
    return fig


def make_area_chart(s: pd.Series, name: str, color: str, height: int = 200) -> go.Figure:
    """Single-series area chart (for spread views)."""
    s = s.dropna()
    fig = go.Figure(
        go.Scatter(
            x=s.index,
            y=s.round(2).values,
            name=name,
            mode="lines",
            fill="tozeroy",
            line=dict(color=color, width=1.6),
            # Use rgba if color already rgb(...); otherwise just reuse the hex.
            # (Avoid invalid 8-digit hex like "#10b9811f" which caused the error.)
            fillcolor=color.replace(")", ",0.12)").replace("rgb", "rgba") if "rgb" in color else color,
            hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<extra></extra>",
        )
    )
    layout = {**_BASE_LAYOUT, "height": height}
    layout.pop("legend", None)
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ ETF Configuration")

    raw_tickers = st.text_area(
        "Tickers (comma-separated)",
        ",".join(DEFAULT_TICKERS),
        height=90,
        help="Any valid US equity tickers separated by commas.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("Start", dt.date.today() - dt.timedelta(days=730))
    with col_b:
        end_date = st.date_input("End", dt.date.today() - dt.timedelta(days=1))

    bench_sel = st.multiselect(
        "Benchmark overlays",
        list(BENCHMARKS.keys()),
        default=["SPY", "QQQ"],
        format_func=lambda x: BENCHMARKS[x],
    )

    st.divider()
    if st.button("🔄 Clear cache & rerun", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDATE INPUTS
# ─────────────────────────────────────────────────────────────────────────────
user_tickers = sorted({t.strip().upper() for t in raw_tickers.split(",") if t.strip()})
if not user_tickers:
    st.warning("Enter at least one ticker.")
    st.stop()
if start_date >= end_date:
    st.error("Start date must be before end date.")
    st.stop()

start_s   = start_date.strftime("%Y-%m-%d")
end_s     = end_date.strftime("%Y-%m-%d")
all_syms  = tuple(sorted(set(user_tickers + bench_sel)))


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="etf-title">📊 Custom ETF Builder</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="etf-sub">Equal-dollar and market-cap-weighted baskets · '
    'prices via Financial Modeling Prep</p>',
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
#  FETCH DATA
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner(f"Fetching prices for {len(all_syms)} symbols…"):
    all_prices, price_ok, price_issues = fetch_prices(all_syms, FMP_KEY, start_s, end_s)

if USE_MARKET_CAP_ETF:
    with st.spinner("Fetching share counts for market-cap weighting…"):
        shares_dict, shares_issues = fetch_shares(tuple(user_tickers), FMP_KEY)
else:
    shares_dict, shares_issues = {}, []

# Push warnings to sidebar (collapsible, so they don't clutter the page)
with st.sidebar:
    if price_issues:
        with st.expander(f"⚠️ Price warnings ({len(price_issues)})"):
            for t, msg in price_issues:
                st.warning(f"**{t}**: {msg}")
    if USE_MARKET_CAP_ETF and shares_issues:
        with st.expander(f"ℹ️ Shares warnings ({len(shares_issues)})"):
            for t, msg in shares_issues:
                st.info(f"**{t}**: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
#  BUILD PRICE DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
custom_prices_map = {t: all_prices[t] for t in user_tickers if t in all_prices}
if not custom_prices_map:
    st.error("No price data returned for your tickers. Check ticker symbols and date range.")
    st.stop()

price_df = pd.DataFrame(custom_prices_map).sort_index()
valid_tickers = [c for c in price_df.columns if not price_df[c].dropna().empty]
if not valid_tickers:
    st.error("All tickers returned empty price series.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  BUILD EQUAL-DOLLAR ETF
# ─────────────────────────────────────────────────────────────────────────────
n = len(valid_tickers)
ew_weights_map = {t: 1.0 / n for t in valid_tickers}
ew_series = build_portfolio(price_df, valid_tickers, ew_weights_map)


# ─────────────────────────────────────────────────────────────────────────────
#  BUILD MARKET-CAP ETF
# ─────────────────────────────────────────────────────────────────────────────
mc_tickers = [t for t in valid_tickers if t in shares_dict] if USE_MARKET_CAP_ETF else []
mc_series: Optional[pd.Series] = None
mc_weights_map: Dict[str, float] = {}
has_mc = False

if USE_MARKET_CAP_ETF and len(mc_tickers) >= 2:
    mc_weights_map = compute_mcap_weights(price_df, mc_tickers, shares_dict)
    if mc_weights_map:
        mc_series = build_portfolio(price_df, mc_tickers, mc_weights_map)
        if mc_series is not None and not mc_series.empty:
            has_mc = True

if USE_MARKET_CAP_ETF and not has_mc:
    missing = [t for t in valid_tickers if t not in shares_dict]
    with st.sidebar:
        st.warning(
            f"Market-cap ETF unavailable — need ≥ 2 tickers with share data.  \n"
            f"Missing: {', '.join(missing) or 'none'}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  NORMALISE BENCHMARKS (align to EW ETF start date)
# ─────────────────────────────────────────────────────────────────────────────
bench_norm: Dict[str, pd.Series] = {}
ew_t0: Optional[pd.Timestamp] = None

if not ew_series.empty:
    ew_t0 = ew_series.dropna().index[0]
    for b in bench_sel:
        if b not in all_prices or all_prices[b].empty:
            continue
        s = rebase_at(all_prices[b], ew_t0)
        if not s.empty:
            bench_norm[BENCHMARKS[b]] = s


# ─────────────────────────────────────────────────────────────────────────────
#  METRICS ROW
# ─────────────────────────────────────────────────────────────────────────────
latest = price_df.index.max()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Constituents", len(valid_tickers))
m2.metric("Date range", f"{start_s[:7]} → {end_s[:7]}")
m3.metric("Last price date", latest.strftime("%Y-%m-%d") if pd.notna(latest) else "–")
m4.metric(
    "Weighting",
    "Equal-dollar + Market-cap" if has_mc else "Equal-dollar only",
)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(
    ["📈 ETF Performance", "🧩 Constituents", "📋 Stats & Weights"]
)


# ── Tab 1: ETF Performance ────────────────────────────────────────────────────
with tab1:
    st.caption(
        "All series start at **100** at the ETF's inception date. "
        "Dashed lines = benchmark overlays."
    )

    perf_map: Dict[str, pd.Series] = {}
    perf_colors: List[str] = []
    dashed_labels: List[str] = []

    if not ew_series.empty:
        perf_map["Equal-Dollar ETF"] = ew_series
        perf_colors.append(BLUE)

    if has_mc and mc_series is not None:
        perf_map["Market-Cap ETF"] = mc_series
        perf_colors.append(GREEN)

    for j, (label, s) in enumerate(bench_norm.items()):
        perf_map[label] = s
        perf_colors.append(BENCH_COLORS[j % len(BENCH_COLORS)])
        dashed_labels.append(label)

    if perf_map:
        fig1 = make_line_chart(
            perf_map,
            y_label="Portfolio value (base = 100)",
            dashed_keys=dashed_labels,
            colors=perf_colors,
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("No ETF data to display.")

    # Dedicated Market-cap ETF chart right under the main chart
    if has_mc and mc_series is not None:
        st.markdown("#### Market-Cap ETF (solo view)")
        mc_only_map: Dict[str, pd.Series] = {"Market-Cap ETF": mc_series}
        fig_mc_only = make_line_chart(
            mc_only_map,
            y_label="Portfolio value (base = 100)",
            colors=[GREEN],
            height=320,
        )
        st.plotly_chart(fig_mc_only, use_container_width=True)

    # Market-cap vs Equal-dollar spread (collapsed by default)
    if has_mc and mc_series is not None and not ew_series.empty:
        common_idx = ew_series.dropna().index.intersection(mc_series.dropna().index)
        if len(common_idx) > 5:
            spread = (mc_series.loc[common_idx] - ew_series.loc[common_idx]).round(3)
            with st.expander("Market-Cap vs Equal-Dollar spread"):
                fig_spread = make_area_chart(
                    spread, "MC − EW (index points)", color=GREEN, height=200
                )
                st.plotly_chart(fig_spread, use_container_width=True)
                st.caption(
                    "Positive = market-cap ETF outperforming equal-dollar. "
                    "Both portfolios start at 100 at the equal-dollar ETF's inception date."
                )


# ── Tab 2: Constituents ───────────────────────────────────────────────────────
with tab2:
    st.caption(
        "Individual stocks normalised to 100 at the same inception date as the ETF. "
        "Use this to see which names drove performance."
    )

    cons_map: Dict[str, pd.Series] = {}
    if ew_t0 is not None:
        for t in valid_tickers:
            s = rebase_at(price_df[t], ew_t0)
            if not s.empty:
                cons_map[t] = s

    if cons_map:
        fig2 = make_line_chart(cons_map, y_label="Normalised price (base = 100)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No constituent data to display.")


# ── Tab 3: Stats & Weights ────────────────────────────────────────────────────
with tab3:

    # ── Performance table ─────────────────────────────────────────────────────
    st.subheader("Performance statistics")
    stat_rows: List[Dict] = []

    if not ew_series.empty:
        stat_rows.append(perf_stats(ew_series, "Equal-Dollar ETF"))
    if has_mc and mc_series is not None:
        stat_rows.append(perf_stats(mc_series, "Market-Cap ETF"))
    for label, s in bench_norm.items():
        stat_rows.append(perf_stats(s, label))
    if ew_t0 is not None:
        for t in sorted(valid_tickers):
            s = rebase_at(price_df[t], ew_t0)
            if not s.empty:
                stat_rows.append(perf_stats(s, t))

    if stat_rows:
        st.dataframe(
            pd.DataFrame(stat_rows).set_index("Name"),
            use_container_width=True,
        )

    st.divider()

    # ── Market-cap weight table ───────────────────────────────────────────────
    if USE_MARKET_CAP_ETF and mc_weights_map:
        st.subheader("Market-cap weights at inception")

        wt_rows = []
        mc_t0 = None
        if mc_series is not None and not mc_series.empty:
            mc_t0 = mc_series.dropna().index[0]

        for t, w in sorted(mc_weights_map.items(), key=lambda x: -x[1]):
            p0_val = float(price_df[t].dropna().iloc[0]) if not price_df[t].dropna().empty else 0.0
            mcap_b = p0_val * float(shares_dict.get(t, 0)) / 1e9
            wt_rows.append({
                "Ticker":         t,
                "Weight":         f"{w:.2%}",
                "Est. Mkt Cap":   f"${mcap_b:.1f}B",
                "Shares (M)":     f"{shares_dict.get(t, 0)/1e6:,.0f}",
            })

        st.dataframe(
            pd.DataFrame(wt_rows).set_index("Ticker"),
            use_container_width=True,
        )
        st.caption(
            f"Weights fixed at inception ({mc_t0.strftime('%Y-%m-%d') if mc_t0 else 'N/A'}) "
            "using a buy-and-hold approach. "
            "Market cap = price × shares outstanding sourced from FMP."
        )
    elif USE_MARKET_CAP_ETF and not has_mc:
        st.info(
            "Market-cap weights unavailable. "
            "Insufficient `sharesOutstanding` data was returned from FMP for "
            f"these tickers: {', '.join(sorted(set(valid_tickers) - set(shares_dict.keys())))}."
        )

    st.divider()

    # ── Raw data + download ───────────────────────────────────────────────────
    st.subheader("Raw price data (last 30 trading days)")
    st.dataframe(
        price_df.tail(30).style.format("{:.2f}", na_rep="–"),
        use_container_width=True,
    )

    st.download_button(
        label="⬇️ Download full price CSV",
        data=price_df.to_csv().encode(),
        file_name=f"etf_builder_prices_{start_s}_to_{end_s}.csv",
        mime="text/csv",
        use_container_width=True,
    )