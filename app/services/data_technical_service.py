# app/services/data_technical_service.py

import pandas as pd
from app.models import StockPrice
from app.services.technical import (
    add_moving_averages,
    add_macd,
    add_rsi
)

# -----------------------------------------------------
# 1. 取價 df
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
# 2. 計算所有技術指標（你昨天使用的版本）
# -----------------------------------------------------
def calc_latest_technical(symbol):
    df = load_price_df(symbol)
    if df.empty:
        return {}

    # === 技術指標 ===
    df = add_moving_averages(df)
    df = add_macd(df)
    df = add_rsi(df)

    latest = df.iloc[-1]

    # === 技術分數 ===
    score = 0
    if latest["MA5"] > latest["MA20"]:
        score += 40
    if latest["MACD_HIST"] > 0:
        score += 30
    if latest["RSI"] > 50:
        score += 30

    return {
        "latest": {
            "ma_short": round(float(latest["MA5"]), 2) if "MA5" in latest else None,
            "ma_long": round(float(latest["MA20"]), 2) if "MA20" in latest else None,
            "rsi": round(float(latest["RSI"]), 2) if "RSI" in latest else None,
            "macd": round(float(latest["MACD_DIF"]), 2) if "MACD_DIF" in latest else None,
            "vol_ma": None,
            "volume": latest.get("volume")
        },
        "score": score
    }
