# /Users/apple/Desktop/fin_ai_platform/app/main/routes.py

from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user

# Blueprint
main_bp = Blueprint("main", __name__, template_folder="../templates")


# ====================
# Dashboard
# ====================
@main_bp.route("/")
def dashboard():
    return render_template("main/dashboard.html", user=current_user)


# ====================
# Backtest
# ====================
@main_bp.route("/backtest")
def backtest_page():
    return render_template("main/backtest.html", user=current_user)


# ====================
# Screener
# ====================
@main_bp.route("/screener")
def page_screener():
    symbol = request.args.get("symbol", "2330.TW")
    return render_template("main/screener.html", symbol=symbol)


# ====================
# Charts
# ====================
@main_bp.route("/chart")
def chart_page():
    return render_template("main/chart.html")

@main_bp.route("/chart/macd")
def chart_macd_page():
    return render_template("main/chart_macd.html")

@main_bp.route("/chart/rsi")
def chart_rsi_page():
    return render_template("main/chart_rsi.html")

@main_bp.route("/chart/kd")
def chart_kd_page():
    return render_template("main/chart_kd.html")

@main_bp.route("/chart/bbands")
def chart_bbands_page():
    return render_template("main/chart_bbands.html")

@main_bp.route("/chart/volume")
def chart_volume_page():
    return render_template("main/chart_volume.html")

@main_bp.route("/chart/all")
def chart_all_page():
    symbol = request.args.get("symbol")
    return render_template("main/chart_all.html", symbol=symbol)


# ====================
# Stock Detail / Summary
# ====================
from app.services.stock_summary_service import get_stock_summary
from app.services.financials_service import get_financials

@main_bp.route("/stock/<symbol>")
def stock_detail(symbol):
    data = get_stock_summary(symbol)

    normalized = symbol.replace(".TW", "").replace(".TWO", "")
    try:
        fin = get_financials(stock_id=normalized, limit=8)
    except Exception as e:
        print("FIN ERROR", normalized, e)
        fin = None

    data["financials"] = fin
    return render_template("main/stock_detail.html", data=data)


# ====================
# Stocks Page
# ====================
@main_bp.route("/stocks")
def page_stocks():
    return render_template("main/stocks.html")


# ====================
# Monte Carlo
# ====================
from app.services.monte_carlo import run_monte_carlo_drawdown

def _get_close_prices(symbol: str, limit: int = 3000):
    """
    最穩版本：直接從 stock_prices 抓 close（不做 date('now') 過濾）
    SQLAlchemy 2.x compatible
    """
    from flask import current_app
    from sqlalchemy import create_engine, text

    raw = symbol.strip().upper()
    norm = raw.replace(".TW", "").replace(".TWO", "")

    candidates = [raw, norm]
    if norm.isdigit():
        candidates += [f"{norm}.TW", f"{norm}.TWO"]

    # 去重
    seen = set()
    candidates = [s for s in candidates if not (s in seen or seen.add(s))]

    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    engine = create_engine(uri)

    # ✅ 注意：LIMIT 直接用字面值，避免 SQLAlchemy/SQLite parameter issues
    sql = text(f"""
        SELECT close
        FROM stock_prices
        WHERE symbol = :sym
        ORDER BY date ASC
        LIMIT {int(limit)}
    """)

    for sym in candidates:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"sym": sym}).fetchall()

        closes = [float(r[0]) for r in rows if r[0] is not None]
        if len(closes) >= 60:
            return closes

    raise ValueError(f"DB stock_prices has no close data for {raw} (tried: {candidates})")


@main_bp.route("/monte_carlo")
def monte_carlo_page():
    # ✅ 跟 /chart/all 一樣：吃 query string 的 symbol
    symbol = request.args.get("symbol", "2330.TW")
    return render_template("main/monte_carlo.html", user=current_user, symbol=symbol)


@main_bp.route("/api/monte_carlo", methods=["GET"])
def api_monte_carlo():
    symbol = request.args.get("symbol", "2330.TW")
    n_simulations = int(request.args.get("n_simulations", 2000))
    horizon = int(request.args.get("horizon", 252))
    seed_raw = request.args.get("seed", "").strip()
    seed = int(seed_raw) if seed_raw != "" else None

    try:
        closes = _get_close_prices(symbol=symbol)

        res = run_monte_carlo_drawdown(
            prices=closes,
            n_simulations=n_simulations,
            horizon=horizon,
            seed=seed
        )

        return jsonify({
            "status": "success",
            "symbol": symbol.upper(),
            "params": res.params,
            "summary": res.summary,
            "drawdown_series": res.drawdown_series,
            "sample_paths": res.sample_paths,
            "last_close": float(closes[-1]),
            "history_len": len(closes),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@main_bp.route("/api/debug/db_schema")
def debug_db_schema():
    from flask import current_app
    from sqlalchemy import create_engine, inspect

    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    engine = create_engine(uri)
    insp = inspect(engine)

    out = {}
    for t in insp.get_table_names():
        cols = insp.get_columns(t)
        out[t] = [c["name"] for c in cols]

    return jsonify({
        "uri": uri,
        "tables": out
    })


## "uri": "sqlite:////Users/apple/Desktop/fin_ai_platform/instance/app.db"