# app/services/scoring/a2_etl.py

import numpy as np
import pandas as pd

# ===== 1. 動能因子：RSI + MACD =====
def compute_momentum_factor(df: pd.DataFrame):
    # RSI：線性轉為 0~100
    df["rsi_score"] = np.clip((df["rsi"] - 30) / (70 - 30) * 100, 0, 100)

    # MACD：DIF - DEA
    df["macd_diff"] = df["macd"] - df["macd_signal"]
    df["macd_score"] = np.clip(df["macd_diff"] * 50 + 50, 0, 100)

    df["score_f4_momentum"] = df[["rsi_score", "macd_score"]].mean(axis=1)
    return df


# ===== 2. 趨勢濾網（使用 ma_long） =====
def compute_trend(df: pd.DataFrame):
    df["trend_filter"] = np.where(
        df["close"] >= df["ma_long"],
        "above_long_ma",
        "below_long_ma"
    )
    return df


# ===== 3. 流動性：成交金額 20 日均 =====
def compute_liquidity(df: pd.DataFrame):
    if "volume" in df.columns:
        df["turnover"] = df["volume"] * df["close"]
        df["avg_turnover_20d"] = df["turnover"].rolling(20).mean()
    else:
        df["avg_turnover_20d"] = np.nan
    return df


# ===== 4. 波動率（60 日年化） =====
def compute_volatility(df: pd.DataFrame):
    df["return"] = df["close"].pct_change()
    df["vol_60d"] = df["return"].rolling(60).std() * np.sqrt(252)
    return df


# ===== 5. 最大回撤（一年） =====
def compute_max_drawdown(df: pd.DataFrame):
    rolling_max = df["close"].rolling(252).max()
    df["mdd_1y"] = df["close"] / rolling_max - 1
    df["max_drawdown_1y"] = df["mdd_1y"].rolling(252).min()
    return df


# ===== 6. 整合 =====
def build_a2_inputs(df: pd.DataFrame):
    df = df.copy()

    df = compute_momentum_factor(df)
    df = compute_trend(df)
    df = compute_liquidity(df)
    df = compute_volatility(df)
    df = compute_max_drawdown(df)

    return df
