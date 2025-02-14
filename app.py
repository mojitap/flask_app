import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, send_from_directory, session
from flask_login import LoginManager, login_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

# 相対インポート
from extensions import db
from routes.main import main
from routes.auth import auth
from models.user import User

load_dotenv()

# Flask アプリケーションのセットアップ
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/local.db"
app.config["JSON_AS_ASCII"] = False

# データベースの初期化
db.init_app(app)

# ユーザーログイン管理の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # ログインが必要な場合、auth.login に飛ばす

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# OAuth 初期化
oauth = OAuth(app)

with app.app_context():
    oauth.init_app(app)  # app が完全に初期化された後に設定
    db.create_all()      # DB作成（初回のみ）

    # OAuth インスタンスを app.config に登録
    # → auth.py 内で使うため
    app.config["OAUTH_INSTANCE"] = oauth

# --- Dropbox からファイルをダウンロードする関数 ---
def download_file(url, local_path):
    """Dropbox の公開 URL からファイルをダウンロード"""
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
# ※ auth に関するすべてのルートは auth.py に書いてあるので、ここで追加のルート定義は不要

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

# --- Google OAuth の登録 ---
# ※ ルートの定義は auth.py に移動しているので、ここでは OAuth の登録だけ行います
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

@auth.route("/login/google")
def login_google():
    """Googleログイン処理"""
    oauth = current_app.config["OAUTH_INSTANCE"]  # ✅ `app.py` から OAuth インスタンスを取得
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/authorize/google")
def authorize_google():
    """Google認証処理"""
    oauth = current_app.config["OAUTH_INSTANCE"]
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    session["user"] = user_info  # ✅ 認証情報をセッションに保存
    return redirect(url_for("main.home"))

# --- Twitter OAuth の登録 ---
# ※ 必要ならここで登録する（auth.py で Twitter の処理が使えるようにするため）
oauth.register(
    name="twitter",
    client_id=os.getenv("TWITTER_API_KEY"),
    client_secret=os.getenv("TWITTER_API_SECRET"),
    request_token_params={"scope": "read write"}
)

@app.route("/login/twitter")
def login_twitter():
    twitter = OAuth1Session(
        client_key=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        callback_uri=url_for("authorize_twitter", _external=True)
    )
    request_token_url = "https://api.twitter.com/oauth/request_token"
    response = twitter.fetch_request_token(request_token_url)
    oauth_token = response.get("oauth_token")
    redirect_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"
    return redirect(redirect_url)

@app.route("/authorize/twitter")
def authorize_twitter():
    oauth_token = request.args.get("oauth_token")
    oauth_verifier = request.args.get("oauth_verifier")
    if not oauth_token or not oauth_verifier:
        return "Error: Missing OAuth parameters", 400

    twitter = OAuth1Session(
        client_key=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        resource_owner_key=oauth_token,
        verifier=oauth_verifier
    )
    access_token_url = "https://api.twitter.com/oauth/access_token"
    tokens = twitter.fetch_access_token(access_token_url)

    user_info_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    user_info = twitter.get(user_info_url).json()
    twitter_id = user_info.get("id_str")
    if not twitter_id:
        return "Error: Unable to retrieve Twitter user ID", 400

    email = user_info.get("email", f"{twitter_id}@twitter.com")
    user = User.query.get(twitter_id)
    if not user:
        user = User(id=twitter_id, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect("/")

# --- 静的ファイル ---
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# --- 利用規約ページ ---
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
