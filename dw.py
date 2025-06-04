# import yfinance as yf
# import pandas as pd

# def fetch_xauusd_m5(period="60d", interval="5m"):
#     symbol = "XAUUSD=X"  # Yahoo Finance symbol for Gold/USD
#     print(f"Downloading {symbol} data for period={period}, interval={interval}...")
    
#     df = yf.download(tickers=symbol, period=period, interval=interval)
#     df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
#     df.dropna(inplace=True)

#     # Save to CSV for reuse
#     df.to_csv("xauusd_5min_data.csv")
#     print(f"✅ Data downloaded and saved to 'xauusd_5min_data.csv'")
#     return df

# if __name__ == "__main__":
#     df = fetch_xauusd_m5()
#     print(df.tail())


# MT5 Bot Example with Stochastic Oscillator

# import MetaTrader5 as mt5
# import pandas as pd
# import time
# from datetime import datetime
# from ta.momentum import StochasticOscillator

# # --- INIT MT5 ---
# if not mt5.initialize():
#     print("❌ MT5 initialization failed:", mt5.last_error())
#     quit()
# print("✅ Connected to MT5")

# # --- SETTINGS ---
# symbol = "XAUUSD"
# risk_percent = 1
# sl_pips = 100
# tp_pips = 200
# deviation = 10
# timeframe = mt5.TIMEFRAME_M1  # 1-minute
# magic_number = 10032024
# lot = 0.05
# log_file = "trade_log.txt"

# # --- HELPER FUNCTIONS ---
# def log_trade(data):
#     with open(log_file, "a") as f:
#         f.write(data + "\n")

# def has_open_positions(symbol):
#     positions = mt5.positions_get(symbol=symbol)
#     if positions is None:
#         print("❌ Error getting positions:", mt5.last_error())
#         return []
#     return positions

# def get_stochastic_signal(df):
#     stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
#     df['%K'] = stoch.stoch()
#     df['%D'] = stoch.stoch_signal()

#     if df['%K'].iloc[-2] < df['%D'].iloc[-2] and df['%K'].iloc[-1] > df['%D'].iloc[-1]:
#         return "buy"
#     elif df['%K'].iloc[-2] > df['%D'].iloc[-2] and df['%K'].iloc[-1] < df['%D'].iloc[-1]:
#         return "sell"
#     else:
#         return None

# def apply_trailing_stop(symbol):
#     candles = mt5.copy_rates_from_pos(symbol, timeframe, 0, 3)
#     if candles is None or len(candles) < 3:
#         print("❌ Not enough candle data for trailing stop.")
#         return

#     prev_candle = candles[-2]  # fully closed previous candle
#     point = mt5.symbol_info(symbol).point

#     for position in has_open_positions(symbol):
#         if position.type == mt5.POSITION_TYPE_BUY:
#             new_sl = round(prev_candle['low'] - 2 * point, 2)
#             if position.sl is None or new_sl > position.sl:
#                 update_sl(position, new_sl)
#         elif position.type == mt5.POSITION_TYPE_SELL:
#             new_sl = round(prev_candle['high'] + 2 * point, 2)
#             if position.sl is None or new_sl < position.sl:
#                 update_sl(position, new_sl)

# def update_sl(position, new_sl):
#     result = mt5.order_send({
#         "action": mt5.TRADE_ACTION_SLTP,
#         "position": position.ticket,
#         "sl": new_sl,
#         "tp": position.tp,
#     })
#     if result.retcode == mt5.TRADE_RETCODE_DONE:
#         print(f"🔄 SL updated for ticket {position.ticket} -> {new_sl}")
#     else:
#         print(f"❌ Failed to update SL for ticket {position.ticket}: {result.retcode}")

# # --- MAIN LOOP ---
# def run_bot():
#     print("🤖 Stochastic Bot Started...")
#     last_checked_candle = None

#     while True:
#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
#         if rates is None or len(rates) < 20:
#             print("❌ Not enough data.")
#             time.sleep(10)
#             continue

#         df = pd.DataFrame(rates)
#         df['time'] = pd.to_datetime(df['time'], unit='s')
#         current_candle_time = df['time'].iloc[-1]

#         signal = get_stochastic_signal(df)
#         open_positions = has_open_positions(symbol)

#         if signal in ["buy", "sell"] and len(open_positions) == 0:
#             order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL
#             tick = mt5.symbol_info_tick(symbol)
#             point = mt5.symbol_info(symbol).point
#             price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
#             sl = price - sl_pips * point if order_type == mt5.ORDER_TYPE_BUY else price + sl_pips * point
#             tp = price + tp_pips * point if order_type == mt5.ORDER_TYPE_BUY else price - tp_pips * point

#             request = {
#                 "action": mt5.TRADE_ACTION_DEAL,
#                 "symbol": symbol,
#                 "volume": lot,
#                 "type": order_type,
#                 "price": price,
#                 "sl": sl,
#                 "tp": tp,
#                 "deviation": deviation,
#                 "magic": magic_number,
#                 "comment": "Stochastic Bot",
#                 "type_time": mt5.ORDER_TIME_GTC,
#                 "type_filling": mt5.ORDER_FILLING_IOC,
#             }

#             result = mt5.order_send(request)
#             if result.retcode != mt5.TRADE_RETCODE_DONE:
#                 print(f"❌ Order failed: {result.retcode}")
#             else:
#                 trade_type = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
#                 print(f"✅ Order placed: {trade_type} at {price}")

#                 # ✅ Log trade
#                 trade_info = (
#                     f"{datetime.now()} | {symbol} | {trade_type} | Price: {price:.2f} | "
#                     f"SL: {sl:.2f} | TP: {tp:.2f} | Lot: {lot} | Ticket: {result.order}"
#                 )
#                 log_trade(trade_info)

#         else:
#             print(f"⏸ No trade signal or existing position found ({len(open_positions)} open).")

#         # Apply trailing SL only if new candle formed
#         if last_checked_candle is None or current_candle_time > last_checked_candle:
#             apply_trailing_stop(symbol)
#             last_checked_candle = current_candle_time

#         time.sleep(10)

# # --- RUN ---
# try:
#     run_bot()
# except KeyboardInterrupt:
#     print("🛑 Bot stopped by user.")
# finally:
#     mt5.shutdown()
