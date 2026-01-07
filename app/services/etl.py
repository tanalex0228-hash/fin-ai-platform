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

    # 1) MultiIndex 欄位壓扁（yfinance 常見）
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = [
            " ".join([str(x) for x in col if x is not None]).strip()
            for col in df.columns
        ]

    # 2) 欄位名正規化：不管是 "Open" / "open" / "Open 2330.TW" 都變成 Open
    def norm(c: str) -> str:
        s = str(c).strip()
        first = s.split()[0].strip().lower()  # 取第一段
        if first == "open": return "Open"
        if first == "high": return "High"
        if first == "low": return "Low"
        if first == "close": return "Close"
        if first == "volume": return "Volume"
        if first == "adj": return "Adj Close"
        if s.lower().replace(" ", "") in ("adjclose", "adj_close"): return "Adj Close"
        if s.lower() == "adj close": return "Adj Close"
        return s

    df.columns = [norm(c) for c in df.columns]

    # 3) 確保 index 是日期
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    df.sort_index(inplace=True)

    # 4) 必要欄位不存在就直接不寫（回 0）
    need = {"Open", "High", "Low", "Close", "Volume"}
    if not need.issubset(set(df.columns)):
        print("❌ Missing OHLCV:", list(df.columns))
        return 0

    # 5) 報酬率
    df["return_pct"] = df["Close"].pct_change()
    df["log_return"] = df["return_pct"].apply(
        lambda x: math.log1p(x) if (x is not None and not pd.isna(x)) else None
    )

    inserted = 0

    for idx, row in df.iterrows():
        trade_date = idx.date()

        open_val = _safe_float(row.get("Open"))
        high_val = _safe_float(row.get("High"))
        low_val = _safe_float(row.get("Low"))
        close_val = _safe_float(row.get("Close"))
        volume_val = _safe_float(row.get("Volume"))
        ret_val = _safe_float(row.get("return_pct"))
        log_ret_val = _safe_float(row.get("log_return"))

        if all(v is None for v in [open_val, high_val, low_val, close_val, volume_val]):
            continue

        existing = StockPrice.query.filter_by(symbol=symbol, date=trade_date).first()

        if existing:
            existing.open = open_val
            existing.high = high_val
            existing.low = low_val
            existing.close = close_val
            existing.volume = volume_val
            existing.return_pct = ret_val
            existing.log_return = log_ret_val
        else:
            db.session.add(StockPrice(
                symbol=symbol,
                date=trade_date,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val,
                return_pct=ret_val,
                log_return=log_ret_val
            ))
            inserted += 1

    db.session.commit()
    print(f"✅ ETL {symbol} inserted={inserted}, rows={len(df)}")
    return inserted




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
