import pandas as pd
import numpy as np

# 台股（例：2330.TW）手續費 & 稅率（可依需求調整）
FEE_RATE = 0.001425   # 買 & 賣都收
TAX_RATE = 0.003      # 賣出要收交易稅


def _calc_rsi(close, period=14):
    change = close.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, macd_signal


def backtest_ma(
    df,
    short=5,
    long=20,
    # ====== 技術濾網參數 ======
    use_rsi=False,
    rsi_period=14,
    rsi_upper=70,      # e.g. 70：過熱就不開新倉
    use_macd=False,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    trend_filter=None,  # "above_long_ma" or None
    # ====== for grid search 用來省資源 ======
    return_equity=True  # False 時不組 equity_curve（給 /strategy_optimize 用）
):
    """
    移動平均策略回測（含手續費 / 交易稅 + 技術濾網）
    df 可以是：
    - 有 'date' 欄位的 DataFrame（/backtest 用）
    - 以 date 為 index、只有 'close' 欄位（/strategy_optimize 用）
    """

    # ========= 標準化 df =========
    df = df.copy()

    if "date" in df.columns:
        # 來自 SQL: SELECT date, close ...
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    else:
        # 來自 load_price_df：index 是日期
        df = df.sort_index()
        df["date"] = df.index

    # 確保有 close 欄位
    if "close" not in df.columns:
        raise ValueError("DataFrame 必須包含 'close' 欄位")

    # ========= 基本指標：MA =========
    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()

    # ========= 技術指標：RSI / MACD =========
    # 這兩個先算好，後面依 use_rsi / use_macd 決定要不要當濾網
    df["rsi"] = _calc_rsi(df["close"], period=rsi_period)

    df["macd"], df["macd_signal"] = _calc_macd(
        df["close"],
        fast=macd_fast,
        slow=macd_slow,
        signal=macd_signal,
    )

    # ========= 原始 MA 多頭訊號 =========
    base_signal = (df["ma_short"] > df["ma_long"]).astype(int)

    # ========= 濾網 1：趨勢濾網 =========
    signal = base_signal.copy()
    if trend_filter == "above_long_ma":
        # 價格必須在長均線上方才允許做多
        signal = np.where(df["close"] > df["ma_long"], signal, 0)

    # ========= 濾網 2：RSI =========
    # RSI 過熱(> rsi_upper)就不開新多單
    if use_rsi:
        signal = np.where(df["rsi"] < rsi_upper, signal, 0)

    # ========= 濾網 3：MACD =========
    # 只有 MACD 線 > signal 線(多頭) 才允許做多
    if use_macd:
        signal = np.where(df["macd"] > df["macd_signal"], signal, 0)

    df["signal"] = signal

    # ========= 報酬計算 =========
    df["ret"] = df["close"].pct_change()
    df["position"] = df["signal"].shift(1).fillna(0)  # 用前一日 signal 下單
    df["strategy_ret"] = df["position"] * df["ret"]

    # ========= 手續費 / 交易稅 =========
    df["trade"] = df["position"].diff().fillna(0)

    def calc_cost(row):
        if row["trade"] == 1:        # 開多：買進
            return -FEE_RATE
        elif row["trade"] == -1:     # 平倉：賣出（含手續費 + 稅）
            return -(FEE_RATE + TAX_RATE)
        return 0

    df["cost"] = df.apply(calc_cost, axis=1)
    df["strategy_ret_cost"] = df["strategy_ret"] + df["cost"]

    # ========= Equity Curve & Drawdown =========
    df["cum_buy_hold"] = (1 + df["ret"]).cumprod()
    df["cum_strategy"] = (1 + df["strategy_ret_cost"]).cumprod()

    running_max = df["cum_strategy"].cummax()
    df["drawdown"] = (df["cum_strategy"] - running_max) / running_max

    # ========= 總績效 =========
    total_return = df["cum_strategy"].iloc[-1] - 1
    buy_hold_return = df["cum_buy_hold"].iloc[-1] - 1
    sharpe = df["strategy_ret_cost"].mean() / (df["strategy_ret_cost"].std() + 1e-9)
    max_dd = df["drawdown"].min()

    # ========= 交易明細 =========
    trades = []
    position = 0
    entry_price = None
    entry_date = None

    for _, row in df.iterrows():
        if position == 0 and row["trade"] == 1:
            position = 1
            entry_price = row["close"] * (1 + FEE_RATE)
            entry_date = row["date"]
        elif position == 1 and row["trade"] == -1:
            exit_price = row["close"] * (1 - FEE_RATE - TAX_RATE)
            exit_date = row["date"]
            ret = (exit_price - entry_price) / entry_price

            trades.append({
                "entry_date": str(entry_date),
                "entry_price": float(entry_price),
                "exit_date": str(exit_date),
                "exit_price": float(exit_price),
                "return_pct": float(ret)
            })

            position = 0

    # ========= 給前端畫圖用的曲線 =========
    equity_curve = None
    if return_equity:
        equity_curve = []
        for _, row in df.iterrows():
            equity_curve.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": float(row["close"]),
                "cum_buy_hold": None if pd.isna(row["cum_buy_hold"]) else float(row["cum_buy_hold"]),
                "cum_strategy": None if pd.isna(row["cum_strategy"]) else float(row["cum_strategy"]),
                "drawdown": None if pd.isna(row["drawdown"]) else float(row["drawdown"]),
                "ma_short": None if pd.isna(row["ma_short"]) else float(row["ma_short"]),
                "ma_long": None if pd.isna(row["ma_long"]) else float(row["ma_long"]),
                "rsi": None if pd.isna(row["rsi"]) else float(row["rsi"]),
                "macd": None if pd.isna(row["macd"]) else float(row["macd"]),
                "macd_signal": None if pd.isna(row["macd_signal"]) else float(row["macd_signal"]),
            })

    return {
        "performance": {
            "total_return": float(total_return),
            "buy_hold_return": float(buy_hold_return),
            "sharpe": float(sharpe),
            "max_drawdown": float(max_dd),
            "trade_count": len(trades),
            "win_rate": float(sum(t["return_pct"] > 0 for t in trades) / len(trades)) if trades else None,
        },
        "params": {
            "short": short,
            "long": long,
            "use_rsi": use_rsi,
            "rsi_period": rsi_period,
            "rsi_upper": rsi_upper,
            "use_macd": use_macd,
            "macd_fast": macd_fast,
            "macd_slow": macd_slow,
            "macd_signal": macd_signal,
            "trend_filter": trend_filter,
        },
        "equity_curve": equity_curve,
        "trades": trades,
    }
