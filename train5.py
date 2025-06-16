import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import Dense, LSTM, Dropout # type: ignore

# Settings
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
WINDOW_SIZE = 60
EPOCHS = 20
MODEL_SAVE_PATH = "model_xauusd_7indicators.keras"

def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")

def get_data(symbol, timeframe, n=10000):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def add_indicators(df):
    # Moving Averages
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    
    # EMA
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Stochastic %K
    low14 = df['low'].rolling(window=14).min()
    high14 = df['high'].rolling(window=14).max()
    df['%K'] = 100 * (df['close'] - low14) / (high14 - low14)

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

    # Bollinger Bands
    df['BB_mid'] = df['close'].rolling(window=20).mean()
    df['BB_std'] = df['close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_mid'] + (2 * df['BB_std'])
    df['BB_lower'] = df['BB_mid'] - (2 * df['BB_std'])

    # ADX
    df['TR'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift()), 
                                     abs(df['low'] - df['close'].shift())))
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 
                         np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 
                         np.maximum(df['low'].shift() - df['low'], 0), 0)
    tr14 = df['TR'].rolling(window=14).sum()
    plus_dm14 = df['+DM'].rolling(window=14).sum()
    minus_dm14 = df['-DM'].rolling(window=14).sum()
    plus_di = 100 * (plus_dm14 / tr14)
    minus_di = 100 * (minus_dm14 / tr14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(window=14).mean()

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
        X.append(data[i:i + window_size])
        y.append(targets[i + window_size])
    return np.array(X), np.array(y)

def train_model():
    initialize_mt5()
    df = get_data(SYMBOL, TIMEFRAME, n=20000)
    df = add_indicators(df)
    df = create_labels(df)

    features = ['close', 'MA10', 'MA20', 'EMA9', 'EMA21', 'RSI', '%K', 'MACD', 'BB_upper', 'BB_lower', 'ADX']
    scaler = MinMaxScaler()
    df[features] = scaler.fit_transform(df[features])
    
    X, y = create_sequences(df, features, WINDOW_SIZE)

    model = Sequential()
    model.add(LSTM(64, return_sequences=True, input_shape=(X.shape[1], X.shape[2])))
    model.add(Dropout(0.3))
    model.add(LSTM(32))
    model.add(Dropout(0.3))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

    model.fit(X, y, epochs=EPOCHS, batch_size=64, validation_split=0.2)
    model.save(MODEL_SAVE_PATH)
    print(f"✅ Model saved at: {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train_model()
