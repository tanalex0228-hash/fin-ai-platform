# /Users/apple/Desktop/fin_ai_platform/app/main/routes.py

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

# Blueprint
main_bp = Blueprint("main", __name__, template_folder="../templates")


# ====================
# Dashboard
# ====================
@main_bp.route("/")
@login_required
def dashboard():
    return render_template("main/dashboard.html", user=current_user)


# ====================
# Backtest
# ====================
@main_bp.route("/backtest")
@login_required
def backtest_page():
    return render_template("main/backtest.html", user=current_user)


# ====================
# Screener
# ====================
@main_bp.route("/screener")
def page_screener():
    symbol = request.args.get("symbol")
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

@main_bp.route("/stock/<symbol>")
def stock_detail(symbol):
    data = get_stock_summary(symbol)
    return render_template("main/stock_detail.html", data=data)


# ====================
# Stocks Page
# ====================
@main_bp.route("/stocks")
def page_stocks():
    return render_template("main/stocks.html")
