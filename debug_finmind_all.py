# debug_finmind_all.py

from dotenv import load_dotenv
load_dotenv()

from FinMind.data import DataLoader
import os
import pandas as pd

dl = DataLoader()
dl.login_by_token(os.getenv("FINMIND_API_TOKEN"))

stock = "2330"

def show(name, df):
    print(f"\n\n===== 🔍 {name} =====")
    if df is None or df.empty:
        print("⚠️ 無資料")
        return
    print(f"📌 Rows: {len(df)}")
    print(f"📌 Columns: {list(df.columns)}\n")
    print(df.head(20).to_string())

# --- 各類財報 ---
res = dl.api(
    dataset="TaiwanStockFinancialStatements",
    data_id=stock,
    start_date="2019-01-01"
)

print("=== RAW RESPONSE ===")
print(res)

balance = dl.taiwan_stock_balance_sheet(stock_id=stock, start_date="2019-01-01")
cashflow = dl.taiwan_stock_cash_flows_statement(stock_id=stock, start_date="2019-01-01")
share = dl.taiwan_stock_shareholding(stock_id=stock, start_date="2019-01-01")

show("Income", income)
show("Balance", balance)
show("Cashflow", cashflow)
show("Shareholding", share)
