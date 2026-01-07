import os
from dotenv import load_dotenv
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-dev-key"

    _db = os.environ.get("DATABASE_URL")
    if _db:
        # Railway 有時候給 postgres://，SQLAlchemy 要 postgresql://
        if _db.startswith("postgres://"):
            _db = _db.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = _db
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "instance", "app.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
