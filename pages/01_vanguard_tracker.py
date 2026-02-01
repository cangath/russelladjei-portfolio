"""Vanguard Money Market Fund Tracker - Optimized for GitHub + Streamlit Cloud"""
import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import os

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Vanguard MM Tracker",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Vanguard Money Market Fund Tracker")
st.markdown("Auto-updated daily via GitHub Actions • Data persisted in repository")

# ============================================================================
# DATA STORAGE - Optimized for GitHub
# ============================================================================
DATA_FILE = Path("data/vanguard_yields.json")

def load_yields():
    """Load historical yield data from repository"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("⚠️ Data file corrupted, starting fresh")
            return {}
    return {}

def save_yields(data):
    """Save yield data locally (for manual testing)"""
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    st.toast(f"✅ Saved yields locally")

def add_yield(ticker: str, name: str, yield_val: float, date: str = None):
    """Add a yield entry"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    data = load_yields()
    if ticker not in data:
        data[ticker] = {
            "name": name,
            "history": {}
        }
    data[ticker]["history"][date] = yield_val
    save_yields(data)
    st.toast(f"✅ Added {ticker}: {yield_val}% on {date}")

# ============================================================================
# VANGUARD FUNDS
# ============================================================================
VANGUARD_FUNDS = {
    'VMRXX': 'Vanguard Cash Reserves Federal Money Market Fund',
    'VMFXX': 'Vanguard Federal Money Market Fund',
    'VUSXX': 'Vanguard Treasury Money Market Fund',
    'VMSXX': 'Vanguard Municipal Money Market Fund',
    'VCTXX': 'Vanguard California Municipal Money Market Fund',
    'VYFXX': 'Vanguard New York Municipal Money Market Fund'
}

# ============================================================================
# SIDEBAR - Manual Entry Only (auto-scrape handled by GitHub Actions)
# ============================================================================
st.sidebar.header("⚙️ Controls")

with st.sidebar:
    st.subheader("📝 Manual Entry")
    st.info("💡 Auto-scraping runs daily via GitHub Actions\n\nUse this to manually add/update yields")
    
    ticker = st.selectbox(
        "Fund Ticker",
        options=list(VANGUARD_FUNDS.keys()),
        format_func=lambda x: f"{x} - {VANGUARD_FUNDS[x][:40]}..."
    )
    yield_val = st.number_input("7-Day SEC Yield (%)", min_value=0.0, max_value=10.0, step=0.01)
    
    if st.button("➕ Add Manual Entry", width='stretch'):
        add_yield(ticker, VANGUARD_FUNDS[ticker], yield_val)
        st.rerun()
    
    st.divider()
    
    st.subheader("📥 Data Export")
    if st.button("📥 Export as JSON", width='stretch'):
        data = load_yields()
        json_str = json.dumps(data, indent=2)
        st.download_button(
            "Download JSON",
            data=json_str,
            file_name=f"vanguard_yields_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
    
    st.divider()
    
    st.subheader("⚙️ Settings")
    if st.button("🗑️ Clear All Data", width='stretch'):
        DATA_FILE.unlink(missing_ok=True)
        st.toast("✅ Data cleared")
        st.rerun()

# ============================================================================
# MAIN TABS
# ============================================================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Trends", "ℹ️ Info"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Current Vanguard Money Market Yields")
    
    data = load_yields()
    
    if data:
        # Build DataFrame
        rows = []
        for ticker, fund_data in data.items():
            if fund_data.get("history"):
                latest_date = max(fund_data["history"].keys())
                latest_yield = fund_data["history"][latest_date]
                rows.append({
                    "Ticker": ticker,
                    "Name": fund_data["name"],
                    "Latest Yield (%)": latest_yield,
                    "Last Updated": latest_date
                })
        
        if rows:
            df = pd.DataFrame(rows)
            df = df.sort_values("Latest Yield (%)", ascending=False)
            
            st.dataframe(df, width='stretch', hide_index=True)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Yield", f"{df['Latest Yield (%)'].mean():.3f}%")
            with col2:
                max_val = df['Latest Yield (%)'].max()
                best = df.loc[df['Latest Yield (%)'].idxmax(), 'Ticker']
                st.metric("Highest", f"{max_val:.3f}%", best)
            with col3:
                min_val = df['Latest Yield (%)'].min()
                worst = df.loc[df['Latest Yield (%)'].idxmin(), 'Ticker']
                st.metric("Lowest", f"{min_val:.3f}%", worst)
            with col4:
                st.metric("Funds Tracked", len(df))
            
            # Bar chart
            st.subheader("Yield Comparison")
            chart_data = df.set_index("Ticker")[["Latest Yield (%)"]]
            st.bar_chart(chart_data)
        else:
            st.info("No yields recorded yet.")
    else:
        st.info("📊 No data yet. Add yields manually or wait for GitHub Actions auto-scrape (runs daily at 9 AM EST)")

# --- TAB 2: TRENDS ---
with tab2:
    st.subheader("Yield Trends Over Time")
    
    data = load_yields()
    tickers = list(data.keys())
    
    if tickers:
        selected = st.multiselect(
            "Select funds to compare",
            options=tickers,
            default=tickers[:min(3, len(tickers))]
        )
        
        if selected:
            # Build historical DataFrame
            rows = []
            for ticker in selected:
                for date, yield_val in data[ticker]["history"].items():
                    rows.append({
                        "Date": pd.to_datetime(date),
                        "Ticker": ticker,
                        "Yield": yield_val
                    })
            
            if rows:
                df_hist = pd.DataFrame(rows).sort_values("Date")
                pivot_df = df_hist.pivot(index="Date", columns="Ticker", values="Yield")
                
                st.line_chart(pivot_df)
                
                # Statistics
                st.subheader("Fund Statistics")
                for ticker in selected:
                    ticker_data = df_hist[df_hist["Ticker"] == ticker]
                    if not ticker_data.empty:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(f"{ticker} Latest", f"{ticker_data['Yield'].iloc[-1]:.3f}%")
                        with col2:
                            st.metric(f"{ticker} Avg", f"{ticker_data['Yield'].mean():.3f}%")
                        with col3:
                            st.metric(f"{ticker} Max", f"{ticker_data['Yield'].max():.3f}%")
                        with col4:
                            st.metric(f"{ticker} Min", f"{ticker_data['Yield'].min():.3f}%")
    else:
        st.info("No historical data yet.")

# --- TAB 3: INFO ---
with tab3:
    st.subheader("About This Tracker")
    st.markdown("""
    ### What is 7-Day SEC Yield?
    The 7-day SEC yield is an **annualized yield** calculated from a fund's net investment income 
    over the past 7 days. It's standardized by the SEC.
    
    ### Vanguard Funds Tracked
    """)
    
    for ticker, name in VANGUARD_FUNDS.items():
        st.write(f"- **{ticker}**: {name}")
    
    st.markdown("""
    ### How to Use
    1. **Auto-Updates**: GitHub Actions runs daily at 9 AM EST
    2. **Dashboard**: View current rates and average yield
    3. **Trends**: Compare historical patterns across funds
    4. **Export**: Download data as JSON
    
    ### Data Storage
    All data is stored in GitHub repository at `data/vanguard_yields.json`
    
    ### GitHub Actions Automation
    Daily scraper runs automatically:
    - Fetches latest yields from Vanguard
    - Updates JSON file
    - Commits to repository
    - Streamlit Cloud auto-reloads with new data
    
    ### Manual Updates
    You can manually add yields via the sidebar if needed
    
    ### Note on Weekend Updates
    Vanguard updates yields on market days (Mon-Fri). On weekends, the dashboard displays the most recent market day's data.
    """)
    
    st.divider()
    
    st.info("""
    **💡 Pro Tip**: This app auto-deploys whenever new data is pushed to GitHub!
    
    Your data pipeline:
    1. GitHub Actions runs scraper daily
    2. Updates vanguard_yields.json
    3. Commits + pushes to repo
    4. Streamlit Cloud auto-deploys
    5. Your visitors see fresh data instantly ✨
    """)
