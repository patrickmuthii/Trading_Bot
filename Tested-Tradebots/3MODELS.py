import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import ta
import time
import requests
import logging
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
import joblib
import lightgbm as lgb
import warnings
warnings.filterwarnings("ignore")

# === CONFIGURATION ===
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
BARS = 1000
LOT_SIZE = 0.1
DEVIATION = 20
MODEL_FILE = "ensemble_models.pkl"
TELEGRAM_TOKEN = "7510490820:AAFo-4Q_5RXVSBJmdjIArEhnWAorQg4Duq0"
TELEGRAM_CHAT_ID = "6281951129"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === INIT MT5 ===
if not mt5.initialize():
    raise RuntimeError("MT5 initialization failed")

# === GET DATA ===
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, BARS)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# === INDICATORS ===
def compute_indicators(df):
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
    return df.dropna()

# === LABELS ===
def create_labels(df, tp_mult=1.5, sl_mult=1.0):
    df = df.copy()
    df['target'] = 0
    for i in range(len(df) - 6):
        entry = df.iloc[i]['close']
        atr = df.iloc[i]['ATR']
        tp = entry + atr * tp_mult
        sl = entry - atr * sl_mult
        future_high = df.iloc[i+1:i+6]['high'].max()
        future_low = df.iloc[i+1:i+6]['low'].min()
        if future_high >= tp:
            df.at[df.index[i], 'target'] = 1
        elif future_low <= sl:
            df.at[df.index[i], 'target'] = 0
    return df.dropna()

# === TRAIN MODELS ===
def train_ensemble_models(df):
    features = ['EMA9', 'EMA21', 'MACD_HIST', 'RSI', 'ADX', 'ATR', 'BB_UPPER', 'BB_MID', 'BB_LOWER']
    X = df[features]
    y = df['target']

    # Balance the dataset
    count_class_0 = y.value_counts().get(0, 0)
    count_class_1 = y.value_counts().get(1, 0)
    min_count = min(count_class_0, count_class_1)

    df_balanced = pd.concat([
        df[df['target'] == 0].sample(min_count, random_state=42),
        df[df['target'] == 1].sample(min_count, random_state=42)
    ])
    X = df_balanced[features]
    y = df_balanced['target']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    models = {
        "lgb": lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, max_depth=5),
        "rf": RandomForestClassifier(n_estimators=100, random_state=42),
        "gb": GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
    }

    for name, model in models.items():
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        logging.info(f"{name.upper()} Accuracy: {acc:.2f}")

    joblib.dump(models, MODEL_FILE)
    return models

# === LOAD MODELS ===
def load_models():
    try:
        models = joblib.load(MODEL_FILE)
    except:
        df = create_labels(compute_indicators(get_data()))
        models = train_ensemble_models(df)
    return models

# === ML SIGNAL ===
def generate_signal(models, df):
    features = ['EMA9', 'EMA21', 'MACD_HIST', 'RSI', 'ADX', 'ATR', 'BB_UPPER', 'BB_MID', 'BB_LOWER']
    last_row = df.iloc[-1:][features]
    votes = [model.predict(last_row)[0] for model in models.values()]
    decision = 1 if sum(votes) > len(votes)/2 else 0
    confidence = votes.count(decision) / len(votes) * 100
    direction = "BUY" if decision == 1 else "SELL"
    return direction, confidence

# === FIBO SIGNAL ===
def fib_pullback_signal(df):
    recent = df.iloc[-20:]
    high_idx = recent['high'].idxmax()
    low_idx = recent['low'].idxmin()
    if high_idx < low_idx:
        start = df.loc[high_idx, 'high']
        end = df.loc[low_idx, 'low']
        direction = "SELL"
    else:
        start = df.loc[low_idx, 'low']
        end = df.loc[high_idx, 'high']
        direction = "BUY"
    fib_50 = start + (end - start) * 0.5
    fib_618 = start + (end - start) * 0.618
    price = df.iloc[-1]['close']
    if direction == "BUY" and fib_618 <= price <= fib_50:
        return "BUY"
    elif direction == "SELL" and fib_50 <= price <= fib_618:
        return "SELL"
    return None

# === TELEGRAM ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# === EXECUTE TRADE ===
def execute_trade(direction, atr):
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    sl = price - atr * 1 if direction == "BUY" else price + atr * 1
    tp = price + atr * 1.5 if direction == "BUY" else price - atr * 1.5

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
        "comment": "AutoTrade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Trade failed: {result.retcode}")
    else:
        send_telegram(f"✅ {direction} executed at {price}")

# === RUN LOOP ===
def run_bot():
    models = load_models()
    logging.info("Bot started...")
    while True:
        df = compute_indicators(get_data())
        fib_signal = fib_pullback_signal(df)
        if fib_signal:
            atr = df.iloc[-1]['ATR']
            execute_trade(fib_signal, atr)
            send_telegram(f"{datetime.now()} — Fibo Signal: {fib_signal}")
        else:
            direction, confidence = generate_signal(models, df)
            send_telegram(f"{datetime.now()} — ML Signal: {direction} ({confidence:.2f}%)")
        time.sleep(300)

# === MAIN ===
if __name__ == "__main__":
    run_bot()
    mt5.shutdown()
