# app/services/data_risk_service.py

import pandas as pd
import numpy as np
from datetime import timedelta
from app.models import StockPrice
from sqlalchemy import desc


# ============================
# 1. 年化波動度
# ============================
def compute_volatility(df):
    df = df.sort_values("date")
    df["ret"] = df["close"].pct_change()
    vol = df["ret"].std() * np.sqrt(252)
    return round(float(vol * 100), 2) if vol is not None else None


# ============================
# 2. 最大回撤
# ============================
def compute_max_drawdown(df):
    df = df.sort_values("date")
    cum_max = df["close"].cummax()
    dd = (df["close"] - cum_max) / cum_max
    return round(float(dd.min() * 100), 2)  # 負值 %


# ============================
# 3. 平均成交金額 (20 日)
# ============================
def compute_turnover(df):
    df["turnover"] = df["close"] * df["volume"]
    return float(df["turnover"].tail(20).mean())


# ============================
# 4. 主計算
# ============================
def calc_risk_factors(symbol):
    """
    回傳：
    {
        "volatility": 年化波動 (%)
        "max_drawdown": 最大回撤 (%)
        "turnover": 平均成交額
        "scores": {vol, mdd, liq}
        "risk_score": 綜合分數
        "risk_report": 中文描述
    }
    """

    prices = (
        StockPrice.query
        .filter_by(symbol=symbol)
        .order_by(desc(StockPrice.date))
        .limit(300)
        .all()
    )
    if not prices:
        return {}

    df = pd.DataFrame([{
        "date": p.date,
        "close": p.close,
        "volume": p.volume
    } for p in prices])

    df.dropna(inplace=True)

    # -------- 計算三項 --------
    vol = compute_volatility(df)
    mdd = compute_max_drawdown(df)
    liq = compute_turnover(df)

    # -------- 轉成分數 (0~100) --------
    score_vol = max(0, min(100, 110 - (vol * 2))) if vol else 0
    score_mdd = max(0, min(100, 110 - abs(mdd) * 2)) if mdd else 0

    # 流動性：假設 >1 億元 => 100 分
    if liq is None:
        score_liq = 0
    else:
        low, high = 10_000_000, 100_000_000
        score_liq = (liq - low) / (high - low) * 100
        score_liq = max(0, min(100, score_liq))

    # -------- 綜合風險分數 --------
    risk_score = round((score_vol + score_mdd + score_liq) / 3, 2)

    # -------- 中文描述 --------
    report_parts = []
    if vol < 20: report_parts.append("波動低")
    elif vol < 40: report_parts.append("波動中性")
    else: report_parts.append("波動高")

    if mdd > -20: report_parts.append("回撤穩定")
    else: report_parts.append("回撤偏大")

    if liq > 50_000_000: report_parts.append("流動佳")
    else: report_parts.append("流動差")

    risk_report = "、".join(report_parts)

    return {
        "volatility": vol,
        "max_drawdown": mdd,
        "turnover": liq,
        "scores": {
            "vol": round(score_vol, 2),
            "mdd": round(score_mdd, 2),
            "liq": round(score_liq, 2),
        },
        "risk_score": risk_score,
        "risk_report": risk_report,
    }
