# app/models.py
from datetime import datetime
from .extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 之後可以加：風險屬性、偏好產業等

class StockPrice(db.Model):
    __tablename__ = "stock_prices"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Float)

    # 報酬與一些基本 technical 可預先存
    return_pct = db.Column(db.Float)
    log_return = db.Column(db.Float)

    # ⭐⭐ 這三行是唯一新增的
    __table_args__ = (
        db.UniqueConstraint("symbol", "date", name="uix_symbol_date"),
    )


class StockFundFlow(db.Model):
    __tablename__ = "stock_funds"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)
    foreign = db.Column(db.Float)      # 外資買賣超
    investment_trust = db.Column(db.Float)  # 投信
    dealer = db.Column(db.Float)       # 自營商

class StockInfo(db.Model):
    __tablename__ = "stock_info"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.String(64))
    industry = db.Column(db.String(64))
    market = db.Column(db.String(16))  # TSE / OTC / US...

class IndicatorSnapshot(db.Model):
    """存技術指標某日的 snapshot，方便調用。"""
    __tablename__ = "indicators"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)

    ma_short = db.Column(db.Float)
    ma_long = db.Column(db.Float)
    macd = db.Column(db.Float)
    macd_signal = db.Column(db.Float)
    macd_hist = db.Column(db.Float)
    rsi = db.Column(db.Float)
    bb_upper = db.Column(db.Float)
    bb_lower = db.Column(db.Float)
    conv_smooth = db.Column(db.Float)   # 卷積平滑
    momentum = db.Column(db.Float)
    breakout_flag = db.Column(db.Boolean)

class PortfolioSuggestion(db.Model):
    """給使用者的投組建議結果."""
    __tablename__ = "portfolio_suggestions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    budget = db.Column(db.Float)
    risk_level = db.Column(db.String(16))  # conservative / balanced / aggressive
    # 可以存成 JSON 字串：包含每檔股票、權重、股數、預期報酬、風險...
    suggestion_json = db.Column(db.Text)

class BacktestResult(db.Model):
    __tablename__ = "backtest_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    symbol = db.Column(db.String(16), index=True)
    strategy_name = db.Column(db.String(64))

    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # 核心績效
    total_return = db.Column(db.Float)
    buy_hold_return = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    trade_count = db.Column(db.Integer)
    win_rate = db.Column(db.Float)

    # JSON 欄位
    params_json = db.Column(db.Text)
    trades_json = db.Column(db.Text)
    equity_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class AIPrediction(db.Model):
    __tablename__ = "ai_predictions"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), index=True)
    date = db.Column(db.Date, index=True)
    model_name = db.Column(db.String(64))   # 'cnn', 'lstm', 'knn' 等
    horizon_days = db.Column(db.Integer)    # 預測天數（例如 5 日後）
    prob_up = db.Column(db.Float)
    prob_down = db.Column(db.Float)
    raw_output_json = db.Column(db.Text)    # 模型輸出的向量、信心等


# === 財報：Income Statement ===
class FinancialIncomeStatement(db.Model):
    __tablename__ = "financial_income_statement"
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)

    revenue = db.Column(db.Float)
    gross_profit = db.Column(db.Float)
    operating_income = db.Column(db.Float)
    net_income = db.Column(db.Float)
    eps = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint("stock_id", "date", name="uix_income_stock_date"),
    )


# === 財報：Balance Sheet ===
class FinancialBalanceSheet(db.Model):
    __tablename__ = "financial_balance_sheet"

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)

    total_assets = db.Column(db.Float)
    total_liabilities = db.Column(db.Float)
    shareholders_equity = db.Column(db.Float)
    current_assets = db.Column(db.Float)
    current_liabilities = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint("stock_id", "date", name="uix_bs_stock_date"),
    )


# === 財報：Cashflow ===
class FinancialCashflow(db.Model):
    __tablename__ = "financial_cashflow"

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)

    operating_cashflow = db.Column(db.Float)
    investing_cashflow = db.Column(db.Float)
    financing_cashflow = db.Column(db.Float)
    free_cashflow = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint("stock_id", "date", name="uix_cf_stock_date"),
    )


# === 財報：Shares ===
class FinancialShares(db.Model):
    __tablename__ = "financial_shares"

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(16), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)

    shares_outstanding = db.Column(db.Float)
    capital = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint("stock_id", "date", name="uix_shares_stock_date"),
    )



class Fundamental(db.Model):
    __tablename__ = 'fundamentals'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String, index=True)
    date = db.Column(db.Date)


    revenue = db.Column(db.Float)
    eps = db.Column(db.Float)
    roe = db.Column(db.Float)
    roa = db.Column(db.Float)

    close = db.Column(db.Float)  # ← 新增季底股價
    
    pe = db.Column(db.Float)
    ps = db.Column(db.Float)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
