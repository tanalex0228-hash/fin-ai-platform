# load_prices.py
import json
from app.services.db_loader import update_price_history
from app import create_app

app = create_app()
ctx = app.app_context()
ctx.push()

# 載入 TW500 + ETF（你之前存的）
with open("tw_top500.json") as f:
    symbols = json.load(f)

# 只抓前 300
symbols = symbols[:300]

print(f"共 {len(symbols)} 檔股票需要下載")

for sym in symbols:
    try:
        update_price_history(sym, years=15)
    except Exception as e:
        print(f"⚠️ {sym} 下載失敗：{e}")
