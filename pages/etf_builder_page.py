import streamlit as st
import pandas as pd
import requests
import datetime as dt
import time
from typing import Dict, List, Tuple, Any

st.set_page_config(page_title="Custom ETF Builder (FMP Stable)", layout="wide", initial_sidebar_state="expanded")
st.title("📈 Custom ETF Builder")
st.caption("Stable-only Financial Modeling Prep version with visible API diagnostics")

st.markdown("""
This version uses Financial Modeling Prep's stable historical EOD route only.
It does not fall back to legacy endpoints, so you can see the real response from your current key and plan.
""")
st.markdown("---")

FMP_API_KEY = None
try:
    FMP_API_KEY = st.secrets.get("FMP_API_KEY")
except Exception:
    FMP_API_KEY = None

if not FMP_API_KEY:
    st.sidebar.error("`FMP_API_KEY` is missing from Streamlit secrets.")
    st.error("No API key found. Add FMP_API_KEY to your Streamlit secrets.toml file.")
    st.stop()

DEFAULT_TICKERS = ["MAR", "HLT", "IHG", "H", "CHH", "ABNB", "EXPE"]
DEFAULT_CUSTOM_TICKERS_STRING = ",".join(DEFAULT_TICKERS)

BENCHMARK_ETFS = {
    "VOO": "S&P 500 (VOO)",
    "DIA": "Dow Jones Industrial Average (DIA)",
    "QQQ": "Nasdaq 100 (QQQ)",
}

STABLE_EOD_URL = "https://financialmodelingprep.com/stable/historical-price-eod/full"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "portfolio-etf-builder-stable/1.0"})


def summarize_payload(data: Any) -> str:
    if isinstance(data, list):
        return f"list[{len(data)}]"
    if isinstance(data, dict):
        return "dict{" + ", ".join(list(data.keys())[:8]) + ("..." if len(data.keys()) > 8 else "") + "}"
    return type(data).__name__


@st.cache_data(ttl="4h", show_spinner=False)
def fetch_stable_daily_prices(tickers_tuple: Tuple[str, ...], api_key: str, start_date: str, end_date: str):
    all_prices: Dict[str, pd.Series] = {}
    successes: List[str] = []
    issues: List[Tuple[str, str]] = []
    diagnostics: List[dict] = []

    for i, ticker in enumerate(tickers_tuple):
        if i > 0:
            time.sleep(0.15)

        params = {
            "symbol": ticker,
            "from": start_date,
            "to": end_date,
            "apikey": api_key,
        }

        try:
            response = SESSION.get(STABLE_EOD_URL, params=params, timeout=30)
            raw_text = response.text[:400]
            diagnostics.append({
                "ticker": ticker,
                "status_code": response.status_code,
                "url": response.url,
                "body_preview": raw_text,
            })

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and data.get("Error Message"):
                issues.append((ticker, f"FMP API error: {data['Error Message']}"))
                continue

            if not isinstance(data, list):
                issues.append((ticker, f"Unexpected stable response shape: {summarize_payload(data)}"))
                continue

            if not data:
                issues.append((ticker, "Stable endpoint returned an empty list for this symbol/date range."))
                continue

            df = pd.DataFrame(data)
            if "date" not in df.columns or "close" not in df.columns:
                issues.append((ticker, f"Stable endpoint missing required columns. Returned columns: {', '.join(df.columns.astype(str).tolist())}"))
                continue

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["date", "close"]).sort_values("date")

            if df.empty:
                issues.append((ticker, "Stable endpoint data became empty after cleaning."))
                continue

            all_prices[ticker] = df.set_index("date")["close"]
            successes.append(ticker)

        except requests.exceptions.HTTPError:
            issues.append((ticker, f"HTTP {response.status_code}: {raw_text}"))
        except requests.exceptions.RequestException as e:
            issues.append((ticker, f"Request error: {e}"))
        except ValueError as e:
            issues.append((ticker, f"JSON parse error: {e}. Body preview: {raw_text}"))
        except Exception as e:
            issues.append((ticker, f"General error: {e}"))

    return all_prices, successes, issues, diagnostics


st.sidebar.header("🛠️ ETF Configuration")
raw_tickers_input = st.sidebar.text_area(
    "Custom ETF stock tickers (comma-separated)",
    DEFAULT_CUSTOM_TICKERS_STRING,
    height=100,
)

default_start_date = dt.date.today() - dt.timedelta(days=365 * 2)
default_end_date = dt.date.today() - dt.timedelta(days=1)
start_date_input = st.sidebar.date_input("Start date", default_start_date)
end_date_input = st.sidebar.date_input("End date", default_end_date)

selected_benchmarks_for_overlay = st.sidebar.multiselect(
    "Compare with benchmarks",
    options=list(BENCHMARK_ETFS.keys()),
    default=["VOO", "QQQ"],
    format_func=lambda x: BENCHMARK_ETFS[x],
)

show_debug = st.sidebar.checkbox("Show API diagnostics", value=True)

st.sidebar.write("---")
if st.sidebar.button("Clear cached data and rerun"):
    st.cache_data.clear()
    st.rerun()

user_tickers_list = sorted({t.strip().upper() for t in raw_tickers_input.split(",") if t.strip()})
if not user_tickers_list:
    st.warning("Enter at least one stock ticker.")
    st.stop()

if start_date_input >= end_date_input:
    st.error("Start date must be before end date.")
    st.stop()

symbols_to_fetch = tuple(sorted(set(user_tickers_list + selected_benchmarks_for_overlay)))
price_start = start_date_input.strftime("%Y-%m-%d")
price_end = end_date_input.strftime("%Y-%m-%d")

with st.spinner(f"Calling FMP stable EOD endpoint for {len(symbols_to_fetch)} symbols..."):
    all_prices, successful_fetches, fetch_issues, diagnostics = fetch_stable_daily_prices(
        symbols_to_fetch, FMP_API_KEY, price_start, price_end
    )

if fetch_issues:
    st.sidebar.subheader("⚠️ Stable endpoint issues")
    for ticker, message in fetch_issues:
        st.sidebar.warning(f"{ticker}: {message}")

if show_debug and diagnostics:
    st.subheader("API diagnostics")
    debug_df = pd.DataFrame(diagnostics)
    st.dataframe(debug_df, use_container_width=True)

custom_prices = {
    t: all_prices[t]
    for t in user_tickers_list
    if t in successful_fetches and t in all_prices and not all_prices[t].empty
}

if not custom_prices:
    st.error("No custom ETF prices were returned from the stable endpoint. Use the diagnostics table above to inspect the exact response.")
    st.stop()

custom_df = pd.DataFrame(custom_prices).sort_index().dropna(how="all")
if custom_df.empty:
    st.error("No overlapping custom ticker data exists in the selected date range.")
    st.stop()

valid_custom_tickers = [c for c in custom_df.columns if not custom_df[c].dropna().empty]
if not valid_custom_tickers:
    st.error("No valid custom ETF constituents remained after cleaning the stable-endpoint data.")
    st.stop()

custom_df["Portfolio Sum"] = custom_df[valid_custom_tickers].sum(axis=1, min_count=1)
custom_df["My Custom ETF"] = custom_df["Portfolio Sum"] / len(valid_custom_tickers)

st.header("ETF performance")
st.caption(f"Constituents used: {', '.join(valid_custom_tickers)}")

main_chart_df = pd.DataFrame(index=custom_df.index)
main_chart_df["My Custom ETF"] = custom_df["My Custom ETF"]

for bench in selected_benchmarks_for_overlay:
    if bench in all_prices and not all_prices[bench].empty:
        main_chart_df[f"{bench} ({BENCHMARK_ETFS[bench]})"] = all_prices[bench].reindex(main_chart_df.index)

plot_df = main_chart_df.dropna(how="all")
if plot_df.empty:
    st.warning("There was not enough data to draw the ETF chart.")
else:
    st.line_chart(plot_df)
    st.subheader("Recent data")
    st.dataframe(custom_df[valid_custom_tickers + ["My Custom ETF"]].tail(), use_container_width=True)

st.markdown("---")
st.header("Normalized growth")
st.caption("Each line starts at 100 so relative growth can be compared across the ETF, constituents, and benchmarks.")

series_list = []
for ticker in valid_custom_tickers:
    s = custom_df[ticker].copy()
    s.name = ticker
    series_list.append(s)

etf_series = custom_df["My Custom ETF"].copy()
etf_series.name = "My Custom ETF"
series_list.append(etf_series)

for bench in selected_benchmarks_for_overlay:
    if bench in all_prices and not all_prices[bench].empty:
        s = all_prices[bench].reindex(custom_df.index)
        s.name = f"{bench} ({BENCHMARK_ETFS[bench]})"
        series_list.append(s)

comparison_df = pd.concat(series_list, axis=1).dropna(how="all") if series_list else pd.DataFrame()
if comparison_df.empty:
    st.warning("Not enough overlapping data for normalized growth.")
else:
    normalized_df = pd.DataFrame(index=comparison_df.index)
    for col in comparison_df.columns:
        valid = comparison_df[col].dropna()
        if valid.empty:
            continue
        base = valid.iloc[0]
        if pd.notna(base) and base != 0:
            normalized_df[col] = (comparison_df[col] / base) * 100
    normalized_df = normalized_df.dropna(how="all", axis=1)
    if normalized_df.empty:
        st.warning("Normalization failed because no valid base values were available.")
    else:
        st.line_chart(normalized_df)

st.markdown("---")
st.info("Stable-only mode. No legacy FMP endpoints are called in this file.")
