# app/services/etl.py

from datetime import datetime
import math
import pandas as pd

from ..extensions import db
from ..models import StockPrice, StockFundFlow


def _safe_float(value):
    """
    把各種奇怪的數值 (NaN、None、字串) 安全轉成 float 或 None。
    用來避免寫進 DB 時因為 NaN/型態錯誤爆掉。
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    # 避免 NaN 寫進資料庫
    if math.isnan(v):
        return None
    return v


def save_price_df_to_db(symbol: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0

    df = df.copy()

    # ✅ 欄位名標準化：不管 Open / open / Adj Close / adjclose 都先轉成可比對 key
    def _norm_col(c: str) -> str:
        return str(c).strip().lower().replace(" ", "").replace("_", "")

    colmap = {_norm_col(c): c for c in df.columns}

    def _get(row, key: str):
        """key 用標準名，例如 open/high/low/close/volume"""
        k = _norm_col(key)
        real = colmap.get(k)
        return row.get(real) if real is not None else None

    # ✅ 確保 index 是 datetime
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    df.sort_index(inplace=True)

    # ✅ 用 close 計算報酬（close 也可能是 Close / close）
    close_series = df[colmap.get("close")] if "close" in colmap else None
    if close_series is not None:
        df["return_pct"] = close_series.pct_change()
        df["log_return"] = df["return_pct"].apply(
            lambda x: math.log1p(x) if (x is not None and not pd.isna(x)) else None
        )
    else:
        df["return_pct"] = None
        df["log_return"] = None

    saved = 0

    for idx, row in df.iterrows():
        trade_date = idx.date()

        open_val = _safe_float(_get(row, "open"))
        high_val = _safe_float(_get(row, "high"))
        low_val  = _safe_float(_get(row, "low"))
        close_val = _safe_float(_get(row, "close"))
        volume_val = _safe_float(_get(row, "volume"))

        ret_val = _safe_float(row.get("return_pct"))
        log_ret_val = _safe_float(row.get("log_return"))

        if all(v is None for v in [open_val, high_val, low_val, close_val, volume_val]):
            continue

        try:
            existing = StockPrice.query.filter_by(symbol=symbol, date=trade_date).first()

            if existing:
                existing.open = open_val
                existing.high = high_val
                existing.low = low_val
                existing.close = close_val
                existing.volume = volume_val
                existing.return_pct = ret_val
                existing.log_return = log_ret_val
                # （可選）你想看更新也算數字，就加這行：
                # saved += 1
            else:
                price = StockPrice(
                    symbol=symbol,
                    date=trade_date,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    volume=volume_val,
                    return_pct=ret_val,
                    log_return=log_ret_val,
                )
                db.session.add(price)
                saved += 1

        except Exception as e:
            print(f"❌ Error saving row {idx} for {symbol}: {e}")

    db.session.commit()
    return saved



def save_t86_df_to_db(df: pd.DataFrame) -> int:
    """
    將 TWSE T86 的三大法人資料寫入 StockFundFlow 表。
    """
    count = 0
    for _, row in df.iterrows():
        date_val = row["日期"]
        if isinstance(date_val, datetime):
            date = date_val.date()
        else:
            date = pd.to_datetime(date_val).date()

        flow = StockFundFlow(
            symbol=row["symbol"],
            date=date,
            foreign=float(row["外資買賣超股數"]),
            investment_trust=float(row["投信買賣超股數"]),
            dealer=float(row["自營商買賣超股數"]),
        )
        db.session.add(flow)
        count += 1

    db.session.commit()
    return count
