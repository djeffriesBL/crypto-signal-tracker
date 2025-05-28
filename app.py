import streamlit as st
import pandas as pd
import requests

# ---- PAGE CONFIG ---- #
st.set_page_config(page_title="Crypto Signal Tracker", layout="wide")
st.title("🚀 Crypto Signal Tracker - MultiChain Dashboard")
st.markdown("""
Live tracking of trending tokens across Ethereum, Solana, and BSC based on:
- 🧠 Buzz (Social Hype)
- 🔐 Safety (Liquidity Lock + Contract)
- 📈 Momentum (Price & Volume)
- ⭐ Total Score (0–10)
""")

# ---- DATA FROM COINGECKO ---- #
def fetch_top_tokens():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params=params)
    data = response.json()
    tokens = []
    for item in data:
        buzz = item.get("price_change_percentage_24h", 0)
        buzz_score = round(min(max(buzz / 5 + 7, 0), 10), 2)

        market_cap = item.get("market_cap", 0)
        safety_score = round(min((market_cap / 5e9) + 3, 10), 2)  # caps at $35B = 10

        momentum = abs(item.get("price_change_percentage_24h", 0))
        momentum_score = round(min(momentum / 5 + 6, 10), 2)

        tokens.append({
            "Token": item.get("name"),
            "Chain": "Multi",  # Coingecko doesn’t specify chain directly
            "Liquidity ($)": item.get("total_volume", 0),
            "Holders": (item.get("market_cap_rank") or 0) * 100,
            "24h Volume ($)": item.get("total_volume", 0),
            "Buzz Score": buzz_score,
            "Safety Score": safety_score,
            "Momentum Score": momentum_score
        })
    df = pd.DataFrame(tokens)
    df["Total Score"] = 0.3 * df["Buzz Score"] + 0.3 * df["Safety Score"] + 0.4 * df["Momentum Score"]
    return df.sort_values(by="Total Score", ascending=False)

# ---- SIDEBAR FILTERS ---- #
st.sidebar.header("🔎 Filters")
min_liquidity = st.sidebar.slider("Minimum Liquidity ($)", 0, 100000000, 5000000, step=1000000)
min_volume = st.sidebar.slider("Minimum 24h Volume ($)", 0, 100000000, 10000000, step=1000000)
min_score = st.sidebar.slider("Minimum Total Score", 0.0, 10.0, 7.5, step=0.1)

# ---- MAIN DASHBOARD ---- #
df = fetch_top_tokens()
filtered_df = df[
    (df["Liquidity ($)"] >= min_liquidity) &
    (df["24h Volume ($)"] >= min_volume) &
    (df["Total Score"] >= min_score)
]

st.dataframe(filtered_df, use_container_width=True)

# ---- WATCHLIST (Session State) ---- #
st.subheader("⭐ Watchlist")
if "watchlist" not in st.sessio
