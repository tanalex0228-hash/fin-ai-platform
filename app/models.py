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
