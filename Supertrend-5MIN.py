import MetaTrader5 as mt5
import pandas as pd
import time
import numpy as np

# Configuration
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
LOT = 0.05
MAGIC_NUMBER = 123456
DEVIATION = 20

# Initialize MT5
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Supertrend calculation
def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    atr = df['high'].rolling(period).max() - df['low'].rolling(period).min()
    atr = atr.rolling(period).mean()
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = [np.nan] * len(df)
    direction = [True] * len(df)  # True = buy, False = sell

    for i in range(period, len(df)):
        if df.loc[i, 'close'] > upperband[i - 1]:
            direction[i] = True
        elif df.loc[i, 'close'] < lowerband[i - 1]:
            direction[i] = False
        else:
            direction[i] = direction[i - 1]
            if direction[i]:
                lowerband[i] = max(lowerband[i], lowerband[i - 1])
            else:
                upperband[i] = min(upperband[i], upperband[i - 1])

        if direction[i]:
            supertrend[i] = lowerband[i]
        else:
            supertrend[i] = upperband[i]

    df['supertrend'] = supertrend
    df['direction'] = direction
    return df

# Fetch latest data
def get_data(symbol, timeframe, n=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# Close all trades of a given type (opposite_type)
def close_trades(opposite_type):
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions:
        for pos in positions:
            if pos.type == opposite_type:
                price = mt5.symbol_info_tick(SYMBOL).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": SYMBOL,
                    "volume": pos.volume,
                    "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": pos.ticket,
                    "price": price,
                    "deviation": DEVIATION,
                    "magic": MAGIC_NUMBER,
                    "comment": "Closing opposite trade",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print(f"Failed to close position {pos.ticket}, retcode: {result.retcode}")
                else:
                    print(f"Closed position {pos.ticket}")

# Send order without SL or TP
def send_order(order_type):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    print(f"Opening {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} at {price:.2f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": order_type,
        "price": price,
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": "Supertrend Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode}")
    else:
        print(f"✅ Trade opened: {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} at {price:.2f}")

# Main loop
print("🚀 Supertrend Bot Started")
last_signal = None

try:
    while True:
        df = get_data(SYMBOL, TIMEFRAME)
        df = calculate_supertrend(df)

        current_dir = df['direction'].iloc[-1]

        if current_dir and last_signal != "buy":
            close_trades(mt5.ORDER_TYPE_SELL)
            send_order(mt5.ORDER_TYPE_BUY)
            last_signal = "buy"
        elif not current_dir and last_signal != "sell":
            close_trades(mt5.ORDER_TYPE_BUY)
            send_order(mt5.ORDER_TYPE_SELL)
            last_signal = "sell"

        time.sleep(60 * 5)  # wait 5 minutes before next check

except KeyboardInterrupt:
    print("Bot stopped by user.")

finally:
    mt5.shutdown()
