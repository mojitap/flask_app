from flask import Blueprint, redirect, url_for, session
from authlib.integrations.flask_client import OAuth

auth = Blueprint("auth", __name__)
oauth = OAuth()

# Google OAuth クライアントを登録
oauth.register(
    name="google",
    client_id="あなたのGoogleクライアントID",
    client_secret="あなたのGoogleクライアントシークレット",
    access_token_url="https://accounts.google.com/o/oauth2/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v1/",
    client_kwargs={
        "scope": "openid email profile",
        "token_endpoint_auth_method": "client_secret_post",
    },
)

# Twitter OAuth クライアントを登録
oauth.register(
    name="twitter",
    client_id="あなたのTwitterクライアントID",
    client_secret="あなたのTwitterクライアントシークレット",
    request_token_url="https://api.twitter.com/oauth/request_token",
    access_token_url="https://api.twitter.com/oauth/access_token",
    authorize_url="https://api.twitter.com/oauth/authenticate",
    api_base_url="https://api.twitter.com/2/",
    client_kwargs={
        "scope": "tweet.read users.read offline.access",
        "token_endpoint_auth_method": "client_secret_post",
    },
)

# Googleログイン
@auth.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/authorize/google")
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("userinfo").json()
    session["user"] = user_info  # ユーザー情報をセッションに保存
    return redirect(url_for("main.index"))

# Twitterログイン
@auth.route("/login/twitter")
def login_twitter():
    redirect_uri = url_for("auth.authorize_twitter", _external=True)
    return oauth.twitter.authorize_redirect(redirect_uri)

@auth.route("/authorize/twitter")
def authorize_twitter():
    token = oauth.twitter.authorize_access_token()
    user_info = oauth.twitter.get("2/users/me").json()  # Twitter API 2.0を使用
    session["user"] = user_info  # ユーザー情報をセッションに保存
    return redirect(url_for("main.index"))

# ログアウト
@auth.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("main.index"))
