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

            token_id = item.get("id", "")
            contract = get_contract_address(token_id)
            sniffer_link = f"https://tokensniffer.com/token/eth/{contract}" if contract else "N/A"

            price_change_1h = item.get("price_change_percentage_1h_in_currency", 0)
            price_change_24h = item.get("price_change_percentage_24h_in_currency", 0)
            market_cap = item.get("market_cap", 1)
            volume = item.get("total_volume", 0)
            volume_to_marketcap = round(volume / market_cap, 4) if market_cap else 0

            # Simulated social buzz score
            buzz_mentions = random.randint(10, 100)

            # Calculate normalized scores
            buzz_score = round(min(max((price_change_1h / 2 + 5) + (buzz_mentions / 25), 0), 10), 2)
            momentum_score = round(min(abs(price_change_24h) / 5 + 6, 10), 2)
            safety_score = round(min((market_cap / 5e9) + 3, 10), 2)
            total_score = round(0.3 * buzz_score + 0.3 * safety_score + 0.4 * momentum_score, 2)

            data.append({
                "Token": item.get("name"),
                "Symbol": symbol,
                "Price ($)": item.get("current_price"),
                "Market Cap ($)": market_cap,
                "Volume ($)": volume,
                "Vol/MCap Ratio": volume_to_marketcap,
                "Buzz Mentions": buzz_mentions,
                "Buzz Score": buzz_score,
                "Safety Score": safety_score,
                "Momentum Score": momentum_score,
                "Total Score": total_score,
                "TokenSniffer": sniffer_link
            })

        return pd.DataFrame(data)
    except Exception as e:
        st.error("Error fetching or processing token data: " + str(e))
        return pd.DataFrame()

# Run everything
df = fetch_top_tokens_with_signals()

if df.empty:
    st.info("No tokens matched the criteria or data could not be loaded. Please try again later.")
else:
    df = df[df["Total Score"] >= 7].sort_values(by="Total Score", ascending=False).reset_index(drop=True)
    min_score = st.sidebar.slider("Minimum Total Score", 0.0, 10.0, 7.0, 0.1)
    df_filtered = df[df["Total Score"] >= min_score]
    st.dataframe(df_filtered, use_container_width=True)
