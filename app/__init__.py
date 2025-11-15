# app/__init__.py
from flask import Flask
from .extensions import db, login_manager
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from .models import User  # for Flask-Login

def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    # 基本設定
    from config import Config
    app.config.from_object(config_class or Config)

    # 初始化 extensions
    db.init_app(app)
    login_manager.init_app(app)

    # 使用者登入設定
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    login_manager.login_view = "auth.login"

    # 註冊 Blueprint
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    print ("🔥 All Routes Loaded:")

    print (app.url_map)

    return app
