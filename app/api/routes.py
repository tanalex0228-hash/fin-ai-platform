# app/api/routes.py

from flask import Blueprint, request, jsonify, current_app
from ..services import screener
import json
import os
import sqlite3
import pandas as pd
import numpy as np

from ..services import (
    data_fetch_async,
    etl,
    technical,
    portfolio,
    monte_carlo,
    fourier,
    stress_test,
    backtest
)
from ..services.deeplearning import cnn, rnn, knn
from ..services.data_fetch_async import fetch_price_batch_turbo
from . import api_bp
from app.services.scoring.a2_scoring import compute_a2_scores
from app.services.financials_service import get_financials





# ---------------------------------------
# 📌 從資料庫讀取單一股票資料
# ---------------------------------------
def load_price_df(symbol: str):
    db_path = os.path.join(current_app.root_path, "..", "instance", "app.db")
    db_path = os.path.abspath(db_path)
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM stock_prices WHERE symbol=? ORDER BY date ASC",
        conn,
        params=(symbol,)
    )

    conn.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df



# ---------------------------------------
# 📌 股票摘要（暫時 placeholder）
# ---------------------------------------
@api_bp.route("/stock/summary", methods=["GET"])
def stock_summary():
    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol required"}), 400

    data = get_stock_summary(symbol)
    return jsonify(data)




@api_bp.route("/financials/<stock_id>", methods=["GET"])
def api_financials(stock_id):
    limit = int(request.args.get("limit", 8))
    latest = request.args.get("latest", "false").lower() == "true"

    data = get_financials(
        stock_id=stock_id,
        limit=limit,
        latest=latest
    )
    return jsonify(data)




# ---------------------------------------
# 📌 主回測 API（MA + RSI + MACD + Trend）
# ---------------------------------------
@api_bp.route("/backtest", methods=["POST"])
def api_backtest():
    import datetime
    data = request.get_json() or {}

    symbol = data.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol required"}), 400

    # ====== MA ======
    short = int(data.get("short", 5))
    long = int(data.get("long", 20))
    if short <= 0 or long <= 0 or short >= long:
        return jsonify({"error": "short < long"}), 400

    # ====== RSI ======
    use_rsi = bool(data.get("use_rsi", False))
    rsi_period = int(data.get("rsi_period", 14))
    rsi_upper = float(data.get("rsi_upper", 70))

    # ====== MACD ======
    use_macd = bool(data.get("use_macd", False))
    macd_fast = int(data.get("macd_fast", 12))
    macd_slow = int(data.get("macd_slow", 26))
    macd_signal = int(data.get("macd_signal", 9))

    trend_filter = data.get("trend_filter")

    # ====== 撈資料 ======
    df = load_price_df(symbol)
    if df.empty:
        return jsonify({"error": "no data"}), 404

    # ====== 回測 ======
    result = backtest.backtest_ma(
        df,
        short=short,
        long=long,
        use_rsi=use_rsi,
        rsi_period=rsi_period,
        rsi_upper=rsi_upper,
        use_macd=use_macd,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        trend_filter=trend_filter,
        return_equity=True
    )

    # ====== 寫入 DB ======
    from app.models import BacktestResult
    from app.extensions import db

    perf = result.get("performance", {})
    params = result.get("params", {})
    trades = result.get("trades", [])
    equity_curve = result.get("equity_curve", [])

    bt = BacktestResult(
        user_id=None,
        symbol=symbol,
        strategy_name="ma",
        start_date=datetime.datetime.fromisoformat(trades[0]["entry_date"]) if trades else None,
        end_date=datetime.datetime.fromisoformat(trades[-1]["exit_date"]) if trades else None,
        total_return=perf.get("total_return"),
        buy_hold_return=perf.get("buy_hold_return"),
        max_drawdown=perf.get("max_drawdown"),
        sharpe_ratio=perf.get("sharpe_ratio") or perf.get("sharpe"),
        trade_count=perf.get("trade_count"),
        win_rate=perf.get("win_rate"),
        params_json=json.dumps(params, ensure_ascii=False),
        trades_json=json.dumps(trades, ensure_ascii=False),
        equity_json=json.dumps(equity_curve, ensure_ascii=False)
    )

    db.session.add(bt)
    db.session.commit()

    return jsonify({"symbol": symbol, **result})



# ---------------------------------------
# 🚀 Turbo async 抓股價 + 寫 DB
# ---------------------------------------
@api_bp.route("/fetch_prices", methods=["POST"])
def fetch_prices():
    import asyncio, time

    data = request.get_json()
    symbols = data.get("symbols", [])
    period = data.get("period", "1mo")

    if not symbols:
        return jsonify({"error": "symbols required"}), 400

    print("📌 開始 Turbo 抓價格…")
    t0 = time.time()

    try:
        price_dict = asyncio.run(
            fetch_price_batch_turbo(
                symbols,
                period=period,
                interval="1d",
                workers=10
            )
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    print("📌 Turbo 完成，耗時 =", round(time.time() - t0, 2), "秒")

    total_saved = 0
    failed = []

    for sym, df in price_dict.items():
        if df.empty:
            failed.append(sym)
            continue

        if isinstance(df.columns, pd.MultiIndex):
            try:
                df = df.xs(sym, level=1, axis=1)
            except:
                failed.append(sym)
                continue

        df.columns = [c.strip() for c in df.columns]
        try:
            total_saved += etl.save_price_df_to_db(sym, df)
        except:
            failed.append(sym)

    return jsonify({
        "status": "success",
        "rows_saved": total_saved,
        "failed": failed
    })



# ---------------------------------------
# 📌 多股票即時選股 Screener
# ---------------------------------------
@api_bp.route("/screener", methods=["POST"])
def api_screener():
    data = request.get_json() or {}

    symbols = data.get("symbols", [])
    period = data.get("period", "6mo")
    params = data.get("params", {})

    if not symbols:
        return jsonify({"error": "symbols 必須為非空的列表"}), 400

    try:
        results = screener.run_screener(
            symbols=symbols,
            period=period,
            params=params
        )
    except Exception as e:
        return jsonify({"error": f"screener 執行失敗：{e}"}), 500

    # ⭐⭐ 最重要：把所有 NaN / inf 轉成 None ⭐⭐
    clean = []
    for r in results:
        for k, v in r.items():
            if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
                r[k] = None
        if isinstance(r.get("latest"), dict):
            for k, v in r["latest"].items():
                if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
                    r["latest"][k] = None
        clean.append(r)

    return jsonify({
        "count": len(clean),
        "results": clean
    })



# ---------------------------------------
# 📌 從 DB 取出 OHLC
# ---------------------------------------
@api_bp.route("/get_prices", methods=["GET"])
@api_bp.route("/get_prices", methods=["GET"])
def get_prices():
    import numpy as np
    import pandas as pd

    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol required"}), 400

    df = load_price_df(symbol)
    if df.empty:
        return jsonify({"error": "no data"}), 404

    # 1. reset index (convert index -> date column)
    df = df.reset_index()

    # 2. convert Python date to safe JSON date format
    df["date"] = df["date"].apply(lambda d: d.strftime("%Y-%m-%d"))

    # 3. convert NaN, inf → None (valid JSON)
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

    # 4. convert to dict
    data = df.to_dict(orient="records")

    return jsonify({
        "symbol": symbol,
        "count": len(data),
        "prices": data
    })




# ---------------------------------------
# 📌 MA Strategy（前端畫圖）
# ---------------------------------------
@api_bp.route("/ma_strategy", methods=["GET"])
def ma_strategy():
    symbol = request.args.get("symbol")
    short = int(request.args.get("short", 5))
    long = int(request.args.get("long", 20))

    df = load_price_df(symbol)
    if df.empty:
        return jsonify({"error": "no data"}), 404

    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()
    df["position"] = (df["ma_short"] > df["ma_long"]).astype(int)
    df["ret"] = df["close"].pct_change()
    df["strategy_ret"] = df["position"].shift(1).fillna(0) * df["ret"]
    df["cum_ret"] = (1 + df["ret"]).cumprod()
    df["cum_strategy_ret"] = (1 + df["strategy_ret"]).cumprod()

    return jsonify(df.reset_index().to_dict(orient="records"))



# ---------------------------------------
# 📌 取得所有回測紀錄
# ---------------------------------------
@api_bp.route("/backtest/history", methods=["GET"])
def backtest_history():
    from app.models import BacktestResult
    results = BacktestResult.query.order_by(BacktestResult.created_at.desc()).all()

    history = []
    for r in results:
        history.append({
            "id": r.id,
            "symbol": r.symbol,
            "strategy": r.strategy_name,
            "total_return": r.total_return,
            "max_drawdown": r.max_drawdown,
            "trade_count": r.trade_count,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(history)



# ---------------------------------------
# 📌 取得單一回測紀錄詳情
# ---------------------------------------
@api_bp.route("/backtest/get/<int:bt_id>", methods=["GET"])
def api_get_backtest(bt_id):
    from app.models import BacktestResult
    bt = BacktestResult.query.get(bt_id)
    if not bt:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": bt.id,
        "symbol": bt.symbol,
        "strategy": bt.strategy_name,
        "performance": {
            "total_return": bt.total_return,
            "buy_hold_return": bt.buy_hold_return,
            "max_drawdown": bt.max_drawdown,
            "sharpe_ratio": bt.sharpe_ratio,
            "trade_count": bt.trade_count,
            "win_rate": bt.win_rate
        },
        "params": json.loads(bt.params_json),
        "trades": json.loads(bt.trades_json),
        "equity_curve": json.loads(bt.equity_json),
        "created_at": str(bt.created_at)
    })



# ---------------------------------------
# 📌 A2 基本面 + 技術面評分 API
# ---------------------------------------
@api_bp.route("/score_a2", methods=["POST"])
def score_a2():
    try:
        data = request.get_json()

        if not data or "stocks" not in data:
            return jsonify({"error": "Missing field 'stocks'"}), 400

        df = pd.DataFrame(data["stocks"])
        df = compute_a2_scores(df)

        #👉 重要：NaN → None
        df = df.replace({np.nan: None})

        return jsonify({
            "count": len(df),
            "results": df.to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@api_bp.route("/stocks_in_db", methods=["GET"])
def get_stocks_in_db():
    from app.extensions import db
    from app.models import StockPrice


    # 查詢 DB 內所有股票代號
    symbols = (
        db.session.query(StockPrice.symbol)
        .distinct()
        .order_by(StockPrice.symbol)
        .all()
    )

    # 轉成純字串 list
    symbols = [s[0] for s in symbols]

    return {"symbols": symbols}, 200




# ---------------------------------------
# 📌 每日更新：批次抓 tw_top500 → update_price_history
# ---------------------------------------
@api_bp.route("/update_today", methods=["POST"])
def update_today():
    """
    從 load_prices.py 呼叫 update_all_prices()
    用於每日更新資料（手動）
    """
    try:
        from load_prices import update_all_prices  # 注意：不改動 load_prices.py 命名

        # 你原本預設只抓前 300，抓 35 年 → 完全保留
        result = update_all_prices(limit=300, years=35)

        return jsonify({
            "status": "success",
            "message": "每日更新完成",
            "details": result
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
