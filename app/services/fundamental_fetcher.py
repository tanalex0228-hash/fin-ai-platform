# app/services/fundamental_fetcher.py
# -----------------------------------
# 📌 FinMind 抓取 + 寫入資料庫（四大財報）

import asyncio
import aiohttp
import pandas as pd
from flask import current_app
from app.extensions import db
from app.models import (
    FinancialIncomeStatement,
    FinancialBalanceSheet,
    FinancialCashflow,
    FinancialShares
)

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"


# =============================================================
# 🌐 非同步抓 API
# =============================================================
async def _finmind_get_async(session, dataset, stock_id, start_date="2010-01-01"):
    token = current_app.config.get("FINMIND_TOKEN")
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "token": token
    }

    try:
        async with session.get(FINMIND_API_URL, params=params, timeout=30) as res:
            if res.status != 200:
                print(f"❌ API Error [{stock_id}, {dataset}] Status {res.status}")
                return {"dataset": dataset, "data": []}

            data = await res.json()
            if "data" not in data:
                print(f"❌ API response invalid: {data}")
                return {"dataset": dataset, "data": []}

            return {"dataset": dataset, "data": data["data"]}

    except Exception as e:
        print(f"❌ API error [{stock_id} {dataset}]: {e}")
        return {"dataset": dataset, "data": []}


# =============================================================
# 📑 資料清理
# =============================================================
def process_finmind_df(result):
    df = pd.DataFrame(result["data"])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    dataset = result["dataset"]

    rename = {}

    if dataset == "TaiwanStockFinancialStatements":
        rename = {
            "OperatingRevenue": "revenue",
            "Revenue": "revenue",
            "GrossProfit": "gross_profit",
            "OperatingIncome": "operating_income",
            "OperatingIncomeLoss": "operating_income",
            "NetIncome": "net_income",
            "EPS": "eps",
            "Eps": "eps",
        }

    elif dataset == "TaiwanStockBalanceSheet":
        rename = {
            "TotalAssets": "total_assets",
            "TotalLiabilities": "total_liabilities",
            "TotalEquity": "shareholders_equity",
            "CurrentAssets": "current_assets",
            "CurrentLiabilities": "current_liabilities",
        }

    elif dataset == "TaiwanStockCashFlowsStatement":
        rename = {
            "CashFlowOperating": "operating_cashflow",
            "CashFlowInvesting": "investing_cashflow",
            "CashFlowFinancing": "financing_cashflow",
        }

    elif dataset == "TaiwanStockShareholding":
        rename = {
            "TotalShares": "shares_outstanding",
            "CapitalStock": "capital",
        }

    return df.rename(columns=rename)


# =============================================================
# 📌 寫入四大財報資料
# =============================================================
def save_income(df, sid):
    dates = set(df["date"])
    exists = {
        r.date for r in FinancialIncomeStatement.query.filter(
            FinancialIncomeStatement.stock_id == sid,
            FinancialIncomeStatement.date.in_(dates)
        ).all()
    }

    to_add = []
    for _, r in df.iterrows():
        if r["date"] in exists:
            continue
        to_add.append(FinancialIncomeStatement(
            stock_id=sid,
            date=r["date"],
            revenue=r.get("revenue"),
            gross_profit=r.get("gross_profit"),
            operating_income=r.get("operating_income"),
            net_income=r.get("net_income"),
            eps=r.get("eps"),
        ))

    if to_add:
        db.session.bulk_save_objects(to_add)
        db.session.commit()

    print(f"📥 Income saved: {sid} ({len(to_add)} rows)")


def save_balance(df, sid):
    dates = set(df["date"])
    exists = {
        r.date for r in FinancialBalanceSheet.query.filter(
            FinancialBalanceSheet.stock_id == sid,
            FinancialBalanceSheet.date.in_(dates)
        ).all()
    }

    to_add = []
    for _, r in df.iterrows():
        if r["date"] in exists:
            continue
        to_add.append(FinancialBalanceSheet(
            stock_id=sid,
            date=r["date"],
            total_assets=r.get("total_assets"),
            total_liabilities=r.get("total_liabilities"),
            shareholders_equity=r.get("shareholders_equity"),
            current_assets=r.get("current_assets"),
            current_liabilities=r.get("current_liabilities"),
        ))

    if to_add:
        db.session.bulk_save_objects(to_add)
        db.session.commit()

    print(f"📥 Balance saved: {sid} ({len(to_add)} rows)")


def save_cashflow(df, sid):
    dates = set(df["date"])
    exists = {
        r.date for r in FinancialCashflow.query.filter(
            FinancialCashflow.stock_id == sid,
            FinancialCashflow.date.in_(dates)
        ).all()
    }

    to_add = []
    for _, r in df.iterrows():
        if r["date"] in exists:
            continue

        ocf = r.get("operating_cashflow")
        icf = r.get("investing_cashflow")

        to_add.append(FinancialCashflow(
            stock_id=sid,
            date=r["date"],
            operating_cashflow=ocf,
            investing_cashflow=icf,
            financing_cashflow=r.get("financing_cashflow"),
            free_cashflow=(ocf + icf) if (ocf is not None and icf is not None) else None,
        ))

    if to_add:
        db.session.bulk_save_objects(to_add)
        db.session.commit()

    print(f"📥 Cashflow saved: {sid} ({len(to_add)} rows)")


def save_shares(df, sid):
    dates = set(df["date"])
    exists = {
        r.date for r in FinancialShares.query.filter(
            FinancialShares.stock_id == sid,
            FinancialShares.date.in_(dates)
        ).all()
    }

    to_add = []
    for _, r in df.iterrows():
        if r["date"] in exists:
            continue
        to_add.append(FinancialShares(
            stock_id=sid,
            date=r["date"],
            shares_outstanding=r.get("shares_outstanding"),
            capital=r.get("capital"),
        ))

    if to_add:
        db.session.bulk_save_objects(to_add)
        db.session.commit()

    print(f"📥 Shares saved: {sid} ({len(to_add)} rows)")


# =============================================================
# ⭐ 主流程：抓資料 + 寫入 DB
# =============================================================
async def fetch_and_save_fundamental(stock_id):
    print(f"\n=== 📊 Fetch Fundamental: {stock_id} ===")

    datasets = [
        "TaiwanStockFinancialStatements",
        "TaiwanStockBalanceSheet",
        "TaiwanStockCashFlowsStatement",
        "TaiwanStockShareholding"
    ]

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[
            _finmind_get_async(session, ds, stock_id)
            for ds in datasets
        ])

    for r in results:
        df = process_finmind_df(r)
        if df.empty:
            print(f"⚠️ {stock_id} {r['dataset']} 無資料")
            continue

        if r["dataset"] == "TaiwanStockFinancialStatements":
            save_income(df, stock_id)
        elif r["dataset"] == "TaiwanStockBalanceSheet":
            save_balance(df, stock_id)
        elif r["dataset"] == "TaiwanStockCashFlowsStatement":
            save_cashflow(df, stock_id)
        elif r["dataset"] == "TaiwanStockShareholding":
            save_shares(df, stock_id)

    print(f"🎯 基本面資料更新完成：{stock_id}")


# =============================================================
# ⭐ 提供給外部使用的 API（舊名稱保持相容）
# =============================================================
def update_fundamental_for_symbol(stock_id):
    """讓外部服務可直接呼叫基本面更新（舊函式名稱保留）"""
    try:
        asyncio.run(fetch_and_save_fundamental(stock_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(fetch_and_save_fundamental(stock_id))
