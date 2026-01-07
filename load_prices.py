# load_prices.py

from app import create_app
from app.services.db_loader import update_all_prices

app = create_app()
ctx = app.app_context()
ctx.push()

if __name__ == "__main__":
    # 這裡可以自己調整 start_date / limit
    # limit=100 → 一次只更新 100 檔，安全不會打爆 600 次/小時
# 🔥 再抓 1990~2018
    update_all_prices(start_date="2018-01-01", limit=None , sleep_sec=0.3)