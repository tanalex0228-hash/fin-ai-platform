# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# 載入 .env
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-dev-key"

    # ✅ Railway 用 /tmp，Local 用 instance/app.db
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_STATIC_URL"):
        SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:////tmp/app.db"
    else:
        SQLALCHEMY_DATABASE_URI = (
            os.environ.get("DATABASE_URL")
            or "sqlite:///" + os.path.join(basedir, "instance", "app.db")
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
