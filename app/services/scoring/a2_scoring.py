# app/services/a2_scoring.py

import numpy as np
import pandas as pd
from typing import Dict, Any

# ==========================
# 1. 參數設定（可以之後搬到 config）
# ==========================

# 七因子權重（你可以自己改）
FACTOR_WEIGHTS = {
    "score_f1_value": 1.0,    # 價值
    "score_f2_growth": 1.0,   # 成長
    "score_f3_quality": 1.0,  # 品質
    "score_f4_momentum": 1.0, # 動能
    "score_f5_volatility": 1.0, # 穩定度（反向）
    "score_f6_size": 1.0,     # 市值/規模
    "score_f7_special": 1.0,  # 你自訂的第七因子
}

# A2 裡面，各小維度的權重
A2_SECTION_WEIGHTS = {
    "base_factor": 0.55,   # 七因子本體
    "risk": 0.20,          # 風險
    "liquidity": 0.15,     # 流動性
    "trend": 0.10,         # 進場條件 / 技術趨勢
}

# 你可以用這個表去決定「最終等級」怎麼切
GRADE_RULES = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (0,  "D"),
]


# ==========================
# 2. Base 七因子分數
# ==========================

def compute_base_factor_score(row: pd.Series) -> float:
    """
    讀取 row 裡各個 score_f* 欄位，做加權平均，輸出 0 ~ 100 之間。
    """
    total_weight = 0.0
    total_score = 0.0

    for col, w in FACTOR_WEIGHTS.items():
        if col in row and pd.notna(row[col]):
            total_score += row[col] * w
            total_weight += w

    if total_weight == 0:
        return np.nan

    return total_score / total_weight


# ==========================
# 3. 風險分數 Risk Score
# ==========================

def compute_risk_score(row: pd.Series) -> float:
    """
    假設 row 有：
    - 'vol_60d'：60日年化波動率 (%)
    - 'max_drawdown_1y'：回測中最大回落 (%，用負數)
    
    輸出 0~100 越高越好（風險越合理）。
    """
    vol = row.get("vol_60d", np.nan)
    mdd = row.get("max_drawdown_1y", np.nan)  # 例如 -0.25 代表 -25%

    # Step 1: 波動度轉成分數（越小越好）
    # 假設 10% 波動 = 90 分, 40% = 30 分
    if pd.isna(vol):
        vol_score = np.nan
    else:
        vol_score = 110 - (vol * 2.0)  # 只是示意公式
        vol_score = np.clip(vol_score, 0, 100)

    # Step 2: 最大回落轉成分數（越小越好，-10% > -40%）
    if pd.isna(mdd):
        mdd_score = np.nan
    else:
        # mdd 是負的，把它轉成正數比例
        mdd_abs = abs(mdd)
        # 10% 回落 = 90 分, 50% 回落 = 10 分
        mdd_score = 110 - (mdd_abs * 200)   # 0.1 -> 90, 0.5 -> 10
        mdd_score = np.clip(mdd_score, 0, 100)

    # 合併風險分數（簡單平均）
    subs = [x for x in [vol_score, mdd_score] if not pd.isna(x)]
    if not subs:
        return np.nan

    return float(np.mean(subs))


# ==========================
# 4. 流動性分數 Liquidity Score
# ==========================

def compute_liquidity_score(row: pd.Series) -> float:
    """
    假設 row 有：
    - 'avg_turnover_20d'：20 日平均成交金額（元）
    
    成交金額高 → 分數高
    """
    turnover = row.get("avg_turnover_20d", np.nan)

    if pd.isna(turnover) or turnover <= 0:
        return np.nan

    # 1000 萬以下很差, 1 億以上滿分中間線性
    low = 10_000_000
    high = 100_000_000

    score = (turnover - low) / (high - low) * 100
    score = np.clip(score, 0, 100)

    return float(score)


# ==========================
# 5. 趨勢分數 Trend Score
# ==========================

def compute_trend_score(row: pd.Series) -> float:
    """
    假設 row 有：
    - 'close'：最新收盤
    - 'ma_long'：長期均線 (例如 60MA 或 120MA)
    - 'trend_filter'：例如 'above_long_ma' / 'below_long_ma'
    
    越接近長期均線、且在均線上方 → 分數較高。
    """
    close = row.get("close", np.nan)
    ma_long = row.get("ma_long", np.nan)
    trend_filter = row.get("trend_filter", None)

    if pd.isna(close) or pd.isna(ma_long):
        return np.nan

    # 價差比例
    diff_ratio = (close - ma_long) / ma_long  # 例如 0.05 = 高於 5%

    # 價差在 -3% ～ +3% 之間最理想
    if -0.03 <= diff_ratio <= 0.03:
        base = 90
    elif -0.08 <= diff_ratio <= 0.08:
        base = 75
    else:
        base = 60

    # 在長期均線上方給點加成
    if diff_ratio > 0:
        base += 5

    # 如果有你之前策略裡的 filter
    if trend_filter == "below_long_ma":
        base -= 15

    return float(np.clip(base, 0, 100))


# ==========================
# 6. 綜合 A2 分數 & 等級
# ==========================

def assign_grade(score: float) -> str:
    if pd.isna(score):
        return "N/A"

    for threshold, grade in GRADE_RULES:
        if score >= threshold:
            return grade
    return "N/A"


def compute_a2_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    df：一個「每一列 = 一檔股票」的資料表，
        需事先準備：
        - score_f1_value ~ score_f7_special
        - vol_60d, max_drawdown_1y
        - avg_turnover_20d
        - close, ma_long, trend_filter
    
    回傳：多幾欄：
        - base_factor_score
        - risk_score
        - liquidity_score
        - trend_score
        - score_a2
        - grade_a2
        - a2_reason（給前端顯示的一行文字）
    """

    df = df.copy()

    # 各分項分數
    df["base_factor_score"] = df.apply(compute_base_factor_score, axis=1)
    df["risk_score"] = df.apply(compute_risk_score, axis=1)
    df["liquidity_score"] = df.apply(compute_liquidity_score, axis=1)
    df["trend_score"] = df.apply(compute_trend_score, axis=1)

    # 綜合 A2 分數
    def _combine_row(row: pd.Series) -> float:
        subs = {}
        for k in ["base_factor", "risk", "liquidity", "trend"]:
            col = f"{k}_score"
            score = row.get(col, np.nan)
            if not pd.isna(score):
                subs[k] = score

        if not subs:
            return np.nan

        # 動態依照有值的項目重新 normalize 權重
        total_w = sum(A2_SECTION_WEIGHTS[k] for k in subs.keys())
        final = 0.0
        for k, s in subs.items():
            w = A2_SECTION_WEIGHTS[k] / total_w
            final += s * w

        return final

    df["score_a2"] = df.apply(_combine_row, axis=1)
    df["grade_a2"] = df["score_a2"].apply(assign_grade)

    # 簡單的文字說明（前端可以直接顯示）
    def _build_reason(row: pd.Series) -> str:
        parts = []

        base = row.get("base_factor_score", np.nan)
        if not pd.isna(base):
            if base >= 80:
                parts.append("基本面強勁")
            elif base >= 60:
                parts.append("基本面普通")
            else:
                parts.append("基本面較弱")

        risk = row.get("risk_score", np.nan)
        if not pd.isna(risk):
            if risk >= 80:
                parts.append("風險表現穩定")
            elif risk <= 50:
                parts.append("風險較高")

        liq = row.get("liquidity_score", np.nan)
        if not pd.isna(liq):
            if liq >= 80:
                parts.append("流動性佳")
            elif liq <= 40:
                parts.append("流動性偏弱")

        trend = row.get("trend_score", np.nan)
        if not pd.isna(trend):
            if trend >= 80:
                parts.append("技術面位置良好")
            elif trend <= 50:
                parts.append("技術面位置不佳")

        if not parts:
            return "暫無足夠資料評分"
        return "、".join(parts)

    df["a2_reason"] = df.apply(_build_reason, axis=1)

    return df
