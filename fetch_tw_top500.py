import yfinance as yf
import pandas as pd
from tqdm import tqdm

def is_valid_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        return df is not None and not df.empty
    except:
        return False

def get_market_cap(symbol):
    try:
        info = yf.Ticker(symbol).fast_info
        return info.get("market_cap", None)
    except:
        return None

def main():
    print("📌 產生台股（縮短版）候選股票")
    tw_listed = [f"{i:04d}.TW" for i in range(1, 3000)]   # 上市 3000
    tw_otc = [f"{i:04d}.TWO" for i in range(1, 2000)]     # 上櫃 2000

    candidates = tw_listed + tw_otc
    print("📌 候選總數：", len(candidates))

    valid = []
    print("📌 檢查有效股票 (1y)...")
    for sym in tqdm(candidates):
        if is_valid_stock(sym):
            valid.append(sym)

    print("✔ 有效股票 =", len(valid))

    print("📌 抓市值...")
    df = pd.DataFrame({"symbol": valid})
    df["cap"] = df["symbol"].apply(get_market_cap)
    df = df.dropna(subset=["cap"])

    print("✔ 有市值的股票 =", len(df))

    df_top500 = df.sort_values("cap", ascending=False).head(500)
    df_top500.to_json("tw_top500.json", orient="values", force_ascii=False)

    print("🎉 完成！輸出 tw_top500.json")
    print(df_top500.head())

if __name__ == "__main__":
    main()
