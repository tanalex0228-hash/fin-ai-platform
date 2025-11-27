# app/services/risk_service.py

import pandas as pd
import numpy as np
from app.models import StockPrice

# -----------------------------------------------------
# 1. 取價格資料 DataFrame
# -----------------------------------------------------
def load_price_df(symbol):
    rows = (
        StockPrice.query
        .filter_by(symbol=symbol)
        .order_by(StockPrice.date.asc())
        .all()
    )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "date": r.date,
        "close": r.close,
        "volume": r.volume
    } for r in rows])

    df.set_index("date", inplace=True)
    return df


# -----------------------------------------------------
# 2. 波動率（年化）
# -----------------------------------------------------
def calc_volatility(df):
    df["ret"] = df["close"].pct_change()

    vol = df["ret"].std() * np.sqrt(252)
    return round(float(vol * 100), 2) if pd.notna(vol) else None


# -----------------------------------------------------
# 3. 最大回撤（MDD）
# -----------------------------------------------------
def calc_mdd(df):
    df["cummax"] = df["close"].cummax()
    df["drawdown"] = df["close"] / df["cummax"] - 1
    mdd = df["drawdown"].min()
    return round(float(mdd * 100), 2) if pd.notna(mdd) else None


# -----------------------------------------------------
# 4. 20 日平均成交額（萬 / 億 元級別）
# -----------------------------------------------------
def calc_avg_turnover(df):
    if "volume" not in df:
        return None

    # 成交金額 = 收盤價 * 成交量
    df["amt"] = df["close"] * df["volume"]
    amt = df["amt"].tail(20).mean()
    return float(amt) if pd.notna(amt) else None


# -----------------------------------------------------
# 5. 趨勢風險：偏離 MA 與方向
# -----------------------------------------------------
def calc_trend_risk(df):
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()

    latest = df.iloc[-1]
    close = latest["close"]
    ma20  = latest["MA20"]
    ma60  = latest["MA60"]

    if pd.isna(ma20) or pd.isna(ma60):
        return None

    # 越偏離，風險越高
    dist20 = abs(close - ma20) / ma20
    dist60 = abs(close - ma60) / ma60

    # 趨勢方向
    trend = 1
    if close < ma60:
        trend = 2   # 長期線下：偏弱

    # 整合
    score = (dist20 * 50 + dist60 * 50) * trend
    return round(float(score * 100), 2)


# -----------------------------------------------------
# 6. 主流程：回傳所有風險因子
# -----------------------------------------------------
def calc_risk_factors(symbol):
    df = load_price_df(symbol)
    if df.empty:
        return {}

    vol  = calc_volatility(df)
    mdd  = calc_mdd(df)
    amt  = calc_avg_turnover(df)
    trend_risk = calc_trend_risk(df)

    return {
        "vol": vol,
        "mdd": mdd,
        "turnover": amt,
        "trend_risk": trend_risk,
    }
