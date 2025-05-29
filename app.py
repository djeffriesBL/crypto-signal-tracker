import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Load fallback mock data
def load_mock_data():
    return pd.DataFrame([
        {"representative": "John Doe", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-10"},
        {"representative": "Jane Smith", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-12"},
        {"representative": "Alice Johnson", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-13"},
        {"representative": "Bob Brown", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-10"},
        {"representative": "Eva Green", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-11"},
        {"representative": "Mark Black", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-12"},
    ])

# Fetch from S3 and rename
@st.cache_data
def fetch_house_trades():
    url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data)
        df = df.rename(columns={'politician': 'representative', 'type': 'transaction_type'})
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        df = df.dropna(subset=['transaction_date'])
        return df
    except Exception as e:
        st.warning(f"⚠️ Failed to fetch live data. Using mock data. Error: {e}")
        mock = load_mock_data()
        mock['transaction_date'] = pd.to_datetime(mock['transaction_date'])
        return mock

# Trade analysis logic
def analyze_trades(df, days_back=14, min_trades=3):
    recent = df[df['transaction_date'] >= (datetime.now() - timedelta(days=days_back))]
    buys = recent[recent['transaction_type'] == 'Purchase']
    sells = recent[recent['transaction_type'].str.contains('Sale')]
    buy_hits = buys['ticker'].value_counts()
    sell_hits = sells['ticker'].value_counts()
    return buy_hits[buy_hits >= min_trades].index.tolist(), sell_hits[sell_hits >= min_trades].index.tolist(), recent

# Portfolio simulator
def simulate_portfolio(df):
    buys = df[df['transaction_type'] == 'Purchase']
    portfolio = buys.groupby('ticker').filter(lambda x: len(x) >= 3)
    results = []
    for ticker in portfolio['ticker'].unique():
        dates = portfolio[portfolio['ticker'] == ticker]['transaction_date']
        avg_date = pd.to_datetime(dates, errors='coerce').dropna().mean()
        try:
            hist = yf.download(ticker, start=avg_date.strftime('%Y-%m-%d'), end=datetime.now().strftime('%Y-%m-%d'))
            if not hist.empty:
                entry = hist.iloc[0]['Close']
                latest = hist.iloc[-1]['Close']
                ret = ((latest - entry) / entry) * 100
                results.append({'Ticker': ticker, 'Avg Buy Date': avg_date.date(), 'Return (%)': round(ret, 2)})
        except:
            continue
    return pd.DataFrame(results)

# 🔧 UI STARTS HERE
st.set_page_config(page_title="Congressional Stock Tracker", layout="wide")
st.title("🏛️ House Stock Buy/Sell Tracker")

# Data toggle
use_mock = st.toggle("Use mock data", value=False)
df = load_mock_data() if use_mock else fetch_house_trades()

# Recent Trades Table
st.subheader("📋 Most Recent House Trades")
if not df.empty:
    df_sorted = df.sort_values(by='transaction_date', ascending=False)
    st.markdown(f"Showing latest {len(df_sorted)} transactions (newest date: **{df_sorted['transaction_date'].max().date()}**)")
    st.dataframe(df_sorted[['representative', 'ticker', 'transaction_type', 'transaction_date']], use_container_width=True)
else:
    st.warning("No trade data available.")

# Buy/Sell Signals
st.subheader("📊 Signal Detection (Last 14 Days, ≥3 trades)")
buy_signals, sell_signals, recent = analyze_trades(df)
st.markdown("### ✅ Strong Buy Signals")
st.write(", ".join(buy_signals) if buy_signals else "No buy signals.")
st.markdown("### ⚠️ Strong Sell Signals")
st.write(", ".join(sell_signals) if sell_signals else "No sell signals.")

# Leaderboard (recent only)
st.subheader("🏆 Congressmember Leaderboard (Past 30 Days)")
leader_cutoff = datetime.now() - timedelta(days=30)
leader_df = df[df['transaction_date'] >= leader_cutoff]

if not leader_df.empty:
    leaderboard = leader_df.groupby('representative').agg(
        total_trades=('ticker', 'count'),
        buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
        sells=('transaction_type', lambda x: x.str.contains('Sale').sum()),
        last_trade=('transaction_date', 'max')
    ).reset_index().sort_values(by='total_trades', ascending=False)
    st.dataframe(leaderboard)
else:
    st.info("No trades from the past 30 days in the current dataset.")

# Trade volume chart
st.subheader("📦 Trade Volume by Ticker (All Time)")
if 'ticker' in df.columns:
    volumes = df.groupby('ticker').agg(
        total=('transaction_type', 'count'),
        buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
        sells=('transaction_type', lambda x: x.str.contains('Sale').sum())
    ).reset_index()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(volumes['ticker'], volumes['buys'], label='Buys', color='green')
    ax.bar(volumes['ticker'], volumes['sells'], bottom=volumes['buys'], label='Sells', color='red')
    ax.set_title("Trade Volume")
    ax.legend()
    st.pyplot(fig)

# Simulated portfolio
st.subheader("💼 Simulated Portfolio: Follow the Buys")
returns_df = simulate_portfolio(df)
if not returns_df.empty:
    st.dataframe(returns_df)
else:
    st.write("No qualifying buy clusters found.")
