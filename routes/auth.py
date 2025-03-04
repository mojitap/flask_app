from flask import Blueprint, redirect, url_for, session, current_app, request
from flask_login import login_user
from requests_oauthlib import OAuth1Session
from authlib.integrations.requests_client import OAuth2Session
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

LINE_CLIENT_ID = os.getenv("LINE_CLIENT_ID")
LINE_CLIENT_SECRET = os.getenv("LINE_CLIENT_SECRET")

line_client = OAuth2Session(
    client_id=LINE_CLIENT_ID,
    client_secret=LINE_CLIENT_SECRET,
    scope="openid profile email",  # LINEが要求
    redirect_uri="https://mojitap.com/authorize/line",
    token_endpoint_auth_method="client_secret_post",
)

@auth.route("/login/line")
def login_line():
    """
    2) LINEログイン開始:
       認可URLを生成してリダイレクト
    """
    # 認可URLを生成
    authorization_url, state = line_client.create_authorization_url(
        "https://access.line.me/oauth2/v2.1/authorize"
    )
    # 必要なら session["line_auth_state"] = state
    return redirect(authorization_url)

@auth.route("/authorize/line")
def authorize_line():
    """LINE認証処理"""

    # ✅ LINEのアクセストークンを取得
    try:
        token = line_client.fetch_token(
            url="https://api.line.me/oauth2/v2.1/token",
            grant_type="authorization_code",
            code=request.args["code"],
        )
    except Exception as e:
        current_app.logger.error(f"LINEトークン取得失敗: {e}")
        return redirect(url_for("auth.login"))

    # ✅ LINEのプロフィールを取得
    try:
        resp = line_client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
        profile = resp.json()
    except Exception as e:
        current_app.logger.error(f"LINEプロフィール取得失敗: {e}")
        return redirect(url_for("auth.login"))

    # ✅ 必要な情報を取得
    line_user_id = profile.get("userId")  # LINEの内部User ID（UUID）
    line_display_name = profile.get("displayName")  # 表示名

    if not line_user_id:
        current_app.logger.error("LINE認証エラー: userIdが取得できませんでした")
        return redirect(url_for("auth.login"))

    # ✅ 仮のメールアドレス（emailは取得できない）
    fake_email = f"{line_user_id}@example.com"

    # ✅ 既存のユーザーをDBで検索 or 新規作成
    user = User.query.filter_by(id=line_user_id).first()
    if not user:
        user = User(
            id=line_user_id,
            email=fake_email,
            display_name=line_display_name,
            provider="line",
            line_display_name=line_display_name,
            line_user_id=line_user_id
        )
        db.session.add(user)
    else:
        user.display_name = line_display_name
        user.line_display_name = line_display_name
        user.line_user_id = line_user_id

    db.session.commit()  # ✅ 変更を保存

    # ✅ Flask-Login でログイン処理
    login_user(user, remember=True)

    # ✅ セッションに情報を保存
    session["user_id"] = user.id
    session["logged_in"] = True
    session.permanent = True

    current_app.logger.info(f"LINEログイン成功: {user.display_name} (ID: {line_user_id})")

    return redirect(url_for("main.home"))
