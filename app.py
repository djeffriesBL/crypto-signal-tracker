import streamlit as st
import pandas as pd
import requests
import random

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

# Fetch contract addresses from CoinGecko (for TokenSniffer links)
@st.cache_data
def get_contract_address(token_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("platforms", {}).get("ethereum", None)
        return None
    except Exception:
        return None

# Fetch market data and calculate scores
@st.cache_data
def fetch_top_tokens_with_signals():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,_
