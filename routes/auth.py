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

    google_id = user_info.get("sub")
    email = user_info.get("email")
    google_name = user_info.get("name")  # <= ここが表示名

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            id=google_id, 
            email=email, 
            display_name=google_name,
            provider="google"
        )
        db.session.add(user)
    else:
        # 既存ユーザーでも、最新の名前を上書きしたいなら
        user.display_name = google_name
        user.provider = "google"

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

    twitter_id = user_info.get("id_str")
    twitter_email = user_info.get("email", f"{twitter_id}@example.com")
    twitter_name = user_info.get("name")            # 例: "Taro"
    twitter_screen_name = user_info.get("screen_name")  # 例: "taro_zzz"

    user = User.query.filter_by(email=twitter_email).first()
    if not user:
        user = User(
            id=twitter_id, 
            email=twitter_email, 
            display_name=f"{twitter_name} (@{twitter_screen_name})",
            provider="twitter",
            twitter_screen_name=twitter_screen_name
        )
        db.session.add(user)
    else:
        user.display_name = f"{twitter_name} (@{twitter_screen_name})"
        user.provider = "twitter"
        user.twitter_screen_name = twitter_screen_name

    db.session.commit()
    login_user(user)
    return redirect(url_for("main.home"))

@auth.route("/login/line")
def login_line():
    """LINEログイン開始"""
    oauth = current_app.config["OAUTH_INSTANCE"]  # あなたの実装に合わせる
    redirect_uri = url_for("auth.authorize_line", _external=True)
    return oauth.line.authorize_redirect(redirect_uri)

@auth.route("/authorize/line")
def authorize_line():
    """LINE認証処理"""
    oauth = current_app.config["OAUTH_INSTANCE"]
    token = oauth.line.authorize_access_token()
    # token の中にアクセストークンや IDトークンなどが含まれる

    # プロフィールを取得
    resp = oauth.line.get("https://api.line.me/v2/profile", token=token)
    profile = resp.json()
    line_user_id = profile.get("userId")
    line_display_name = profile.get("displayName")

    # 必要に応じて IDトークンを decode し、email を取得することもある
    # id_token = token.get("id_token")
    # ...

    # DBにユーザーを保存 or 更新
    user = User.query.filter_by(line_id=line_user_id).first()
    if not user:
        user = User(
            id=line_user_id,  # あるいは line_id カラムを用意
            display_name=line_display_name,
            provider="line"
        )
        db.session.add(user)
    else:
        user.display_name = line_display_name
        user.provider = "line"

    db.session.commit()
    login_user(user)
    return redirect(url_for("main.home"))
