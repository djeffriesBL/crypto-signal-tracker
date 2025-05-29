import streamlit as st
import pandas as pd

# Set Streamlit config
st.set_page_config(page_title="Insider Buying Screener", layout="wide")
st.title("🕵️‍♂️ Insider Buying Screener (Last 3 Days)")

# OpenInsider CSV URL for buys over $10K in last 3 days
csv_url = "https://openinsider.com/screener.csv?s=&o=&pl=&ph=&ll=&lh=&fd=0&td=0&daysago=3&xp=1&vl=10000&vh=&sortcol=0&maxresults=1000"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Failed to fetch insider data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No insider purchase data available.")
else:
    # Filter for key columns
    display_cols = ["Filing Date", "Trade Date", "Ticker", "Company Name", "Insider Name", "Title", "Trade Type", "Price", "Qty", "Owned", "Value"]
    df = df[display_cols]
    
    # Convert dates
    df["Trade Date"] = pd.to_datetime(df["Trade Date"], errors="coerce")
    df["Filing Date"] = pd.to_datetime(df["Filing Date"], errors="coerce")
    
    # Display table
    st.dataframe(df.sort_values("Trade Date", ascending=False), use_container_width=True)

    # Summary stats
    st.subheader("📊 Most Bought Stocks")
    most_bought = df["Ticker"].value_counts().head(10)
    st.bar_chart(most_bought)
