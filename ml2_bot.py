import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import time
import pytz
import tensorflow as tf
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import pyttsx3
import requests

# === CONFIG ===
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
MODEL_PATH = "model_xauusd_7indicators.keras"
LOT_SIZE = 0.1
SL_PIPS = 25
TP_PIPS = 50
BOT_TOKEN = "7510490820:AAFo-4Q_5RXVSBJmdjIArEhnWAorQg4Duq0"
CHAT_ID = 6281951129

# === INIT ===
model = tf.keras.models.load_model(MODEL_PATH)
scaler = MinMaxScaler()
mt5.initialize()
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except:
        print("Failed to send Telegram message")

def get_data(symbol, timeframe, n=300):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def add_indicators(df):
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['EMA9'] = df['close'].ewm(span=9).mean()
    df['EMA21'] = df['close'].ewm(span=21).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    low14 = df['low'].rolling(14).min()
    high14 = df['high'].rolling(14).max()
    df['%K'] = 100 * (df['close'] - low14) / (high14 - low14)

    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26

    df['BB_mid'] = df['close'].rolling(window=20).mean()
    df['BB_std'] = df['close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_mid'] + (2 * df['BB_std'])
    df['BB_lower'] = df['BB_mid'] - (2 * df['BB_std'])

    df['TR'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift()),
                                     abs(df['low'] - df['close'].shift())))
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']),
                         np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()),
                         np.maximum(df['low'].shift() - df['low'], 0), 0)

    tr14 = df['TR'].rolling(14).sum()
    plus_dm14 = df['+DM'].rolling(14).sum()
    minus_dm14 = df['-DM'].rolling(14).sum()
    plus_di = 100 * (plus_dm14 / tr14)
    minus_di = 100 * (minus_dm14 / tr14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(14).mean()

    df.dropna(inplace=True)
    return df

def predict(df):
    features = ['close', 'MA10', 'MA20', 'EMA9', 'EMA21', 'RSI', '%K', 'MACD', 'BB_upper', 'BB_lower', 'ADX']
    df[features] = scaler.fit_transform(df[features])
    X = np.array([df[features].values[-60:]])
    pred = model.predict(X)[0][0]
    return pred

def execute_trade(pred, df):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print("Failed to get tick data.")
        return

    price = tick.ask if pred > 0.52 else tick.bid
    sl = SL_PIPS * 0.1
    tp = TP_PIPS * 0.1
    deviation = 20
    trade_type = mt5.ORDER_TYPE_BUY if pred > 0.52 else mt5.ORDER_TYPE_SELL
    sl_price = price - sl if trade_type == mt5.ORDER_TYPE_BUY else price + sl
    tp_price = price + tp if trade_type == mt5.ORDER_TYPE_BUY else price - tp

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": trade_type,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": deviation,
        "magic": 123456,
        "comment": "LSTM BUY" if trade_type == mt5.ORDER_TYPE_BUY else "LSTM SELL",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"📤 Sending order: {request}")
    result = mt5.order_send(request)
    print(f"📥 Order result: {result}")

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        action = "BUY" if trade_type == mt5.ORDER_TYPE_BUY else "SELL"
        send_telegram_message(f"✅✅✅ {action} order executed at {price:.2f}")
        speak(f"Order Filled. {action} order sent")
    else:
        send_telegram_message(f"❌ Trade Failed | Retcode: {result.retcode}")
        send_telegram_message(f"📛 MT5 Last Error: {mt5.last_error()}")
        send_telegram_message(f"📛 Server Comment: {result.comment}")
        speak("Trade failed.")
        print(f"❌ Trade Failed | Retcode: {result.retcode}")
        print(f"📛 Error: {mt5.last_error()} | Server Comment: {result.comment}")

def main():
    while True:
        df = get_data(SYMBOL, TIMEFRAME)
        df = add_indicators(df)
        pred = predict(df)
        print(f"[{datetime.now()}] 🔮 Prediction: {pred:.4f}")
        execute_trade(pred, df)
        time.sleep(5 * 60)

if __name__ == "__main__":
    main()
