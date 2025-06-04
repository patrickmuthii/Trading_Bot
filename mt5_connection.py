import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

# Connect to MetaTrader 5
if not mt5.initialize():
    print("❌ MT5 connection failed:", mt5.last_error())
    quit()
else:
    print("✅ Connected to MT5")

# Set the symbol and timeframe
symbol = "XAUUSD"
timeframe = mt5.TIMEFRAME_M5
bars = 500  # number of 5-min candles

# Get data
rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)

# Shutdown MT5 connection
mt5.shutdown()

# Convert to DataFrame
data = pd.DataFrame(rates)
data['time'] = pd.to_datetime(data['time'], unit='s')
data.set_index('time', inplace=True)

print(data.tail())
