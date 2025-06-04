import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout  # type: ignore
from sklearn.preprocessing import StandardScaler

# --- Helper function to compute RSI ---
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)  # fill NaN with neutral RSI value 50

# --- Fetch data from MT5 ---
def get_data(symbol, timeframe, bars):
    if not mt5.initialize():
        print("MT5 initialization failed")
        mt5.shutdown()
        return None

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    mt5.shutdown()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# --- Prepare data with technical indicators ---
def prepare_data(df):
    df['ma_10'] = df['close'].rolling(window=10).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['rsi_14'] = compute_rsi(df['close'], 14)

    # Fill NaN values from rolling calculations
    df.fillna(method='bfill', inplace=True)

    features = ['open', 'high', 'low', 'close', 'tick_volume', 'ma_10', 'ma_20', 'rsi_14']

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df[features])

    # Prepare sequences for LSTM input
    WINDOW_SIZE = 10
    X = []
    y = []
    for i in range(WINDOW_SIZE, len(scaled_data) - 1):
        X.append(scaled_data[i - WINDOW_SIZE:i])
        y.append(1 if df['close'].iloc[i + 1] > df['close'].iloc[i] else 0)

    X, y = np.array(X), np.array(y)
    return X, y, scaler

# --- Define model ---
def create_model(input_shape):
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# --- Training process ---
def train():
    symbol = 'XAUUSD'
    timeframe = mt5.TIMEFRAME_M15

    # 1 year of 15-minute bars: 365 days * 24 hours * 4 (15-min bars per hour)
    bars = 365 * 24 * 4  # = 35,040 bars

    df = get_data(symbol, timeframe, bars)
    if df is None:
        print("Failed to get data")
        return

    X, y, scaler = prepare_data(df)

    model = create_model(X.shape[1:])
    model.fit(X, y, epochs=10, batch_size=32, validation_split=0.1)

    model.save('model_xauusd_1year.keras')
    print("✅ Model trained and saved as model_xauusd_1year.keras")

if __name__ == '__main__':
    train()
