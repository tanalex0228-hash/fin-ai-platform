# app/services/technical.py
import numpy as np
import pandas as pd

def add_moving_averages(df: pd.DataFrame, short: int = 5, long: int = 20):
    df[f"MA{short}"] = df["Close"].rolling(short).mean()
    df[f"MA{long}"] = df["Close"].rolling(long).mean()
    return df

def add_macd(df: pd.DataFrame, fast=12, slow=26, signal=9):
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    df["MACD_DIF"] = dif
    df["MACD_DEA"] = dea
    df["MACD_HIST"] = hist
    return df

def add_rsi(df: pd.DataFrame, period=14):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def add_bollinger(df: pd.DataFrame, period=20, num_std=2):
    ma = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    df["BB_MID"] = ma
    df["BB_UPPER"] = ma + num_std * std
    df["BB_LOWER"] = ma - num_std * std
    return df

def add_convolution_smoothing(df: pd.DataFrame, kernel=None, col="Close"):
    if kernel is None:
        kernel = np.array([0.25, 0.5, 0.25])
    values = df[col].values
    conv = np.convolve(values, kernel, mode="same")
    df["CONV_SMOOTH"] = conv
    return df
