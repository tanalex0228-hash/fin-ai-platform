# app/services/db_loader.py

import json
import time

from app.services.data_price_service import update_price_history


def load_symbols_from_file(path="tw_top500.json"):
    with open(path, "r") as f:
        syms = json.load(f)

    # 確保都有 .TW 尾巴（簡單版）
    norm = []
    for s in syms:
        s = s.strip()
        if s.endswith(".TW") or s.endswith(".TWO"):
            norm.append(s)
        else:
            # 這裡你可以自己決定要不要補 .TW
            norm.append(s + ".TW")
    return norm


def update_all_prices(start_date="2018-01-01", limit=None, sleep_sec=0.3):
    """
    用 FinMind 依序更新 tw_top500.json 裡面的標的
    - limit: 最多更新幾檔（避免一次打爆 API）
    - sleep_sec: 每檔之間稍微 sleep，保險用
    """
    symbols = load_symbols_from_file("tw_top500.json")

    for i, sym in enumerate(symbols):
        if limit is not None and i >= limit:
            print(f"⏹ 已達 limit={limit}，停止")
            break

        update_price_history(sym, start_date=start_date)
        time.sleep(sleep_sec)
