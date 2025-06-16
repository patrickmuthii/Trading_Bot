import streamlit as st
import json
import os
import pandas as pd

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")
st.title("🧠 XAUUSD Trading Bot🤖 Dashboard")

# Paths
status_path = "status.json"
flag_path = "bot_flag.json"
trades_path = "trades.json"

# === Load Current Bot Status ===
if os.path.exists(status_path):
    with open(status_path, "r") as f:
        status = json.load(f)
else:
    status = {
        "prediction": 0.0,
        "last_action": "None",
        "balance": 0.0,
        "trade_status": "Bot not running",
        "timestamp": "N/A"
    }

# === Load Bot Running Flag ===
if os.path.exists(flag_path):
    with open(flag_path, "r") as f:
        flag = json.load(f)
else:
    flag = {"running": False}

# === Load Last Trades ===
if os.path.exists(trades_path):
    with open(trades_path, "r") as f:
        trades = json.load(f)
else:
    trades = []

last_5_trades = trades[-5:][::-1]  # Most recent 5 in reverse order
df_trades = pd.DataFrame(last_5_trades)

# === Metrics ===
col1, col2, col3 = st.columns(3)
col1.metric("🔮 Prediction", f"{status['prediction']:.4f}")
col2.metric("📈 Last Action", status['last_action'])
col3.metric("💵 Balance", f"${status['balance']:,.2f}")

st.info(f"📅 Last Update: {status['timestamp']}")
st.success(status["trade_status"])

# === Controls ===
st.subheader("🤖 Bot Control Panel")
start = st.button("▶️ Start Bot")
stop = st.button("⛔ Stop Bot")

if start:
    with open(flag_path, "w") as f:
        json.dump({"running": True}, f)
    st.success("✅ Bot started.")

if stop:
    with open(flag_path, "w") as f:
        json.dump({"running": False}, f)
    st.warning("🛑 Bot stopped.")

# === Last 5 Trades Table ===
st.markdown("---")
st.subheader("📊 Last 5 Trades")

if not df_trades.empty:
    def format_pnl(row):
        return f"🟢 +${row['pnl']:.2f}" if row["pnl"] >= 0 else f"🔴 -${abs(row['pnl']):.2f}"

    df_trades_display = df_trades.copy()
    df_trades_display["pnl"] = df_trades_display.apply(format_pnl, axis=1)
    st.dataframe(df_trades_display[["timestamp", "type", "entry", "exit", "pnl"]], use_container_width=True)

    # Total Profit Display
    total_profit = df_trades["pnl"].sum()
    st.metric("📈 Total PnL (Last 5)", f"${total_profit:.2f}", delta_color="normal")

    # Chart
    st.subheader("📈 PnL Trend")
    st.line_chart(df_trades["pnl"].cumsum(), use_container_width=True)
else:
    st.warning("No trades recorded yet.")

st.markdown("---")
st.caption("AI Trading Bot • Enhanced with trade history, PnL, and live control")
