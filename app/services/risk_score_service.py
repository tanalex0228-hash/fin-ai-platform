# app/services/risk_score_service.py

import numpy as np
import pandas as pd
from app.models import StockPrice


# ======================================================
# 1. 讀取股價 DF
# ======================================================
def load_df(symbol):
    rows = (
        StockPrice.query
        .filter(StockPrice.symbol.like(f"{symbol}%"))
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


# ======================================================
# 2. 計算原始風險值
# ======================================================
def calc_raw_risk(df):
    # 波動
    df["ret"] = df["close"].pct_change()
    vol = df["ret"].std() * np.sqrt(252)
    vol = round(float(vol * 100), 2) if pd.notna(vol) else None

    # 最大回撤
    df["cummax"] = df["close"].cummax()
    df["dd"] = df["close"] / df["cummax"] - 1
    mdd = df["dd"].min()
    mdd = round(float(mdd * 100), 2) if pd.notna(mdd) else None

    # 流動性 = 成交金額平均
    df["amt"] = df["close"] * df["volume"]
    turnover = df["amt"].tail(20).mean()
    turnover = float(turnover) if pd.notna(turnover) else None

    return {
        "volatility": vol,
        "max_drawdown": mdd,
        "turnover": turnover
    }


# ======================================================
# 3. 各指標分數
# ======================================================
# app/services/risk_score_service.py

def score_vol(vol):
    if vol is None:
        return None
    if vol < 10: return 95
    if vol < 20: return 80
    if vol < 30: return 65
    if vol < 40: return 50
    if vol < 50: return 30
    return 10


def score_mdd(mdd):
    if mdd is None:
        return None

    mdd = abs(mdd)

    if mdd < 10: return 95
    if mdd < 20: return 80
    if mdd < 30: return 60
    if mdd < 40: return 40
    if mdd < 60: return 20
    return 10


def score_turnover(amt):
    if amt is None:
        return None

    if amt > 5e9: return 100      # >50 億
    if amt > 1e9: return 80       # >10 億
    if amt > 5e8: return 60       # >5 億
    if amt > 1e8: return 40       # >1 億
    return 20


def score_trend_risk(tr):
    if tr is None:
        return None

    # 越大越危險 → 分數越低
    if tr < 5: return 90
    if tr < 10: return 75
    if tr < 20: return 60
    if tr < 30: return 45
    return 20


def combine_risk_scores(scores: dict):
    vals = [v for v in scores.values() if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


# ======================================================
# 4. 綜合風險敘述
# ======================================================
def risk_report(raw, scores, final):
    msg = []

    # 波動
    if raw["volatility"] is not None:
        if raw["volatility"] < 20:
            msg.append("波動偏低、穩定度佳")
        elif raw["volatility"] < 40:
            msg.append("波動中性")
        else:
            msg.append("波動偏高")

    # 回撤
    if raw["max_drawdown"] is not None:
        if abs(raw["max_drawdown"]) < 20:
            msg.append("回撤風險可控")
        else:
            msg.append("過去回撤較大")

    # 流動性
    if raw["turnover"] is not None:
        if raw["turnover"] > 1e9:
            msg.append("流動性佳")
        else:
            msg.append("流動性普通")

    msg.append(f"綜合風險分數：{final} 分")

    return "；".join(msg)


# ======================================================
# 5. 主流程：回傳完整 dict（前端使用）
# ======================================================
def calc_risk_summary(symbol):
    df = load_df(symbol)
    if df.empty:
        return {
            "raw": {},
            "scores": {},
            "final": None,
            "report": "無資料"
        }

    raw = calc_raw_risk(df)

    scores = {
        "vol": score_vol(raw["volatility"]),
        "mdd": score_mdd(raw["max_drawdown"]),
        "liq": score_turnover(raw["turnover"]),
    }

    valid = [v for v in scores.values() if v is not None]
    final = round(sum(valid) / len(valid), 2) if valid else None

    report = risk_report(raw, scores, final)

    return {
        "raw": raw,
        "scores": scores,
        "final": final,
        "report": report
    }
