import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Crypto Signal Tracker", layout="wide")
st.title("🔥 Hot Coinbase-Listed Tokens with Early Signal Detection")

# Fetch tradable tokens from Coinbase Pro
@st.cache_data
def get_coinbase_tradable_ids():
    try:
        response = requests.get("https://api.pro.coinbase.com/products")
        data = response.json()
        return {item['base_currency'] for item in data}
    except Exception as e:
        st.warning("Coinbase API error: " + str(e))
        return set()

# Fetch market data from CoinGecko + compute scores
@st.cache_data
def fetch_top_tokens_with_signals():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h"
    }

    response = requests.get(url, params=params)
    tokens = response.json()

    coinbase_ids = get_coinbase_tradable_ids()
    data = []

    for item in tokens:
        symbol = item.get("symbol", "").upper()
        if symbol not in coinbase_ids:
            continue

        price_change_1h = item.get("price_change_percentage_1h_in_currency", 0)
        price_change_24h = item.get("price_change_percentage_24h_in_currency", 0)
        market_cap = item.get("market_cap", 1)
        volume = item.get("total_volume", 0)
        volume_to_marketcap = round(volume / market_cap, 4) if market_cap else 0

        # Normalized scoring system
        buzz_score = round(min(max(price_change_1h / 2 + 5, 0), 10), 2)
        momentum_score = round(min(abs(price_change_24h) / 5 +_
