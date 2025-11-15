# app/auth/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Email 或帳號已存在")
            return redirect(url_for("auth.register"))

        user = User(
            email=email,
            username=username,
            password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        )
        db.session.add(user)
        db.session.commit()
        flash("註冊成功，請登入")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_or_user = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter(
            (User.email == email_or_user) | (User.username == email_or_user)
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("帳號或密碼錯誤")
            return redirect(url_for("auth.login"))
        login_user(user)
        return redirect(url_for("main.dashboard"))
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已登出")
    return redirect(url_for("auth.login"))
