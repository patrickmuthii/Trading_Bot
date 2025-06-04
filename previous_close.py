# import MetaTrader5 as mt5
# import pandas as pd
# from datetime import datetime
# import time

# # --- INIT MT5 ---
# if not mt5.initialize():
#     print("❌ MT5 initialization failed:", mt5.last_error())
#     quit()
# print("✅ Connected to MT5")

# # --- SETTINGS ---
# symbol = "XAUUSD"
# risk_percent = 1
# sl_pips = 100
# tp_pips = 300
# trailing_sl_pips = 50
# deviation = 10
# timeframe = mt5.TIMEFRAME_M1  # ⏱ 1-minute chart
# bars = 10
# magic_number = 10032024
# max_trades = 5
# lot_size = 0.05

# # --- COUNT OPEN POSITIONS ---
# def count_open_positions(symbol):
#     positions = mt5.positions_get(symbol=symbol)
#     if positions is None:
#         print("❌ Error getting positions:", mt5.last_error())
#         return 0
#     return len(positions)

# # --- PLACE ORDER ---
# def place_order(symbol, order_type, lot, sl_pips, tp_pips, deviation):
#     symbol_info = mt5.symbol_info(symbol)
#     if not symbol_info:
#         print(f"❌ Failed to get symbol info for {symbol}")
#         return False

#     tick = mt5.symbol_info_tick(symbol)
#     if not tick:
#         print(f"❌ Failed to get tick for {symbol}")
#         return False

#     point = symbol_info.point
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
#         "comment": "Breakout bot with trailing SL",
#         "type_time": mt5.ORDER_TIME_GTC,
#         "type_filling": mt5.ORDER_FILLING_IOC
#     }

#     result = mt5.order_send(request)

#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         print(f"❌ Trade failed: {result.retcode}, {result.comment}")
#         return False
#     else:
#         print(f"✅ {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} executed at {price}")
#         return True

# # --- TRAILING STOP LOSS ---
# def apply_trailing_stop(symbol, trailing_sl_pips):
#     positions = mt5.positions_get(symbol=symbol)
#     if not positions:
#         return

#     for pos in positions:
#         order_type = pos.type
#         sl = pos.sl
#         price_open = pos.price_open
#         volume = pos.volume
#         ticket = pos.ticket

#         tick = mt5.symbol_info_tick(symbol)
#         point = mt5.symbol_info(symbol).point

#         current_price = tick.bid if order_type == mt5.ORDER_TYPE_BUY else tick.ask
#         new_sl = None

#         if order_type == mt5.ORDER_TYPE_BUY:
#             potential_sl = current_price - trailing_sl_pips * point
#             if sl < potential_sl:
#                 new_sl = potential_sl
#         else:
#             potential_sl = current_price + trailing_sl_pips * point
#             if sl > potential_sl or sl == 0.0:
#                 new_sl = potential_sl

#         if new_sl:
#             modify_request = {
#                 "action": mt5.TRADE_ACTION_SLTP,
#                 "position": ticket,
#                 "sl": round(new_sl, mt5.symbol_info(symbol).digits),
#                 "tp": pos.tp,
#                 "magic": magic_number,
#                 "comment": "Trailing SL update"
#             }
#             mt5.order_send(modify_request)

# # --- MAIN LOOP ---
# def run_bot():
#     print("🤖 Breakout bot running on 1-minute timeframe...")

#     while True:
#         if not mt5.symbol_info(symbol).visible:
#             print(f"❌ Symbol {symbol} not visible.")
#             time.sleep(60)
#             continue

#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
#         if rates is None or len(rates) < 2:
#             print("❌ Not enough candles.")
#             time.sleep(10)
#             continue

#         df = pd.DataFrame(rates)
#         df['time'] = pd.to_datetime(df['time'], unit='s')
#         df.set_index('time', inplace=True)

#         prev_close = df['close'].iloc[-2]
#         prev_open = df['open'].iloc[-2]

#         tick = mt5.symbol_info_tick(symbol)
#         if not tick:
#             print("❌ Could not get tick data.")
#             time.sleep(5)
#             continue

#         current_price = tick.last
#         print(f"🕒 {datetime.now().strftime('%H:%M:%S')} | Prev Close: {prev_close:.2f} | Prev Open: {prev_open:.2f} | Current: {current_price:.2f}")

#         open_trades = count_open_positions(symbol)

#         if current_price > prev_close:
#             if open_trades < max_trades:
#                 place_order(symbol, mt5.ORDER_TYPE_BUY, lot_size, sl_pips, tp_pips, deviation)
#             else:
#                 print("📛 Max trades open. Waiting for slot.")
#         elif current_price < prev_open:
#             if open_trades < max_trades:
#                 place_order(symbol, mt5.ORDER_TYPE_SELL, lot_size, sl_pips, tp_pips, deviation)
#             else:
#                 print("📛 Max trades open. Waiting for slot.")
#         else:
#             print("⏸ No signal.")

#         apply_trailing_stop(symbol, trailing_sl_pips)
#         time.sleep(5)

# # --- RUN ---
# try:
#     run_bot()
# except KeyboardInterrupt:
#     print("🛑 Bot stopped by user.")
# finally:
#     mt5.shutdown()
#     print("✅ MT5 shut down.")
