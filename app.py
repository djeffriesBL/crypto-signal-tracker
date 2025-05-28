import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ✅ Use mock data only (for now)
def load_mock_data():
    mock = [
        {"representative": "John Doe", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-10"},
        {"representative": "Jane Smith", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-12"},
        {"representative": "Alice Johnson", "ticker": "AAPL", "transaction_type": "Purchase", "transaction_date": "2024-05-13"},
        {"representative": "Bob Brown", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-10"},
        {"representative": "Eva Green", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-11"},
        {"representative": "Mark Black", "ticker": "TSLA", "transaction_type": "Sale (Full)", "transaction_date": "2024-05-12"},
    ]
    return pd.DataFrame(mock)

# ✅ Analyze trades
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

# ✅ Draw price chart
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

# ✅ UI
st.set_page_config(page_title="House Stock Signals", layout="wide")
st.title("🏛️ House Stock Buy/Sell Signals")

# Always use mock for now
df = load_mock_data()

st.subheader("📋 Recent House Trades")
st.dataframe(df[['representative', 'ticker', 'transaction_type', 'transaction_date']], use_container_width=True)

st.subheader("📊 Signal Detection")
buys, sells, recent = analyze_trades(df)
st.markdown("### ✅ Strong Buy Signals")
st.write(", ".join(buys) if buys else "No buy signals in past 14 days.")
st.markdown("### ⚠️ Strong Sell Signals")
st.write(", ".join(sells) if sells else "No sell signals in past 14 days.")

# ✅ Live Price Chart always available now
st.subheader("📈 Live Price Chart")
tickers = sorted(df["ticker"].dropna().unique())
selected_ticker = st.selectbox("Select a ticker", tickers)
if selected_ticker:
    plot_price_chart(selected_ticker)
