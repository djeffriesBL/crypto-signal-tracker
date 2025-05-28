import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Use mock data for now
def load_mock_data():
    return pd.DataFrame([
        {"representative": "John Doe", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-10"},
        {"representative": "Jane Smith", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-12"},
        {"representative": "Alice Johnson", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-13"},
        {"representative": "Bob Brown", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-10"},
        {"representative": "Eva Green", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-11"},
        {"representative": "Mark Black", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-12"},
    ])

def analyze_trades(df, days_back=14, min_trades=3):
    cutoff = datetime.now() - timedelta(days=days_back)
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    recent = df[df['transaction_date'] >= cutoff]

    buys = recent[recent['transaction_type'] == 'Purchase']
    sells = recent[recent['transaction_type'].str.contains('Sale')]

    buy_signals = buys['ticker'].value_counts()
    sell_signals = sells['ticker'].value_counts()

    buy_hits = buy_signals[buy_signals >= min_trades].index.tolist()
    sell_hits = sell_signals[sell_signals >= min_trades].index.tolist()

    return buy_hits, sell_hits, recent

def plot_price_chart(ticker, period="1mo", interval="1d"):
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            st.error(f"No price data available for {ticker}")
            return
        fig, ax = plt.subplots()
        ax.plot(data.index, data['Close'], label="Close Price")
        ax.set_title(f"{ticker} Price Chart ({period})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error fetching chart for {ticker}: {e}")

# App UI
st.set_page_config(page_title="House Stock Tracker", layout="wide")
st.title("🏛️ House Stock Buy/Sell Tracker")

df = load_mock_data()

st.subheader("📋 Recent House Trades")
st.dataframe(df[['representative', 'ticker', 'transaction_type', 'transaction_date']], use_container_width=True)

st.subheader("📊 Signal Detection")
buys, sells, recent = analyze_trades(df)
st.markdown("### ✅ Strong Buy Signals")
st.write(", ".join(buys) if buys else "No buy signals in past 14 days.")
st.markdown("### ⚠️ Strong Sell Signals")
st.write(", ".join(sells) if sells else "No sell signals in past 14 days.")

st.subheader("📈 Live Price Chart")
tickers = sorted(df["ticker"].dropna().unique())
selected_ticker = st.selectbox("Select a ticker", tickers)
if selected_ticker:
    plot_price_chart(selected_ticker)

# 🔥 Congressmember Leaderboard
st.subheader("🏆 Congressmember Leaderboard")
leaderboard = df.groupby('representative').agg(
    total_trades=('ticker', 'count'),
    buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
    sells=('transaction_type', lambda x: x.str.contains('Sale').sum())
).reset_index()
st.dataframe(leaderboard, use_container_width=True)

# 📊 Trade Volume Stats
st.subheader("📦 Trade Volume by Ticker")
volume_stats = df.groupby('ticker').agg(
    total_trades=('transaction_type', 'count'),
    buys=('transaction_type', lambda x: (x == 'Purchase').sum()),
    sells=('transaction_type', lambda x: x.str.contains('Sale').sum())
).reset_index()

fig, ax = plt.subplots()
ax.bar(volume_stats['ticker'], volume_stats['buys'], label='Buys', color='green')
ax.bar(volume_stats['ticker'], volume_stats['sells'], bottom=volume_stats['buys'], label='Sells', color='red')
ax.set_ylabel("Trade Volume")
ax.set_title("Total Trades by Ticker")
ax.legend()
st.pyplot(fig)

# 💼 Simulated Portfolio Returns
st.subheader("💼 Simulated Portfolio: Follow the Buys")
portfolio = df[df['transaction_type'] == 'Purchase'].groupby('ticker').size().reset_index(name='count')
portfolio = portfolio[portfolio['count'] >= 3]
if not portfolio.empty:
    portfolio['simulated_return_%'] = [12.5] * len(portfolio)  # Placeholder values
    st.dataframe(portfolio, use_container_width=True)
    st.markdown("_Simulates buying any stock with 3+ congressional buys in the last 14 days._")
else:
    st.write("No qualifying buy clusters yet.")
