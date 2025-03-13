import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, send_from_directory, session, current_app
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from extensions import db
from routes.main import main
from routes.auth import auth
from models.user import User

# ★★★ ここを追加: text_evaluation から呼び出す関数を import
from models.text_evaluation import load_offensive_dict_with_tokens, load_whitelist

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

    # --- `data/` フォルダを確実に作成 ---
    DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(DATA_FOLDER, exist_ok=True)

    # --- 汎用的なファイルダウンロード関数 ---
    def download_file(url, local_path):
        """ 一般的なファイルダウンロード関数 """
        if not url:
            print(f"❌ {local_path} のURLが設定されていません")
            return

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ {local_path} をダウンロードしました")
            else:
                print(f"❌ {local_path} のダウンロードに失敗しました: {response.status_code}")
        except Exception as e:
            print(f"❌ {local_path} のダウンロード中にエラー発生: {str(e)}")

    # --- `offensive_words.json` のダウンロード ---
    def download_offensive_words():
        dropbox_url = os.getenv("DROPBOX_OFFENSIVE_URL")
        local_path = os.path.join(app.root_path, "data", "offensive_words.json")
        download_file(dropbox_url, local_path)

        # ▼ ダウンロード直後の中身を一部デバッグ表示
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print("[DEBUG] downloaded offensive_words.json content (first 10):")
                if "offensive" in data:
                    print(data["offensive"][:10])
                app.config["OFFENSIVE_WORDS"] = data  # ここは一旦 raw dict
                print("[DEBUG] app.config['OFFENSIVE_WORDS'] is set successfully!")
            except Exception as e:
                print(f"[DEBUG] error reading {local_path}: {e}")
        else:
            print(f"[DEBUG] {local_path} not found after download!")

    # --- `whitelist.json` のダウンロード ---
    def download_whitelist_json():
        dropbox_url = os.getenv("DROPBOX_WHITELIST_URL")
        local_path = os.path.join(app.root_path, "data", "whitelist.json")
        download_file(dropbox_url, local_path)

    # --- `surnames.csv` のダウンロード ---
    def download_surnames():
        dropbox_url = os.getenv("DROPBOX_SURNAMES_URL")
        local_csv_path = os.path.join(app.root_path, "data", "surnames.csv")

        if not dropbox_url:
            print("❌ DROPBOX_SURNAMES_URL が設定されていません")
            return

        download_file(dropbox_url, local_csv_path)
        print("✅ `surnames.csv` をダウンロードしました（ZIP解凍は不要）")

    # **アプリ起動時にファイルをダウンロード**
    download_offensive_words()
    download_whitelist_json()
    download_surnames()

    # --------------------------------------------------------
    # ★ ここで text_evaluation.py の関数を使って token 化する
    # --------------------------------------------------------
    # 1) OFFENSIVE_WORDS (raw dict) があれば token 化
    raw_offensive_dict = app.config.get("OFFENSIVE_WORDS", None)
    if raw_offensive_dict:
        # 形態素解析済みリストに変換
        #   まずファイルパスを "data/offensive_words.json" としてロード
        #   or 直接 raw_offensive_dict を使うために一時ファイルへ書き出す方法などがありますが、
        #   シンプルにもう一度 load_offensive_dict_with_tokens() を呼ぶ方が確実です。
        #   → もしくは text_evaluation.py に "dict を token 化する関数" を作ってもOK
        #   ここではもう一度ファイルを読む例を示します:
        offensive_list = load_offensive_dict_with_tokens(
            os.path.join(app.root_path, "data", "offensive_words.json")
        )
        app.config["OFFENSIVE_LIST"] = offensive_list
    else:
        app.config["OFFENSIVE_LIST"] = []

    # 2) whitelist.json を読み込んで set 化
    #    さきほどダウンロードした "data/whitelist.json" を読み込む
    whitelist_set = load_whitelist(
        os.path.join(app.root_path, "data", "whitelist.json")
    )
    app.config["WHITELIST_SET"] = whitelist_set

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
            return render_template("privacy.html", privacy_content="プライバシーポリシーは現在利用できません。")

    # ---- (C) 特定商取引法に基づく表記の表示 ----
    @app.route("/tokushoho")
    def show_tokushoho():
        tokushoho_path = os.path.join(app.root_path, "tokushoho.txt")
        try:
            with open(tokushoho_path, "r", encoding="utf-8") as f:
                tokushoho_content = f.read()
            return render_template("tokushoho.html", tokushoho_content=tokushoho_content)
        except FileNotFoundError:
            return render_template("tokushoho.html", tokushoho_content="特定商取引法に基づく表記は現在利用できません。")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
