# app/services/data_fundamental_service.py

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from flask import current_app
from app.extensions import db

from app.models import (
    FinancialIncomeStatement,
    FinancialBalanceSheet,
    FinancialCashflow,
    FinancialShares,
    StockPrice
)

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"


# ------------------------------
# FinMind API (Async Version)
# ------------------------------

async def _finmind_get_async(session, dataset, stock_id, start_date="2010-01-01"):
    """非同步版本的 FinMind API 請求"""
    token = current_app.config.get("FINMIND_TOKEN")
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "token": token
    }
    
    try:
        # Give FinMind API more time
        async with session.get(FINMIND_API_URL, params=params, timeout=30) as res:
            if res.status != 200:
                print(f"⚠️ FinMind API Error ({stock_id}, {dataset}): Status {res.status}")
                return {"dataset": dataset, "stock_id": stock_id, "data": []}

            data = await res.json()
            if "data" not in data:
                print(f"⚠️ FinMind 回傳錯誤({stock_id}, {dataset}): {data}")
                return {"dataset": dataset, "stock_id": stock_id, "data": []}
            
            return {"dataset": dataset, "stock_id": stock_id, "data": data["data"]}
    except asyncio.TimeoutError:
        print(f"TIMEOUT ERROR while fetching {stock_id} {dataset}")
        return {"dataset": dataset, "stock_id": stock_id, "data": []}
    except aiohttp.ClientError as e:
        print(f"NETWORK ERROR while fetching {stock_id} {dataset}: {e}")
        return {"dataset": dataset, "stock_id": stock_id, "data": []}


def _process_finmind_response(result):
    """將 API 回應轉換為 DataFrame 並做基本清理"""
    if not result or not result["data"]:
        return pd.DataFrame()

    df = pd.DataFrame(result["data"])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    
    dataset = result["dataset"]
    rename_map = {}
    if dataset == "TaiwanStockFinancialStatements":
        rename_map = {
            "OperatingRevenue": "revenue", "Revenue": "revenue", "GrossProfit": "gross_profit",
            "OperatingIncome": "operating_income", "OperatingIncomeLoss": "operating_income",
            "NetIncome": "net_income", "EPS": "eps", "Eps": "eps",
        }
    elif dataset == "TaiwanStockBalanceSheet":
        rename_map = {
            "TotalAssets": "total_assets", "TotalLiabilities": "total_liabilities",
            "TotalEquity": "shareholders_equity", "CurrentAssets": "current_assets",
            "CurrentLiabilities": "current_liabilities"
        }
    elif dataset == "TaiwanStockCashFlowsStatement":
        rename_map = {
            "CashFlowOperating": "operating_cashflow", "CashFlowFromOperatingActivities": "operating_cashflow",
            "CashFlowInvesting": "investing_cashflow", "CashFlowFromInvestingActivities": "investing_cashflow",
            "CashFlowFinancing": "financing_cashflow", "CashFlowFromFinancingActivities": "financing_cashflow",
        }
    elif dataset == "TaiwanStockShareholding":
        rename_map = {"TotalShares": "shares_outstanding", "CapitalStock": "capital"}
        
    if rename_map:
        df = df.rename(columns=rename_map)
        
    return df


# ------------------------------
# 寫入四大財報資料
# ------------------------------

def save_income(df, stock_id):
    # 1. 一次性查出已存在的紀錄
    all_dates = df['date'].tolist()
    existing_records = FinancialIncomeStatement.query.filter(
        FinancialIncomeStatement.stock_id == stock_id,
        FinancialIncomeStatement.date.in_(all_dates)
    ).all()
    existing_dates = {rec.date for rec in existing_records}

    # 2. 準備要新增的紀錄
    to_insert = []
    for _, row in df.iterrows():
        if row["date"] in existing_dates:
            continue

        rec = FinancialIncomeStatement(
            stock_id=stock_id,
            date=row["date"],
            revenue=row.get("revenue"),
            gross_profit=row.get("gross_profit"),
            operating_income=row.get("operating_income"),
            net_income=row.get("net_income"),
            eps=row.get("eps"),
        )
        to_insert.append(rec)

    # 3. 批次寫入
    if to_insert:
        db.session.bulk_save_objects(to_insert)
        db.session.commit()
    
    print(f"📥 Income 寫入 {stock_id}: {len(to_insert)} 筆")


def save_balance(df, stock_id):
    # 1. 一次性查出已存在的紀錄
    all_dates = df['date'].tolist()
    existing_records = FinancialBalanceSheet.query.filter(
        FinancialBalanceSheet.stock_id == stock_id,
        FinancialBalanceSheet.date.in_(all_dates)
    ).all()
    existing_dates = {rec.date for rec in existing_records}

    # 2. 準備要新增的紀錄
    to_insert = []
    for _, row in df.iterrows():
        if row["date"] in existing_dates:
            continue

        rec = FinancialBalanceSheet(
            stock_id=stock_id,
            date=row["date"],
            total_assets=row.get("total_assets"),
            total_liabilities=row.get("total_liabilities"),
            shareholders_equity=row.get("shareholders_equity"),
            current_assets=row.get("current_assets"),
            current_liabilities=row.get("current_liabilities"),
        )
        to_insert.append(rec)

    # 3. 批次寫入
    if to_insert:
        db.session.bulk_save_objects(to_insert)
        db.session.commit()
    
    print(f"📥 Balance 寫入 {stock_id}: {len(to_insert)} 筆")


def save_cashflow(df, stock_id):
    # 1. 一次性查出已存在的紀錄
    all_dates = df['date'].tolist()
    existing_records = FinancialCashflow.query.filter(
        FinancialCashflow.stock_id == stock_id,
        FinancialCashflow.date.in_(all_dates)
    ).all()
    existing_dates = {rec.date for rec in existing_records}

    # 2. 準備要新增的紀錄
    to_insert = []
    for _, row in df.iterrows():
        if row["date"] in existing_dates:
            continue

        ocf = row.get("operating_cashflow")
        icf = row.get("investing_cashflow")
        fcf = ocf + icf if (ocf is not None and icf is not None) else None

        rec = FinancialCashflow(
            stock_id=stock_id,
            date=row["date"],
            operating_cashflow=ocf,
            investing_cashflow=icf,
            financing_cashflow=row.get("financing_cashflow"),
            free_cashflow=fcf,
        )
        to_insert.append(rec)

    # 3. 批次寫入
    if to_insert:
        db.session.bulk_save_objects(to_insert)
        db.session.commit()
    
    print(f"📥 Cashflow 寫入 {stock_id}: {len(to_insert)} 筆")


def save_shares(df, stock_id):
    # 1. 一次性查出已存在的紀錄
    all_dates = df['date'].tolist()
    existing_records = FinancialShares.query.filter(
        FinancialShares.stock_id == stock_id,
        FinancialShares.date.in_(all_dates)
    ).all()
    existing_dates = {rec.date for rec in existing_records}

    # 2. 準備要新增的紀錄
    to_insert = []
    for _, row in df.iterrows():
        if row["date"] in existing_dates:
            continue

        rec = FinancialShares(
            stock_id=stock_id,
            date=row["date"],
            shares_outstanding=row.get("shares_outstanding"),
            capital=row.get("capital")
        )
        to_insert.append(rec)

    # 3. 批次寫入
    if to_insert:
        db.session.bulk_save_objects(to_insert)
        db.session.commit()
    
    print(f"📥 Shares 寫入 {stock_id}: {len(to_insert)} 筆")


# ------------------------------
# 主流程：抓一檔股票的基本面並寫入 DB
# ------------------------------

async def fetch_and_save_fundamental(stock_id):
    """
    非同步獲取單一股票的四大財報並存入資料庫
    """
    print(f"\n=== 📊 非同步處理 {stock_id} ===")
    
    datasets = {
        "income": "TaiwanStockFinancialStatements",
        "balance": "TaiwanStockBalanceSheet",
        "cashflow": "TaiwanStockCashFlowsStatement",
        "shares": "TaiwanStockShareholding"
    }

    async with aiohttp.ClientSession() as session:
        tasks = [_finmind_get_async(session, ds, stock_id) for ds in datasets.values()]
        results = await asyncio.gather(*tasks)

    processed_dfs = {}
    for result in results:
        df = _process_finmind_response(result)
        # 找出 df 對應的 key (income, balance, ...)
        key = next((k for k, v in datasets.items() if v == result['dataset']), None)
        if key:
            processed_dfs[key] = df
    
    if "income" in processed_dfs and not processed_dfs["income"].empty:
        save_income(processed_dfs["income"], stock_id)

    if "balance" in processed_dfs and not processed_dfs["balance"].empty:
        save_balance(processed_dfs["balance"], stock_id)

    if "cashflow" in processed_dfs and not processed_dfs["cashflow"].empty:
        save_cashflow(processed_dfs["cashflow"], stock_id)

    if "shares" in processed_dfs and not processed_dfs["shares"].empty:
        save_shares(processed_dfs["shares"], stock_id)
        
    print(f"🎯 {stock_id} 基本面資料全部更新完成")


# ------------------------------
# 舊函式名稱相容（避免 import error）
# ------------------------------

def update_fundamental_for_symbol(stock_id):
    """
    舊名稱 wrapper，外部呼叫 update_fundamental_for_symbol
    實際執行 fetch_and_save_fundamental
    """
    try:
        asyncio.run(fetch_and_save_fundamental(stock_id))
    except RuntimeError as e:
        # 如果事件迴圈已在執行，就用不同的方式處理
        if "cannot run loop while another loop is running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(fetch_and_save_fundamental(stock_id))
        else:
            raise e


# ======================================================
# 基本面七因子計算（PE, PB, PS, ROE, ROA, 營收, EPS）
# ======================================================

def _latest_record(model, stock_id):
    return (
        model.query
        .filter_by(stock_id=stock_id)
        .order_by(model.date.desc())
        .first()
    )

def _clean_sid(sid: str) -> str:
    """去除 .TW / .TWO，維持資料庫格式一致"""
    return sid.replace(".TW", "").replace(".TWO", "")




# ======================================================
# ⭐ 七因子 scoring function（全域可用）
# ======================================================

def score_pe(x):
    if x is None or x <= 0:
        return 0
    if x < 10:   return 100
    if x < 20:   return 80
    if x < 30:   return 60
    if x < 40:   return 40
    return 20

def score_pb(x):
    if x is None or x <= 0:
        return 0
    if x < 1:   return 100
    if x < 2:   return 80
    if x < 3:   return 60
    if x < 4:   return 40
    return 20

def score_ps(x):
    if x is None or x <= 0:
        return 0
    if x < 1:   return 100
    if x < 2:   return 80
    if x < 3:   return 60
    if x < 5:   return 40
    return 20

def score_roe(x):
    if x is None: return 0
    x *= 100
    if x >= 20: return 100
    if x >= 15: return 90
    if x >= 10: return 75
    if x >= 5:  return 60
    if x >= 0:  return 40
    return 10

def score_roa(x):
    if x is None: return 0
    x *= 100
    if x >= 10: return 100
    if x >= 7:  return 90
    if x >= 5:  return 75
    if x >= 3:  return 60
    if x >= 0:  return 40
    return 10

import math
def score_revenue(x):
    if x is None: return 0
    try:
        s = math.log10(max(x, 1))
    except ValueError:
        return 0
    s_norm = (s - 5) / (9 - 5)
    return max(0, min(100, int(s_norm * 100)))

def score_eps(x):
    if x is None: return 0
    if x >= 10: return 100
    if x >= 5:  return 90
    if x >= 3:  return 80
    if x >= 1:  return 60
    if x >= 0:  return 40
    return 10





def calc_fundamental_factors(stock_id):
    """
    回傳：
    {
        "metrics": {...},
        "scores":  {...},
        "a2_score": float,
        "a2_grade": "A+ / B / ..."
    }
    """
    # 先標準化
    sid = _clean_sid(stock_id)

    # 1. 撈最新財報
    inc = _latest_record(FinancialIncomeStatement, sid)
    bal = _latest_record(FinancialBalanceSheet, sid)
    sh  = _latest_record(FinancialShares, sid)

    # 股價表是 symbol=2330.TW 或 2330.TWO，反向用 LIKE 抓
    px = (
        StockPrice.query
        .filter(StockPrice.symbol.like(f"{sid}%"))
        .order_by(StockPrice.date.desc())
        .first()
    )

    if not (inc and bal and sh and px):
        print("⚠️ 基本面資料不足:", stock_id, inc, bal, sh, px)
        return {
            "metrics": {},
            "scores": {},
            "a2_score": None,
            "a2_grade": None,
        }

    # ----- 取欄位 -----
    price = px.close
    eps   = inc.eps
    revenue = inc.revenue
    net_income = inc.net_income
    equity = bal.shareholders_equity
    total_assets = bal.total_assets
    # --- shares_outstanding（補強：若為 None，用最新的替代） ---
    shares = sh.shares_outstanding

    # 如果這一筆為 None，就試著找資料庫中最新的 Shares
    if shares is None:
        latest_shares = (FinancialShares.query
                         .filter(FinancialShares.stock_id == sid)
                         .order_by(FinancialShares.date.desc())
                         .first())
        if latest_shares:
            shares = latest_shares.shares_outstanding


    # ----- 計算比率 -----
    pe = pb = ps = roe = roa = None

    if eps and eps > 0 and price is not None:
        pe = price / eps

    if equity and equity > 0 and shares and shares > 0 and price is not None:
        bvps = equity / shares
        pb = price / bvps

    if revenue and revenue > 0 and shares and shares > 0 and price is not None:
        sp = revenue / shares
        ps = price / sp

    if equity and equity > 0 and net_income is not None:
        roe = net_income / equity

    if total_assets and total_assets > 0 and net_income is not None:
        roa = net_income / total_assets

    metrics = {
        "pe": pe,
        "pb": pb,
        "ps": ps,
        "roe": roe,
        "roa": roa,
        "revenue": revenue,
        "eps": eps,
    }

    # ----- 七因子分數 -----
       # ----- A2 動態權重加權分數 -----
    a2_score, final_scores, final_weights = calc_a2_dynamic(metrics)


    def grade(score):
        if score is None: return None
        if score >= 90: return "A+"
        if score >= 80: return "A"
        if score >= 70: return "B"
        if score >= 60: return "C"
        if score >= 50: return "D"
        return "E"

    a2_grade = grade(a2_score)

    return {
        "metrics": metrics,
        "scores": final_scores,
        "final_weights": final_weights,
        "a2_score": a2_score,
        "a2_grade": a2_grade,
    }



# ======================================================
# ⭐ 動態權重 A2 打分：缺資料 → 自動調整權重
# ======================================================

def calc_a2_dynamic(metrics):
    """
    metrics = {
        "pe": ...,
        "pb": ...,
        "ps": ...,
        "roe": ...,
        "roa": ...,
        "revenue": ...,
        "eps": ...
    }
    """

    # --- 原始因子分數（沿用你的 score_xx） ---
    scores = {
        "pe": score_pe(metrics.get("pe")),
        "pb": score_pb(metrics.get("pb")),
        "ps": score_ps(metrics.get("ps")),
        "roe": score_roe(metrics.get("roe")),
        "roa": score_roa(metrics.get("roa")),
        "revenue": score_revenue(metrics.get("revenue")),
        "eps": score_eps(metrics.get("eps")),
    }

    # --- 權重（你可調整） ---
    weights = {
        "pe": 20,
        "pb": 10,
        "ps": 10,
        "roe": 20,
        "roa": 20,
        "revenue": 10,
        "eps": 10,
    }

    # --- 只保留有資料的（None 不採計） ---
    valid_scores = {k: v for k, v in scores.items() if metrics.get(k) is not None}
    valid_weights = {k: weights[k] for k in valid_scores.keys()}

    if not valid_scores:
        return 0, scores, {}

    # --- 正規化權重：讓總權重 = 1 ---
    total_w = sum(valid_weights.values())
    norm_w = {k: valid_weights[k] / total_w for k in valid_weights}

    # --- 加權平均 ---
    final = 0
    for k in valid_scores:
        final += valid_scores[k] * norm_w[k]

    final = round(final, 2)

    return final, scores, norm_w
