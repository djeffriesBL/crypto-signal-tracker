import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ----------------------------------
#  CONFIGURATION
# ----------------------------------

# 1) Alpha Vantage API key for price lookups
ALPHA_VANTAGE_KEY = "YOUR_ALPHA_VANTAGE_KEY_HERE"

# 2) Local CSV filename for insider data
INSIDER_CSV = "insider_buys.csv"


# ----------------------------------
#  ALPHA VANTAGE “STOCK SEARCH” TAB
# ----------------------------------

def fetch_intraday_av(symbol: str, interval: str) -> pd.DataFrame:
    """
    Fetch intraday time series from Alpha Vantage for 'symbol' at 'interval'.
    Returns a DataFrame with columns: Open, High, Low, Close, Volume (indexed by datetime).
    """
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_INTRADAY"
        f"&symbol={symbol}&interval={interval}"
        f"&apikey={ALPHA_VANTAGE_KEY}&outputsize=compact"
    )
    r = requests.get(url)
    data = r.json()
    key = f"Time Series ({interval})"
    if key not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data[key]).T
    df = df.rename(columns={
        "1. open": "Open",
        "2. high": "High",
        "3. low":  "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    }).astype(float)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame with a 'Close' column, compute SMA (20) and RSI (14)
    and return the augmented DataFrame.
    """
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


# ----------------------------------
#  OPENINSIDER INSIDER‐DATA TAB
# ----------------------------------

def load_mock_data() -> pd.DataFrame:
    """
    Load a local CSV of insider buys (fallback).
    """
    try:
        df = pd.read_csv(INSIDER_CSV)
    except FileNotFoundError:
        df = pd.DataFrame()
    return df

@st.cache_data(ttl=3600)
def fetch_insider_data(use_mock: bool, days_back: int, min_value: int) -> pd.DataFrame:
    """
    If use_mock is True, load local CSV.
    Otherwise, attempt to fetch live from OpenInsider for the last 'days_back' days,
    filtering for insider purchases over 'min_value'. On failure, revert to mock.
    """
    if use_mock:
        return load_mock_data()

    url = (
        "https://openinsider.com/screener.csv?"
        f"s=&o=&pl=&ph=&ll=&lh=&fd=0&td=0"
        f"&daysago={days_back}&xp=1&vl={min_value}&vh=&sortcol=0&maxresults=1000"
    )
    try:
        df = pd.read_csv(url)
    except Exception:
        st.warning("⚠️ Could not fetch live insider data. Reverting to mock dataset.")
        return load_mock_data()

    # Only keep “Purchase” trades
    if "Trade Type" in df.columns:
        df = df[df["Trade Type"] == "Purchase"].copy()
    # Parse dates
    if "Trade Date" in df.columns:
        df["Trade Date"] = pd.to_datetime(df["Trade Date"], errors="coerce")
    if "Filing Date" in df.columns:
        df["Filing Date"] = pd.to_datetime(df["Filing Date"], errors="coerce")
    return df

def compute_most_bought(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count how many insider purchases per ticker, return DataFrame sorted desc.
    """
    if df.empty or "Ticker" not in df.columns:
        return pd.DataFrame(columns=["Ticker", "Buy Count"])
    counts = df["Ticker"].value_counts().reset_index()
    counts.columns = ["Ticker", "Buy Count"]
    return counts

def get_filings_for_ticker(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Return all filings for a specific ticker, sorted by most recent 'Trade Date'.
    """
    sub = df[df["Ticker"] == ticker].copy()
    if "Trade Date" in sub.columns:
        sub = sub.sort_values("Trade Date", ascending=False)
    return sub

def simulate_returns_for_ticker(df_filings: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate a simulated return since the average “Trade Date” for df_filings.
    Uses yfinance to fetch historical prices.
    """
    if df_filings.empty or "Trade Date" not in df_filings.columns:
        return pd.DataFrame()
    avg_date = df_filings["Trade Date"].dropna().mean().date()
    ticker = df_filings["Ticker"].iloc[0]
    try:
        hist = yf.download(
            ticker,
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
            "Ticker": ticker,
            "Avg_Trade_Date": avg_date,
            "Entry_Price": round(entry, 2),
            "Latest_Price": round(latest, 2),
            "Return (%)": round(ret_pct, 2),
        }])
    except Exception:
        return pd.DataFrame()


# ----------------------------------
#  STREAMLIT LAYOUT
# ----------------------------------

st.set_page_config(page_title="Unified Stock + Insider Dashboard", layout="wide")
st.title("📊 Unified Stock + Insider Dashboard")

# Create two tabs: “Stock Lookup” and “Insider Dashboard”
tab1, tab2 = st.tabs(["📈 Stock Lookup (Alpha Vantage)", "🏛️ Insider Dashboard (OpenInsider)"])

# ------------------------------  
# Tab 1: STOCK LOOKUP  
# ------------------------------
with tab1:
    st.header("Stock Lookup with Alpha Vantage")
    symbol = st.text_input("Enter Stock Ticker Symbol (e.g., AAPL, TSLA):", value="AAPL")
    interval = st.selectbox("Interval", ["1min", "5min", "15min", "30min", "60min"])
    show_tech = st.checkbox("Show SMA (20) & RSI (14)", value=True)

    df_price = fetch_intraday_av(symbol, interval)
    if df_price.empty:
        st.warning("⚠️ No data found. Check your symbol or API key.")
    else:
        if show_tech:
            df_price = add_technical_indicators(df_price)

        st.subheader(f"📊 {symbol} Price Chart ({interval})")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df_price["Close"], label="Close", linewidth=1.5)
        if show_tech and "SMA_20" in df_price.columns:
            ax.plot(df_price["SMA_20"], label="SMA 20", linestyle="--")
        ax.set_ylabel("Price")
        ax.set_title(f"{symbol} Price Chart")
        ax.legend()
        st.pyplot(fig)

        if show_tech and "RSI" in df_price.columns:
            st.subheader("📉 RSI (14)")
            fig2, ax2 = plt.subplots(figsize=(10, 2))
            ax2.plot(df_price["RSI"], label="RSI", color="orange")
            ax2.axhline(70, color="red", linestyle="--", label="Overbought (70)")
            ax2.axhline(30, color="green", linestyle="--", label="Oversold (30)")
            ax2.set_title("RSI (14)")
            ax2.legend()
            st.pyplot(fig2)

        st.subheader("📄 Raw Data (most recent 50 rows)")
        st.dataframe(df_price.tail(50), use_container_width=True)

# ------------------------------  
# Tab 2: INSIDER DASHBOARD  
# ------------------------------
with tab2:
    st.header("Insider Dashboard (OpenInsider)")
    use_mock = st.checkbox("Use mock data (local CSV)", value=True)
    days_back = st.slider("Window (days) for insider filings", 1, 30, 3)
    min_value = st.number_input("Min Buy Value ($)", min_value=1000, max_value=1_000_000, value=10000, step=1000)

    df_insiders = fetch_insider_data(use_mock, days_back, min_value)

    st.subheader("📋 Recent Insider Purchases")
    if df_insiders.empty:
        st.warning("No insider purchase records in this window.")
    else:
        if "Trade Date" in df_insiders.columns:
            df_insiders = df_insiders.sort_values("Trade Date", ascending=False)
        st.dataframe(df_insiders, use_container_width=True)

    st.subheader("📊 Top Insider‐Bought Tickers")
    df_counts = compute_most_bought(df_insiders)
    if df_counts.empty:
        st.info("No tickers to display.")
    else:
        st.dataframe(df_counts.head(10), use_container_width=True)
        st.bar_chart(df_counts.set_index("Ticker")["Buy Count"].head(10))

        tickers_list = df_counts["Ticker"].tolist()
        chosen_ticker = st.selectbox("🔎 Drill down into ticker:", [""] + tickers_list)
        if chosen_ticker:
            st.markdown(f"### Details for {chosen_ticker}")
            filings_for_ticker = get_filings_for_ticker(df_insiders, chosen_ticker)
            st.dataframe(filings_for_ticker, use_container_width=True)

            st.markdown(f"### {chosen_ticker} Price Chart (Since Avg Trade Date)")
            ret_df = simulate_returns_for_ticker(filings_for_ticker)
            if not ret_df.empty:
                avg_date = ret_df["Avg_Trade_Date"].iloc[0]
                st.write(f"- Average Insider Trade Date: **{avg_date}**")
                try:
                    hist = yf.download(
                        chosen_ticker,
                        start=(avg_date - timedelta(days=1)).strftime("%Y-%m-%d"),
                        end=datetime.now().strftime("%Y-%m-%d"),
                        progress=False,
                    )
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(hist.index, hist["Close"], label="Close", linewidth=1.5)
                    ax.axvline(avg_date, color="green", linestyle="--", label="Avg Trade Date")
                    ax.set_title(f"{chosen_ticker} Price (from {avg_date - timedelta(days=1)} to today)")
                    ax.set_ylabel("Price")
                    ax.legend()
                    st.pyplot(fig)
                except Exception:
                    st.error("Failed to fetch price history for chart.")
                st.subheader("💰 Simulated Return Since Avg Trade Date")
                st.dataframe(ret_df, use_container_width=True)
            else:
                st.info("Not enough data to simulate returns for this ticker.")

    st.subheader("💼 Simulated Portfolio: Clustered Buys")
    clustered = df_counts[df_counts["Buy Count"] >= 3]["Ticker"].tolist()
    if clustered:
        st.write(f"Tickers with ≥ 3 insider buys: {', '.join(clustered)}")
        portfolio_list = []
        for t in clustered:
            df_t = get_filings_for_ticker(df_insiders, t)
            ret = simulate_returns_for_ticker(df_t)
            if not ret.empty:
                portfolio_list.append(ret.iloc[0])
        if portfolio_list:
            df_portfolio = pd.DataFrame(portfolio_list)
            st.dataframe(df_portfolio, use_container_width=True)
        else:
            st.info("No return data available for clustered tickers yet.")
    else:
        st.info("No tickers have ≥ 3 insider buys in this window.")
