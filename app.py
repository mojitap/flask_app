import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, send_from_directory, session
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# --- 拡張機能のインポート ---
from extensions import db  # ✅ `db = SQLAlchemy()` は `extensions.py` に移動
from routes.main import main
from routes.auth import auth
from models.user import User

# --- Flask アプリの作成 ---
def create_app():
    load_dotenv()  # ✅ 正しいインデント
    app = Flask(__name__, static_folder="static")  # ✅ 正しいインデント

    # ここで Flask の設定をまとめて行う
    app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/local.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"] = False

    # --- SQLAlchemy + Migrate の初期化 ---
    db.init_app(app)
    migrate = Migrate(app, db)

    # --- Flask-Login 設定 ---
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # --- Blueprint の登録 ---
    app.register_blueprint(main)
    app.register_blueprint(auth)

    # --- OAuth 初期化 ---
    oauth = OAuth(app)
    oauth.init_app(app)
    app.config["OAUTH_INSTANCE"] = oauth

    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )

    oauth.register(
        name="twitter",
        client_id=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        request_token_params={"scope": "read write"}
    )

    # --- メインページのルート ---
    @app.route("/")
    def home():
        return render_template("index.html")

    # --- 静的ファイル & 利用規約ページ ---
    @app.route("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory("static", filename)

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt")

    @app.route("/terms")
    def show_terms():
        terms_path = os.path.join(app.root_path, "terms.txt")
        try:
            with open(terms_path, "r", encoding="utf-8") as f:
                terms_content = f.read()
            return render_template("terms.html", terms_content=terms_content)
        except FileNotFoundError:
            app.logger.error(f"利用規約ファイルが見つかりません: {terms_path}")
            return render_template("terms.html", terms_content="利用規約は現在利用できません。")

    return app  # ✅ `app` を返す

# --- エントリーポイント ---
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
