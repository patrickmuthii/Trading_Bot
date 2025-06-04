import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import time

# Constants
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
MODEL_PATH = "model_xauusd.keras"
WINDOW_SIZE = 60
VOLUME = 0.05
SL_PIPS = 50
TP_PIPS = 100

def initialize_mt5():
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        mt5.shutdown()
        exit()

def get_data(symbol, timeframe, n=10000):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    atr = df['high'].rolling(period).max() - df['low'].rolling(period).min()
    atr = atr.rolling(period).mean()
    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    trend = [True]  # Uptrend = True, Downtrend = False
    for i in range(1, len(df)):
        if df['close'][i] > upperband[i - 1]:
            trend.append(True)
        elif df['close'][i] < lowerband[i - 1]:
            trend.append(False)
        else:
            trend.append(trend[-1])

    df['supertrend'] = trend
    return df.dropna()

def get_open_positions():
    return [pos for pos in mt5.positions_get() if pos.symbol == SYMBOL]

def close_opposite_trades(current_trend):
    for pos in get_open_positions():
        if (current_trend and pos.type == mt5.ORDER_TYPE_SELL) or (not current_trend and pos.type == mt5.ORDER_TYPE_BUY):
            close_order(pos)

def close_order(position):
    price = mt5.symbol_info_tick(SYMBOL).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": price,
        "deviation": 10,
        "magic": 234000,
        "comment": "Auto close by Supertrend",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    mt5.order_send(request)

def open_trade(trend):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if trend else tick.bid
    sl = price - SL_PIPS * 0.1 if trend else price + SL_PIPS * 0.1
    tp = price + TP_PIPS * 0.1 if trend else price - TP_PIPS * 0.1

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "type": mt5.ORDER_TYPE_BUY if trend else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "deviation": 10,
        "magic": 234000,
        "comment": "Supertrend Signal Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Trade opened: {'BUY' if trend else 'SELL'} at {price:.2f}")
    else:
        print(f"❌ Trade failed: retcode={result.retcode}, comment={result.comment}")

def main():
    initialize_mt5()
    print("🚀 Supertrend Bot Started")

    while True:
        try:
            df = get_data(SYMBOL, TIMEFRAME, n=500)
            df = calculate_supertrend(df)
            current_trend = df['supertrend'].iloc[-1]

            close_opposite_trades(current_trend)
            open_positions = get_open_positions()
            current_type = mt5.ORDER_TYPE_BUY if current_trend else mt5.ORDER_TYPE_SELL

            # Check if there are already trades of current trend
            if not any(pos.type == current_type for pos in open_positions):
                for _ in range(3):
                    open_trade(current_trend)
                    time.sleep(1)

            time.sleep(60 * 15)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
