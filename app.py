from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user
from requests_oauthlib import OAuth1Session  # Twitter 認証で使用
from dotenv import load_dotenv
from routes import main, auth
from authlib.integrations.flask_client import OAuth
import os
import json
from models.user import db, User

# 環境変数の読み込み
load_dotenv()

# Flask アプリケーションの設定
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# データベース初期化
db.init_app(app)

# OAuth クライアント初期化
oauth = OAuth(app)
# Google OAuth 登録
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
# Twitter OAuth 登録
oauth.register(
    name='twitter',
    client_id=os.getenv('TWITTER_API_KEY'),
    client_secret=os.getenv('TWITTER_API_SECRET'),
    request_token_params={'scope': 'read write'}
)

# Flask-Login 設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Google 認証ルート
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/authorize/google")
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    email = user_info["email"]
    # 既にユーザーが存在するかチェック
    user = User.query.get(email)
    if not user:
        user = User(id=email, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect("/")

# Twitter 認証ルート
@app.route('/login/twitter')
def login_twitter():
    twitter = OAuth1Session(
        client_key=os.getenv('TWITTER_API_KEY'),
        client_secret=os.getenv('TWITTER_API_SECRET'),
        callback_uri=url_for('authorize_twitter', _external=True)
    )
    request_token_url = "https://api.twitter.com/oauth/request_token"
    response = twitter.fetch_request_token(request_token_url)
    oauth_token = response.get('oauth_token')
    redirect_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"
    return redirect(redirect_url)

@app.route('/authorize/twitter')
def authorize_twitter():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    if not oauth_verifier:
        return "Error: OAuth verifier is missing.", 400
    twitter = OAuth1Session(
        client_key=os.getenv('TWITTER_API_KEY'),
        client_secret=os.getenv('TWITTER_API_SECRET'),
        resource_owner_key=oauth_token,
        verifier=oauth_verifier
    )
    access_token_url = "https://api.twitter.com/oauth/access_token"
    tokens = twitter.fetch_access_token(access_token_url)
    user_info_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    user_info = twitter.get(user_info_url).json()
    twitter_id = user_info['id_str']
    # 既にユーザーが存在するかチェック（ここでは Twitter の id をそのままユーザーIDとして利用）
    user = User.query.get(twitter_id)
    if not user:
        user = User(id=twitter_id, email=user_info.get('email', ''))
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect("/")

# Blueprint 登録
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix="/auth")

# offensive_words.json の読み込み
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "offensive_words.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    offensive_words = data.get("categories", {}).get("insults", [])

# Flask の設定に offensive_words を登録
app.config['OFFENSIVE_WORDS'] = offensive_words

# 利用規約ページのルート
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

# テーブル作成（モジュールインポート時に必ず実行する）
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
