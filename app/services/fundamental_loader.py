# app/services/fundamental_loader.py

import asyncio
from flask import current_app
from app.extensions import db

# 引入你已有的 FinMind async service
from app.services.data_fundamental_service import (
    fetch_and_save_fundamental
)

# 舊名稱相容
def fetch_and_save(stock_id: str):
    """
    給 update_fundamental_full.py 使用：
    同步版本的 fetch_and_save_fundamental
    """
    # 確保 stock_id 沒有 .TW / .TWO
    sid = stock_id.replace(".TW", "").replace(".TWO", "")

    try:
        asyncio.run(fetch_and_save_fundamental(sid))
    except RuntimeError as e:
        # Jupyter / Flask debug 模式下 event loop 可能已在執行
        if "cannot run the event loop" in str(e) or "another loop is running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(fetch_and_save_fundamental(sid))
        else:
            raise e


# 非同步版本（未來可做大量更新用）
async def fetch_and_save_async(stock_id: str):
    sid = stock_id.replace(".TW", "").replace(".TWO", "")
    await fetch_and_save_fundamental(sid)
