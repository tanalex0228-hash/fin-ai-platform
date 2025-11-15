from flask import Blueprint
api_bp = Blueprint("api", __name__)

try:
    from . import routes
    print("✅ routes.py 已成功載入")
except Exception as e:
    print("❌ routes.py 載入失敗：", e)
