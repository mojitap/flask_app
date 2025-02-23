from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os

# 環境変数を読み込む
load_dotenv()

# データベースの初期化
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    """Flask アプリの作成"""
    app = Flask(__name__)

    # アプリ設定
    app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 拡張機能をアプリに登録
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ルートの登録
    from flask_app.routes.main import main
    from flask_app.routes.auth import auth
    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app
