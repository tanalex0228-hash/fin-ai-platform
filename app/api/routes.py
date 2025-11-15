# app/api/routes.py
from flask import Blueprint, request, jsonify
from ..services import data_fetch_async, etl, technical, portfolio, monte_carlo, fourier, stress_test
from ..services.deeplearning import cnn, rnn, knn
from . import api_bp   # ← 用 __init__ 裡的那個 Blueprint，不是自己創的




@api_bp.route("/stock/summary", methods=["GET"])
def stock_summary():
    symbol = request.args.get("symbol")
    return jsonify({"symbol": symbol, "message": "這裡之後回傳完整股票摘要"})


@api_bp.route("/backtest", methods=["POST"])
def api_backtest():
    data = request.get_json()
    symbol = data.get("symbol")
    strategy = data.get("strategy", "ma")
    return jsonify({"status": "ok", "symbol": symbol, "strategy": strategy})


@api_bp.route("/portfolio/suggest", methods=["POST"])
def portfolio_suggest():
    payload = request.get_json()
    return jsonify({"status": "ok", "suggestion": {}})


@api_bp.route("/ai/predict", methods=["GET"])
def ai_predict():
    symbol = request.args.get("symbol")
    horizon = int(request.args.get("horizon", 5))
    model_name = request.args.get("model", "cnn")

    return jsonify({
        "symbol": symbol,
        "horizon": horizon,
        "model": model_name,
        "prob_up": 0.6,
        "prob_down": 0.4,
    })


# -------------------------
# 🚀 新增：非同步抓價格 + 寫入 DB
# -------------------------
@api_bp.route("/fetch_prices", methods=["POST"])
def fetch_prices():
    import asyncio
    import pandas as pd

    data = request.get_json()
    symbols = data.get("symbols", [])
    period = data.get("period", "1mo")

    print("📌 收到 symbols =", symbols)
    print("📌 period =", period)

    if not symbols:
        return jsonify({"error": "symbols is required"}), 400

    print("📌 開始抓價格……")
    price_dict = asyncio.run(
        data_fetch_async.fetch_price_batch(symbols, period=period)
    )

    print("📌 抓到的 price_dict keys =", list(price_dict.keys()))

    total_saved = 0

    for sym, df in price_dict.items():
        print("📌 df.head(3) =\n", df.head(3))
        print(f"📌 {sym} df shape =", df.shape)
        print("📌 df.columns =", df.columns)

        # -------------------------------
        # ✔️ MultiIndex 正確處理
        # -------------------------------
        if isinstance(df.columns, pd.MultiIndex):
            print("📌 MultiIndex detected → selecting only", sym)

            try:
                df = df.xs(sym, level="Ticker", axis=1)
            except Exception as e:
                print("❌ xs() failed:", e)
                return jsonify({"error": "MultiIndex error"}), 500

        print("📌 修正後 df.columns =", df.columns)

        # -------------------------------
        # 寫進 DB
        # -------------------------------
        total_saved += etl.save_price_df_to_db(sym, df)

    print("📌 寫入完成，總筆數 =", total_saved)

    return jsonify({
        "status": "success",
        "symbols": symbols,
        "rows_saved": total_saved
    })
# -------------------------------------
# 📌 新增：從 DB 讀取 OHLC
# -------------------------------------
# -------------------------------------
# 📌 新增：從 DB 讀取 OHLC
# -------------------------------------
@api_bp.route("/get_prices", methods=["GET"])
def get_prices():
    import sqlite3
    import pandas as pd
    import os
    from flask import current_app

    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol is required"}), 400

    # 正確 DB 位置（SQLAlchemy 寫入的位置）
    # 正確資料庫路徑（回到專案根目錄）
    db_path = os.path.join(current_app.root_path, "..", "instance", "app.db")
    db_path = os.path.abspath(db_path)

    conn = sqlite3.connect(db_path)


    query = """
        SELECT date, open, high, low, close, volume
        FROM stock_prices
        WHERE symbol = ?
        ORDER BY date ASC
    """

    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()

    if df.empty:
        return jsonify({"error": f"No data for {symbol}"}), 404

    data = df.to_dict(orient="records")

    return jsonify({
        "symbol": symbol,
        "count": len(data),
        "prices": data
    })


# -------------------------------------
# 📌 新增：MA Strategy 計算 API
# -------------------------------------
@api_bp.route("/ma_strategy", methods=["GET"])
def ma_strategy():
    import sqlite3
    import pandas as pd
    import os
    from flask import current_app

    symbol = request.args.get("symbol")
    short = request.args.get("short", default=5, type=int)
    long = request.args.get("long", default=20, type=int)

    if not symbol:
        return jsonify({"error": "symbol is required"}), 400
    if short >= long:
        return jsonify({"error": "short must be < long"}), 400

    # 正確 DB 路徑
    db_path = os.path.join(current_app.root_path, "instance", "app.db")
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        "SELECT date, close FROM stock_prices WHERE symbol=? ORDER BY date ASC",
        conn,
        params=(symbol,)
    )
    conn.close()

    if df.empty:
        return jsonify({"error": f"No data for {symbol}"}), 404

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    # 計算 MA
    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()

    df["position"] = (df["ma_short"] > df["ma_long"]).astype(int)
    df["ret"] = df["close"].pct_change()
    df["strategy_ret"] = df["position"].shift(1).fillna(0) * df["ret"]

    df["cum_ret"] = (1 + df["ret"]).cumprod()
    df["cum_strategy_ret"] = (1 + df["strategy_ret"]).cumprod()

    result = df.reset_index().to_dict(orient="records")

    return jsonify({
        "symbol": symbol,
        "short": short,
        "long": long,
        "rows": result
    })
