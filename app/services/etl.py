# app/services/etl.py

from datetime import datetime
import pandas as pd

from ..extensions import db
from ..models import StockPrice, StockFundFlow


# app/services/etl.py
def save_price_df_to_db(symbol, df):
    from app import db
    from app.models import PriceHistory
    import pandas as pd

    saved = 0

    for idx, row in df.iterrows():
        try:
            open_val = safe_val(row[("Open", symbol)])
            high_val = safe_val(row[("High", symbol)])
            low_val = safe_val(row[("Low", symbol)])
            close_val = safe_val(row[("Close", symbol)])
            volume_val = safe_val(row[("Volume", symbol)])

            price = PriceHistory(
                symbol=symbol,
                date=idx,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val,
            )
            db.session.add(price)
            saved += 1

        except Exception as e:
            print(f"❌ Error saving row {idx} for {symbol}: {e}")

    db.session.commit()
    return saved




def save_t86_df_to_db(df: pd.DataFrame) -> int:
    """
    將 TWSE T86 的三大法人資料寫入 StockFundFlow 表。
    """
    count = 0
    for _, row in df.iterrows():
        date_val = row["日期"]
        if isinstance(date_val, datetime):
            date = date_val.date()
        else:
            date = pd.to_datetime(date_val).date()

        flow = StockFundFlow(
            symbol=row["symbol"],
            date=date,
            foreign=float(row["外資買賣超股數"]),
            investment_trust=float(row["投信買賣超股數"]),
            dealer=float(row["自營商買賣超股數"]),
        )
        db.session.add(flow)
        count += 1

    db.session.commit()
    return count
