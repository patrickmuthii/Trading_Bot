# import MetaTrader5 as mt5
# import pandas as pd
# import pandas_ta as ta
# from datetime import datetime
# import time

# # --- INIT MT5 ---
# if not mt5.initialize():
#     print("❌ MT5 initialization failed:", mt5.last_error())
#     quit()
# print("✅ Connected to MT5")

# # --- SETTINGS ---
# symbol = "XAUUSD"
# risk_percent = 1      # Risk 1% of account balance per trade
# sl_pips = 100          # Stop-loss in pips
# tp_pips = 200          # Take-profit in pips
# deviation = 10
# timeframe = mt5.TIMEFRAME_M5
# bars = 100
# magic_number = 10032024
# ema_threshold = 0.1   # Optional margin to avoid fake signals

# # --- LAST SIGNAL STORAGE ---
# def load_last_executed_signal():
#     try:
#         with open("last_signal.txt", "r") as file:
#             return int(file.read().strip())
#     except:
#         return 0

# def save_last_executed_signal(signal):
#     with open("last_signal.txt", "w") as file:
#         file.write(str(signal))

# # --- CHECK OPEN POSITION ---
# def has_open_position(symbol):
#     positions = mt5.positions_get(symbol=symbol)
#     if positions is None:
#         print("❌ Error getting positions:", mt5.last_error())
#         return False
#     return len(positions) > 0

# # --- CALCULATE LOT SIZE ---
# def calculate_lot_size(symbol, sl_pips, risk_percent):
#     account_info = mt5.account_info()
#     if account_info is None:
#         print("❌ Failed to get account info")
#         return 0.1

#     balance = account_info.balance
#     symbol_info = mt5.symbol_info(symbol)
#     if symbol_info is None:
#         print(f"❌ Failed to get symbol info for {symbol}")
#         return 0.1

#     point = symbol_info.point
#     contract_size = 100  # Typical for XAUUSD

#     risk_amount = balance * (risk_percent / 100)
#     sl_price_risk = sl_pips * point * contract_size

#     lot_size = risk_amount / sl_price_risk
#     lot_size = max(0.01, round(lot_size, 2))  # Minimum lot 0.01
#     print(f"DEBUG: Calculated lot size: {lot_size} (Risk: {risk_amount}, SL risk: {sl_price_risk})")
#     return lot_size

# # --- PLACE ORDER ---
# def place_order(symbol, order_type, lot, sl_pips, tp_pips, deviation):
#     symbol_info = mt5.symbol_info(symbol)
#     if symbol_info is None:
#         print(f"❌ Failed to get symbol info for placing order {symbol}")
#         return False

#     tick = mt5.symbol_info_tick(symbol)
#     if tick is None:
#         print(f"❌ Failed to get tick info for {symbol}")
#         return False

#     price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
#     point = symbol_info.point

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
#         "comment": "EMA cross EA",
#         "type_time": mt5.ORDER_TIME_GTC,
#         "type_filling": mt5.ORDER_FILLING_IOC
#     }

#     print(f"DEBUG: Sending order request: {request}")
#     result = mt5.order_send(request)

#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         print(f"❌ Trade failed: retcode={result.retcode}, comment={result.comment}")
#         return False
#     else:
#         print(f"✅ Trade executed: {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} at {price}, lot: {lot}")
#         return True

# # --- MAIN LOOP ---
# def run_bot():
#     print("🤖 Aggressive EMA Crossover Bot Started (Looping every 5 minutes)...")

#     while True:
#         symbol_info = mt5.symbol_info(symbol)
#         if symbol_info is None or not symbol_info.visible or symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
#             print(f"❌ Symbol issue. Retrying in 60 seconds...")
#             time.sleep(60)
#             continue

#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
#         if rates is None or len(rates) == 0:
#             print("❌ Failed to get rates, retrying in 60s")
#             time.sleep(60)
#             continue

#         df = pd.DataFrame(rates)
#         df['time'] = pd.to_datetime(df['time'], unit='s')
#         df.set_index('time', inplace=True)

#         # Calculate EMAs
#         df['EMA9'] = ta.ema(df['close'], length=9)
#         df['EMA21'] = ta.ema(df['close'], length=21)

#         # Aggressive signal detection (real-time)
#         current_ema9 = df['EMA9'].iloc[-1]
#         current_ema21 = df['EMA21'].iloc[-1]
#         last_price = df['close'].iloc[-1]

#         if current_ema9 > current_ema21 + ema_threshold:
#             last_signal = 1
#         elif current_ema9 < current_ema21 - ema_threshold:
#             last_signal = -1
#         else:
#             last_signal = 0

#         # Debug output
#         print(df[['close', 'EMA9', 'EMA21']].tail(5))
#         print(f"DEBUG: Last price: {last_price}")
#         print(f"DEBUG: EMA9: {current_ema9}, EMA21: {current_ema21}, Signal: {last_signal}")

#         executed_signal = load_last_executed_signal()
#         print(f"DEBUG: Last executed signal: {executed_signal}")

#         open_position = has_open_position(symbol)
#         print(f"DEBUG: Has open position: {open_position}")

#         lot = calculate_lot_size(symbol, sl_pips, risk_percent)

#         # Execute trades
#         if last_signal == 1 and not open_position and executed_signal != 1:
#             print("📈 Aggressive Buy Signal!")
#             if place_order(symbol, mt5.ORDER_TYPE_BUY, lot, sl_pips, tp_pips, deviation):
#                 save_last_executed_signal(1)

#         elif last_signal == -1 and not open_position and executed_signal != -1:
#             print("📉 Aggressive Sell Signal!")
#             if place_order(symbol, mt5.ORDER_TYPE_SELL, lot, sl_pips, tp_pips, deviation):
#                 save_last_executed_signal(-1)

#         else:
#             print("⏸ No new aggressive signal or already acted on it")

#         # Sleep until next 5-min candle
#         now = datetime.now()
#         sleep_seconds = 300 - (now.minute % 5) * 60 - now.second
#         print(f"⏳ Sleeping for {sleep_seconds} seconds until next check...")
#         time.sleep(sleep_seconds)

# # --- RUN ---
# try:
#     run_bot()
# except KeyboardInterrupt:
#     print("🛑 Bot stopped by user")
# finally:
#     mt5.shutdown()
#     print("✅ MT5 shutdown completed")
