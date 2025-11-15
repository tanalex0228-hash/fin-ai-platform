# config.py
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-dev-key"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 之後可以加一些你會用到的設定，例如：
    # YFINANCE_DEFAULT_PERIOD = "1y"
    # ASYNC_FETCH_MAX_CONCURRENCY = 10
