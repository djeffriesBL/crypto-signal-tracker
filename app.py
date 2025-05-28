import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ✅ Fetch trades from House Stock Watcher with error handling
@st.cache_data
def fetch_house_trades():
    url = "https://housestockwatcher.com/api/transactions"
    response = requests.get(url)

    try:
        data = response.json()
        return pd.DataFrame(data)
    except ValueError:
        st.error("API response was not valid JSON. Try again later.")
        return pd.DataFrame()

# ✅ Analyze trades for buy/sell signals
def analyze_trades(df, days_back=14, min_trades=3):
    cutoff = datetime.now() - timedelta(days=days_back)
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    recent = df[df['transaction_date'] >= cutoff]

    buys = recent[recent['transaction_type'] == 'Purchase']
    sells = recent[recent['transaction_type'] == 'Sale (Full)']

    buy_signals = buys['ticker'].value_counts()
    sell_signals = sells['ticker'].value_counts()

    buy_hits = buy_signals[buy_signals >= min_trades].index.tolist()
    sell_hits = sell_signals[sell_signals >= min_trades].index.tolist()

    return buy_hits, sell_hits, recent

# ✅ Streamlit app UI
st.set_page_config(page_title="Congressional Stock Signals", layout="wide")
st.title("🏛️ Congressional Stock Buy/Sell Signals")

df = fetch_house_trades()

if not df.empty:
    st.subheader("Recent Trades (Raw)")
    st.dataframe(df[['representative', 'ticker', 'transaction_type', 'transaction_date']], use_container_width=True)

    st.subheader("📊 Signal Detection")
    buys, sells, recent = analyze_trades(df)

    st.markdown("### ✅ Strong Buy Signals")
    st.write(", ".join(buys) if buys else "No buy signals in past 14 days.")

    st.markdown("### ⚠️ Strong Sell Signals")
    st.write(", ".join(sells) if sells else "No sell signals in past 14 days.")
else:
    st.warning("No trade data available.")
