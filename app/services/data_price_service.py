# app/services/data_price_service.py

import pandas as pd
from datetime import date

from app.extensions import db
from app.models import StockPrice
from app.services.finmind_client import finmind_get


# ---------------------------------------
# 📌 將 symbol 轉成 FinMind 用的 stock_id（去掉 .TW / .TWO）
# ---------------------------------------
def _clean_sid(symbol: str) -> str:
    return symbol.replace(".TW", "").replace(".TWO", "")


# ---------------------------------------
# 📌 從 FinMind 抓股價（取代 yfinance）
# ---------------------------------------
def fetch_price_from_finmind(symbol: str, start_date: str = "2000-01-01") -> pd.DataFrame:
    stock_id = _clean_sid(symbol)

    raw = finmind_get(
        dataset="TaiwanStockPrice",
        data_id=stock_id,
        start_date=start_date,
    )

    if not raw:
        print(f"⚠️ FinMind 沒有回傳股價資料: {symbol}")
        return pd.DataFrame()

    df = pd.DataFrame(raw)

    df["date"] = pd.to_datetime(df["date"]).dt.date

    df = df.rename(columns={
        "open": "open",
        "max": "high",
        "min": "low",
        "close": "close",
        "Trading_Volume": "volume",
    })

    df = df[["date", "open", "high", "low", "close", "volume"]]

    # ===== 缺值保護 =====
    df["open"] = df["open"].fillna(method="ffill")
    df["high"] = df["high"].fillna(method="ffill")
    df["low"] = df["low"].fillna(method="ffill")
    df["close"] = df["close"].fillna(method="ffill")
    df["volume"] = df["volume"].fillna(0)

    return df



# ---------------------------------------
# 📌 寫入 DB（update-if-exists）
# ---------------------------------------
def save_price_to_db(symbol: str, df: pd.DataFrame):
    """
    將 df 寫入 stock_prices 資料表
    - 若 (symbol, date) 已存在 → 更新
    - 否則 → 新增
    """
    if df is None or df.empty:
        print(f"⚠️ {symbol} df 為空，略過寫入")
        return

    # 保險：確保 date 是 Python date
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    for _, row in df.iterrows():
        d = row["date"]

        open_p = row.get("open")
        close_p = row.get("close")

        # 安全計算 return_pct
        if (
            open_p is None
            or close_p is None
            or pd.isna(open_p)
            or pd.isna(close_p)
            or open_p == 0
        ):
            return_pct = None
        else:
            return_pct = close_p / open_p - 1

        exists = StockPrice.query.filter_by(
            symbol=symbol,
            date=d
        ).first()

        if exists:
            exists.open = open_p
            exists.high = row.get("high")
            exists.low = row.get("low")
            exists.close = close_p
            exists.volume = row.get("volume")
            exists.return_pct = return_pct
        else:
            rec = StockPrice(
                symbol=symbol,
                date=d,
                open=open_p,
                high=row.get("high"),
                low=row.get("low"),
                close=close_p,
                volume=row.get("volume"),
                return_pct=return_pct,
                log_return=None,
            )
            db.session.add(rec)

    db.session.commit()
    print(f"✅ {symbol} 價格寫入完成，共 {len(df)} 筆")


# ---------------------------------------
# 📌 單檔更新：抓 + 寫入
# ---------------------------------------
def update_price_history(symbol: str, start_date: str = "2018-01-01"):
    """
    給外部使用的主函式：
    - 用 FinMind 抓趨勢以來股價
    - 寫入 DB
    """
    print(f"📌 使用 FinMind 更新 {symbol} 股價，自 {start_date} 起...")
    df = fetch_price_from_finmind(symbol, start_date=start_date)
    if df.empty:
        print(f"⚠️ {symbol} 無任何資料，略過")
        return
    save_price_to_db(symbol, df)


# ---------------------------------------
# 📌 從 DB 讀回 DataFrame（給技術面 / 風險用）
# ---------------------------------------
def get_price_df(symbol: str) -> pd.DataFrame:
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
        "open": r.open,
        "high": r.high,
        "low": r.low,
        "close": r.close,
        "volume": r.volume,
    } for r in rows])

    df.set_index("date", inplace=True)
    return df


# ⭐ 舊名稱相容：如果以前有 import load_price_df，就不會爆掉
def load_price_df(symbol: str) -> pd.DataFrame:
    return get_price_df(symbol)
