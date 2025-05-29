import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# Replace this with your real Alpha Vantage API key
API_KEY = "0IHUC0FIX7RZSUHH"

st.set_page_config(page_title="Alpha Vantage Stock Tracker", layout="wide")
st.title("📈 Stock Tracker with Alpha Vantage")

symbol = st.text_input("Enter Stock Ticker Symbol (e.g., AAPL, TSLA):", value="AAPL")
interval = st.selectbox("Select Time Interval", ["1min", "5min", "15min", "30min", "60min"])
show_technical = st.checkbox("Show SMA and RSI indicators", value=True)

@st.cache_data(ttl=300)
def fetch_intraday(symbol, interval):
    url = (
        f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY"
        f"&symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize=compact"
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
        "3. low": "Low", 
        "4. close": "Close", 
        "5. volume": "Volume"
    }).astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

def add_technical_indicators(df):
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

df = fetch_intraday(symbol, interval)

if df.empty:
    st.warning("⚠️ No data available. Please check the symbol or try again later.")
else:
    if show_technical:
        df = add_technical_indicators(df)

    st.subheader(f"📊 {symbol} Price Chart ({interval} interval)")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["Close"], label="Close Price", linewidth=1.5)
    if show_technical and "SMA_20" in df.columns:
        ax.plot(df["SMA_20"], label="SMA 20", linestyle="--")
    ax.set_title(f"{symbol} Price Chart")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)

    if show_technical and "RSI" in df.columns:
        st.subheader("📉 RSI Indicator")
        fig2, ax2 = plt.subplots(figsize=(10, 2))
        ax2.plot(df["RSI"], label="RSI", color="orange")
        ax2.axhline(70, color="red", linestyle="--", label="Overbought (70)")
        ax2.axhline(30, color="green", linestyle="--", label="Oversold (30)")
        ax2.set_title("Relative Strength Index (RSI)")
        ax2.legend()
        st.pyplot(fig2)

    st.subheader("📄 Raw Price Data")
    st.dataframe(df.tail(50), use_container_width=True)
