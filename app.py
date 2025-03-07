import os
import json
import requests
import zipfile
from flask import Flask, render_template, redirect, url_for, send_from_directory, session, current_app
from flask_login import LoginManager, login_required, current_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from extensions import db
from routes.main import main
from routes.auth import auth
from models.user import User

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="static")
    
    # Flask設定
    app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/local.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"] = False

    # SQLAlchemy + Migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Blueprint登録
    app.register_blueprint(main)
    app.register_blueprint(auth)

    # OAuth 初期化
    oauth = OAuth(app)
    oauth.init_app(app)
    app.config["OAUTH_INSTANCE"] = oauth

    # --- Dropbox からファイルをダウンロードする関数 ---
    def download_file(url, local_path):
        """ 汎用的なファイルダウンロード関数 """
        if not url:
            app.logger.error(f"❌ {local_path} のURLが設定されていません")
            return

        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                app.logger.info(f"✅ {local_path} をダウンロードしました")
            else:
                app.logger.error(f"❌ {local_path} のダウンロードに失敗しました: {response.status_code}")
        except Exception as e:
            app.logger.error(f"❌ {local_path} のダウンロード中にエラー発生: {str(e)}")

    # --- `offensive_words.json` のダウンロード ---
    def download_offensive_words():
        dropbox_url = os.getenv("DROPBOX_OFFENSIVE_URL")
        local_path = os.path.join(app.root_path, "data", "offensive_words.json")
        download_file(dropbox_url, local_path)

    # --- `whitelist.json` のダウンロード ---
    def download_whitelist():
        dropbox_url = os.getenv("DROPBOX_WHITELIST_URL")
        local_path = os.path.join(app.root_path, "data", "whitelist.json")
        download_file(dropbox_url, local_path)

    # --- `surnames.zip` のダウンロード & 解凍 ---
    def download_surnames():
        dropbox_url = os.getenv("DROPBOX_SURNAMES_URL")
        local_zip_path = os.path.join(app.root_path, "data", "surnames.zip")
        extract_path = os.path.join(app.root_path, "data", "surnames")

        if not dropbox_url:
            app.logger.error("❌ DROPBOX_SURNAMES_URL が設定されていません")
            return

        try:
            os.makedirs(os.path.dirname(local_zip_path), exist_ok=True)

            response = requests.get(dropbox_url, stream=True)
            if response.status_code == 200:
                with open(local_zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                app.logger.info("✅ `surnames.zip` をダウンロードしました")

                # **ZIPファイルを解凍**
                with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)
                app.logger.info("✅ `surnames` フォルダを解凍しました")

                # **解凍後、ZIPファイルを削除**
                try:
                    os.remove(local_zip_path)
                    app.logger.info("✅ `surnames.zip` を削除しました")
                except Exception as e:
                    app.logger.warning(f"⚠️ `surnames.zip` の削除に失敗: {str(e)}")

            else:
                app.logger.error(f"❌ `surnames.zip` のダウンロードに失敗しました: {response.status_code}")

        except Exception as e:
            app.logger.error(f"❌ `surnames.zip` のダウンロードまたは解凍でエラー発生: {str(e)}")

    # **アプリ起動時にファイルをダウンロード**
    download_offensive_words()
    download_whitelist()
    download_surnames()

    # OAuth登録
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

    # 静的ファイル & 利用規約ページなどのルート
    @app.route("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory("static", filename)

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt")

    # ---- (A) 利用規約の表示 ----
    @app.route("/terms")
    def show_terms():
        terms_path = os.path.join(app.root_path, "terms.txt")
        try:
            with open(terms_path, "r", encoding="utf-8") as f:
                terms_content = f.read()
            return render_template("terms.html", terms_content=terms_content)
        except FileNotFoundError:
            current_app.logger.error(f"{terms_path} が見つかりません。")
            return render_template("terms.html", terms_content="利用規約は現在利用できません。")

    # ---- (B) プライバシーポリシーの表示 ----
    @app.route("/privacy")
    def show_privacy():
        privacy_path = os.path.join(app.root_path, "privacy.txt")
        try:
            with open(privacy_path, "r", encoding="utf-8") as f:
                privacy_content = f.read()
            return render_template("privacy.html", privacy_content=privacy_content)
        except FileNotFoundError:
            current_app.logger.error(f"{privacy_path} が見つかりません。")
            return render_template("privacy.html", privacy_content="プライバシーポリシーは現在利用できません。")

    # ---- (C) 特定商取引法に基づく表記の表示 ----
    @app.route("/tokushoho")
    def show_tokushoho():
        tokushoho_path = os.path.join(app.root_path, "tokushoho.txt")  # ここを実際の配置場所に合わせる
        try:
            with open(tokushoho_path, "r", encoding="utf-8") as f:
                tokushoho_content = f.read()
            return render_template("tokushoho.html", tokushoho_content=tokushoho_content)
        except FileNotFoundError:
            current_app.logger.error(f"{tokushoho_path} が見つかりません。")
            return render_template("tokushoho.html", tokushoho_content="特定商取引法に基づく表記は現在利用できません。")
 
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
