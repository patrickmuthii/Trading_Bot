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
# sl_pips = 50
# tp_pips = 100
# deviation = 10
# timeframe = mt5.TIMEFRAME_M1  # 1-minute
# magic_number = 10032024
# max_trades = 5
# lot = 0.05
# trailing_sl_pips = 50

# # --- HELPER FUNCTIONS ---
# def has_open_positions(symbol):
#     positions = mt5.positions_get(symbol=symbol)
#     if positions is None:
#         print("❌ Error getting positions:", mt5.last_error())
#         return []
#     return positions

# def calculate_trailing_stop(symbol, position):
#     price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
#     sl_price = price - trailing_sl_pips * mt5.symbol_info(symbol).point if position.type == mt5.POSITION_TYPE_BUY else price + trailing_sl_pips * mt5.symbol_info(symbol).point
#     return round(sl_price, 2)

# def apply_trailing_stop(symbol):
#     for position in has_open_positions(symbol):
#         sl = calculate_trailing_stop(symbol, position)
#         if abs(sl - position.sl) * 10 > 1:  # avoid spamming
#             result = mt5.order_send({
#                 "action": mt5.TRADE_ACTION_SLTP,
#                 "position": position.ticket,
#                 "sl": sl,
#                 "tp": position.tp,
#             })
#             if result.retcode != mt5.TRADE_RETCODE_DONE:
#                 print(f"❌ Failed to modify SL: {result.retcode}")
#             else:
#                 print(f"🔄 Updated SL for ticket {position.ticket}")

# def place_order(symbol, order_type, lot, sl_pips, tp_pips):
#     tick = mt5.symbol_info_tick(symbol)
#     point = mt5.symbol_info(symbol).point
#     price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
#     sl = price - sl_pips * point if order_type == mt5.ORDER_TYPE_BUY else price + sl_pips * point
#     tp = price + tp_pips * point if order_type == mt5.ORDER_TYPE_BUY else price - tp_pips * point

#     request = {
#         "action": mt5.TRADE_ACTION_DEAL,
#         "symbol": symbol,
#         "volume": lot,
#         "type": order_type,
#         "price": price,
#         "sl": sl,
#         "tp": tp,
#         "deviation": deviation,
#         "magic": magic_number,
#         "comment": "Stochastic Bot",
#         "type_time": mt5.ORDER_TIME_GTC,
#         "type_filling": mt5.ORDER_FILLING_IOC,
#     }

#     result = mt5.order_send(request)
#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         print(f"❌ Order failed: {result.retcode}")
#     else:
#         print(f"✅ Order placed: {'BUY' if order_type == 0 else 'SELL'} at {price}")

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

# # --- MAIN LOOP ---
# def run_bot():
#     print("🤖 Stochastic Bot Started...")
#     while True:
#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
#         if rates is None or len(rates) < 20:
#             print("❌ Not enough data.")
#             time.sleep(10)
#             continue

#         df = pd.DataFrame(rates)
#         df['time'] = pd.to_datetime(df['time'], unit='s')

#         signal = get_stochastic_signal(df)
#         open_positions = has_open_positions(symbol)

#         if len(open_positions) < max_trades:
#             if signal == "buy":
#                 print("📈 BUY Signal from Stochastic")
#                 place_order(symbol, mt5.ORDER_TYPE_BUY, lot, sl_pips, tp_pips)
#             elif signal == "sell":
#                 print("📉 SELL Signal from Stochastic")
#                 place_order(symbol, mt5.ORDER_TYPE_SELL, lot, sl_pips, tp_pips)
#             else:
#                 print("⏸ No trade signal.")
#         else:
#             print(f"📊 Max trades ({max_trades}) open. Waiting...")

#         apply_trailing_stop(symbol)
#         time.sleep(10)

# # --- RUN ---
# try:
#     run_bot()
# except KeyboardInterrupt:
#     print("🛑 Bot stopped by user.")
# finally:
#     mt5.shutdown()
