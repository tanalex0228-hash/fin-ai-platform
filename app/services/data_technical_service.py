import pandas as pd
from app.models import StockPrice
from app.services.technical import (
    add_moving_averages,
    add_macd,
    add_rsi
)


# -----------------------------------------------------
# 0. 技術面文字分析（AI 解說器）
# -----------------------------------------------------
def generate_technical_comment(latest: dict, score: int) -> str:
    if not latest:
        return "目前技術指標資料不足，無法評估短線走勢。"

    close = latest.get("close")
    ma5 = latest.get("MA5")
    ma20 = latest.get("MA20")
    rsi = latest.get("RSI")
    dif = latest.get("MACD_DIF")
    dea = latest.get("MACD_DEA")
    hist = latest.get("MACD_HIST")
    vol = latest.get("volume")
    vol_ma = latest.get("vol_ma")

    parts = []

    # 1) 趨勢（均線）
    if ma5 is not None and ma20 is not None:
        if ma5 > ma20:
            parts.append("短期均線高於中期均線，屬於多頭排列，短線趨勢偏強。")
        elif ma5 < ma20:
            parts.append("短期均線低於中期均線，呈現空頭排列，股價位於相對弱勢區。")
        else:
            parts.append("短中期均線黏著，短線仍在整理區間，方向尚不明確。")

    # 2) 動能（MACD）
    if dif is not None and dea is not None and hist is not None:
        if hist > 0 and dif > dea:
            parts.append("MACD 柱狀值為正且 DIF 高於 DEA，動能偏多，有續漲或反彈的條件。")
        elif hist < 0 and dif < dea:
            parts.append("MACD 柱狀值為負且 DIF 低於 DEA，空方動能仍然佔優，需留意趨勢續弱。")
        else:
            parts.append("MACD 位於中性區附近，多空力道暫時均衡。")

    # 3) 超買超賣（RSI）
    if rsi is not None:
        if rsi >= 70:
            parts.append(f"RSI 約為 {rsi:.1f}，已接近或落在超買區，短線漲多拉回風險提升。")
        elif rsi <= 30:
            parts.append(f"RSI 約為 {rsi:.1f}，位於超賣區，若出現止跌訊號，可能出現技術性反彈。")
        elif 40 <= rsi <= 60:
            parts.append(f"RSI 約為 {rsi:.1f}，屬於中性偏穩，尚未出現明顯過熱或過冷訊號。")
        else:
            parts.append(f"RSI 約為 {rsi:.1f}，偏向弱勢區，但尚未到極端超賣。")

    # 4) 量能（Volume vs vol_ma）
    if vol is not None and vol_ma is not None:
        if vol > 1.3 * vol_ma:
            parts.append("成交量明顯高於均量，屬於放量區間，若價格順勢突破，訊號可信度較高。")
        elif vol < 0.7 * vol_ma:
            parts.append("成交量明顯低於均量，量能偏弱，突破或跌破的有效性可能有限。")
        else:
            parts.append("成交量約在均量附近，屬於正常水準，市場情緒相對平穩。")

    # 5) 總結句，參考技術面分數
    if score >= 60:
        parts.append("整體技術面評分偏高，屬於相對強勢標的，但仍需留意短線波動風險。")
    elif score >= 40:
        parts.append("整體技術面評分中等，短線多空仍在拉鋸，適合以區間震盪思維看待。")
    elif score > 0:
        parts.append("整體技術面評分偏低，走勢仍在整理或偏空階段，保守投資人宜降低持股比重。")
    else:
        parts.append("目前技術面訊號偏弱，建議耐心等待新的多頭訊號出現後再考慮進場。")

    return " ".join(parts)




# -----------------------------------------------------
# 1. 從 DB 取得價格 df
# -----------------------------------------------------
def load_price_df(symbol):
    rows = (
        StockPrice.query
        .filter_by(symbol=symbol)
        .order_by(StockPrice.date.asc())
        .all()
    )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "date": r.date,
        "open": r.open,
        "high": r.high,
        "low": r.low,
        "close": r.close,
        "volume": r.volume
    } for r in rows])

    # 全部小寫欄位
    df.columns = [c.lower() for c in df.columns]

    # 清掉任何 NaN
    df = df.dropna(subset=["open", "high", "low", "close"])

    # 日期設成 index
    df.set_index("date", inplace=True)
    return df


# -----------------------------------------------------
# 2. 計算最新技術指標
# -----------------------------------------------------
def calc_latest_technical(symbol):
    df = load_price_df(symbol)
    if df.empty:
        return {"score": 0, "latest": {}, "comment": "目前無足夠技術資料。"}

    # ➤ 加入技術指標
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)

    # 成交量均量
    df["vol_ma"] = df["volume"].rolling(20).mean()

    # 丟掉技術指標產生的 NaN
    df = df.dropna()

    latest = df.iloc[-1].to_dict()

    # ===== 技術面分數 =====
    score = 0

    ma5 = latest.get("MA5")
    ma20 = latest.get("MA20")
    rsi = latest.get("RSI")
    dif = latest.get("MACD_DIF")
    dea = latest.get("MACD_DEA")
    vol = latest.get("volume")
    vol_ma = latest.get("vol_ma")

    # MA 趨勢
    if ma5 is not None and ma20 is not None:
        if ma5 > ma20:
            score += 20

    # RSI
    if rsi is not None:
        if 40 <= rsi <= 60:
            score += 20
        elif 30 <= rsi <= 70:
            score += 10

    # MACD
    if dif is not None and dea is not None:
        if dif > dea:
            score += 20

    # 量能
    if vol is not None and vol_ma is not None:
        if vol > vol_ma:
            score += 20

    # ➤ 產生技術面文字分析
    comment = generate_technical_comment(latest, score)

    return {
        "latest": latest,
        "score": score,
        "comment": comment
    }

