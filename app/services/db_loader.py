import json
import time
from datetime import date, timedelta

from app.models import StockPrice
from app.services.data_price_service import update_price_history


# -------------------------------------------------
# 讀取股票清單
# -------------------------------------------------
def load_symbols_from_file(path="tw_top500.json"):
    with open(path, "r") as f:
        syms = json.load(f)

    norm = []
    for s in syms:
        s = s.strip()
        if s.endswith(".TW") or s.endswith(".TWO"):
            norm.append(s)
        else:
            norm.append(s + ".TW")
    return norm


# -------------------------------------------------
# 取得增量更新起點
# -------------------------------------------------
def get_next_start_date(symbol: str, fallback: str):
    """
    回傳下一個應該更新的 start_date
    - 若 DB 無資料 → fallback
    - 若已是最新 → None
    """
    last = (
        StockPrice.query
        .filter_by(symbol=symbol)
        .order_by(StockPrice.date.desc())
        .first()
    )

    if not last:
        return fallback

    next_date = last.date + timedelta(days=1)

    # 🔒 未來日期保護
    today = date.today()

    # 若 next_date >= today，代表今天還沒收盤或是假日
    if next_date >= today:
        return None

    

    return next_date.isoformat()


# -------------------------------------------------
# 批次更新全部股票
# -------------------------------------------------
def update_all_prices(start_date="2018-01-01", limit=None, sleep_sec=0.3):
    symbols = load_symbols_from_file("tw_top500.json")

    for i, sym in enumerate(symbols):
        if limit is not None and i >= limit:
            print(f"⏹ 已達 limit={limit}，停止")
            break

        next_start = get_next_start_date(sym, fallback=start_date)

        if not next_start:
            print(f"⏭ {sym} 已是最新，略過")
            continue

        print(f"🚀 {sym} 增量更新起點: {next_start}")
        update_price_history(sym, start_date=next_start)
        time.sleep(sleep_sec)
