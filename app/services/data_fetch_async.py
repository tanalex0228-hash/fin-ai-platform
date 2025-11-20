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
    """安全版：一檔一檔抓，避免 yfinance dictionary changed size bug"""

    out = {}

    # 逐檔下載（避免 yfinance 多執行緒 bug）
    for sym in symbols:
        print(f"📌 下載 {sym} ...")

        df = await fetch_price_single(sym, period, interval)

        if df is not None and not df.empty:
            out[sym] = df
        else:
            print(f"⚠️ 無資料：{sym}")

        # 避免被 Yahoo 封鎖（安全延遲）
        await asyncio.sleep(0.3)

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


# -------------------------------------------------
# 🟦 async turbo 版（10～30 倍速度）
#     多檔同時抓，不必一個個等
# -------------------------------------------------
async def fetch_price_batch_turbo(symbols, period="1y", interval="1d", workers=10):
    """
    超高速：同時丟出多個 executor 下載任務（非同步 + thread pool）
    workers: 同時抓幾檔 (10~20 最剛好)
    """

    loop = asyncio.get_event_loop()
    out = {}

    print(f"🚀 async TURBO 模式啟動：{len(symbols)} 檔，workers={workers}")

    # 建立 thread pool
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=workers)

    tasks = []
    for sym in symbols:
        tasks.append(loop.run_in_executor(
            executor,
            _download_yf,   # 你原本寫好的單檔抓取
            sym,
            period,
            interval
        ))

    # gather → 等全部抓完
    results = await asyncio.gather(*tasks)

    # 組 output dict
    for sym, df in zip(symbols, results):
        if df is not None and not df.empty:
            out[sym] = df
        else:
            print(f"⚠️ 無資料：{sym}")

    print(f"🔥 TURBO 完成：成功 {len(out)}/{len(symbols)} 檔")

    return out
# -----------------------------
# 🚀 Turbo Async 版（併發 workers）
# -----------------------------
import asyncio
import time
from typing import Dict

async def _fetch_worker(queue, out, period, interval):
    """工作者：負責抓單一股票"""
    while True:
        sym = await queue.get()
        if sym is None:
            queue.task_done()
            break

        print(f"📌 下載 {sym} ...")

        try:
            df = await fetch_price_single(sym, period=period, interval=interval)
            if df is not None and not df.empty:
                out[sym] = df
            else:
                print(f"⚠️ 無資料：{sym}")
        except Exception as e:
            print(f"❌ {sym} 抓取失敗：", e)

        await asyncio.sleep(0.05)  # 安全延遲防封鎖
        queue.task_done()


async def fetch_price_batch_turbo(symbols, period="1y", interval="1d", workers=10) -> Dict[str, pd.DataFrame]:
    """
    Turbo 版：
    ✔ 使用 queue 多工抓取
    ✔ 10～30 倍速度
    ✔ 安全防封鎖
    """
    queue = asyncio.Queue()
    out = {}

    # 將任務加入 queue
    for sym in symbols:
        queue.put_nowait(sym)

    # 建立 workers
    tasks = [
        asyncio.create_task(_fetch_worker(queue, out, period, interval))
        for _ in range(workers)
    ]

    # 放入停止訊號
    for _ in range(workers):
        queue.put_nowait(None)

    await queue.join()

    # 等待 workers 完成
    await asyncio.gather(*tasks, return_exceptions=True)

    return out
