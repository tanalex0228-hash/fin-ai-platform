# app/main/routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

main_bp = Blueprint("main", __name__, template_folder="../templates/main")

@main_bp.route("/")
@login_required
def dashboard():
    # 之後在這裡呼叫服務：
    # 1. 從 DB 抓使用者偏好
    # 2. 預設顯示某檔股票或投組
    return render_template("main/dashboard.html", user=current_user)
