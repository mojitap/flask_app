from flask import Blueprint, redirect, url_for, session, current_app, request
from flask_login import login_user
from requests_oauthlib import OAuth1Session
import os
from models import User  # ✅ `models/__init__.py` で `User` をインポートしているため
from extensions import db

auth = Blueprint("auth", __name__)

@auth.route("/login/google")
def login_google():
    """Googleログイン処理"""
    oauth = current_app.config["OAUTH_INSTANCE"]
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/authorize/google")
def authorize_google():
    """Google認証処理"""
    oauth = current_app.config["OAUTH_INSTANCE"]
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()

    # Google の 'sub' を一意なIDとして利用
    google_id = user_info.get("sub")
    email = user_info.get("email")

    # ✅ ユーザーがDBに存在するかチェック
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(id=google_id, email=email)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("main.home"))

@auth.route("/login/twitter")
def login_twitter():
    """Twitterログイン処理"""
    twitter = OAuth1Session(
        client_key=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        callback_uri=url_for("auth.authorize_twitter", _external=True)
    )
    request_token_url = "https://api.twitter.com/oauth/request_token"
    response = twitter.fetch_request_token(request_token_url)
    oauth_token = response.get("oauth_token")
    return redirect(f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}")

@auth.route("/authorize/twitter")
def authorize_twitter():
    """Twitter認証処理"""
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
    user_info = twitter.get(user_info_url, params={"include_email": "true"}).json()
    
    print(f"✅ Twitter認証成功！取得データ: {user_info}")  # 👈 ここで取得データをログに出力
    
    twitter_id = user_info.get("id_str")
    email = user_info.get("email", f"{twitter_id}@example.com")  # ✅ Twitterはメールが取得できない可能性があるので、仮のメールを作成

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(id=twitter_id, email=email)
        db.session.add(user)
        db.session.commit()  # ✅ ここでDBに保存

    login_user(user)
    return redirect(url_for("main.home"))
