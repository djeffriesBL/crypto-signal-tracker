import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ------------------------------
# 1) DATA LOADING
# ------------------------------

def load_mock_data():
    """Fallback mock CSV (last 3 days, >$10K) saved as 'insider_buys.csv'."""
    try:
        return pd.read_csv("insider_buys.csv")
    except FileNotFoundError:
        # If no local CSV, just return empty
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_insider_data(use_mock: bool, days_back: int, min_value: int):
    """
    If use_mock=True, load local CSV.
    Otherwise, attempt to fetch from OpenInsider URL (last N days, > min_value).
    """
    if use_mock:
        df = load_mock_data()
    else:
        # Construct the OpenInsider CSV URL for last 'days_back' days, buys > 'min_value'
        url = (
            f"https://openinsider.com/screener.csv?"
            f"s=&o=&pl=&ph=&ll=&lh=&fd=0&td=0"
            f"&daysago={days_back}&xp=1&vl={min_value}&vh=&sortcol=0&maxresults=1000"
        )
        try:
            df = pd.read_csv(url)
        except Exception as e:
            st.error(f"Failed to fetch live insider data: {e}")
            df = load_mock_data()
    # Standardize column names and filter only Purchase rows
    if "Trade Type" in df.columns:
        df = df.rename(columns={"Trade Type": "Trade_Type"})
    if "Ticker" in df.columns and "Trade_Type" in df.columns:
        df = df[df["Trade_Type"] == "Purchase"].copy()
    # Parse dates
    if "Trade Date" in df.columns:
        df["Trade Date"] = pd.to_datetime(df["Trade Date"], errors="coerce")
    if "Filing Date" in df.columns:
        df["Filing Date"] = pd.to_datetime(df["Filing Date"], errors="coerce")
    return df

# ------------------------------
# 2) SIGNAL & METRIC CALCULATIONS
# ------------------------------

def compute_most_bought(df):
    """
    Return a DataFrame of tickers sorted by count of insider buys in descending order.
    """
    if df.empty or "Ticker" not in df.columns:
        return pd.DataFrame(columns=["Ticker", "Buy Count"])
    counts = df["Ticker"].value_counts().reset_index()
    counts.columns = ["Ticker", "Buy Count"]
    return counts

def get_filings_for_ticker(df, ticker: str):
    """
    Return the subset of 'df' where Ticker == ticker, sorted by Trade Date descending.
    """
    sub = df[df["Ticker"] == ticker].copy()
    if "Trade Date" in sub.columns:
        sub = sub.sort_values("Trade Date", ascending=False)
    return sub

def simulate_returns_for_ticker(df_filings):
    """
    Given all filings for a single ticker (>=1 rows), compute average trade date,
    fetch price at that date and current price, and return a DataFrame with Return (%).
    """
    if df_filings.empty or "Trade Date" not in df_filings.columns:
        return pd.DataFrame()
    avg_date = df_filings["Trade Date"].dropna().mean().date()
    try:
        hist = yf.download(
            df_filings["Ticker"].iloc[0],
            start=avg_date.strftime("%Y-%m-%d"),
            end=datetime.now().strftime("%Y-%m-%d"),
            progress=False,
        )
        if hist.empty:
            return pd.DataFrame()
        entry = hist["Close"].iloc[0]
        latest = hist["Close"].iloc[-1]
        ret_pct = ((latest - entry) / entry) * 100
        return pd.DataFrame([{
            "Ticker": df_filings["Ticker"].iloc[0],
            "Avg_Trade_Date": avg_date,
            "Entry_Price": round(entry, 2),
            "Latest_Price": round(latest, 2),
            "Return (%)": round(ret_pct, 2),
        }])
    except Exception:
        return pd.DataFrame()

# ------------------------------
# 3) STREAMLIT UI
# ------------------------------

st.set_page_config(page_title="Insider‐Driven Stock Dashboard", layout="wide")
st.title("🏛️ Insider‐Driven Stock Dashboard")

with st.sidebar:
    st.header("⚙️ Settings")
    use_mock = st.checkbox("Use mock data (local CSV)", value=True)
    days_back = st.slider("Insider filings window (days)", 1, 30, 3)
    min_value = st.number_input("Min Buy Value ($)", min_value=1000, max_value=1_000_000, value=10000, step=1000)

# 1) Load insider data
df_insiders = fetch_insider_data(use_mock, days_back, min_value)

# 2) Show raw filings table
st.subheader("📋 Recent Insider Purchases")
if df_insiders.empty:
    st.warning("No insider purchase records in this window.")
else:
    # Show table, most‐recent first
    if "Trade Date" in df_insiders.columns:
        df_insiders = df_insiders.sort_values("Trade Date", ascending=False)
    st.dataframe(df_insiders, use_container_width=True)

# 3) Compute & display "Most Bought" summary
st.subheader("📊 Top Insider‐Bought Tickers")
df_counts = compute_most_bought(df_insiders)
if df_counts.empty:
    st.info("No tickers to display.")
else:
    st.dataframe(df_counts.head(10), use_container_width=True)
    # Bar chart for top 10
    st.bar_chart(df_counts.set_index("Ticker")["Buy Count"].head(10))

    # 4) Let user select one of these tickers to drill down
    tickers_list = df_counts["Ticker"].tolist()
    chosen_ticker = st.selectbox("🔎 Drill down into ticker:", [""] + tickers_list)
    if chosen_ticker:
        st.markdown(f"### Details for {chosen_ticker}")
        filings_for_ticker = get_filings_for_ticker(df_insiders, chosen_ticker)
        st.dataframe(filings_for_ticker, use_container_width=True)

        # 5) Show price chart + optional RSI/SMA (via yfinance)
        st.markdown(f"### {chosen_ticker} Price Chart (Since Avg Trade Date)")
        ret_df = simulate_returns_for_ticker(filings_for_ticker)
        if not ret_df.empty:
            avg_date = ret_df["Avg_Trade_Date"].iloc[0]
            st.write(f"- Average Insider Trade Date: **{avg_date}**")
            # Fetch and plot price from one day before avg_date to today
            try:
                hist = yf.download(
                    chosen_ticker,
                    start=(avg_date - timedelta(days=1)).strftime("%Y-%m-%d"),
                    end=datetime.now().strftime("%Y-%m-%d"),
                    progress=False,
                )
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(hist.index, hist["Close"], label="Close Price", linewidth=1.5)
                ax.axvline(avg_date, color="green", linestyle="--", label="Avg Trade Date")
                ax.set_title(f"{chosen_ticker} Price (from {avg_date - timedelta(days=1)} to today)")
                ax.set_ylabel("Price")
                ax.legend()
                st.pyplot(fig)
            except Exception:
                st.error("Failed to fetch price history for chart.")
            # Show Return %
            st.subheader("💰 Simulated Return Since Average Trade Date")
            st.dataframe(ret_df, use_container_width=True)
        else:
            st.info("Not enough data to simulate returns for this ticker.")

# 6) Optionally, show a portfolio view of all “clustered” tickers
st.subheader("💼 Simulated Portfolio: All Clustered Buys")
clustered = df_counts[df_counts["Buy Count"] >= 3]["Ticker"].tolist()
if clustered:
    st.write(f"Tickers with ≥ 3 insider buys: {', '.join(clustered)}")
    port_list = []
    for t in clustered:
        df_t = get_filings_for_ticker(df_insiders, t)
        ret = simulate_returns_for_ticker(df_t)
        if not ret.empty:
            port_list.append(ret.iloc[0])
    if port_list:
        df_portfolio = pd.DataFrame(port_list)
        st.dataframe(df_portfolio, use_container_width=True)
    else:
        st.info("No return data available for clustered tickers yet.")
else:
    st.info("No tickers have ≥ 3 insider buys in this window.")
