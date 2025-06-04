# import MetaTrader5 as mt5
# import pandas as pd
# import pandas_ta as ta
# from datetime import datetime

# # Initialize MT5 connection
# mt5.initialize()

# # --- SETTINGS ---
# symbol = "XAUUSD"
# timeframe = mt5.TIMEFRAME_M5
# bars = 500

# # Get rates
# rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
# mt5.shutdown()

# # Prepare dataframe
# df = pd.DataFrame(rates)
# df['time'] = pd.to_datetime(df['time'], unit='s')
# df.set_index('time', inplace=True)

# # --- INDICATORS ---

# # EMAs
# df['EMA9'] = ta.ema(df['close'], length=9)
# df['EMA21'] = ta.ema(df['close'], length=21)

# # Generate signal
# df['signal'] = 0
# df.loc[(df['EMA9'] > df['EMA21']) & (df['EMA9'].shift() <= df['EMA21'].shift()), 'signal'] = 1  # Buy
# df.loc[(df['EMA9'] < df['EMA21']) & (df['EMA9'].shift() >= df['EMA21'].shift()), 'signal'] = -1  # Sell

# # Show last few rows
# print(df[['close', 'EMA9', 'EMA21', 'signal']].tail(10))


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
# risk_percent = 1  # Risk 1% of account balance per trade
# sl_pips = 30      # Stop-loss in pips (points)
# tp_pips = 60      # Take-profit in pips
# deviation = 10
# timeframe = mt5.TIMEFRAME_M5
# bars = 100
# magic_number = 10032024

# ### STEP 5 functions (load/save last signal) ###
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

# ### STEP 6: Calculate lot size based on risk percentage and SL ###
# def calculate_lot_size(symbol, sl_pips, risk_percent):
#     account_info = mt5.account_info()
#     if account_info is None:
#         print("❌ Failed to get account info")
#         return 0.1  # default lot size

#     balance = account_info.balance
#     symbol_info = mt5.symbol_info(symbol)
#     if symbol_info is None:
#         print(f"❌ Failed to get symbol info for {symbol}")
#         return 0.1

#     point = symbol_info.point
#     contract_size = 100  # typical for XAUUSD, adjust if your broker differs

#     risk_amount = balance * (risk_percent / 100)
#     sl_price_risk = sl_pips * point * contract_size

#     lot_size = risk_amount / sl_price_risk
#     lot_size = max(0.01, round(lot_size, 2))  # minimum 0.01 lot
#     print(f"DEBUG: Calculated lot size: {lot_size} (Risk: {risk_amount}, SL risk: {sl_price_risk})")
#     return lot_size

# # --- PLACE TRADE ---
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

#     if order_type == mt5.ORDER_TYPE_BUY:
#         sl = price - sl_pips * point
#         tp = price + tp_pips * point
#     else:
#         sl = price + sl_pips * point
#         tp = price - tp_pips * point

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
#     print("🤖 EMA Crossover Bot Started (Looping every 5 minutes)...")

#     while True:
#         # Get symbol info & check trading status
#         symbol_info = mt5.symbol_info(symbol)
#         if symbol_info is None:
#             print(f"❌ Symbol info not found for {symbol}")
#             time.sleep(60)
#             continue

#         print(f"DEBUG: Symbol {symbol} visible: {symbol_info.visible}, trade mode: {symbol_info.trade_mode}")

#         if not symbol_info.visible:
#             print(f"❌ Symbol {symbol} not visible in Market Watch.")
#             time.sleep(60)
#             continue

#         if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
#             print(f"❌ Trading disabled for symbol {symbol}")
#             time.sleep(60)
#             continue

#         # Fetch rates
#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
#         if rates is None or len(rates) == 0:
#             print("❌ Failed to get rates, retrying in 60s")
#             time.sleep(60)
#             continue

#         df = pd.DataFrame(rates)
#         df['time'] = pd.to_datetime(df['time'], unit='s')
#         df.set_index('time', inplace=True)

#         # Calculate indicators
#         df['EMA9'] = ta.ema(df['close'], length=9)
#         df['EMA21'] = ta.ema(df['close'], length=21)

#         # Generate signal
#         df['signal'] = 0
#         df.loc[(df['EMA9'] > df['EMA21']) & (df['EMA9'].shift() <= df['EMA21'].shift()), 'signal'] = 1
#         df.loc[(df['EMA9'] < df['EMA21']) & (df['EMA9'].shift() >= df['EMA21'].shift()), 'signal'] = -1

#         last_signal = int(df['signal'].iloc[-1])
#         last_price = df['close'].iloc[-1]

#         print(df[['close', 'EMA9', 'EMA21', 'signal']].tail(5))
#         print(f"DEBUG: Last signal: {last_signal}, Last price: {last_price}")

#         # Load last executed signal
#         executed_signal = load_last_executed_signal()
#         print(f"DEBUG: Last executed signal: {executed_signal}")

#         # Check open positions
#         open_position = has_open_position(symbol)
#         print(f"DEBUG: Has open position: {open_position}")

#         # Calculate lot size
#         lot = calculate_lot_size(symbol, sl_pips, risk_percent)

#         # Trade execution logic
#         if last_signal == 1 and not open_position and executed_signal != 1:
#             print("📈 Buy signal detected!")
#             success = place_order(symbol, mt5.ORDER_TYPE_BUY, lot, sl_pips, tp_pips, deviation)
#             if success:
#                 save_last_executed_signal(1)

#         elif last_signal == -1 and not open_position and executed_signal != -1:
#             print("📉 Sell signal detected!")
#             success = place_order(symbol, mt5.ORDER_TYPE_SELL, lot, sl_pips, tp_pips, deviation)
#             if success:
#                 save_last_executed_signal(-1)

#         else:
#             print("⏸ No new signal or already acted on the same signal")

#         # Sleep until next 5-min candle close
#         now = datetime.now()
#         sleep_seconds = 300 - (now.minute % 5) * 60 - now.second
#         print(f"⏳ Sleeping for {sleep_seconds} seconds until next candle...")
#         time.sleep(sleep_seconds)

# # --- RUN ---
# try:
#     run_bot()
# except KeyboardInterrupt:
#     print("🛑 Bot stopped by user")

# finally:
#     mt5.shutdown()
#     print("✅ MT5 shutdown completed")
