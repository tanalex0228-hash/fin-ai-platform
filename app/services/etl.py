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
    """
    將單一股票的價格 DataFrame 寫入 StockPrice 資料表。

    期待的 df 格式：
        index: DatetimeIndex (交易日期)
        columns 至少包含: 'Open', 'High', 'Low', 'Close', 'Volume'
        （這跟 data_fetch_async._download_yf 的輸出一致）

    行為：
        - 若 (symbol, date) 已經存在 → 更新該筆資料
        - 否則 → 新增一筆
        - 同時計算 return_pct 與 log_return
    """
    if df is None or df.empty:
        return 0

    # 確保 index 是 datetime，並依日期排序
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    # 先在 DataFrame 層級計算報酬率（效率比較好）
    df["return_pct"] = df["Close"].pct_change()
    # 避免 log(1 + NaN) / log(1 + 負到爆炸）
    df["log_return"] = df["return_pct"].apply(
        lambda x: math.log1p(x) if (x is not None and not pd.isna(x)) else None
    )

    saved = 0

    for idx, row in df.iterrows():
        trade_date = idx.date()  # datetime → date (對應到 models.StockPrice 的 Date 型別)

        open_val = _safe_float(row.get("Open"))
        high_val = _safe_float(row.get("High"))
        low_val = _safe_float(row.get("Low"))
        close_val = _safe_float(row.get("Close"))
        volume_val = _safe_float(row.get("Volume"))
        ret_val = _safe_float(row.get("return_pct"))
        log_ret_val = _safe_float(row.get("log_return"))

        # 如果這一行完全沒有價格資訊，就直接跳過
        if all(v is None for v in [open_val, high_val, low_val, close_val, volume_val]):
            continue

        try:
            # 檢查這個 symbol + date 是否已存在
            existing = StockPrice.query.filter_by(
                symbol=symbol,
                date=trade_date
            ).first()

            if existing:
                # 更新已有紀錄
                existing.open = open_val
                existing.high = high_val
                existing.low = low_val
                existing.close = close_val
                existing.volume = volume_val
                existing.return_pct = ret_val
                existing.log_return = log_ret_val
            else:
                # 新增一筆新的價格紀錄
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
