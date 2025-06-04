import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import load_model  # type: ignore
from sklearn.preprocessing import MinMaxScaler
import time

# Define constants
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
MODEL_PATH = "model_xauusd.keras"
WINDOW_SIZE = 60  # number of bars per input sequence

def initialize_mt5():
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        mt5.shutdown()
        exit()

def get_data(symbol, timeframe, n=10000):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def add_indicators(df):
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    low14 = df['low'].rolling(window=14).min()
    high14 = df['high'].rolling(window=14).max()
    df['%K'] = 100 * (df['close'] - low14) / (high14 - low14)
    
    df.dropna(inplace=True)
    return df

def create_labels(df):
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)
    return df

def create_sequences(df, features, window_size):
    X, y = [], []
    data = df[features].values
    targets = df['target'].values
    for i in range(len(df) - window_size):
        X.append(data[i:i+window_size])
        y.append(targets[i+window_size])
    return np.array(X), np.array(y)

def build_model(input_shape):
    from tensorflow.keras.models import Sequential # type: ignore
    from tensorflow.keras.layers import LSTM, Dropout, Dense # type: ignore

    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(25, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def send_order(action, num_orders=3):
    symbol_info = mt5.symbol_info(SYMBOL)
    if not symbol_info:
        print("❌ Symbol not found")
        return False
    if not symbol_info.visible:
        mt5.symbol_select(SYMBOL, True)

    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        print("❌ No tick data. Market might be closed.")
        return False

    price = tick.ask if action == "buy" else tick.bid
    volume = 0.05  # Adjust volume per order
    point = symbol_info.point
    sl = price - 200 * point if action == "buy" else price + 50 * point
    tp = price + 500 * point if action == "buy" else price - 100 * point

    for i in range(num_orders):
        print(f"🧾 Sending {action.upper()} order #{i+1} | Volume: {volume}, Price: {price:.5f}, SL: {sl:.5f}, TP: {tp:.5f}")
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if action == "buy" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "ML bot trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order #{i+1} failed, retcode={result.retcode}, comment: {result.comment}")
        else:
            print(f"✅ Order #{i+1} placed: {action.upper()} at {price:.5f}")
    
    return True

def main():
    initialize_mt5()
    
    print("📥 Loading model...")
    model = load_model(MODEL_PATH)
    print("✅ Model loaded")
    
    scaler = MinMaxScaler()
    
    print("🚀 Starting prediction and trading loop...")
    while True:
        try:
            df = get_data(SYMBOL, TIMEFRAME, n=15000)
            df = add_indicators(df)

            feature_cols = ['close', 'MA10', 'MA20', 'EMA9', 'EMA21', 'EMA50', 'RSI', '%K']
            df.dropna(inplace=True)

            scaler.fit(df[feature_cols])
            scaled_features = scaler.transform(df[feature_cols])
            
            X_pred = np.array([scaled_features[-WINDOW_SIZE:]])
            prediction = model.predict(X_pred)
            print(f"📈 Prediction: {prediction[0][0]:.4f}")
            
            if prediction > 0.5:
                send_order("buy", num_orders=3)
            else:
                send_order("sell", num_orders=3)
            
            time.sleep(60 * 15)  # Wait for 15 minutes
        except Exception as e:
            print(f"⚠️ Error during loop: {e}")
            time.sleep(60)

    mt5.shutdown()

if __name__ == "__main__":
    main()
