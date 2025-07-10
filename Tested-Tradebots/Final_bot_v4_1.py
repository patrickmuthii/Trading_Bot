# === XAUUSD SMART ANALYZER BOT v2.2 ===
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import ta
import time
import requests
import logging
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# === CONFIG ===
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
BARS = 1000
TELEGRAM_TOKEN = "7510490820:AAFo-4Q_5RXVSBJmdjIArEhnWAorQg4Duq0"
TELEGRAM_CHAT_ID = "6281951129"
LOT_SIZE = 0.05
TP_POINTS = 100  # in points (1 point = 0.1 pip)
SL_POINTS = 50

# === INIT ===
logging.basicConfig(level=logging.INFO)
if not mt5.initialize():
    raise RuntimeError("MT5 initialization failed")

# === UTILITY ===
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, BARS)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def is_trade_open():
    orders = mt5.positions_get(symbol=SYMBOL)
    return len(orders) > 0

def place_trade(direction, price):
    point = mt5.symbol_info(SYMBOL).point
    deviation = 20
    sl = None
    tp = None

    if direction == "buy":
        sl = price - SL_POINTS * point
        tp = price + TP_POINTS * point
        order_type = mt5.ORDER_TYPE_BUY
    elif direction == "sell":
        sl = price + SL_POINTS * point
        tp = price - TP_POINTS * point
        order_type = mt5.ORDER_TYPE_SELL
    else:
        return False, "❌ Invalid trade direction."

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": mt5.symbol_info_tick(SYMBOL).ask if direction == "buy" else mt5.symbol_info_tick(SYMBOL).bid,
        "sl": sl,
        "tp": tp,
        "deviation": deviation,
        "magic": 234000,
        "comment": "AutoTrade by Smart Analyzer v2.2",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"❌ Trade failed: {result.comment}"
    return True, f"✅ Trade executed at {price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}"

# === ANALYSIS ===
def detect_sr_levels(df):
    levels = []
    for i in range(2, len(df) - 2):
        if df['low'][i] < df['low'][i - 1] and df['low'][i] < df['low'][i + 1]:
            levels.append((df['time'][i], df['low'][i], 'support'))
        if df['high'][i] > df['high'][i - 1] and df['high'][i] > df['high'][i + 1]:
            levels.append((df['time'][i], df['high'][i], 'resistance'))
    return levels

def detect_order_blocks(df):
    ob_zones = []
    for i in range(1, len(df) - 1):
        if df['close'][i] > df['open'][i] and df['open'][i] < df['close'][i-1] < df['open'][i-1]:
            ob_zones.append((df['time'][i], df['low'][i], 'bullish'))
        if df['close'][i] < df['open'][i] and df['open'][i] > df['close'][i-1] > df['open'][i-1]:
            ob_zones.append((df['time'][i], df['high'][i], 'bearish'))
    return ob_zones

def detect_price_action(df):
    patterns = []
    for i in range(2, len(df) - 2):
        o, c, h, l = df['open'][i], df['close'][i], df['high'][i], df['low'][i]
        body = abs(c - o)
        range_ = h - l
        upper_wick = h - max(c, o)
        lower_wick = min(c, o) - l

        if body < range_ * 0.2 and upper_wick > range_ * 0.4 and lower_wick > range_ * 0.4:
            patterns.append((df['time'][i], 'doji'))
        elif body > range_ * 0.7 and c > o:
            patterns.append((df['time'][i], 'bullish engulfing'))
        elif body > range_ * 0.7 and c < o:
            patterns.append((df['time'][i], 'bearish engulfing'))
        elif upper_wick > body * 2:
            patterns.append((df['time'][i], 'pin bar top'))
        elif lower_wick > body * 2:
            patterns.append((df['time'][i], 'pin bar bottom'))
    return patterns

def generate_outlook(price, sr_levels, order_blocks, price_actions):
    outlook = ""
    key_zone = None
    for sr in sr_levels[-3:]:
        for ob in order_blocks[-2:]:
            if abs(sr[1] - ob[1]) <= 0.5:
                key_zone = sr[1]
                outlook += f"\n🔍 Key confluence zone detected around {key_zone:.2f} where {sr[2]} and {ob[2]} order block intersect."
                break

    bull_signals = [x for x in price_actions if 'bullish' in x[1]]
    bear_signals = [x for x in price_actions if 'bearish' in x[1]]
    pin_bars = [x for x in price_actions if 'pin bar' in x[1]]

    direction = "neutral"
    if len(bull_signals) > len(bear_signals):
        outlook += "\n📈 Market shows bullish momentum from recent candle structures."
        direction = "buy"
    elif len(bear_signals) > len(bull_signals):
        outlook += "\n📉 Market shows bearish momentum with strong bearish candles."
        direction = "sell"
    else:
        outlook += "\n⚖️ Market currently in indecision—awaiting breakout or confirmation near key zones."

    if pin_bars:
        outlook += f"\n🕯️ Presence of {len(pin_bars)} pin bars suggests possible reversals."

    return outlook.strip(), direction

# === TELEGRAM ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# === MAIN REPORTING + TRADING ===
def generate_report():
    df = get_data().dropna()
    df = ta.add_all_ta_features(df, open="open", high="high", low="low", close="close", volume="tick_volume")

    sr = detect_sr_levels(df)
    ob = detect_order_blocks(df)
    pa = detect_price_action(df)

    latest = df.iloc[-1]
    price = latest['close']

    report = f"🟡 XAUUSD Market Report (5M)\n\n📌 Price: {price:.2f}"
    if sr:
        report += "\n🔷 S/R Levels: " + ", ".join([f"{x[2].capitalize()} @ {x[1]:.2f}" for x in sr[-3:]])
    if ob:
        report += "\n📦 Order Blocks: " + ", ".join([f"{x[2].capitalize()} OB @ {x[1]:.2f}" for x in ob[-2:]])
    if pa:
        report += "\n📊 Price Action: " + ", ".join([f"{x[1]} @ {x[0].strftime('%H:%M')}" for x in pa[-3:]])

    outlook, decision = generate_outlook(price, sr, ob, pa)
    report += f"\n\n🧠 Outlook:\n{outlook}"

    trade_message = ""
    if decision in ["buy", "sell"] and not is_trade_open():
        success, trade_message = place_trade(decision, price)
        report += f"\n\n📌 Final Advice: Consider a {decision.upper()} toward next {'resistance' if decision == 'buy' else 'support'}."
        report += f"\n{trade_message}"
    elif is_trade_open():
        report += "\n\n⚠️ Trade not executed: Existing open trade detected."
    else:
        report += "\n\n⚠️ No actionable advice at this moment."

    send_telegram(report)
    logging.info("✅ Report sent.")

# === RUN LOOP ===
def run():
    logging.info("🤖 Smart Analyzer v2.2 Started...")
    while True:
        generate_report()
        time.sleep(300)

if __name__ == "__main__":
    run()
    mt5.shutdown()
