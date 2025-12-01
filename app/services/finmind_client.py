# app/services/finmind_client.py

import requests
from flask import current_app

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"


def finmind_get(dataset: str, data_id: str = None, start_date: str = "2010-01-01"):
    """
    共用 FinMind 請求函式
    dataset: 例如 "TaiwanStockPrice", "TaiwanStockFinancialStatements" 等
    data_id: 股票代碼（不含 .TW）例如 "2330"
    """
    token = current_app.config.get("FINMIND_TOKEN")

    params = {
        "dataset": dataset,
        "start_date": start_date,
    }
    if data_id:
        params["data_id"] = data_id
    if token:
        params["token"] = token

    try:
        res = requests.get(FINMIND_API_URL, params=params, timeout=20)
        if res.status_code != 200:
            print(f"⚠️ FinMind API Error {dataset} {data_id}: status={res.status_code}")
            return []

        data = res.json()
        if "data" not in data:
            print(f"⚠️ FinMind 回傳格式錯誤 {dataset} {data_id}: {data}")
            return []

        return data["data"]
    except requests.RequestException as e:
        print(f"⚠️ FinMind 網路錯誤 {dataset} {data_id}: {e}")
        return []
