import yfinance as yf
import pandas as pd
from app.extensions import db
from app.models import StockPrice

def clean_columns(df):
    """
    將 MultiIndex 欄位轉成單層欄位並小寫化
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]
    return df


def save_price_to_db(symbol: str, df: pd.DataFrame):
    df = df.reset_index()
    df = clean_columns(df)

    for _, row in df.iterrows():
        date = row["date"]

        # --- 若資料已存在 → 跳過 ---
        exists = StockPrice.query.filter_by(symbol=symbol, date=date).first()
        if exists:
            continue

        # --- 計算報酬 ---
        open_ = row.get("open")
        close_ = row.get("close")
        return_pct = (close_ / open_ - 1) if (open_ and open_ != 0) else None

        price = StockPrice(
            symbol=symbol,
            date=date,
            open=open_,
            high=row.get("high"),
            low=row.get("low"),
            close=close_,
            volume=row.get("volume"),
            return_pct=return_pct,
            log_return=None,  # 未來可補：np.log(close/open)
        )

        db.session.add(price)

    db.session.commit()



def update_price_history(symbol: str, years: int = 5):
    print(f"📌 正在下載 {symbol} 的歷史資料 ({years} 年)...")

    df = yf.download(
        symbol,
        period=f"{years}y",
        interval="1d",
        progress=False,
        auto_adjust=False   # 必須加這個！
    )

    if df.empty:
        print(f"⚠️ 無法下載 {symbol}")
        return

    df = clean_columns(df)
    save_price_to_db(symbol, df)
    print(f"✅ {symbol} 寫入資料庫完成！共 {len(df)} 筆")
