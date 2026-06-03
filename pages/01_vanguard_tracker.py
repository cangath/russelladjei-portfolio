import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json

# ============================================================================
# PAGE CONFIG - Fintech / Trading App Look
# ============================================================================
st.set_page_config(
    page_title="Vanguard Yield Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS to mimic a modern dark trading dashboard
st.markdown(
    """
    <style>
    /* Global background */
    .stApp {
        background: radial-gradient(circle at top left, #111827 0, #020617 50%, #000000 100%);
        color: #e5e7eb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    }

    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.08));
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        border: 1px solid rgba(55,65,81,0.8);
        box-shadow: 0 18px 40px rgba(0,0,0,0.5);
    }
    div[data-testid="metric-container"] > label {
        color: #9ca3af;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: .06em;
    }
    div[data-testid="metric-container"] > div {
        color: #f9fafb;
        font-size: 1.25rem;
        font-weight: 700;
    }

    /* Dataframe tweaks */
    .dataframe th, .dataframe td {
        color: #e5e7eb !important;
        border-color: #1f2937 !important;
    }

    /* Subheaders */
    h2, h3 {
        font-weight: 600;
        letter-spacing: .04em;
    }

    /* Selectbox label */
    label[data-baseweb="select"] {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: #9ca3af;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# DATA LOGIC
# ============================================================================
DATA_FILE = Path("/Users/russbook/Desktop/RNAdotCOM/testprod/data/vanguard_yields.json")


def load_yields() -> dict:
    """Load historical yield data from repository."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("⚠️ Data file corrupted, starting fresh")
            return {}
    return {}


# ============================================================================
# HEADER SECTION
# ============================================================================
st.title("📈 Vanguard Money Market Tracker")
st.markdown(
    "Real-time yield tracking powered by GitHub Actions • **Live Vanguard money market yields**"
)
st.divider()

# Load the data once at the start
data = load_yields()

if not data:
    st.error(
        "🚨 No data found in `data/vanguard_yields.json`. "
        "Please check your GitHub Action or upload a data file."
    )
    st.stop()

# Prepare DataFrame for calculations
rows = []
for ticker, fund_data in data.items():
    history = fund_data.get("history") or {}
    if history:
        latest_date = max(history.keys())
        latest_yield = history[latest_date]
        rows.append(
            {
                "Ticker": ticker,
                "Name": fund_data.get("name", ticker),
                "Latest Yield (%)": latest_yield,
                "Last Updated": latest_date,
            }
        )

df = pd.DataFrame(rows)
if df.empty:
    st.error("No history found for any fund in the dataset.")
    st.stop()

# Clean up and sort
df["Last Updated"] = pd.to_datetime(df["Last Updated"])
df = df.sort_values("Latest Yield (%)", ascending=False)
#df = df.head(6).reset_index(drop=True)
#limits to top six rows but i think we are good


# ============================================================================
# TOP METRICS ROW (Quiver-style stat cards)
# ============================================================================
top_fund = df.iloc[0]
avg_yield = df["Latest Yield (%)"].mean()
fund_count = len(df)
last_refresh = df["Last Updated"].max()

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    label="Top Yield Fund",
    value=f"{top_fund['Latest Yield (%)']:.2f}%",
    delta=top_fund["Ticker"],
)

m2.metric(
    label="Funds Tracked",
    value=f"{fund_count}",
)

m3.metric(
    label="Average Yield (All Funds)",
    value=f"{avg_yield:.2f}%",
)

m4.metric(
    label="Last Data Refresh",
    value=last_refresh.strftime("%Y-%m-%d"),
)

st.markdown("")

# ============================================================================
# MAIN LAYOUT: Table + Detail Chart
# ============================================================================
left, right = st.columns([2, 1])

with left:
    st.subheader("Money Market Yield Board")
    st.caption("Sorted by latest reported SEC yield (highest to lowest).")

display_df = df.copy()
display_df["Latest Yield (%)"] = display_df["Latest Yield (%)"].map(lambda x: f"{x:.2f}%")
display_df["Last Updated"] = display_df["Last Updated"].dt.strftime("%Y-%m-%d")

st.dataframe(
    display_df,
    use_container_width=True,
    #height=420,
    hide_index=True,
)

with right:
    st.subheader("Fund Focus")

    # Fund selector
    tickers = df["Ticker"].tolist()
    default_ticker = tickers[0]
    selected_ticker = st.selectbox(
        "Select fund",
        tickers,
        index=tickers.index(default_ticker),
    )

    fund_obj = data[selected_ticker]
    fund_name = fund_obj.get("name", selected_ticker)
    history = fund_obj.get("history") or {}

    if history:
        hist_df = (
            pd.DataFrame(
                {
                    "Date": pd.to_datetime(list(history.keys())),
                    "Yield (%)": list(history.values()),
                }
            )
            .sort_values("Date")
            .reset_index(drop=True)
        )

        latest_value = hist_df.iloc[-1]["Yield (%)"]

        st.metric(
            label=f"{selected_ticker} Latest Yield",
            value=f"{latest_value:.2f}%",
        )

        fig = px.area(
            hist_df,
            x="Date",
            y="Yield (%)",
            title=f"{fund_name} ({selected_ticker}) – Yield History",
            template="plotly_dark",
        )
        fig.update_traces(line_color="#22c55e")
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No historical data available for this fund yet.")

# ============================================================================
# FOOTER
# ============================================================================
st.caption(
    "Data sourced from Vanguard; yields shown are for informational purposes only and "
    "do not constitute investment advice."
)