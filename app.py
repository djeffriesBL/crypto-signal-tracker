import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ✅ Paste your real API key between the quotes below
API_KEY = "3RWGW2YEm0guedMt5kUAK05QxGW5JchJ"

# ✅ Fetch trades from FMP Senate Trading API
@st.cache_data
def fetch_senate_trades():
    url = f"https://financialmodelingprep.com/api/v4/senate-trading?apikey=3RWGW2YEm0guedMt5kUAK05QxGW5JchJ"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return pd.DataFrame(data)
    except Exception:
        st.error("⚠️ Failed to fetch data from FMP Senate Trading API.")
        return pd.DataFrame()

# ✅ Analyze trades for buy/sell signals
def analyze_trades(df, days_back=14, min_trades=3):
    cutoff = datetime.now() - timedelta(days=days_back)
    df['transactionDate'] = pd.to_datetime(df['transactionDate'])
    recent = df[df['transactionDate'] >= cutoff]

    buys = recent[recent['transactionType'] == 'Purchase']
    sells = recent[recent['transactionType'].str.contains('Sale')]

    buy_signals = buys['ticker'].value_counts()
    sell_signals = sells['ticker'].value_counts()

    buy_hits = buy_signals[buy_signals >= min_trades].index.tolist()
    sell_hits = sell_signals[sell_signals >= min_trades].index.tolist()

    return buy_hits, sell_hits, recent

# ✅ Streamlit app UI
st.set_page_config(page_title="Senate Stock Signals", layout="wide")
st.title("🏛️ Senate Stock Buy/Sell Signals")

df = fetch_senate_trades()

if not df.empty:
    st.subheader("Recent Senate Trades")
    st.dataframe(df[['senator', 'ticker', 'transactionType', 'transactionDate']], use_container_width=True)

    st.subheader("📊 Signal Detection")
    buys, sells, recent = analyze_trades(df)

    st.markdown("### ✅ Strong Buy Signals")
    st.write(", ".join(buys) if buys else "No buy signals in past 14 days.")

    st.markdown("### ⚠️ Strong Sell Signals")
    st.write(", ".join(sells) if sells else "No sell signals in past 14 days.")
else:
    st.warning("No trade data available.")
