import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import ta
import time
import requests
import logging
from datetime import datetime
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import lightgbm as lgb

# === CONFIGURATION ===
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
BARS = 1000
MODEL_FILE = "lgbm_trading_model.pkl"
LOT_SIZE = 0.1
SL_PIPS = 500
TP_PIPS = 1000
DEVIATION = 20

TELEGRAM_TOKEN = "7510490820:AAFo-4Q_5RXVSBJmdjIArEhnWAorQg4Duq0"
TELEGRAM_CHAT_ID = "6281951129"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === MT5 INIT ===
if not mt5.initialize():
    raise RuntimeError("MT5 initialization failed")

# === FETCH HISTORICAL DATA ===
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, BARS)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# === INDICATOR CALCULATION ===
def compute_indicators(df):
    df = df.copy()
    df['EMA9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['EMA21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['MACD_HIST'] = ta.trend.macd_diff(df['close'])
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    df['ADX'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
    df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    bb = ta.volatility.BollingerBands(df['close'], window=20)
    df['BB_UPPER'] = bb.bollinger_hband()
    df['BB_MID'] = bb.bollinger_mavg()
    df['BB_LOWER'] = bb.bollinger_lband()
    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    return df.dropna()

# === TRAIN MODEL ===
def train_model(df):
    features = ['EMA9', 'EMA21', 'MACD_HIST', 'RSI', 'ADX', 'ATR', 'BB_UPPER', 'BB_MID', 'BB_LOWER']
    X = df[features]
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=7, random_state=42)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    logging.info(f"[LightGBM] Model trained with accuracy: {acc:.2f}")
    joblib.dump(model, MODEL_FILE)
    return model

# === LOAD OR RETRAIN MODEL ===
def load_model():
    try:
        return joblib.load(MODEL_FILE)
    except:
        logging.warning("Model not found. Training new LightGBM model...")
        df = compute_indicators(get_data())
        return train_model(df)

# === SIGNAL GENERATOR ===
def generate_signal(model, df):
    features = ['EMA9', 'EMA21', 'MACD_HIST', 'RSI', 'ADX', 'ATR', 'BB_UPPER', 'BB_MID', 'BB_LOWER']
    last_row = df.iloc[-1:][features]
    prediction = model.predict(last_row)[0]
    confidence = model.predict_proba(last_row)[0][prediction] * 100
    direction = "BUY" if prediction == 1 else "SELL"
    return direction, confidence

# === TELEGRAM ALERT ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# === LIVE TRADE EXECUTION ===
def execute_trade(direction):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    sl = price - SL_PIPS * 0.01 if direction == "BUY" else price + SL_PIPS * 0.01
    tp = price + TP_PIPS * 0.01 if direction == "BUY" else price - TP_PIPS * 0.01

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": 123456,
        "comment": "AI Trading Bot - XAUUSD",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Trade failed: {result.retcode} - {result.comment}")
    else:
        logging.info(f"Trade successful: {direction} XAUUSD at {price}")
        send_telegram(f"✅ Executed {direction} on XAUUSD at {price}")

# === MAIN LOOP ===
def run_bot():
    model = load_model()
    logging.info("AI Trading Bot started. Monitoring XAUUSD every 5 minutes...")
    while True:
        df = compute_indicators(get_data())
        signal, confidence = generate_signal(model, df)
        insight = f"{signal} Signal with {confidence:.2f}% confidence."
        logging.info(insight)
        send_telegram(f"{datetime.now()}\nXAUUSD 5M\n{insight}")
        execute_trade(signal)
        time.sleep(300)

# === RUN BOT ===
if __name__ == '__main__':
    run_bot()
    mt5.shutdown()
