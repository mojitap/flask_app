import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, send_from_directory, session, current_app
from flask_login import LoginManager, login_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

# インポート文の修正（flask_app. を削除）
from extensions import db  # ✅ ルートにあるため
from routes.main import main
from routes.auth import auth
from models.user import User
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

load_dotenv()

# データベースのセットアップ
app = Flask(__name__, static_folder="static")
db = SQLAlchemy(app)  # ✅ ここでバインド
app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")

# 本番環境では PostgreSQL、本番用 DB がない場合は SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/local.db"  # ✅ SQLite に固定
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_AS_ASCII"] = False
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", False)  # ✅ DEBUGを明示的に設定

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # ← これが Flask-Migrate の設定

# モデルのインポート
from models.search_history import SearchHistory

with app.app_context():
    

# ユーザーログイン管理の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # ※ 必要なら、専用のログイン画面を定義

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# OAuth 初期化
oauth = OAuth(app)
oauth.init_app(app)
app.config["OAUTH_INSTANCE"] = oauth

# --- Dropbox からファイルをダウンロードする関数 ---
def download_file(url, local_path):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ {local_path} をダウンロードしました")
    else:
        print(f"❌ {local_path} のダウンロードに失敗しました: {response.status_code}")

# --- Blueprint の登録 ---
app.register_blueprint(main)
app.register_blueprint(auth)
# ※ 認証関連のルートはすべて routes/auth.py に記述しています

# --- Dropbox から offensive_words.json をダウンロード ---
dropbox_offensive_words_url = os.getenv("DROPBOX_OFFENSIVE_WORDS_URL")
local_offensive_words_path = os.path.join(app.root_path, "data", "offensive_words.json")
if dropbox_offensive_words_url:
    download_file(dropbox_offensive_words_url, local_offensive_words_path)

# offensive_words.json のロード
try:
    with open(local_offensive_words_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    app.config["OFFENSIVE_WORDS"] = data
    print("✅ `offensive_words.json` をロードしました")
except FileNotFoundError:
    app.logger.error(f"{local_offensive_words_path} が見つかりません。")
    app.config["OFFENSIVE_WORDS"] = {}

# --- OAuth 登録 ---
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

# --- 静的ファイル & 利用規約ページ ---
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

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

# ✅ Flask アプリを直接実行できるようにする
if __name__ == "__main__":
    app.run(debug=True)
