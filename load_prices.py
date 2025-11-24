# load_prices.py
import json
from app.services.db_loader import update_price_history
from app import create_app


def update_all_prices(limit=300, years=35):
    """
    每日更新資料（改為只抓最近 5 天，但保留 years 作為兼容參數）
    """
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    # 載入 TW500 + ETF（你之前存的）
    with open("tw_top500.json") as f:
        symbols = json.load(f)

    # 只抓前 limit（保持你原來 symbols[:300] 的邏輯）
    symbols = symbols[:limit]

    print(f"共 {len(symbols)} 檔股票需要下載（最近 5 天）")

    for sym in symbols:
        try:
            # ⭐⭐ 改這一行：每日更新只抓 5 天，不重抓歷史 ⭐⭐
            update_price_history(sym, period="5d")
        except Exception as e:
            print(f"⚠️ {sym} 更新失敗：{e}")


# 讓 python load_prices.py 可以直接跑（保持你的原設計）
if __name__ == "__main__":
    update_all_prices(limit=300)
