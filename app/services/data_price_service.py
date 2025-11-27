# app/services/data_price_service.py

import yfinance as yf
import pandas as pd
from datetime import datetime

from app.extensions import db
from app.models import StockPrice


# ---------------------------------------
# 📌 欄位標準化
# ---------------------------------------
def clean_columns(df):
    df = df.copy()

    # 統一欄位名稱
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rename_map = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "adj_close": "close",   # 若有調整後收盤價 → 使用它
        "volume": "volume"
    }

    new_cols = {}
    for c in df.columns:
        if c in rename_map:
            new_cols[c] = rename_map[c]

    df = df.rename(columns=new_cols)

    # 確保 date 欄位存在
    if "date" not in df.columns:
        df = df.reset_index().rename(columns={"index": "date"})

    # 把 date 轉成 Python date（避免比對錯誤）
    df["date"] = pd.to_datetime(df["date"]).dt.date

    return df


# ---------------------------------------
# 📌 從 Yahoo 抓資料（自動處理 MultiIndex）
# ---------------------------------------
def fetch_price_from_yf(symbol, start=None, period="1y"):
    df = yf.download(
        symbol,
        start=start,
        period=None if start else period,
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        return df

    # 🟦 如果是單日資料 → index 是 DatetimeIndex → 必須 reset_index()
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    # 🟦 若出現 'Date' 欄 → rename 成 'date'
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "date"})

    # MultiIndex → 展平
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(symbol, level=1, axis=1)
        except:
            df = df.droplevel(1, axis=1)

    # 🟦 再保險一次：第一欄可能不是 date → 強制命名
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})

    df = clean_columns(df)
    return df


# ---------------------------------------
# 📌 寫入 DB（safe: update-if-exists）
# ---------------------------------------
def save_price_to_db(symbol: str, df: pd.DataFrame):
    df = clean_columns(df)

    for _, row in df.iterrows():

        open_p = row.get("open")
        close_p = row.get("close")

        # 🟦 安全 return_pct：避免 None, NaN, zero
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
            date=row["date"]
        ).first()

        if exists:
            exists.open = open_p
            exists.high = row.get("high")
            exists.low = row.get("low")
            exists.close = close_p
            exists.volume = row.get("volume")
            exists.return_pct = return_pct

        else:
            price = StockPrice(
                symbol=symbol,
                date=row["date"],
                open=open_p,
                high=row.get("high"),
                low=row.get("low"),
                close=close_p,
                volume=row.get("volume"),
                return_pct=return_pct,
                log_return=None
            )
            db.session.add(price)

    db.session.commit()



# ---------------------------------------
# 📌 從資料庫讀取成 DataFrame
# ---------------------------------------
def get_price_df(symbol):
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



# ---------------------------------------
# 📌 load_price_df：stock_summary_service 需要的簡化版
# ---------------------------------------
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