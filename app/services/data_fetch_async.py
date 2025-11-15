# app/services/data_fetch_async.py

import asyncio
from datetime import datetime
from typing import List, Optional
import pandas as pd
import yfinance as yf
import aiohttp

# -----------------------------
# 🟦 yfinance async (核心功能)
# -----------------------------
def _download_yf(symbol: str, period="1y", interval="1d") -> Optional[pd.DataFrame]:
    """確保每支股票獨立下載，不會產生 MultiIndex"""

    symbol = str(symbol)  # 🔥 強制是字串，避免 yfinance 當 list

    df = yf.download(
        tickers=symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        group_by="ticker",     # 🔥 這樣最乾淨
    )

    if df is None or df.empty:
        return None

    # yfinance 有時候還是會給 MultiIndex → 在這裡統一清理
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)

    df.index = pd.to_datetime(df.index)
    df = df.dropna(how="all")
    return df


async def fetch_price_single(symbol: str, period="1y", interval="1d"):
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, _download_yf, symbol, period, interval)
    return df


async def fetch_price_batch(symbols: List[str], period="1y", interval="1d"):
    """一次 async 抓多支股票，但每支股票會獨立下載"""

    tasks = [fetch_price_single(sym, period, interval) for sym in symbols]
    results = await asyncio.gather(*tasks)

    out = {}
    for sym, df in zip(symbols, results):
        if df is not None and not df.empty:
            out[sym] = df  # 🔥 此時已經是單層 columns
    return out


# -----------------------------
# 🟩 台股法人（T86）
# -----------------------------
async def _fetch_twse_t86_single(session: aiohttp.ClientSession, stock_num: str, d: datetime):
    date_str = d.strftime("%Y%m%d")
    url = (
        f"https://www.twse.com.tw/fund/T86"
        f"?response=html&date={date_str}&selectType=ALLBUT0999&stockNo={stock_num}"
    )
    try:
        async with session.get(url) as resp:
            html = await resp.text()
            tables = pd.read_html(html)
            if not tables:
                return None

            table = tables[0]
            if isinstance(table.columns, pd.MultiIndex):
                table.columns = table.columns.droplevel(0)
            table.columns = [c.strip() for c in table.columns]

            table["日期"] = pd.to_datetime(d)
            table["外資買賣超股數"] = (
                table["外陸資買賣超股數(不含外資自營商)"].astype(int)
                + table["外資自營商買賣超股數"].astype(int)
            )
            table["投信買賣超股數"] = table["投信買賣超股數"].astype(int)
            table["自營商買賣超股數"] = table["自營商買賣超股數"].astype(int)

            table = table[["日期", "證券代號", "外資買賣超股數", "投信買賣超股數", "自營商買賣超股數"]]
            return table
    except Exception:
        return None


async def fetch_twse_t86_range(stock_num: str, start_date: datetime, end_date: datetime):
    dates = pd.date_range(start=start_date, end=end_date)
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_twse_t86_single(session, stock_num, d.to_pydatetime()) for d in dates]
        results = await asyncio.gather(*tasks)

    dfs = [r for r in results if r is not None]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
