import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 🧱 Load mock data
def load_mock_data():
    return pd.DataFrame([
        {"representative": "John Doe", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-10"},
        {"representative": "Jane Smith", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-12"},
        {"representative": "Alice Johnson", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-13"},
        {"representative": "Bob Brown", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-10"},
        {"representative": "Eva Green", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-11"},
        {"representative": "Mark Black", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-12"},
    ])

# ✅ Live data from S3 with column renaming
@st.cache_data
def fetch_house_trades():
    url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data)

        # Rename S3 fields to expected names
        df = df.rename(columns={
            'politician': 'representative',
            'type': 'transaction_type'
        })

        return df
    except Exception as e:
        st.warning(f"⚠️ Failed to fetch S3 data. Using mock data. Error: {e}")
        return load_mock_data()

# 📊 Analyze trades
def analyze_trades(df, days_back=14, min_trades=3):
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    recent = df[df['transaction_date'] >= (datetime.now() - timedelta(days=days_back))]
    buys = recent[recent['transaction_type'] == 'Purchase']
    sells = recent[recent['transaction_type'].str.contains('Sale')]
    buy_hits = buys['ticker'].value_counts()
    sell_hits = sells['ticker'].value_counts()
    return buy_hits[buy_hits >= min_trades].index.tolist(), sell_hits[sell_hits >= min_trades].index.tolist(), recent

# 📈 Clean price chart
def plot_price_chart(ticker, period="1mo", interval="1d"):
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            st.error(f"No data for {ticker}")
            return

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.plot(data.index, data['Close'], label="Close", linewidth=2)
        ax.set_title(f"{ticker} Price Chart", fontsize=14)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Price", fontsize=10)
        ax.tick_params(axis='x', labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %d'))
        plt.xticks(rotation=45)
        ax.legend()
        fig.tight_layout()

        st.pyplot(fig)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")

# 💼 Portfolio simulation
def simulate_portfolio(df):
    buys = df[df['transaction_type'] == 'Purchase']
    portfolio = buys.groupby('ticker').filter(lambda x: len(x) >= 3)
    results = []

    for ticker in portfolio['ticker'].unique():
        dates = portfolio[portfolio['ticker'] == ticker]['transaction_date']
        avg_date = pd.to_datetime(dates).mean()
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

# 🎛️ App Layout
st.set_page_config(page_title="House Stock Tracker", layout="wide")
st.title("🏛️ House Stock Buy/Sell Tracker")

# Toggle between live/mock
use_mock = st.toggle("Use mock data", value=False)
df = load_mock_data() if use_mock else fetch_house_trades()

# UI - Data
st.subheader("📋 Recent House Trades")
required_cols = ['representative', 'ticker', 'transaction_type', 'transaction_date']
if all(col in df.columns for col in required_cols):
    st.dataframe(df[required_cols], use_container_width=True)
else:
    st.warning("Some required columns are missing from the dataset.")

# UI - Signal Detection
st.subheader("📊 Signal Detection")
buy_signals, sell_signals, recent = analyze_trades(df)
st.markdown("### ✅ Strong Buy Signals")
st.write(", ".join(buy_signals) if buy_signals else "No buy signals")
st.markdown("### ⚠️ Strong Sell Signals")
st.write(", ".join(sell_signals) if sell_signals else "No sell signals")

# UI - Price Chart
st.subheader("📈 Live Price Chart")
tickers = sorted(df["ticker"].dropna().unique())
selected = st.selectbox("Select ticker", tickers)
if selected:
    plot_price_chart(selected)

# UI - Leaderboard
st.subheader("🏆 Congressmember Leaderboard")
if 'representative' in df.columns:
    leaderboard = df.groupby('representative').agg(
        total_trades=('ticker', 'count'),
        buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
        sells=('transaction_type', lambda x: x.str.contains('Sale').sum())
    ).reset_index()
    st.dataframe(leaderboard)

# UI - Trade Volume Chart
st.subheader("📦 Trade Volume by Ticker")
if 'ticker' in df.columns:
    volumes = df.groupby('ticker').agg(
        total=('transaction_type', 'count'),
        buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
        sells=('transaction_type', lambda x: x.str.contains('Sale').sum())
    ).reset_index()
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.bar(volumes['ticker'], volumes['buys'], label='Buys', color='green')
    ax.bar(volumes['ticker'], volumes['sells'], bottom=volumes['buys'], label='Sells', color='red')
    ax.legend()
    ax.set_title("Trade Volume")
    st.pyplot(fig)

# UI - Portfolio Simulation
st.subheader("💼 Simulated Portfolio: Follow the Buys")
returns_df = simulate_portfolio(df)
if not returns_df.empty:
    st.dataframe(returns_df)
else:
    st.write("No qualifying buy clusters.")
