# app/services/fundamental_service.py
# -----------------------------------
# 📌 對外 API：抓資料 + 算分 + 整理給前端

from app.models import (
    FinancialIncomeStatement,
    FinancialBalanceSheet,
    FinancialShares,
    StockPrice
)
from .fundamental_scoring import calc_a2_dynamic
from .fundamental_fetcher import update_fundamental_for_symbol


# -----------------------------------------------------
# 🧩 工具：抓某資料表最新一筆
# -----------------------------------------------------
def _latest(model, sid):
    return (
        model.query
        .filter_by(stock_id=sid)
        .order_by(model.date.desc())
        .first()
    )


# -----------------------------------------------------
# 🧩 工具：清洗 symbol（去掉 .TW/.TWO）
# -----------------------------------------------------
def _clean_sid(sid):
    return sid.replace(".TW", "").replace(".TWO", "")


# -----------------------------------------------------
# ⭐ 主功能：計算基本面七因子 + A2 + 權重
# -----------------------------------------------------
def calc_fundamental_factors(stock_id):
    sid = _clean_sid(stock_id)

    # ---- 最新財報 ----
    inc = _latest(FinancialIncomeStatement, sid)
    bal = _latest(FinancialBalanceSheet, sid)
    sh  = _latest(FinancialShares, sid)

    # ---- 最新股價 ----
    px = (
        StockPrice.query
        .filter(StockPrice.symbol.like(f"{sid}%"))
        .order_by(StockPrice.date.desc())
        .first()
    )

    # 任一缺資料 → 不給分（權重會讓缺項目跳過）
    if not (inc and bal and sh and px):
        return {
            "metrics": {},
            "scores": {},
            "final_weights": {},
            "a2_score": None,
            "a2_grade": None
        }

    price = px.close
    eps = inc.eps
    revenue = inc.revenue
    net_income = inc.net_income
    equity = bal.shareholders_equity
    total_assets = bal.total_assets

    # shares_outstanding 補強
    shares = sh.shares_outstanding or None

    # 若 shares 為 None → 自動用最新一筆補
    if shares is None:
        latest_sh = (
            FinancialShares.query
            .filter(FinancialShares.stock_id == sid)
            .order_by(FinancialShares.date.desc())
            .first()
        )
        if latest_sh:
            shares = latest_sh.shares_outstanding

    # shares 若仍為 None → 避免除以 None，改為 1（但之後 scoring 會處理）
    if shares is None or shares == 0:
        shares = 1

    # -----------------------------------------------------
    # ⭐ 指標計算（與你原本版本一致，只是更安全）
    # -----------------------------------------------------
    pe = price / eps if eps and eps > 0 else None

    pb = (
        price / (equity / shares)
        if equity and equity > 0 and shares > 0
        else None
    )

    ps = (
        price / (revenue / shares)
        if revenue and revenue > 0 and shares > 0
        else None
    )

    roe = (
        net_income / equity
        if equity and equity > 0 and net_income is not None
        else None
    )

    roa = (
        net_income / total_assets
        if total_assets and total_assets > 0 and net_income is not None
        else None
    )

    metrics = {
        "pe": pe,
        "pb": pb,
        "ps": ps,
        "roe": roe,
        "roa": roa,
        "revenue": revenue,
        "eps": eps,
    }

    # -----------------------------------------------------
    # ⭐ A2 分數（動態權重）
    # -----------------------------------------------------
    a2_score, scores, weights = calc_a2_dynamic(metrics)

    # -----------------------------------------------------
    # 等級分類
    # -----------------------------------------------------
    def grade(x):
        if x is None: return None
        if x >= 90: return "A+"
        if x >= 80: return "A"
        if x >= 70: return "B"
        if x >= 60: return "C"
        if x >= 50: return "D"
        return "E"

    return {
        "metrics": metrics,
        "scores": scores,           # 每個因子的分數
        "final_weights": weights,   # 動態權重（缺資料的自動排除）
        "a2_score": a2_score,       # 最終 A2 分數
        "a2_grade": grade(a2_score)
    }
