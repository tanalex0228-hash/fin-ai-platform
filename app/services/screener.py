# app/services/screener.py

import asyncio
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd

from app.extensions import db
from app.models import StockPrice              # 你的價格模型（通常是這個名字）

# 如果之後完全不用 yfinance，可以把這行拿掉
from .data_fetch_async import fetch_price_batch_turbo

from app.services.scoring.a2_scoring import compute_a2_scores
from app.services.scoring.a2_etl import build_a2_inputs




# ====== 技術指標 ======


def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    change = close.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, macd_signal




# ====== 從資料庫抓價格（取代 yfinance） ======
# ====== 從資料庫抓價格（取代 yfinance） ======

def fetch_price_batch_from_db(
    symbols: List[str],
    lookback_days: int = 800,  # 抓 2 年資料，夠算 A2
) -> Dict[str, pd.DataFrame]:
    """
    從 SQLite / app.db 的 stock_prices 抓最近 lookback_days 天的資料。
    回傳 dict: {symbol: df}，欄位全部小寫，index = 日期
    """
    if not symbols:
        return {}

    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=lookback_days)

    query = (
        db.session.query(
            StockPrice.symbol,
            StockPrice.date,
            StockPrice.open,
            StockPrice.high,
            StockPrice.low,
            StockPrice.close,
            StockPrice.volume,
        )
        .filter(StockPrice.symbol.in_(symbols))
        .filter(StockPrice.date >= start.date())
        .order_by(StockPrice.date.asc())
    )

    rows = query.all()

    # 先按照 symbol 分組
    data_map = {s: [] for s in symbols}

    for sym, date, open_, high_, low_, close_, volume_ in rows:
        data_map[sym].append({
            "date": pd.to_datetime(date),
            "open": float(open_) if open_ is not None else np.nan,
            "high": float(high_) if high_ is not None else np.nan,
            "low": float(low_) if low_ is not None else np.nan,
            "close": float(close_) if close_ is not None else np.nan,
            "volume": float(volume_) if volume_ is not None else np.nan,
        })

    result = {}

    for sym in symbols:
        recs = data_map.get(sym, [])
        if not recs:
            # 資料庫沒有 → 給空 df
            result[sym] = pd.DataFrame()
            continue

        df = pd.DataFrame(recs)
        df.sort_values("date", inplace=True)
        df.set_index("date", inplace=True)

        # 全部欄位小寫（和 screener 主流程一致）
        df.columns = [c.lower() for c in df.columns]

        result[sym] = df

    return result





# ====== 計算指標 ======


def _compute_indicators(
    df: pd.DataFrame,
    short: int,
    long: int,
    rsi_period: int,
    macd_fast: int,
    macd_slow: int,
    macd_signal: int,
    bb_window: int,
    bb_std: float,
    vol_ma_window: int,
) -> pd.DataFrame:
    """
    df 預期至少有: close, open, high, low, volume
    """
    df = df.copy().sort_index()

    if "close" not in df.columns:
        raise ValueError("DataFrame 需要 'close' 欄位")

    # MA
    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()

    # RSI
    df["rsi"] = _calc_rsi(df["close"], period=rsi_period)

    # MACD
    df["macd"], df["macd_signal"] = _calc_macd(
        df["close"],
        fast=macd_fast,
        slow=macd_slow,
        signal=macd_signal,
    )

    # 布林通道
    mid = df["close"].rolling(bb_window).mean()
    std = df["close"].rolling(bb_window).std()
    df["bb_mid"] = mid
    df["bb_upper"] = mid + bb_std * std
    df["bb_lower"] = mid - bb_std * std

    # 成交量均線
    if "volume" in df.columns:
        df["vol_ma"] = df["volume"].rolling(vol_ma_window).mean()
    else:
        df["vol_ma"] = np.nan

    return df


# ====== 打分 ======


def _score_single_symbol(
    df: pd.DataFrame,
    rsi_upper: float,
    rsi_lower: float,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    將多個技術因子轉成 -1~+1，再依照權重加總成 0~100 分。
    weights keys: "trend", "ma", "rsi", "macd", "bb", "volume", "candle"
    """
    if df.empty:
        return {
            "date": None,
            "score": 0,
            "signal": "no_data",
            "reason": "資料為空",
            "latest": None,
        }

    last = df.iloc[-1]
    needed = ["close", "ma_short", "ma_long", "rsi", "macd", "macd_signal"]

    if any(col not in df.columns for col in needed) or any(pd.isna(last.get(c)) for c in needed):
        date_str = str(getattr(last.name, "date", last.name))
        return {
            "date": date_str,
            "score": 0,
            "signal": "no_data",
            "reason": "指標資料不足",
            "latest": None,
        }

    close = float(last["close"])
    ma_short = float(last["ma_short"])
    ma_long = float(last["ma_long"])
    rsi = float(last["rsi"])
    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])

    open_ = float(last["open"]) if "open" in last and not pd.isna(last["open"]) else np.nan
    high = float(last["high"]) if "high" in last and not pd.isna(last["high"]) else np.nan
    low = float(last["low"]) if "low" in last and not pd.isna(last["low"]) else np.nan
    volume = float(last["volume"]) if "volume" in last and not pd.isna(last["volume"]) else np.nan
    bb_mid = float(last["bb_mid"]) if "bb_mid" in last and not pd.isna(last["bb_mid"]) else np.nan
    bb_upper = float(last["bb_upper"]) if "bb_upper" in last and not pd.isna(last["bb_upper"]) else np.nan
    bb_lower = float(last["bb_lower"]) if "bb_lower" in last and not pd.isna(last["bb_lower"]) else np.nan
    vol_ma = float(last["vol_ma"]) if "vol_ma" in last and not pd.isna(last["vol_ma"]) else np.nan

    reasons: List[str] = []



    # ---------- 1) 趨勢因子：價位相對長期均線 ----------
    if ma_long != 0:
        trend_raw = (close - ma_long) / ma_long
    else:
        trend_raw = 0.0
    trend_raw = max(-0.1, min(0.1, trend_raw))
    trend_score = trend_raw / 0.1  # -1 ~ +1

    if trend_score > 0.2:
        reasons.append("股價明顯在長期均線之上（偏多）")
    elif trend_score < -0.2:
        reasons.append("股價明顯跌破長期均線（偏空）")
    else:
        reasons.append("股價接近長期均線附近")



    # ---------- 2) 均線排列因子：短均 vs 長均 ----------
    if ma_long != 0:
        ma_raw = (ma_short - ma_long) / ma_long
    else:
        ma_raw = 0.0
    ma_raw = max(-0.05, min(0.05, ma_raw))
    ma_score = ma_raw / 0.05  # -1 ~ +1

    if ma_score > 0.2:
        reasons.append("短均線明顯在長均線之上（多頭排列）")
    elif ma_score < -0.2:
        reasons.append("短均線明顯在長均線之下（空頭排列）")
    else:
        reasons.append("短均線與長均線差距不大")



    # ---------- 3) RSI 因子：偏離 50 的程度 ----------
    rsi_distance = abs(rsi - 50.0) / 50.0  # 0(最佳) ~ 1(最差)
    rsi_distance = max(0.0, min(1.0, rsi_distance))
    rsi_score = (1.0 - rsi_distance) * 2 - 1.0  # 0距離→+1，50距離→-1

    if rsi < rsi_lower:
        reasons.append(f"RSI {rsi:.1f} 接近超賣區（反彈機會）")
    elif rsi > rsi_upper:
        reasons.append(f"RSI {rsi:.1f} 接近過熱區（修正風險）")
    else:
        reasons.append(f"RSI {rsi:.1f} 接近中性")



    # ---------- 4) MACD 動能因子 ----------
    macd_diff = macd - macd_signal
    macd_std = float(df["macd"].tail(30).std() or 0.0)
    if macd_std == 0:
        macd_std = 1.0
    macd_norm = macd_diff / macd_std  # 約落在 -2~+2
    macd_norm = max(-2.0, min(2.0, macd_norm))
    macd_score = macd_norm / 2.0  # -1 ~ +1

    if macd_score > 0.2:
        reasons.append("MACD 動能偏多")
    elif macd_score < -0.2:
        reasons.append("MACD 動能偏空")
    else:
        reasons.append("MACD 動能不明顯")



    # ---------- 5) 布林通道因子 ----------
    if not np.isnan(bb_mid) and not np.isnan(bb_upper) and not np.isnan(bb_lower):
        band_half = (bb_upper - bb_lower) / 2.0
        if band_half > 0:
            bb_raw = (bb_mid - close) / band_half  # close 在下軌附近→正
            bb_raw = max(-1.0, min(1.0, bb_raw))
            bb_score = bb_raw  # -1 ~ +1
        else:
            bb_score = 0.0
        if bb_score > 0.2:
            reasons.append("股價接近布林帶下軌（偏便宜）")
        elif bb_score < -0.2:
            reasons.append("股價接近布林帶上軌（偏昂貴）")
        else:
            reasons.append("股價位於布林帶中軌附近")
    else:
        bb_score = 0.0
        reasons.append("布林帶資料不足，略過此因子")



    # ---------- 6) 成交量因子 ----------
    if not np.isnan(volume) and not np.isnan(vol_ma) and vol_ma > 0:
        vol_ratio = volume / vol_ma  # 大約 0.5~2
        vol_ratio = max(0.5, min(2.0, vol_ratio))
        # 1 → 0, 0.5→ -1, 2 → +1
        vol_score = (vol_ratio - 1.0) / 0.5
        vol_score = max(-1.0, min(1.0, vol_score))
        if vol_score > 0.2:
            reasons.append("成交量明顯放大")
        elif vol_score < -0.2:
            reasons.append("成交量明顯萎縮")
        else:
            reasons.append("成交量接近平均水準")
    else:
        vol_score = 0.0
        reasons.append("成交量資料不足，略過此因子")



    # ---------- 7) K 線形態因子 ----------
    if not np.isnan(open_) and not np.isnan(high) and not np.isnan(low) and (high - low) > 0:
        body = close - open_
        rng = high - low
        candle_raw = body / rng  # 紅K靠高點→接近+1，黑K靠低點→接近-1
        candle_raw = max(-1.0, min(1.0, candle_raw))
        candle_score = candle_raw
        if candle_score > 0.3:
            reasons.append("近期出現相對強勢的紅K")
        elif candle_score < -0.3:
            reasons.append("近期出現相對明顯的黑K")
        else:
            reasons.append("近期 K 線多空力道不明顯")
    else:
        candle_score = 0.0
        reasons.append("K 線資料不足，略過此因子")

    # ---------- 權重加總 ----------
    trend_w = weights.get("trend", 0.25)
    ma_w = weights.get("ma", 0.15)
    rsi_w = weights.get("rsi", 0.15)
    macd_w = weights.get("macd", 0.15)
    bb_w = weights.get("bb", 0.15)
    vol_w = weights.get("volume", 0.10)
    candle_w = weights.get("candle", 0.05)

    # 修正負權重 + normalize
    trend_w = max(0.0, float(trend_w))
    ma_w = max(0.0, float(ma_w))
    rsi_w = max(0.0, float(rsi_w))
    macd_w = max(0.0, float(macd_w))
    bb_w = max(0.0, float(bb_w))
    vol_w = max(0.0, float(vol_w))
    candle_w = max(0.0, float(candle_w))

    w_sum = trend_w + ma_w + rsi_w + macd_w + bb_w + vol_w + candle_w
    if w_sum == 0:
        trend_w, ma_w, rsi_w, macd_w, bb_w, vol_w, candle_w = 0.25, 0.15, 0.15, 0.15, 0.15, 0.10, 0.05
        w_sum = 1.0

    trend_w /= w_sum
    ma_w /= w_sum
    rsi_w /= w_sum
    macd_w /= w_sum
    bb_w /= w_sum
    vol_w /= w_sum
    candle_w /= w_sum

    # -1 ~ +1
    total_factor = (
        trend_w * trend_score
        + ma_w * ma_score
        + rsi_w * rsi_score
        + macd_w * macd_score
        + bb_w * bb_score
        + vol_w * vol_score
        + candle_w * candle_score
    )



    # 映射成 0~100 分
    raw_score = 50.0 + total_factor * 50.0
    final_score = max(0.0, min(100.0, raw_score))

    if final_score >= 70:
        signal = "buy"
    elif final_score <= 30:
        signal = "sell"
    else:
        signal = "hold"

    date_str = str(getattr(last.name, "date", last.name))

    latest = {
        "close": close,
        "open": open_,
        "high": high,
        "low": low,
        "ma_short": ma_short,
        "ma_long": ma_long,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "bb_mid": bb_mid,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "volume": volume,
        "vol_ma": vol_ma,
    }

    return {
        "date": date_str,
        "score": float(final_score),
        "signal": signal,
        "reason": "；".join(reasons),
        "latest": latest,
    }




# ====== 主流程 ======


def run_screener(
    symbols: List[str],
    period: str = "2y",
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:

    if params is None:
        params = {}

    short = int(params.get("short", 8))
    long = int(params.get("long", 30))
    rsi_period = int(params.get("rsi_period", 14))
    rsi_upper = float(params.get("rsi_upper", 70))
    rsi_lower = float(params.get("rsi_lower", 30))
    macd_fast = int(params.get("macd_fast", 12))
    macd_slow = int(params.get("macd_slow", 26))
    macd_signal = int(params.get("macd_signal", 9))

    bb_window = int(params.get("bb_window", 20))
    bb_std = float(params.get("bb_std", 2.0))
    vol_ma_window = int(params.get("vol_ma_window", 20))

    # 因子權重（可以在 params 自訂）
    weights = {
        "trend": float(params.get("w_trend", 0.25)),
        "ma": float(params.get("w_ma", 0.15)),
        "rsi": float(params.get("w_rsi", 0.15)),
        "macd": float(params.get("w_macd", 0.15)),
        "bb": float(params.get("w_bb", 0.15)),
        "volume": float(params.get("w_volume", 0.10)),
        "candle": float(params.get("w_candle", 0.05)),
    }

        # 先從本地資料庫抓價
    price_dict = fetch_price_batch_from_db(
        symbols,
        lookback_days=800,   # 大約 1.5 年，夠算 252 天回撤
    )

    # 如果某檔在 DB 完全沒有，必要時可以考慮 fallback 到 yfinance
    # （現在先簡單處理：price_dict 裡是空 df 就當無資料）


    results: List[Dict[str, Any]] = []

    for sym in symbols:
        df = price_dict.get(sym)

        if df is None or df.empty:
            results.append({
                "symbol": sym,
                "date": None,
                "score": 0,
                "signal": "no_data",
                "reason": "無法取得價格資料",
                "latest": None,
                "score_a2": None,
                "grade_a2": "N/A",
                "a2_reason": "資料不足"
            })
            continue

        # yfinance MultiIndex（Price×Ticker）
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df = df.xs(sym, level=1, axis=1)
            except Exception:
                results.append({
                    "symbol": sym,
                    "date": None,
                    "score": 0,
                    "signal": "no_data",
                    "reason": "欄位結構不符合預期",
                    "latest": None,
                    "score_a2": None,
                    "grade_a2": "N/A",
                    "a2_reason": "資料不足"
                })
                continue

        # 所有欄位轉小寫
        df.columns = [str(c).strip().lower() for c in df.columns]

        if "close" not in df.columns:
            results.append({
                "symbol": sym,
                "date": None,
                "score": 0,
                "signal": "no_data",
                "reason": "缺少 close 欄位",
                "latest": None,
                "score_a2": None,
                "grade_a2": "N/A",
                "a2_reason": "資料不足"
            })
            continue

        # ===== 1) 計算技術指標 =====
        try:
            df_ind = _compute_indicators(
                df,
                short=short,
                long=long,
                rsi_period=rsi_period,
                macd_fast=macd_fast,
                macd_slow=macd_slow,
                macd_signal=macd_signal,
                bb_window=bb_window,
                bb_std=bb_std,
                vol_ma_window=vol_ma_window,
            )
        except Exception as e:
            results.append({
                "symbol": sym,
                "date": None,
                "score": 0,
                "signal": "error",
                "reason": f"指標計算失敗：{e}",
                "latest": None,
                "score_a2": None,
                "grade_a2": "N/A",
                "a2_reason": "資料不足"
            })
            continue

        # ===== 2) A2 需要的欄位（Momentum, Trend, Turnover, Volatility, Drawdown）=====
        from app.services.scoring.a2_etl import build_a2_inputs
        try:
            df_ind = build_a2_inputs(df_ind)
            print("A2 DEBUG COLUMNS:", df_ind.columns.tolist())
            print("A2 DEBUG TAIL:", df_ind.tail(1))

        except Exception as e:
            print("⚠️ A2 ETL error:", e)

        # ===== 3) 技術指標總分（你原本的 screener）=====
        scored = _score_single_symbol(
            df_ind,
            rsi_upper=rsi_upper,
            rsi_lower=rsi_lower,
            weights=weights,
        )

        # ===== 4) A2 評分（吃 df_ind 不是 results）=====
        try:
            df_a2 = compute_a2_scores(df_ind.tail(1))   # 只用最新一列
            a2_row = df_a2.iloc[-1]

            scored["score_a2"] = float(a2_row["score_a2"])
            scored["grade_a2"] = a2_row["grade_a2"]
            scored["a2_reason"] = a2_row["a2_reason"]

        except Exception as e:
            print("⚠️ A2 scoring error:", e)
            scored["score_a2"] = None
            scored["grade_a2"] = "N/A"
            scored["a2_reason"] = "資料不足"

        # ===== 5) 存入結果 =====
        results.append({
            "symbol": sym,
            **scored,
        })

    return results

    




